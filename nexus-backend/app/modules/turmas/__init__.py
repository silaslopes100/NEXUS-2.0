"""Módulo de Turmas do NEXUS 2.0.

- Início e fim da turma = vigência do Calendário Acadêmico do curso (não se editam).
- Situação derivada: planejada → em andamento → concluída / cancelada (ver `regras.py`).
  Concluída e cancelada ficam só leitura até o admin reabrir.
- Código automático {SIGLA}-{ANO}-{SEQ}; modalidade presencial/EAD; vagas; responsável da unidade.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.config import settings
from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.roles import nomes_equivalentes, perfil_canonico, perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.polos_escolas.repository import get_polos_escolas_repository
from app.modules.professores.access import listar_vinculos_academicos_docente, usuario_eh_professor
from app.modules.turmas import regras

router = APIRouter(prefix="/turmas", tags=["Turmas & Calendários"])

_PERFIS_TURMA = ["admin", "polo", "escola"]

NomeTurma = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]
Modalidade = Literal["presencial", "ead"]
Turno = Literal["manha", "tarde", "noite", "integral"]


class TurmaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    codigo: Optional[str] = None
    curso_id: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    nome: str
    modalidade: str = "presencial"
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    situacao: str = "em_andamento"


class TurmaDetalheSchema(TurmaSchema):
    curso_nome: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    calendario_nome: Optional[str] = None
    total_alunos: int = 0
    turno: Optional[str] = None
    horario_inicio: Optional[time] = None
    horario_fim: Optional[time] = None
    vagas: Optional[int] = None
    local_aulas: Optional[str] = None
    responsavel_id: Optional[str] = None
    responsavel_nome: Optional[str] = None
    concluida_em: Optional[datetime] = None
    cancelada_em: Optional[datetime] = None
    motivo_cancelamento: Optional[str] = None
    periodo_encerrado: bool = False
    andamento_pct: Optional[float] = None


class TurmaWriteSchema(BaseModel):
    """Início e fim não são enviados: vêm da vigência do calendário do curso."""
    curso_id: uuid.UUID
    polo_id: Optional[uuid.UUID] = None
    escola_id: Optional[uuid.UUID] = None
    nome: NomeTurma
    modalidade: Modalidade = "presencial"
    turno: Optional[Turno] = None
    horario_inicio: Optional[time] = None
    horario_fim: Optional[time] = None
    vagas: Optional[int] = Field(default=None, gt=0, le=10000)
    local_aulas: Optional[str] = Field(default=None, max_length=500)
    responsavel_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def _horario(self) -> "TurmaWriteSchema":
        if self.horario_inicio and self.horario_fim and self.horario_fim <= self.horario_inicio:
            raise ValueError("O horário de término deve ser depois do início")
        if self.local_aulas is not None:
            self.local_aulas = self.local_aulas.strip() or None
        return self


class TurmasPaginaSchema(BaseModel):
    items: List[TurmaDetalheSchema]
    total: int
    limit: int
    offset: int


class AlunoTurmaSchema(BaseModel):
    aluno_id: str
    nome: Optional[str] = None
    email: Optional[str] = None
    numero_matricula: Optional[str] = None
    status: Optional[str] = None
    data_matricula: Optional[datetime] = None


class AlunosTurmaPaginaSchema(BaseModel):
    items: List[AlunoTurmaSchema]
    total: int
    limit: int
    offset: int


class CursoDetalhesSchema(BaseModel):
    disciplinas: List[Dict[str, Any]]
    turmas: List[TurmaSchema]


class CancelarTurmaRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)


class SugestaoTurmaSchema(BaseModel):
    codigo: str
    nome: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    calendario_nome: Optional[str] = None


class ResponsavelSchema(BaseModel):
    id: str
    nome: str
    perfil: str


_turmas_db: Dict[str, Dict[str, Any]] = {}
_turma_alunos_db: List[Dict[str, Any]] = []

_ALUNOS_ATIVOS_SQL = (
    "(SELECT COUNT(*) FROM turma_alunos ta WHERE ta.turma_id = t.id AND COALESCE(ta.status, 'ativo') = 'ativo')"
)

# Andamento da lista: horas das aulas previstas já cumpridas (ata prevista/reposição) ÷ total previsto.
_ANDAMENTO_SQL = """
    (SELECT ROUND(100.0 * COALESCE(SUM(ap.horas_previstas) FILTER (WHERE EXISTS (
                SELECT 1 FROM aulas_ministradas am
                 WHERE am.aula_prevista_id = ap.id AND am.tipo IN ('prevista', 'reposicao'))), 0)
            / NULLIF(SUM(ap.horas_previstas), 0), 1)
       FROM aulas_previstas ap WHERE ap.turma_id = t.id)
