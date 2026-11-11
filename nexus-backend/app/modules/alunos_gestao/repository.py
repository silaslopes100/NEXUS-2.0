"""Persistência da Central de Alunos."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.database import get_db_cursor

LICENCAS_REINGRESSO = 2  # RN-04: cobradas do Polo de destino
_ENCERRADAS = ("aprovado", "reprovado")


class ConflitoNegocio(Exception):
    """Regra de negócio impede a operação no estado atual dos dados."""


@dataclass(frozen=True)
class FiltrosAlunos:
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    somente_ead: bool = False
    observacao: Optional[str] = None
    q: Optional[str] = None


@dataclass(frozen=True)
class DadosReingresso:
    modalidade: str
    polo_id: Optional[str]
    escola_id: Optional[str]
    licencas: int


class AlunosGestaoRepositoryInterface(Protocol):
    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]: ...
    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]: ...
    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...
    def listar(
        self, filtros: FiltrosAlunos, limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def academico(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def confirmar_churn(self, aluno_id: str, ator_id: str, ip: Optional[str]) -> bool: ...
    def reingressar(
        self, aluno_id: str, dados: DadosReingresso, ator_id: str, ip: Optional[str]
    ) -> Optional[str]: ...
    def aprendizado(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def conteudo_do_aluno(self, aluno_id: str, conteudo_id: str) -> bool: ...
    def arquivo_conteudo_do_aluno(
        self, aluno_id: str, conteudo_id: str
    ) -> Optional[Dict[str, Any]]: ...
    def marcar_conteudo(self, aluno_id: str, conteudo_id: str, concluido: bool) -> None: ...


def _cursos_do_aluno(aluno: str) -> str:
    return f"""
        SELECT t.curso_id FROM turma_alunos ta JOIN turmas t ON t.id = ta.turma_id
        WHERE ta.aluno_id = {aluno} AND t.curso_id IS NOT NULL
        UNION
        SELECT m.curso_id FROM matriculas_ead m
        WHERE m.aluno_id = {aluno} AND m.curso_id IS NOT NULL
        UNION
        SELECT d.curso_id FROM historico_unificado h JOIN disciplinas d ON d.id = h.disciplina_id
        WHERE h.aluno_id = {aluno} AND d.curso_id IS NOT NULL
    """


_REFERENCIA = "COALESCE(a.ultima_movimentacao_em, a.atualizado_em, a.criado_em)"

_ALUNO_SELECT = f"""
    SELECT a.id, a.usuario_id, a.polo_id, a.escola_id, a.modalidade, a.status,
           a.numero_matricula, {_REFERENCIA} AS referencia_movimentacao,
           concat_ws(' ', u.nome, u.sobrenome) AS nome, p.nome AS perfil_nome
    FROM alunos a
    JOIN usuarios u ON u.id = a.usuario_id
    LEFT JOIN perfis p ON p.id = u.perfil_id
