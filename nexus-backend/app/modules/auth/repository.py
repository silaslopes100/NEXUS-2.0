"""Repositórios de dados para o módulo de autenticação."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol

from app.core.database import get_db_cursor


class AuthRepositoryInterface(Protocol):
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]: ...
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    def get_usuario_permissoes(self, user_id: str) -> List[str]: ...
    def update_user_password(
        self, user_id: str, senha_hash: str, senha_algoritmo: str = "argon2id"
    ) -> None: ...
    def update_user_last_login(self, user_id: str) -> None: ...
    def count_recent_failed_attempts(
        self, email: str, ip: Optional[str] = None, minutes: int = 15
    ) -> int: ...
    def record_login_attempt(
        self,
        usuario_id: Optional[str],
        email: Optional[str],
        ip: Optional[str],
        sucesso: bool,
    ) -> None: ...
    def create_refresh_token(
        self,
        usuario_id: str,
        token_hash: str,
        expira_em: datetime,
        criado_por_ip: Optional[str] = None,
    ) -> None: ...
    def get_refresh_token(self, token_hash: str) -> Optional[Dict[str, Any]]: ...
    def revoke_refresh_token(self, token_hash: str) -> None: ...
    def revoke_all_user_refresh_tokens(self, usuario_id: str) -> None: ...
    def create_password_reset(
        self, usuario_id: str, token_hash: str, expira_em: datetime
    ) -> None: ...
    def get_password_reset(self, token_hash: str) -> Optional[Dict[str, Any]]: ...
    def mark_password_reset_used(self, token_hash: str) -> None: ...
    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str = "usuarios",
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None: ...


class PostgresAuthRepository:
    """Implementação do repositório de autenticação no PostgreSQL."""

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT u.id, u.nome, u.sobrenome, u.email, u.cpf, u.senha_hash, u.senha_algoritmo,
                   u.telefone, u.celular, u.foto_url, u.status, u.ultimo_login_em,
                   u.polo_id, u.escola_id, u.perfil_id,
                   p.nome as perfil_nome, p.descricao as perfil_descricao
            FROM usuarios u
            LEFT JOIN perfis p ON u.perfil_id = p.id
            WHERE lower(u.email) = lower(%s)
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (email.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT u.id, u.nome, u.sobrenome, u.email, u.cpf, u.senha_hash, u.senha_algoritmo,
                   u.telefone, u.celular, u.foto_url, u.status, u.ultimo_login_em,
                   u.polo_id, u.escola_id, u.perfil_id,
                   p.nome as perfil_nome, p.descricao as perfil_descricao
            FROM usuarios u
            LEFT JOIN perfis p ON u.perfil_id = p.id
            WHERE u.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(user_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_usuario_permissoes(self, user_id: str) -> List[str]:
        sql = """
            SELECT p.chave
            FROM usuario_permissoes up
            JOIN permissoes p ON up.permissao_id = p.id
            WHERE up.usuario_id = %s
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(user_id),))
            rows = cur.fetchall()
            return [r["chave"] for r in rows]

    def update_user_password(
        self, user_id: str, senha_hash: str, senha_algoritmo: str = "argon2id"
    ) -> None:
        sql = """
            UPDATE usuarios
            SET senha_hash = %s, senha_algoritmo = %s, atualizado_em = now()
            WHERE id = %s
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (senha_hash, senha_algoritmo, str(user_id)))

    def update_user_last_login(self, user_id: str) -> None:
        sql = """
            UPDATE usuarios
            SET ultimo_login_em = now(), atualizado_em = now()
            WHERE id = %s
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(user_id),))

    def count_recent_failed_attempts(
        self, email: str, ip: Optional[str] = None, minutes: int = 15
    ) -> int:
        sql = """
            SELECT COUNT(*) as count
            FROM login_tentativas
            WHERE (lower(email) = lower(%s) OR (%s IS NOT NULL AND ip = %s))
              AND sucesso = false
              AND criado_em >= now() - (%s || ' minutes')::interval
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (email.strip(), ip, ip, str(minutes)))
            row = cur.fetchone()
            return int(row["count"]) if row else 0

    def record_login_attempt(
        self,
        usuario_id: Optional[str],
        email: Optional[str],
        ip: Optional[str],
        sucesso: bool,
    ) -> None:
        sql = """
            INSERT INTO login_tentativas (usuario_id, email, ip, sucesso, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (usuario_id, email, ip, sucesso))

    def create_refresh_token(
        self,
        usuario_id: str,
        token_hash: str,
        expira_em: datetime,
        criado_por_ip: Optional[str] = None,
    ) -> None:
        sql = """
            INSERT INTO refresh_tokens (usuario_id, token_hash, expira_em, criado_por_ip, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(usuario_id), token_hash, expira_em, criado_por_ip))

    def get_refresh_token(self, token_hash: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT id, usuario_id, token_hash, expira_em, revogado_em, criado_por_ip, criado_em
            FROM refresh_tokens
            WHERE token_hash = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (token_hash,))
            row = cur.fetchone()
            return dict(row) if row else None

    def revoke_refresh_token(self, token_hash: str) -> None:
        sql = """
            UPDATE refresh_tokens
            SET revogado_em = now(), atualizado_em = now()
            WHERE token_hash = %s AND revogado_em IS NULL
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (token_hash,))

    def revoke_all_user_refresh_tokens(self, usuario_id: str) -> None:
        sql = """
            UPDATE refresh_tokens
            SET revogado_em = now(), atualizado_em = now()
            WHERE usuario_id = %s AND revogado_em IS NULL
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(usuario_id),))

    def create_password_reset(
        self, usuario_id: str, token_hash: str, expira_em: datetime
    ) -> None:
        sql = """
            INSERT INTO password_reset (usuario_id, token_hash, expira_em, criado_em, atualizado_em)
            VALUES (%s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(usuario_id), token_hash, expira_em))

    def get_password_reset(self, token_hash: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT id, usuario_id, token_hash, expira_em, usado_em, criado_em
            FROM password_reset
            WHERE token_hash = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (token_hash,))
            row = cur.fetchone()
            return dict(row) if row else None

    def mark_password_reset_used(self, token_hash: str) -> None:
        sql = """
            UPDATE password_reset
            SET usado_em = now(), atualizado_em = now()
            WHERE token_hash = %s
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (token_hash,))

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str = "usuarios",
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None:
        sql = """
            INSERT INTO logs_auditoria (
                usuario_id, acao, entidade, entidade_id, dados_antes, dados_depois, ip, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    str(usuario_id) if usuario_id else None,
                    acao,
                    entidade,
                    str(entidade_id) if entidade_id else None,
                    json.dumps(dados_antes) if dados_antes else None,
                    json.dumps(dados_depois) if dados_depois else None,
                    ip,
                ),
            )


