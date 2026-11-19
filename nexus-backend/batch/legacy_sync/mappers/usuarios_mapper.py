"""Usuarios (unificacao da tabela `users`, 62 colunas -> modelo normalizado).

Normalizacoes:
- polo: se o usuario tem escola e a escola tem polo, vale o polo da escola;
  senao `users.polo` (id da conta role 3; polo extinto no legado -> NULL).
- aluno sem polo e sem escola -> polo "EAD" e escola "EAD" criados no NEXUS
  (carregar_lotacao_ead); a modalidade do aluno continua `ead`.
- perfil (carga unica de migracao, sem convivencia com o legado):
  titular de conta polo/escola -> `polo`/`escola`; conta role 3/4 migrada ->
  `polo`/`escola`; role 2 com `is_instructor=1` -> `professor`; demais role 2
  -> `aluno` (inclusive is_secret/is_exec). alunos/professores sao derivados
  do perfil gravado aqui (carregar_perfis_migrados).
- Polo/Escola sao extraidos nas tabelas proprias; aqui apenas as FKs.
- CPF gravado so com digitos (com/sem mascara viram a mesma chave); CPF fora
  do formato vira NULL. e-mail gravado em minusculas.
- e-mail e CPF duplicados no legado viram NULL no destino (unicidade garantida
  por indice parcial) e sao gravados como AVISO em etl_erros pelo runner.
- senha: migrada como esta (hash legado), marcada `senha_algoritmo='legacy_bcrypt'`
  para o lazy rehash do modulo Login.
- o campo `users.status` (int, sem dicionario) mapeia para ativo/inativo.

Re-upsert (incremental / nova carga) NAO sobrescreve o que o NEXUS mantem:
- `senha_hash` so e atualizada enquanto o usuario ainda nao logou no NEXUS
  (`senha_algoritmo = 'legacy_bcrypt'`); depois do rehash, a senha e do NEXUS.
- `senha_algoritmo` e `ultimo_login_em` sao gravados so no INSERT.
- `email`/`cpf` ja preenchidos no destino sao mantidos (um NULL vindo da
  deduplicacao nunca apaga o valor existente).
"""
from __future__ import annotations

import logging
from typing import ClassVar

from .base import BaseMapper

logger = logging.getLogger(__name__)

USERS_COLUMNS = [
    "id", "first_name", "last_name", "email", "password", "role_id",
    "date_added", "last_modified", "status", "is_instructor", "image",
    "celular", "is_vendedor", "cpf", "p_cadastro", "p_edicao", "p_acomp",
    "p_vendas", "p_matriculas", "p_matricula_manual", "p_ranking", "polo",
    "escola", "telefone", "nascimento", "revalidacao", "is_secret", "is_exec",
    "is_pedag", "p_cursos", "p_users", "p_chat", "p_academico", "p_financeiro",
    "legacy_id", "duplicata_id", "rg", "nome_escola",
]

# Escopo da carga: users role 2 (pessoas) + contas de acesso role 3 (polo) e
# role 4 (escola) SOMENTE quando nao existe role 2 com o mesmo CPF (sem par).
ROLE_ID_CARGA = 2
ROLES_CONTA = (3, 4)

# TODO(validar no legado): status=0 hoje conta como ativo (sem dicionario).
STATUS_ATIVOS = {None, 0, 1}


def normalize_cpf(value) -> str | None:
    """CPF canonico (11 digitos). Aceita mascara e zero a esquerda perdido.

    Retorna None quando nao ha digitos; levanta ValueError se o formato e
    invalido (para o mapper registrar aviso).
    """
    digits = BaseMapper.only_digits(value)
    if not digits or set(digits) == {"0"}:
        return None
    if len(digits) == 10:  # CPF salvo como numero perdeu o zero a esquerda
        digits = digits.zfill(11)
    if len(digits) != 11:
        raise ValueError(digits)
    return digits


def cpf_ou_none(value) -> str | None:
    """normalize_cpf sem excecao (CPF invalido -> None)."""
    try:
        return normalize_cpf(value)
    except ValueError:
        return None