"""

_CONDICAO_OBSERVACAO = {
    "formado": "EXISTS (SELECT 1 FROM certificados c WHERE c.aluno_id = a.id)",
    "churn": "a.status = 'desistente'",
    "transferido": (
        "EXISTS (SELECT 1 FROM solicitacoes_transferencia st "
        "WHERE st.aluno_id = a.id AND st.status = 'aprovada' AND st.tipo <> 'reingresso')"
    ),
    "revalidado": "a.revalidado_em IS NOT NULL",
    "sem_movimentacao": f"a.status = 'ativo' AND {_REFERENCIA} < now() - interval '365 days'",
}


def _auditar(
    cur: Any,
    ator_id: str,
    acao: str,
    aluno_id: str,
    antes: Dict[str, Any],
    depois: Dict[str, Any],
    ip: Optional[str],
) -> None:
    cur.execute(
        """
        INSERT INTO logs_auditoria (
            usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip,
            criado_em, atualizado_em
        ) VALUES (%s, %s, 'alunos', %s, %s, %s, %s, now(), now())
        """,
        (
            ator_id,
            acao,
            aluno_id,
            json.dumps(antes, default=str),
            json.dumps(depois, default=str),
            ip,
        ),
    )


def _atualizar_vinculo_usuario(
    cur: Any, aluno: Dict[str, Any], polo_id: Optional[str], escola_id: Optional[str]
) -> None:
    # Em Polo e Escola, esses campos definem a unidade gerenciada, não onde a pessoa estuda.
    if (aluno.get("perfil_nome") or "").lower() == "aluno":
        cur.execute(
            "UPDATE usuarios SET polo_id = %s, escola_id = %s, atualizado_em = now() WHERE id = %s",
            (polo_id, escola_id, aluno["usuario_id"]),
        )


class PostgresAlunosGestaoRepository:
    def _um(self, sql: str, params: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        return self._um("SELECT id, nome, status FROM polos WHERE id = %s", (polo_id,))

    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]:
        return self._um("SELECT id, nome, status, polo_id FROM escolas WHERE id = %s", (escola_id,))

    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        return self._um(f"{_ALUNO_SELECT} WHERE a.id = %s", (aluno_id,))

    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        return self._um(f"{_ALUNO_SELECT} WHERE a.usuario_id = %s", (usuario_id,))

    def listar(
        self, filtros: FiltrosAlunos, limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds: List[str] = []
        params: List[Any] = []
        if filtros.polo_id:
            conds.append("a.polo_id = %s")
            params.append(filtros.polo_id)
        if filtros.escola_id:
            conds.append("a.escola_id = %s")
            params.append(filtros.escola_id)
        if filtros.somente_ead:
            conds.append("a.modalidade = 'ead'")
        if filtros.observacao:
            conds.append(_CONDICAO_OBSERVACAO[filtros.observacao])
        if filtros.q and filtros.q.strip():
            termo = filtros.q.strip().lower()
            like = f"%{termo}%"
            digitos = "".join(filter(str.isdigit, termo))
            conds.append(
                "(lower(concat_ws(' ', u.nome, u.sobrenome)) LIKE %s OR lower(u.email) LIKE %s "
                "OR lower(a.numero_matricula) LIKE %s "
                "OR regexp_replace(coalesce(u.cpf, ''), '[^0-9]', '', 'g') LIKE %s)"
            )
            params.extend([like, like, like, f"%{digitos}%" if digitos else "sem-digitos"])
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        encerradas = ", ".join(f"'{situacao}'" for situacao in _ENCERRADAS)

        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) AS total FROM alunos a JOIN usuarios u ON u.id = a.usuario_id {where}",
                tuple(params),
            )
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"""
                WITH pagina AS (
                    SELECT a.id, a.usuario_id, a.polo_id, a.escola_id, a.modalidade, a.status,
                           a.numero_matricula, a.revalidado_em,
                           {_REFERENCIA} AS referencia_movimentacao,
                           concat_ws(' ', u.nome, u.sobrenome) AS nome,
                           u.email, u.ultimo_login_em
                    FROM alunos a
                    JOIN usuarios u ON u.id = a.usuario_id
                    {where}
                    ORDER BY nome, a.id
                    LIMIT %s OFFSET %s
                )
                SELECT p.*, po.nome AS polo_nome, es.nome AS escola_nome,
                       COALESCE(pr.presentes, 0) AS presentes,
                       COALESCE(pr.total_aulas, 0) AS total_aulas,
                       COALESCE(tu.turmas, ARRAY[]::text[]) AS turmas,
                       EXISTS (SELECT 1 FROM certificados c WHERE c.aluno_id = p.id) AS tem_certificado,
                       EXISTS (
                           SELECT 1 FROM solicitacoes_transferencia st
                           WHERE st.aluno_id = p.id AND st.status = 'aprovada'
                             AND st.tipo <> 'reingresso'
                       ) AS transferido,
                       rein.polo_destino_id AS reingresso_polo_destino_id,
                       rein.escola_destino_id AS reingresso_escola_destino_id,
                       COALESCE(dc.total, 0) AS disciplinas_em_curso
                FROM pagina p
                LEFT JOIN polos po ON po.id = p.polo_id
                LEFT JOIN escolas es ON es.id = p.escola_id
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) FILTER (WHERE pre.presente) AS presentes, COUNT(*) AS total_aulas
                    FROM presencas pre WHERE pre.aluno_id = p.id
                ) pr ON TRUE
                LEFT JOIN LATERAL (
                    SELECT array_agg(t.nome::text ORDER BY t.nome) AS turmas
                    FROM turma_alunos ta JOIN turmas t ON t.id = ta.turma_id
                    WHERE ta.aluno_id = p.id
                ) tu ON TRUE
                LEFT JOIN LATERAL (
                    SELECT st.polo_destino_id, st.escola_destino_id
                    FROM solicitacoes_transferencia st
                    WHERE st.aluno_id = p.id AND st.tipo = 'reingresso' AND st.status = 'pendente'
                    LIMIT 1
                ) rein ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS total
                    FROM disciplinas d
                    WHERE p.status = 'ativo'
                      AND d.curso_id IN ({_cursos_do_aluno("p.id")})
                      AND NOT EXISTS (
                          SELECT 1 FROM historico_unificado h
                          WHERE h.aluno_id = p.id AND h.disciplina_id = d.id
                            AND h.status IN ({encerradas})
                      )
                ) dc ON TRUE
                ORDER BY p.nome, p.id
                """,
                (*params, limit, offset),
            )
            return total, [dict(row) for row in cur.fetchall()]

    def academico(self, aluno_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                WITH cursos_aluno AS ({_cursos_do_aluno("%(aluno)s")})
                SELECT c.id AS curso_id, c.nome AS curso_nome,
                       d.id AS disciplina_id, d.nome AS disciplina_nome, d.semestre, d.carga_horaria,
                       COALESCE(
                           h.nota_final,
                           (SELECT MAX(n.valor) FROM notas n
                            WHERE n.aluno_id = %(aluno)s AND n.disciplina_id = d.id)
                       ) AS nota,
                       h.status AS situacao,
                       (SELECT COUNT(*) FROM disciplina_conteudos dc
                        WHERE dc.disciplina_id = d.id) AS total_conteudos,
                       (SELECT COUNT(*) FROM conteudo_progresso cp
                        JOIN disciplina_conteudos dc ON dc.id = cp.conteudo_id
                        WHERE cp.aluno_id = %(aluno)s AND dc.disciplina_id = d.id
                       ) AS conteudos_concluidos
                FROM cursos_aluno ca
                JOIN cursos c ON c.id = ca.curso_id
                JOIN disciplinas d ON d.curso_id = c.id
                LEFT JOIN historico_unificado h
                       ON h.aluno_id = %(aluno)s AND h.disciplina_id = d.id
                ORDER BY c.nome, c.id, d.semestre NULLS LAST, d.ordem, d.nome
                """,
                {"aluno": aluno_id},
            )
            return [dict(row) for row in cur.fetchall()]

    def _aluno_bloqueado(self, cur: Any, aluno_id: str) -> Optional[Dict[str, Any]]:
        cur.execute(f"{_ALUNO_SELECT} WHERE a.id = %s FOR UPDATE OF a", (aluno_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def confirmar_churn(self, aluno_id: str, ator_id: str, ip: Optional[str]) -> bool:
        with get_db_cursor() as cur:
            aluno = self._aluno_bloqueado(cur, aluno_id)
            if aluno is None:
                return False
            if aluno["status"] != "ativo":
                raise ConflitoNegocio("O aluno não está ativo")
            cur.execute(
                f"SELECT {_REFERENCIA} < now() - interval '365 days' AS parado FROM alunos a WHERE a.id = %s",
                (aluno_id,),
            )
            if not cur.fetchone()["parado"]:
                raise ConflitoNegocio("O aluno teve movimentação no último ano")

            cur.execute(
                """
                UPDATE alunos
                SET status = 'desistente', polo_id = NULL, escola_id = NULL, atualizado_em = now()
                WHERE id = %s
                """,
                (aluno_id,),
            )
            _atualizar_vinculo_usuario(cur, aluno, None, None)
            cur.execute("DELETE FROM turma_alunos WHERE aluno_id = %s", (aluno_id,))
            cur.execute(
                """
                INSERT INTO alunos_desistentes (id, aluno_id, motivo, criado_em, atualizado_em)
                VALUES (%s, %s, 'Sem movimentação há mais de 1 ano', now(), now())
                """,
                (str(uuid.uuid4()), aluno_id),
            )
            cur.execute(
                """
                UPDATE solicitacoes_transferencia
                SET status = 'rejeitada', motivo_rejeicao = 'Aluno enviado ao Churn',
                    resolvido_por = %s, resolvido_em = now(), atualizado_em = now()
                WHERE aluno_id = %s AND status = 'pendente'
                """,
                (ator_id, aluno_id),
            )
            _auditar(cur, ator_id, "aluno_churn_confirmado", aluno_id, aluno, {"status": "desistente"}, ip)
        return True

    def _debitar_licencas(
        self, cur: Any, aluno_id: str, polo_id: str, quantidade: int, ator_id: str
    ) -> None:
        cur.execute(
            """
            SELECT id, quantidade_disponivel FROM licencas_estoque
            WHERE polo_id = %s AND escola_id IS NULL
            LIMIT 1 FOR UPDATE
            """,
            (polo_id,),
        )
        estoque = cur.fetchone()
        if estoque is None or estoque["quantidade_disponivel"] < quantidade:
            raise ConflitoNegocio(
                f"O Polo de destino não tem {quantidade} licenças disponíveis para o reingresso"
            )
        cur.execute(
            """
            UPDATE licencas_estoque
            SET quantidade_disponivel = quantidade_disponivel - %s, atualizado_em = now()
            WHERE id = %s
            """,
            (quantidade, estoque["id"]),
        )
        cur.execute(
            """
            INSERT INTO licencas_movimentacoes (
                id, tipo, polo_id, aluno_id, quantidade, status, actor_id, observacao, criado_em
            ) VALUES (%s, 'reingresso_churn', %s, %s, %s, 'consumida', %s, %s, now())
            """,
            (
                str(uuid.uuid4()),
                polo_id,
                aluno_id,
                quantidade,
                ator_id,
                "Cobrança de reingresso de aluno em Churn",
            ),
        )

    def reingressar(
        self, aluno_id: str, dados: DadosReingresso, ator_id: str, ip: Optional[str]
    ) -> Optional[str]:
        with get_db_cursor() as cur:
            aluno = self._aluno_bloqueado(cur, aluno_id)
            if aluno is None:
                return None
            if aluno["status"] != "desistente":
                raise ConflitoNegocio("Somente alunos em Churn podem receber nova matrícula")

            if dados.licencas and dados.polo_id:
                self._debitar_licencas(cur, aluno_id, dados.polo_id, dados.licencas, ator_id)

            cur.execute(
                """
                UPDATE alunos
                SET status = 'ativo', polo_id = %s, escola_id = %s, modalidade = %s,
                    numero_matricula =
                        'NX-' || to_char(now(), 'YYYY') || '-'
                        || lpad(nextval('seq_matricula_aluno')::text, 7, '0'),
                    revalidado_em = now(), ultima_movimentacao_em = now(), atualizado_em = now()
                WHERE id = %s
                RETURNING numero_matricula
                """,
                (dados.polo_id, dados.escola_id, dados.modalidade, aluno_id),
            )
            nova_matricula = cur.fetchone()["numero_matricula"]
            _atualizar_vinculo_usuario(cur, aluno, dados.polo_id, dados.escola_id)

            cur.execute(
                """
                UPDATE alunos_desistentes
                SET taxa_regularizacao_paga = true, reingresso_em = now(),
                    matricula_anterior = %s, atualizado_em = now()
                WHERE id = (
                    SELECT id FROM alunos_desistentes
                    WHERE aluno_id = %s AND reingresso_em IS NULL
                    ORDER BY data_marcacao DESC
                    LIMIT 1
                )
                RETURNING id
                """,
                (aluno["numero_matricula"], aluno_id),
            )
            if cur.fetchone() is None:
                cur.execute(
                    """
                    INSERT INTO alunos_desistentes (
                        id, aluno_id, motivo, taxa_regularizacao_paga, reingresso_em,
                        matricula_anterior, criado_em, atualizado_em
                    ) VALUES (%s, %s, 'Marcado como desistente na carga do legado', true, now(), %s, now(), now())
                    """,
                    (str(uuid.uuid4()), aluno_id, aluno["numero_matricula"]),
                )

            cur.execute(
                """
                UPDATE solicitacoes_transferencia
                SET status = 'aprovada', resolvido_por = %s, resolvido_em = now(), atualizado_em = now()
                WHERE aluno_id = %s AND tipo = 'reingresso' AND status = 'pendente'
                """,
                (ator_id, aluno_id),
            )
            _auditar(
                cur,
                ator_id,
                "aluno_reingresso",
                aluno_id,
                aluno,
                {
                    "numero_matricula": nova_matricula,
                    "polo_id": dados.polo_id,
                    "escola_id": dados.escola_id,
                    "modalidade": dados.modalidade,
                    "licencas_debitadas": dados.licencas,
                },
                ip,
            )
        return nova_matricula

    def aprendizado(self, aluno_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                WITH cursos_aluno AS ({_cursos_do_aluno("%(aluno)s")})
                SELECT c.id AS curso_id, c.nome AS curso_nome,
                       d.id AS disciplina_id, d.nome AS disciplina_nome,
                       dc.id AS conteudo_id, dc.titulo, dc.tipo_midia, dc.url_arquivo,
                       dc.arquivo_nome, dc.arquivo_mime_type, dc.arquivo_tamanho_bytes,
                       dc.arquivo_storage_key IS NOT NULL AS tem_arquivo,
                       cp.id IS NOT NULL AS concluido
                FROM cursos_aluno ca
                JOIN cursos c ON c.id = ca.curso_id
                JOIN disciplinas d ON d.curso_id = c.id
                LEFT JOIN disciplina_conteudos dc ON dc.disciplina_id = d.id
                LEFT JOIN conteudo_progresso cp
                       ON cp.conteudo_id = dc.id AND cp.aluno_id = %(aluno)s
                ORDER BY c.nome, c.id, d.semestre NULLS LAST, d.ordem, d.nome, d.id, dc.ordem, dc.id
                """,
                {"aluno": aluno_id},
            )
            return [dict(row) for row in cur.fetchall()]

    def conteudo_do_aluno(self, aluno_id: str, conteudo_id: str) -> bool:
        row = self._um(
            f"""
            SELECT 1 AS existe
            FROM disciplina_conteudos dc
            JOIN disciplinas d ON d.id = dc.disciplina_id
            WHERE dc.id = %(conteudo)s AND d.curso_id IN ({_cursos_do_aluno("%(aluno)s")})
            """,
            {"aluno": aluno_id, "conteudo": conteudo_id},  # type: ignore[arg-type]
        )
        return row is not None

    def arquivo_conteudo_do_aluno(
        self, aluno_id: str, conteudo_id: str
    ) -> Optional[Dict[str, Any]]:
        return self._um(
            f"""
            SELECT dc.arquivo_storage_key, dc.arquivo_nome,
                   dc.arquivo_mime_type, dc.arquivo_tamanho_bytes
            FROM disciplina_conteudos dc
            JOIN disciplinas d ON d.id = dc.disciplina_id
            WHERE dc.id = %(conteudo)s
              AND dc.arquivo_storage_key IS NOT NULL
              AND d.curso_id IN ({_cursos_do_aluno("%(aluno)s")})
            """,
            {"aluno": aluno_id, "conteudo": conteudo_id},
        )

    def marcar_conteudo(self, aluno_id: str, conteudo_id: str, concluido: bool) -> None:
        with get_db_cursor() as cur:
            if not concluido:
                cur.execute(
                    "DELETE FROM conteudo_progresso WHERE aluno_id = %s AND conteudo_id = %s",
                    (aluno_id, conteudo_id),
                )
                return
            cur.execute(
                """
                INSERT INTO conteudo_progresso (aluno_id, conteudo_id)
                VALUES (%s, %s)
                ON CONFLICT (aluno_id, conteudo_id) DO NOTHING
                """,
                (aluno_id, conteudo_id),
            )
            cur.execute(
                "UPDATE alunos SET ultima_movimentacao_em = now(), atualizado_em = now() WHERE id = %s",
                (aluno_id,),
            )


class InMemoryAlunosGestaoRepository:
    """Implementação em memória para testes."""

    def __init__(self) -> None:
        self.alunos: Dict[str, Dict[str, Any]] = {}
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, Dict[str, Any]] = {}
        self.estoque_polo: Dict[str, int] = {}
        self.movimentacoes: List[Dict[str, Any]] = []
        self.desistentes: List[Dict[str, Any]] = []
        self.turma_alunos: List[Dict[str, Any]] = []
        self.solicitacoes: List[Dict[str, Any]] = []
        self.linhas_academico: Dict[str, List[Dict[str, Any]]] = {}
        self.linhas_aprendizado: Dict[str, List[Dict[str, Any]]] = {}
        self.progresso: set[Tuple[str, str]] = set()
        self.logs: List[str] = []
        self._seq_matricula = 0

    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        return self.polos.get(str(polo_id))

    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]:
        return self.escolas.get(str(escola_id))

    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        aluno = self.alunos.get(str(aluno_id))
        return dict(aluno) if aluno else None

    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        for aluno in self.alunos.values():
            if aluno["usuario_id"] == usuario_id:
                return dict(aluno)
        return None

    def _combina(self, aluno: Dict[str, Any], filtros: FiltrosAlunos) -> bool:
        if filtros.polo_id and aluno.get("polo_id") != filtros.polo_id:
            return False
        if filtros.escola_id and aluno.get("escola_id") != filtros.escola_id:
            return False
        if filtros.somente_ead and aluno.get("modalidade") != "ead":
            return False
        if filtros.q and filtros.q.strip().lower() not in aluno["nome"].lower():
            return False
        if filtros.observacao == "churn":
            return aluno.get("status") == "desistente"
        if filtros.observacao == "formado":
            return bool(aluno.get("tem_certificado"))
        if filtros.observacao == "transferido":
            return bool(aluno.get("transferido"))
        if filtros.observacao == "revalidado":
            return aluno.get("revalidado_em") is not None
        return True

    def listar(
        self, filtros: FiltrosAlunos, limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        itens = sorted(
            (dict(a) for a in self.alunos.values() if self._combina(a, filtros)),
            key=lambda aluno: aluno["nome"],
        )
        return len(itens), itens[offset : offset + limit]

    def academico(self, aluno_id: str) -> List[Dict[str, Any]]:
        return list(self.linhas_academico.get(aluno_id, []))

    def confirmar_churn(self, aluno_id: str, ator_id: str, ip: Optional[str]) -> bool:
        aluno = self.alunos.get(aluno_id)
        if aluno is None:
            return False
        if aluno["status"] != "ativo":
            raise ConflitoNegocio("O aluno não está ativo")
        if not aluno.get("parado"):
            raise ConflitoNegocio("O aluno teve movimentação no último ano")
        aluno.update(status="desistente", polo_id=None, escola_id=None)
        self.turma_alunos = [v for v in self.turma_alunos if v["aluno_id"] != aluno_id]
        self.desistentes.append({"aluno_id": aluno_id, "reingresso_em": None})
        for solicitacao in self.solicitacoes:
            if solicitacao["aluno_id"] == aluno_id and solicitacao["status"] == "pendente":
                solicitacao["status"] = "rejeitada"
        self.logs.append("aluno_churn_confirmado")
        return True

    def reingressar(
        self, aluno_id: str, dados: DadosReingresso, ator_id: str, ip: Optional[str]
    ) -> Optional[str]:
        aluno = self.alunos.get(aluno_id)
        if aluno is None:
            return None
        if aluno["status"] != "desistente":
            raise ConflitoNegocio("Somente alunos em Churn podem receber nova matrícula")
        if dados.licencas and dados.polo_id:
            if self.estoque_polo.get(dados.polo_id, 0) < dados.licencas:
                raise ConflitoNegocio(
                    f"O Polo de destino não tem {dados.licencas} licenças disponíveis para o reingresso"
                )
            self.estoque_polo[dados.polo_id] -= dados.licencas
            self.movimentacoes.append({"tipo": "reingresso_churn", "polo_id": dados.polo_id})
        self._seq_matricula += 1
        anterior = aluno.get("numero_matricula")
        nova = f"NX-2026-{self._seq_matricula:07d}"
        aluno.update(
            status="ativo",
            polo_id=dados.polo_id,
            escola_id=dados.escola_id,
            modalidade=dados.modalidade,
            numero_matricula=nova,
            revalidado_em=datetime.now(timezone.utc),
        )
        self.desistentes.append(
            {"aluno_id": aluno_id, "reingresso_em": datetime.now(timezone.utc), "matricula_anterior": anterior}
        )
        for solicitacao in self.solicitacoes:
            if solicitacao["aluno_id"] == aluno_id and solicitacao["tipo"] == "reingresso":
                solicitacao["status"] = "aprovada"
        self.logs.append("aluno_reingresso")
        return nova

    def aprendizado(self, aluno_id: str) -> List[Dict[str, Any]]:
        return [
            {**linha, "concluido": (aluno_id, linha.get("conteudo_id")) in self.progresso}
            for linha in self.linhas_aprendizado.get(aluno_id, [])
        ]

    def conteudo_do_aluno(self, aluno_id: str, conteudo_id: str) -> bool:
        return any(
            linha.get("conteudo_id") == conteudo_id
            for linha in self.linhas_aprendizado.get(aluno_id, [])
        )

    def arquivo_conteudo_do_aluno(
        self, aluno_id: str, conteudo_id: str
    ) -> Optional[Dict[str, Any]]:
        row = next(
            (
                linha
                for linha in self.linhas_aprendizado.get(aluno_id, [])
                if str(linha.get("conteudo_id")) == str(conteudo_id)
            ),
            None,
        )
        if not row or not row.get("arquivo_storage_key"):
            return None
        return {
            "arquivo_storage_key": row["arquivo_storage_key"],
            "arquivo_nome": row.get("arquivo_nome"),
            "arquivo_mime_type": row.get("arquivo_mime_type"),
            "arquivo_tamanho_bytes": row.get("arquivo_tamanho_bytes"),
        }

    def marcar_conteudo(self, aluno_id: str, conteudo_id: str, concluido: bool) -> None:
        if concluido:
            self.progresso.add((aluno_id, conteudo_id))
        else:
            self.progresso.discard((aluno_id, conteudo_id))


_repo_instance: Optional[AlunosGestaoRepositoryInterface] = None


def get_alunos_gestao_repository() -> AlunosGestaoRepositoryInterface:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = PostgresAlunosGestaoRepository()
    return _repo_instance


def set_alunos_gestao_repository(repo: Optional[AlunosGestaoRepositoryInterface]) -> None:
    global _repo_instance
    _repo_instance = repo
