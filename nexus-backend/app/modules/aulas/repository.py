"""Repositório do módulo `aulas` (PostgreSQL + implementação em memória para testes)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.database import get_db_cursor

# Filtros aceitos por `listar`:
#   professor_usuario_id, professor_id, disciplina_id, polo_id, vinculo_id,
#   data_inicio, data_fim, q
Filtros = Dict[str, Any]

_SELECT_AULA = """
    SELECT aula.id::text AS id,
           aula.professor_disciplina_id::text AS professor_disciplina_id,
           disciplina.id::text AS disciplina_id,
           disciplina.nome AS disciplina_nome,
           curso.nome AS curso_nome,
           turma.id::text AS turma_id,
           turma.nome AS turma_nome,
           polo.id::text AS polo_id,
           polo.nome AS polo_nome,
           escola.nome AS escola_nome,
           professor.id::text AS professor_id,
           professor.usuario_id::text AS professor_usuario_id,
           TRIM(CONCAT_WS(' ', usuario.nome, usuario.sobrenome)) AS professor_nome,
           aula.data_aula, aula.numero_aula, aula.conteudo_ministrado,
           aula.observacoes, aula.visivel_aluno, aula.criado_em, aula.atualizado_em,
           (SELECT COUNT(*) FROM professor_materiais material
             WHERE material.aula_id = aula.id) AS total_materiais,
           COALESCE(chamada.presentes, 0) AS presentes,
           COALESCE(chamada.total, 0) AS total_chamada
"""

_FROM_AULA = """
    FROM aulas_ministradas aula
    JOIN professor_disciplinas vinculo ON vinculo.id = aula.professor_disciplina_id
    JOIN professores professor ON professor.id = vinculo.professor_id
    LEFT JOIN usuarios usuario ON usuario.id = professor.usuario_id
    JOIN disciplinas disciplina ON disciplina.id = vinculo.disciplina_id
    LEFT JOIN cursos curso ON curso.id = disciplina.curso_id
    LEFT JOIN turmas turma ON turma.id = vinculo.turma_id
    LEFT JOIN escolas escola ON escola.id = turma.escola_id
    LEFT JOIN polos polo ON polo.id = COALESCE(turma.polo_id, escola.polo_id)
"""

_CHAMADA_LATERAL = """
    LEFT JOIN LATERAL (
        SELECT COUNT(*) FILTER (WHERE presenca.presente) AS presentes,
               COUNT(*) AS total
        FROM presencas presenca
        WHERE presenca.professor_disciplina_id = aula.professor_disciplina_id
          AND presenca.data_aula = aula.data_aula
          AND presenca.numero_aula = aula.numero_aula
    ) chamada ON true