class InMemoryAuthRepository:
    """Implementação em memória para testes unitários isolados e de alta performance."""

    def __init__(self) -> None:
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.perfis: Dict[str, Dict[str, Any]] = {
            "p-admin": {"id": "p-admin", "nome": "admin", "descricao": "Administrador"},
            "p-polo": {"id": "p-polo", "nome": "polo", "descricao": "Gestor de Polo"},
            "p-escola": {"id": "p-escola", "nome": "escola", "descricao": "Gestor de Escola"},
            "p-prof": {"id": "p-prof", "nome": "professor", "descricao": "Professor"},
            "p-aluno": {"id": "p-aluno", "nome": "aluno", "descricao": "Aluno"},
        }
        self.permissoes: Dict[str, Dict[str, Any]] = {
            "perm-vendas": {"id": "perm-vendas", "chave": "vendas", "descricao": "Acesso a vendas"},
            "perm-fin": {"id": "perm-fin", "chave": "financeiro", "descricao": "Acesso financeiro"},
            "perm-acad": {"id": "perm-acad", "chave": "academico", "descricao": "Acesso acadêmico"},
        }
        self.usuario_permissoes: List[Dict[str, str]] = []
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}  # token_hash -> dict
        self.password_reset: Dict[str, Dict[str, Any]] = {}  # token_hash -> dict
        self.login_tentativas: List[Dict[str, Any]] = []
        self.logs_auditoria: List[Dict[str, Any]] = []

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email_clean = email.strip().lower()
        for u in self.usuarios.values():
            if u.get("email") and u["email"].strip().lower() == email_clean:
                out = u.copy()
                perfil_id = u.get("perfil_id")
                if perfil_id and perfil_id in self.perfis:
                    out["perfil_nome"] = self.perfis[perfil_id]["nome"]
                    out["perfil_descricao"] = self.perfis[perfil_id]["descricao"]
                return out
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        u = self.usuarios.get(str(user_id))
        if not u:
            return None
        out = u.copy()
        perfil_id = u.get("perfil_id")
        if perfil_id and perfil_id in self.perfis:
            out["perfil_nome"] = self.perfis[perfil_id]["nome"]
            out["perfil_descricao"] = self.perfis[perfil_id]["descricao"]
        return out

    def get_usuario_permissoes(self, user_id: str) -> List[str]:
        uid = str(user_id)
        perm_ids = [up["permissao_id"] for up in self.usuario_permissoes if up["usuario_id"] == uid]
        return [self.permissoes[pid]["chave"] for pid in perm_ids if pid in self.permissoes]

    def update_user_password(
        self, user_id: str, senha_hash: str, senha_algoritmo: str = "argon2id"
    ) -> None:
        uid = str(user_id)
        if uid in self.usuarios:
            self.usuarios[uid]["senha_hash"] = senha_hash
            self.usuarios[uid]["senha_algoritmo"] = senha_algoritmo
            self.usuarios[uid]["atualizado_em"] = datetime.now(timezone.utc)

    def update_user_last_login(self, user_id: str) -> None:
        uid = str(user_id)
        if uid in self.usuarios:
            self.usuarios[uid]["ultimo_login_em"] = datetime.now(timezone.utc)
            self.usuarios[uid]["atualizado_em"] = datetime.now(timezone.utc)

    def count_recent_failed_attempts(
        self, email: str, ip: Optional[str] = None, minutes: int = 15
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        email_clean = email.strip().lower()
        count = 0
        for t in self.login_tentativas:
            if t["sucesso"]:
                continue
            if t["criado_em"] < cutoff:
                continue
            t_email = (t.get("email") or "").strip().lower()
            t_ip = t.get("ip")
            if t_email == email_clean or (ip and t_ip == ip):
                count += 1
        return count

    def record_login_attempt(
        self,
        usuario_id: Optional[str],
        email: Optional[str],
        ip: Optional[str],
        sucesso: bool,
    ) -> None:
        self.login_tentativas.append({
            "id": str(uuid.uuid4()),
            "usuario_id": str(usuario_id) if usuario_id else None,
            "email": email,
            "ip": ip,
            "sucesso": sucesso,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        })

    def create_refresh_token(
        self,
        usuario_id: str,
        token_hash: str,
        expira_em: datetime,
        criado_por_ip: Optional[str] = None,
    ) -> None:
        self.refresh_tokens[token_hash] = {
            "id": str(uuid.uuid4()),
            "usuario_id": str(usuario_id),
            "token_hash": token_hash,
            "expira_em": expira_em,
            "revogado_em": None,
            "criado_por_ip": criado_por_ip,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }

    def get_refresh_token(self, token_hash: str) -> Optional[Dict[str, Any]]:
        token_data = self.refresh_tokens.get(token_hash)
        return token_data.copy() if token_data else None

    def revoke_refresh_token(self, token_hash: str) -> None:
        if token_hash in self.refresh_tokens:
            self.refresh_tokens[token_hash]["revogado_em"] = datetime.now(timezone.utc)
            self.refresh_tokens[token_hash]["atualizado_em"] = datetime.now(timezone.utc)

    def revoke_all_user_refresh_tokens(self, usuario_id: str) -> None:
        uid = str(usuario_id)
        now = datetime.now(timezone.utc)
        for t in self.refresh_tokens.values():
            if t["usuario_id"] == uid and t["revogado_em"] is None:
                t["revogado_em"] = now
                t["atualizado_em"] = now

    def create_password_reset(
        self, usuario_id: str, token_hash: str, expira_em: datetime
    ) -> None:
        self.password_reset[token_hash] = {
            "id": str(uuid.uuid4()),
            "usuario_id": str(usuario_id),
            "token_hash": token_hash,
            "expira_em": expira_em,
            "usado_em": None,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }

    def get_password_reset(self, token_hash: str) -> Optional[Dict[str, Any]]:
        pr = self.password_reset.get(token_hash)
        return pr.copy() if pr else None

    def mark_password_reset_used(self, token_hash: str) -> None:
        if token_hash in self.password_reset:
            self.password_reset[token_hash]["usado_em"] = datetime.now(timezone.utc)
            self.password_reset[token_hash]["atualizado_em"] = datetime.now(timezone.utc)

    def record_audit_log(
        self,
        usuario_id: Optional[str],
        acao: str,
        entidade: str = "usuarios",
        entidade_id: Optional[str] = None,
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> None:
        self.logs_auditoria.append({
            "id": str(uuid.uuid4()),
            "usuario_id": str(usuario_id) if usuario_id else None,
            "acao": acao,
            "entidade": entidade,
            "entidade_id": str(entidade_id) if entidade_id else None,
            "dados_antes": dados_antes,
            "dados_depois": dados_depois,
            "ip": ip,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        })


_default_repo: Optional[AuthRepositoryInterface] = None


def get_auth_repository() -> AuthRepositoryInterface:
    """Retorna o repositório padrão de autenticação."""
    global _default_repo
    if _default_repo is None:
        _default_repo = PostgresAuthRepository()
    return _default_repo


def set_auth_repository(repo: AuthRepositoryInterface) -> None:
    """Configura o repositório de autenticação (usado para testes ou injeção)."""
    global _default_repo
    _default_repo = repo
