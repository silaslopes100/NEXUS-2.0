"""Repositório de dados do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.database import get_db_cursor

_SELECT_BASE = """
    SELECT prof.*, u.nome, u.email,
           p.nome AS polo_nome, e.nome AS escola_nome
    FROM professores prof
    LEFT JOIN usuarios u ON u.id = prof.usuario_id
    LEFT JOIN polos p ON p.id = prof.polo_id
    LEFT JOIN escolas e ON e.id = prof.escola_id
"""


class ProfessoresRepositoryInterface(Protocol):
    def list_professores(
        self,
        search: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        disciplina: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]: ...

    def get_professor_by_usuario_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...

    def create_professor(self, data: Dict[str, Any]) -> str: ...

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None: ...

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str,
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None: ...


class PostgresProfessoresRepository:
    """Implementação PostgreSQL (SQL crudo via psycopg2, padrão do NEXUS 2.0)."""

    # ---------- Listagem ----------

    def list_professores(
        self,
        search: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        disciplina: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds: List[str] = []
        params: List[Any] = []

        if search and search.strip():
            conds.append("(lower(u.nome) LIKE %s OR lower(u.sobrenome) LIKE %s OR lower(u.email) LIKE %s)")
            like = f"%{search.strip().lower()}%"
            params.extend([like, like, like])
        if polo_id:
            conds.append("prof.polo_id = %s")
            params.append(str(polo_id))
        if escola_id:
            conds.append("prof.escola_id = %s")
            params.append(str(escola_id))
        if disciplina and disciplina.strip():
            conds.append("prof.materias::text ILIKE %s")
            params.append(f"%{disciplina.strip()}%")
        if status_filter:
            conds.append("prof.status = %s")
            params.append(status_filter)

        where = "WHERE " + " AND ".join(conds) if conds else ""
        count_sql = (
            "SELECT COUNT(*) AS total FROM professores prof "
            "LEFT JOIN usuarios u ON u.id = prof.usuario_id"
        )

        with get_db_cursor() as cur:
            cur.execute(f"{count_sql} {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"{_SELECT_BASE} {where} ORDER BY u.nome ASC, u.email ASC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    # ---------- Registro ----------

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(f"{_SELECT_BASE} WHERE prof.id = %s LIMIT 1", (str(professor_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_professor_by_usuario_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(f"{_SELECT_BASE} WHERE prof.usuario_id = %s LIMIT 1", (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome, sobrenome, email, status FROM usuarios WHERE id = %s LIMIT 1", (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_professor(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO professores (
                    id, usuario_id, polo_id, escola_id, materias, data_inicio,
                    quantidade_aulas, horas_totais, valor_hora_aula, pix,
                    conteudo_programatico, status, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo', now(), now())
                """,
                (
                    new_id,
                    str(data["usuario_id"]),
                    data.get("polo_id"),
                    data.get("escola_id"),
                    json.dumps(data.get("materias") or []),
                    data.get("data_inicio"),
                    data.get("quantidade_aulas") or 0,
                    data.get("horas_totais") or 0,
                    data.get("valor_hora_aula"),
                    data.get("pix"),
                    data.get("conteudo_programatico"),
                ),
            )
        return new_id

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return
        fields: List[str] = []
        params: List[Any] = []
        for key, value in data.items():
            if key == "materias":
                fields.append("materias = %s")
                params.append(json.dumps(value or []))
            else:
                fields.append(f"{key} = %s")
                params.append(value)
        fields.append("atualizado_em = now()")
        params.append(str(professor_id))
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE professores SET {', '.join(fields)} WHERE id = %s",
                tuple(params),
            )

    # ---------- Auditoria ----------

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str,
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO logs_auditoria (
                    usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    str(usuario_id) if usuario_id else None,
                    acao,
                    entidade,
                    str(entidade_id) if entidade_id else None,
                    json.dumps(dados_antes) if dados_antes is not None else None,
                    json.dumps(dados_depois) if dados_depois is not None else None,
                    ip,
                ),
            )


class InMemoryProfessoresRepository:
    """Implementação em memória para testes unitários isolados."""

    def __init__(self) -> None:
        self.professores: Dict[str, Dict[str, Any]] = {}
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, Dict[str, Any]] = {}
        self.logs_auditoria: List[Dict[str, Any]] = []

    def _join(self, row: Dict[str, Any]) -> Dict[str, Any]:
        usuario = self.usuarios.get(str(row.get("usuario_id")), {})
        polo = self.polos.get(str(row.get("polo_id")), {}) if row.get("polo_id") else {}
        escola = self.escolas.get(str(row.get("escola_id")), {}) if row.get("escola_id") else {}
        return {
            **row,
            "nome": usuario.get("nome"),
            "email": usuario.get("email"),
            "polo_nome": polo.get("nome"),
            "escola_nome": escola.get("nome"),
        }

    def list_professores(
        self,
        search: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        disciplina: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        items = [self._join(p) for p in self.professores.values()]
        if search and search.strip():
            termo = search.strip().lower()
            items = [
                p
                for p in items
                if termo in str(p.get("nome") or "").lower()
                or termo in str(p.get("email") or "").lower()
            ]
        if polo_id:
            items = [p for p in items if str(p.get("polo_id")) == str(polo_id)]
        if escola_id:
            items = [p for p in items if str(p.get("escola_id")) == str(escola_id)]
        if disciplina and disciplina.strip():
            termo = disciplina.strip().lower()
            items = [p for p in items if any(termo in str(m).lower() for m in (p.get("materias") or []))]
        if status_filter:
            items = [p for p in items if p.get("status") == status_filter]
        items = sorted(items, key=lambda p: str(p.get("nome") or ""))
        return len(items), items[offset : offset + limit]

    def get_professor(self, professor_id: str) -> Optional[Dict[str, Any]]:
        row = self.professores.get(str(professor_id))
        return self._join(row) if row else None

    def get_professor_by_usuario_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        for row in self.professores.values():
            if str(row.get("usuario_id")) == str(usuario_id):
                return self._join(row)
        return None

    def get_usuario_by_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        row = self.usuarios.get(str(usuario_id))
        return dict(row) if row else None

    def create_professor(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        self.professores[new_id] = {
            "id": new_id,
            "status": "ativo",
            "materias": list(data.get("materias") or []),
            "quantidade_aulas": data.get("quantidade_aulas") or 0,
            "horas_totais": data.get("horas_totais") or 0,
            "criado_em": None,
            "atualizado_em": None,
            **{k: v for k, v in data.items() if k not in ("materias", "quantidade_aulas", "horas_totais")},
        }
        return new_id

    def update_professor(self, professor_id: str, data: Dict[str, Any]) -> None:
        row = self.professores.get(str(professor_id))
        if row:
            row.update(data)

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str,
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None:
        self.logs_auditoria.append(
            {
                "usuario_id": usuario_id,
                "acao": acao,
                "entidade": entidade,
                "entidade_id": entidade_id,
                "dados_antes": dados_antes,
                "dados_depois": dados_depois,
                "ip": ip,
            }
        )


_repo_instance: Optional[ProfessoresRepositoryInterface] = None


def get_professores_repository() -> ProfessoresRepositoryInterface:
    """Provedor padrão do repositório (PostgreSQL em produção)."""
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = PostgresProfessoresRepository()
    return _repo_instance


def set_professores_repository(repo: ProfessoresRepositoryInterface) -> None:
    """Permite injeção de um repositório alternativo (ex: InMemory nos testes)."""
    global _repo_instance
    _repo_instance = repo
