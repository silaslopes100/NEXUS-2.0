"""Persistência das solicitações de transferência."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from psycopg2.errors import UniqueViolation

from app.core.database import get_db_cursor

DIAS_CHURN = 365  # RN-05: mais de 1 ano sem movimentação


class SolicitacaoPendenteError(Exception):
    """O aluno já possui uma solicitação aguardando análise."""


@dataclass(frozen=True)
class EscopoListagem:
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    solicitante_id: Optional[str] = None
    aluno_usuario_id: Optional[str] = None


@dataclass(frozen=True)
class Resolucao:
    """Efeitos que uma decisão aplica, todos na mesma transação."""

    status: str
    acao_auditoria: str
    motivo_rejeicao: Optional[str] = None
    aluno_campos: Optional[Dict[str, Any]] = None
    atualizar_usuario: bool = False
    renovar_movimentacao: bool = False
    motivo_churn: Optional[str] = None
    remover_turmas: bool = False


Decisao = Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Resolucao]


class TransferenciasRepositoryInterface(Protocol):
    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]: ...
    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...
    def buscar_alunos(
        self, q: str, polo_id: Optional[str], escola_id: Optional[str], limit: int
    ) -> List[Dict[str, Any]]: ...
    def buscar_desistentes(self, q: str, limit: int) -> List[Dict[str, Any]]: ...
    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]: ...
    def listar_polos_ativos(self) -> List[Dict[str, Any]]: ...
    def listar_escolas_ativas(self, polo_id: str) -> List[Dict[str, Any]]: ...
    def criar(self, data: Dict[str, Any], ip: Optional[str]) -> str: ...
    def get(self, solicitacao_id: str) -> Optional[Dict[str, Any]]: ...
    def listar(
        self,
        escopo: EscopoListagem,
        status_filter: Optional[str],
        tipo: Optional[str],
        q: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def resolver(
        self, solicitacao_id: str, decidir: Decisao, resolvido_por: str, ip: Optional[str]
    ) -> Optional[Dict[str, Any]]: ...


_ALUNO_SELECT = """
    SELECT a.id, a.usuario_id, a.polo_id, a.escola_id, a.modalidade, a.status,
           a.numero_matricula,
           COALESCE(a.ultima_movimentacao_em, a.atualizado_em, a.criado_em) AS referencia_movimentacao,
           concat_ws(' ', u.nome, u.sobrenome) AS nome,
           p.nome AS perfil_nome, po.nome AS polo_nome, es.nome AS escola_nome
    FROM alunos a
    JOIN usuarios u ON u.id = a.usuario_id
    LEFT JOIN perfis p ON p.id = u.perfil_id
    LEFT JOIN polos po ON po.id = a.polo_id
    LEFT JOIN escolas es ON es.id = a.escola_id
"""

_SOLICITACAO_FROM = """
    FROM solicitacoes_transferencia st
    LEFT JOIN alunos a ON a.id = st.aluno_id
    LEFT JOIN usuarios u ON u.id = a.usuario_id
    LEFT JOIN usuarios sol ON sol.id = st.solicitado_por
    LEFT JOIN polos po ON po.id = st.polo_origem_id
    LEFT JOIN polos pd ON pd.id = st.polo_destino_id
    LEFT JOIN escolas eo ON eo.id = st.escola_origem_id
    LEFT JOIN escolas ed ON ed.id = st.escola_destino_id
"""

_SOLICITACAO_SELECT = f"""
    SELECT st.id, st.aluno_id, st.tipo, st.status, st.polo_origem_id, st.polo_destino_id,
           st.escola_origem_id, st.escola_destino_id, st.modalidade_origem,
           st.modalidade_destino, st.solicitado_por, st.observacao, st.motivo_rejeicao,
           st.resolvido_em, st.criado_em, a.numero_matricula,
           concat_ws(' ', u.nome, u.sobrenome) AS aluno_nome,
           concat_ws(' ', sol.nome, sol.sobrenome) AS solicitado_por_nome,
           po.nome AS polo_origem_nome, pd.nome AS polo_destino_nome,
           eo.nome AS escola_origem_nome, ed.nome AS escola_destino_nome,
           COALESCE(
               st.status = 'pendente'
               AND st.tipo <> 'reingresso'
               AND COALESCE(a.ultima_movimentacao_em, a.atualizado_em, a.criado_em)
                   < now() - interval '{DIAS_CHURN} days',
               false
           ) AS alerta_churn