def carregar_titulares_cpf(source, emails_role2: set[str] | None = None) -> dict[str, int]:
    """CPF -> users.id do "titular" da pessoa (quem vira o usuario no NEXUS).

    Regra unica, usada pelo UsuarioMapper e pelo vinculo de coordenador:
    1. o menor users.id role 2 com esse CPF;
    2. sem role 2 com o CPF: a menor conta role 3/4 com esse CPF (opcao B:
       a propria conta de polo/escola vira usuario, sem duplicar a pessoa).
    Contas role 3/4 sem CPF valido nao entram aqui: cada uma e o proprio
    titular. Se `emails_role2` for passado, recebe os e-mails do role 2.
    """
    titulares: dict[str, int] = {}
    for u in source.stream("users", ["id", "cpf", "email"], where=f"role_id = {ROLE_ID_CARGA}", order="id"):
        cpf = cpf_ou_none(u.get("cpf"))
        if cpf:
            titulares.setdefault(cpf, int(u["id"]))
        if emails_role2 is not None:
            email = (u.get("email") or "").strip().lower()
            if email:
                emails_role2.add(email)
    for u in source.stream(
        "users", ["id", "cpf"], where=f"role_id IN {ROLES_CONTA}", order="id",
    ):
        cpf = cpf_ou_none(u.get("cpf"))
        if cpf:
            titulares.setdefault(cpf, int(u["id"]))
    return titulares


def carregar_lotacao_ead(registry) -> tuple[str, str] | None:
    """(polo_id, escola_id) do polo "EAD" e da escola "EAD" criados no NEXUS.

    Aluno sem polo e sem escola e vinculado a eles (modalidade continua ead).
    Exige exatamente uma escola "EAD" (criada no NEXUS) ligada a um polo
    "EAD"; senao retorna None e nada e vinculado.
    """
    target = getattr(registry, "_target", None) if registry else None
    conn = getattr(target, "conn", None) if target else None
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT e.polo_id, e.id FROM escolas e JOIN polos p ON p.id = e.polo_id "
                "WHERE upper(trim(e.nome)) = 'EAD' AND upper(trim(p.nome)) = 'EAD' "
                "AND e.legacy_id IS NULL"
            )
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nao foi possivel localizar polo/escola EAD: %s", exc)
        return None
    if len(rows) != 1 or not isinstance(rows[0], (list, tuple)) or len(rows[0]) != 2:
        logger.warning("Polo/escola EAD: esperado 1 par, encontrado %d; alunos EAD ficam sem vinculo", len(rows))
        return None
    return str(rows[0][0]), str(rows[0][1])


def carregar_usuarios_migrados(registry) -> dict[int, dict] | None:
    """users.id legado -> {perfil, polo_id, escola_id} gravados em usuarios.

    Fonte unica para alunos/professores (mesmo perfil e mesma lotacao do
    usuario). None se o destino nao estiver acessivel (testes).
    """
    target = getattr(registry, "_target", None) if registry else None
    conn = getattr(target, "conn", None) if target else None
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.legacy_id, p.nome, u.polo_id, u.escola_id FROM usuarios u "
                "JOIN perfis p ON p.id = u.perfil_id "
                "WHERE u.legacy_table = 'users' AND u.legacy_id IS NOT NULL"
            )
            return {
                int(r[0]): {
                    "perfil": r[1],
                    "polo_id": str(r[2]) if r[2] else None,
                    "escola_id": str(r[3]) if r[3] else None,
                }
                for r in cur.fetchall()
            }
    except (TypeError, ValueError, IndexError):  # fakes de teste
        return None


class UsuarioMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_COLUMNS + ["escola_old"]
    target_table: ClassVar[str] = "usuarios"
    order_by: ClassVar[str | None] = "id"
    incremental_column: ClassVar[str | None] = "last_modified"

    insert_only_columns: ClassVar[tuple[str, ...]] = ("senha_algoritmo", "ultimo_login_em")
    update_expressions: ClassVar[dict[str, str]] = {
        "senha_hash": (
            "CASE WHEN {table}.senha_algoritmo = 'legacy_bcrypt' "
            "THEN EXCLUDED.senha_hash ELSE {table}.senha_hash END"
        ),
        "email": "COALESCE({table}.email, EXCLUDED.email)",
        "cpf": "COALESCE({table}.cpf, EXCLUDED.cpf)",
    }

    def __init__(self, registry=None) -> None:
        super().__init__(registry)
        self._seen_cpf: dict[str, int | None] = {}
        self._perfis_uuid: dict[str, str] | None = None
        # vinculo role 3/4 -> titular role 2 (preenchidos em iter_source)
        self._titular_cpf: dict[str, int] = {}
        self._polos_por_cpf: dict[str, list[int]] = {}    # cpf -> [users.id role 3]
        self._escolas_por_cpf: dict[str, list[int]] = {}  # cpf -> [escola_old role 4]
        self._escola_polo: dict[str, str | None] | None = None
        self._emails_role2: set[str] = set()
        self._ead: tuple[str, str] | None = None
        self._load_existing_uniques()

    def initial_where(self, last_run=None) -> str | None:
        """role 2 + contas role 3/4 (filtradas no map: so as sem par role 2)."""
        return f"role_id IN ({ROLE_ID_CARGA}, {', '.join(map(str, ROLES_CONTA))})"

    def iter_source(self, source, last_run=None):
        self._carregar_vinculos(source)
        yield from super().iter_source(source, last_run)

    def _carregar_vinculos(self, source) -> None:
        """Le do legado as contas role 3 (polo) e role 4 (escola) por CPF."""
        self._emails_role2 = set()
        self._titular_cpf = carregar_titulares_cpf(source, self._emails_role2)
        self._ead = carregar_lotacao_ead(self.registry)
        if self._ead:
            logger.info("Alunos sem polo/escola -> polo/escola EAD (%s / %s)", *self._ead)
        self._polos_por_cpf, self._escolas_por_cpf = {}, {}
        for u in source.stream(
            "users", ["id", "role_id", "cpf", "escola_old"],
            where="role_id IN (3, 4)", order="id",
        ):
            cpf = cpf_ou_none(u.get("cpf"))
            if not cpf:
                continue
            if self.as_int(u.get("role_id")) == 3:
                self._polos_por_cpf.setdefault(cpf, []).append(int(u["id"]))
            else:
                escola_old = self.as_int(u.get("escola_old"))
                lista = self._escolas_por_cpf.setdefault(cpf, [])
                if escola_old and escola_old not in lista:
                    lista.append(escola_old)
        logger.info(
            "Vinculos por CPF: %d titulares, %d CPFs com polo, %d CPFs com escola",
            len(self._titular_cpf), len(self._polos_por_cpf), len(self._escolas_por_cpf),
        )

    def _polo_da_escola(self, escola_id: str) -> str | None:
        if self._escola_polo is None:
            self._escola_polo = {}
            conn = self._target_conn()
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, polo_id FROM escolas")
                    self._escola_polo = {str(r[0]): (str(r[1]) if r[1] else None) for r in cur.fetchall()}
        return self._escola_polo.get(escola_id)

    def _vinculo(self, cpf: str | None, current_lid: int | None):
        """(perfil, polo_id, escola_id) do titular que casa com contas role 3/4.

        So o titular do CPF (ver carregar_titulares_cpf) recebe o vinculo. Escola
        prevalece sobre polo no usuario (ele continua coordenador do polo em
        polos.coordenador_usuario_id). Varios polos/escolas -> o de menor id
        legado + aviso.
        """
        if not cpf or current_lid is None or self._titular_cpf.get(cpf) != current_lid:
            return None
        resolve = self.registry.resolve if self.registry else (lambda *a: None)
        polos = [p for p in (resolve("polos", "users", lid) for lid in self._polos_por_cpf.get(cpf, [])) if p]
        escolas = [e for e in (resolve("escolas", "users", eo) for eo in self._escolas_por_cpf.get(cpf, [])) if e]
        if len(polos) > 1:
            self.warn(f"cpf {cpf} (users.id={current_lid}) coordena {len(polos)} polos; usuario fica no 1o")
        if len(escolas) > 1:
            self.warn(f"cpf {cpf} (users.id={current_lid}) casa com {len(escolas)} escolas; usuario fica na 1a")
        if escolas:
            polo_id = self._polo_da_escola(escolas[0]) or (polos[0] if polos else None)
            return "escola", polo_id, escolas[0]
        if polos:
            return "polo", polos[0], None
        return None

    def _target_conn(self):
        target = getattr(self.registry, "_target", None) if self.registry else None
        return getattr(target, "conn", None) if target else None

    def _load_existing_uniques(self) -> None:
        """Pre-popula a dedup com e-mails/CPFs ja gravados no destino."""
        conn = self._target_conn()
        if conn is None:
            return
        try:
            sql = "SELECT legacy_id, email, cpf FROM usuarios WHERE email IS NOT NULL OR cpf IS NOT NULL"
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nao foi possivel carregar emails/cpfs existentes de usuarios: %s", exc)
            return
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            lid = int(r[0]) if r[0] is not None else None
            if r[1]:
                self.seen_emails.setdefault(str(r[1]).lower().strip(), lid)
            cp = self.only_digits(r[2])
            if cp:
                self._seen_cpf.setdefault(cp.zfill(11) if len(cp) == 10 else cp, lid)

    def _dedup_cpf(self, cpf: str | None, current_lid: int | None = None) -> str | None:
        if not cpf:
            return None
        if cpf in self._seen_cpf:
            existing_lid = self._seen_cpf[cpf]
            if current_lid is not None and existing_lid is not None and existing_lid == current_lid:
                return cpf
            self.warn(f"cpf duplicado ignorado: {cpf} (users.id={current_lid}, ja usado por legacy_id={existing_lid})")
            return None
        self._seen_cpf[cpf] = current_lid
        return cpf

    def _clean_cpf(self, raw, current_lid: int | None) -> str | None:
        try:
            return normalize_cpf(raw)
        except ValueError:
            self.warn(f"cpf invalido ignorado: {raw!r} (users.id={current_lid})")
            return None

    def _perfil_uuid(self, nome: str | None) -> str | None:
        if not nome:
            return None
        if self._perfis_uuid is None:
            conn = self._target_conn()
            if conn is None:
                return None
            with conn.cursor() as cur:
                cur.execute("SELECT nome, id FROM perfis")
                self._perfis_uuid = {r[0]: str(r[1]) for r in cur.fetchall()}
        return self._perfis_uuid.get(nome)

    def _vinculo_proprio(self, row: dict, role: int | None):
        """Conta role 3/4 sem CPF: o vinculo e o do proprio polo/escola."""
        resolve = self.registry.resolve if self.registry else (lambda *a: None)
        if role == 3:
            polo_id = resolve("polos", "users", row.get("id"))
            return ("polo", polo_id, None) if polo_id else None
        escola_id = resolve("escolas", "users", row.get("escola_old"))
        return ("escola", self._polo_da_escola(escola_id), escola_id) if escola_id else None

    def map(self, row: dict) -> dict | None:
        current_lid = self.as_int(row.get("id"))
        role = self.as_int(row.get("role_id"))
        conta = role in ROLES_CONTA
        try:
            cpf_canonico = normalize_cpf(row.get("cpf"))
        except ValueError:
            cpf_canonico = None

        if conta and cpf_canonico and self._titular_cpf.get(cpf_canonico) != current_lid:
            # a pessoa ja existe (role 2 ou outra conta com o mesmo CPF):
            # a conta so gera vinculo no titular, nunca um usuario duplicado
            return None

        email_raw = self.str_clean(row.get("email"), 255)
        email_raw = email_raw.lower() if email_raw else None
        if conta and email_raw in self._emails_role2:
            # o e-mail pertence a uma pessoa role 2: fica com ela
            self.warn(f"email {email_raw} da conta role {role} (users.id={current_lid}) ja usado por role 2; ignorado")
            email_raw = None
        email = self._dedup_email(email_raw, current_lid)
        cpf = self._dedup_cpf(self._clean_cpf(row.get("cpf"), current_lid), current_lid)

        vinculo = self._vinculo(cpf_canonico, current_lid)
        if not vinculo and conta and not cpf_canonico:
            vinculo = self._vinculo_proprio(row, role)
        if vinculo:
            # titular de conta(s) role 3/4: perfil e lotacao vem do polo/escola
            nome_perfil, polo_id, escola_id = vinculo
        else:
            if conta:
                nome_perfil = "polo" if role == 3 else "escola"
            elif self.as_bool(row.get("is_instructor")):
                nome_perfil = "professor"
            else:
                nome_perfil = "aluno"
            polo_id = self.registry.resolve("polos", "users", row.get("polo")) if self.registry else None
            escola_id = self.registry.resolve("escolas", "users", row.get("escola")) if self.registry else None
            if escola_id:
                # a escola define o polo: cobre users.polo extinto no legado e
                # users.polo divergente do polo da escola (decisao: escola vence)
                polo_id = self._polo_da_escola(escola_id) or polo_id
            if nome_perfil == "aluno" and not polo_id and not escola_id and self._ead:
                # aluno EAD (sem polo/escola no legado): polo e escola EAD do NEXUS
                polo_id, escola_id = self._ead
        perfil_id = self._perfil_uuid(nome_perfil)

        status_raw = row.get("status")
        status_int = self.as_int(status_raw) if status_raw not in (None, "") else None
        status = "ativo" if status_int in STATUS_ATIVOS else "inativo"
        return {
            "nome": self.str_clean(row.get("first_name"), 255) or "",
            "sobrenome": self.str_clean(row.get("last_name"), 255) or "",
            "email": email,
            "cpf": cpf,
            "senha_hash": self.str_clean(row.get("password"), 255),
            "senha_algoritmo": "legacy_bcrypt",
            "telefone": self.str_clean(row.get("telefone"), 64),
            "celular": self.str_clean(row.get("celular"), 64),
            "foto_url": self.str_clean(row.get("image"), 500),
            "perfil_id": perfil_id,
            "polo_id": polo_id,
            "escola_id": escola_id,
            "status": status,
            "ultimo_login_em": None,
        }
