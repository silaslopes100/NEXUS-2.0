"""Persistência das solicitações Escola → Polo e das Notas de Prestação de Contas."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from app.core.database import get_db_cursor


def _limpar(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    out = {}
    for k, v in dict(row).items():
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, Decimal):
            v = float(v)
        out[k] = v
    return out


def _uuid_valido(valor: Any) -> bool:
    try:
        uuid.UUID(str(valor))
        return True
    except ValueError:
        return False


class SolicitacoesRepositoryInterface(Protocol):
    def disciplinas(self, ids: List[str]) -> Dict[str, Dict[str, Any]]: ...
    def criar(self, dados: Dict[str, Any], itens: List[Dict[str, Any]]) -> str: ...
    def get(self, solicitacao_id: str) -> Optional[Dict[str, Any]]: ...
    def listar(self, *, escola_id: Optional[str] = None, polo_id: Optional[str] = None,
               status: Optional[str] = None) -> List[Dict[str, Any]]: ...
    def resolver(self, solicitacao_id: str, *, status: str, resolvido_por: Optional[str],
                 motivo_recusa: Optional[str] = None, atendidos: Optional[Dict[str, int]] = None) -> bool: ...
    def criar_nota(self, dados: Dict[str, Any]) -> str: ...
    def get_nota(self, nota_id: str) -> Optional[Dict[str, Any]]: ...
    def marcar_repasse(self, nota_id: str, usuario_id: Optional[str]) -> bool: ...


_SELECT = """
    SELECT s.*, e.nome AS escola_nome, p.nome AS polo_nome,
           n.id AS nota_id, n.numero AS nota_numero, n.status AS nota_status,
           n.valor_total AS nota_valor_total, n.vencimento AS nota_vencimento, n.repasse_em AS nota_repasse_em
      FROM solicitacoes_unidade s
      JOIN escolas e ON e.id = s.escola_id
      JOIN polos p ON p.id = s.polo_id
      LEFT JOIN notas_prestacao_contas n ON n.solicitacao_id = s.id AND n.status <> 'cancelada'