"""


def _registrar_auditoria(
    cur: Any,
    usuario_id: Optional[str],
    acao: str,
    entidade_id: str,
    dados_antes: Optional[Dict[str, Any]],
    dados_depois: Dict[str, Any],
    ip: Optional[str],
) -> None:
    cur.execute(
        """
        INSERT INTO logs_auditoria (
            usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip,
            criado_em, atualizado_em
        ) VALUES (%s, %s, 'solicitacoes_transferencia', %s, %s, %s, %s, now(), now())
        """,
        (
            usuario_id,
            acao,
            entidade_id,
            json.dumps(dados_antes, default=str) if dados_antes is not None else None,
            json.dumps(dados_depois, default=str),
            ip,
        ),
    )


class PostgresTransferenciasRepository:
    def _um(self, sql: str, params: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def _varios(self, sql: str, params: Tuple[Any, ...]) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        return self._um(f"{_ALUNO_SELECT} WHERE a.id = %s LIMIT 1", (aluno_id,))

    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        return self._um(f"{_ALUNO_SELECT} WHERE a.usuario_id = %s LIMIT 1", (usuario_id,))

    def buscar_alunos(
        self, q: str, polo_id: Optional[str], escola_id: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        like = f"%{q.lower()}%"
        conds = [
            "a.status = 'ativo'",
            "(lower(concat_ws(' ', u.nome, u.sobrenome)) LIKE %s"
            " OR lower(coalesce(a.numero_matricula, '')) LIKE %s"
            " OR lower(coalesce(u.email, '')) LIKE %s)",
        ]
        params: List[Any] = [like, like, like]
        # Alunos EAD não têm polo: qualquer unidade pode pedir a migração deles.
        if escola_id:
            conds.append("(a.modalidade = 'ead' OR a.escola_id = %s)")
            params.append(escola_id)
        elif polo_id:
            conds.append("(a.modalidade = 'ead' OR a.polo_id = %s)")
            params.append(polo_id)
        return self._varios(
            f"{_ALUNO_SELECT} WHERE {' AND '.join(conds)} ORDER BY nome LIMIT %s",
            (*params, limit),
        )

    def buscar_desistentes(self, q: str, limit: int) -> List[Dict[str, Any]]:
        like = f"%{q.lower()}%"
        # Quem está em Churn não tem mais Polo; a busca é por toda a base, com poucos campos.
        return self._varios(
            f"""
            {_ALUNO_SELECT}
            WHERE a.status = 'desistente'
              AND (lower(concat_ws(' ', u.nome, u.sobrenome)) LIKE %s
                   OR lower(coalesce(a.numero_matricula, '')) LIKE %s)
            ORDER BY nome LIMIT %s
            """,
            (like, like, limit),
        )

    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        return self._um("SELECT id, nome, status FROM polos WHERE id = %s", (polo_id,))

    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]:
        return self._um("SELECT id, nome, status, polo_id FROM escolas WHERE id = %s", (escola_id,))

    def listar_polos_ativos(self) -> List[Dict[str, Any]]:
        return self._varios("SELECT id, nome FROM polos WHERE status = 'ativo' ORDER BY nome", ())

    def listar_escolas_ativas(self, polo_id: str) -> List[Dict[str, Any]]:
        return self._varios(
            "SELECT id, nome FROM escolas WHERE polo_id = %s AND status = 'ativo' ORDER BY nome",
            (polo_id,),
        )

    def criar(self, data: Dict[str, Any], ip: Optional[str]) -> str:
        new_id = str(uuid.uuid4())
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO solicitacoes_transferencia (
                        id, aluno_id, tipo, polo_origem_id, polo_destino_id, escola_origem_id,
                        escola_destino_id, modalidade_origem, modalidade_destino, solicitado_por,
                        observacao, status, criado_em, atualizado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendente', now(), now())
                    """,
                    (
                        new_id,
                        data["aluno_id"],
                        data["tipo"],
                        data["polo_origem_id"],
                        data["polo_destino_id"],
                        data["escola_origem_id"],
                        data["escola_destino_id"],
                        data["modalidade_origem"],
                        data["modalidade_destino"],
                        data["solicitado_por"],
                        data["observacao"],
                    ),
                )
                _registrar_auditoria(
                    cur, data["solicitado_por"], "transferencia_solicitada", new_id, None, data, ip
                )
        except UniqueViolation as exc:
            raise SolicitacaoPendenteError from exc
        return new_id

    def get(self, solicitacao_id: str) -> Optional[Dict[str, Any]]:
        return self._um(
            f"{_SOLICITACAO_SELECT} {_SOLICITACAO_FROM} WHERE st.id = %s", (solicitacao_id,)
        )

    def listar(
        self,
        escopo: EscopoListagem,
        status_filter: Optional[str],
        tipo: Optional[str],
        q: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds: List[str] = []
        params: List[Any] = []
        if escopo.aluno_usuario_id:
            conds.append("a.usuario_id = %s")
            params.append(escopo.aluno_usuario_id)
        elif escopo.escola_id:
            conds.append("(st.escola_origem_id = %s OR st.escola_destino_id = %s OR st.solicitado_por = %s)")
            params.extend([escopo.escola_id, escopo.escola_id, escopo.solicitante_id])
        elif escopo.polo_id:
            conds.append("(st.polo_origem_id = %s OR st.polo_destino_id = %s OR st.solicitado_por = %s)")
            params.extend([escopo.polo_id, escopo.polo_id, escopo.solicitante_id])
        if status_filter:
            conds.append("st.status = %s")
            params.append(status_filter)
        if tipo:
            conds.append("st.tipo = %s")
            params.append(tipo)
        if q and q.strip():
            like = f"%{q.strip().lower()}%"
            conds.append(
                "(lower(concat_ws(' ', u.nome, u.sobrenome)) LIKE %s"
                " OR lower(coalesce(a.numero_matricula, '')) LIKE %s)"
            )
            params.extend([like, like])
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total {_SOLICITACAO_FROM} {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"""
                {_SOLICITACAO_SELECT} {_SOLICITACAO_FROM} {where}
                ORDER BY (st.status = 'pendente') DESC, st.criado_em DESC, st.id
                LIMIT %s OFFSET %s
                """,
                (*params, limit, offset),
            )
            return total, [dict(row) for row in cur.fetchall()]

    def resolver(
        self, solicitacao_id: str, decidir: Decisao, resolvido_por: str, ip: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM solicitacoes_transferencia WHERE id = %s FOR UPDATE",
                (solicitacao_id,),
            )
            solicitacao = cur.fetchone()
            if solicitacao is None:
                return None
            solicitacao = dict(solicitacao)

            aluno = None
            if solicitacao.get("aluno_id"):
                cur.execute(
                    f"{_ALUNO_SELECT} WHERE a.id = %s FOR UPDATE OF a",
                    (solicitacao["aluno_id"],),
                )
                row = cur.fetchone()
                aluno = dict(row) if row else None

            resolucao = decidir(solicitacao, aluno)

            if aluno and resolucao.aluno_campos is not None:
                campos = resolucao.aluno_campos
                sets = [f"{coluna} = %s" for coluna in campos]
                if resolucao.renovar_movimentacao:
                    sets.append("ultima_movimentacao_em = now()")
                cur.execute(
                    f"UPDATE alunos SET {', '.join(sets)}, atualizado_em = now() WHERE id = %s",
                    (*campos.values(), aluno["id"]),
                )
                if resolucao.atualizar_usuario:
                    cur.execute(
                        "UPDATE usuarios SET polo_id = %s, escola_id = %s, atualizado_em = now() WHERE id = %s",
                        (campos.get("polo_id"), campos.get("escola_id"), aluno["usuario_id"]),
                    )
            if aluno and resolucao.motivo_churn:
                cur.execute(
                    """
                    INSERT INTO alunos_desistentes (id, aluno_id, motivo, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, now(), now())
                    """,
                    (str(uuid.uuid4()), aluno["id"], resolucao.motivo_churn),
                )
            if aluno and resolucao.remover_turmas:
                cur.execute("DELETE FROM turma_alunos WHERE aluno_id = %s", (aluno["id"],))

            cur.execute(
                """
                UPDATE solicitacoes_transferencia
                SET status = %s, motivo_rejeicao = %s, resolvido_por = %s,
                    resolvido_em = now(), atualizado_em = now()
                WHERE id = %s
                """,
                (resolucao.status, resolucao.motivo_rejeicao, resolvido_por, solicitacao_id),
            )
            _registrar_auditoria(
                cur,
                resolvido_por,
                resolucao.acao_auditoria,
                solicitacao_id,
                {"status": solicitacao.get("status"), "aluno": aluno},
                {"status": resolucao.status, "aluno_campos": resolucao.aluno_campos},
                ip,
            )
        return self.get(solicitacao_id)


class InMemoryTransferenciasRepository:
    """Implementação em memória para testes."""

    def __init__(self) -> None:
        self.alunos: Dict[str, Dict[str, Any]] = {}
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, Dict[str, Any]] = {}
        self.solicitacoes: Dict[str, Dict[str, Any]] = {}
        self.turma_alunos: List[Dict[str, Any]] = []
        self.desistentes: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []

    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        aluno = self.alunos.get(str(aluno_id))
        return dict(aluno) if aluno else None

    def get_aluno_por_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        for aluno in self.alunos.values():
            if aluno.get("usuario_id") == str(usuario_id):
                return dict(aluno)
        return None

    def buscar_alunos(
        self, q: str, polo_id: Optional[str], escola_id: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        termo = q.lower()
        encontrados = []
        for aluno in self.alunos.values():
            if aluno.get("status") != "ativo" or termo not in aluno.get("nome", "").lower():
                continue
            if aluno.get("modalidade") != "ead":
                if escola_id and aluno.get("escola_id") != escola_id:
                    continue
                if not escola_id and polo_id and aluno.get("polo_id") != polo_id:
                    continue
            encontrados.append(dict(aluno))
        return encontrados[:limit]

    def buscar_desistentes(self, q: str, limit: int) -> List[Dict[str, Any]]:
        termo = q.lower()
        return [
            dict(aluno)
            for aluno in self.alunos.values()
            if aluno.get("status") == "desistente" and termo in aluno.get("nome", "").lower()
        ][:limit]

    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        polo = self.polos.get(str(polo_id))
        return dict(polo) if polo else None

    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]:
        escola = self.escolas.get(str(escola_id))
        return dict(escola) if escola else None

    def listar_polos_ativos(self) -> List[Dict[str, Any]]:
        return [dict(p) for p in self.polos.values() if p.get("status") == "ativo"]

    def listar_escolas_ativas(self, polo_id: str) -> List[Dict[str, Any]]:
        return [
            dict(e)
            for e in self.escolas.values()
            if e.get("polo_id") == polo_id and e.get("status") == "ativo"
        ]

    def criar(self, data: Dict[str, Any], ip: Optional[str]) -> str:
        if any(
            s["aluno_id"] == data["aluno_id"] and s["status"] == "pendente"
            for s in self.solicitacoes.values()
        ):
            raise SolicitacaoPendenteError
        new_id = str(uuid.uuid4())
        self.solicitacoes[new_id] = {
            **data,
            "id": new_id,
            "status": "pendente",
            "motivo_rejeicao": None,
            "resolvido_em": None,
            "criado_em": datetime.now(timezone.utc),
        }
        self.logs.append({"acao": "transferencia_solicitada", "entidade_id": new_id})
        return new_id

    def _com_nomes(self, solicitacao: Dict[str, Any]) -> Dict[str, Any]:
        aluno = self.alunos.get(solicitacao.get("aluno_id") or "")
        referencia = aluno.get("referencia_movimentacao") if aluno else None
        limite = datetime.now(timezone.utc) - timedelta(days=DIAS_CHURN)
        nome = lambda tabela, chave: (tabela.get(solicitacao.get(chave) or "") or {}).get("nome")
        return {
            **solicitacao,
            "aluno_nome": aluno.get("nome") if aluno else None,
            "numero_matricula": aluno.get("numero_matricula") if aluno else None,
            "polo_origem_nome": nome(self.polos, "polo_origem_id"),
            "polo_destino_nome": nome(self.polos, "polo_destino_id"),
            "escola_origem_nome": nome(self.escolas, "escola_origem_id"),
            "escola_destino_nome": nome(self.escolas, "escola_destino_id"),
            "alerta_churn": bool(
                solicitacao["status"] == "pendente"
                and solicitacao["tipo"] != "reingresso"
                and referencia
                and referencia < limite
            ),
        }

    def get(self, solicitacao_id: str) -> Optional[Dict[str, Any]]:
        solicitacao = self.solicitacoes.get(str(solicitacao_id))
        return self._com_nomes(solicitacao) if solicitacao else None

    def _no_escopo(self, solicitacao: Dict[str, Any], escopo: EscopoListagem) -> bool:
        if escopo.aluno_usuario_id:
            aluno = self.alunos.get(solicitacao.get("aluno_id") or "") or {}
            return aluno.get("usuario_id") == escopo.aluno_usuario_id
        if escopo.escola_id:
            return (
                escopo.escola_id in (solicitacao.get("escola_origem_id"), solicitacao.get("escola_destino_id"))
                or solicitacao.get("solicitado_por") == escopo.solicitante_id
            )
        if escopo.polo_id:
            return (
                escopo.polo_id in (solicitacao.get("polo_origem_id"), solicitacao.get("polo_destino_id"))
                or solicitacao.get("solicitado_por") == escopo.solicitante_id
            )
        return True

    def listar(
        self,
        escopo: EscopoListagem,
        status_filter: Optional[str],
        tipo: Optional[str],
        q: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        itens = [self._com_nomes(s) for s in self.solicitacoes.values() if self._no_escopo(s, escopo)]
        if status_filter:
            itens = [s for s in itens if s["status"] == status_filter]
        if tipo:
            itens = [s for s in itens if s["tipo"] == tipo]
        if q and q.strip():
            termo = q.strip().lower()
            itens = [s for s in itens if termo in (s.get("aluno_nome") or "").lower()]
        itens.sort(key=lambda s: s["criado_em"], reverse=True)
        itens.sort(key=lambda s: s["status"] != "pendente")
        return len(itens), itens[offset : offset + limit]

    def resolver(
        self, solicitacao_id: str, decidir: Decisao, resolvido_por: str, ip: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        solicitacao = self.solicitacoes.get(str(solicitacao_id))
        if solicitacao is None:
            return None
        aluno = self.alunos.get(solicitacao.get("aluno_id") or "")
        resolucao = decidir(dict(solicitacao), dict(aluno) if aluno else None)

        if aluno and resolucao.aluno_campos is not None:
            aluno.update(resolucao.aluno_campos)
            if resolucao.renovar_movimentacao:
                aluno["referencia_movimentacao"] = datetime.now(timezone.utc)
            if resolucao.atualizar_usuario:
                self.usuarios.setdefault(aluno["usuario_id"], {}).update(
                    {
                        "polo_id": resolucao.aluno_campos.get("polo_id"),
                        "escola_id": resolucao.aluno_campos.get("escola_id"),
                    }
                )
        if aluno and resolucao.motivo_churn:
            self.desistentes.append({"aluno_id": aluno["id"], "motivo": resolucao.motivo_churn})
        if aluno and resolucao.remover_turmas:
            self.turma_alunos = [v for v in self.turma_alunos if v["aluno_id"] != aluno["id"]]

        solicitacao.update(
            status=resolucao.status,
            motivo_rejeicao=resolucao.motivo_rejeicao,
            resolvido_por=resolvido_por,
            resolvido_em=datetime.now(timezone.utc),
        )
        self.logs.append({"acao": resolucao.acao_auditoria, "entidade_id": solicitacao_id})
        return self.get(solicitacao_id)


_repo_instance: Optional[TransferenciasRepositoryInterface] = None


def get_transferencias_repository() -> TransferenciasRepositoryInterface:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = PostgresTransferenciasRepository()
    return _repo_instance


def set_transferencias_repository(repo: Optional[TransferenciasRepositoryInterface]) -> None:
    global _repo_instance
    _repo_instance = repo
