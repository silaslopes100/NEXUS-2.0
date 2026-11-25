"""Repositório do módulo `carga_horaria` (PostgreSQL + implementação em memória para testes)."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, Sequence

from psycopg2.extras import Json

from app.core.database import get_db_cursor
from app.modules.carga_horaria.cronograma import AulaPlanejada, status_aula_prevista
from app.modules.carga_horaria.schemas import TIPOS_QUE_ABATEM

_CAMPOS_CALENDARIO = (
    "nome", "descricao", "data_inicio", "data_fim", "dias_semana", "meses_recesso",
    "feriados", "datas_excluidas", "datas_extras", "regras", "ativo",
)


def _limpar(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    out: Dict[str, Any] = {}
    for k, v in dict(row).items():
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, Decimal):
            v = float(v)
        out[k] = v
    return out


class CargaHorariaRepositoryInterface(Protocol):
    # Calendários
    def listar_calendarios(self) -> List[Dict[str, Any]]: ...
    def obter_calendario(self, calendario_id: str) -> Optional[Dict[str, Any]]: ...
    def criar_calendario(self, dados: Dict[str, Any]) -> str: ...
    def atualizar_calendario(self, calendario_id: str, dados: Dict[str, Any]) -> None: ...
    def contar_cursos_do_calendario(self, calendario_id: str) -> int: ...
    def excluir_calendario(self, calendario_id: str) -> None: ...

    # Turma
    def contexto_turma(self, turma_id: str) -> Optional[Dict[str, Any]]:
        """{id, nome, curso_id, polo_id, escola_id, data_inicio, data_fim, concluida_em, calendario}"""
        ...
    def disciplinas_do_curso(self, curso_id: str) -> List[Dict[str, Any]]: ...
    def listar_aulas_previstas(self, turma_id: str) -> List[Dict[str, Any]]: ...
    def obter_aula_prevista(self, aula_prevista_id: str) -> Optional[Dict[str, Any]]: ...
    def substituir_pendentes(self, turma_id: str, novas: Sequence[AulaPlanejada]) -> None: ...
    def listar_atas_turma(self, turma_id: str) -> List[Dict[str, Any]]: ...
    def listar_presencas_turma(self, turma_id: str) -> List[Dict[str, Any]]: ...
    def alunos_turma(self, turma_id: str) -> List[Dict[str, Any]]: ...
    def concluir_turma(self, turma_id: str, usuario_id: str) -> datetime: ...

    # Auditoria
    def auditar(self, usuario_id: Optional[str], acao: str, entidade: str, entidade_id: Optional[str],
                antes: Optional[Dict[str, Any]] = None, depois: Optional[Dict[str, Any]] = None,
                ip: Optional[str] = None) -> None: ...


_SELECT_CALENDARIO = """
    SELECT c.id::text AS id, c.nome, c.descricao, c.data_inicio, c.data_fim, c.dias_semana,
           c.meses_recesso, c.feriados, c.datas_excluidas, c.datas_extras, c.regras, c.ativo,
           c.criado_em, c.atualizado_em,
           (SELECT COUNT(*) FROM cursos cu WHERE cu.calendario_id = c.id) AS total_cursos
      FROM calendarios_academicos c
"""

# Ata que cumpre cada aula prevista (prevista ou reposição): define o status.
_SELECT_AULA_PREVISTA = """
    SELECT ap.id::text AS id, ap.turma_id::text AS turma_id, ap.disciplina_id::text AS disciplina_id,
           d.nome AS disciplina_nome, ap.numero, ap.data_prevista, ap.horas_previstas,
           ata.id::text AS ata_id, ata.tipo AS ata_tipo, ata.data_aula AS ata_data
      FROM aulas_previstas ap
      JOIN disciplinas d ON d.id = ap.disciplina_id
      LEFT JOIN aulas_ministradas ata
        ON ata.aula_prevista_id = ap.id AND ata.tipo IN ('prevista', 'reposicao')