"""

_TURMA_SELECT = f"""
    SELECT t.id, t.codigo, t.curso_id, t.polo_id, t.escola_id, t.nome, t.modalidade, t.data_inicio, t.data_fim,
           t.turno, t.horario_inicio, t.horario_fim, t.vagas, t.local_aulas, t.responsavel_id,
           t.concluida_em, t.cancelada_em, t.motivo_cancelamento,
           c.nome AS curso_nome, p.nome AS polo_nome, e.nome AS escola_nome, ca.nome AS calendario_nome,
           NULLIF(TRIM(CONCAT_WS(' ', r.nome, r.sobrenome)), '') AS responsavel_nome,
           {_ALUNOS_ATIVOS_SQL} AS total_alunos,
           {_ANDAMENTO_SQL} AS andamento_pct
    FROM turmas t
    LEFT JOIN cursos c ON c.id = t.curso_id
    LEFT JOIN calendarios_academicos ca ON ca.id = c.calendario_id
    LEFT JOIN polos p ON p.id = t.polo_id
    LEFT JOIN escolas e ON e.id = t.escola_id
    LEFT JOIN usuarios r ON r.id = t.responsavel_id
"""

_CAMPOS_ESCRITA = (
    "curso_id", "polo_id", "escola_id", "nome", "modalidade", "data_inicio", "data_fim",
    "turno", "horario_inicio", "horario_fim", "vagas", "local_aulas", "responsavel_id",
)

_ALUNO_NOME_SQL = "trim(concat(u.nome, ' ', u.sobrenome))"


def _texto(valor: Any) -> Optional[str]:
    return str(valor) if valor else None


def _carga_repo():
    from app.modules.carga_horaria.repository import get_carga_horaria_repository

    return get_carga_horaria_repository()


def _enriquecer(turma: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if turma is None:
        return None
    for k in ("id", "curso_id", "polo_id", "escola_id", "responsavel_id"):
        if turma.get(k) is not None:
            turma[k] = str(turma[k])
    if turma.get("andamento_pct") is not None:
        turma["andamento_pct"] = float(turma["andamento_pct"])
    turma["situacao"] = regras.situacao(turma)
    turma["periodo_encerrado"] = regras.periodo_encerrado(turma)
    return turma


def _escopo_usuario(user: UserResponse) -> Tuple[Optional[str], Optional[str]]:
    """Retorna (polo_id, escola_id) a que o usuário está restrito; admin não tem restrição."""
    perfil = perfil_do_usuario(user)
    if perfil == "polo":
        if not user.polo_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo")
        return str(user.polo_id), None
    if perfil == "escola":
        if not user.escola_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Escola sem vínculo")
        return None, str(user.escola_id)
    return None, None


def _exigir_no_escopo(turma: Optional[Dict[str, Any]], user: UserResponse) -> Dict[str, Any]:
    if turma is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")
    polo_id, escola_id = _escopo_usuario(user)
    if (polo_id and str(turma.get("polo_id")) != polo_id) or (
        escola_id and str(turma.get("escola_id")) != escola_id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta Turma")
    return turma


def _resolver_vinculo(
    user: UserResponse, polo: Optional[Any], escola: Optional[Any]
) -> Tuple[Optional[str], Optional[str]]:
    """Define polo e escola da turma: a escola determina o polo, e o perfil limita ambos."""
    polo_escopo, escola_escopo = _escopo_usuario(user)
    polo_id = _texto(polo)
    escola_id = escola_escopo or _texto(escola)
    if escola_id:
        escola_row = get_polos_escolas_repository().get_escola(escola_id)
        if not escola_row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
        polo_id = _texto(escola_row.get("polo_id")) or polo_id
    if polo_escopo:
        if polo_id and polo_id != polo_escopo:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a este Polo")
        polo_id = polo_escopo
    return polo_id, escola_id


def _validar_existencia(cur: Any, referencias: List[Tuple[str, Optional[str], str]]) -> None:
    """Confere chaves estrangeiras antes da escrita, para responder 404 em vez de erro do banco."""
    for tabela, valor, mensagem in referencias:
        if not valor:
            continue
        cur.execute(f"SELECT 1 FROM {tabela} WHERE id = %s", (valor,))
        if cur.fetchone() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=mensagem)


def _auditar(
    user: UserResponse,
    acao: str,
    entidade: str,
    entidade_id: str,
    ip: Optional[str],
    antes: Optional[Dict[str, Any]] = None,
    depois: Optional[Dict[str, Any]] = None,
) -> None:
    if not settings.PG_DSN:
        return
    get_polos_escolas_repository().record_audit_log(
        usuario_id=user.id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        dados_antes=jsonable_encoder(antes) if antes else None,
        dados_depois=jsonable_encoder(depois) if depois else None,
        ip=ip,
    )


def _turma_ja_iniciada(turma: Dict[str, Any]) -> bool:
    """RN-04: sem data de início não há como garantir que a turma começa do zero."""
    inicio = turma.get("data_inicio")
    return inicio is None or inicio < date.today()


def _buscar_turma(cur: Any, turma_id: str, bloquear: bool = False) -> Optional[Dict[str, Any]]:
    cur.execute(_TURMA_SELECT + " WHERE t.id = %s" + (" FOR UPDATE OF t" if bloquear else ""), (turma_id,))
    row = cur.fetchone()
    return _enriquecer(dict(row)) if row else None


def _turma_memoria(turma_id: str) -> Optional[Dict[str, Any]]:
    turma = _turmas_db.get(turma_id)
    if turma is None:
        return None
    total = sum(1 for vinculo in _turma_alunos_db if vinculo["turma_id"] == turma_id)
    return _enriquecer({**turma, "total_alunos": total})


def _filtrar_turmas_memoria(
    polo_id: Optional[str],
    escola_id: Optional[str],
    curso_id: Optional[str],
    termo: Optional[str] = None,
    situacao: Optional[str] = None,
    modalidade: Optional[str] = None,
    ano: Optional[int] = None,
) -> List[Dict[str, Any]]:
    turmas = [_turma_memoria(turma_id) for turma_id in _turmas_db]
    return [
        turma
        for turma in turmas
        if turma is not None
        and (not polo_id or turma.get("polo_id") == polo_id)
        and (not escola_id or turma.get("escola_id") == escola_id)
        and (not curso_id or turma.get("curso_id") == curso_id)
        and (not situacao or turma["situacao"] == situacao)
        and (not modalidade or turma.get("modalidade", "presencial") == modalidade)
        and (not ano or (turma.get("data_inicio") and turma["data_inicio"].year == ano))
        and (not termo or termo in f"{turma.get('nome') or ''} {turma.get('codigo') or ''}".lower())
    ]


def _condicoes_turma(
    polo_id: Optional[str],
    escola_id: Optional[str],
    curso_id: Optional[str],
    termo: Optional[str] = None,
    situacao: Optional[str] = None,
    modalidade: Optional[str] = None,
    ano: Optional[int] = None,
) -> Tuple[str, List[Any]]:
    conditions: List[str] = []
    params: List[Any] = []
    for coluna, valor in (
        ("t.polo_id", polo_id), ("t.escola_id", escola_id), ("t.curso_id", curso_id), ("t.modalidade", modalidade),
    ):
        if valor:
            conditions.append(f"{coluna} = %s")
            params.append(valor)
    if situacao:
        conditions.append(f"({regras.SQL_SITUACAO}) = %s")
        params.append(situacao)
    if ano:
        conditions.append("EXTRACT(YEAR FROM t.data_inicio) = %s")
        params.append(ano)
    if termo:
        conditions.append("(lower(t.nome) LIKE %s OR lower(COALESCE(t.codigo, '')) LIKE %s)")
        params.extend([f"%{termo}%", f"%{termo}%"])
    return (" WHERE " + " AND ".join(conditions) if conditions else ""), params


# ---------- Regras de gravação ----------

def _vigencia_do_curso(curso_id: str) -> Dict[str, Any]:
    vig = _carga_repo().vigencia_do_curso(curso_id)
    if vig is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O curso não tem Calendário Acadêmico: vincule um calendário ao curso antes de criar a turma.",
        )
    return vig


def _nome_curso(curso_id: str) -> Optional[str]:
    if not settings.PG_DSN:
        from app.modules.cursos_disciplinas import _cursos_db

        return (_cursos_db.get(curso_id) or {}).get("nome")
    with get_db_cursor() as cur:
        cur.execute("SELECT nome FROM cursos WHERE id = %s", (curso_id,))
        row = cur.fetchone()
        return row["nome"] if row else None


def _usuario_basico(user_id: str) -> Optional[Dict[str, Any]]:
    """{status, perfil, polo_id, escola_id} do usuário (para validar o responsável)."""
    if not settings.PG_DSN:
        from app.modules.auth.repository import get_auth_repository

        u = get_auth_repository().get_user_by_id(user_id)
        if not u:
            return None
        return {"status": u.get("status"), "perfil": u.get("perfil_nome"),
                "polo_id": _texto(u.get("polo_id")), "escola_id": _texto(u.get("escola_id"))}
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT u.status, p.nome AS perfil, u.polo_id::text AS polo_id, u.escola_id::text AS escola_id
              FROM usuarios u LEFT JOIN perfis p ON p.id = u.perfil_id
             WHERE u.id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def _responsavel_valido(usuario: Optional[Dict[str, Any]], polo_id: Optional[str], escola_id: Optional[str]) -> bool:
    if not usuario or usuario.get("status") != "ativo":
        return False
    perfil = perfil_canonico(usuario.get("perfil"))
    if perfil == "polo":
        return bool(polo_id) and usuario.get("polo_id") == polo_id
    if perfil == "escola":
        return bool(escola_id) and usuario.get("escola_id") == escola_id
    return False


def _dados_turma(user: UserResponse, dados: TurmaWriteSchema) -> Dict[str, Any]:
    polo_id, escola_id = _resolver_vinculo(user, dados.polo_id, dados.escola_id)
    if dados.modalidade == "presencial" and not polo_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Turma presencial precisa de um polo.")
    curso_id = str(dados.curso_id)
    vig = _vigencia_do_curso(curso_id)
    responsavel_id = _texto(dados.responsavel_id)
    if responsavel_id and not _responsavel_valido(_usuario_basico(responsavel_id), polo_id, escola_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O responsável deve ser um usuário ativo do polo ou da escola da turma.",
        )
    return {
        "curso_id": curso_id,
        "polo_id": polo_id,
        "escola_id": escola_id,
        "nome": dados.nome,
        "modalidade": dados.modalidade,
        "data_inicio": vig["data_inicio"],
        "data_fim": vig["data_fim"],
        "turno": dados.turno,
        "horario_inicio": dados.horario_inicio,
        "horario_fim": dados.horario_fim,
        "vagas": dados.vagas,
        "local_aulas": dados.local_aulas,
        "responsavel_id": responsavel_id,
    }


def _codigo_memoria(sigla: str, ano: int) -> str:
    return regras.proximo_codigo(sigla, ano, [t.get("codigo") or "" for t in _turmas_db.values()])


def _codigo_postgres(cur: Any, sigla: str, ano: int) -> str:
    """Trava o prefixo na transação (evita dois códigos iguais em criações simultâneas)."""
    prefixo = f"{sigla}-{ano}-"
    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (prefixo,))
    cur.execute("SELECT codigo FROM turmas WHERE codigo LIKE %s", (prefixo + "%",))
    return regras.proximo_codigo(sigla, ano, [r["codigo"] for r in cur.fetchall()])


def _validar_vagas(total_ativos: int, vagas: Optional[int]) -> None:
    if vagas is not None and total_ativos > vagas:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A turma já tem {total_ativos} aluno(s) ativo(s): as vagas não podem ficar abaixo disso.",
        )


# ---------- Listagens ----------

@router.get(
    "",
    response_model=List[TurmaSchema],
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_turmas(
    polo_id: Optional[str] = None,
    curso_id: Optional[str] = None,
    escola_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
):
    polo_escopo, escola_escopo = _escopo_usuario(current_user)
    polo_id = polo_escopo or polo_id
    escola_id = escola_escopo or escola_id

    if not settings.PG_DSN:
        return _filtrar_turmas_memoria(polo_id, escola_id, curso_id)

    where, params = _condicoes_turma(polo_id, escola_id, curso_id)
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT t.id, t.codigo, t.curso_id, t.polo_id, t.escola_id, t.nome, t.modalidade, t.data_inicio, "
            "t.data_fim, t.concluida_em, t.cancelada_em FROM turmas t" + where + " ORDER BY t.nome, t.id",
            tuple(params),
        )
        return [_enriquecer(dict(r)) for r in cur.fetchall()]


@router.get(
    "/paginadas",
    response_model=TurmasPaginaSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_turmas_paginadas(
    q: Optional[str] = Query(None, max_length=255),
    curso_id: Optional[uuid.UUID] = None,
    polo_id: Optional[uuid.UUID] = None,
    escola_id: Optional[uuid.UUID] = None,
    situacao: Optional[regras.Situacao] = None,
    modalidade: Optional[Modalidade] = None,
    ano: Optional[int] = Query(None, ge=2000, le=2100),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
):
    polo_escopo, escola_escopo = _escopo_usuario(current_user)
    polo_filtro = polo_escopo or _texto(polo_id)
    escola_filtro = escola_escopo or _texto(escola_id)
    curso_filtro = _texto(curso_id)
    termo = q.strip().lower() if q and q.strip() else None
    filtros = (polo_filtro, escola_filtro, curso_filtro, termo, situacao, modalidade, ano)

    if not settings.PG_DSN:
        turmas = _filtrar_turmas_memoria(*filtros)
        turmas.sort(key=lambda turma: ((turma.get("nome") or "").lower(), str(turma.get("id"))))
        return {"items": turmas[offset : offset + limit], "total": len(turmas), "limit": limit, "offset": offset}

    where, params = _condicoes_turma(*filtros)
    with get_db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM turmas t" + where, tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            _TURMA_SELECT + where + " ORDER BY t.nome, t.id LIMIT %s OFFSET %s",
            tuple(params + [limit, offset]),
        )
        return {
            "items": [_enriquecer(dict(r)) for r in cur.fetchall()],
            "total": total, "limit": limit, "offset": offset,
        }


@router.get(
    "/sugestao",
    response_model=SugestaoTurmaSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def sugestao_turma(
    curso_id: uuid.UUID,
    modalidade: Modalidade = "presencial",
    polo_id: Optional[uuid.UUID] = None,
    escola_id: Optional[uuid.UUID] = None,
    current_user: UserResponse = Depends(get_current_user),
) -> SugestaoTurmaSchema:
    """Código previsto, nome sugerido e datas do calendário do curso (assistente de criação)."""
    polo, escola = _resolver_vinculo(current_user, polo_id, escola_id)
    vig = _vigencia_do_curso(str(curso_id))
    sigla = regras.sigla_curso(_nome_curso(str(curso_id)))
    ano = (vig["data_inicio"] or date.today()).year
    unidade = None
    if escola:
        unidade = (get_polos_escolas_repository().get_escola(escola) or {}).get("nome")
    elif polo and settings.PG_DSN:
        with get_db_cursor() as cur:
            cur.execute("SELECT nome FROM polos WHERE id = %s", (polo,))
            row = cur.fetchone()
            unidade = row["nome"] if row else None
    if settings.PG_DSN:
        with get_db_cursor() as cur:
            cur.execute("SELECT codigo FROM turmas WHERE codigo LIKE %s", (f"{sigla}-{ano}-%",))
            codigo = regras.proximo_codigo(sigla, ano, [r["codigo"] for r in cur.fetchall()])
    else:
        codigo = _codigo_memoria(sigla, ano)
    return SugestaoTurmaSchema(
        codigo=codigo, nome=regras.nome_sugerido(codigo, unidade, modalidade),
        data_inicio=vig["data_inicio"], data_fim=vig["data_fim"], calendario_nome=vig.get("nome"),
    )


@router.get(
    "/responsaveis-possiveis",
    response_model=List[ResponsavelSchema],
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def responsaveis_possiveis(
    polo_id: Optional[uuid.UUID] = None,
    escola_id: Optional[uuid.UUID] = None,
    current_user: UserResponse = Depends(get_current_user),
) -> List[ResponsavelSchema]:
    """Usuários ativos de perfil polo (do polo) ou escola (da escola) que podem responder pela turma."""
    polo, escola = _resolver_vinculo(current_user, polo_id, escola_id)
    if not polo and not escola:
        return []
    if not settings.PG_DSN:
        from app.modules.auth.repository import get_auth_repository

        saida = []
        for u in getattr(get_auth_repository(), "usuarios", {}).values():
            basico = _usuario_basico(u["id"])
            if _responsavel_valido(basico, polo, escola):
                saida.append(ResponsavelSchema(id=u["id"], nome=f"{u.get('nome') or ''} {u.get('sobrenome') or ''}".strip(),
                                               perfil=perfil_canonico(basico["perfil"])))
        return sorted(saida, key=lambda r: r.nome.lower())
    perfis_polo = list(nomes_equivalentes("polo"))
    perfis_escola = list(nomes_equivalentes("escola"))
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT u.id::text AS id, TRIM(CONCAT_WS(' ', u.nome, u.sobrenome)) AS nome, lower(p.nome) AS perfil
              FROM usuarios u JOIN perfis p ON p.id = u.perfil_id
             WHERE u.status = 'ativo'
               AND ((lower(p.nome) = ANY(%s) AND u.polo_id = %s::uuid)
                 OR (lower(p.nome) = ANY(%s) AND u.escola_id = %s::uuid))
             ORDER BY nome
             LIMIT 200
            """,
            (perfis_polo, polo, perfis_escola, escola),
        )
        return [ResponsavelSchema(id=r["id"], nome=r["nome"], perfil=perfil_canonico(r["perfil"])) for r in cur.fetchall()]


