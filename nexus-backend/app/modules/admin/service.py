"""Serviço contendo as regras de negócio do módulo administrativo."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.security import hash_password
from app.modules.admin.repository import AdminRepositoryInterface, get_admin_repository
from app.modules.admin.schemas import (
    ConfiguracaoResponse,
    ConfiguracaoSetRequest,
    EtlErroResponse,
    EtlSyncRunListResponse,
    EtlSyncRunResponse,
    LogAuditoriaListResponse,
    LogAuditoriaResponse,
    PerfilItemResponse,
    PermissaoItemResponse,
    UsuarioAdminResponse,
    UsuarioCreateRequest,
    UsuarioListResponse,
    UsuarioPermissoesUpdateRequest,
    UsuarioUpdateRequest,
)


class AdminService:
    def __init__(self, repo: Optional[AdminRepositoryInterface] = None) -> None:
        self._repo = repo

    @property
    def repo(self) -> AdminRepositoryInterface:
        return self._repo or get_admin_repository()

    def _build_user_response(
        self, user_data: Dict[str, Any], permissoes: Optional[List[str]] = None
    ) -> UsuarioAdminResponse:
        uid = str(user_data["id"])
        if permissoes is None:
            permissoes = self.repo.get_user_permissions(uid)

        return UsuarioAdminResponse(
            id=uid,
            nome=user_data.get("nome", ""),
            sobrenome=user_data.get("sobrenome", ""),
            email=user_data.get("email"),
            cpf=user_data.get("cpf"),
            telefone=user_data.get("telefone"),
            celular=user_data.get("celular"),
            foto_url=user_data.get("foto_url"),
            status=user_data.get("status", "ativo"),
            perfil_id=str(user_data["perfil_id"]) if user_data.get("perfil_id") else None,
            perfil_nome=user_data.get("perfil_nome"),
            polo_id=str(user_data["polo_id"]) if user_data.get("polo_id") else None,
            escola_id=str(user_data["escola_id"]) if user_data.get("escola_id") else None,
            permissoes=permissoes,
            ultimo_login_em=user_data.get("ultimo_login_em"),
            criado_em=user_data.get("criado_em"),
            atualizado_em=user_data.get("atualizado_em"),
        )

    # ---------- CRUD de Usuários ----------

    def list_usuarios(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> UsuarioListResponse:
        total, raw_users = self.repo.list_users(
            query=query,
            perfil_id=perfil_id,
            perfil_nome=perfil_nome,
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        items: List[UsuarioAdminResponse] = []
        for u in raw_users:
            perms = self.repo.get_user_permissions(str(u["id"]))
            items.append(self._build_user_response(u, perms))

        return UsuarioListResponse(
            total=total,
            items=items,
            limit=limit,
            offset=offset,
        )

    def get_usuario(self, user_id: str) -> UsuarioAdminResponse:
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        perms = self.repo.get_user_permissions(user_id)
        return self._build_user_response(user, perms)

    def create_usuario(
        self,
        dados: UsuarioCreateRequest,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> UsuarioAdminResponse:
        # 1. Verifica duplicidade de e-mail
        if dados.email:
            existing = self.repo.get_user_by_email(dados.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O e-mail '{dados.email}' já está em uso por outro usuário",
                )

        # 2. Verifica duplicidade de CPF
        if dados.cpf:
            existing_cpf = self.repo.get_user_by_cpf(dados.cpf)
            if existing_cpf:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O CPF informado já está cadastrado",
                )

        # 3. Resolve perfil
        perfil_id = dados.perfil_id
        if not perfil_id and dados.perfil_nome:
            p = self.repo.get_perfil_by_nome(dados.perfil_nome)
            if p:
                perfil_id = p["id"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Perfil '{dados.perfil_nome}' não encontrado no sistema",
                )

        # 4. Gera hash Argon2id da senha inicial
        senha_hash = hash_password(dados.senha)

        # 5. Cria usuário no repositório
        user_dict = {
            "nome": dados.nome.strip(),
            "sobrenome": dados.sobrenome.strip() if dados.sobrenome else "",
            "email": dados.email.strip().lower(),
            "cpf": dados.cpf.strip() if dados.cpf else None,
            "senha_hash": senha_hash,
            "senha_algoritmo": "argon2id",
            "perfil_id": perfil_id,
            "polo_id": dados.polo_id,
            "escola_id": dados.escola_id,
            "telefone": dados.telefone,
            "celular": dados.celular,
            "status": dados.status,
        }
        new_id = self.repo.create_user(user_dict)

        # 6. Atribui permissões granulares
        if dados.permissoes:
            self.repo.set_user_permissions(new_id, dados.permissoes)

        # 7. Registra auditoria
        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_criado",
            entidade="usuarios",
            entidade_id=new_id,
            dados_depois={
                "nome": dados.nome,
                "email": dados.email,
                "perfil_id": perfil_id,
                "status": dados.status,
                "permissoes": dados.permissoes,
            },
            ip=client_ip,
        )

        return self.get_usuario(new_id)

    def update_usuario(
        self,
        user_id: str,
        dados: UsuarioUpdateRequest,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> UsuarioAdminResponse:
        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        old_perms = self.repo.get_user_permissions(user_id)

        # Valida duplicidade se o e-mail for alterado
        if dados.email and dados.email.strip().lower() != (old_user.get("email") or "").lower():
            existing = self.repo.get_user_by_email(dados.email)
            if existing and str(existing["id"]) != str(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O e-mail '{dados.email}' já está em uso",
                )

        # Valida CPF se for alterado
        if dados.cpf and dados.cpf.strip() != (old_user.get("cpf") or ""):
            existing_cpf = self.repo.get_user_by_cpf(dados.cpf)
            if existing_cpf and str(existing_cpf["id"]) != str(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O CPF informado já está em uso",
                )

        # Resolve perfil se fornecido perfil_nome
        perfil_id = dados.perfil_id
        if not perfil_id and dados.perfil_nome:
            p = self.repo.get_perfil_by_nome(dados.perfil_nome)
            if p:
                perfil_id = p["id"]

        update_dict: Dict[str, Any] = {}
        if dados.nome is not None:
            update_dict["nome"] = dados.nome.strip()
        if dados.sobrenome is not None:
            update_dict["sobrenome"] = dados.sobrenome.strip()
        if dados.email is not None:
            update_dict["email"] = dados.email.strip().lower()
        if dados.cpf is not None:
            update_dict["cpf"] = dados.cpf.strip() if dados.cpf else None
        if perfil_id is not None:
            update_dict["perfil_id"] = perfil_id
        if dados.polo_id is not None:
            update_dict["polo_id"] = dados.polo_id
        if dados.escola_id is not None:
            update_dict["escola_id"] = dados.escola_id
        if dados.telefone is not None:
            update_dict["telefone"] = dados.telefone
        if dados.celular is not None:
            update_dict["celular"] = dados.celular
        if dados.status is not None:
            update_dict["status"] = dados.status

        if update_dict:
            self.repo.update_user(user_id, update_dict)

        # Atualiza permissões se enviadas
        if dados.permissoes is not None:
            self.repo.set_user_permissions(user_id, dados.permissoes)

        new_perms = self.repo.get_user_permissions(user_id)

        # Registra auditoria com dados_antes e dados_depois
        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_atualizado",
            entidade="usuarios",
            entidade_id=user_id,
            dados_antes={
                "nome": old_user.get("nome"),
                "email": old_user.get("email"),
                "status": old_user.get("status"),
                "perfil_id": old_user.get("perfil_id"),
                "permissoes": old_perms,
            },
            dados_depois={
                "nome": update_dict.get("nome", old_user.get("nome")),
                "email": update_dict.get("email", old_user.get("email")),
                "status": update_dict.get("status", old_user.get("status")),
                "perfil_id": update_dict.get("perfil_id", old_user.get("perfil_id")),
                "permissoes": new_perms,
            },
            ip=client_ip,
        )

        return self.get_usuario(user_id)

    def update_usuario_permissoes(
        self,
        user_id: str,
        dados: UsuarioPermissoesUpdateRequest,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> UsuarioAdminResponse:
        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        old_perms = self.repo.get_user_permissions(user_id)
        self.repo.set_user_permissions(user_id, dados.permissoes)
        new_perms = self.repo.get_user_permissions(user_id)

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_permissoes_atualizadas",
            entidade="usuario_permissoes",
            entidade_id=user_id,
            dados_antes={"permissoes": old_perms},
            dados_depois={"permissoes": new_perms},
            ip=client_ip,
        )

        return self.get_usuario(user_id)

    def reset_usuario_senha(
        self,
        user_id: str,
        nova_senha: str,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> dict[str, str]:
        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        if len(nova_senha) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A nova senha deve possuir no mínimo 6 caracteres",
            )

        new_hash = hash_password(nova_senha)
        self.repo.update_user(
            user_id,
            {"senha_hash": new_hash, "senha_algoritmo": "argon2id"},
        )

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="senha_alterada_admin",
            entidade="usuarios",
            entidade_id=user_id,
            dados_depois={"algoritmo": "argon2id", "alterado_por_admin": True},
            ip=client_ip,
        )

        return {"message": "Senha do usuário redefinida com sucesso para Argon2id."}

    def delete_usuario(
        self,
        user_id: str,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> dict[str, str]:
        if actor_user_id and str(actor_user_id) == str(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é permitido excluir o próprio usuário administrador logado",
            )

        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        self.repo.delete_user(user_id)

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_excluido",
            entidade="usuarios",
            entidade_id=user_id,
            dados_antes={"nome": old_user.get("nome"), "email": old_user.get("email")},
            ip=client_ip,
        )

        return {"message": "Usuário excluído com sucesso."}

    # ---------- Perfis & Permissões ----------

    def list_perfis(self) -> List[PerfilItemResponse]:
        rows = self.repo.list_perfis()
        return [PerfilItemResponse(id=str(r["id"]), nome=r["nome"], descricao=r.get("descricao")) for r in rows]

    def list_permissoes(self) -> List[PermissaoItemResponse]:
        rows = self.repo.list_permissoes()
        return [PermissaoItemResponse(id=str(r["id"]), chave=r["chave"], descricao=r.get("descricao")) for r in rows]

    # ---------- Logs de Auditoria ----------

    def list_audit_logs(
        self,
        usuario_id: Optional[str] = None,
        entidade: Optional[str] = None,
        acao: Optional[str] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LogAuditoriaListResponse:
        total, rows = self.repo.list_audit_logs(
            usuario_id=usuario_id,
            entidade=entidade,
            acao=acao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=limit,
            offset=offset,
        )

        items = [
            LogAuditoriaResponse(
                id=str(r["id"]),
                usuario_id=str(r["usuario_id"]) if r.get("usuario_id") else None,
                usuario_nome=r.get("usuario_nome"),
                usuario_email=r.get("usuario_email"),
                acao=r["acao"],
                entidade=r.get("entidade"),
                entidade_id=str(r["entidade_id"]) if r.get("entidade_id") else None,
                dados_antes=r.get("dados_antes") if isinstance(r.get("dados_antes"), dict) else None,
                dados_depois=r.get("dados_depois") if isinstance(r.get("dados_depois"), dict) else None,
                ip=r.get("ip"),
                criado_em=r.get("criado_em"),
            )
            for r in rows
        ]

        return LogAuditoriaListResponse(
            total=total,
            items=items,
            limit=limit,
            offset=offset,
        )

    # ---------- Configurações Gerais ----------

    def list_configuracoes(self) -> List[ConfiguracaoResponse]:
        rows = self.repo.list_configuracoes()
        return [
            ConfiguracaoResponse(
                id=str(r["id"]) if r.get("id") else None,
                chave=r["chave"],
                valor=r["valor"],
                criado_em=r.get("criado_em"),
                atualizado_em=r.get("atualizado_em"),
            )
            for r in rows
        ]

    def get_configuracao(self, chave: str) -> ConfiguracaoResponse:
        row = self.repo.get_configuracao(chave)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuração '{chave}' não encontrada",
            )
        return ConfiguracaoResponse(
            id=str(row["id"]) if row.get("id") else None,
            chave=row["chave"],
            valor=row["valor"],
            criado_em=row.get("criado_em"),
            atualizado_em=row.get("atualizado_em"),
        )

    def set_configuracao(
        self,
        chave: str,
        valor: Any,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> ConfiguracaoResponse:
        old = self.repo.get_configuracao(chave)
        old_val = old.get("valor") if old else None

        updated = self.repo.set_configuracao(chave, valor)

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="configuracao_atualizada",
            entidade="configuracoes",
            entidade_id=chave,
            dados_antes={"chave": chave, "valor": old_val},
            dados_depois={"chave": chave, "valor": valor},
            ip=client_ip,
        )

        return ConfiguracaoResponse(
            id=str(updated["id"]) if updated.get("id") else None,
            chave=updated["chave"],
            valor=updated["valor"],
            criado_em=updated.get("criado_em"),
            atualizado_em=updated.get("atualizado_em"),
        )

    # ---------- ETL Sync Runs ----------

    def list_etl_execucoes(
        self,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EtlSyncRunListResponse:
        total, rows = self.repo.list_etl_sync_runs(status=status_filter, limit=limit, offset=offset)

        items: List[EtlSyncRunResponse] = []
        total_lidos = 0
        total_inseridos = 0

        for r in rows:
            duracao = r.get("duracao_segundos")
            if duracao is not None:
                duracao = float(duracao)

            total_lidos += int(r.get("total_lido") or 0)
            total_inseridos += int(r.get("total_inserido") or 0)

            items.append(
                EtlSyncRunResponse(
                    id=int(r["id"]),
                    modo=r["modo"],
                    iniciado_em=r["iniciado_em"],
                    finalizado_em=r.get("finalizado_em"),
                    total_lido=int(r.get("total_lido") or 0),
                    total_inserido=int(r.get("total_inserido") or 0),
                    total_atualizado=int(r.get("total_atualizado") or 0),
                    total_erro=int(r.get("total_erro") or 0),
                    status=r.get("status", "rodando"),
                    duracao_segundos=duracao,
                    total_erros_detalhados=int(r.get("total_erros_detalhados") or 0),
                )
            )

        taxa_sucesso = (total_inseridos / total_lidos * 100.0) if total_lidos > 0 else 100.0

        return EtlSyncRunListResponse(
            total=total,
            items=items,
            taxa_sucesso_geral=round(taxa_sucesso, 2),
        )

    def get_etl_execucao_erros(
        self,
        execucao_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EtlErroResponse]:
        run = self.repo.get_etl_sync_run(execucao_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execução ETL id {execucao_id} não encontrada",
            )

        _, rows = self.repo.list_etl_erros(execucao_id, limit=limit, offset=offset)
        return [
            EtlErroResponse(
                id=int(r["id"]),
                execucao_id=int(r["execucao_id"]) if r.get("execucao_id") else None,
                tabela_origem=r.get("tabela_origem"),
                id_origem=r.get("id_origem"),
                erro=r.get("erro"),
                linha_raw=r.get("linha_raw"),
                criado_em=r.get("criado_em"),
            )
            for r in rows
        ]