"""


def _com_status(row: Dict[str, Any]) -> Dict[str, Any]:
    row = _limpar(row) or {}
    row["status"] = status_aula_prevista(row.get("ata_tipo"))
    return row


class PostgresCargaHorariaRepository:
    # ---------- Calendários ----------

    def listar_calendarios(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(_SELECT_CALENDARIO + " ORDER BY c.ativo DESC, c.nome, c.id")
            return [_limpar(r) for r in cur.fetchall()]

    def obter_calendario(self, calendario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(_SELECT_CALENDARIO + " WHERE c.id = %s", (str(calendario_id),))
            return _limpar(cur.fetchone())

    @staticmethod
    def _valores(dados: Dict[str, Any]) -> List[Any]:
        return [
            Json(dados[c]) if c in ("feriados", "regras") else dados[c]
            for c in _CAMPOS_CALENDARIO
        ]

    def criar_calendario(self, dados: Dict[str, Any]) -> str:
        novo_id = str(uuid.uuid4())
        colunas = ", ".join(_CAMPOS_CALENDARIO)
        marcadores = ", ".join(["%s"] * len(_CAMPOS_CALENDARIO))
        with get_db_cursor() as cur:
            cur.execute(
                f"INSERT INTO calendarios_academicos (id, {colunas}) VALUES (%s, {marcadores})",
                tuple([novo_id] + self._valores(dados)),
            )
        return novo_id

    def atualizar_calendario(self, calendario_id: str, dados: Dict[str, Any]) -> None:
        sets = ", ".join(f"{c} = %s" for c in _CAMPOS_CALENDARIO)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE calendarios_academicos SET {sets}, atualizado_em = now() WHERE id = %s",
                tuple(self._valores(dados) + [str(calendario_id)]),
            )

    def contar_cursos_do_calendario(self, calendario_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM cursos WHERE calendario_id = %s", (str(calendario_id),))
            return int(cur.fetchone()["n"])

    def excluir_calendario(self, calendario_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM calendarios_academicos WHERE id = %s", (str(calendario_id),))

    # ---------- Turma ----------

    def contexto_turma(self, turma_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT t.id::text AS id, t.nome, t.curso_id::text AS curso_id, t.polo_id::text AS polo_id,
                       t.escola_id::text AS escola_id, t.data_inicio, t.data_fim, t.concluida_em,
                       cu.calendario_id::text AS calendario_id
                  FROM turmas t
                  LEFT JOIN cursos cu ON cu.id = t.curso_id
                 WHERE t.id = %s
                """,
                (str(turma_id),),
            )
            turma = _limpar(cur.fetchone())
        if not turma:
            return None
        turma["calendario"] = self.obter_calendario(turma["calendario_id"]) if turma.get("calendario_id") else None
        return turma

    def disciplinas_do_curso(self, curso_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, nome, COALESCE(carga_horaria, 0) AS carga_horaria,
                       COALESCE(qtd_aulas_prevista, 0) AS qtd_aulas_prevista, semestre, ordem
                  FROM disciplinas
                 WHERE curso_id = %s AND COALESCE(ativo, true) AND NOT COALESCE(eh_extra_grade, false)
                 ORDER BY semestre NULLS LAST, ordem, nome, id
                """,
                (str(curso_id),),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def listar_aulas_previstas(self, turma_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                _SELECT_AULA_PREVISTA + " WHERE ap.turma_id = %s ORDER BY d.nome, ap.disciplina_id, ap.numero",
                (str(turma_id),),
            )
            return [_com_status(r) for r in cur.fetchall()]

    def obter_aula_prevista(self, aula_prevista_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(_SELECT_AULA_PREVISTA + " WHERE ap.id = %s", (str(aula_prevista_id),))
            row = cur.fetchone()
            return _com_status(row) if row else None

    def substituir_pendentes(self, turma_id: str, novas: Sequence[AulaPlanejada]) -> None:
        """Remove as aulas pendentes (sem ata que as cumpra) e grava as novas, numa transação."""
        with get_db_cursor() as cur:
            cur.execute(
                """
                DELETE FROM aulas_previstas ap
                 WHERE ap.turma_id = %s
                   AND NOT EXISTS (
                       SELECT 1 FROM aulas_ministradas ata
                        WHERE ata.aula_prevista_id = ap.id AND ata.tipo IN ('prevista', 'reposicao'))
                """,
                (str(turma_id),),
            )
            for a in novas:
                cur.execute(
                    """
                    INSERT INTO aulas_previstas (id, turma_id, disciplina_id, numero, data_prevista, horas_previstas)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (str(uuid.uuid4()), str(turma_id), a.disciplina_id, a.numero, a.data, a.horas),
                )

    def listar_atas_turma(self, turma_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT ata.id::text AS id, v.disciplina_id::text AS disciplina_id, ata.tipo, ata.horas,
                       ata.aula_prevista_id::text AS aula_prevista_id,
                       ata.professor_disciplina_id::text AS professor_disciplina_id,
                       ata.data_aula, ata.numero_aula
                  FROM aulas_ministradas ata
                  JOIN professor_disciplinas v ON v.id = ata.professor_disciplina_id
                 WHERE v.turma_id = %s
                """,
                (str(turma_id),),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def listar_presencas_turma(self, turma_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT p.aluno_id::text AS aluno_id, p.professor_disciplina_id::text AS professor_disciplina_id,
                       p.data_aula, p.numero_aula, p.presente
                  FROM presencas p
                  JOIN professor_disciplinas v ON v.id = p.professor_disciplina_id
                 WHERE v.turma_id = %s
                """,
                (str(turma_id),),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def alunos_turma(self, turma_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT a.id::text AS aluno_id, a.numero_matricula,
                       COALESCE(NULLIF(TRIM(CONCAT_WS(' ', u.nome, u.sobrenome)), ''), a.numero_matricula) AS nome
                  FROM turma_alunos ta
                  JOIN alunos a ON a.id = ta.aluno_id
                  LEFT JOIN usuarios u ON u.id = a.usuario_id
                 WHERE ta.turma_id = %s AND COALESCE(ta.status, 'ativo') = 'ativo'
                 ORDER BY nome
                """,
                (str(turma_id),),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def concluir_turma(self, turma_id: str, usuario_id: str) -> datetime:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE turmas SET concluida_em = now(), concluida_por = %s, atualizado_em = now() "
                "WHERE id = %s RETURNING concluida_em",
                (str(usuario_id), str(turma_id)),
            )
            return cur.fetchone()["concluida_em"]

    # ---------- Auditoria ----------

    def auditar(self, usuario_id, acao, entidade, entidade_id, antes=None, depois=None, ip=None) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO logs_auditoria (
                    usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    str(usuario_id) if usuario_id else None, acao, entidade,
                    str(entidade_id) if entidade_id else None,
                    json.dumps(antes, default=str) if antes is not None else None,
                    json.dumps(depois, default=str) if depois is not None else None,
                    ip,
                ),
            )


class InMemoryCargaHorariaRepository:
    """Usado nos testes. As atas e presenças são lidas do repositório de aulas em memória
    (`aulas_repo`), para que o fluxo Diário → andamento seja testado de ponta a ponta."""

    def __init__(self, aulas_repo: Any = None) -> None:
        self.calendarios: Dict[str, Dict[str, Any]] = {}
        self.cursos: Dict[str, Dict[str, Any]] = {}  # id -> {calendario_id}
        self.turmas: Dict[str, Dict[str, Any]] = {}
        self.disciplinas: Dict[str, Dict[str, Any]] = {}  # id -> {nome, carga_horaria, qtd_aulas_prevista, curso_id}
        self.aulas_previstas: Dict[str, Dict[str, Any]] = {}
        self.alunos: Dict[str, List[Dict[str, Any]]] = {}  # turma_id -> alunos
        self.auditoria: List[Dict[str, Any]] = []
        self.aulas_repo = aulas_repo

    # ---------- Calendários ----------

    def _calendario(self, cal: Dict[str, Any]) -> Dict[str, Any]:
        total = sum(1 for c in self.cursos.values() if c.get("calendario_id") == cal["id"])
        return {**cal, "total_cursos": total}

    def listar_calendarios(self) -> List[Dict[str, Any]]:
        return [self._calendario(c) for c in sorted(self.calendarios.values(), key=lambda c: c["nome"])]

    def obter_calendario(self, calendario_id: str) -> Optional[Dict[str, Any]]:
        cal = self.calendarios.get(str(calendario_id))
        return self._calendario(cal) if cal else None

    def criar_calendario(self, dados: Dict[str, Any]) -> str:
        novo_id = str(uuid.uuid4())
        self.calendarios[novo_id] = {"id": novo_id, **dados, "criado_em": datetime.now(timezone.utc)}
        return novo_id

    def atualizar_calendario(self, calendario_id: str, dados: Dict[str, Any]) -> None:
        self.calendarios[str(calendario_id)].update(dados)

    def contar_cursos_do_calendario(self, calendario_id: str) -> int:
        return sum(1 for c in self.cursos.values() if c.get("calendario_id") == str(calendario_id))

    def excluir_calendario(self, calendario_id: str) -> None:
        self.calendarios.pop(str(calendario_id), None)

    # ---------- Turma ----------

    def contexto_turma(self, turma_id: str) -> Optional[Dict[str, Any]]:
        turma = self.turmas.get(str(turma_id))
        if not turma:
            return None
        cal_id = (self.cursos.get(str(turma.get("curso_id"))) or {}).get("calendario_id")
        return {**turma, "calendario_id": cal_id, "calendario": self.obter_calendario(cal_id) if cal_id else None}

    def disciplinas_do_curso(self, curso_id: str) -> List[Dict[str, Any]]:
        return [{"id": k, **v} for k, v in self.disciplinas.items() if v.get("curso_id") == str(curso_id)]

    def _atas(self) -> List[Dict[str, Any]]:
        return list(self.aulas_repo.aulas.values()) if self.aulas_repo else []

    def _montar_prevista(self, ap: Dict[str, Any]) -> Dict[str, Any]:
        ata = next((a for a in self._atas() if a.get("aula_prevista_id") == ap["id"]
                    and a.get("tipo") in TIPOS_QUE_ABATEM), None)
        return {
            **ap,
            "disciplina_nome": (self.disciplinas.get(ap["disciplina_id"]) or {}).get("nome"),
            "ata_id": ata["id"] if ata else None,
            "ata_tipo": ata.get("tipo") if ata else None,
            "ata_data": ata.get("data_aula") if ata else None,
            "status": status_aula_prevista(ata.get("tipo") if ata else None),
        }

    def listar_aulas_previstas(self, turma_id: str) -> List[Dict[str, Any]]:
        itens = [self._montar_prevista(a) for a in self.aulas_previstas.values() if a["turma_id"] == str(turma_id)]
        return sorted(itens, key=lambda a: (a["disciplina_id"], a["numero"]))

    def obter_aula_prevista(self, aula_prevista_id: str) -> Optional[Dict[str, Any]]:
        ap = self.aulas_previstas.get(str(aula_prevista_id))
        return self._montar_prevista(ap) if ap else None

    def substituir_pendentes(self, turma_id: str, novas: Sequence[AulaPlanejada]) -> None:
        for ap_id in [k for k, a in self.aulas_previstas.items() if a["turma_id"] == str(turma_id)]:
            if self._montar_prevista(self.aulas_previstas[ap_id])["status"] == "pendente":
                del self.aulas_previstas[ap_id]
        for a in novas:
            novo_id = str(uuid.uuid4())
            self.aulas_previstas[novo_id] = {
                "id": novo_id, "turma_id": str(turma_id), "disciplina_id": a.disciplina_id,
                "numero": a.numero, "data_prevista": a.data, "horas_previstas": a.horas,
            }

    def listar_atas_turma(self, turma_id: str) -> List[Dict[str, Any]]:
        if not self.aulas_repo:
            return []
        saida = []
        for ata in self._atas():
            vinculo = self.aulas_repo.vinculos.get(ata["professor_disciplina_id"]) or {}
            if vinculo.get("turma_id") == str(turma_id):
                saida.append({**ata, "disciplina_id": vinculo.get("disciplina_id")})
        return saida

    def listar_presencas_turma(self, turma_id: str) -> List[Dict[str, Any]]:
        if not self.aulas_repo:
            return []
        vinculos = {k for k, v in self.aulas_repo.vinculos.items() if v.get("turma_id") == str(turma_id)}
        return [p for p in self.aulas_repo.presencas if p["professor_disciplina_id"] in vinculos]

    def alunos_turma(self, turma_id: str) -> List[Dict[str, Any]]:
        if self.aulas_repo and str(turma_id) in self.aulas_repo.alunos_turma:
            return list(self.aulas_repo.alunos_turma[str(turma_id)])
        return list(self.alunos.get(str(turma_id), []))

    def concluir_turma(self, turma_id: str, usuario_id: str) -> datetime:
        agora = datetime.now(timezone.utc)
        self.turmas[str(turma_id)].update({"concluida_em": agora, "concluida_por": usuario_id})
        return agora

    def auditar(self, usuario_id, acao, entidade, entidade_id, antes=None, depois=None, ip=None) -> None:
        self.auditoria.append({"usuario_id": usuario_id, "acao": acao, "entidade": entidade,
                               "entidade_id": entidade_id, "antes": antes, "depois": depois})


_repo_padrao: Optional[CargaHorariaRepositoryInterface] = None


def get_carga_horaria_repository() -> CargaHorariaRepositoryInterface:
    global _repo_padrao
    if _repo_padrao is None:
        _repo_padrao = PostgresCargaHorariaRepository()
    return _repo_padrao


def set_carga_horaria_repository(repo: Optional[CargaHorariaRepositoryInterface]) -> None:
    global _repo_padrao
    _repo_padrao = repo