@router.get(
    "/cursos/{curso_id}/detalhes",
    response_model=CursoDetalhesSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def get_detalhes_curso(
    curso_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
) -> CursoDetalhesSchema:
    polo_id, escola_id = _escopo_usuario(current_user)

    course_key = str(curso_id)
    if not settings.PG_DSN:
        from app.modules.cursos_disciplinas import _disciplinas_db

        disciplinas = sorted(
            [
                dict(discipline)
                for discipline in _disciplinas_db.values()
                if str(discipline.get("curso_id")) == course_key
            ],
            key=lambda discipline: (discipline.get("ordem") or 0, str(discipline.get("id") or "")),
        )
        turmas = [
            _turma_memoria(turma_id)
            for turma_id, turma in _turmas_db.items()
            if str(turma.get("curso_id")) == course_key
            and (polo_id is None or str(turma.get("polo_id")) == polo_id)
            and (escola_id is None or str(turma.get("escola_id")) == escola_id)
        ]
        return CursoDetalhesSchema(disciplinas=disciplinas, turmas=turmas)

    turma_conditions = ["curso_id = %s"]
    turma_params: List[Any] = [course_key]
    if polo_id:
        turma_conditions.append("polo_id = %s")
        turma_params.append(polo_id)
    if escola_id:
        turma_conditions.append("escola_id = %s")
        turma_params.append(escola_id)

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, curso_id, semestre, nome, ordem, carga_horaria,
                   qtd_aulas_prevista, tipo, eh_extra_grade
            FROM disciplinas
            WHERE curso_id = %s
            ORDER BY ordem, id
            """,
            (course_key,),
        )
        disciplinas = [dict(row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT id, codigo, curso_id, polo_id, escola_id, nome, modalidade, data_inicio, data_fim,
                   concluida_em, cancelada_em
            FROM turmas t
            WHERE """
            + " AND ".join(turma_conditions),
            tuple(turma_params),
        )
        turmas = [_enriquecer(dict(row)) for row in cur.fetchall()]

    return CursoDetalhesSchema(disciplinas=disciplinas, turmas=turmas)


