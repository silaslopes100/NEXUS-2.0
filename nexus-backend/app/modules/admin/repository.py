"""Repositório de dados para o módulo administrativo do NEXUS 2.0."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from app.core.database import get_db_cursor
from app.modules.admin.schemas import POPUP_MENSAGEM_CHURN


class AdminRepositoryInterface(Protocol):
    # Usuários
    def list_users(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status: Optional[str] = None,
        incluir_gerenciados: Optional[bool] = None,
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

    # ========== Dashboard & Entidades Operacionais ==========

    # Polos (RN-01: vínculo 1:1 com usuário coordenador)
    def list_polos(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        polo_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def get_polo_by_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...
    def create_polo_com_usuario(
        self,
        polo_data: Dict[str, Any],
        usuario_data: Dict[str, Any],
        permission_keys: Optional[List[str]] = None,
    ) -> Tuple[str, str]: ...
    def update_polo_sincronizar_usuario(
        self,
        polo_id: str,
        polo_data: Dict[str, Any],
        usuario_id: str,
        usuario_data: Dict[str, Any],
    ) -> None: ...
    def desativar_polo_e_usuario(self, polo_id: str, usuario_id: str) -> None: ...
    def get_polo_detalhes(self, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def get_ranking_polos(self) -> List[Dict[str, Any]]: ...

    # Escolas (RN-01: vínculo 1:1 com usuário secretário)
    def list_escolas(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]: ...
    def get_escola_by_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...
    def create_escola_com_usuario(
        self,
        escola_data: Dict[str, Any],
        usuario_data: Dict[str, Any],
        permission_keys: Optional[List[str]] = None,
    ) -> Tuple[str, str]: ...
    def update_escola_sincronizar_usuario(
        self,
        escola_id: str,
        escola_data: Dict[str, Any],
        usuario_id: str,
        usuario_data: Dict[str, Any],
    ) -> None: ...
    def desativar_escola_e_usuario(self, escola_id: str, usuario_id: str) -> None: ...
    def get_escola_detalhes(self, escola_id: str) -> Optional[Dict[str, Any]]: ...

    # Cursos / Módulos / Matérias
    def list_cursos(
        self, query: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_curso(self, curso_id: str) -> Optional[Dict[str, Any]]: ...
    def create_curso(self, data: Dict[str, Any]) -> str: ...
    def update_curso(self, curso_id: str, data: Dict[str, Any]) -> None: ...
    def delete_curso(self, curso_id: str) -> None: ...
    def list_modulos(
        self, curso_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_modulo(self, modulo_id: str) -> Optional[Dict[str, Any]]: ...
    def create_modulo(self, data: Dict[str, Any]) -> str: ...
    def update_modulo(self, modulo_id: str, data: Dict[str, Any]) -> None: ...
    def delete_modulo(self, modulo_id: str) -> None: ...
    def list_materias(
        self,
        curso_id: Optional[str] = None,
        modulo_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_materia(self, materia_id: str) -> Optional[Dict[str, Any]]: ...
    def create_materia(self, data: Dict[str, Any]) -> str: ...
    def update_materia(self, materia_id: str, data: Dict[str, Any]) -> None: ...
    def delete_materia(self, materia_id: str) -> None: ...

    # Matrículas
    def list_matriculas(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_matricula(self, matricula_id: str) -> Optional[Dict[str, Any]]: ...
    def create_matricula(self, data: Dict[str, Any]) -> str: ...
    def update_matricula(self, matricula_id: str, data: Dict[str, Any]) -> None: ...

    # Alunos
    def list_alunos(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]: ...
    def create_aluno_com_usuario(
        self,
        usuario_data: Dict[str, Any],
        aluno_data: Dict[str, Any],
        matricula_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Optional[str]]: ...
    def update_aluno(self, aluno_id: str, data: Dict[str, Any]) -> None: ...
    def marcar_desistentes_automatico(self, cutoff: datetime) -> int: ...

    # EAD
    def list_matriculas_ead(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_matricula_ead(self, matricula_ead_id: str) -> Optional[Dict[str, Any]]: ...
    def create_matricula_ead(self, data: Dict[str, Any]) -> str: ...
    def update_matricula_ead(self, matricula_ead_id: str, data: Dict[str, Any]) -> None: ...
    def get_matricula_ead_por_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]: ...
    def count_liberacoes_ead_mes(self, aluno_id: str, ano: int, mes: int) -> int: ...
    def registrar_liberacao_ead(self, data: Dict[str, Any]) -> str: ...
    def get_ultima_liberacao_ead(self, matricula_ead_id: str) -> Optional[Dict[str, Any]]: ...
    def list_ead_calendario(
        self, curso_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_ead_calendario(self, data: Dict[str, Any]) -> str: ...
    def delete_ead_calendario(self, calendario_id: str) -> None: ...
    def list_feed_noticias(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_feed_noticia(self, data: Dict[str, Any]) -> str: ...
    def delete_feed_noticia(self, noticia_id: str) -> None: ...
    def list_lembretes(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_lembrete(self, data: Dict[str, Any]) -> str: ...
    def delete_lembrete(self, lembrete_id: str) -> None: ...

    # Licenças / Estoque
    def list_licencas_estoque(
        self, query: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_licenca_estoque(self, materia_id: str, tipo: str = "licenca") -> Optional[Dict[str, Any]]: ...
    def ajustar_licenca_estoque(
        self,
        materia_id: str,
        tipo: str,
        delta: int,
        movimentacao: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...
    def list_licencas_movimentacoes(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...

    # Aulas / Presenças / Anexos / Atas
    def list_aulas(
        self,
        professor_id: Optional[str] = None,
        materia_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_aula(self, aula_id: str) -> Optional[Dict[str, Any]]: ...
    def create_aula(self, data: Dict[str, Any]) -> str: ...
    def registrar_presencas(
        self, aula_id: str, registros: List[Dict[str, Any]], registrado_por: Optional[str] = None
    ) -> None: ...
    def list_presencas(
        self,
        aula_id: Optional[str] = None,
        aluno_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_presencas_resumo_aluno(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def get_presencas_resumo_professor(self, professor_id: str) -> List[Dict[str, Any]]: ...
    def count_presencas_aluno(self, aluno_id: str) -> Tuple[int, float]: ...
    def list_anexos_aula(
        self,
        professor_id: Optional[str] = None,
        aula_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def list_atas(
        self,
        professor_id: Optional[str] = None,
        aula_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...

    # Certificados (RN-05)
    def list_certificados(
        self,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_certificado(self, certificado_id: str) -> Optional[Dict[str, Any]]: ...
    def create_certificado(self, data: Dict[str, Any]) -> str: ...
    def count_certificados(self) -> int: ...
    def get_estagios_aluno(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def get_materias_pendentes_aluno(self, aluno_id: str) -> List[Dict[str, Any]]: ...

    # Chat (RN-06)
    def list_chat_conversas(
        self,
        usuario_id: Optional[str] = None,
        tipo: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_chat_conversa(self, conversa_id: str) -> Optional[Dict[str, Any]]: ...
    def create_chat_conversa(
        self,
        tipo: str,
        criado_por: str,
        nome: Optional[str] = None,
        participantes: Optional[List[str]] = None,
    ) -> str: ...
    def add_chat_participantes(self, conversa_id: str, usuario_ids: List[str]) -> None: ...
    def get_chat_participantes(self, conversa_id: str) -> List[Dict[str, Any]]: ...
    def update_chat_conversa(self, conversa_id: str, data: Dict[str, Any]) -> None: ...
    def delete_chat_conversa(self, conversa_id: str) -> None: ...
    def list_chat_mensagens(
        self, conversa_id: str, limit: int = 200, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def create_chat_mensagem(self, conversa_id: str, remetente_id: str, conteudo: str) -> str: ...
    def marcar_mensagem_lida(self, mensagem_id: str) -> None: ...

    # Financeiro
    def list_vendas(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]], float]: ...
    def create_venda(self, data: Dict[str, Any]) -> str: ...
    def list_boletos(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_boleto(self, boleto_id: str) -> Optional[Dict[str, Any]]: ...
    def create_boleto(self, data: Dict[str, Any]) -> str: ...

    # Logística
    def list_pedidos_livros(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_pedido_livro(self, pedido_id: str) -> Optional[Dict[str, Any]]: ...
    def create_pedido_livro(self, data: Dict[str, Any]) -> str: ...
    def update_pedido_livro(self, pedido_id: str, data: Dict[str, Any]) -> None: ...

    # Churn (RN-04)
    def list_alunos_churn(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_aluno_churn(self, aluno_id: str) -> Optional[Dict[str, Any]]: ...
    def create_aluno_churn(self, data: Dict[str, Any]) -> str: ...
    def update_aluno_churn(self, churn_id: str, data: Dict[str, Any]) -> None: ...

    # Requisições de Troca
    def list_requisicoes_troca(
        self,
        status: Optional[str] = None,
        aluno_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_requisicao_troca(self, requisicao_id: str) -> Optional[Dict[str, Any]]: ...
    def create_requisicao_troca(self, data: Dict[str, Any]) -> str: ...
    def update_requisicao_troca(self, requisicao_id: str, data: Dict[str, Any]) -> None: ...

    # Notas / Histórico
    def list_notas_aluno(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def create_nota(self, data: Dict[str, Any]) -> str: ...
    def list_historico_aluno(self, aluno_id: str) -> List[Dict[str, Any]]: ...
    def upsert_historico(self, data: Dict[str, Any]) -> None: ...
    def list_professores_ativos(
        self,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]: ...
    def get_professor_por_id(self, usuario_id: str) -> Optional[Dict[str, Any]]: ...


# ---------- Helpers genéricos do PostgreSQL ----------

def _exec_paginated(
    count_sql: str,
    data_sql: str,
    params: List[Any],
    limit: int,
    offset: int,
) -> Tuple[int, List[Dict[str, Any]]]:
    """Executa consulta de contagem + listagem paginada (limit/offset com total)."""
    with get_db_cursor() as cur:
        cur.execute(count_sql, tuple(params))
        count_row = cur.fetchone()
        total = int(count_row["total"]) if count_row else 0

        cur.execute(data_sql, tuple(params + [limit, offset]))
        rows = cur.fetchall()
        return total, [dict(r) for r in rows]


class PostgresAdminRepository:
    """Implementação PostgreSQL das operações administrativas."""

    def list_users(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status: Optional[str] = None,
        incluir_gerenciados: Optional[bool] = None,
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

        # RN-01: usuários gerenciados via cadastro unificado de Polo/Escola
        # (coordenador_polo vinculado a polo / secretario_escola vinculado a escola)
        # podem ser ocultados (False) ou exibidos com flag (True); None = todos
        gerenciado_case = """
            CASE
                WHEN lower(p.nome) = 'coordenador_polo' AND u.polo_id IS NOT NULL THEN 'polo'
                WHEN lower(p.nome) = 'secretario_escola' AND u.escola_id IS NOT NULL THEN 'escola'
            END
        """
        if incluir_gerenciados is False:
            conditions.append(f"({gerenciado_case}) IS NULL")
        elif incluir_gerenciados is True:
            conditions.append(f"({gerenciado_case}) IS NOT NULL")

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
                   u.perfil_id, p.nome as perfil_nome,
                   {gerenciado_case} as gerenciado_via,
                   u.criado_em, u.atualizado_em
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

    # ========== Dashboard & Entidades Operacionais (PostgreSQL) ==========

    # ---------- Polos (RN-01) ----------

    def list_polos(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        polo_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if query:
            q = f"%{query.strip().lower()}%"
            conditions.append(
                "(lower(coalesce(p.nome, '')) LIKE %s OR lower(coalesce(p.responsavel, '')) LIKE %s "
                "OR lower(coalesce(p.cpf, '')) LIKE %s OR lower(coalesce(p.email, '')) LIKE %s)"
            )
            params.extend([q, q, q, q])
        if status:
            conditions.append("p.status = %s")
            params.append(status.strip())
        else:
            # Por padrão oculta polos inativos (exclusão lógica)
            conditions.append("p.status != 'inativo'")
        if polo_id:
            conditions.append("p.id = %s")
            params.append(str(polo_id))

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM polos p {where_clause}"
        data_sql = f"""
            SELECT p.id, p.nome, p.responsavel, p.cpf, p.email, p.endereco,
                   p.responsavel_nome, p.responsavel_cpf, p.responsavel_email,
                   p.logradouro, p.numero, p.bairro, p.cidade, p.uf, p.cep,
                   p.usuario_id, p.status, p.criado_em, p.atualizado_em
            FROM polos p
            {where_clause}
            ORDER BY p.nome ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT p.id, p.nome, p.responsavel, p.cpf, p.email, p.endereco,
                   p.responsavel_nome, p.responsavel_cpf, p.responsavel_email,
                   p.logradouro, p.numero, p.bairro, p.cidade, p.uf, p.cep,
                   p.usuario_id, p.status, p.criado_em, p.atualizado_em
            FROM polos p
            WHERE p.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(polo_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_polo_by_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM polos WHERE usuario_id = %s LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_polo_com_usuario(
        self,
        polo_data: Dict[str, Any],
        usuario_data: Dict[str, Any],
        permission_keys: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        # RN-01: criação atômica de Polo + usuário coordenador (mesma transação)
        polo_id = str(uuid.uuid4())
        usuario_id = str(uuid.uuid4())

        self.ensure_permissoes(permission_keys or [])

        with get_db_cursor() as cur:
            # 1. Insere o usuário coordenador
            cur.execute(
                """
                INSERT INTO usuarios (
                    id, nome, sobrenome, email, cpf, senha_hash, senha_algoritmo,
                    telefone, celular, foto_url, perfil_id, polo_id, escola_id, status, criado_em, atualizado_em
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, now(), now()
                )
                """,
                (
                    usuario_id,
                    usuario_data.get("nome", ""),
                    usuario_data.get("sobrenome", ""),
                    usuario_data.get("email"),
                    usuario_data.get("cpf"),
                    usuario_data.get("senha_hash"),
                    usuario_data.get("senha_algoritmo", "argon2id"),
                    usuario_data.get("telefone"),
                    usuario_data.get("celular"),
                    usuario_data.get("foto_url"),
                    usuario_data.get("perfil_id"),
                    polo_id,
                    usuario_data.get("escola_id"),
                    usuario_data.get("status", "ativo"),
                ),
            )

            # 2. Permissões granulares do coordenador
            for k in permission_keys or []:
                cur.execute(
                    """
                    INSERT INTO usuario_permissoes (usuario_id, permissao_id)
                    SELECT %s, id FROM permissoes WHERE chave = %s
                    ON CONFLICT DO NOTHING
                    """,
                    (usuario_id, k.strip().lower()),
                )

            # 3. Insere o polo com FK usuario_id (RN-01: vínculo 1:1)
            cur.execute(
                """
                INSERT INTO polos (
                    id, nome, responsavel, cpf, email, endereco,
                    responsavel_nome, responsavel_cpf, responsavel_email,
                    logradouro, numero, bairro, cidade, uf, cep,
                    usuario_id, status, criado_em, atualizado_em
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, now(), now()
                )
                """,
                (
                    polo_id,
                    polo_data.get("nome"),
                    polo_data.get("responsavel"),
                    polo_data.get("cpf"),
                    polo_data.get("email"),
                    polo_data.get("endereco"),
                    polo_data.get("responsavel"),
                    polo_data.get("cpf"),
                    polo_data.get("email"),
                    polo_data.get("logradouro"),
                    polo_data.get("numero"),
                    polo_data.get("bairro"),
                    polo_data.get("cidade"),
                    polo_data.get("uf"),
                    polo_data.get("cep"),
                    usuario_id,
                    polo_data.get("status", "ativo"),
                ),
            )

        return polo_id, usuario_id

    def update_polo_sincronizar_usuario(
        self,
        polo_id: str,
        polo_data: Dict[str, Any],
        usuario_id: str,
        usuario_data: Dict[str, Any],
    ) -> None:
        # RN-01: sincronização atômica dos dados do responsável/coordenador
        polo_fields = []
        polo_params: List[Any] = []
        for key, val in polo_data.items():
            polo_fields.append(f"{key} = %s")
            polo_params.append(val)
        polo_fields.append("atualizado_em = now()")
        polo_params.append(str(polo_id))

        user_fields = []
        user_params: List[Any] = []
        for key, val in usuario_data.items():
            user_fields.append(f"{key} = %s")
            user_params.append(val)
        user_fields.append("atualizado_em = now()")
        user_params.append(str(usuario_id))

        with get_db_cursor() as cur:
            cur.execute(f"UPDATE polos SET {', '.join(polo_fields)} WHERE id = %s", tuple(polo_params))
            cur.execute(f"UPDATE usuarios SET {', '.join(user_fields)} WHERE id = %s", tuple(user_params))

    def desativar_polo_e_usuario(self, polo_id: str, usuario_id: str) -> None:
        # RN-01: exclusão do polo desativa o usuário coordenador vinculado
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE polos SET status = 'inativo', atualizado_em = now() WHERE id = %s",
                (str(polo_id),),
            )
            cur.execute(
                "UPDATE usuarios SET status = 'inativo', atualizado_em = now() WHERE id = %s",
                (str(usuario_id),),
            )

    def get_polo_detalhes(self, polo_id: str) -> Optional[Dict[str, Any]]:
        polo = self.get_polo(polo_id)
        if not polo:
            return None
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM alunos WHERE polo_id = %s AND status = 'ativo'",
                (str(polo_id),),
            )
            polo["total_alunos"] = int((cur.fetchone() or {}).get("total", 0))

            cur.execute(
                """
                SELECT id, polo_id, nome, responsavel, cpf, email, endereco, usuario_id, status, criado_em, atualizado_em
                FROM escolas WHERE polo_id = %s AND status != 'inativo' ORDER BY nome ASC
                """,
                (str(polo_id),),
            )
            polo["escolas_vinculadas"] = [dict(r) for r in cur.fetchall()]
            polo["total_escolas"] = len(polo["escolas_vinculadas"])

            cur.execute(
                """
                SELECT COALESCE(SUM(m.quantidade), 0) AS total
                FROM licencas_movimentacoes m
                WHERE m.polo_id = %s AND m.tipo_movimento = 'saida'
                """,
                (str(polo_id),),
            )
            polo["total_licencas"] = int((cur.fetchone() or {}).get("total", 0))
        return polo

    def get_ranking_polos(self) -> List[Dict[str, Any]]:
        # Ranking de polos por ordem de novas licenças/livros adquiridos
        sql = """
            SELECT p.id, p.nome,
                   COALESCE(SUM(v.quantidade) FILTER (WHERE v.tipo_item = 'licenca'), 0) AS total_licencas,
                   COALESCE(SUM(v.quantidade) FILTER (WHERE v.tipo_item = 'livro'), 0) AS total_livros,
                   COALESCE(SUM(v.quantidade) FILTER (WHERE v.tipo_item IN ('licenca', 'livro')), 0) AS total_adquirido
            FROM polos p
            LEFT JOIN vendas v ON v.polo_id = p.id
            WHERE p.status != 'inativo'
            GROUP BY p.id, p.nome
            ORDER BY total_adquirido DESC, p.nome ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]

    # ---------- Escolas (RN-01) ----------

    def list_escolas(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if query:
            q = f"%{query.strip().lower()}%"
            conditions.append(
                "(lower(coalesce(e.nome, '')) LIKE %s OR lower(coalesce(e.responsavel, '')) LIKE %s "
                "OR lower(coalesce(e.cpf, '')) LIKE %s OR lower(coalesce(e.email, '')) LIKE %s)"
            )
            params.extend([q, q, q, q])
        if status:
            conditions.append("e.status = %s")
            params.append(status.strip())
        else:
            conditions.append("e.status != 'inativo'")
        if polo_id:
            conditions.append("e.polo_id = %s")
            params.append(str(polo_id))
        if escola_id:
            conditions.append("e.id = %s")
            params.append(str(escola_id))

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM escolas e {where_clause}"
        data_sql = f"""
            SELECT e.id, e.polo_id, e.nome, e.responsavel, e.cpf, e.email, e.endereco,
                   e.responsavel_nome, e.responsavel_cpf, e.responsavel_email,
                   e.logradouro, e.numero, e.bairro, e.cidade, e.uf, e.cep,
                   e.usuario_id, e.status, e.criado_em, e.atualizado_em
            FROM escolas e
            {where_clause}
            ORDER BY e.nome ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_escola(self, escola_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT e.id, e.polo_id, e.nome, e.responsavel, e.cpf, e.email, e.endereco,
                   e.responsavel_nome, e.responsavel_cpf, e.responsavel_email,
                   e.logradouro, e.numero, e.bairro, e.cidade, e.uf, e.cep,
                   e.usuario_id, e.status, e.criado_em, e.atualizado_em
            FROM escolas e
            WHERE e.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(escola_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_escola_by_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM escolas WHERE usuario_id = %s LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_escola_com_usuario(
        self,
        escola_data: Dict[str, Any],
        usuario_data: Dict[str, Any],
        permission_keys: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        # RN-01: criação atômica de Escola + usuário secretário (mesma transação)
        escola_id = str(uuid.uuid4())
        usuario_id = str(uuid.uuid4())

        self.ensure_permissoes(permission_keys or [])

        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuarios (
                    id, nome, sobrenome, email, cpf, senha_hash, senha_algoritmo,
                    telefone, celular, foto_url, perfil_id, polo_id, escola_id, status, criado_em, atualizado_em
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, now(), now()
                )
                """,
                (
                    usuario_id,
                    usuario_data.get("nome", ""),
                    usuario_data.get("sobrenome", ""),
                    usuario_data.get("email"),
                    usuario_data.get("cpf"),
                    usuario_data.get("senha_hash"),
                    usuario_data.get("senha_algoritmo", "argon2id"),
                    usuario_data.get("telefone"),
                    usuario_data.get("celular"),
                    usuario_data.get("foto_url"),
                    usuario_data.get("perfil_id"),
                    usuario_data.get("polo_id"),
                    escola_id,
                    usuario_data.get("status", "ativo"),
                ),
            )

            for k in permission_keys or []:
                cur.execute(
                    """
                    INSERT INTO usuario_permissoes (usuario_id, permissao_id)
                    SELECT %s, id FROM permissoes WHERE chave = %s
                    ON CONFLICT DO NOTHING
                    """,
                    (usuario_id, k.strip().lower()),
                )

            cur.execute(
                """
                INSERT INTO escolas (
                    id, polo_id, nome, responsavel, cpf, email, endereco,
                    responsavel_nome, responsavel_cpf, responsavel_email,
                    logradouro, numero, bairro, cidade, uf, cep,
                    usuario_id, status, criado_em, atualizado_em
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, now(), now()
                )
                """,
                (
                    escola_id,
                    str(escola_data.get("polo_id")) if escola_data.get("polo_id") else None,
                    escola_data.get("nome"),
                    escola_data.get("responsavel"),
                    escola_data.get("cpf"),
                    escola_data.get("email"),
                    escola_data.get("endereco"),
                    escola_data.get("responsavel"),
                    escola_data.get("cpf"),
                    escola_data.get("email"),
                    escola_data.get("logradouro"),
                    escola_data.get("numero"),
                    escola_data.get("bairro"),
                    escola_data.get("cidade"),
                    escola_data.get("uf"),
                    escola_data.get("cep"),
                    usuario_id,
                    escola_data.get("status", "ativo"),
                ),
            )

        return escola_id, usuario_id

    def update_escola_sincronizar_usuario(
        self,
        escola_id: str,
        escola_data: Dict[str, Any],
        usuario_id: str,
        usuario_data: Dict[str, Any],
    ) -> None:
        # RN-01: sincronização atômica dos dados do responsável/secretário
        escola_fields = []
        escola_params: List[Any] = []
        for key, val in escola_data.items():
            escola_fields.append(f"{key} = %s")
            escola_params.append(val)
        escola_fields.append("atualizado_em = now()")
        escola_params.append(str(escola_id))

        user_fields = []
        user_params: List[Any] = []
        for key, val in usuario_data.items():
            user_fields.append(f"{key} = %s")
            user_params.append(val)
        user_fields.append("atualizado_em = now()")
        user_params.append(str(usuario_id))

        with get_db_cursor() as cur:
            cur.execute(f"UPDATE escolas SET {', '.join(escola_fields)} WHERE id = %s", tuple(escola_params))
            cur.execute(f"UPDATE usuarios SET {', '.join(user_fields)} WHERE id = %s", tuple(user_params))

    def desativar_escola_e_usuario(self, escola_id: str, usuario_id: str) -> None:
        # RN-01: exclusão da escola desativa o usuário secretário vinculado
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE escolas SET status = 'inativo', atualizado_em = now() WHERE id = %s",
                (str(escola_id),),
            )
            cur.execute(
                "UPDATE usuarios SET status = 'inativo', atualizado_em = now() WHERE id = %s",
                (str(usuario_id),),
            )

    def get_escola_detalhes(self, escola_id: str) -> Optional[Dict[str, Any]]:
        escola = self.get_escola(escola_id)
        if not escola:
            return None
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM alunos WHERE escola_id = %s AND status = 'ativo'",
                (str(escola_id),),
            )
            escola["total_alunos"] = int((cur.fetchone() or {}).get("total", 0))
        if escola.get("polo_id"):
            polo = self.get_polo(escola["polo_id"])
            escola["polo_nome"] = polo.get("nome") if polo else None
        return escola

    # ---------- Cursos / Módulos / Matérias ----------

    def list_cursos(
        self, query: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if query:
            conditions.append("(lower(c.nome) LIKE %s OR lower(coalesce(c.descricao, '')) LIKE %s)")
            q = f"%{query.strip().lower()}%"
            params.extend([q, q])
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM cursos c {where_clause}"
        data_sql = f"""
            SELECT c.id, c.nome, c.descricao, c.carga_horaria_horas, c.grade_curricular,
                   c.status, c.criado_em, c.atualizado_em
            FROM cursos c {where_clause}
            ORDER BY c.nome ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_curso(self, curso_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM cursos WHERE id = %s LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(curso_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_curso(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO cursos (id, nome, descricao, carga_horaria_horas, grade_curricular, status, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    data.get("nome"),
                    data.get("descricao"),
                    data.get("carga_horaria_horas", 0),
                    json.dumps(data.get("grade_curricular")) if data.get("grade_curricular") is not None else None,
                    data.get("status", "ativo"),
                ),
            )
        return new_id

    def update_curso(self, curso_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            if key == "grade_curricular" and val is not None:
                val = json.dumps(val)
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(curso_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE cursos SET {', '.join(fields)} WHERE id = %s", tuple(params))

    def delete_curso(self, curso_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE cursos SET status = 'inativo', atualizado_em = now() WHERE id = %s", (str(curso_id),))

    def list_modulos(
        self, curso_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if curso_id:
            conditions.append("m.curso_id = %s")
            params.append(str(curso_id))
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM modulos m {where_clause}"
        data_sql = f"""
            SELECT m.id, m.curso_id, m.nome, m.ordem, m.conteudo, m.carga_horaria_horas, m.criado_em, m.atualizado_em
            FROM modulos m {where_clause}
            ORDER BY m.ordem ASC, m.nome ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_modulo(self, modulo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM modulos WHERE id = %s LIMIT 1", (str(modulo_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_modulo(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO modulos (id, curso_id, nome, ordem, conteudo, carga_horaria_horas, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("curso_id")),
                    data.get("nome"),
                    data.get("ordem", 1),
                    data.get("conteudo"),
                    data.get("carga_horaria_horas", 0),
                ),
            )
        return new_id

    def update_modulo(self, modulo_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(modulo_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE modulos SET {', '.join(fields)} WHERE id = %s", tuple(params))

    def delete_modulo(self, modulo_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM modulos WHERE id = %s", (str(modulo_id),))

    def list_materias(
        self,
        curso_id: Optional[str] = None,
        modulo_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if curso_id:
            conditions.append("ma.curso_id = %s")
            params.append(str(curso_id))
        if modulo_id:
            conditions.append("ma.modulo_id = %s")
            params.append(str(modulo_id))
        if query:
            conditions.append("lower(ma.nome) LIKE %s")
            params.append(f"%{query.strip().lower()}%")
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM materias ma {where_clause}"
        data_sql = f"""
            SELECT ma.id, ma.curso_id, ma.modulo_id, ma.nome, ma.ordem, ma.carga_horaria_horas,
                   ma.total_aulas_previstas, ma.tipo, ma.conteudo, ma.preco, ma.status,
                   ma.criado_em, ma.atualizado_em
            FROM materias ma {where_clause}
            ORDER BY ma.ordem ASC, ma.nome ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_materia(self, materia_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM materias WHERE id = %s LIMIT 1", (str(materia_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_materia(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO materias (
                id, curso_id, modulo_id, nome, ordem, carga_horaria_horas,
                total_aulas_previstas, tipo, conteudo, preco, status, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("curso_id")),
                    str(data.get("modulo_id")) if data.get("modulo_id") else None,
                    data.get("nome"),
                    data.get("ordem", 1),
                    data.get("carga_horaria_horas", 0),
                    data.get("total_aulas_previstas", 0),
                    data.get("tipo", "disciplina"),
                    data.get("conteudo"),
                    data.get("preco", 45.0),
                    data.get("status", "ativo"),
                ),
            )
        return new_id

    def update_materia(self, materia_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(materia_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE materias SET {', '.join(fields)} WHERE id = %s", tuple(params))

    def delete_materia(self, materia_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE materias SET status = 'inativo', atualizado_em = now() WHERE id = %s", (str(materia_id),))

    # ---------- Matrículas ----------

    def list_matriculas(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if filtros.get("data_inicio"):
            conditions.append("mt.data_matricula >= %s")
            params.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            conditions.append("mt.data_matricula <= %s")
            params.append(filtros["data_fim"])
        if filtros.get("mes"):
            conditions.append("EXTRACT(MONTH FROM mt.data_matricula) = %s")
            params.append(int(filtros["mes"]))
        if filtros.get("semestre"):
            conditions.append("mt.semestre = %s")
            params.append(int(filtros["semestre"]))
        if filtros.get("ano"):
            conditions.append("mt.ano = %s")
            params.append(int(filtros["ano"]))
        if filtros.get("polo_id"):
            conditions.append("mt.polo_id = %s")
            params.append(str(filtros["polo_id"]))
        if filtros.get("escola_id"):
            conditions.append("mt.escola_id = %s")
            params.append(str(filtros["escola_id"]))
        if filtros.get("modalidade"):
            conditions.append("mt.modalidade = %s")
            params.append(filtros["modalidade"])
        if filtros.get("aluno_id"):
            conditions.append("mt.aluno_id = %s")
            params.append(str(filtros["aluno_id"]))
        if filtros.get("curso_id"):
            conditions.append("mt.curso_id = %s")
            params.append(str(filtros["curso_id"]))
        if filtros.get("status"):
            conditions.append("mt.status = %s")
            params.append(filtros["status"])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM matriculas mt {where_clause}"
        data_sql = f"""
            SELECT mt.id, mt.aluno_id, u.nome AS aluno_nome,
                   mt.curso_id, c.nome AS curso_nome,
                   mt.polo_id, p.nome AS polo_nome,
                   mt.escola_id, e.nome AS escola_nome,
                   mt.modalidade, mt.numero_matricula, mt.semestre, mt.ano,
                   mt.status, mt.data_matricula, mt.criado_em, mt.atualizado_em
            FROM matriculas mt
            LEFT JOIN usuarios u ON mt.aluno_id = u.id
            LEFT JOIN cursos c ON mt.curso_id = c.id
            LEFT JOIN polos p ON mt.polo_id = p.id
            LEFT JOIN escolas e ON mt.escola_id = e.id
            {where_clause}
            ORDER BY mt.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_matricula(self, matricula_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT mt.id, mt.aluno_id, u.nome AS aluno_nome,
                   mt.curso_id, c.nome AS curso_nome,
                   mt.polo_id, p.nome AS polo_nome,
                   mt.escola_id, e.nome AS escola_nome,
                   mt.modalidade, mt.numero_matricula, mt.semestre, mt.ano,
                   mt.status, mt.data_matricula, mt.criado_em, mt.atualizado_em
            FROM matriculas mt
            LEFT JOIN usuarios u ON mt.aluno_id = u.id
            LEFT JOIN cursos c ON mt.curso_id = c.id
            LEFT JOIN polos p ON mt.polo_id = p.id
            LEFT JOIN escolas e ON mt.escola_id = e.id
            WHERE mt.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(matricula_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_matricula(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO matriculas (
                id, aluno_id, curso_id, polo_id, escola_id, modalidade, numero_matricula,
                semestre, ano, status, data_matricula, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()), now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("aluno_id")),
                    str(data.get("curso_id")) if data.get("curso_id") else None,
                    str(data.get("polo_id")) if data.get("polo_id") else None,
                    str(data.get("escola_id")) if data.get("escola_id") else None,
                    data.get("modalidade", "polo"),
                    data.get("numero_matricula") or f"NX-{uuid.uuid4().hex[:8].upper()}",
                    data.get("semestre"),
                    data.get("ano"),
                    data.get("status", "ativa"),
                    data.get("data_matricula"),
                ),
            )
        return new_id

    def update_matricula(self, matricula_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(matricula_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE matriculas SET {', '.join(fields)} WHERE id = %s", tuple(params))

    # ---------- Alunos ----------

    def list_alunos(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = ["u.perfil_id IN (SELECT id FROM perfis WHERE lower(nome) = 'aluno')"]
        params: List[Any] = []
        if filtros.get("data_inicio"):
            conditions.append("a.criado_em >= %s")
            params.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            conditions.append("a.criado_em <= %s")
            params.append(filtros["data_fim"])
        if filtros.get("polo_id"):
            conditions.append("a.polo_id = %s")
            params.append(str(filtros["polo_id"]))
        if filtros.get("escola_id"):
            conditions.append("a.escola_id = %s")
            params.append(str(filtros["escola_id"]))
        if filtros.get("pais"):
            conditions.append("a.pais = %s")
            params.append(filtros["pais"])
        if filtros.get("estado"):
            conditions.append("a.estado = %s")
            params.append(filtros["estado"])
        if filtros.get("curso_id"):
            conditions.append("a.curso_id = %s")
            params.append(str(filtros["curso_id"]))
        if filtros.get("semestre"):
            conditions.append("mt.semestre = %s")
            params.append(int(filtros["semestre"]))
        if filtros.get("ano"):
            conditions.append("mt.ano = %s")
            params.append(int(filtros["ano"]))
        if filtros.get("modalidade"):
            conditions.append("a.modalidade = %s")
            params.append(filtros["modalidade"])
        if filtros.get("q"):
            q = f"%{filtros['q'].strip().lower()}%"
            conditions.append("(lower(u.nome) LIKE %s OR lower(u.sobrenome) LIKE %s OR lower(u.email) LIKE %s OR u.cpf LIKE %s)")
            params.extend([q, q, q, q])

        where_clause = "WHERE " + " AND ".join(conditions)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            LEFT JOIN matriculas mt ON mt.aluno_id = u.id
            {where_clause}
        """
        data_sql = f"""
            SELECT a.id, a.usuario_id, u.nome, u.sobrenome, u.email, u.cpf,
                   a.data_nascimento, a.pais, a.estado,
                   a.polo_id, p.nome AS polo_nome,
                   a.escola_id, e.nome AS escola_nome,
                   a.modalidade, a.numero_matricula, a.status, a.ultima_movimentacao_em,
                   a.curso_id, c.nome AS curso_nome, mt.semestre, mt.ano,
                   a.criado_em, a.atualizado_em
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            LEFT JOIN polos p ON a.polo_id = p.id
            LEFT JOIN escolas e ON a.escola_id = e.id
            LEFT JOIN cursos c ON a.curso_id = c.id
            LEFT JOIN matriculas mt ON mt.aluno_id = u.id
            {where_clause}
            ORDER BY u.nome ASC
            LIMIT %s OFFSET %s
        """
        total, rows = _exec_paginated(count_sql, data_sql, params, limit, offset)
        # Colunas obrigatórias (seção 9.1): presenças puxadas da lista de chamada (RN-07)
        for r in rows:
            qtd, pct = self.count_presencas_aluno(str(r["usuario_id"]))
            r["quantidade_presencas"] = qtd
            r["percentual_presenca"] = pct
        return total, rows

    def get_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        # Aceita tanto id da tabela alunos quanto id do usuário
        sql_by_aluno_id = """
            SELECT a.id, a.usuario_id, u.nome, u.sobrenome, u.email, u.cpf,
                   a.data_nascimento, a.pais, a.estado,
                   a.polo_id, p.nome AS polo_nome,
                   a.escola_id, e.nome AS escola_nome,
                   a.modalidade, a.numero_matricula, a.status, a.ultima_movimentacao_em,
                   a.curso_id, a.criado_em, a.atualizado_em
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            LEFT JOIN polos p ON a.polo_id = p.id
            LEFT JOIN escolas e ON a.escola_id = e.id
            WHERE a.id = %s
            LIMIT 1
        """
        sql_by_usuario_id = sql_by_aluno_id.replace("WHERE a.id = %s", "WHERE a.usuario_id = %s")
        with get_db_cursor() as cur:
            cur.execute(sql_by_aluno_id, (str(aluno_id),))
            row = cur.fetchone()
            if not row:
                cur.execute(sql_by_usuario_id, (str(aluno_id),))
                row = cur.fetchone()
            if not row:
                return None
            out = dict(row)
            qtd, pct = self.count_presencas_aluno(str(out["usuario_id"]))
            out["quantidade_presencas"] = qtd
            out["percentual_presenca"] = pct
            return out

    def create_aluno_com_usuario(
        self,
        usuario_data: Dict[str, Any],
        aluno_data: Dict[str, Any],
        matricula_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Optional[str]]:
        # Criação atômica de usuário (perfil aluno) + registro em alunos + matrícula inicial
        usuario_id = str(uuid.uuid4())
        aluno_id = str(uuid.uuid4())
        matricula_id: Optional[str] = None

        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuarios (
                    id, nome, sobrenome, email, cpf, senha_hash, senha_algoritmo,
                    telefone, celular, foto_url, perfil_id, polo_id, escola_id, status, criado_em, atualizado_em
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, now(), now()
                )
                """,
                (
                    usuario_id,
                    usuario_data.get("nome", ""),
                    usuario_data.get("sobrenome", ""),
                    usuario_data.get("email"),
                    usuario_data.get("cpf"),
                    usuario_data.get("senha_hash"),
                    usuario_data.get("senha_algoritmo", "argon2id"),
                    usuario_data.get("telefone"),
                    usuario_data.get("celular"),
                    usuario_data.get("foto_url"),
                    usuario_data.get("perfil_id"),
                    aluno_data.get("polo_id"),
                    aluno_data.get("escola_id"),
                    usuario_data.get("status", "ativo"),
                ),
            )
            cur.execute(
                """
                INSERT INTO alunos (
                    id, usuario_id, polo_id, escola_id, modalidade, numero_matricula,
                    data_nascimento, pais, estado, curso_id, status, ultima_movimentacao_em, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now(), now())
                """,
                (
                    aluno_id,
                    usuario_id,
                    aluno_data.get("polo_id"),
                    aluno_data.get("escola_id"),
                    aluno_data.get("modalidade", "polo"),
                    aluno_data.get("numero_matricula") or f"NX-{uuid.uuid4().hex[:8].upper()}",
                    aluno_data.get("data_nascimento"),
                    aluno_data.get("pais"),
                    aluno_data.get("estado"),
                    aluno_data.get("curso_id"),
                    aluno_data.get("status", "ativo"),
                ),
            )
            if matricula_data:
                matricula_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO matriculas (
                        id, aluno_id, curso_id, polo_id, escola_id, modalidade, numero_matricula,
                        semestre, ano, status, data_matricula, criado_em, atualizado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now(), now())
                    """,
                    (
                        matricula_id,
                        usuario_id,
                        str(matricula_data.get("curso_id")) if matricula_data.get("curso_id") else None,
                        str(matricula_data.get("polo_id")) if matricula_data.get("polo_id") else None,
                        str(matricula_data.get("escola_id")) if matricula_data.get("escola_id") else None,
                        matricula_data.get("modalidade", "polo"),
                        matricula_data.get("numero_matricula") or f"NX-{uuid.uuid4().hex[:8].upper()}",
                        matricula_data.get("semestre"),
                        matricula_data.get("ano"),
                        matricula_data.get("status", "ativa"),
                    ),
                )
        return usuario_id, aluno_id, matricula_id

    def update_aluno(self, aluno_id: str, data: Dict[str, Any]) -> None:
        # Atualiza campos da tabela alunos (e dados de usuário se fornecidos em usuario_data)
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(aluno_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE alunos SET {', '.join(fields)} WHERE id = %s", tuple(params))

    def marcar_desistentes_automatico(self, cutoff: datetime) -> int:
        # RN-04: > 1 ano sem movimentação/compra -> status "desistente", desvinculado do polo
        with get_db_cursor() as cur:
            cur.execute(
                """
                UPDATE alunos
                SET status = 'desistente', polo_id = NULL, atualizado_em = now()
                WHERE status = 'ativo' AND ultima_movimentacao_em IS NOT NULL AND ultima_movimentacao_em < %s
                RETURNING id, usuario_id
                """,
                (cutoff,),
            )
            marcados = cur.fetchall()
            for r in marcados:
                cur.execute(
                    """
                    INSERT INTO alunos_churn (id, aluno_id, motivo, data_marcacao, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, now(), now(), now())
                    ON CONFLICT DO NOTHING
                    """,
                    (str(uuid.uuid4()), str(r["usuario_id"]), "Inatividade superior a 1 ano (churn automático)"),
                )
            return len(marcados)

    # ---------- EAD ----------

    def list_matriculas_ead(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if filtros.get("q"):
            q = f"%{filtros['q'].strip().lower()}%"
            conditions.append("(lower(u.nome) LIKE %s OR lower(u.sobrenome) LIKE %s OR lower(u.email) LIKE %s)")
            params.extend([q, q, q])
        if filtros.get("curso_id"):
            conditions.append("me.curso_id = %s")
            params.append(str(filtros["curso_id"]))
        if filtros.get("status"):
            conditions.append("me.status = %s")
            params.append(filtros["status"])
        if filtros.get("origem"):
            conditions.append("me.origem = %s")
            params.append(filtros["origem"])
        if filtros.get("data_inicio"):
            conditions.append("me.criado_em >= %s")
            params.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            conditions.append("me.criado_em <= %s")
            params.append(filtros["data_fim"])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM matriculas_ead me JOIN usuarios u ON me.aluno_id = u.id {where_clause}"
        data_sql = f"""
            SELECT me.id, me.matricula_id, me.aluno_id, u.nome AS aluno_nome,
                   me.curso_id, c.nome AS curso_nome,
                   me.materia_atual_id, m.nome AS materia_atual_nome,
                   me.progresso_pct, me.ultimo_acesso_em, me.origem, me.status,
                   me.criado_em, me.atualizado_em
            FROM matriculas_ead me
            JOIN usuarios u ON me.aluno_id = u.id
            LEFT JOIN cursos c ON me.curso_id = c.id
            LEFT JOIN materias m ON me.materia_atual_id = m.id
            {where_clause}
            ORDER BY COALESCE(me.ultimo_acesso_em, me.criado_em) DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_matricula_ead(self, matricula_ead_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT me.id, me.matricula_id, me.aluno_id, u.nome AS aluno_nome,
                   me.curso_id, c.nome AS curso_nome,
                   me.materia_atual_id, m.nome AS materia_atual_nome,
                   me.progresso_pct, me.ultimo_acesso_em, me.origem, me.status,
                   me.criado_em, me.atualizado_em
            FROM matriculas_ead me
            JOIN usuarios u ON me.aluno_id = u.id
            LEFT JOIN cursos c ON me.curso_id = c.id
            LEFT JOIN materias m ON me.materia_atual_id = m.id
            WHERE me.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(matricula_ead_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_matricula_ead(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO matriculas_ead (
                id, matricula_id, aluno_id, curso_id, materia_atual_id,
                progresso_pct, ultimo_acesso_em, origem, status, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("matricula_id")) if data.get("matricula_id") else None,
                    str(data.get("aluno_id")),
                    str(data.get("curso_id")),
                    str(data.get("materia_atual_id")) if data.get("materia_atual_id") else None,
                    data.get("progresso_pct", 0),
                    data.get("ultimo_acesso_em"),
                    data.get("origem", "manual"),
                    data.get("status", "ativa"),
                ),
            )
        return new_id

    def update_matricula_ead(self, matricula_ead_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(matricula_ead_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE matriculas_ead SET {', '.join(fields)} WHERE id = %s", tuple(params))

    def get_matricula_ead_por_aluno(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM matriculas_ead WHERE aluno_id = %s ORDER BY criado_em DESC LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def count_liberacoes_ead_mes(self, aluno_id: str, ano: int, mes: int) -> int:
        sql = """
            SELECT COUNT(*) AS total
            FROM ead_liberacoes l
            JOIN matriculas_ead me ON l.matricula_ead_id = me.id
            WHERE me.aluno_id = %s
              AND EXTRACT(YEAR FROM l.data_liberacao) = %s
              AND EXTRACT(MONTH FROM l.data_liberacao) = %s
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id), int(ano), int(mes)))
            row = cur.fetchone()
            return int(row["total"]) if row else 0

    def registrar_liberacao_ead(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO ead_liberacoes (id, matricula_ead_id, materia_id, data_liberacao, status, criado_em, atualizado_em)
            VALUES (%s, %s, %s, COALESCE(%s, now()), %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("matricula_ead_id")),
                    str(data.get("materia_id")),
                    data.get("data_liberacao"),
                    data.get("status", "liberada"),
                ),
            )
        return new_id

    def get_ultima_liberacao_ead(self, matricula_ead_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT * FROM ead_liberacoes
            WHERE matricula_ead_id = %s
            ORDER BY data_liberacao DESC, criado_em DESC
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(matricula_ead_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_ead_calendario(
        self, curso_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if curso_id:
            conditions.append("ec.curso_id = %s")
            params.append(str(curso_id))
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM ead_calendario ec {where_clause}"
        data_sql = f"""
            SELECT ec.id, ec.materia_id, m.nome AS materia_nome, ec.ordem, ec.data_liberacao, ec.ano, ec.criado_em
            FROM ead_calendario ec
            LEFT JOIN materias m ON ec.materia_id = m.id
            {where_clause}
            ORDER BY ec.ordem ASC, ec.data_liberacao ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def create_ead_calendario(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO ead_calendario (id, materia_id, curso_id, ordem, data_liberacao, ano, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("materia_id")),
                    str(data.get("curso_id")) if data.get("curso_id") else None,
                    data.get("ordem", 1),
                    data.get("data_liberacao"),
                    data.get("ano"),
                ),
            )
        return new_id

    def delete_ead_calendario(self, calendario_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM ead_calendario WHERE id = %s", (str(calendario_id),))

    def list_feed_noticias(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        count_sql = "SELECT COUNT(*) AS total FROM feed_noticias WHERE status = 'publicado'"
        data_sql = """
            SELECT fn.id, fn.titulo, fn.conteudo, fn.autor_id, u.nome AS autor_nome,
                   p.nome AS autor_perfil, fn.status, fn.criado_em
            FROM feed_noticias fn
            LEFT JOIN usuarios u ON fn.autor_id = u.id
            LEFT JOIN perfis p ON u.perfil_id = p.id
            WHERE fn.status = 'publicado'
            ORDER BY fn.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, [], limit, offset)

    def create_feed_noticia(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO feed_noticias (id, titulo, conteudo, autor_id, status, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    data.get("titulo"),
                    data.get("conteudo"),
                    str(data.get("autor_id")) if data.get("autor_id") else None,
                    data.get("status", "publicado"),
                ),
            )
        return new_id

    def delete_feed_noticia(self, noticia_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM feed_noticias WHERE id = %s", (str(noticia_id),))

    def list_lembretes(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        count_sql = "SELECT COUNT(*) AS total FROM lembretes"
        data_sql = """
            SELECT id, titulo, mensagem, tipo, data_exibicao, destino_perfil, materia_id, criado_em
            FROM lembretes
            ORDER BY criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, [], limit, offset)

    def create_lembrete(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO lembretes (id, titulo, mensagem, tipo, data_exibicao, destino_perfil, materia_id, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    data.get("titulo"),
                    data.get("conteudo") or data.get("mensagem"),
                    data.get("tipo", "popup"),
                    data.get("data_exibicao"),
                    data.get("destino_perfil"),
                    str(data.get("materia_id")) if data.get("materia_id") else None,
                ),
            )
        return new_id

    def delete_lembrete(self, lembrete_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM lembretes WHERE id = %s", (str(lembrete_id),))

    # ---------- Licenças / Estoque ----------

    def list_licencas_estoque(
        self, query: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if query:
            conditions.append("lower(coalesce(m.nome, '')) LIKE %s")
            params.append(f"%{query.strip().lower()}%")
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM licencas_estoque le {where_clause}"
        data_sql = f"""
            SELECT le.id, le.materia_id, m.nome AS materia_nome, le.tipo, le.quantidade,
                   le.criado_em, le.atualizado_em
            FROM licencas_estoque le
            LEFT JOIN materias m ON le.materia_id = m.id
            {where_clause}
            ORDER BY m.nome ASC, le.tipo ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_licenca_estoque(self, materia_id: str, tipo: str = "licenca") -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM licencas_estoque WHERE materia_id = %s AND tipo = %s LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(materia_id), tipo))
            row = cur.fetchone()
            return dict(row) if row else None

    def ajustar_licenca_estoque(
        self,
        materia_id: str,
        tipo: str,
        delta: int,
        movimentacao: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Atualiza (ou cria) o estoque da matéria e registra a movimentação na mesma transação
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO licencas_estoque (id, materia_id, tipo, quantidade, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, now(), now())
                ON CONFLICT (materia_id, tipo) DO NOTHING
                """,
                (str(uuid.uuid4()), str(materia_id), tipo, 0),
            )
            cur.execute(
                """
                UPDATE licencas_estoque
                SET quantidade = quantidade + %s, atualizado_em = now()
                WHERE materia_id = %s AND tipo = %s
                RETURNING id, materia_id, tipo, quantidade, criado_em, atualizado_em
                """,
                (int(delta), str(materia_id), tipo),
            )
            row = cur.fetchone()
            if movimentacao:
                cur.execute(
                    """
                    INSERT INTO licencas_movimentacoes (
                        id, materia_id, tipo_item, tipo_movimento, quantidade,
                        destino_tipo, polo_id, escola_id, usuario_id, observacao, criado_em
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    """,
                    (
                        str(uuid.uuid4()),
                        str(materia_id),
                        tipo,
                        movimentacao.get("tipo_movimento", "ajuste"),
                        int(movimentacao.get("quantidade", abs(delta))),
                        movimentacao.get("destino_tipo"),
                        str(movimentacao.get("polo_id")) if movimentacao.get("polo_id") else None,
                        str(movimentacao.get("escola_id")) if movimentacao.get("escola_id") else None,
                        str(movimentacao.get("usuario_id")) if movimentacao.get("usuario_id") else None,
                        movimentacao.get("observacao"),
                    ),
                )
            return dict(row) if row else {}

    def list_licencas_movimentacoes(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if filtros.get("data_inicio"):
            conditions.append("lm.criado_em >= %s")
            params.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            conditions.append("lm.criado_em <= %s")
            params.append(filtros["data_fim"])
        if filtros.get("mes"):
            conditions.append("EXTRACT(MONTH FROM lm.criado_em) = %s")
            params.append(int(filtros["mes"]))
        if filtros.get("ano"):
            conditions.append("EXTRACT(YEAR FROM lm.criado_em) = %s")
            params.append(int(filtros["ano"]))
        if filtros.get("polo_id"):
            conditions.append("lm.polo_id = %s")
            params.append(str(filtros["polo_id"]))
        if filtros.get("escola_id"):
            conditions.append("lm.escola_id = %s")
            params.append(str(filtros["escola_id"]))
        if filtros.get("materia_id"):
            conditions.append("lm.materia_id = %s")
            params.append(str(filtros["materia_id"]))
        if filtros.get("tipo_movimento"):
            conditions.append("lm.tipo_movimento = %s")
            params.append(filtros["tipo_movimento"])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM licencas_movimentacoes lm {where_clause}"
        data_sql = f"""
            SELECT lm.id, lm.materia_id, m.nome AS materia_nome, lm.tipo_item, lm.tipo_movimento,
                   lm.quantidade, lm.destino_tipo, lm.polo_id, lm.escola_id,
                   lm.usuario_id, u.nome AS usuario_nome, lm.observacao, lm.criado_em
            FROM licencas_movimentacoes lm
            LEFT JOIN materias m ON lm.materia_id = m.id
            LEFT JOIN usuarios u ON lm.usuario_id = u.id
            {where_clause}
            ORDER BY lm.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    # ---------- Aulas / Presenças / Anexos / Atas ----------

    def list_aulas(
        self,
        professor_id: Optional[str] = None,
        materia_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if professor_id:
            conditions.append("a.professor_id = %s")
            params.append(str(professor_id))
        if materia_id:
            conditions.append("a.materia_id = %s")
            params.append(str(materia_id))
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM aulas a {where_clause}"
        data_sql = f"""
            SELECT a.id, a.materia_id, m.nome AS materia_nome, a.professor_id, u.nome AS professor_nome,
                   a.data_aula, a.assunto, a.criado_em
            FROM aulas a
            LEFT JOIN materias m ON a.materia_id = m.id
            LEFT JOIN usuarios u ON a.professor_id = u.id
            {where_clause}
            ORDER BY a.data_aula DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_aula(self, aula_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT a.id, a.materia_id, m.nome AS materia_nome, a.professor_id, u.nome AS professor_nome,
                   a.data_aula, a.assunto, a.criado_em
            FROM aulas a
            LEFT JOIN materias m ON a.materia_id = m.id
            LEFT JOIN usuarios u ON a.professor_id = u.id
            WHERE a.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aula_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_aula(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO aulas (id, materia_id, professor_id, data_aula, assunto, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("materia_id")),
                    str(data.get("professor_id")),
                    data.get("data_aula"),
                    data.get("assunto"),
                ),
            )
            # RN-07: se informado, atualiza o total de aulas previstas da matéria
            if data.get("total_aulas_previstas") is not None:
                cur.execute(
                    "UPDATE materias SET total_aulas_previstas = %s, atualizado_em = now() WHERE id = %s",
                    (int(data["total_aulas_previstas"]), str(data.get("materia_id"))),
                )
        return new_id

    def registrar_presencas(
        self, aula_id: str, registros: List[Dict[str, Any]], registrado_por: Optional[str] = None
    ) -> None:
        # Lista de chamada: upsert de presença por aluno na aula (mesma transação)
        with get_db_cursor() as cur:
            for r in registros:
                cur.execute(
                    """
                    INSERT INTO presencas (id, aula_id, aluno_id, presente, registrado_por, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, now(), now())
                    ON CONFLICT (aula_id, aluno_id) DO UPDATE
                    SET presente = EXCLUDED.presente, registrado_por = EXCLUDED.registrado_por, atualizado_em = now()
                    """,
                    (
                        str(uuid.uuid4()),
                        str(aula_id),
                        str(r.get("aluno_id")),
                        bool(r.get("presente")),
                        str(registrado_por) if registrado_por else None,
                    ),
                )

    def list_presencas(
        self,
        aula_id: Optional[str] = None,
        aluno_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if aula_id:
            conditions.append("pr.aula_id = %s")
            params.append(str(aula_id))
        if aluno_id:
            conditions.append("pr.aluno_id = %s")
            params.append(str(aluno_id))
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM presencas pr {where_clause}"
        data_sql = f"""
            SELECT pr.id, pr.aula_id, pr.aluno_id, u.nome AS aluno_nome, pr.presente,
                   pr.registrado_por, pr.criado_em
            FROM presencas pr
            LEFT JOIN usuarios u ON pr.aluno_id = u.id
            {where_clause}
            ORDER BY pr.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_presencas_resumo_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        # RN-07: percentual = (presenças / total_aulas_previstas) * 100 por matéria
        sql = """
            SELECT m.id AS materia_id, m.nome AS materia_nome, m.total_aulas_previstas,
                   COUNT(pr.id) FILTER (WHERE pr.presente = TRUE) AS presencas
            FROM materias m
            JOIN matriculas mt ON mt.curso_id = m.curso_id AND mt.aluno_id = %s
            LEFT JOIN aulas au ON au.materia_id = m.id
            LEFT JOIN presencas pr ON pr.aula_id = au.id AND pr.aluno_id = %s
            GROUP BY m.id, m.nome, m.total_aulas_previstas
            ORDER BY m.ordem ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id), str(aluno_id)))
            rows = [dict(r) for r in cur.fetchall()]
        out = []
        for r in rows:
            previstas = int(r.get("total_aulas_previstas") or 0)
            presencas = int(r.get("presencas") or 0)
            pct = round((presencas / previstas) * 100.0, 1) if previstas > 0 else 0.0
            out.append({
                "materia_id": r["materia_id"],
                "materia_nome": r.get("materia_nome"),
                "total_aulas_previstas": previstas,
                "presencas": presencas,
                "percentual": pct,
            })
        return out

    def get_presencas_resumo_professor(self, professor_id: str) -> List[Dict[str, Any]]:
        # Lista de chamada por aluno nas matérias lecionadas pelo professor
        sql = """
            SELECT pr.aluno_id, u.nome AS aluno_nome,
                   COUNT(DISTINCT pr.aula_id) AS aulas_registradas,
                   COUNT(pr.id) FILTER (WHERE pr.presente = TRUE) AS presencas,
                   m.id AS materia_id, m.nome AS materia_nome, m.total_aulas_previstas
            FROM aulas au
            JOIN presencas pr ON pr.aula_id = au.id
            JOIN usuarios u ON pr.aluno_id = u.id
            JOIN materias m ON au.materia_id = m.id
            WHERE au.professor_id = %s
            GROUP BY pr.aluno_id, u.nome, m.id, m.nome, m.total_aulas_previstas
            ORDER BY u.nome ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(professor_id),))
            rows = [dict(r) for r in cur.fetchall()]
        out = []
        for r in rows:
            previstas = int(r.get("total_aulas_previstas") or 0)
            presencas = int(r.get("presencas") or 0)
            pct = round((presencas / previstas) * 100.0, 1) if previstas > 0 else 0.0
            out.append({
                "aluno_id": r["aluno_id"],
                "aluno_nome": r.get("aluno_nome"),
                "materia_id": r["materia_id"],
                "materia_nome": r.get("materia_nome"),
                "aulas_registradas": int(r.get("aulas_registradas") or 0),
                "presencas": presencas,
                "percentual": pct,
            })
        return out

    def count_presencas_aluno(self, aluno_id: str) -> Tuple[int, float]:
        # RN-07: agregado geral do aluno: presenças / total de aulas previstas * 100
        sql = """
            SELECT COALESCE(SUM(previstas), 0) AS total_previstas
            FROM (
                SELECT m.total_aulas_previstas AS previstas
                FROM materias m
                JOIN matriculas mt ON mt.curso_id = m.curso_id AND mt.aluno_id = %s
                GROUP BY m.id, m.total_aulas_previstas
            ) t
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id),))
            row = cur.fetchone()
            total_previstas = int(row["total_previstas"]) if row else 0

            cur.execute(
                "SELECT COUNT(*) AS total FROM presencas WHERE aluno_id = %s AND presente = TRUE",
                (str(aluno_id),),
            )
            row2 = cur.fetchone()
            presencas = int(row2["total"]) if row2 else 0

        pct = round((presencas / total_previstas) * 100.0, 1) if total_previstas > 0 else 0.0
        return presencas, pct

    def list_anexos_aula(
        self,
        professor_id: Optional[str] = None,
        aula_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if professor_id:
            conditions.append("au.professor_id = %s")
            params.append(str(professor_id))
        if aula_id:
            conditions.append("an.aula_id = %s")
            params.append(str(aula_id))
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM anexos_aula an JOIN aulas au ON an.aula_id = au.id {where_clause}"
        data_sql = f"""
            SELECT an.id, an.aula_id, au.materia_id, m.nome AS materia_nome, au.data_aula,
                   an.nome_arquivo, an.url_arquivo, an.criado_em
            FROM anexos_aula an
            JOIN aulas au ON an.aula_id = au.id
            LEFT JOIN materias m ON au.materia_id = m.id
            {where_clause}
            ORDER BY au.data_aula DESC, an.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def list_atas(
        self,
        professor_id: Optional[str] = None,
        aula_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if professor_id:
            conditions.append("at.professor_id = %s")
            params.append(str(professor_id))
        if aula_id:
            conditions.append("at.aula_id = %s")
            params.append(str(aula_id))
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM atas at {where_clause}"
        data_sql = f"""
            SELECT at.id, at.aula_id, au.materia_id, m.nome AS materia_nome, au.data_aula,
                   at.professor_id, u.nome AS professor_nome, at.conteudo, at.criado_em
            FROM atas at
            JOIN aulas au ON at.aula_id = au.id
            LEFT JOIN materias m ON au.materia_id = m.id
            LEFT JOIN usuarios u ON at.professor_id = u.id
            {where_clause}
            ORDER BY au.data_aula DESC, at.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    # ---------- Certificados (RN-05) ----------

    def list_certificados(
        self,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if query:
            q = f"%{query.strip().lower()}%"
            conditions.append("(lower(u.nome) LIKE %s OR lower(u.sobrenome) LIKE %s OR lower(coalesce(ct.numero_certificado, '')) LIKE %s)")
            params.extend([q, q, q])
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM certificados ct JOIN usuarios u ON ct.aluno_id = u.id {where_clause}"
        data_sql = f"""
            SELECT ct.id, ct.aluno_id, u.nome AS aluno_nome, ct.matricula_id,
                   ct.numero_certificado, ct.data_emissao, ct.status, ct.criado_em
            FROM certificados ct
            JOIN usuarios u ON ct.aluno_id = u.id
            {where_clause}
            ORDER BY ct.data_emissao DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_certificado(self, certificado_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT ct.id, ct.aluno_id, u.nome AS aluno_nome, ct.matricula_id,
                   ct.numero_certificado, ct.data_emissao, ct.status, ct.criado_em
            FROM certificados ct
            JOIN usuarios u ON ct.aluno_id = u.id
            WHERE ct.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(certificado_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_certificado(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO certificados (
                id, aluno_id, matricula_id, numero_certificado, data_emissao,
                data_entrega_estagio_teologia, data_entrega_estagio_homiletica, status, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("aluno_id")),
                    str(data.get("matricula_id")) if data.get("matricula_id") else None,
                    data.get("numero_certificado") or f"CERT-{uuid.uuid4().hex[:8].upper()}",
                    data.get("data_emissao"),
                    data.get("data_entrega_estagio_teologia"),
                    data.get("data_entrega_estagio_homiletica"),
                    data.get("status", "emitido"),
                ),
            )
        return new_id

    def count_certificados(self) -> int:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM certificados")
            row = cur.fetchone()
            return int(row["total"]) if row else 0

    def get_estagios_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        # RN-05: entrega dos 2 estágios (Teologia do Ministério + Homilética) no histórico
        sql = """
            SELECT h.materia_id, h.nome_materia, h.status, h.atualizado_em AS data_entrega
            FROM historico_alunos h
            WHERE h.aluno_id = %s
              AND (
                lower(h.nome_materia) LIKE '%teologia do ministério%'
                OR lower(h.nome_materia) LIKE '%teologia do ministerio%'
                OR lower(h.nome_materia) LIKE '%homilética%'
                OR lower(h.nome_materia) LIKE '%homiletica%'
              )
            ORDER BY h.criado_em ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id),))
            return [dict(r) for r in cur.fetchall()]

    def get_materias_pendentes_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        # RN-05: matérias do curso ainda não concluídas/aprovadas no histórico
        sql = """
            SELECT m.id, m.nome, m.total_aulas_previstas
            FROM materias m
            JOIN matriculas mt ON mt.curso_id = m.curso_id AND mt.aluno_id = %s AND mt.status IN ('ativa', 'trancada')
            WHERE m.status = 'ativo'
              AND NOT EXISTS (
                SELECT 1 FROM historico_alunos h
                WHERE h.aluno_id = %s AND h.materia_id = m.id AND h.status = 'aprovado'
              )
            ORDER BY m.ordem ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id), str(aluno_id)))
            return [dict(r) for r in cur.fetchall()]

    # ---------- Chat (RN-06) ----------

    def list_chat_conversas(
        self,
        usuario_id: Optional[str] = None,
        tipo: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if usuario_id:
            # Só conversas em que o usuário participa
            conditions.append(
                "cv.id IN (SELECT cp.conversa_id FROM chat_participantes cp WHERE cp.usuario_id = %s)"
            )
            params.append(str(usuario_id))
        if tipo:
            conditions.append("cv.tipo = %s")
            params.append(tipo)
        if status:
            conditions.append("cv.status = %s")
            params.append(status)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM chat_conversas cv {where_clause}"
        data_sql = f"""
            SELECT cv.id, cv.tipo, cv.nome, cv.status, cv.criado_por, cv.criado_em,
                   (SELECT COUNT(*) FROM chat_mensagens cm WHERE cm.conversa_id = cv.id) AS total_mensagens,
                   (SELECT cm.conteudo FROM chat_mensagens cm WHERE cm.conversa_id = cv.id
                    ORDER BY cm.criado_em DESC LIMIT 1) AS ultima_mensagem
            FROM chat_conversas cv
            {where_clause}
            ORDER BY cv.criado_em DESC
            LIMIT %s OFFSET %s
        """
        total, rows = _exec_paginated(count_sql, data_sql, params, limit, offset)
        for r in rows:
            r["participantes"] = self.get_chat_participantes(str(r["id"]))
        return total, rows

    def get_chat_conversa(self, conversa_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT cv.id, cv.tipo, cv.nome, cv.status, cv.criado_por, cv.criado_em,
                   (SELECT COUNT(*) FROM chat_mensagens cm WHERE cm.conversa_id = cv.id) AS total_mensagens,
                   (SELECT cm.conteudo FROM chat_mensagens cm WHERE cm.conversa_id = cv.id
                    ORDER BY cm.criado_em DESC LIMIT 1) AS ultima_mensagem
            FROM chat_conversas cv
            WHERE cv.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(conversa_id),))
            row = cur.fetchone()
            if not row:
                return None
            out = dict(row)
            out["participantes"] = self.get_chat_participantes(conversa_id)
            return out

    def create_chat_conversa(
        self,
        tipo: str,
        criado_por: str,
        nome: Optional[str] = None,
        participantes: Optional[List[str]] = None,
    ) -> str:
        conversa_id = str(uuid.uuid4())
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_conversas (id, tipo, nome, status, criado_por, criado_em, atualizado_em)
                VALUES (%s, %s, %s, 'ativa', %s, now(), now())
                """,
                (conversa_id, tipo, nome, str(criado_por)),
            )
            if tipo == "grupo":
                cur.execute(
                    """
                    INSERT INTO chat_grupos (id, conversa_id, nome, criado_por, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, %s, now(), now())
                    """,
                    (str(uuid.uuid4()), conversa_id, nome, str(criado_por)),
                )
            for uid in participantes or [criado_por]:
                cur.execute(
                    """
                    INSERT INTO chat_participantes (id, conversa_id, usuario_id, criado_em)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT DO NOTHING
                    """,
                    (str(uuid.uuid4()), conversa_id, str(uid)),
                )
        return conversa_id

    def add_chat_participantes(self, conversa_id: str, usuario_ids: List[str]) -> None:
        with get_db_cursor() as cur:
            for uid in usuario_ids:
                cur.execute(
                    """
                    INSERT INTO chat_participantes (id, conversa_id, usuario_id, criado_em)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT DO NOTHING
                    """,
                    (str(uuid.uuid4()), str(conversa_id), str(uid)),
                )

    def get_chat_participantes(self, conversa_id: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT cp.usuario_id, u.nome, p.nome AS perfil
            FROM chat_participantes cp
            JOIN usuarios u ON cp.usuario_id = u.id
            LEFT JOIN perfis p ON u.perfil_id = p.id
            WHERE cp.conversa_id = %s
            ORDER BY u.nome ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(conversa_id),))
            return [dict(r) for r in cur.fetchall()]

    def update_chat_conversa(self, conversa_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(conversa_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE chat_conversas SET {', '.join(fields)} WHERE id = %s", tuple(params))

    def delete_chat_conversa(self, conversa_id: str) -> None:
        # Exclusão em cascata: mensagens, grupos e participantes (FK ON DELETE CASCADE)
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM chat_conversas WHERE id = %s", (str(conversa_id),))

    def list_chat_mensagens(
        self, conversa_id: str, limit: int = 200, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        count_sql = "SELECT COUNT(*) AS total FROM chat_mensagens WHERE conversa_id = %s"
        data_sql = """
            SELECT cm.id, cm.conversa_id, cm.remetente_id, u.nome AS remetente_nome,
                   cm.conteudo, cm.lida, cm.lida_em, cm.criado_em
            FROM chat_mensagens cm
            LEFT JOIN usuarios u ON cm.remetente_id = u.id
            WHERE cm.conversa_id = %s
            ORDER BY cm.criado_em ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, [str(conversa_id)], limit, offset)

    def create_chat_mensagem(self, conversa_id: str, remetente_id: str, conteudo: str) -> str:
        msg_id = str(uuid.uuid4())
        sql = """
            INSERT INTO chat_mensagens (id, conversa_id, remetente_id, conteudo, lida, criado_em)
            VALUES (%s, %s, %s, %s, FALSE, now())
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (msg_id, str(conversa_id), str(remetente_id), conteudo))
        return msg_id

    def marcar_mensagem_lida(self, mensagem_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE chat_mensagens SET lida = TRUE, lida_em = now() WHERE id = %s",
                (str(mensagem_id),),
            )

    # ---------- Financeiro ----------

    def list_vendas(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]], float]:
        conditions = []
        params: List[Any] = []
        if filtros.get("data_inicio"):
            conditions.append("v.criado_em >= %s")
            params.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            conditions.append("v.criado_em <= %s")
            params.append(filtros["data_fim"])
        if filtros.get("mes"):
            conditions.append("EXTRACT(MONTH FROM v.criado_em) = %s")
            params.append(int(filtros["mes"]))
        if filtros.get("ano"):
            conditions.append("EXTRACT(YEAR FROM v.criado_em) = %s")
            params.append(int(filtros["ano"]))
        if filtros.get("polo_id"):
            conditions.append("v.polo_id = %s")
            params.append(str(filtros["polo_id"]))
        if filtros.get("escola_id"):
            conditions.append("v.escola_id = %s")
            params.append(str(filtros["escola_id"]))
        if filtros.get("modalidade"):
            conditions.append("v.modalidade = %s")
            params.append(filtros["modalidade"])
        if filtros.get("tipo_item"):
            conditions.append("v.tipo_item = %s")
            params.append(filtros["tipo_item"])
        if filtros.get("aluno_id"):
            conditions.append("v.aluno_id = %s")
            params.append(str(filtros["aluno_id"]))

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"""
            SELECT COUNT(*) AS total, COALESCE(SUM(v.valor), 0) AS total_valor
            FROM vendas v {where_clause}
        """
        data_sql = f"""
            SELECT v.id, v.descricao, v.modalidade, v.tipo_item, v.valor, v.quantidade,
                   v.materia_id, m.nome AS materia_nome,
                   v.polo_id, p.nome AS polo_nome,
                   v.escola_id, e.nome AS escola_nome,
                   v.aluno_id, v.criado_por, v.criado_em
            FROM vendas v
            LEFT JOIN materias m ON v.materia_id = m.id
            LEFT JOIN polos p ON v.polo_id = p.id
            LEFT JOIN escolas e ON v.escola_id = e.id
            {where_clause}
            ORDER BY v.criado_em DESC
            LIMIT %s OFFSET %s
        """
        with get_db_cursor() as cur:
            cur.execute(count_sql, tuple(params))
            row = cur.fetchone()
            total = int(row["total"]) if row else 0
            total_valor = float(row["total_valor"] or 0) if row else 0.0

            cur.execute(data_sql, tuple(params + [limit, offset]))
            rows = [dict(r) for r in cur.fetchall()]
        return total, rows, total_valor

    def create_venda(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO vendas (
                id, descricao, modalidade, tipo_item, valor, quantidade,
                materia_id, polo_id, escola_id, aluno_id, criado_por, criado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    data.get("descricao"),
                    data.get("modalidade", "polo"),
                    data.get("tipo_item", "licenca"),
                    data.get("valor", 0.0),
                    data.get("quantidade", 1),
                    str(data.get("materia_id")) if data.get("materia_id") else None,
                    str(data.get("polo_id")) if data.get("polo_id") else None,
                    str(data.get("escola_id")) if data.get("escola_id") else None,
                    str(data.get("aluno_id")) if data.get("aluno_id") else None,
                    str(data.get("criado_por")) if data.get("criado_por") else None,
                ),
            )
        return new_id

    def list_boletos(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if filtros.get("polo_id"):
            conditions.append("b.polo_id = %s")
            params.append(str(filtros["polo_id"]))
        if filtros.get("status"):
            conditions.append("b.status = %s")
            params.append(filtros["status"])
        if filtros.get("venda_id"):
            conditions.append("b.venda_id = %s")
            params.append(str(filtros["venda_id"]))

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM boletos b {where_clause}"
        data_sql = f"""
            SELECT b.id, b.venda_id, b.valor, b.data_vencimento, b.status,
                   b.nosso_numero, b.asaas_id, b.link_pdf, b.criado_em
            FROM boletos b
            {where_clause}
            ORDER BY b.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_boleto(self, boleto_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM boletos WHERE id = %s LIMIT 1", (str(boleto_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_boleto(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO boletos (id, venda_id, polo_id, valor, data_vencimento, status, nosso_numero, asaas_id, link_pdf, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("venda_id")) if data.get("venda_id") else None,
                    str(data.get("polo_id")) if data.get("polo_id") else None,
                    data.get("valor", 0.0),
                    data.get("data_vencimento"),
                    data.get("status", "gerado"),
                    data.get("nosso_numero") or f"NXB-{uuid.uuid4().hex[:10].upper()}",
                    data.get("asaas_id"),
                    data.get("link_pdf"),
                ),
            )
        return new_id

    # ---------- Logística ----------

    def list_pedidos_livros(
        self,
        filtros: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if filtros.get("status"):
            conditions.append("pl.status = %s")
            params.append(filtros["status"])
        if filtros.get("data_inicio"):
            conditions.append("pl.criado_em >= %s")
            params.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            conditions.append("pl.criado_em <= %s")
            params.append(filtros["data_fim"])
        if filtros.get("mes"):
            conditions.append("EXTRACT(MONTH FROM pl.criado_em) = %s")
            params.append(int(filtros["mes"]))
        if filtros.get("semestre"):
            conditions.append(
                "EXTRACT(QUARTER FROM pl.criado_em) IN %s"
            )
            params.append(tuple([1, 2] if int(filtros["semestre"]) == 1 else [3, 4]))
        if filtros.get("ano"):
            conditions.append("EXTRACT(YEAR FROM pl.criado_em) = %s")
            params.append(int(filtros["ano"]))
        if filtros.get("polo_id"):
            conditions.append("pl.polo_id = %s")
            params.append(str(filtros["polo_id"]))
        if filtros.get("escola_id"):
            conditions.append("pl.escola_id = %s")
            params.append(str(filtros["escola_id"]))

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM pedidos_livros pl {where_clause}"
        data_sql = f"""
            SELECT pl.id, pl.polo_id, p.nome AS polo_nome, pl.escola_id,
                   pl.materia_id, m.nome AS materia_nome, pl.quantidade, pl.status,
                   pl.solicitado_por, pl.observacao, pl.criado_em, pl.atualizado_em
            FROM pedidos_livros pl
            LEFT JOIN polos p ON pl.polo_id = p.id
            LEFT JOIN materias m ON pl.materia_id = m.id
            {where_clause}
            ORDER BY pl.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_pedido_livro(self, pedido_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT pl.id, pl.polo_id, p.nome AS polo_nome, pl.escola_id,
                   pl.materia_id, m.nome AS materia_nome, pl.quantidade, pl.status,
                   pl.solicitado_por, pl.observacao, pl.criado_em, pl.atualizado_em
            FROM pedidos_livros pl
            LEFT JOIN polos p ON pl.polo_id = p.id
            LEFT JOIN materias m ON pl.materia_id = m.id
            WHERE pl.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(pedido_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_pedido_livro(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO pedidos_livros (id, polo_id, escola_id, materia_id, quantidade, status, solicitado_por, observacao, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("polo_id")) if data.get("polo_id") else None,
                    str(data.get("escola_id")) if data.get("escola_id") else None,
                    str(data.get("materia_id")) if data.get("materia_id") else None,
                    data.get("quantidade", 1),
                    data.get("status", "pendente"),
                    str(data.get("solicitado_por")) if data.get("solicitado_por") else None,
                    data.get("observacao"),
                ),
            )
        return new_id

    def update_pedido_livro(self, pedido_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(pedido_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE pedidos_livros SET {', '.join(fields)} WHERE id = %s", tuple(params))

    # ---------- Churn (RN-04) ----------

    def list_alunos_churn(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        count_sql = """
            SELECT COUNT(*) AS total
            FROM alunos_churn ch
            JOIN usuarios u ON ch.aluno_id = u.id
        """
        data_sql = """
            SELECT ch.id, ch.aluno_id, u.nome AS aluno_nome, u.email, u.cpf,
                   ch.motivo, ch.data_marcacao, ch.etiqueta, ch.taxa_paga, ch.reingresso_em
            FROM alunos_churn ch
            JOIN usuarios u ON ch.aluno_id = u.id
            ORDER BY ch.data_marcacao DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, [], limit, offset)

    def get_aluno_churn(self, aluno_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM alunos_churn WHERE aluno_id = %s ORDER BY data_marcacao DESC LIMIT 1"
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_aluno_churn(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO alunos_churn (id, aluno_id, motivo, data_marcacao, etiqueta, taxa_paga, reingresso_em, criado_em, atualizado_em)
            VALUES (%s, %s, %s, COALESCE(%s, now()), %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("aluno_id")),
                    data.get("motivo"),
                    data.get("data_marcacao"),
                    data.get("etiqueta"),
                    data.get("taxa_paga", False),
                    data.get("reingresso_em"),
                ),
            )
        return new_id

    def update_aluno_churn(self, churn_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(churn_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE alunos_churn SET {', '.join(fields)} WHERE id = %s", tuple(params))

    # ---------- Requisições de Troca ----------

    def list_requisicoes_troca(
        self,
        status: Optional[str] = None,
        aluno_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: List[Any] = []
        if status:
            conditions.append("rt.status = %s")
            params.append(status.strip())
        if aluno_id:
            conditions.append("rt.aluno_id = %s")
            params.append(str(aluno_id))
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_sql = f"SELECT COUNT(*) AS total FROM requisicoes_troca rt {where_clause}"
        data_sql = f"""
            SELECT rt.id, rt.aluno_id, u.nome AS aluno_nome, rt.tipo,
                   rt.polo_origem_id, rt.polo_destino_id, rt.escola_destino_id,
                   rt.modalidade_destino, rt.solicitante_id, su.nome AS solicitante_nome,
                   rt.status, rt.observacao, rt.resolvido_por, rt.resolvido_em, rt.criado_em
            FROM requisicoes_troca rt
            LEFT JOIN usuarios u ON rt.aluno_id = u.id
            LEFT JOIN usuarios su ON rt.solicitante_id = su.id
            {where_clause}
            ORDER BY rt.criado_em DESC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_requisicao_troca(self, requisicao_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT rt.id, rt.aluno_id, u.nome AS aluno_nome, rt.tipo,
                   rt.polo_origem_id, rt.polo_destino_id, rt.escola_destino_id,
                   rt.modalidade_destino, rt.solicitante_id, su.nome AS solicitante_nome,
                   rt.status, rt.observacao, rt.resolvido_por, rt.resolvido_em, rt.criado_em
            FROM requisicoes_troca rt
            LEFT JOIN usuarios u ON rt.aluno_id = u.id
            LEFT JOIN usuarios su ON rt.solicitante_id = su.id
            WHERE rt.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(requisicao_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def create_requisicao_troca(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO requisicoes_troca (
                id, aluno_id, tipo, polo_origem_id, polo_destino_id, escola_destino_id,
                modalidade_destino, solicitante_id, status, observacao, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("aluno_id")),
                    data.get("tipo"),
                    str(data.get("polo_origem_id")) if data.get("polo_origem_id") else None,
                    str(data.get("polo_destino_id")) if data.get("polo_destino_id") else None,
                    str(data.get("escola_destino_id")) if data.get("escola_destino_id") else None,
                    data.get("modalidade_destino"),
                    str(data.get("solicitante_id")) if data.get("solicitante_id") else None,
                    data.get("status", "pendente"),
                    data.get("observacao"),
                ),
            )
        return new_id

    def update_requisicao_troca(self, requisicao_id: str, data: Dict[str, Any]) -> None:
        fields = []
        params: List[Any] = []
        for key, val in data.items():
            fields.append(f"{key} = %s")
            params.append(val)
        if not fields:
            return
        fields.append("atualizado_em = now()")
        params.append(str(requisicao_id))
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE requisicoes_troca SET {', '.join(fields)} WHERE id = %s", tuple(params))

    # ---------- Notas / Histórico ----------

    def list_notas_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT na.id, na.aluno_id, na.materia_id, m.nome AS materia_nome, na.matricula_id,
                   na.nota, na.tipo_avaliacao, na.ano, na.semestre, na.criado_em, na.atualizado_em
            FROM notas_alunos na
            LEFT JOIN materias m ON na.materia_id = m.id
            WHERE na.aluno_id = %s
            ORDER BY na.criado_em DESC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id),))
            return [dict(r) for r in cur.fetchall()]

    def create_nota(self, data: Dict[str, Any]) -> str:
        new_id = str(uuid.uuid4())
        sql = """
            INSERT INTO notas_alunos (id, aluno_id, materia_id, matricula_id, nota, tipo_avaliacao, ano, semestre, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    new_id,
                    str(data.get("aluno_id")),
                    str(data.get("materia_id")),
                    str(data.get("matricula_id")) if data.get("matricula_id") else None,
                    data.get("nota"),
                    data.get("tipo_avaliacao", "avaliacao"),
                    data.get("ano"),
                    data.get("semestre"),
                ),
            )
        return new_id

    def list_historico_aluno(self, aluno_id: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT h.id, h.aluno_id, h.matricula_id, h.materia_id, h.nome_materia,
                   h.nota, h.frequencia_pct, h.ano, h.semestre, h.status, h.criado_em, h.atualizado_em
            FROM historico_alunos h
            WHERE h.aluno_id = %s
            ORDER BY h.ano NULLS LAST, h.semestre NULLS LAST, h.criado_em ASC
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(aluno_id),))
            return [dict(r) for r in cur.fetchall()]

    def upsert_historico(self, data: Dict[str, Any]) -> None:
        sql = """
            INSERT INTO historico_alunos (
                id, aluno_id, matricula_id, materia_id, nome_materia, nota, frequencia_pct, ano, semestre, status, criado_em, atualizado_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            ON CONFLICT (aluno_id, materia_id) DO UPDATE
            SET nota = EXCLUDED.nota,
                frequencia_pct = EXCLUDED.frequencia_pct,
                status = EXCLUDED.status,
                atualizado_em = now()
        """
        with get_db_cursor() as cur:
            cur.execute(
                sql,
                (
                    str(uuid.uuid4()),
                    str(data.get("aluno_id")),
                    str(data.get("matricula_id")) if data.get("matricula_id") else None,
                    str(data.get("materia_id")),
                    data.get("nome_materia"),
                    data.get("nota"),
                    data.get("frequencia_pct"),
                    data.get("ano"),
                    data.get("semestre"),
                    data.get("status", "cursando"),
                ),
            )

    def list_professores_ativos(
        self,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = ["u.perfil_id IN (SELECT id FROM perfis WHERE lower(nome) = 'professor')"]
        params: List[Any] = []
        if data_inicio:
            conditions.append("u.criado_em >= %s")
            params.append(data_inicio)
        if data_fim:
            conditions.append("u.criado_em <= %s")
            params.append(data_fim)
        where_clause = "WHERE " + " AND ".join(conditions)
        count_sql = f"SELECT COUNT(*) AS total FROM usuarios u {where_clause}"
        data_sql = f"""
            SELECT u.id, u.nome, u.email, u.cpf, u.status, u.criado_em
            FROM usuarios u
            {where_clause}
            ORDER BY u.nome ASC
            LIMIT %s OFFSET %s
        """
        return _exec_paginated(count_sql, data_sql, params, limit, offset)

    def get_professor_por_id(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT u.id, u.nome, u.email, u.cpf, u.status, u.foto_url, u.criado_em
            FROM usuarios u
            WHERE u.id = %s
            LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (str(usuario_id),))
            row = cur.fetchone()
            return dict(row) if row else None


def _im_paginate(items: List[Dict[str, Any]], limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
    """Helper de paginação (limit/offset com total) para o repositório em memória."""
    total = len(items)
    return total, items[offset : offset + limit]


class InMemoryAdminRepository:
    """Implementação em memória para testes unitários e de integração."""

    def __init__(self) -> None:
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        # Perfis do sistema (novos + aliases legados "polo"/"escola" p/ compatibilidade)
        self.perfis: Dict[str, Dict[str, Any]] = {
            "p-admin": {"id": "p-admin", "nome": "admin", "descricao": "Administrador — acesso total"},
            "p-secretario-geral": {"id": "p-secretario-geral", "nome": "secretario_geral", "descricao": "Visão global, sem configurar sistema"},
            "p-coord-ead": {"id": "p-coord-ead", "nome": "coordenador_ead", "descricao": "Gestão EAD"},
            "p-coord-polo": {"id": "p-coord-polo", "nome": "coordenador_polo", "descricao": "Gestão do próprio polo"},
            "p-sec-escola": {"id": "p-sec-escola", "nome": "secretario_escola", "descricao": "Gestão da própria escola"},
            "p-prof": {"id": "p-prof", "nome": "professor", "descricao": "Aulas, atas, anexos, presença"},
            "p-monitor": {"id": "p-monitor", "nome": "monitor", "descricao": "Apoio ao professor, chat"},
            "p-aluno": {"id": "p-aluno", "nome": "aluno", "descricao": "Acesso ao próprio histórico"},
            "p-financeiro": {"id": "p-financeiro", "nome": "financeiro", "descricao": "Vendas, boletos"},
            "p-logistica": {"id": "p-logistica", "nome": "logistica", "descricao": "Pedidos de livros"},
            "p-polo": {"id": "p-polo", "nome": "polo", "descricao": "Gestor de Polo (legado)"},
            "p-escola": {"id": "p-escola", "nome": "escola", "descricao": "Gestor de Escola (legado)"},
        }
        # Permissões granulares (chaves oficiais + legadas p/ compatibilidade de testes)
        self.permissoes: Dict[str, Dict[str, Any]] = {
            "perm-p_cadastro": {"id": "perm-p_cadastro", "chave": "p_cadastro", "descricao": "Permissão de cadastro"},
            "perm-p_edicao": {"id": "perm-p_edicao", "chave": "p_edicao", "descricao": "Permissão de edição"},
            "perm-p_vendas": {"id": "perm-p_vendas", "chave": "p_vendas", "descricao": "Permissão de vendas"},
            "perm-p_matriculas": {"id": "perm-p_matriculas", "chave": "p_matriculas", "descricao": "Permissão de matrículas"},
            "perm-p_financeiro": {"id": "perm-p_financeiro", "chave": "p_financeiro", "descricao": "Permissão financeira"},
            "perm-p_academico": {"id": "perm-p_academico", "chave": "p_academico", "descricao": "Permissão acadêmica"},
            "perm-p_chat": {"id": "perm-p_chat", "chave": "p_chat", "descricao": "Permissão de chat"},
            "perm-p_ranking": {"id": "perm-p_ranking", "chave": "p_ranking", "descricao": "Permissão de ranking"},
            "perm-p_dashboard": {"id": "perm-p_dashboard", "chave": "p_dashboard", "descricao": "Acesso à dashboard interativa"},
            "perm-p_alunos": {"id": "perm-p_alunos", "chave": "p_alunos", "descricao": "Gestão de alunos"},
            "perm-p_polos": {"id": "perm-p_polos", "chave": "p_polos", "descricao": "Gestão de polos"},
            "perm-p_escolas": {"id": "perm-p_escolas", "chave": "p_escolas", "descricao": "Gestão de escolas"},
            "perm-p_cursos": {"id": "perm-p_cursos", "chave": "p_cursos", "descricao": "Gestão de cursos"},
            "perm-p_modulos": {"id": "perm-p_modulos", "chave": "p_modulos", "descricao": "Gestão de módulos/matrérias"},
            "perm-p_licencas": {"id": "perm-p_licencas", "chave": "p_licencas", "descricao": "Gestão de licenças/estoque"},
            "perm-p_ead": {"id": "perm-p_ead", "chave": "p_ead", "descricao": "Gestão EAD"},
            "perm-p_logistica": {"id": "perm-p_logistica", "chave": "p_logistica", "descricao": "Gestão logística (pedidos de livros)"},
            "perm-p_certificados": {"id": "perm-p_certificados", "chave": "p_certificados", "descricao": "Emissão de certificados"},
            "perm-p_config": {"id": "perm-p_config", "chave": "p_config", "descricao": "Configurações do sistema"},
            "perm-p_auditoria": {"id": "perm-p_auditoria", "chave": "p_auditoria", "descricao": "Consulta de auditoria"},
            "perm-p_usuarios": {"id": "perm-p_usuarios", "chave": "p_usuarios", "descricao": "Gestão de usuários"},
            "perm-p_relatorios": {"id": "perm-p_relatorios", "chave": "p_relatorios", "descricao": "Relatórios e PDFs"},
        }
        self.usuario_permissoes: List[Dict[str, str]] = []  # {"usuario_id", "permissao_id"}
        self.logs_auditoria: List[Dict[str, Any]] = []
        self.configuracoes: Dict[str, Dict[str, Any]] = {}  # chave -> dict
        self.etl_sync_runs: List[Dict[str, Any]] = []
        self.etl_erros: List[Dict[str, Any]] = []
        # Entidades operacionais (Dashboard Interativa)
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.escolas: Dict[str, Dict[str, Any]] = {}
        self.cursos: Dict[str, Dict[str, Any]] = {}
        self.modulos: Dict[str, Dict[str, Any]] = {}
        self.materias: Dict[str, Dict[str, Any]] = {}
        self.matriculas: Dict[str, Dict[str, Any]] = {}
        self.matriculas_ead: Dict[str, Dict[str, Any]] = {}
        self.ead_liberacoes: List[Dict[str, Any]] = []
        self.ead_calendario: Dict[str, Dict[str, Any]] = {}
        self.feed_noticias: Dict[str, Dict[str, Any]] = {}
        self.lembretes: Dict[str, Dict[str, Any]] = {}
        self.licencas_estoque: Dict[str, Dict[str, Any]] = {}  # "{materia_id}::{tipo}" -> dict
        self.licencas_movimentacoes: List[Dict[str, Any]] = []
        self.aulas: Dict[str, Dict[str, Any]] = {}
        self.presencas: List[Dict[str, Any]] = []
        self.anexos_aula: List[Dict[str, Any]] = []
        self.atas: List[Dict[str, Any]] = []
        self.certificados: Dict[str, Dict[str, Any]] = {}
        self.chat_conversas: Dict[str, Dict[str, Any]] = {}
        self.chat_grupos: Dict[str, Dict[str, Any]] = {}
        self.chat_participantes: List[Dict[str, str]] = []
        self.chat_mensagens: List[Dict[str, Any]] = []
        self.vendas: Dict[str, Dict[str, Any]] = {}
        self.boletos: Dict[str, Dict[str, Any]] = {}
        self.pedidos_livros: Dict[str, Dict[str, Any]] = {}
        self.alunos_churn: Dict[str, Dict[str, Any]] = {}  # churn_id -> dict (aluno_id guardado)
        self.requisicoes_troca: Dict[str, Dict[str, Any]] = {}
        self.notas_alunos: List[Dict[str, Any]] = []
        self.historico_alunos: List[Dict[str, Any]] = []
        # Registros de alunos (tabela "alunos" — compat com módulos existentes)
        self.alunos: Dict[str, Dict[str, Any]] = {}

    def _gerenciado_via(self, u: Dict[str, Any]) -> Optional[str]:
        """RN-01: identifica usuários que são 'reflexo' do cadastro unificado."""
        pid = u.get("perfil_id")
        perfil_nome = (self.perfis.get(pid, {}) or {}).get("nome", "") if pid else ""
        if perfil_nome == "coordenador_polo" and u.get("polo_id"):
            return "polo"
        if perfil_nome == "secretario_escola" and u.get("escola_id"):
            return "escola"
        return None

    def list_users(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status: Optional[str] = None,
        incluir_gerenciados: Optional[bool] = None,
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

        # RN-01: ocultar (False) ou exibir apenas (True) usuários gerenciados via Polo/Escola
        if incluir_gerenciados is False:
            filtered = [u for u in filtered if not self._gerenciado_via(u)]
        elif incluir_gerenciados is True:
            filtered = [u for u in filtered if self._gerenciado_via(u)]

        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        out = []
        for u in paginated:
            u_copy = u.copy()
            pid = u.get("perfil_id")
            if pid and pid in self.perfis:
                u_copy["perfil_nome"] = self.perfis[pid]["nome"]
            u_copy["gerenciado_via"] = self._gerenciado_via(u)
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

    # ========== Polos (RN-01) ==========

    def list_polos(self, query=None, status=None, polo_id=None, limit=50, offset=0):
        filtered = list(self.polos.values())
        if query:
            q = query.strip().lower()
            filtered = [p for p in filtered if q in (p.get("nome") or "").lower() or q in (p.get("responsavel") or "").lower() or q in (p.get("cpf") or "").lower() or q in (p.get("email") or "").lower()]
        if status:
            filtered = [p for p in filtered if p.get("status") == status]
        else:
            filtered = [p for p in filtered if p.get("status") != "inativo"]
        if polo_id:
            filtered = [p for p in filtered if str(p.get("id")) == str(polo_id)]
        filtered.sort(key=lambda p: (p.get("nome") or "").lower())
        total = len(filtered)
        return total, [p.copy() for p in filtered[offset:offset + limit]]

    def get_polo(self, polo_id):
        return self.polos.get(str(polo_id))

    def get_polo_by_usuario(self, usuario_id):
        uid = str(usuario_id)
        for p in self.polos.values():
            if str(p.get("usuario_id")) == uid:
                return p
        return None

    def create_polo_com_usuario(self, polo_data, usuario_data, permission_keys=None):
        polo_id = str(uuid.uuid4())
        usuario_id = str(uuid.uuid4())
        self.usuarios[usuario_id] = {
            "id": usuario_id,
            "nome": usuario_data.get("nome", ""),
            "sobrenome": usuario_data.get("sobrenome", ""),
            "email": usuario_data.get("email"),
            "cpf": usuario_data.get("cpf"),
            "senha_hash": usuario_data.get("senha_hash"),
            "senha_algoritmo": usuario_data.get("senha_algoritmo", "argon2id"),
            "telefone": usuario_data.get("telefone"),
            "celular": usuario_data.get("celular"),
            "foto_url": usuario_data.get("foto_url"),
            "perfil_id": usuario_data.get("perfil_id"),
            "polo_id": polo_id,
            "escola_id": None,
            "status": usuario_data.get("status", "ativo"),
            "ultimo_login_em": None,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        self.usuario_permissoes.extend([{"usuario_id": usuario_id, "permissao_id": f"perm-{k.strip().lower()}"} for k in (permission_keys or [])])
        self.polos[polo_id] = {
            "id": polo_id,
            "nome": polo_data.get("nome"),
            "responsavel": polo_data.get("responsavel"),
            "cpf": polo_data.get("cpf"),
            "email": polo_data.get("email"),
            "endereco": polo_data.get("endereco"),
            "logradouro": polo_data.get("logradouro"),
            "numero": polo_data.get("numero"),
            "bairro": polo_data.get("bairro"),
            "cidade": polo_data.get("cidade"),
            "uf": polo_data.get("uf"),
            "cep": polo_data.get("cep"),
            "usuario_id": usuario_id,
            "status": polo_data.get("status", "ativo"),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return polo_id, usuario_id

    def update_polo_sincronizar_usuario(self, polo_id, polo_data, usuario_id, usuario_data):
        p = self.polos.get(str(polo_id))
        if p:
            for k, v in polo_data.items():
                p[k] = v
            p["atualizado_em"] = datetime.now(timezone.utc)
        u = self.usuarios.get(str(usuario_id))
        if u:
            for k, v in usuario_data.items():
                u[k] = v
            u["atualizado_em"] = datetime.now(timezone.utc)

    def desativar_polo_e_usuario(self, polo_id, usuario_id):
        p = self.polos.get(str(polo_id))
        if p:
            p["status"] = "inativo"; p["atualizado_em"] = datetime.now(timezone.utc)
        u = self.usuarios.get(str(usuario_id))
        if u:
            u["status"] = "inativo"; u["atualizado_em"] = datetime.now(timezone.utc)

    def get_polo_detalhes(self, polo_id):
        p = self.polos.get(str(polo_id))
        if not p:
            return None
        p = p.copy()
        matriculas = [m for m in self.matriculas.values() if str(m.get("polo_id")) == str(polo_id)]
        p["total_alunos"] = len([m for m in matriculas if m.get("status") == "ativa"])
        escolas_vinculadas = [e.copy() for e in self.escolas.values() if str(e.get("polo_id")) == str(polo_id) and e.get("status") != "inativo"]
        p["escolas_vinculadas"] = escolas_vinculadas
        p["total_escolas"] = len(escolas_vinculadas)
        movs = [m for m in self.licencas_movimentacoes if str(m.get("polo_id")) == str(polo_id) and m.get("tipo_movimento") == "saida"]
        p["total_licencas"] = sum(int(m.get("quantidade", 0)) for m in movs)
        return p

    def get_ranking_polos(self):
        ranking = []
        for p in self.polos.values():
            if p.get("status") == "inativo":
                continue
            total_lic = sum(int(m.get("quantidade", 0)) for m in self.vendas.values() if str(m.get("polo_id")) == str(p["id"]) and m.get("tipo_item") == "licenca")
            total_liv = sum(int(m.get("quantidade", 0)) for m in self.vendas.values() if str(m.get("polo_id")) == str(p["id"]) and m.get("tipo_item") == "livro")
            ranking.append({"id": p["id"], "nome": p.get("nome"), "total_licencas": total_lic, "total_livros": total_liv, "total_adquirido": total_lic + total_liv})
        ranking.sort(key=lambda r: (-r["total_adquirido"], r["nome"]))
        return ranking

    # ========== Escolas (RN-01) ==========

    def list_escolas(self, query=None, status=None, polo_id=None, escola_id=None, limit=50, offset=0):
        filtered = list(self.escolas.values())
        if query:
            q = query.strip().lower()
            filtered = [e for e in filtered if q in (e.get("nome") or "").lower() or q in (e.get("responsavel") or "").lower() or q in (e.get("cpf") or "").lower() or q in (e.get("email") or "").lower()]
        if status:
            filtered = [e for e in filtered if e.get("status") == status]
        else:
            filtered = [e for e in filtered if e.get("status") != "inativo"]
        if polo_id:
            filtered = [e for e in filtered if str(e.get("polo_id")) == str(polo_id)]
        if escola_id:
            filtered = [e for e in filtered if str(e.get("id")) == str(escola_id)]
        filtered.sort(key=lambda e: (e.get("nome") or "").lower())
        total = len(filtered)
        return total, [e.copy() for e in filtered[offset:offset + limit]]

    def get_escola(self, escola_id):
        return self.escolas.get(str(escola_id))

    def get_escola_by_usuario(self, usuario_id):
        uid = str(usuario_id)
        for e in self.escolas.values():
            if str(e.get("usuario_id")) == uid:
                return e
        return None

    def create_escola_com_usuario(self, escola_data, usuario_data, permission_keys=None):
        escola_id = str(uuid.uuid4())
        usuario_id = str(uuid.uuid4())
        self.usuarios[usuario_id] = {
            "id": usuario_id,
            "nome": usuario_data.get("nome", ""),
            "sobrenome": usuario_data.get("sobrenome", ""),
            "email": usuario_data.get("email"),
            "cpf": usuario_data.get("cpf"),
            "senha_hash": usuario_data.get("senha_hash"),
            "senha_algoritmo": usuario_data.get("senha_algoritmo", "argon2id"),
            "telefone": usuario_data.get("telefone"),
            "celular": usuario_data.get("celular"),
            "foto_url": usuario_data.get("foto_url"),
            "perfil_id": usuario_data.get("perfil_id"),
            "polo_id": usuario_data.get("polo_id"),
            "escola_id": escola_id,
            "status": usuario_data.get("status", "ativo"),
            "ultimo_login_em": None,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        self.usuario_permissoes.extend([{"usuario_id": usuario_id, "permissao_id": f"perm-{k.strip().lower()}"} for k in (permission_keys or [])])
        self.escolas[escola_id] = {
            "id": escola_id,
            "polo_id": str(escola_data.get("polo_id")) if escola_data.get("polo_id") else None,
            "nome": escola_data.get("nome"),
            "responsavel": escola_data.get("responsavel"),
            "cpf": escola_data.get("cpf"),
            "email": escola_data.get("email"),
            "endereco": escola_data.get("endereco"),
            "logradouro": escola_data.get("logradouro"),
            "numero": escola_data.get("numero"),
            "bairro": escola_data.get("bairro"),
            "cidade": escola_data.get("cidade"),
            "uf": escola_data.get("uf"),
            "cep": escola_data.get("cep"),
            "usuario_id": usuario_id,
            "status": escola_data.get("status", "ativo"),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return escola_id, usuario_id

    def update_escola_sincronizar_usuario(self, escola_id, escola_data, usuario_id, usuario_data):
        e = self.escolas.get(str(escola_id))
        if e:
            for k, v in escola_data.items():
                e[k] = v
            e["atualizado_em"] = datetime.now(timezone.utc)
        u = self.usuarios.get(str(usuario_id))
        if u:
            for k, v in usuario_data.items():
                u[k] = v
            u["atualizado_em"] = datetime.now(timezone.utc)

    def desativar_escola_e_usuario(self, escola_id, usuario_id):
        e = self.escolas.get(str(escola_id))
        if e:
            e["status"] = "inativo"; e["atualizado_em"] = datetime.now(timezone.utc)
        u = self.usuarios.get(str(usuario_id))
        if u:
            u["status"] = "inativo"; u["atualizado_em"] = datetime.now(timezone.utc)

    def get_escola_detalhes(self, escola_id):
        e = self.escolas.get(str(escola_id))
        if not e:
            return None
        e = e.copy()
        matriculas = [m for m in self.matriculas.values() if str(m.get("escola_id")) == str(escola_id)]
        e["total_alunos"] = len([m for m in matriculas if m.get("status") == "ativa"])
        if e.get("polo_id"):
            polo = self.polos.get(e["polo_id"])
            e["polo_nome"] = polo.get("nome") if polo else None
        return e

    # ========== Cursos / Módulos / Matérias ==========

    def list_cursos(self, query=None, limit=50, offset=0):
        items = list(self.cursos.values())
        if query:
            q = query.strip().lower()
            items = [c for c in items if q in (c.get("nome") or "").lower() or q in (c.get("descricao") or "").lower()]
        items.sort(key=lambda c: (c.get("nome") or "").lower())
        total = len(items)
        return total, [c.copy() for c in items[offset:offset + limit]]

    def get_curso(self, curso_id):
        return self.cursos.get(str(curso_id))

    def create_curso(self, data):
        new_id = str(uuid.uuid4())
        self.cursos[new_id] = {
            "id": new_id,
            "nome": data.get("nome"),
            "descricao": data.get("descricao"),
            "carga_horaria_horas": data.get("carga_horaria_horas", 0),
            "grade_curricular": data.get("grade_curricular"),
            "status": data.get("status", "ativo"),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return new_id

    def update_curso(self, curso_id, data):
        c = self.cursos.get(str(curso_id))
        if not c:
            return
        for k, v in data.items():
            c[k] = v
        c["atualizado_em"] = datetime.now(timezone.utc)

    def delete_curso(self, curso_id):
        c = self.cursos.get(str(curso_id))
        if c:
            c["status"] = "inativo"; c["atualizado_em"] = datetime.now(timezone.utc)

    def list_modulos(self, curso_id=None, limit=50, offset=0):
        items = list(self.modulos.values())
        if curso_id:
            items = [m for m in items if str(m.get("curso_id")) == str(curso_id)]
        items.sort(key=lambda m: (m.get("ordem", 1), m.get("nome", "")))
        total = len(items)
        return total, [m.copy() for m in items[offset:offset + limit]]

    def get_modulo(self, modulo_id):
        return self.modulos.get(str(modulo_id))

    def create_modulo(self, data):
        new_id = str(uuid.uuid4())
        self.modulos[new_id] = {
            "id": new_id,
            "curso_id": str(data.get("curso_id")),
            "nome": data.get("nome"),
            "ordem": data.get("ordem", 1),
            "conteudo": data.get("conteudo"),
            "carga_horaria_horas": data.get("carga_horaria_horas", 0),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return new_id

    def update_modulo(self, modulo_id, data):
        m = self.modulos.get(str(modulo_id))
        if not m:
            return
        for k, v in data.items():
            m[k] = v
        m["atualizado_em"] = datetime.now(timezone.utc)

    def delete_modulo(self, modulo_id):
        self.modulos.pop(str(modulo_id), None)

    def list_materias(self, curso_id=None, modulo_id=None, query=None, limit=50, offset=0):
        items = list(self.materias.values())
        if curso_id:
            items = [m for m in items if str(m.get("curso_id")) == str(curso_id)]
        if modulo_id:
            items = [m for m in items if str(m.get("modulo_id")) == str(modulo_id)]
        if query:
            q = query.strip().lower()
            items = [m for m in items if q in (m.get("nome") or "").lower()]
        items.sort(key=lambda m: (m.get("ordem", 1), m.get("nome", "")))
        total = len(items)
        return total, [m.copy() for m in items[offset:offset + limit]]

    def get_materia(self, materia_id):
        return self.materias.get(str(materia_id))

    def create_materia(self, data):
        new_id = str(uuid.uuid4())
        self.materias[new_id] = {
            "id": new_id,
            "curso_id": str(data.get("curso_id")),
            "modulo_id": str(data.get("modulo_id")) if data.get("modulo_id") else None,
            "nome": data.get("nome"),
            "ordem": data.get("ordem", 1),
            "carga_horaria_horas": data.get("carga_horaria_horas", 0),
            "total_aulas_previstas": data.get("total_aulas_previstas", 0),
            "tipo": data.get("tipo", "disciplina"),
            "conteudo": data.get("conteudo"),
            "preco": data.get("preco", 45.0),
            "status": data.get("status", "ativo"),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return new_id

    def update_materia(self, materia_id, data):
        m = self.materias.get(str(materia_id))
        if not m:
            return
        for k, v in data.items():
            m[k] = v
        m["atualizado_em"] = datetime.now(timezone.utc)

    def delete_materia(self, materia_id):
        m = self.materias.get(str(materia_id))
        if m:
            m["status"] = "inativo"; m["atualizado_em"] = datetime.now(timezone.utc)

    # ========== Matrículas ==========

    def list_matriculas(self, filtros, limit=50, offset=0):
        items = list(self.matriculas.values())
        if filtros.get("polo_id"):
            items = [m for m in items if str(m.get("polo_id")) == str(filtros["polo_id"])]
        if filtros.get("escola_id"):
            items = [m for m in items if str(m.get("escola_id")) == str(filtros["escola_id"])]
        if filtros.get("modalidade"):
            items = [m for m in items if m.get("modalidade") == filtros["modalidade"]]
        if filtros.get("aluno_id"):
            items = [m for m in items if str(m.get("aluno_id")) == str(filtros["aluno_id"])]
        if filtros.get("curso_id"):
            items = [m for m in items if str(m.get("curso_id")) == str(filtros["curso_id"])]
        if filtros.get("status"):
            items = [m for m in items if m.get("status") == filtros["status"]]
        if filtros.get("semestre"):
            items = [m for m in items if m.get("semestre") == filtros["semestre"]]
        if filtros.get("ano"):
            items = [m for m in items if m.get("ano") == filtros["ano"]]
        if filtros.get("data_inicio"):
            items = [m for m in items if (m.get("criado_em") or datetime.min) >= filtros["data_inicio"]]
        if filtros.get("data_fim"):
            items = [m for m in items if (m.get("criado_em") or datetime.max) <= filtros["data_fim"]]
        items.sort(key=lambda m: m.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        return total, [m.copy() for m in items[offset:offset + limit]]

    def get_matricula(self, matricula_id):
        return self.matriculas.get(str(matricula_id))

    def create_matricula(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.matriculas[new_id] = {
            "id": new_id,
            "aluno_id": str(data.get("aluno_id")),
            "curso_id": str(data.get("curso_id")) if data.get("curso_id") else None,
            "polo_id": str(data.get("polo_id")) if data.get("polo_id") else None,
            "escola_id": str(data.get("escola_id")) if data.get("escola_id") else None,
            "modalidade": data.get("modalidade", "polo"),
            "numero_matricula": data.get("numero_matricula") or f"NX-{uuid.uuid4().hex[:8].upper()}",
            "semestre": data.get("semestre"),
            "ano": data.get("ano"),
            "status": data.get("status", "ativa"),
            "data_matricula": data.get("data_matricula"),
            "criado_em": now,
            "atualizado_em": now,
        }
        return new_id

    def update_matricula(self, matricula_id, data):
        m = self.matriculas.get(str(matricula_id))
        if not m:
            return
        for k, v in data.items():
            m[k] = v
        m["atualizado_em"] = datetime.now(timezone.utc)

    # ========== Alunos ==========

    def _usuario_perfil_nome(self, usuario_id):
        u = self.usuarios.get(str(usuario_id))
        if not u:
            return None
        pid = u.get("perfil_id")
        return self.perfis.get(pid, {}).get("nome") if pid else None

    def list_alunos(self, filtros, limit=50, offset=0):
        items = list(self.alunos.values())
        if filtros.get("polo_id"):
            items = [a for a in items if str(a.get("polo_id")) == str(filtros["polo_id"])]
        if filtros.get("escola_id"):
            items = [a for a in items if str(a.get("escola_id")) == str(filtros["escola_id"])]
        if filtros.get("modalidade"):
            items = [a for a in items if a.get("modalidade") == filtros["modalidade"]]
        if filtros.get("curso_id"):
            items = [a for a in items if str(a.get("curso_id")) == str(filtros["curso_id"])]
        if filtros.get("semestre"):
            items = [a for a in items if a.get("semestre") == filtros["semestre"]]
        if filtros.get("ano"):
            items = [a for a in items if a.get("ano") == filtros["ano"]]
        if filtros.get("pais"):
            items = [a for a in items if a.get("pais") == filtros["pais"]]
        if filtros.get("estado"):
            items = [a for a in items if a.get("estado") == filtros["estado"]]
        if filtros.get("data_inicio"):
            items = [a for a in items if (a.get("criado_em") or datetime.min) >= filtros["data_inicio"]]
        if filtros.get("data_fim"):
            items = [a for a in items if (a.get("criado_em") or datetime.max) <= filtros["data_fim"]]
        if filtros.get("q"):
            q = filtros["q"].strip().lower()
            items = [a for a in items if q in (self.usuarios.get(str(a.get("usuario_id", "")), {}).get("nome", "") or "").lower() or q in (self.usuarios.get(str(a.get("usuario_id", "")), {}).get("email", "") or "").lower()]
        total = len(items)
        for a in items:
            uid = str(a.get("usuario_id"))
            u = self.usuarios.get(uid, {})
            a = a.copy()
            a["nome"] = u.get("nome")
            a["sobrenome"] = u.get("sobrenome")
            a["email"] = u.get("email")
            a["cpf"] = u.get("cpf")
            previstas = 0
            presencas = 0
            for m in self.materias.values():
                if str(m.get("curso_id")) == str(a.get("curso_id")):
                    previstas += int(m.get("total_aulas_previstas") or 0)
            for pr in self.presencas:
                if str(pr.get("aluno_id")) == uid and pr.get("presente"):
                    presencas += 1
            a["quantidade_presencas"] = presencas
            a["percentual_presenca"] = round((presencas / previstas) * 100.0, 1) if previstas > 0 else 0.0
            a["perfil_nome"] = self._usuario_perfil_nome(uid)
            items[items.index(a)] = a
        pag = items[offset:offset + limit]
        return total, pag

    def get_aluno(self, aluno_id):
        for a in self.alunos.values():
            if str(a.get("id")) == str(aluno_id) or str(a.get("usuario_id")) == str(aluno_id):
                u = self.usuarios.get(str(a.get("usuario_id")), {})
                out = a.copy()
                out["nome"] = u.get("nome")
                out["sobrenome"] = u.get("sobrenome")
                out["email"] = u.get("email")
                out["cpf"] = u.get("cpf")
                out["perfil_nome"] = self._usuario_perfil_nome(str(a.get("usuario_id")))
                previstas = 0
                presencas = 0
                for m in self.materias.values():
                    if str(m.get("curso_id")) == str(a.get("curso_id")):
                        previstas += int(m.get("total_aulas_previstas") or 0)
                for pr in self.presencas:
                    if str(pr.get("aluno_id")) == str(a.get("usuario_id")) and pr.get("presente"):
                        presencas += 1
                out["quantidade_presencas"] = presencas
                out["percentual_presenca"] = round((presencas / previstas) * 100.0, 1) if previstas > 0 else 0.0
                return out
        return None

    def create_aluno_com_usuario(self, usuario_data, aluno_data, matricula_data=None):
        usuario_id = str(uuid.uuid4())
        aluno_id = str(uuid.uuid4())
        matricula_id = None
        self.usuarios[usuario_id] = {
            "id": usuario_id,
            "nome": usuario_data.get("nome", ""),
            "sobrenome": usuario_data.get("sobrenome", ""),
            "email": usuario_data.get("email"),
            "cpf": usuario_data.get("cpf"),
            "senha_hash": usuario_data.get("senha_hash"),
            "senha_algoritmo": usuario_data.get("senha_algoritmo", "argon2id"),
            "telefone": usuario_data.get("telefone"),
            "celular": usuario_data.get("celular"),
            "foto_url": usuario_data.get("foto_url"),
            "perfil_id": usuario_data.get("perfil_id"),
            "polo_id": aluno_data.get("polo_id"),
            "escola_id": aluno_data.get("escola_id"),
            "status": usuario_data.get("status", "ativo"),
            "ultimo_login_em": None,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        now = datetime.now(timezone.utc)
        self.alunos[aluno_id] = {
            "id": aluno_id,
            "usuario_id": usuario_id,
            "polo_id": aluno_data.get("polo_id"),
            "escola_id": aluno_data.get("escola_id"),
            "modalidade": aluno_data.get("modalidade", "polo"),
            "numero_matricula": aluno_data.get("numero_matricula") or f"NX-{uuid.uuid4().hex[:8].upper()}",
            "data_nascimento": aluno_data.get("data_nascimento"),
            "pais": aluno_data.get("pais"),
            "estado": aluno_data.get("estado"),
            "curso_id": aluno_data.get("curso_id"),
            "status": aluno_data.get("status", "ativo"),
            "ultima_movimentacao_em": None,
            "criado_em": now,
            "atualizado_em": now,
        }
        if matricula_data:
            matricula_id = str(uuid.uuid4())
            self.matriculas[matricula_id] = {
                "id": matricula_id,
                "aluno_id": usuario_id,
                "curso_id": str(matricula_data.get("curso_id")) if matricula_data.get("curso_id") else None,
                "polo_id": str(matricula_data.get("polo_id")) if matricula_data.get("polo_id") else None,
                "escola_id": str(matricula_data.get("escola_id")) if matricula_data.get("escola_id") else None,
                "modalidade": matricula_data.get("modalidade", "polo"),
                "numero_matricula": matricula_data.get("numero_matricula") or f"NX-{uuid.uuid4().hex[:8].upper()}",
                "semestre": matricula_data.get("semestre"),
                "ano": matricula_data.get("ano"),
                "status": matricula_data.get("status", "ativa"),
                "data_matricula": None,
                "criado_em": now,
                "atualizado_em": now,
            }
        return usuario_id, aluno_id, matricula_id

    def update_aluno(self, aluno_id, data):
        a = self.alunos.get(str(aluno_id))
        if not a:
            return
        for k, v in data.items():
            a[k] = v
        a["atualizado_em"] = datetime.now(timezone.utc)

    def marcar_desistentes_automatico(self, cutoff):
        marcados = 0
        for a in list(self.alunos.values()):
            if a.get("status") == "ativo" and a.get("ultima_movimentacao_em") and a["ultima_movimentacao_em"] < cutoff:
                a["status"] = "desistente"
                a["polo_id"] = None
                a["atualizado_em"] = datetime.now(timezone.utc)
                self.alunos_churn[str(uuid.uuid4())] = {
                    "id": str(uuid.uuid4()),
                    "aluno_id": str(a["usuario_id"]),
                    "motivo": "Inatividade superior a 1 ano (churn automático)",
                    "data_marcacao": datetime.now(timezone.utc),
                    "etiqueta": None,
                    "taxa_paga": False,
                    "reingresso_em": None,
                    "criado_em": datetime.now(timezone.utc),
                    "atualizado_em": datetime.now(timezone.utc),
                }
                marcados += 1
        return marcados

    # ========== EAD ==========

    def list_matriculas_ead(self, filtros, limit=50, offset=0):
        items = list(self.matriculas_ead.values())
        if filtros.get("q"):
            q = filtros["q"].strip().lower()
            items = [m for m in items if q in (self.usuarios.get(str(m.get("aluno_id")), {}).get("nome", "") or "").lower() or q in (self.usuarios.get(str(m.get("aluno_id")), {}).get("email", "") or "").lower()]
        if filtros.get("curso_id"):
            items = [m for m in items if str(m.get("curso_id")) == str(filtros["curso_id"])]
        if filtros.get("status"):
            items = [m for m in items if m.get("status") == filtros["status"]]
        if filtros.get("origem"):
            items = [m for m in items if m.get("origem") == filtros["origem"]]
        if filtros.get("data_inicio"):
            items = [m for m in items if (m.get("criado_em") or datetime.min) >= filtros["data_inicio"]]
        if filtros.get("data_fim"):
            items = [m for m in items if (m.get("criado_em") or datetime.max) <= filtros["data_fim"]]
        items.sort(key=lambda m: m.get("ultimo_acesso_em") or m.get("criado_em") or datetime.min, reverse=True)
        total = len(items)
        out = []
        for m in items[offset:offset + limit]:
            mc = m.copy()
            mc["aluno_nome"] = self.usuarios.get(str(mc.get("aluno_id")), {}).get("nome")
            mc["curso_nome"] = self.cursos.get(str(mc.get("curso_id")), {}).get("nome")
            mc["materia_atual_nome"] = self.materias.get(str(mc.get("materia_atual_id")), {}).get("nome")
            mc["materias_liberadas_no_mes"] = self.count_liberacoes_ead_mes(str(mc.get("aluno_id")), (mc.get("criado_em") or datetime.now(timezone.utc)).year, (mc.get("criado_em") or datetime.now(timezone.utc)).month) if mc.get("aluno_id") else 0
            out.append(mc)
        return total, out

    def get_matricula_ead(self, matricula_ead_id):
        m = self.matriculas_ead.get(str(matricula_ead_id))
        if not m:
            return None
        mc = m.copy()
        mc["aluno_nome"] = self.usuarios.get(str(mc.get("aluno_id")), {}).get("nome")
        mc["curso_nome"] = self.cursos.get(str(mc.get("curso_id")), {}).get("nome")
        mc["materia_atual_nome"] = self.materias.get(str(mc.get("materia_atual_id")), {}).get("nome")
        return mc

    def create_matricula_ead(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.matriculas_ead[new_id] = {
            "id": new_id,
            "matricula_id": str(data.get("matricula_id")) if data.get("matricula_id") else None,
            "aluno_id": str(data.get("aluno_id")),
            "curso_id": str(data.get("curso_id")),
            "materia_atual_id": str(data.get("materia_atual_id")) if data.get("materia_atual_id") else None,
            "progresso_pct": data.get("progresso_pct", 0),
            "ultimo_acesso_em": data.get("ultimo_acesso_em"),
            "origem": data.get("origem", "manual"),
            "status": data.get("status", "ativa"),
            "criado_em": now,
            "atualizado_em": now,
        }
        return new_id

    def update_matricula_ead(self, matricula_ead_id, data):
        m = self.matriculas_ead.get(str(matricula_ead_id))
        if not m:
            return
        for k, v in data.items():
            m[k] = v
        m["atualizado_em"] = datetime.now(timezone.utc)

    def get_matricula_ead_por_aluno(self, aluno_id):
        uid = str(aluno_id)
        for m in sorted(self.matriculas_ead.values(), key=lambda x: x.get("criado_em", datetime.min), reverse=True):
            if str(m.get("aluno_id")) == uid:
                return m
        return None

    def count_liberacoes_ead_mes(self, aluno_id, ano, mes):
        uid = str(aluno_id)
        count = 0
        for l in self.ead_liberacoes:
            if str(l.get("aluno_id")) == uid:
                ld = l.get("data_liberacao")
                if ld and ld.year == int(ano) and ld.month == int(mes):
                    count += 1
        return count

    def registrar_liberacao_ead(self, data):
        new_id = str(uuid.uuid4())
        aluno_id = str(data.get("aluno_id")) if data.get("aluno_id") else None
        self.ead_liberacoes.append({
            "id": new_id,
            "matricula_ead_id": str(data.get("matricula_ead_id")),
            "materia_id": str(data.get("materia_id")),
            "aluno_id": aluno_id,
            "data_liberacao": data.get("data_liberacao") or datetime.now(timezone.utc).date(),
            "status": data.get("status", "liberada"),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        })
        return new_id

    def get_ultima_liberacao_ead(self, matricula_ead_id):
        liberacoes = [l for l in self.ead_liberacoes if str(l.get("matricula_ead_id")) == str(matricula_ead_id)]
        if not liberacoes:
            return None
        return max(liberacoes, key=lambda l: l.get("data_liberacao") or datetime.min)

    def list_ead_calendario(self, curso_id=None, limit=50, offset=0):
        items = list(self.ead_calendario.values())
        if curso_id:
            items = [c for c in items if str(c.get("curso_id")) == str(curso_id)]
        items.sort(key=lambda c: (c.get("ordem", 1), c.get("data_liberacao") or datetime.min))
        total = len(items)
        out = []
        for c in items[offset:offset + limit]:
            cc = c.copy()
            cc["materia_nome"] = self.materias.get(str(cc.get("materia_id")), {}).get("nome")
            out.append(cc)
        return total, out

    def create_ead_calendario(self, data):
        new_id = str(uuid.uuid4())
        self.ead_calendario[new_id] = {
            "id": new_id,
            "materia_id": str(data.get("materia_id")),
            "curso_id": str(data.get("curso_id")) if data.get("curso_id") else None,
            "ordem": data.get("ordem", 1),
            "data_liberacao": data.get("data_liberacao"),
            "ano": data.get("ano"),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return new_id

    def delete_ead_calendario(self, calendario_id):
        self.ead_calendario.pop(str(calendario_id), None)

    def list_feed_noticias(self, limit=50, offset=0):
        items = [f for f in self.feed_noticias.values() if f.get("status") == "publicado"]
        items.sort(key=lambda f: f.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for f in items[offset:offset + limit]:
            fc = f.copy()
            fc["autor_nome"] = self.usuarios.get(str(fc.get("autor_id", "")), {}).get("nome")
            pid = self.usuarios.get(str(fc.get("autor_id", "")), {}).get("perfil_id")
            fc["autor_perfil"] = self.perfis.get(pid, {}).get("nome") if pid else None
            out.append(fc)
        return total, out

    def create_feed_noticia(self, data):
        new_id = str(uuid.uuid4())
        self.feed_noticias[new_id] = {
            "id": new_id,
            "titulo": data.get("titulo"),
            "conteudo": data.get("conteudo"),
            "autor_id": str(data.get("autor_id")) if data.get("autor_id") else None,
            "status": data.get("status", "publicado"),
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return new_id

    def delete_feed_noticia(self, noticia_id):
        self.feed_noticias.pop(str(noticia_id), None)

    def list_lembretes(self, limit=50, offset=0):
        items = list(self.lembretes.values())
        items.sort(key=lambda l: l.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        return total, [l.copy() for l in items[offset:offset + limit]]

    def create_lembrete(self, data):
        new_id = str(uuid.uuid4())
        self.lembretes[new_id] = {
            "id": new_id,
            "titulo": data.get("titulo"),
            "mensagem": data.get("mensagem") or data.get("conteudo"),
            "tipo": data.get("tipo", "popup"),
            "data_exibicao": data.get("data_exibicao"),
            "destino_perfil": data.get("destino_perfil"),
            "materia_id": str(data.get("materia_id")) if data.get("materia_id") else None,
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
        }
        return new_id

    def delete_lembrete(self, lembrete_id):
        self.lembretes.pop(str(lembrete_id), None)

    # ========== Licenças / Estoque ==========

    def _estoque_key(self, materia_id, tipo):
        return f"{materia_id}::{tipo}"

    def list_licencas_estoque(self, query=None, limit=50, offset=0):
        items = list(self.licencas_estoque.values())
        if query:
            q = query.strip().lower()
            items = [e for e in items if q in (self.materias.get(str(e.get("materia_id")), {}).get("nome", "").lower())]
        items.sort(key=lambda e: (self.materias.get(str(e.get("materia_id")), {}).get("nome", ""), e.get("tipo")))
        total = len(items)
        out = []
        for e in items[offset:offset + limit]:
            ec = e.copy()
            ec["materia_nome"] = self.materias.get(str(e.get("materia_id")), {}).get("nome")
            out.append(ec)
        return total, out

    def get_licenca_estoque(self, materia_id, tipo="licenca"):
        return self.licencas_estoque.get(self._estoque_key(str(materia_id), tipo))

    def ajustar_licenca_estoque(self, materia_id, tipo, delta, movimentacao=None):
        key = self._estoque_key(str(materia_id), tipo)
        now = datetime.now(timezone.utc)
        if key not in self.licencas_estoque:
            self.licencas_estoque[key] = {
                "id": str(uuid.uuid4()),
                "materia_id": str(materia_id),
                "tipo": tipo,
                "quantidade": 0,
                "criado_em": now,
                "atualizado_em": now,
            }
        est = self.licencas_estoque[key]
        est["quantidade"] = int(est["quantidade"]) + int(delta)
        est["atualizado_em"] = now
        if movimentacao:
            self.licencas_movimentacoes.append({
                "id": str(uuid.uuid4()),
                "materia_id": str(materia_id),
                "tipo_item": tipo,
                "tipo_movimento": movimentacao.get("tipo_movimento", "ajuste"),
                "quantidade": int(movimentacao.get("quantidade", abs(delta))),
                "destino_tipo": movimentacao.get("destino_tipo"),
                "polo_id": str(movimentacao.get("polo_id")) if movimentacao.get("polo_id") else None,
                "escola_id": str(movimentacao.get("escola_id")) if movimentacao.get("escola_id") else None,
                "usuario_id": str(movimentacao.get("usuario_id")) if movimentacao.get("usuario_id") else None,
                "observacao": movimentacao.get("observacao"),
                "criado_em": now,
                "atualizado_em": now,
            })
        est["materia_nome"] = self.materias.get(str(materia_id), {}).get("nome")
        return est

    def list_licencas_movimentacoes(self, filtros, limit=50, offset=0):
        items = list(self.licencas_movimentacoes)
        if filtros.get("materia_id"):
            items = [m for m in items if str(m.get("materia_id")) == str(filtros["materia_id"])]
        if filtros.get("polo_id"):
            items = [m for m in items if str(m.get("polo_id")) == str(filtros["polo_id"])]
        if filtros.get("escola_id"):
            items = [m for m in items if str(m.get("escola_id")) == str(filtros["escola_id"])]
        if filtros.get("tipo_movimento"):
            items = [m for m in items if m.get("tipo_movimento") == filtros["tipo_movimento"]]
        if filtros.get("ano"):
            items = [m for m in items if (m.get("criado_em") or datetime.min).year == int(filtros["ano"])]
        if filtros.get("mes"):
            items = [m for m in items if (m.get("criado_em") or datetime.min).month == int(filtros["mes"])]
        if filtros.get("data_inicio"):
            items = [m for m in items if (m.get("criado_em") or datetime.min) >= filtros["data_inicio"]]
        if filtros.get("data_fim"):
            items = [m for m in items if (m.get("criado_em") or datetime.max) <= filtros["data_fim"]]
        items.sort(key=lambda m: m.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for m in items[offset:offset + limit]:
            mc = m.copy()
            mc["materia_nome"] = self.materias.get(str(mc.get("materia_id")), {}).get("nome")
            mc["usuario_nome"] = self.usuarios.get(str(mc.get("usuario_id")), {}).get("nome")
            out.append(mc)
        return total, out

    # ========== Aulas / Presenças / Anexos / Atas ==========

    def list_aulas(self, professor_id=None, materia_id=None, limit=50, offset=0):
        items = list(self.aulas.values())
        if professor_id:
            items = [a for a in items if str(a.get("professor_id")) == str(professor_id)]
        if materia_id:
            items = [a for a in items if str(a.get("materia_id")) == str(materia_id)]
        items.sort(key=lambda a: a.get("data_aula") or datetime.min, reverse=True)
        total = len(items)
        out = []
        for a in items[offset:offset + limit]:
            ac = a.copy()
            ac["materia_nome"] = self.materias.get(str(ac.get("materia_id")), {}).get("nome")
            ac["professor_nome"] = self.usuarios.get(str(ac.get("professor_id")), {}).get("nome")
            out.append(ac)
        return total, out

    def get_aula(self, aula_id):
        a = self.aulas.get(str(aula_id))
        if not a:
            return None
        out = a.copy()
        out["materia_nome"] = self.materias.get(str(out.get("materia_id")), {}).get("nome")
        out["professor_nome"] = self.usuarios.get(str(out.get("professor_id")), {}).get("nome")
        return out

    def create_aula(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.aulas[new_id] = {
            "id": new_id,
            "materia_id": str(data.get("materia_id")),
            "professor_id": str(data.get("professor_id")),
            "data_aula": data.get("data_aula"),
            "assunto": data.get("assunto"),
            "criado_em": now,
            "atualizado_em": now,
        }
        if data.get("total_aulas_previstas") is not None:
            m = self.materias.get(str(data.get("materia_id")))
            if m:
                m["total_aulas_previstas"] = int(data["total_aulas_previstas"])
        return new_id

    def registrar_presencas(self, aula_id, registros, registrado_por=None):
        now = datetime.now(timezone.utc)
        for r in registros:
            uid = str(r.get("aluno_id"))
            presenca = next((p for p in self.presencas if str(p.get("aula_id")) == str(aula_id) and str(p.get("aluno_id")) == uid), None)
            if presenca:
                presenca["presente"] = bool(r.get("presente"))
                presenca["registrado_por"] = str(registrado_por) if registrado_por else presenca.get("registrado_por")
                presenca["atualizado_em"] = now
            else:
                self.presencas.append({
                    "id": str(uuid.uuid4()),
                    "aula_id": str(aula_id),
                    "aluno_id": uid,
                    "presente": bool(r.get("presente")),
                    "registrado_por": str(registrado_por) if registrado_por else None,
                    "criado_em": now,
                    "atualizado_em": now,
                })

    def list_presencas(self, aula_id=None, aluno_id=None, limit=50, offset=0):
        items = list(self.presencas)
        if aula_id:
            items = [p for p in items if str(p.get("aula_id")) == str(aula_id)]
        if aluno_id:
            items = [p for p in items if str(p.get("aluno_id")) == str(aluno_id)]
        items.sort(key=lambda p: p.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for p in items[offset:offset + limit]:
            pc = p.copy()
            pc["aluno_nome"] = self.usuarios.get(str(pc.get("aluno_id")), {}).get("nome")
            out.append(pc)
        return total, out

    def _presencas_aluno(self, aluno_id):
        """Retorna presenças por matéria para RN-07."""
        uid = str(aluno_id)
        presencas_por_materia = {}
        presencas_reais = {}
        for p in self.presencas:
            if str(p.get("aluno_id")) == uid and p.get("presente"):
                aid = str(p.get("aula_id"))
                presencas_reais[aid] = presencas_reais.get(aid, 0) + 1
        for a in self.aulas.values():
            aid = str(a.get("id"))
            mid = str(a.get("materia_id"))
            presencas_por_materia.setdefault(mid, {"presencas": 0, "total_aulas": 0})
            presencas_por_materia[mid]["total_aulas"] += 1
            if aid in presencas_reais:
                presencas_por_materia[mid]["presencas"] += presencas_reais[aid]
        out = []
        for mid, dados in presencas_por_materia.items():
            m = self.materias.get(mid, {})
            previstas = dados["total_aulas"]
            presencas = dados["presencas"]
            pct = round((presencas / previstas) * 100.0, 1) if previstas > 0 else 0.0
            out.append({"materia_id": mid, "materia_nome": m.get("nome"), "total_aulas_previstas": previstas, "presencas": presencas, "percentual": pct})
        return out

    def get_presencas_resumo_aluno(self, aluno_id):
        return self._presencas_aluno(aluno_id)

    def get_presencas_resumo_professor(self, professor_id):
        professor_alunos = {}
        aulas_prof = [a for a in self.aulas.values() if str(a.get("professor_id")) == str(professor_id)]
        materia_ids = list({str(a.get("materia_id")) for a in aulas_prof})
        for p in self.presencas:
            if str(p.get("aula_id")) not in [str(a.get("id")) for a in aulas_prof]:
                continue
            aluno_id = str(p.get("aluno_id"))
            if aluno_id not in professor_alunos:
                professor_alunos[aluno_id] = {"aulas_registradas": set(), "presencas_materia": {}}
            aid = str(p.get("aula_id"))
            professor_alunos[aluno_id]["aulas_registradas"].add(aid)
            materia_id = str(self.aulas.get(aid, {}).get("materia_id"))
            if materia_id:
                if p.get("presente"):
                    professor_alunos[aluno_id]["presencas_materia"][materia_id] = professor_alunos[aluno_id]["presencas_materia"].get(materia_id, 0) + 1
        out = []
        for uid, dados in professor_alunos.items():
            u = self.usuarios.get(uid, {})
            for mid in materia_ids:
                presencas = dados["presencas_materia"].get(mid, 0)
                total_aulas = sum(1 for a in aulas_prof if str(a.get("materia_id")) == mid)
                pct = round((presencas / total_aulas) * 100.0, 1) if total_aulas > 0 else 0.0
                out.append({
                    "aluno_id": uid, "aluno_nome": u.get("nome"), "materia_id": mid,
                    "materia_nome": self.materias.get(mid, {}).get("nome"), "aulas_registradas": len(dados["aulas_registradas"]),
                    "presencas": presencas, "percentual": pct,
                })
        return out

    def count_presencas_aluno(self, aluno_id):
        presencas = 0
        previstas = 0
        uid = str(aluno_id)
        for p in self.presencas:
            if str(p.get("aluno_id")) == uid and p.get("presente"):
                presencas += 1
        for m in self.materias.values():
            if str(m.get("curso_id")) in [str(a.get("curso_id")) for a in self.matriculas.values() if str(a.get("aluno_id")) == uid and a.get("status") == "ativa"]:
                previstas += int(m.get("total_aulas_previstas") or 0)
        pct = round((presencas / previstas) * 100.0, 1) if previstas > 0 else 0.0
        return presencas, pct

    def list_anexos_aula(self, professor_id=None, aula_id=None, limit=50, offset=0):
        items = list(self.anexos_aula)
        if professor_id:
            items = [a for a in items if str(a.get("professor_id")) == str(professor_id)]
        if aula_id:
            items = [a for a in items if str(a.get("aula_id")) == str(aula_id)]
        items.sort(key=lambda a: a.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for a in items[offset:offset + limit]:
            ac = a.copy()
            ac["materia_nome"] = self.materias.get(str(ac.get("materia_id")), {}).get("nome")
            ac["data_aula"] = self.aulas.get(str(ac.get("aula_id")), {}).get("data_aula")
            out.append(ac)
        return total, out

    def list_atas(self, professor_id=None, aula_id=None, limit=50, offset=0):
        items = list(self.atas)
        if professor_id:
            items = [a for a in items if str(a.get("professor_id")) == str(professor_id)]
        if aula_id:
            items = [a for a in items if str(a.get("aula_id")) == str(aula_id)]
        items.sort(key=lambda a: a.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for a in items[offset:offset + limit]:
            ac = a.copy()
            ac["materia_nome"] = self.materias.get(str(ac.get("materia_id")), {}).get("nome")
            ac["data_aula"] = self.aulas.get(str(ac.get("aula_id")), {}).get("data_aula")
            ac["professor_nome"] = self.usuarios.get(str(ac.get("professor_id")), {}).get("nome")
            out.append(ac)
        return total, out

    # ========== Certificados (RN-05) ==========

    def list_certificados(self, query=None, limit=50, offset=0):
        items = list(self.certificados.values())
        if query:
            q = query.strip().lower()
            items = [c for c in items if q in (self.usuarios.get(str(c.get("aluno_id")), {}).get("nome", "") or "").lower() or q in (c.get("numero_certificado") or "").lower()]
        items.sort(key=lambda c: c.get("data_emissao") or datetime.min, reverse=True)
        total = len(items)
        out = []
        for c in items[offset:offset + limit]:
            cc = c.copy()
            cc["aluno_nome"] = self.usuarios.get(str(cc.get("aluno_id")), {}).get("nome")
            out.append(cc)
        return total, out

    def get_certificado(self, certificado_id):
        return self.certificados.get(str(certificado_id))

    def create_certificado(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.certificados[new_id] = {
            "id": new_id,
            "aluno_id": str(data.get("aluno_id")),
            "matricula_id": str(data.get("matricula_id")) if data.get("matricula_id") else None,
            "numero_certificado": data.get("numero_certificado") or f"CERT-{uuid.uuid4().hex[:8].upper()}",
            "data_emissao": data.get("data_emissao") or now,
            "data_entrega_estagio_teologia": data.get("data_entrega_estagio_teologia"),
            "data_entrega_estagio_homiletica": data.get("data_entrega_estagio_homiletica"),
            "status": data.get("status", "emitido"),
            "historico_completo": data.get("historico_completo", False),
            "criado_em": now,
            "atualizado_em": now,
        }
        return new_id

    def count_certificados(self):
        return len(self.certificados)

    def get_estagios_aluno(self, aluno_id):
        uid = str(aluno_id)
        resultados = []
        for h in self.historico_alunos:
            if str(h.get("aluno_id")) == uid and h.get("status") == "aprovado":
                nm = (h.get("nome_materia") or "").lower()
                if "teologia do minist" in nm or "teologia do ministerio" in nm or "homiletica" in nm or "homiletica" in nm:
                    resultados.append(h.copy())
        return resultados

    def get_materias_pendentes_aluno(self, aluno_id):
        uid = str(aluno_id)
        matriculas_ativas = [m for m in self.matriculas.values() if str(m.get("aluno_id")) == uid and m.get("status") in ("ativa", "trancada")]
        cursos_ids = list({str(m.get("curso_id")) for m in matriculas_ativas})
        pendentes = []
        for materia in self.materias.values():
            if str(materia.get("curso_id")) not in cursos_ids or materia.get("status") != "ativo":
                continue
            concluida = any(
                str(h.get("materia_id")) == str(materia.get("id")) and h.get("status") == "aprovado"
                for h in self.historico_alunos
                if str(h.get("aluno_id")) == uid
            )
            if not concluida:
                pendentes.append(materia.copy())
        return pendentes

    # ========== Chat (RN-06) ==========

    def list_chat_conversas(self, usuario_id=None, tipo=None, status=None, limit=50, offset=0):
        items = list(self.chat_conversas.values())
        if usuario_id:
            uid = str(usuario_id)
            items = [c for c in items if any(str(p.get("usuario_id")) == uid for p in self.chat_participantes if str(p.get("conversa_id")) == c.get("id"))]
        if tipo:
            items = [c for c in items if c.get("tipo") == tipo]
        if status:
            items = [c for c in items if c.get("status") == status]
        items.sort(key=lambda c: c.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for c in items[offset:offset + limit]:
            cc = c.copy()
            cc["participantes"] = self.get_chat_participantes(c.get("id"))
            mensagens = [m for m in self.chat_mensagens if str(m.get("conversa_id")) == c.get("id")]
            cc["total_mensagens"] = len(mensagens)
            if mensagens:
                cc["ultima_mensagem"] = max(mensagens, key=lambda m: m.get("criado_em", datetime.min)).get("conteudo")
            out.append(cc)
        return total, out

    def get_chat_conversa(self, conversa_id):
        c = self.chat_conversas.get(str(conversa_id))
        if not c:
            return None
        out = c.copy()
        out["participantes"] = self.get_chat_participantes(conversa_id)
        mensagens = [m for m in self.chat_mensagens if str(m.get("conversa_id")) == conversa_id]
        out["total_mensagens"] = len(mensagens)
        if mensagens:
            out["ultima_mensagem"] = max(mensagens, key=lambda m: m.get("criado_em", datetime.min)).get("conteudo")
        out["mensagens"] = sorted(mensagens, key=lambda m: m.get("criado_em", datetime.min))
        return out

    def create_chat_conversa(self, tipo, criado_por, nome=None, participantes=None):
        conversa_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.chat_conversas[conversa_id] = {
            "id": conversa_id, "tipo": tipo, "nome": nome, "status": "ativa",
            "criado_por": str(criado_por), "criado_em": now, "atualizado_em": now,
        }
        if tipo == "grupo":
            self.chat_grupos[str(uuid.uuid4())] = {"id": str(uuid.uuid4()), "conversa_id": conversa_id, "nome": nome, "criado_por": criado_por, "criado_em": now, "atualizado_em": now}
        for uid in (participantes or [criado_por]):
            self.chat_participantes.append({"id": str(uuid.uuid4()), "conversa_id": conversa_id, "usuario_id": str(uid), "criado_em": now})
        return conversa_id

    def add_chat_participantes(self, conversa_id, usuario_ids):
        now = datetime.now(timezone.utc)
        for uid in usuario_ids:
            exists = any(p.get("conversa_id") == conversa_id and p.get("usuario_id") == str(uid) for p in self.chat_participantes)
            if not exists:
                self.chat_participantes.append({"id": str(uuid.uuid4()), "conversa_id": conversa_id, "usuario_id": str(uid), "criado_em": now})

    def get_chat_participantes(self, conversa_id):
        out = []
        for p in self.chat_participantes:
            if str(p.get("conversa_id")) == str(conversa_id):
                u = self.usuarios.get(str(p.get("usuario_id")), {})
                out.append({"usuario_id": p.get("usuario_id"), "nome": u.get("nome"), "perfil": self.perfis.get(u.get("perfil_id"), {}).get("nome")})
        out.sort(key=lambda x: x.get("nome", ""))
        return out

    def update_chat_conversa(self, conversa_id, data):
        c = self.chat_conversas.get(str(conversa_id))
        if not c:
            return
        for k, v in data.items():
            c[k] = v
        c["atualizado_em"] = datetime.now(timezone.utc)

    def delete_chat_conversa(self, conversa_id):
        self.chat_conversas.pop(str(conversa_id), None)
        self.chat_mensagens[:] = [m for m in self.chat_mensagens if str(m.get("conversa_id")) != conversa_id]
        self.chat_participantes[:] = [p for p in self.chat_participantes if str(p.get("conversa_id")) != conversa_id]
        self.chat_grupos = {k: v for k, v in self.chat_grupos.items() if str(v.get("conversa_id")) != conversa_id}

    def list_chat_mensagens(self, conversa_id, limit=200, offset=0):
        items = [m for m in self.chat_mensagens if str(m.get("conversa_id")) == str(conversa_id)]
        items.sort(key=lambda m: m.get("criado_em", datetime.min))
        total = len(items)
        out = []
        for m in items[offset:offset + limit]:
            mc = m.copy()
            mc["remetente_nome"] = self.usuarios.get(str(mc.get("remetente_id")), {}).get("nome")
            out.append(mc)
        return total, out

    def create_chat_mensagem(self, conversa_id, remetente_id, conteudo):
        msg_id = str(uuid.uuid4())
        self.chat_mensagens.append({
            "id": msg_id, "conversa_id": str(conversa_id), "remetente_id": str(remetente_id),
            "conteudo": conteudo, "lida": False, "criado_em": datetime.now(timezone.utc),
        })
        return msg_id

    def marcar_mensagem_lida(self, mensagem_id):
        for m in self.chat_mensagens:
            if str(m.get("id")) == str(mensagem_id):
                m["lida"] = True
                m["lida_em"] = datetime.now(timezone.utc)
                break

    # ========== Financeiro ==========

    def list_vendas(self, filtros, limit=50, offset=0):
        items = list(self.vendas.values())
        if filtros.get("modalidade"):
            items = [v for v in items if v.get("modalidade") == filtros["modalidade"]]
        if filtros.get("tipo_item"):
            items = [v for v in items if v.get("tipo_item") == filtros["tipo_item"]]
        if filtros.get("polo_id"):
            items = [v for v in items if str(v.get("polo_id")) == str(filtros["polo_id"])]
        if filtros.get("escola_id"):
            items = [v for v in items if str(v.get("escola_id")) == str(filtros["escola_id"])]
        if filtros.get("aluno_id"):
            items = [v for v in items if str(v.get("aluno_id")) == str(filtros["aluno_id"])]
        if filtros.get("data_inicio"):
            items = [v for v in items if (v.get("criado_em") or datetime.min) >= filtros["data_inicio"]]
        if filtros.get("data_fim"):
            items = [v for v in items if (v.get("criado_em") or datetime.max) <= filtros["data_fim"]]
        if filtros.get("mes"):
            items = [v for v in items if (v.get("criado_em") or datetime.min).month == int(filtros["mes"])]
        if filtros.get("ano"):
            items = [v for v in items if (v.get("criado_em") or datetime.min).year == int(filtros["ano"])]
        items.sort(key=lambda v: v.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        total_valor = sum(float(v.get("valor", 0)) for v in items)
        out = []
        for v in items[offset:offset + limit]:
            vc = v.copy()
            vc["materia_nome"] = self.materias.get(str(vc.get("materia_id")), {}).get("nome")
            vc["polo_nome"] = self.polos.get(str(vc.get("polo_id")), {}).get("nome")
            vc["escola_nome"] = self.escolas.get(str(vc.get("escola_id")), {}).get("nome")
            out.append(vc)
        return total, out, total_valor

    def create_venda(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.vendas[new_id] = {
            "id": new_id, "descricao": data.get("descricao"), "modalidade": data.get("modalidade", "polo"),
            "tipo_item": data.get("tipo_item", "licenca"), "valor": data.get("valor", 0.0), "quantidade": data.get("quantidade", 1),
            "materia_id": str(data.get("materia_id")) if data.get("materia_id") else None,
            "polo_id": str(data.get("polo_id")) if data.get("polo_id") else None,
            "escola_id": str(data.get("escola_id")) if data.get("escola_id") else None,
            "aluno_id": str(data.get("aluno_id")) if data.get("aluno_id") else None,
            "criado_por": str(data.get("criado_por")) if data.get("criado_por") else None,
            "criado_em": now,
        }
        return new_id

    def list_boletos(self, filtros, limit=50, offset=0):
        items = list(self.boletos.values())
        if filtros.get("polo_id"):
            items = [b for b in items if str(b.get("polo_id")) == str(filtros["polo_id"])]
        if filtros.get("status"):
            items = [b for b in items if b.get("status") == filtros["status"]]
        if filtros.get("venda_id"):
            items = [b for b in items if str(b.get("venda_id")) == str(filtros["venda_id"])]
        items.sort(key=lambda b: b.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        return total, [b.copy() for b in items[offset:offset + limit]]

    def get_boleto(self, boleto_id):
        return self.boletos.get(str(boleto_id))

    def create_boleto(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.boletos[new_id] = {
            "id": new_id, "venda_id": str(data.get("venda_id")) if data.get("venda_id") else None,
            "polo_id": str(data.get("polo_id")) if data.get("polo_id") else None, "valor": data.get("valor", 0.0),
            "data_vencimento": data.get("data_vencimento"), "status": data.get("status", "gerado"),
            "nosso_numero": data.get("nosso_numero") or f"NXB-{uuid.uuid4().hex[:10].upper()}",
            "asaas_id": data.get("asaas_id"), "link_pdf": data.get("link_pdf"), "criado_em": now,
        }
        return new_id

    # ========== Logística ==========

    def list_pedidos_livros(self, filtros, limit=50, offset=0):
        items = list(self.pedidos_livros.values())
        if filtros.get("status"):
            items = [p for p in items if p.get("status") == filtros["status"]]
        if filtros.get("polo_id"):
            items = [p for p in items if str(p.get("polo_id")) == str(filtros["polo_id"])]
        if filtros.get("escola_id"):
            items = [p for p in items if str(p.get("escola_id")) == str(filtros["escola_id"])]
        if filtros.get("mes"):
            items = [p for p in items if (p.get("criado_em") or datetime.min).month == int(filtros["mes"])]
        if filtros.get("semestre"):
            semestre = int(filtros["semestre"])
            items = [p for p in items if ((p.get("criado_em") or datetime.min).month in (1, 2) if semestre == 1 else (p.get("criado_em") or datetime.min).month in (3, 4))]
        if filtros.get("ano"):
            items = [p for p in items if (p.get("criado_em") or datetime.min).year == int(filtros["ano"])]
        if filtros.get("data_inicio"):
            items = [p for p in items if (p.get("criado_em") or datetime.min) >= filtros["data_inicio"]]
        if filtros.get("data_fim"):
            items = [p for p in items if (p.get("criado_em") or datetime.max) <= filtros["data_fim"]]
        items.sort(key=lambda p: p.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for p in items[offset:offset + limit]:
            pc = p.copy()
            pc["polo_nome"] = self.polos.get(str(pc.get("polo_id")), {}).get("nome")
            pc["materia_nome"] = self.materias.get(str(pc.get("materia_id")), {}).get("nome")
            out.append(pc)
        return total, out

    def get_pedido_livro(self, pedido_id):
        return self.pedidos_livros.get(str(pedido_id))

    def create_pedido_livro(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.pedidos_livros[new_id] = {
            "id": new_id, "polo_id": str(data.get("polo_id")) if data.get("polo_id") else None,
            "escola_id": str(data.get("escola_id")) if data.get("escola_id") else None,
            "materia_id": str(data.get("materia_id")) if data.get("materia_id") else None,
            "quantidade": data.get("quantidade", 1), "status": data.get("status", "pendente"),
            "solicitado_por": str(data.get("solicitado_por")) if data.get("solicitado_por") else None,
            "observacao": data.get("observacao"), "criado_em": now, "atualizado_em": now,
        }
        return new_id

    def update_pedido_livro(self, pedido_id, data):
        p = self.pedidos_livros.get(str(pedido_id))
        if not p:
            return
        for k, v in data.items():
            p[k] = v
        p["atualizado_em"] = datetime.now(timezone.utc)

    # ========== Churn (RN-04) ==========

    def list_alunos_churn(self, limit=50, offset=0):
        items = list(self.alunos_churn.values())
        items.sort(key=lambda c: c.get("data_marcacao", datetime.min), reverse=True)
        total = len(items)
        out = []
        for c in items[offset:offset + limit]:
            cc = c.copy()
            u = self.usuarios.get(str(cc.get("aluno_id")), {})
            cc["aluno_nome"] = u.get("nome")
            cc["email"] = u.get("email")
            cc["cpf"] = u.get("cpf")
            a = self.alunos.get(str(cc.get("aluno_id")))
            cc["ultima_movimentacao_em"] = a.get("ultima_movimentacao_em") if a else None
            cc["popup_mensagem"] = POPUP_MENSAGEM_CHURN if (a and a.get("modalidade") == "ead") else None
            out.append(cc)
        return total, out

    def get_aluno_churn(self, aluno_id):
        for c in self.alunos_churn.values():
            if str(c.get("aluno_id")) == str(aluno_id):
                return c
        return None

    def create_aluno_churn(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.alunos_churn[new_id] = {
            "id": new_id, "aluno_id": str(data.get("aluno_id")), "motivo": data.get("motivo"),
            "data_marcacao": data.get("data_marcacao") or now, "etiqueta": data.get("etiqueta"),
            "taxa_paga": data.get("taxa_paga", False), "reingresso_em": data.get("reingresso_em"),
            "criado_em": now, "atualizado_em": now,
        }
        return new_id

    def update_aluno_churn(self, churn_id, data):
        c = self.alunos_churn.get(str(churn_id))
        if not c:
            return
        for k, v in data.items():
            c[k] = v
        c["atualizado_em"] = datetime.now(timezone.utc)

    # ========== Requisições de Troca ==========

    def list_requisicoes_troca(self, status=None, aluno_id=None, limit=50, offset=0):
        items = list(self.requisicoes_troca.values())
        if status:
            items = [r for r in items if r.get("status") == status]
        if aluno_id:
            items = [r for r in items if str(r.get("aluno_id")) == str(aluno_id)]
        items.sort(key=lambda r: r.get("criado_em", datetime.min), reverse=True)
        total = len(items)
        out = []
        for r in items[offset:offset + limit]:
            rc = r.copy()
            u = self.usuarios.get(str(rc.get("aluno_id")), {})
            rc["aluno_nome"] = u.get("nome")
            su = self.usuarios.get(str(rc.get("solicitante_id")), {})
            rc["solicitante_nome"] = su.get("nome")
            out.append(rc)
        return total, out

    def get_requisicao_troca(self, requisicao_id):
        return self.requisicoes_troca.get(str(requisicao_id))

    def create_requisicao_troca(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.requisicoes_troca[new_id] = {
            "id": new_id, "aluno_id": str(data.get("aluno_id")), "tipo": data.get("tipo"),
            "polo_origem_id": str(data.get("polo_origem_id")) if data.get("polo_origem_id") else None,
            "polo_destino_id": str(data.get("polo_destino_id")) if data.get("polo_destino_id") else None,
            "escola_destino_id": str(data.get("escola_destino_id")) if data.get("escola_destino_id") else None,
            "modalidade_destino": data.get("modalidade_destino"),
            "solicitante_id": str(data.get("solicitante_id")) if data.get("solicitante_id") else None,
            "status": data.get("status", "pendente"), "observacao": data.get("observacao"),
            "resolvido_por": None, "resolvido_em": None, "criado_em": now, "atualizado_em": now,
        }
        return new_id

    def update_requisicao_troca(self, requisicao_id, data):
        r = self.requisicoes_troca.get(str(requisicao_id))
        if not r:
            return
        for k, v in data.items():
            r[k] = v
        r["atualizado_em"] = datetime.now(timezone.utc)

    # ========== Notas / Histórico ==========

    def list_notas_aluno(self, aluno_id):
        uid = str(aluno_id)
        return [n.copy() for n in self.notas_alunos if str(n.get("aluno_id")) == uid]

    def create_nota(self, data):
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.notas_alunos.append({
            "id": new_id, "aluno_id": str(data.get("aluno_id")), "materia_id": str(data.get("materia_id")),
            "matricula_id": str(data.get("matricula_id")) if data.get("matricula_id") else None,
            "nota": data.get("nota"), "tipo_avaliacao": data.get("tipo_avaliacao", "avaliacao"),
            "ano": data.get("ano"), "semestre": data.get("semestre"), "criado_em": now, "atualizado_em": now,
        })
        # Atualiza histórico do aluno (upsert)
        u = self.usuarios.get(str(data.get("aluno_id")))
        materia = self.materias.get(str(data.get("materia_id")))
        self.upsert_historico({
            "aluno_id": data.get("aluno_id"), "materia_id": data.get("materia_id"),
            "matricula_id": data.get("matricula_id"),
            "nome_materia": materia.get("nome") if materia else None,
            "nota": data.get("nota"), "frequencia_pct": None,
            "ano": data.get("ano"), "semestre": data.get("semestre"),
            "status": "aprovado" if data.get("nota", 0) >= 6 else "reprovado",
        })
        return new_id

    def list_historico_aluno(self, aluno_id):
        uid = str(aluno_id)
        return [h.copy() for h in self.historico_alunos if str(h.get("aluno_id")) == uid]

    def upsert_historico(self, data):
        uid = str(data.get("aluno_id"))
        mid = str(data.get("materia_id"))
        existing = None
        for h in self.historico_alunos:
            if str(h.get("aluno_id")) == uid and str(h.get("materia_id")) == mid:
                existing = h
                break
        now = datetime.now(timezone.utc)
        row = {
            "id": str(uuid.uuid4()), "aluno_id": uid, "matricula_id": str(data.get("matricula_id")) if data.get("matricula_id") else None,
            "materia_id": mid, "nome_materia": data.get("nome_materia"), "nota": data.get("nota"),
            "frequencia_pct": data.get("frequencia_pct"), "ano": data.get("ano"), "semestre": data.get("semestre"),
            "status": data.get("status", "cursando"), "criado_em": existing.get("criado_em") if existing else now,
            "atualizado_em": now,
        }
        if existing:
            existing.update(row)
        else:
            self.historico_alunos.append(row)

    def list_professores_ativos(self, data_inicio=None, data_fim=None, limit=50, offset=0):
        items = []
        for u in self.usuarios.values():
            pid = u.get("perfil_id")
            if pid and self.perfis.get(pid, {}).get("nome") != "professor":
                continue
            if data_inicio and (u.get("criado_em") or datetime.min) < data_inicio:
                continue
            if data_fim and (u.get("criado_em") or datetime.max) > data_fim:
                continue
            items.append(u.copy())
        items.sort(key=lambda u: u.get("nome", ""))
        total = len(items)
        return total, items[offset:offset + limit]

    def get_professor_por_id(self, usuario_id):
        u = self.usuarios.get(str(usuario_id))
        if not u:
            return None
        out = u.copy()
        pid = u.get("perfil_id")
        out["perfil_nome"] = self.perfis.get(pid, {}).get("nome") if pid else None
        return out

    # ========== Usuários (RN-01 + métodos restantes) ==========

    def get_user_by_id(self, user_id):
        u = self.usuarios.get(str(user_id))
        if not u:
            return None
        out = u.copy()
        pid = u.get("perfil_id")
        if pid and pid in self.perfis:
            out["perfil_nome"] = self.perfis[pid]["nome"]
        out["gerenciado_via"] = self._gerenciado_via(u)
        return out

    def get_user_by_email(self, email):
        clean = email.strip().lower()
        for u in self.usuarios.values():
            if (u.get("email") or "").strip().lower() == clean:
                out = u.copy()
                pid = u.get("perfil_id")
                if pid and pid in self.perfis:
                    out["perfil_nome"] = self.perfis[pid]["nome"]
                out["gerenciado_via"] = self._gerenciado_via(u)
                return out
        return None

    def get_user_by_cpf(self, cpf):
        clean_cpf = "".join(filter(str.isdigit, cpf))
        for u in self.usuarios.values():
            u_cpf = "".join(filter(str.isdigit, u.get("cpf") or ""))
            if u_cpf and u_cpf == clean_cpf:
                out = u.copy()
                pid = u.get("perfil_id")
                if pid and pid in self.perfis:
                    out["perfil_nome"] = self.perfis[pid]["nome"]
                out["gerenciado_via"] = self._gerenciado_via(u)
                return out
        return None

    def create_user(self, data):
        new_id = data.get("id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_record = {
            "id": new_id, "nome": data.get("nome", ""), "sobrenome": data.get("sobrenome", ""),
            "email": data.get("email"), "cpf": data.get("cpf"), "senha_hash": data.get("senha_hash"),
            "senha_algoritmo": data.get("senha_algoritmo", "argon2id"), "telefone": data.get("telefone"),
            "celular": data.get("celular"), "foto_url": data.get("foto_url"), "perfil_id": data.get("perfil_id"),
            "polo_id": data.get("polo_id"), "escola_id": data.get("escola_id"), "status": data.get("status", "ativo"),
            "ultimo_login_em": data.get("ultimo_login_em"), "criado_em": now, "atualizado_em": now,
        }
        self.usuarios[new_id] = user_record
        return new_id

    def update_user(self, user_id, data):
        uid = str(user_id)
        if uid in self.usuarios:
            self.usuarios[uid].update(data)
            self.usuarios[uid]["atualizado_em"] = datetime.now(timezone.utc)

    def delete_user(self, user_id):
        uid = str(user_id)
        if uid in self.usuarios:
            del self.usuarios[uid]
        self.usuario_permissoes = [up for up in self.usuario_permissoes if up["usuario_id"] != uid]

    def get_user_permissions(self, user_id):
        uid = str(user_id)
        perm_ids = [up["permissao_id"] for up in self.usuario_permissoes if up["usuario_id"] == uid]
        return sorted([self.permissoes[pid]["chave"] for pid in perm_ids if pid in self.permissoes])

    def ensure_permissoes(self, keys):
        for k in keys:
            clean_k = k.strip().lower()
            exists = any(p["chave"] == clean_k for p in self.permissoes.values())
            if not exists:
                pid = f"perm-{clean_k}"
                self.permissoes[pid] = {"id": pid, "chave": clean_k, "descricao": f"Permissão {clean_k}"}

    def set_user_permissions(self, user_id, permission_keys):
        uid = str(user_id)
        self.ensure_permissoes(permission_keys)
        self.usuario_permissoes = [up for up in self.usuario_permissoes if up["usuario_id"] != uid]
        clean_keys = set(k.strip().lower() for k in permission_keys)
        for pid, pdata in self.permissoes.items():
            if pdata["chave"] in clean_keys:
                self.usuario_permissoes.append({"usuario_id": uid, "permissao_id": pid})

    def list_perfis(self):
        return list(self.perfis.values())

    def get_perfil_by_id(self, perfil_id):
        return self.perfis.get(str(perfil_id))

    def get_perfil_by_nome(self, nome):
        clean_nome = nome.strip().lower()
        for p in self.perfis.values():
            if p["nome"].lower() == clean_nome:
                return p.copy()
        return None

    def list_permissoes(self):
        return list(self.permissoes.values())

    def list_audit_logs(self, usuario_id=None, entidade=None, acao=None, data_inicio=None, data_fim=None, limit=50, offset=0):
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
        out = []
        for l in filtered[offset:offset + limit]:
            l_copy = l.copy()
            uid = l.get("usuario_id")
            if uid and uid in self.usuarios:
                l_copy["usuario_nome"] = self.usuarios[uid].get("nome")
                l_copy["usuario_email"] = self.usuarios[uid].get("email")
            out.append(l_copy)
        return total, out

    def record_audit_log(self, usuario_id=None, acao="", entidade="usuarios", entidade_id=None, dados_antes=None, dados_depois=None, ip=None):
        self.logs_auditoria.append({
            "id": str(uuid.uuid4()), "usuario_id": str(usuario_id) if usuario_id else None,
            "acao": acao, "entidade": entidade, "entidade_id": str(entidade_id) if entidade_id else None,
            "dados_antes": dados_antes, "dados_depois": dados_depois, "ip": ip,
            "criado_em": datetime.now(timezone.utc), "atualizado_em": datetime.now(timezone.utc),
        })

    def list_configuracoes(self):
        return list(self.configuracoes.values())

    def get_configuracao(self, chave):
        return self.configuracoes.get(chave.strip())

    def set_configuracao(self, chave, valor):
        k = chave.strip()
        now = datetime.now(timezone.utc)
        if k in self.configuracoes:
            self.configuracoes[k]["valor"] = valor
            self.configuracoes[k]["atualizado_em"] = now
        else:
            self.configuracoes[k] = {"id": str(uuid.uuid4()), "chave": k, "valor": valor, "criado_em": now, "atualizado_em": now}
        return self.configuracoes[k].copy()

    def list_etl_sync_runs(self, status=None, limit=50, offset=0):
        filtered = self.etl_sync_runs
        if status:
            s_clean = status.strip().lower()
            filtered = [r for r in filtered if r.get("status", "").lower() == s_clean]
        filtered = sorted(filtered, key=lambda x: x.get("iniciado_em", datetime.min), reverse=True)
        total = len(filtered)
        return total, [r.copy() for r in filtered[offset:offset + limit]]

    def get_etl_sync_run(self, run_id):
        for r in self.etl_sync_runs:
            if r.get("id") == int(run_id):
                return r.copy()
        return None

    def list_etl_erros(self, execucao_id, limit=50, offset=0):
        eid = int(execucao_id)
        filtered = [e for e in self.etl_erros if e.get("execucao_id") == eid]
        filtered = sorted(filtered, key=lambda x: x.get("criado_em", datetime.min), reverse=True)
        total = len(filtered)
        return total, [r.copy() for r in filtered[offset:offset + limit]]


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