"""


class PostgresSolicitacoesRepository:
    def disciplinas(self, ids):
        ids = [str(i) for i in ids if _uuid_valido(i)]
        if not ids:
            return {}
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome, preco, curso_id, ativo FROM disciplinas WHERE id::text = ANY(%s)", (ids,))
            return {str(r["id"]): _limpar(r) for r in cur.fetchall()}

    def _itens(self, cur, ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        if not ids:
            return {}
        cur.execute(
            """SELECT i.*, d.nome AS disciplina_nome FROM solicitacoes_unidade_itens i
                 JOIN disciplinas d ON d.id = i.disciplina_id
                WHERE i.solicitacao_id::text = ANY(%s) ORDER BY d.nome""",
            (ids,),
        )
        out: Dict[str, List[Dict[str, Any]]] = {}
        for r in (_limpar(x) for x in cur.fetchall()):
            out.setdefault(r["solicitacao_id"], []).append(r)
        return out

    def criar(self, dados, itens):
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO solicitacoes_unidade (escola_id, polo_id, solicitante_id, observacao)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (dados["escola_id"], dados["polo_id"], dados.get("solicitante_id"), dados.get("observacao")),
            )
            sid = str(cur.fetchone()["id"])
            for item in itens:
                cur.execute(
                    """INSERT INTO solicitacoes_unidade_itens (solicitacao_id, disciplina_id, quantidade, valor_unitario)
                       VALUES (%s, %s, %s, %s)""",
                    (sid, item["disciplina_id"], item["quantidade"], item["valor_unitario"]),
                )
            return sid

    def get(self, solicitacao_id):
        if not _uuid_valido(solicitacao_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(_SELECT + " WHERE s.id = %s", (str(solicitacao_id),))
            row = _limpar(cur.fetchone())
            if row:
                row["itens"] = self._itens(cur, [row["id"]]).get(row["id"], [])
            return row

    def listar(self, *, escola_id=None, polo_id=None, status=None):
        conds, params = [], []
        if escola_id:
            conds.append("s.escola_id = %s")
            params.append(str(escola_id))
        if polo_id:
            conds.append("s.polo_id = %s")
            params.append(str(polo_id))
        if status:
            conds.append("s.status = %s")
            params.append(status)
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        with get_db_cursor() as cur:
            cur.execute(_SELECT + where + " ORDER BY s.criado_em DESC LIMIT 300", tuple(params))
            linhas = [_limpar(r) for r in cur.fetchall()]
            itens = self._itens(cur, [r["id"] for r in linhas])
            for r in linhas:
                r["itens"] = itens.get(r["id"], [])
            return linhas

    def resolver(self, solicitacao_id, *, status, resolvido_por, motivo_recusa=None, atendidos=None):
        """Só sai de 'pendente' uma vez (evita atender duas vezes em cliques simultâneos)."""
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE solicitacoes_unidade SET status = %s, motivo_recusa = %s, resolvido_por = %s,
                          resolvido_em = now(), atualizado_em = now()
                    WHERE id = %s AND status = 'pendente'""",
                (status, motivo_recusa, resolvido_por, str(solicitacao_id)),
            )
            if cur.rowcount == 0:
                return False
            for item_id, qtd in (atendidos or {}).items():
                cur.execute("UPDATE solicitacoes_unidade_itens SET quantidade_atendida = %s WHERE id = %s AND solicitacao_id = %s",
                            (qtd, item_id, str(solicitacao_id)))
            return True

    def criar_nota(self, dados):
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO notas_prestacao_contas (solicitacao_id, polo_id, escola_id, valor_total, vencimento, emitida_por)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (dados["solicitacao_id"], dados["polo_id"], dados["escola_id"], dados["valor_total"],
                 dados["vencimento"], dados.get("emitida_por")),
            )
            return str(cur.fetchone()["id"])

    def get_nota(self, nota_id):
        if not _uuid_valido(nota_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM notas_prestacao_contas WHERE id = %s", (str(nota_id),))
            return _limpar(cur.fetchone())

    def marcar_repasse(self, nota_id, usuario_id):
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE notas_prestacao_contas SET status = 'repasse_recebido', repasse_em = now(),
                          repasse_confirmado_por = %s WHERE id = %s AND status = 'emitida'""",
                (usuario_id, str(nota_id)),
            )
            return cur.rowcount > 0


class InMemorySolicitacoesRepository:
    def __init__(self) -> None:
        self.disciplinas_db: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, str] = {}
        self.polos: Dict[str, str] = {}
        self.solicitacoes: Dict[str, Dict[str, Any]] = {}
        self.notas: Dict[str, Dict[str, Any]] = {}
        self._seq = 0

    def disciplinas(self, ids):
        return {i: {"id": i, **self.disciplinas_db[i]} for i in ids if i in self.disciplinas_db}

    def criar(self, dados, itens):
        self._seq += 1
        sid = str(uuid.uuid4())
        self.solicitacoes[sid] = {
            **dados, "id": sid, "numero": f"SOL-{date.today().year}-{self._seq:06d}", "status": "pendente",
            "motivo_recusa": None, "criado_em": datetime.now(timezone.utc),
            "itens": [{**i, "id": str(uuid.uuid4()), "solicitacao_id": sid, "quantidade_atendida": 0,
                       "disciplina_nome": self.disciplinas_db.get(i["disciplina_id"], {}).get("nome")} for i in itens],
        }
        return sid

    def _com_nota(self, s: Dict[str, Any]) -> Dict[str, Any]:
        nota = next((n for n in self.notas.values() if n["solicitacao_id"] == s["id"] and n["status"] != "cancelada"), None)
        return {**s, "escola_nome": self.escolas.get(s["escola_id"]), "polo_nome": self.polos.get(s["polo_id"]),
                "itens": [dict(i) for i in s["itens"]],
                "nota_id": nota and nota["id"], "nota_numero": nota and nota["numero"],
                "nota_status": nota and nota["status"], "nota_valor_total": nota and nota["valor_total"],
                "nota_vencimento": nota and nota["vencimento"], "nota_repasse_em": nota and nota.get("repasse_em")}

    def get(self, solicitacao_id):
        s = self.solicitacoes.get(solicitacao_id)
        return self._com_nota(s) if s else None

    def listar(self, *, escola_id=None, polo_id=None, status=None):
        return [self._com_nota(s) for s in reversed(list(self.solicitacoes.values()))
                if (not escola_id or s["escola_id"] == escola_id) and (not polo_id or s["polo_id"] == polo_id)
                and (not status or s["status"] == status)]

    def resolver(self, solicitacao_id, *, status, resolvido_por, motivo_recusa=None, atendidos=None):
        s = self.solicitacoes.get(solicitacao_id)
        if not s or s["status"] != "pendente":
            return False
        s.update(status=status, resolvido_por=resolvido_por, motivo_recusa=motivo_recusa,
                 resolvido_em=datetime.now(timezone.utc))
        for item in s["itens"]:
            if item["id"] in (atendidos or {}):
                item["quantidade_atendida"] = atendidos[item["id"]]
        return True

    def criar_nota(self, dados):
        nid = str(uuid.uuid4())
        self.notas[nid] = {**dados, "id": nid, "numero": f"NPC-{date.today().year}-{len(self.notas) + 1:06d}",
                           "status": "emitida", "criado_em": datetime.now(timezone.utc)}
        return nid

    def get_nota(self, nota_id):
        return dict(self.notas[nota_id]) if nota_id in self.notas else None

    def marcar_repasse(self, nota_id, usuario_id):
        n = self.notas.get(nota_id)
        if not n or n["status"] != "emitida":
            return False
        n.update(status="repasse_recebido", repasse_em=datetime.now(timezone.utc), repasse_confirmado_por=usuario_id)
        return True


_repo: Optional[SolicitacoesRepositoryInterface] = None


def get_solicitacoes_repository() -> SolicitacoesRepositoryInterface:
    global _repo
    if _repo is None:
        _repo = PostgresSolicitacoesRepository()
    return _repo


def set_solicitacoes_repository(repo: Optional[SolicitacoesRepositoryInterface]) -> None:
    global _repo
    _repo = repo
