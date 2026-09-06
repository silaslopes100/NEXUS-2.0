"""Repositório de dados para o módulo administrativo do NEXUS 2.0."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.database import get_db_cursor


class AdminRepositoryInterface(Protocol):
    # Usuários
    def list_users(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]: ...
    def get_user_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]: ...
    def create_user(self, data: Dict[str, Any]) -> str: ...
    def update_user(self, user_id: str, data: Dict[str, Any]) -> None: ...
    def delete_user(self, user_id: str) -> None: ...
    def get_user_permissions(self, user_id: str) -> List[str]: ...
    def set_user_permissions(self, user_id: str, permission_keys: List[str]) -> None: ...

    # Perfis & Permissões
    def list_perfis(self) -> List[Dict[str, Any]]: ...
    def get_perfil_by_id(self, perfil_id: str) -> Optional[Dict[str, Any]]: ...
    def get_perfil_by_nome(self, nome: str) -> Optional[Dict[str, Any]]: ...
    def list_permissoes(self) -> List[Dict[str, Any]]: ...
    def ensure_permissoes(self, keys: List[str]) -> None: ...

    # Logs de Auditoria
    def list_audit_logs(
        self,
        usuario_id: Optional[str] = None,
        entidade: Optional[str] = None,
        acao: Optional[str] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
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

    # Configurações
    def list_configuracoes(self) -> List[Dict[str, Any]]: ...
    def get_configuracao(self, chave: str) -> Optional[Dict[str, Any]]: ...
    def set_configuracao(self, chave: str, valor: Any) -> Dict[str, Any]: ...

    # ETL Sync Runs
    def list_etl_sync_runs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_etl_sync_run(self, run_id: int) -> Optional[Dict[str, Any]]: ...
    def list_etl_erros(
        self,
        execucao_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...


class PostgresAdminRepository:
    """Implementação PostgreSQL das operações administrativas."""

    def list_users(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []

        if query:
            q = f"%{query.strip().lower()}%"
            conditions.append("(lower(u.nome) LIKE %s OR lower(u.sobrenome) LIKE %s OR lower(u.email) LIKE %s OR u.cpf LIKE %s)")
            params.extend([q, q, q, q])

        if perfil_id:
            conditions.append("u.perfil_id = %s")
            params.append(str(perfil_id))

        if perfil_nome:
            conditions.append("lower(p.nome) = lower(%s)")
            params.append(perfil_nome.strip())

        if status:
            conditions.append("u.status = %s")
            params.append(status.strip())

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"""
            SELECT COUNT(*) as total
            FROM usuarios u
            LEFT JOIN perfis p ON u.perfil_id = p.id
            {where_clause}
        """

        data_sql = f"""
            SELECT u.id, u.nome, u.sobrenome, u.email, u.cpf, u.telefone, u.celular,
                   u.foto_url, u.status, u.ultimo_login_em, u.polo_id, u.escola_id,
                   u.perfil_id, p.nome as perfil_nome, u.criado_em, u.atualizado_em
            FROM usuarios u
            LEFT JOIN perfis p ON u.perfil_id = p.id
            {where_clause}
            ORDER BY u.criado_em DESC
            LIMIT %s OFFSET %s
        """

        with get_db_cursor() as cur:
            cur.execute(count_sql, tuple(params))
            count_row = cur.fetchone()
            total = int(count_row["total"]) if count_row else 0

            cur.execute(data_sql, tuple(params + [limit, offset]))
            rows = cur.fetchall()
            return total, [dict(r) for r in rows]

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT u.id, u.nome, u.sobrenome, u.email, u.cpf, u.senha_hash, u.senha_algoritmo,
                   u.telefone, u.celular, u.foto_url, u.status, u.ultimo_login_em,
                   u.polo_id, u.escola_id, u.perfil_id,
                   p.nome as perfil_nome, p.descricao as perfil_descricao,
                   u.criado_em, u.atualizado_em
            FROM usuarios u
            LEFT JOIN perfis p ON u.perfil_id = p.id
            WHERE u.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(user_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT u.id, u.nome, u.sobrenome, u.email, u.cpf, u.senha_hash, u.senha_algoritmo,
                   u.telefone, u.celular, u.foto_url, u.status, u.ultimo_login_em,
                   u.polo_id, u.escola_id, u.perfil_id,
                   p.nome as perfil_nome, u.criado_em, u.atualizado_em
            FROM usuarios u
            LEFT JOIN perfis p ON u.perfil_id = p.id
            WHERE lower(u.email) = lower(%s)
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (email.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        clean_cpf = "".join(filter(str.isdigit, cpf))
        sql = """
            SELECT id, nome, email, cpf FROM usuarios WHERE regexp_replace(cpf, '[^0-9]', '', 'g') = %s LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (clean_cpf,))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_user(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO usuarios (
                id, nome, sobrenome, email, cpf, senha_hash, senha_algoritmo,
                telefone, celular, foto_url, perfil_id, polo_id, escola_id,
                status, criado_em, atualizado_em
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, now(), now()
            ) RETURNING id
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    data.get("nome", ""),
                    data.get("sobrenome", ""),
                    data.get("email"),
                    data.get("cpf"),
                    data.get("senha_hash"),
                    data.get("senha_algoritmo", "argon2id"),
                    data.get("telefone"),
                    data.get("celular"),
                    data.get("foto_url"),
                    data.get("perfil_id"),
                    data.get("polo_id"),
                    data.get("escola_id"),
                    data.get("status", "ativo"),
                ),
            )
            row = cur.fetchone()
            return str(row["id"]) if row else new_id

    def update_user(self, user_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(user_id))

        sql = f"UPDATE usuarios SET {', '.join(fields)} WHERE id = %s"
        with get_db_cursor() as cur:
            cur.execute(sql, tuple(params))

    def delete_user(self, user_id: str) -> None:
        sql = "DELETE FROM usuarios WHERE id = %s"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(user_id),))

    def get_user_permissions(self, user_id: str) -> List[str]:
        sql = """
            SELECT p.chave
            FROM usuario_permissoes up
            JOIN permissoes p ON up.permissao_id = p.id
            WHERE up.usuario_id = %s
            ORDER BY p.chave ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(user_id),))
            rows = cur.fetchall()
            return [r["chave"] for r in rows]

    def ensure_permissoes(self, keys: List[str]) -> None:
        if not keys:
            return
        sql = """
            INSERT INTO permissoes (chave, descricao, criado_em, atualizado_em)
            VALUES (%s, %s, now(), now())
            ON CONFLICT (chave) DO NOTHING
        """
        with get_db_cursor() as cur:
            for k in keys:
                cur.execute(sql, (k.strip().lower(), f"Permissão {k.strip()}"))

    def set_user_permissions(self, user_id: str, permission_keys: List[str]) -> None:
        uid = str(user_id)
        # 1. Garante que as chaves existem na tabela permissoes
        self.ensure_permissoes(permission_keys)

        with get_db_cursor() as cur:
            # 2. Remove permissões antigas
            cur.execute("DELETE FROM usuario_permissoes WHERE usuario_id = %s", (uid,))

            if permission_keys:
                # 3. Busca IDs das permissões
                placeholders = ",".join(["%s"] * len(permission_keys))
                cur.execute(
                    f"SELECT id FROM permissoes WHERE chave IN ({placeholders})",
                    tuple(k.strip().lower() for k in permission_keys),
                )
                perm_ids = [r["id"] for r in cur.fetchall()]

                for pid in perm_ids:
                    cur.execute(
                        "INSERT INTO usuario_permissoes (usuario_id, permissao_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (uid, str(pid)),
                    )

    def list_perfis(self) -> List[Dict[str, Any]]:
        sql = "SELECT id, nome, descricao FROM perfis ORDER BY nome ASC"
        with get_db_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_perfil_by_id(self, perfil_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT id, nome, descricao FROM perfis WHERE id = %s LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(perfil_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_perfil_by_nome(self, nome: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT id, nome, descricao FROM perfis WHERE lower(nome) = lower(%s) LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (nome.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_permissoes(self) -> List[Dict[str, Any]]:
        sql = "SELECT id, chave, descricao FROM permissoes ORDER BY chave ASC"
        with get_db_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def list_audit_logs(
        self,
        usuario_id: Optional[str] = None,
        entidade: Optional[str] = None,
        acao: Optional[str] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []

        if usuario_id:
            conditions.append("l.usuario_id = %s")
            params.append(str(usuario_id))

        if entidade:
            conditions.append("lower(l.entidade) = lower(%s)")
            params.append(entidade.strip())

        if acao:
            conditions.append("lower(l.acao) = lower(%s)")
            params.append(acao.strip())

        if data_inicio:
            conditions.append("l.criado_em >= %s")
            params.append(data_inicio)

        if data_fim:
            conditions.append("l.criado_em <= %s")
            params.append(data_fim)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"SELECT COUNT(*) as total FROM logs_auditoria l {where_clause}"
        data_sql = f"""
            SELECT l.id, l.usuario_id, u.nome as usuario_nome, u.email as usuario_email,
                   l.acao, l.entidade, l.entidade_id, l.dados_antes, l.dados_depois,
                   l.ip, l.criado_em
            FROM logs_auditoria l
            LEFT JOIN usuarios u ON l.usuario_id = u.id
            {where_clause}
            ORDER BY l.criado_em DESC
            LIMIT %s OFFSET %s
        """

        with get_db_cursor() as cur:
            cur.execute(count_sql, tuple(params))
            count_row = cur.fetchone()
            total = int(count_row["total"]) if count_row else 0

            cur.execute(data_sql, tuple(params + [limit, offset]))
            rows = cur.fetchall()
            return total, [dict(r) for r in rows]

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
                    json.dumps(dados_antes) if dados_antes is not None else None,
                    json.dumps(dados_depois) if dados_depois is not None else None,
                    ip,
                ),
            )

    def list_configuracoes(self) -> List[Dict[str, Any]]:
        sql = "SELECT id, chave, valor, criado_em, atualizado_em FROM configuracoes ORDER BY chave ASC"
        with get_db_cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_configuracao(self, chave: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT id, chave, valor, criado_em, atualizado_em FROM configuracoes WHERE chave = %s LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (chave.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def set_configuracao(self, chave: str, valor: Any) -> Dict[str, Any]:
        sql = """
            INSERT INTO configuracoes (chave, valor, criado_em, atualizado_em)
            VALUES (%s, %s, now(), now())
            ON CONFLICT (chave) DO UPDATE
            SET valor = EXCLUDED.valor, atualizado_em = now()
            RETURNING id, chave, valor, criado_em, atualizado_em
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (chave.strip(), json.dumps(valor)))
            row = cur.fetchone()
            return dict(row) if row else {"chave": chave, "valor": valor}

    def list_etl_sync_runs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if status:
            conditions.append("status = %s")
            params.append(status.strip())

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"SELECT COUNT(*) as total FROM etl_sync_runs {where_clause}"
        data_sql = f"""
            SELECT id, modo, iniciado_em, finalizado_em, total_lido, total_inserido,
                   total_atualizado, total_erro, status,
                   EXTRACT(EPOCH FROM (COALESCE(finalizado_em, now()) - iniciado_em)) as duracao_segundos,
                   (SELECT COUNT(*) FROM etl_erros WHERE execucao_id = etl_sync_runs.id) as total_erros_detalhados
            FROM etl_sync_runs
            {where_clause}
            ORDER BY iniciado_em DESC
            LIMIT %s OFFSET %s
        """
        with get_db_cursor() as cur:
            cur.execute(count_sql, tuple(params))
            count_row = cur.fetchone()
            total = int(count_row["total"]) if count_row else 0

            cur.execute(data_sql, tuple(params + [limit, offset]))
            rows = cur.fetchall()
            return total, [dict(r) for r in rows]

    def get_etl_sync_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT id, modo, iniciado_em, finalizado_em, total_lido, total_inserido,
                   total_atualizado, total_erro, status,
                   EXTRACT(EPOCH FROM (COALESCE(finalizado_em, now()) - iniciado_em)) as duracao_segundos,
                   (SELECT COUNT(*) FROM etl_erros WHERE execucao_id = etl_sync_runs.id) as total_erros_detalhados
            FROM etl_sync_runs
            WHERE id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (int(run_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_etl_erros(
        self,
        execucao_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        count_sql = "SELECT COUNT(*) as total FROM etl_erros WHERE execucao_id = %s"
        data_sql = """
            SELECT id, execucao_id, tabela_origem, id_origem, erro, linha_raw, criado_em
            FROM etl_erros
            WHERE execucao_id = %s
            ORDER BY criado_em DESC
            LIMIT %s OFFSET %s
        """
        with get_db_cursor() as cur:
            cur.execute(count_sql, (int(execucao_id),))
            count_row = cur.fetchone()
            total = int(count_row["total"]) if count_row else 0

            cur.execute(data_sql, (int(execucao_id), limit, offset))
            rows = cur.fetchall()
            return total, [dict(r) for r in rows]


class InMemoryAdminRepository:
    """Implementação em memória para testes unitários e de integração."""

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
            "perm-p_cadastro": {"id": "perm-p_cadastro", "chave": "p_cadastro", "descricao": "Permissão de cadastro"},
            "perm-p_edicao": {"id": "perm-p_edicao", "chave": "p_edicao", "descricao": "Permissão de edição"},
            "perm-p_vendas": {"id": "perm-p_vendas", "chave": "p_vendas", "descricao": "Permissão de vendas"},
            "perm-p_matriculas": {"id": "perm-p_matriculas", "chave": "p_matriculas", "descricao": "Permissão de matrículas"},
            "perm-p_financeiro": {"id": "perm-p_financeiro", "chave": "p_financeiro", "descricao": "Permissão financeira"},
            "perm-p_academico": {"id": "perm-p_academico", "chave": "p_academico", "descricao": "Permissão acadêmica"},
            "perm-p_chat": {"id": "perm-p_chat", "chave": "p_chat", "descricao": "Permissão de chat"},
            "perm-p_ranking": {"id": "perm-p_ranking", "chave": "p_ranking", "descricao": "Permissão de ranking"},
        }
        self.usuario_permissoes: List[Dict[str, str]] = []  # {"usuario_id", "permissao_id"}
        self.logs_auditoria: List[Dict[str, Any]] = []
        self.configuracoes: Dict[str, Dict[str, Any]] = {}  # chave -> dict
        self.etl_sync_runs: List[Dict[str, Any]] = []
        self.etl_erros: List[Dict[str, Any]] = []

    def list_users(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        filtered = list(self.usuarios.values())

        if query:
            q = query.strip().lower()
            filtered = [
                u for u in filtered
                if q in (u.get("nome") or "").lower()
                or q in (u.get("sobrenome") or "").lower()
                or q in (u.get("email") or "").lower()
                or q in (u.get("cpf") or "").lower()
            ]

        if perfil_id:
            filtered = [u for u in filtered if u.get("perfil_id") == str(perfil_id)]

        if perfil_nome:
            p_name_clean = perfil_nome.strip().lower()
            filtered = [
                u for u in filtered
                if (
                    self.perfis.get(u.get("perfil_id", ""), {}).get("nome", "").lower() == p_name_clean
                    or u.get("perfil_nome", "").lower() == p_name_clean
                )
            ]

        if status:
            filtered = [u for u in filtered if u.get("status") == status.strip()]

        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        out = []
        for u in paginated:
            u_copy = u.copy()
            pid = u.get("perfil_id")
            if pid and pid in self.perfis:
                u_copy["perfil_nome"] = self.perfis[pid]["nome"]
            out.append(u_copy)

        return total, out

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        u = self.usuarios.get(str(user_id))
        if not u:
            return None
        out = u.copy()
        pid = u.get("perfil_id")
        if pid and pid in self.perfis:
            out["perfil_nome"] = self.perfis[pid]["nome"]
            out["perfil_descricao"] = self.perfis[pid].get("descricao")
        return out

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        for u in self.usuarios.values():
            if (u.get("email") or "").strip().lower() == clean_email:
                out = u.copy()
                pid = u.get("perfil_id")
                if pid and pid in self.perfis:
                    out["perfil_nome"] = self.perfis[pid]["nome"]
                return out
        return None

    def get_user_by_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        clean_cpf = "".join(filter(str.isdigit, cpf))
        for u in self.usuarios.values():
            u_cpf_clean = "".join(filter(str.isdigit, u.get("cpf") or ""))
            if u_cpf_clean and u_cpf_clean == clean_cpf:
                return u.copy()
        return None

    def create_user(self, data: Dict[str, Any]) -> str:
        new_id = data.get("id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_record = {
            "id": new_id,
            "nome": data.get("nome", ""),
            "sobrenome": data.get("sobrenome", ""),
            "email": data.get("email"),
            "cpf": data.get("cpf"),
            "senha_hash": data.get("senha_hash"),
            "senha_algoritmo": data.get("senha_algoritmo", "argon2id"),
            "telefone": data.get("telefone"),
            "celular": data.get("celular"),
            "foto_url": data.get("foto_url"),
            "perfil_id": data.get("perfil_id"),
            "polo_id": data.get("polo_id"),
            "escola_id": data.get("escola_id"),
            "status": data.get("status", "ativo"),
            "ultimo_login_em": data.get("ultimo_login_em"),
            "criado_em": now,
            "atualizado_em": now,
        }
        self.usuarios[new_id] = user_record
        return new_id

    def update_user(self, user_id: str, data: Dict[str, Any]) -> None:
        uid = str(user_id)
        if uid in self.usuarios:
            self.usuarios[uid].update(data)
            self.usuarios[uid]["atualizado_em"] = datetime.now(timezone.utc)

    def delete_user(self, user_id: str) -> None:
        uid = str(user_id)
        if uid in self.usuarios:
            del self.usuarios[uid]
        self.usuario_permissoes = [up for up in self.usuario_permissoes if up["usuario_id"] != uid]

    def get_user_permissions(self, user_id: str) -> List[str]:
        uid = str(user_id)
        perm_ids = [up["permissao_id"] for up in self.usuario_permissoes if up["usuario_id"] == uid]
        return sorted([self.permissoes[pid]["chave"] for pid in perm_ids if pid in self.permissoes])

    def ensure_permissoes(self, keys: List[str]) -> None:
        for k in keys:
            clean_k = k.strip().lower()
            exists = any(p["chave"] == clean_k for p in self.permissoes.values())
            if not exists:
                pid = f"perm-{clean_k}"
                self.permissoes[pid] = {
                    "id": pid,
                    "chave": clean_k,
                    "descricao": f"Permissão {clean_k}",
                }

    def set_user_permissions(self, user_id: str, permission_keys: List[str]) -> None:
        uid = str(user_id)
        self.ensure_permissoes(permission_keys)

        # Remove permissões atuais do usuário
        self.usuario_permissoes = [up for up in self.usuario_permissoes if up["usuario_id"] != uid]

        # Adiciona novas
        clean_keys = set(k.strip().lower() for k in permission_keys)
        for pid, pdata in self.permissoes.items():
            if pdata["chave"] in clean_keys:
                self.usuario_permissoes.append({"usuario_id": uid, "permissao_id": pid})

    def list_perfis(self) -> List[Dict[str, Any]]:
        return list(self.perfis.values())

    def get_perfil_by_id(self, perfil_id: str) -> Optional[Dict[str, Any]]:
        return self.perfis.get(str(perfil_id))

    def get_perfil_by_nome(self, nome: str) -> Optional[Dict[str, Any]]:
        clean_nome = nome.strip().lower()
        for p in self.perfis.values():
            if p["nome"].lower() == clean_nome:
                return p.copy()
        return None

    def list_permissoes(self) -> List[Dict[str, Any]]:
        return list(self.permissoes.values())

    def list_audit_logs(
        self,
        usuario_id: Optional[str] = None,
        entidade: Optional[str] = None,
        acao: Optional[str] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        filtered = self.logs_auditoria

        if usuario_id:
            filtered = [l for l in filtered if l.get("usuario_id") == str(usuario_id)]

        if entidade:
            e_clean = entidade.strip().lower()
            filtered = [l for l in filtered if (l.get("entidade") or "").lower() == e_clean]

        if acao:
            a_clean = acao.strip().lower()
            filtered = [l for l in filtered if (l.get("acao") or "").lower() == a_clean]

        if data_inicio:
            filtered = [l for l in filtered if l.get("criado_em") and l["criado_em"] >= data_inicio]

        if data_fim:
            filtered = [l for l in filtered if l.get("criado_em") and l["criado_em"] <= data_fim]

        filtered = sorted(filtered, key=lambda x: x.get("criado_em", datetime.min), reverse=True)
        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        out = []
        for l in paginated:
            l_copy = l.copy()
            uid = l.get("usuario_id")
            if uid and uid in self.usuarios:
                l_copy["usuario_nome"] = self.usuarios[uid].get("nome")
                l_copy["usuario_email"] = self.usuarios[uid].get("email")
            out.append(l_copy)

        return total, out

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

    def list_configuracoes(self) -> List[Dict[str, Any]]:
        return list(self.configuracoes.values())

    def get_configuracao(self, chave: str) -> Optional[Dict[str, Any]]:
        return self.configuracoes.get(chave.strip())

    def set_configuracao(self, chave: str, valor: Any) -> Dict[str, Any]:
        k = chave.strip()
        now = datetime.now(timezone.utc)
        if k in self.configuracoes:
            self.configuracoes[k]["valor"] = valor
            self.configuracoes[k]["atualizado_em"] = now
        else:
            self.configuracoes[k] = {
                "id": str(uuid.uuid4()),
                "chave": k,
                "valor": valor,
                "criado_em": now,
                "atualizado_em": now,
            }
        return self.configuracoes[k].copy()

    def list_etl_sync_runs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        filtered = self.etl_sync_runs
        if status:
            s_clean = status.strip().lower()
            filtered = [r for r in filtered if r.get("status", "").lower() == s_clean]

        filtered = sorted(filtered, key=lambda x: x.get("iniciado_em", datetime.min), reverse=True)
        total = len(filtered)
        paginated = filtered[offset : offset + limit]
        return total, [r.copy() for r in paginated]

    def get_etl_sync_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        for r in self.etl_sync_runs:
            if r.get("id") == int(run_id):
                return r.copy()
        return None

    def list_etl_erros(
        self,
        execucao_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        eid = int(execucao_id)
        filtered = [e for e in self.etl_erros if e.get("execucao_id") == eid]
        filtered = sorted(filtered, key=lambda x: x.get("criado_em", datetime.min), reverse=True)
        total = len(filtered)
        paginated = filtered[offset : offset + limit]
        return total, [r.copy() for r in paginated]


_default_admin_repo: Optional[AdminRepositoryInterface] = None


def get_admin_repository() -> AdminRepositoryInterface:
    """Retorna o repositório padrão de administração."""
    global _default_admin_repo
    if _default_admin_repo is None:
        _default_admin_repo = PostgresAdminRepository()
    return _default_admin_repo


def set_admin_repository(repo: AdminRepositoryInterface) -> None:
    """Injeta repositório para testes."""
    global _default_admin_repo
    _default_admin_repo = repo