# ---------- CRUD ----------

@router.post(
    "",
    response_model=TurmaDetalheSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def create_turma(
    dados: TurmaWriteSchema,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    new_id = str(uuid.uuid4())
    valores = _dados_turma(current_user, dados)
    sigla = regras.sigla_curso(_nome_curso(valores["curso_id"]))
    ano = (valores["data_inicio"] or date.today()).year
    if not settings.PG_DSN:
        _turmas_db[new_id] = {"id": new_id, "codigo": _codigo_memoria(sigla, ano), **valores}
        return _turma_memoria(new_id)

    with get_db_cursor() as cur:
        _validar_existencia(cur, [("cursos", valores["curso_id"], "Curso não encontrado"),
                                  ("polos", valores["polo_id"], "Polo não encontrado")])
        codigo = _codigo_postgres(cur, sigla, ano)
        colunas = ("id", "codigo", *_CAMPOS_ESCRITA)
        cur.execute(
            f"INSERT INTO turmas ({', '.join(colunas)}, criado_em, atualizado_em) "
            f"VALUES ({', '.join(['%s'] * len(colunas))}, now(), now())",
            (new_id, codigo, *(valores[c] for c in _CAMPOS_ESCRITA)),
        )
        turma = _buscar_turma(cur, new_id)
    _auditar(current_user, "turma_criada", "turmas", new_id, ip, depois=turma)
    return turma


@router.get(
    "/{turma_id}",
    response_model=TurmaDetalheSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def get_turma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
):
    uid = str(turma_id)
    if not settings.PG_DSN:
        return _exigir_no_escopo(_turma_memoria(uid), current_user)
    with get_db_cursor() as cur:
        return _exigir_no_escopo(_buscar_turma(cur, uid), current_user)


@router.put(
    "/{turma_id}",
    response_model=TurmaDetalheSchema,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def update_turma(
    turma_id: uuid.UUID,
    dados: TurmaWriteSchema,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    uid = str(turma_id)
    if not settings.PG_DSN:
        antes = _exigir_no_escopo(_turma_memoria(uid), current_user)
        regras.exigir_turma_editavel(antes)
        valores = _dados_turma(current_user, dados)
        _validar_vagas(antes["total_alunos"], valores["vagas"])
        _turmas_db[uid].update(valores)
        return _turma_memoria(uid)

    with get_db_cursor() as cur:
        antes = _exigir_no_escopo(_buscar_turma(cur, uid, bloquear=True), current_user)
        regras.exigir_turma_editavel(antes)
        valores = _dados_turma(current_user, dados)
        _validar_existencia(cur, [("cursos", valores["curso_id"], "Curso não encontrado"),
                                  ("polos", valores["polo_id"], "Polo não encontrado")])
        _validar_vagas(int(antes.get("total_alunos") or 0), valores["vagas"])
        if valores["curso_id"] != antes.get("curso_id"):
            cur.execute("SELECT EXISTS (SELECT 1 FROM aulas_previstas WHERE turma_id = %s) AS tem", (uid,))
            if cur.fetchone()["tem"]:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail="A turma já tem cronograma gerado: o curso não pode ser trocado.",
                )
        cur.execute(
            f"UPDATE turmas SET {', '.join(f'{c} = %s' for c in _CAMPOS_ESCRITA)}, atualizado_em = now() "
            "WHERE id = %s",
            (*(valores[c] for c in _CAMPOS_ESCRITA), uid),
        )
        depois = _buscar_turma(cur, uid)
    _auditar(current_user, "turma_atualizada", "turmas", uid, ip, antes=antes, depois=depois)
    return depois


@router.delete(
    "/{turma_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def delete_turma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
) -> Response:
    uid = str(turma_id)
    mensagem_conflito = (
        "Não é possível excluir uma turma com alunos, notas ou professores vinculados. Cancele a turma."
    )
    if not settings.PG_DSN:
        turma = _exigir_no_escopo(_turma_memoria(uid), current_user)
        if turma["total_alunos"]:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=mensagem_conflito)
        del _turmas_db[uid]
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    with get_db_cursor() as cur:
        antes = _exigir_no_escopo(_buscar_turma(cur, uid, bloquear=True), current_user)
        cur.execute(
            """
            SELECT
                EXISTS (SELECT 1 FROM turma_alunos WHERE turma_id = %s)
                OR EXISTS (SELECT 1 FROM notas WHERE turma_id = %s)
                OR EXISTS (SELECT 1 FROM professor_disciplinas WHERE turma_id = %s)
                AS em_uso
            """,
            (uid, uid, uid),
        )
        if cur.fetchone()["em_uso"]:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=mensagem_conflito)
        cur.execute("DELETE FROM turmas WHERE id = %s", (uid,))
    _auditar(current_user, "turma_excluida", "turmas", uid, ip, antes=antes)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Ciclo de vida ----------

@router.post(
    "/{turma_id}/cancelar",
    response_model=TurmaDetalheSchema,
    dependencies=[Depends(require_role(["admin", "polo"]))],
)
async def cancelar_turma(
    turma_id: uuid.UUID,
    dados: CancelarTurmaRequest,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    """Cancela a turma (fica só leitura). Turma concluída não pode ser cancelada."""
    uid = str(turma_id)
    motivo = dados.motivo.strip()
    agora = datetime.now(timezone.utc)
    if not settings.PG_DSN:
        turma = _exigir_no_escopo(_turma_memoria(uid), current_user)
        regras.exigir_turma_editavel(turma)
        _turmas_db[uid].update(cancelada_em=agora, cancelada_por=current_user.id, motivo_cancelamento=motivo)
        return _turma_memoria(uid)
    with get_db_cursor() as cur:
        turma = _exigir_no_escopo(_buscar_turma(cur, uid, bloquear=True), current_user)
        regras.exigir_turma_editavel(turma)
        cur.execute(
            "UPDATE turmas SET cancelada_em = now(), cancelada_por = %s, motivo_cancelamento = %s, "
            "atualizado_em = now() WHERE id = %s",
            (str(current_user.id), motivo, uid),
        )
        depois = _buscar_turma(cur, uid)
    _auditar(current_user, "turma_cancelada", "turmas", uid, ip,
             antes={"situacao": turma["situacao"]}, depois={"situacao": "cancelada", "motivo": motivo})
    return depois


@router.post(
    "/{turma_id}/reabrir",
    response_model=TurmaDetalheSchema,
    dependencies=[Depends(require_role(["admin"]))],
)
async def reabrir_turma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    """Desfaz a conclusão ou o cancelamento (só admin)."""
    uid = str(turma_id)
    limpar = {"concluida_em": None, "concluida_por": None, "cancelada_em": None,
              "cancelada_por": None, "motivo_cancelamento": None}
    if not settings.PG_DSN:
        turma = _exigir_no_escopo(_turma_memoria(uid), current_user)
        if turma["situacao"] not in ("concluida", "cancelada"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Só turma concluída ou cancelada pode ser reaberta.")
        _turmas_db[uid].update(limpar)
        return _turma_memoria(uid)
    with get_db_cursor() as cur:
        turma = _exigir_no_escopo(_buscar_turma(cur, uid, bloquear=True), current_user)
        if turma["situacao"] not in ("concluida", "cancelada"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Só turma concluída ou cancelada pode ser reaberta.")
        cur.execute(
            f"UPDATE turmas SET {', '.join(f'{c} = NULL' for c in limpar)}, atualizado_em = now() WHERE id = %s",
            (uid,),
        )
        depois = _buscar_turma(cur, uid)
    _auditar(current_user, "turma_reaberta", "turmas", uid, ip,
             antes={"situacao": turma["situacao"], "motivo": turma.get("motivo_cancelamento")},
             depois={"situacao": depois["situacao"]})
    return depois


# ---------- Alunos ----------

@router.get(
    "/{turma_id}/alunos",
    response_model=AlunosTurmaPaginaSchema,
    dependencies=[Depends(require_role([*_PERFIS_TURMA, "professor"]))],
)
async def list_alunos_turma(
    turma_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
):
    uid = str(turma_id)
    if usuario_eh_professor(current_user) and not any(
        str(vinculo.get("turma_id")) == uid
        for vinculo in listar_vinculos_academicos_docente(current_user)
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Professor sem vínculo ativo com esta turma",
        )
    if not settings.PG_DSN:
        _exigir_no_escopo(_turma_memoria(uid), current_user)
        vinculos = [
            {"aluno_id": vinculo["aluno_id"], "status": "ativo"}
            for vinculo in _turma_alunos_db
            if vinculo["turma_id"] == uid
        ]
        return {"items": vinculos[offset : offset + limit], "total": len(vinculos), "limit": limit, "offset": offset}

    with get_db_cursor() as cur:
        _exigir_no_escopo(_buscar_turma(cur, uid), current_user)
        cur.execute("SELECT COUNT(*) AS total FROM turma_alunos WHERE turma_id = %s", (uid,))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT a.id AS aluno_id, {_ALUNO_NOME_SQL} AS nome, u.email, a.numero_matricula,
                   ta.status, ta.data_matricula
            FROM turma_alunos ta
            JOIN alunos a ON a.id = ta.aluno_id
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE ta.turma_id = %s
            ORDER BY nome, a.id
            LIMIT %s OFFSET %s
            """,
            (uid, limit, offset),
        )
        return {"items": [dict(r) for r in cur.fetchall()], "total": total, "limit": limit, "offset": offset}


@router.get(
    "/{turma_id}/alunos-disponiveis",
    response_model=List[AlunoTurmaSchema],
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def list_alunos_disponiveis(
    turma_id: uuid.UUID,
    q: Optional[str] = Query(None, max_length=255),
    limit: int = Query(20, ge=1, le=50),
    current_user: UserResponse = Depends(get_current_user),
):
    uid = str(turma_id)
    if not settings.PG_DSN:
        _exigir_no_escopo(_turma_memoria(uid), current_user)
        return []

    termo = q.strip().lower() if q and q.strip() else None
    with get_db_cursor() as cur:
        turma = _exigir_no_escopo(_buscar_turma(cur, uid), current_user)
        conditions = [
            "a.status = 'ativo'",
            "NOT EXISTS (SELECT 1 FROM turma_alunos ta WHERE ta.turma_id = %s AND ta.aluno_id = a.id)",
        ]
        params: List[Any] = [uid]
        if turma.get("escola_id"):
            conditions.append("a.escola_id = %s")
            params.append(str(turma["escola_id"]))
        elif turma.get("polo_id"):
            conditions.append("a.polo_id = %s")
            params.append(str(turma["polo_id"]))
        if _turma_ja_iniciada(turma):
            conditions.append("a.revalidado_em IS NULL")
        if termo:
            conditions.append(
                f"(lower({_ALUNO_NOME_SQL}) LIKE %s OR lower(coalesce(a.numero_matricula, '')) LIKE %s)"
            )
            params.extend([f"%{termo}%", f"%{termo}%"])
        cur.execute(
            f"""
            SELECT a.id AS aluno_id, {_ALUNO_NOME_SQL} AS nome, u.email, a.numero_matricula, a.status
            FROM alunos a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE {" AND ".join(conditions)}
            ORDER BY nome, a.id
            LIMIT %s
            """,
            tuple(params + [limit]),
        )
        return [dict(r) for r in cur.fetchall()]


def _mensagem_lotada(vagas: int) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail=f"Turma lotada ({vagas} vagas).")


@router.post(
    "/{turma_id}/matricular-aluno",
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def matricular_aluno_turma(
    turma_id: uuid.UUID,
    aluno_id: str,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
):
    uid = str(turma_id)
    mensagem = {"message": "Aluno matriculado na turma com sucesso"}
    if not settings.PG_DSN:
        turma = _exigir_no_escopo(_turma_memoria(uid), current_user)
        regras.exigir_turma_editavel(turma)
        vinculo = {"turma_id": uid, "aluno_id": aluno_id}
        if vinculo not in _turma_alunos_db:
            if turma.get("vagas") and turma["total_alunos"] >= turma["vagas"]:
                raise _mensagem_lotada(turma["vagas"])
            _turma_alunos_db.append(vinculo)
        return mensagem

    with get_db_cursor() as cur:
        turma = _exigir_no_escopo(_buscar_turma(cur, uid, bloquear=True), current_user)
        regras.exigir_turma_editavel(turma)
        cur.execute(
            "SELECT id, polo_id, escola_id, revalidado_em FROM alunos WHERE id::text = %s",
            (aluno_id,),
        )
        aluno = cur.fetchone()
        if aluno is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")
        if aluno.get("revalidado_em") and _turma_ja_iniciada(turma):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Aluno revalidado só pode entrar em turmas que comecem do zero.",
            )
        campo = "escola_id" if turma.get("escola_id") else "polo_id"
        if turma.get(campo) and str(aluno[campo]) != str(turma[campo]):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Aluno não pertence ao polo/escola da turma.")
        cur.execute(
            "SELECT 1 FROM turma_alunos WHERE turma_id = %s AND aluno_id = %s", (uid, str(aluno["id"]))
        )
        ja_matriculado = cur.fetchone() is not None
        if not ja_matriculado and turma.get("vagas") and int(turma.get("total_alunos") or 0) >= turma["vagas"]:
            raise _mensagem_lotada(turma["vagas"])
        cur.execute(
            """
            INSERT INTO turma_alunos (id, turma_id, aluno_id, data_matricula, status, criado_em, atualizado_em)
            VALUES (%s, %s, %s, now(), 'ativo', now(), now())
            ON CONFLICT DO NOTHING
            """,
            (str(uuid.uuid4()), uid, str(aluno["id"])),
        )
    _auditar(current_user, "turma_aluno_matriculado", "turmas", uid, ip, depois={"aluno_id": aluno_id})
    return mensagem


@router.delete(
    "/{turma_id}/alunos/{aluno_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_PERFIS_TURMA))],
)
async def remover_aluno_turma(
    turma_id: uuid.UUID,
    aluno_id: str,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
) -> Response:
    uid = str(turma_id)
    if not settings.PG_DSN:
        regras.exigir_turma_editavel(_exigir_no_escopo(_turma_memoria(uid), current_user))
        vinculo = {"turma_id": uid, "aluno_id": aluno_id}
        if vinculo not in _turma_alunos_db:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não matriculado nesta turma")
        _turma_alunos_db.remove(vinculo)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    with get_db_cursor() as cur:
        regras.exigir_turma_editavel(_exigir_no_escopo(_buscar_turma(cur, uid), current_user))
        cur.execute(
            "DELETE FROM turma_alunos WHERE turma_id = %s AND aluno_id::text = %s RETURNING id",
            (uid, aluno_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não matriculado nesta turma")
    _auditar(current_user, "turma_aluno_removido", "turmas", uid, ip, antes={"aluno_id": aluno_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