"""


class AulasRepositoryInterface(Protocol):
    def get_vinculo(self, vinculo_id: str) -> Optional[Dict[str, Any]]: ...

    def listar(self, filtros: Filtros, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]: ...

    def obter(self, aula_id: str) -> Optional[Dict[str, Any]]: ...

    def chave_em_uso(
        self, vinculo_id: str, data_aula: date, numero_aula: int, ignorar_id: Optional[str] = None
    ) -> bool: ...

    def criar(self, data: Dict[str, Any]) -> str: ...

    def atualizar(self, aula_id: str, data: Dict[str, Any]) -> None: ...

    def excluir(self, aula_id: str) -> List[str]:
        """Remove a aula, sua chamada e seus materiais; devolve as chaves de arquivo a limpar."""
        ...

    def listar_materiais(self, aula_id: str) -> List[Dict[str, Any]]: ...

    def excluir_material(self, aula_id: str, material_id: str) -> Tuple[bool, Optional[str]]: ...

    def listar_chamada(self, aula: Dict[str, Any]) -> List[Dict[str, Any]]: ...

    def opcoes_filtro(self, disciplina_id: Optional[str]) -> Dict[str, List[Dict[str, str]]]: ...

    def resumo_por_disciplina(self) -> List[Dict[str, Any]]: ...

    def atividade(self, data_inicio: date, data_corte_polos: date, top: int) -> Dict[str, Any]: ...


def _like(texto: str) -> str:
    return f"%{texto.strip()}%"


class PostgresAulasRepository:
    def get_vinculo(self, vinculo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT vinculo.id::text AS id,
                       vinculo.professor_id::text AS professor_id,
                       professor.usuario_id::text AS professor_usuario_id,
                       vinculo.disciplina_id::text AS disciplina_id,
                       vinculo.turma_id::text AS turma_id,
                       vinculo.ativo
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                WHERE vinculo.id = %s
                """,
                (str(vinculo_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def _where(filtros: Filtros) -> Tuple[str, List[Any]]:
        conds: List[str] = []
        params: List[Any] = []
        colunas = {
            "professor_usuario_id": "professor.usuario_id = %s",
            "professor_id": "professor.id = %s",
            "disciplina_id": "disciplina.id = %s",
            "polo_id": "polo.id = %s",
            "vinculo_id": "vinculo.id = %s",
            "data_inicio": "aula.data_aula >= %s",
            "data_fim": "aula.data_aula <= %s",
        }
        for chave, condicao in colunas.items():
            valor = filtros.get(chave)
            if valor:
                conds.append(condicao)
                params.append(str(valor) if not isinstance(valor, date) else valor)
        termo = (filtros.get("q") or "").strip()
        if termo:
            conds.append(
                """(
                    aula.conteudo_ministrado ILIKE %s OR aula.observacoes ILIKE %s
                    OR usuario.nome ILIKE %s OR usuario.sobrenome ILIKE %s
                    OR disciplina.nome ILIKE %s OR polo.nome ILIKE %s OR turma.nome ILIKE %s
                    OR EXISTS (
                        SELECT 1 FROM professor_materiais material
                        WHERE material.aula_id = aula.id
                          AND (material.descricao ILIKE %s OR material.arquivo_nome ILIKE %s)
                    )
                )"""
            )
            params.extend([_like(termo)] * 9)
        return ("WHERE " + " AND ".join(conds)) if conds else "", params

    def listar(self, filtros: Filtros, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        where, params = self._where(filtros)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total {_FROM_AULA} {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"""{_SELECT_AULA} {_FROM_AULA} {_CHAMADA_LATERAL} {where}
                ORDER BY aula.data_aula DESC, aula.numero_aula DESC, polo.nome NULLS LAST, aula.id
                LIMIT %s OFFSET %s""",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def obter(self, aula_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"{_SELECT_AULA} {_FROM_AULA} {_CHAMADA_LATERAL} WHERE aula.id = %s",
                (str(aula_id),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def chave_em_uso(
        self, vinculo_id: str, data_aula: date, numero_aula: int, ignorar_id: Optional[str] = None
    ) -> bool:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM aulas_ministradas
                    WHERE professor_disciplina_id = %s AND data_aula = %s AND numero_aula = %s
                      AND (%s::uuid IS NULL OR id <> %s::uuid)
                ) AS existe
                """,
                (str(vinculo_id), data_aula, numero_aula, ignorar_id, ignorar_id),
            )
            return bool(cur.fetchone()["existe"])

    def criar(self, data: Dict[str, Any]) -> str:
        aula_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO aulas_ministradas (
                    id, professor_disciplina_id, data_aula, numero_aula, conteudo_ministrado,
                    observacoes, visivel_aluno, criado_por, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    aula_id,
                    str(data["professor_disciplina_id"]),
                    data["data_aula"],
                    data["numero_aula"],
                    data.get("conteudo_ministrado"),
                    data.get("observacoes"),
                    data.get("visivel_aluno", True),
                    data.get("criado_por"),
                ),
            )
        return aula_id

    def atualizar(self, aula_id: str, data: Dict[str, Any]) -> None:
        permitidos = ("data_aula", "numero_aula", "conteudo_ministrado", "observacoes", "visivel_aluno")
        campos = [k for k in permitidos if k in data]
        if not campos:
            return
        with get_db_cursor() as cur:
            # A chamada acompanha a aula se a data ou o número mudarem.
            if "data_aula" in data or "numero_aula" in data:
                cur.execute(
                    """
                    UPDATE presencas presenca
                       SET data_aula = %s, numero_aula = %s, atualizado_em = now()
                      FROM aulas_ministradas aula
                     WHERE aula.id = %s
                       AND presenca.professor_disciplina_id = aula.professor_disciplina_id
                       AND presenca.data_aula = aula.data_aula
                       AND presenca.numero_aula = aula.numero_aula
                    """,
                    (
                        data.get("data_aula"),
                        data.get("numero_aula"),
                        str(aula_id),
                    ),
                )
                cur.execute(
                    "UPDATE professor_materiais SET data_aula = %s, atualizado_em = now() WHERE aula_id = %s",
                    (data.get("data_aula"), str(aula_id)),
                )
            sets = ", ".join(f"{campo} = %s" for campo in campos)
            cur.execute(
                f"UPDATE aulas_ministradas SET {sets}, atualizado_em = now() WHERE id = %s",
                tuple([data[c] for c in campos] + [str(aula_id)]),
            )

    def excluir(self, aula_id: str) -> List[str]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                DELETE FROM presencas presenca
                 USING aulas_ministradas aula
                 WHERE aula.id = %s
                   AND presenca.professor_disciplina_id = aula.professor_disciplina_id
                   AND presenca.data_aula = aula.data_aula
                   AND presenca.numero_aula = aula.numero_aula
                """,
                (str(aula_id),),
            )
            cur.execute(
                "DELETE FROM professor_materiais WHERE aula_id = %s RETURNING arquivo_storage_key",
                (str(aula_id),),
            )
            chaves = [r["arquivo_storage_key"] for r in cur.fetchall() if r["arquivo_storage_key"]]
            cur.execute("DELETE FROM aulas_ministradas WHERE id = %s", (str(aula_id),))
            return chaves

    def listar_materiais(self, aula_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, descricao, arquivo_url, arquivo_nome,
                       arquivo_mime_type, arquivo_tamanho_bytes,
                       arquivo_storage_key IS NOT NULL AS tem_arquivo
                FROM professor_materiais
                WHERE aula_id = %s
                ORDER BY criado_em, id
                """,
                (str(aula_id),),
            )
            return [dict(r) for r in cur.fetchall()]

    def excluir_material(self, aula_id: str, material_id: str) -> Tuple[bool, Optional[str]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                DELETE FROM professor_materiais
                WHERE id = %s AND aula_id = %s
                RETURNING arquivo_storage_key
                """,
                (str(material_id), str(aula_id)),
            )
            row = cur.fetchone()
            return (True, row["arquivo_storage_key"]) if row else (False, None)

    def listar_chamada(self, aula: Dict[str, Any]) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT aluno.id::text AS aluno_id,
                       COALESCE(usuario.nome, usuario.email, aluno.numero_matricula, aluno.id::text) AS nome,
                       aluno.numero_matricula,
                       presenca.presente
                FROM turma_alunos matricula
                JOIN alunos aluno ON aluno.id = matricula.aluno_id
                LEFT JOIN usuarios usuario ON usuario.id = aluno.usuario_id
                LEFT JOIN presencas presenca
                    ON presenca.aluno_id = aluno.id
                   AND presenca.professor_disciplina_id = %s
                   AND presenca.data_aula = %s
                   AND presenca.numero_aula = %s
                WHERE matricula.turma_id = %s
                  AND (COALESCE(matricula.status, 'ativo') = 'ativo' OR presenca.id IS NOT NULL)
                ORDER BY nome, aluno.id
                """,
                (
                    str(aula["professor_disciplina_id"]),
                    aula["data_aula"],
                    aula["numero_aula"],
                    str(aula.get("turma_id")),
                ),
            )
            return [dict(r) for r in cur.fetchall()]

    def opcoes_filtro(self, disciplina_id: Optional[str]) -> Dict[str, List[Dict[str, str]]]:
        where = "WHERE disciplina.id = %s" if disciplina_id else ""
        params = (str(disciplina_id),) if disciplina_id else ()
        with get_db_cursor() as cur:
            resultado: Dict[str, List[Dict[str, str]]] = {}
            consultas = {
                "disciplinas": ("disciplina.id::text", "disciplina.nome"),
                "polos": ("polo.id::text", "polo.nome"),
                "professores": (
                    "professor.id::text",
                    "TRIM(CONCAT_WS(' ', usuario.nome, usuario.sobrenome))",
                ),
            }
            for chave, (coluna_id, coluna_nome) in consultas.items():
                cur.execute(
                    f"""
                    SELECT DISTINCT {coluna_id} AS id, {coluna_nome} AS nome
                    {_FROM_AULA} {where}
                    ORDER BY nome
                    """,
                    params,
                )
                resultado[chave] = [
                    {"id": r["id"], "nome": r["nome"] or "Sem nome"} for r in cur.fetchall() if r["id"]
                ]
            return resultado

    def resumo_por_disciplina(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT vinculo.disciplina_id::text AS disciplina_id,
                       COUNT(*) AS total_aulas,
                       MAX(aula.data_aula) AS ultima_aula
                FROM aulas_ministradas aula
                JOIN professor_disciplinas vinculo ON vinculo.id = aula.professor_disciplina_id
                GROUP BY vinculo.disciplina_id
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def atividade(self, data_inicio: date, data_corte_polos: date, top: int) -> Dict[str, Any]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*) AS aulas,
                       COUNT(DISTINCT disciplina.id) AS disciplinas,
                       COUNT(DISTINCT polo.id) AS polos
                {_FROM_AULA}
                WHERE aula.data_aula >= %s
                """,
                (data_inicio,),
            )
            totais = dict(cur.fetchone())
            cur.execute(
                f"""
                SELECT disciplina.id::text AS id, disciplina.nome, COUNT(*) AS total_aulas
                {_FROM_AULA}
                WHERE aula.data_aula >= %s
                GROUP BY disciplina.id, disciplina.nome
                ORDER BY total_aulas DESC, disciplina.nome
                LIMIT %s
                """,
                (data_inicio, top),
            )
            top_disciplinas = [dict(r) for r in cur.fetchall()]
            # Polos ativos que têm turma com professor vinculado, mas sem aula recente.
            cur.execute(
                """
                SELECT polo.id::text AS id, polo.nome, MAX(aula.data_aula) AS ultima_aula
                FROM professor_disciplinas vinculo
                JOIN turmas turma ON turma.id = vinculo.turma_id
                LEFT JOIN escolas escola ON escola.id = turma.escola_id
                JOIN polos polo ON polo.id = COALESCE(turma.polo_id, escola.polo_id)
                LEFT JOIN aulas_ministradas aula ON aula.professor_disciplina_id = vinculo.id
                WHERE vinculo.ativo = true
                  AND COALESCE(polo.status, 'ativo') = 'ativo'
                GROUP BY polo.id, polo.nome
                HAVING MAX(aula.data_aula) IS NULL OR MAX(aula.data_aula) < %s
                ORDER BY MAX(aula.data_aula) NULLS FIRST, polo.nome
                LIMIT 20
                """,
                (data_corte_polos,),
            )
            polos = [dict(r) for r in cur.fetchall()]
        return {
            "aulas_registradas": int(totais["aulas"] or 0),
            "disciplinas_com_aula": int(totais["disciplinas"] or 0),
            "polos_com_aula": int(totais["polos"] or 0),
            "top_disciplinas": top_disciplinas,
            "polos_sem_registro": polos,
        }


class InMemoryAulasRepository:
    """Implementação em memória para testes. Os vínculos já vêm "achatados" com nomes."""

    def __init__(self) -> None:
        # vinculo: id, professor_id, professor_usuario_id, professor_nome, disciplina_id,
        # disciplina_nome, curso_nome, turma_id, turma_nome, polo_id, polo_nome,
        # escola_nome, ativo
        self.vinculos: Dict[str, Dict[str, Any]] = {}
        self.aulas: Dict[str, Dict[str, Any]] = {}
        self.materiais: Dict[str, Dict[str, Any]] = {}
        self.presencas: List[Dict[str, Any]] = []
        self.alunos_turma: Dict[str, List[Dict[str, Any]]] = {}
        self.polos_ativos: Dict[str, str] = {}

    def get_vinculo(self, vinculo_id: str) -> Optional[Dict[str, Any]]:
        vinculo = self.vinculos.get(str(vinculo_id))
        return dict(vinculo) if vinculo else None

    def _chamada(self, aula: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            p
            for p in self.presencas
            if p["professor_disciplina_id"] == aula["professor_disciplina_id"]
            and p["data_aula"] == aula["data_aula"]
            and p["numero_aula"] == aula["numero_aula"]
        ]

    def _montar(self, aula: Dict[str, Any]) -> Dict[str, Any]:
        vinculo = self.vinculos[aula["professor_disciplina_id"]]
        chamada = self._chamada(aula)
        return {
            **{k: vinculo.get(k) for k in (
                "disciplina_id", "disciplina_nome", "curso_nome", "turma_id", "turma_nome",
                "polo_id", "polo_nome", "escola_nome", "professor_id", "professor_usuario_id",
                "professor_nome",
            )},
            **aula,
            "total_materiais": sum(1 for m in self.materiais.values() if m.get("aula_id") == aula["id"]),
            "presentes": sum(1 for p in chamada if p["presente"]),
            "total_chamada": len(chamada),
        }

    def listar(self, filtros: Filtros, limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        itens = [self._montar(a) for a in self.aulas.values()]
        for chave in ("professor_usuario_id", "professor_id", "disciplina_id", "polo_id"):
            if filtros.get(chave):
                itens = [i for i in itens if str(i.get(chave)) == str(filtros[chave])]
        if filtros.get("vinculo_id"):
            itens = [i for i in itens if i["professor_disciplina_id"] == str(filtros["vinculo_id"])]
        if filtros.get("data_inicio"):
            itens = [i for i in itens if i["data_aula"] >= filtros["data_inicio"]]
        if filtros.get("data_fim"):
            itens = [i for i in itens if i["data_aula"] <= filtros["data_fim"]]
        termo = (filtros.get("q") or "").strip().lower()
        if termo:
            def bate(item: Dict[str, Any]) -> bool:
                textos = [
                    item.get(k) for k in (
                        "conteudo_ministrado", "observacoes", "professor_nome",
                        "disciplina_nome", "polo_nome", "turma_nome",
                    )
                ] + [
                    texto
                    for m in self.materiais.values() if m.get("aula_id") == item["id"]
                    for texto in (m.get("descricao"), m.get("arquivo_nome"))
                ]
                return any(termo in str(t or "").lower() for t in textos)

            itens = [i for i in itens if bate(i)]
        itens.sort(key=lambda i: (i["data_aula"], i["numero_aula"]), reverse=True)
        return len(itens), itens[offset : offset + limit]

    def obter(self, aula_id: str) -> Optional[Dict[str, Any]]:
        aula = self.aulas.get(str(aula_id))
        return self._montar(aula) if aula else None

    def chave_em_uso(
        self, vinculo_id: str, data_aula: date, numero_aula: int, ignorar_id: Optional[str] = None
    ) -> bool:
        return any(
            a["professor_disciplina_id"] == str(vinculo_id)
            and a["data_aula"] == data_aula
            and a["numero_aula"] == numero_aula
            and a["id"] != ignorar_id
            for a in self.aulas.values()
        )

    def criar(self, data: Dict[str, Any]) -> str:
        aula_id = str(uuid.uuid4())
        agora = datetime.now(timezone.utc)
        self.aulas[aula_id] = {
            "id": aula_id,
            "professor_disciplina_id": str(data["professor_disciplina_id"]),
            "data_aula": data["data_aula"],
            "numero_aula": data["numero_aula"],
            "conteudo_ministrado": data.get("conteudo_ministrado"),
            "observacoes": data.get("observacoes"),
            "visivel_aluno": data.get("visivel_aluno", True),
            "criado_em": agora,
            "atualizado_em": agora,
        }
        return aula_id

    def atualizar(self, aula_id: str, data: Dict[str, Any]) -> None:
        aula = self.aulas[str(aula_id)]
        if "data_aula" in data or "numero_aula" in data:
            for presenca in self._chamada(aula):
                presenca["data_aula"] = data["data_aula"]
                presenca["numero_aula"] = data["numero_aula"]
        aula.update(data)
        aula["atualizado_em"] = datetime.now(timezone.utc)

    def excluir(self, aula_id: str) -> List[str]:
        aula = self.aulas.pop(str(aula_id))
        chamada = self._chamada(aula)
        self.presencas = [p for p in self.presencas if p not in chamada]
        chaves = []
        for material_id in [k for k, m in self.materiais.items() if m.get("aula_id") == aula["id"]]:
            chave = self.materiais.pop(material_id).get("arquivo_storage_key")
            if chave:
                chaves.append(chave)
        return chaves

    def listar_materiais(self, aula_id: str) -> List[Dict[str, Any]]:
        return [
            {**m, "tem_arquivo": bool(m.get("arquivo_storage_key"))}
            for m in self.materiais.values()
            if m.get("aula_id") == str(aula_id)
        ]

    def excluir_material(self, aula_id: str, material_id: str) -> Tuple[bool, Optional[str]]:
        material = self.materiais.get(str(material_id))
        if not material or material.get("aula_id") != str(aula_id):
            return False, None
        self.materiais.pop(str(material_id))
        return True, material.get("arquivo_storage_key")

    def listar_chamada(self, aula: Dict[str, Any]) -> List[Dict[str, Any]]:
        registros = {p["aluno_id"]: p["presente"] for p in self._chamada(aula)}
        return [
            {**aluno, "presente": registros.get(aluno["aluno_id"])}
            for aluno in self.alunos_turma.get(str(aula.get("turma_id")), [])
        ]

    def opcoes_filtro(self, disciplina_id: Optional[str]) -> Dict[str, List[Dict[str, str]]]:
        _, itens = self.listar({"disciplina_id": disciplina_id}, 10_000, 0)

        def distintos(id_key: str, nome_key: str) -> List[Dict[str, str]]:
            vistos = {i[id_key]: i.get(nome_key) or "Sem nome" for i in itens if i.get(id_key)}
            return sorted(({"id": k, "nome": v} for k, v in vistos.items()), key=lambda o: o["nome"])

        return {
            "disciplinas": distintos("disciplina_id", "disciplina_nome"),
            "polos": distintos("polo_id", "polo_nome"),
            "professores": distintos("professor_id", "professor_nome"),
        }

    def resumo_por_disciplina(self) -> List[Dict[str, Any]]:
        resumo: Dict[str, Dict[str, Any]] = {}
        for aula in self.aulas.values():
            disciplina_id = self.vinculos[aula["professor_disciplina_id"]]["disciplina_id"]
            item = resumo.setdefault(disciplina_id, {"disciplina_id": disciplina_id, "total_aulas": 0, "ultima_aula": None})
            item["total_aulas"] += 1
            if not item["ultima_aula"] or aula["data_aula"] > item["ultima_aula"]:
                item["ultima_aula"] = aula["data_aula"]
        return list(resumo.values())

    def atividade(self, data_inicio: date, data_corte_polos: date, top: int) -> Dict[str, Any]:
        _, recentes = self.listar({"data_inicio": data_inicio}, 10_000, 0)
        contagem: Dict[str, Dict[str, Any]] = {}
        for item in recentes:
            registro = contagem.setdefault(
                item["disciplina_id"], {"id": item["disciplina_id"], "nome": item["disciplina_nome"], "total_aulas": 0}
            )
            registro["total_aulas"] += 1
        ultima_por_polo: Dict[str, Optional[date]] = {}
        for vinculo in self.vinculos.values():
            polo_id = vinculo.get("polo_id")
            if not vinculo.get("ativo", True) or polo_id not in self.polos_ativos:
                continue
            datas = [a["data_aula"] for a in self.aulas.values() if a["professor_disciplina_id"] == vinculo["id"]]
            atual = ultima_por_polo.get(polo_id)
            maior = max(datas) if datas else None
            ultima_por_polo[polo_id] = max(filter(None, [atual, maior]), default=None)
        polos = [
            {"id": polo_id, "nome": self.polos_ativos[polo_id], "ultima_aula": ultima}
            for polo_id, ultima in ultima_por_polo.items()
            if ultima is None or ultima < data_corte_polos
        ]
        return {
            "aulas_registradas": len(recentes),
            "disciplinas_com_aula": len({i["disciplina_id"] for i in recentes}),
            "polos_com_aula": len({i["polo_id"] for i in recentes if i.get("polo_id")}),
            "top_disciplinas": sorted(contagem.values(), key=lambda d: (-d["total_aulas"], d["nome"]))[:top],
            "polos_sem_registro": sorted(polos, key=lambda p: (p["ultima_aula"] is not None, p["ultima_aula"] or date.min)),
        }


_repo_instance: Optional[AulasRepositoryInterface] = None


def get_aulas_repository() -> AulasRepositoryInterface:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = PostgresAulasRepository()
    return _repo_instance


def set_aulas_repository(repo: Optional[AulasRepositoryInterface]) -> None:
    global _repo_instance
    _repo_instance = repo


def hoje() -> date:
    return datetime.now(timezone.utc).date()


def dias_atras(dias: int) -> date:
    return hoje() - timedelta(days=dias)
