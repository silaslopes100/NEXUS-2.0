"""Serviço contendo as regras de negócio do módulo administrativo."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.core.security import hash_password
from app.modules.admin.repository import AdminRepositoryInterface, get_admin_repository
from app.modules.admin.schemas import (
    AjusteEstoqueRequest,
    AlunoCreateRequest,
    AlunoDesistenteListResponse,
    AlunoDesistenteResponse,
    AlunoListResponse,
    AlunoResponse,
    AlunoUpdateRequest,
    AnexoAulaResponse,
    AtaResponse,
    AulaCreateRequest,
    AulaListResponse,
    AulaResponse,
    BoletoCreateRequest,
    BoletoListResponse,
    BoletoResponse,
    CertificadoDetalheResponse,
    CertificadoEmitirRequest,
    CertificadoListResponse,
    CertificadoResponse,
    ChatMensagemCreateRequest,
    ChatMensagemResponse,
    ChatGrupoCreateRequest,
    ConversaCreateRequest,
    ConversaDetalheResponse,
    ConversaListResponse,
    ConversaResponse,
    CursoCreateRequest,
    CursoListResponse,
    CursoResponse,
    ConfiguracaoBulkUpdateRequest,
    ConfiguracaoResponse,
    ConfiguracaoSetRequest,
    DashboardResumoResponse,
    DistribuicaoEstoqueRequest,
    FeedNoticiaResponse,
    LembreteResponse,
    MatriculaEadListResponse,
    MatriculaEadResponse,
    EadCalendarioCreateRequest,
    EadProgressoRequest,
    EscolaCreateRequest,
    EscolaDetalheResponse,
    EscolaListResponse,
    EscolaResponse,
    EscolaUpdateRequest,
    FeedNoticiaCreateRequest,
    HistoricoListResponse,
    LembreteCreateRequest,
    LicencaEstoqueListResponse,
    LicencaEstoqueResponse,
    LogAuditoriaListResponse,
    LogAuditoriaResponse,
    MateriaCreateRequest,
    MateriaListResponse,
    MateriaResponse,
    MatriculaCreateRequest,
    MatriculaListResponse,
    MatriculaResponse,
    ModuloCreateRequest,
    ModuloListResponse,
    ModuloResponse,
    MovimentacaoListResponse,
    MovimentacaoResponse,
    NotaCreateRequest,
    NotaHistoricoItem,
    NotaResponse,
    PedidoLivroCreateRequest,
    PedidoLivroListResponse,
    PedidoLivroResponse,
    PerfilItemResponse,
    PerfilMeUpdateRequest,
    PermissaoItemResponse,
    PresencaListaRequest,
    PresencaMateriaItem,
    PresencaProfessorItem,
    PresencaResponse,
    PoloCreateRequest,
    PoloDetalheResponse,
    PoloListResponse,
    PoloResponse,
    PoloUpdateRequest,
    RankingPoloItem,
    RankingPolosResponse,
    ReingressoRequest,
    RequisicaoTrocaCreateRequest,
    RequisicaoTrocaDecisaoRequest,
    RequisicaoTrocaListResponse,
    RequisicaoTrocaResponse,
    UsuarioAdminResponse,
    UsuarioCreateRequest,
    UsuarioListResponse,
    UsuarioPermissoesUpdateRequest,
    UsuarioUpdateRequest,
    VendaCreateRequest,
    VendaListResponse,
    VendaResponse,
    WHATSAPP_CHURN,
)


# Regras de negócio (constantes)
PRECO_MATERIA_EAD = 45.00  # RN-03: preço por matéria EAD
REINGRESSO_TAXA_REAIS = 100.00  # RN-04: taxa de reingresso
REINGRESSO_LICENCAS = 2  # RN-04: quantidade de licenças alternativa
DIAS_PARA_DESISTENTE = 365  # RN-04 / RN-03: > 1 ano sem movimentação
DIA_SEMANA_INICIO_AULA = 1  # segunda-feira (presença)


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

    # ==================== Polos (RN-01) ====================

    def _actor_is_global(self, actor: Dict[str, Any]) -> bool:
        return actor.get("perfil") in ("admin", "secretario_geral")

    def _actor_scope(self, actor: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        perfil = actor.get("perfil")
        if perfil in ("admin", "secretario_geral"):
            return None, None
        if perfil == "coordenador_polo":
            return actor.get("polo_id"), None
        if perfil == "secretario_escola":
            return None, actor.get("escola_id")
        return None, None

    def create_polo_com_usuario(
        self,
        actor: Dict[str, Any],
        polo_data: PoloCreateRequest,
    ) -> Tuple[str, str]:
        polo_id = str(uuid.uuid4())
        usuario_id = str(uuid.uuid4())
        polo_payload = polo_data.model_dump(exclude={"senha"}) | {"id": polo_id, "usuario_id": usuario_id}
        usuario_payload = {
            "id": usuario_id,
            "nome": polo_data.responsavel,
            "email": polo_data.email,
            "cpf": polo_data.cpf,
            "senha_hash": hash_password(polo_data.senha),
            "perfil_id": "coordenador_polo",
            "polo_id": polo_id,
            "status": polo_data.status,
        }
        permission_keys = [
            "p_dashboard", "p_alunos", "p_polos", "p_cursos", "p_modulos",
            "p_licencas", "p_ead", "p_financeiro", "p_logistica", "p_chat",
            "p_certificados", "p_config", "p_auditoria", "p_usuarios", "p_relatorios",
        ]
        self.repo.create_polo_com_usuario(polo_payload, usuario_payload, permission_keys)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="create", entidade="polo", entidade_id=polo_id,
            dados_antes=None, dados_depois={**polo_payload, **usuario_payload},
        )
        return polo_id, usuario_id

    def update_polo_sincronizar_usuario(
        self, actor: Dict[str, Any], polo_id: str, polo_data: PoloUpdateRequest,
    ) -> None:
        polo_existente = self.repo.get_polo(polo_id)
        if not polo_existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Polo id {polo_id} não encontrado")
        usuario_id = polo_existente.get("usuario_id")
        if not usuario_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Polo não possui usuário coordenador vinculado")
        polo_payload = polo_data.model_dump(exclude_unset=True) | {"id": polo_id}
        usuario_payload: Dict[str, Any] = {}
        if polo_data.senha:
            usuario_payload["senha_hash"] = hash_password(polo_data.senha)
        if polo_data.nome is not None:
            usuario_payload["nome"] = polo_data.nome
        if polo_data.cpf is not None:
            usuario_payload["cpf"] = polo_data.cpf
        if polo_data.email is not None:
            usuario_payload["email"] = polo_data.email
        if usuario_payload:
            self.repo.update_usuario(usuario_id, usuario_payload)
        self.repo.update_polo_sincronizar_usuario(polo_id, polo_payload, usuario_id, usuario_payload)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="update", entidade="polo", entidade_id=polo_id,
            dados_antes=polo_existente, dados_depois={**polo_existente, **polo_payload},
        )

    def delete_polo(self, actor: Dict[str, Any], polo_id: str) -> None:
        polo_existente = self.repo.get_polo(polo_id)
        if not polo_existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Polo id {polo_id} não encontrado")
        usuario_id = polo_existente.get("usuario_id") or ""
        self.repo.desativar_polo_e_usuario(polo_id, usuario_id)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="delete", entidade="polo", entidade_id=polo_id,
            dados_antes=polo_existente, dados_depois={"status": "inativo", "deletado_em": datetime.now(timezone.utc)},
        )

    def list_polos(
        self, actor: Dict[str, Any], query: Optional[str] = None,
        status_filter: Optional[str] = None, polo_id: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[PoloResponse]]:
        if not self._actor_is_global(actor) and polo_id is None:
            polo_id = actor.get("polo_id")
        total, rows = self.repo.list_polos(query=query, status=status_filter, polo_id=polo_id, limit=limit, offset=offset)
        return total, [PoloResponse.model_validate(r) for r in rows]

    def get_polo(self, actor: Dict[str, Any], polo_id: str) -> PoloDetalheResponse:
        detalhe = self.repo.get_polo_detalhes(polo_id)
        if not detalhe:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Polo id {polo_id} não encontrado")
        return PoloDetalheResponse.model_validate(detalhe)

    def get_polo_by_usuario(self, actor: Dict[str, Any], usuario_id: str) -> Optional[PoloResponse]:
        polo = self.repo.get_polo_by_usuario(usuario_id)
        if not polo:
            return None
        return PoloResponse.model_validate(polo)

    def get_ranking_polos(self, actor: Dict[str, Any]) -> List[RankingPoloItem]:
        rows = self.repo.get_ranking_polos()
        return [RankingPoloItem.model_validate(r) for r in rows]

    # ==================== Escolas (RN-01) ====================

    def create_escola_com_usuario(
        self, actor: Dict[str, Any], escola_data: EscolaCreateRequest,
    ) -> Tuple[str, str]:
        escola_id = str(uuid.uuid4())
        usuario_id = str(uuid.uuid4())
        escola_payload = escola_data.model_dump(exclude={"senha"}) | {"id": escola_id, "usuario_id": usuario_id}
        usuario_payload = {
            "id": usuario_id,
            "nome": escola_data.responsavel,
            "email": escola_data.email,
            "cpf": escola_data.cpf,
            "senha_hash": hash_password(escola_data.senha),
            "perfil_id": "secretario_escola",
            "escola_id": escola_id,
            "status": escola_data.status,
        }
        permission_keys = [
            "p_dashboard", "p_alunos", "p_polos", "p_escolas", "p_cursos", "p_modulos",
            "p_licencas", "p_ead", "p_financeiro", "p_logistica", "p_chat", "p_certificados",
            "p_config", "p_auditoria", "p_usuarios", "p_relatorios",
        ]
        self.repo.create_escola_com_usuario(escola_payload, usuario_payload, permission_keys)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="create", entidade="escola", entidade_id=escola_id,
            dados_antes=None, dados_depois={**escola_payload, **usuario_payload},
        )
        return escola_id, usuario_id

    def update_escola_sincronizar_usuario(
        self, actor: Dict[str, Any], escola_id: str, escola_data: EscolaUpdateRequest,
    ) -> None:
        escola_existente = self.repo.get_escola(escola_id)
        if not escola_existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Escola id {escola_id} não encontrada")
        usuario_id = escola_existente.get("usuario_id")
        if not usuario_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escola não possui usuário secretário vinculado")
        escola_payload = escola_data.model_dump(exclude_unset=True) | {"id": escola_id}
        usuario_payload: Dict[str, Any] = {}
        if escola_data.senha:
            usuario_payload["senha_hash"] = hash_password(escola_data.senha)
        if escola_data.nome is not None:
            usuario_payload["nome"] = escola_data.nome
        if escola_data.cpf is not None:
            usuario_payload["cpf"] = escola_data.cpf
        if escola_data.email is not None:
            usuario_payload["email"] = escola_data.email
        if usuario_payload:
            self.repo.update_usuario(usuario_id, usuario_payload)
        self.repo.update_escola_sincronizar_usuario(escola_id, escola_payload, usuario_id, usuario_payload)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="update", entidade="escola", entidade_id=escola_id,
            dados_antes=escola_existente, dados_depois={**escola_existente, **escola_payload},
        )

    def delete_escola(self, actor: Dict[str, Any], escola_id: str) -> None:
        escola_existente = self.repo.get_escola(escola_id)
        if not escola_existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Escola id {escola_id} não encontrada")
        usuario_id = escola_existente.get("usuario_id") or ""
        self.repo.desativar_escola_e_usuario(escola_id, usuario_id)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="delete", entidade="escola", entidade_id=escola_id,
            dados_antes=escola_existente, dados_depois={"status": "inativo", "deletado_em": datetime.now(timezone.utc)},
        )

    def list_escolas(
        self, actor: Dict[str, Any], query: Optional[str] = None,
        status_filter: Optional[str] = None, polo_id: Optional[str] = None,
        escola_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[EscolaResponse]]:
        if not self._actor_is_global(actor) and escola_id is None:
            escola_id = actor.get("escola_id")
        total, rows = self.repo.list_escolas(query=query, status=status_filter, polo_id=polo_id, escola_id=escola_id, limit=limit, offset=offset)
        return total, [EscolaResponse.model_validate(r) for r in rows]

    def get_escola(self, actor: Dict[str, Any], escola_id: str) -> EscolaDetalheResponse:
        detalhe = self.repo.get_escola_detalhes(escola_id)
        if not detalhe:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Escola id {escola_id} não encontrada")
        return EscolaDetalheResponse.model_validate(detalhe)

    def get_escola_by_usuario(self, actor: Dict[str, Any], usuario_id: str) -> Optional[EscolaResponse]:
        escola = self.repo.get_escola_by_usuario(usuario_id)
        if not escola:
            return None
        return EscolaResponse.model_validate(escola)

    # ==================== Cursos ====================

    def create_curso(self, actor: Dict[str, Any], data: CursoCreateRequest) -> str:
        curso_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": curso_id}
        self.repo.create_curso(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="curso", entidade_id=curso_id, dados_antes=None, dados_depois=payload)
        return curso_id

    def update_curso(self, actor: Dict[str, Any], curso_id: str, data: CursoUpdateRequest) -> None:
        existente = self.repo.get_curso(curso_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Curso id {curso_id} não encontrado")
        payload = data.model_dump(exclude_unset=True) | {"id": curso_id}
        self.repo.update_curso(curso_id, payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="update", entidade="curso", entidade_id=curso_id, dados_antes=existente, dados_depois={**existente, **payload})

    def delete_curso(self, actor: Dict[str, Any], curso_id: str) -> None:
        existente = self.repo.get_curso(curso_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Curso id {curso_id} não encontrado")
        self.repo.delete_curso(curso_id)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="delete", entidade="curso", entidade_id=curso_id, dados_antes=existente, dados_depois={"status": "inativo", "deletado_em": datetime.now(timezone.utc)})

    def list_cursos(self, actor: Dict[str, Any], query: Optional[str] = None, limit: int = 50, offset: int = 0) -> Tuple[int, List[CursoResponse]]:
        total, rows = self.repo.list_cursos(query=query, limit=limit, offset=offset)
        return total, [CursoResponse.model_validate(r) for r in rows]

    def get_curso(self, actor: Dict[str, Any], curso_id: str) -> CursoResponse:
        curso = self.repo.get_curso(curso_id)
        if not curso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Curso id {curso_id} não encontrado")
        return CursoResponse.model_validate(curso)

    # ==================== Módulos ====================

    def create_modulo(self, actor: Dict[str, Any], data: ModuloCreateRequest) -> str:
        modulo_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": modulo_id}
        self.repo.create_modulo(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="modulo", entidade_id=modulo_id, dados_antes=None, dados_depois=payload)
        return modulo_id

    def update_modulo(self, actor: Dict[str, Any], modulo_id: str, data: ModuloUpdateRequest) -> None:
        existente = self.repo.get_modulo(modulo_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Módulo id {modulo_id} não encontrado")
        payload = data.model_dump(exclude_unset=True) | {"id": modulo_id}
        self.repo.update_modulo(modulo_id, payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="update", entidade="modulo", entidade_id=modulo_id, dados_antes=existente, dados_depois={**existente, **payload})

    def delete_modulo(self, actor: Dict[str, Any], modulo_id: str) -> None:
        existente = self.repo.get_modulo(modulo_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Módulo id {modulo_id} não encontrado")
        self.repo.delete_modulo(modulo_id)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="delete", entidade="modulo", entidade_id=modulo_id, dados_antes=existente, dados_depois={"status": "inativo", "deletado_em": datetime.now(timezone.utc)})

    def list_modulos(self, actor: Dict[str, Any], curso_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> Tuple[int, List[ModuloResponse]]:
        total, rows = self.repo.list_modulos(curso_id=curso_id, limit=limit, offset=offset)
        return total, [ModuloResponse.model_validate(r) for r in rows]

    def get_modulo(self, actor: Dict[str, Any], modulo_id: str) -> ModuloResponse:
        modulo = self.repo.get_modulo(modulo_id)
        if not modulo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Módulo id {modulo_id} não encontrado")
        return ModuloResponse.model_validate(modulo)

    # ==================== Matérias ====================

    def create_materia(self, actor: Dict[str, Any], data: MateriaCreateRequest) -> str:
        materia_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": materia_id}
        self.repo.create_materia(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="materia", entidade_id=materia_id, dados_antes=None, dados_depois=payload)
        return materia_id

    def update_materia(self, actor: Dict[str, Any], materia_id: str, data: MateriaUpdateRequest) -> None:
        existente = self.repo.get_materia(materia_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matéria id {materia_id} não encontrada")
        payload = data.model_dump(exclude_unset=True) | {"id": materia_id}
        self.repo.update_materia(materia_id, payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="update", entidade="materia", entidade_id=materia_id, dados_antes=existente, dados_depois={**existente, **payload})

    def delete_materia(self, actor: Dict[str, Any], materia_id: str) -> None:
        existente = self.repo.get_materia(materia_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matéria id {materia_id} não encontrada")
        self.repo.delete_materia(materia_id)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="delete", entidade="materia", entidade_id=materia_id, dados_antes=existente, dados_depois={"status": "inativo", "deletado_em": datetime.now(timezone.utc)})

    def list_materias(self, actor: Dict[str, Any], curso_id: Optional[str] = None, modulo_id: Optional[str] = None, query: Optional[str] = None, limit: int = 50, offset: int = 0) -> Tuple[int, List[MateriaResponse]]:
        total, rows = self.repo.list_materias(curso_id=curso_id, modulo_id=modulo_id, query=query, limit=limit, offset=offset)
        return total, [MateriaResponse.model_validate(r) for r in rows]

    def get_materia(self, actor: Dict[str, Any], materia_id: str) -> MateriaResponse:
        materia = self.repo.get_materia(materia_id)
        if not materia:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matéria id {materia_id} não encontrada")
        return MateriaResponse.model_validate(materia)

    # ==================== Matrículas ====================

    def list_matriculas(
        self, actor: Dict[str, Any], filtros: Dict[str, Any],
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[MatriculaResponse]]:
        total, rows = self.repo.list_matriculas(filtros=filtros, limit=limit, offset=offset)
        return total, [MatriculaResponse.model_validate(r) for r in rows]

    def get_matricula(self, actor: Dict[str, Any], matricula_id: str) -> MatriculaResponse:
        matricula = self.repo.get_matricula(matricula_id)
        if not matricula:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matrícula id {matricula_id} não encontrada")
        return MatriculaResponse.model_validate(matricula)

    # ==================== Alunos ====================

    def create_aluno(self, actor: Dict[str, Any], data: AlunoCreateRequest) -> Tuple[str, str, Optional[str]]:
        aluno_id = str(uuid.uuid4())
        usuario_id = str(uuid.uuid4())
        polo_id = data.polo_id if data.eh_aluno_polo else None
        escola_id = data.pertence_escola if data.eh_aluno_polo else None
        usuario_payload = {
            "id": usuario_id,
            "nome": data.nome,
            "sobrenome": data.sobrenome,
            "email": data.email,
            "cpf": data.cpf,
            "senha_hash": hash_password(data.senha),
            "perfil_id": "aluno",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "status": "ativo",
        }
        aluno_payload = data.model_dump(exclude={"senha"}) | {
            "id": aluno_id,
            "usuario_id": usuario_id,
            "modalidade": "polo" if data.eh_aluno_polo else ("ead" if data.eh_aluno_ead else "escola"),
        }
        self.repo.create_aluno_com_usuario(usuario_payload, aluno_payload, None)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="create", entidade="aluno", entidade_id=aluno_id,
            dados_antes=None, dados_depois={**usuario_payload, **aluno_payload},
        )
        return aluno_id, usuario_id, None

    def update_aluno(self, actor: Dict[str, Any], aluno_id: str, data: AlunoUpdateRequest) -> None:
        existente = self.repo.get_aluno(aluno_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno id {aluno_id} não encontrado")
        payload = data.model_dump(exclude_unset=True)
        self.repo.update_aluno(aluno_id, payload)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="update", entidade="aluno", entidade_id=aluno_id,
            dados_antes=existente, dados_depois={**existente, **payload},
        )

    def list_alunos(
        self, actor: Dict[str, Any], filtros: Dict[str, Any],
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[AlunoResponse]]:
        total, rows = self.repo.list_alunos(filtros=filtros, limit=limit, offset=offset)
        return total, [AlunoResponse.model_validate(r) for r in rows]

    def get_aluno(self, actor: Dict[str, Any], aluno_id: str) -> AlunoDetalheResponse:
        aluno = self.repo.get_aluno(aluno_id)
        if not aluno:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno id {aluno_id} não encontrado")
        return AlunoDetalheResponse.model_validate(aluno)

    # ==================== Notas / Histórico ====================

    def create_nota_aluno(self, actor: Dict[str, Any], aluno_id: str, data: NotaCreateRequest) -> str:
        nota_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": nota_id, "aluno_id": aluno_id}
        self.repo.create_nota(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="nota", entidade_id=nota_id, dados_antes=None, dados_depois=payload)
        return nota_id

    def list_notas_aluno(self, actor: Dict[str, Any], aluno_id: str) -> List[NotaResponse]:
        rows = self.repo.list_notas_aluno(aluno_id)
        return [NotaResponse.model_validate(r) for r in rows]

    def get_historico_aluno(self, actor: Dict[str, Any], aluno_id: str) -> HistoricoListResponse:
        rows = self.repo.list_historico_aluno(aluno_id)
        return HistoricoListResponse(
            total=len(rows),
            items=[NotaHistoricoItem.model_validate(r) for r in rows],
            limit=50,
            offset=0,
        )

    # ==================== Dashboard ====================

    def get_dashboard_resumo(self, actor: Dict[str, Any]) -> DashboardResumoResponse:
        polo_filter, escola_filter = self._actor_scope(actor)
        base_filtros: Dict[str, Any] = {"status": "ativa"}
        if polo_filter:
            base_filtros["polo_id"] = polo_filter
        if escola_filter:
            base_filtros["escola_id"] = escola_filter
        return DashboardResumoResponse(
            alunos_ativos=self.repo.list_alunos(filtros=base_filtros, limit=1)[0],
            matriculas=self.repo.list_matriculas(filtros=base_filtros, limit=1)[0],
            polos_ativos=self.repo.list_polos(limit=1)[0],
            escolas_ativas=self.repo.list_escolas(limit=1)[0],
            professores_ativos=self.repo.list_professores_ativos(limit=1)[0],
            certificados_emitidos=self.repo.count_certificados(),
        )

    def get_dashboard_polo_detalhe(self, actor: Dict[str, Any], polo_id: str) -> PoloDetalheResponse:
        detalhe = self.repo.get_polo_detalhes(polo_id)
        if not detalhe:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Polo id {polo_id} não encontrado")
        return PoloDetalheResponse.model_validate(detalhe)

    def get_dashboard_escola_detalhe(self, actor: Dict[str, Any], escola_id: str) -> EscolaDetalheResponse:
        detalhe = self.repo.get_escola_detalhes(escola_id)
        if not detalhe:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Escola id {escola_id} não encontrada")
        return EscolaDetalheResponse.model_validate(detalhe)

    def get_dashboard_professor_detalhe(self, actor: Dict[str, Any], professor_id: str) -> ProfessorDetalheResponse:
        prof = self.repo.get_professor_por_id(professor_id)
        if not prof:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Professor id {professor_id} não encontrado")
        detalhes = {**prof, "presencas": self.repo.get_presencas_resumo_professor(professor_id)}
        return ProfessorDetalheResponse.model_validate(detalhes)

    def get_contagem(self, actor: Dict[str, Any], visualizador: str) -> ContagemResponse:
        if visualizador == "alunos_ativos":
            total = self.repo.list_alunos({"status": "ativa"}, limit=1)[0]
        elif visualizador == "matriculas":
            total = self.repo.list_matriculas({}, limit=1)[0]
        elif visualizador == "polos_ativos":
            total = self.repo.list_polos(limit=1)[0]
        elif visualizador == "escolas_ativas":
            total = self.repo.list_escolas(limit=1)[0]
        elif visualizador == "professores_ativos":
            total = self.repo.list_professores_ativos(limit=1)[0]
        else:
            total = 0
        return ContagemResponse(titulo=visualizador, total=total)

    # ==================== EAD ====================

    def list_ead_matriculas(
        self, actor: Dict[str, Any], filtros: Dict[str, Any],
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[MatriculaEadResponse]]:
        total, rows = self.repo.list_matriculas_ead(filtros=filtros, limit=limit, offset=offset)
        return total, [MatriculaEadResponse.model_validate(r) for r in rows]

    def get_ead_calendario(
        self, actor: Dict[str, Any], curso_id: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> List[EadCalendarioResponse]:
        rows = self.repo.list_ead_calendario(curso_id=curso_id, limit=limit, offset=offset)
        return [EadCalendarioResponse.model_validate(r) for r in rows]

    def create_ead_matricula(self, actor: Dict[str, Any], data: MatriculaEadCreateRequest) -> str:
        # RN-03: limitar a 2 matérias por mês
        ano = data.data_inicio.year if data.data_inicio else datetime.now().year
        mes = data.data_inicio.month if data.data_inicio else datetime.now().month
        liberacoes = self.repo.count_liberacoes_ead_mes(data.aluno_id, ano, mes)
        if liberacoes >= 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Limite de 2 matérias por mês atingido (RN-03)")
        matricula_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": matricula_id}
        self.repo.create_matricula_ead(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="matricula_ead", entidade_id=matricula_id, dados_antes=None, dados_depois=payload)
        return matricula_id

    def get_ead_feed(self, actor: Dict[str, Any], limit: int = 50, offset: int = 0) -> List[FeedNoticiaResponse]:
        rows = self.repo.list_feed_noticias(limit=limit, offset=offset)
        return [FeedNoticiaResponse.model_validate(r) for r in rows]

    def get_ead_lembretes(self, actor: Dict[str, Any], limit: int = 50, offset: int = 0) -> List[LembreteResponse]:
        rows = self.repo.list_lembretes(limit=limit, offset=offset)
        return [LembreteResponse.model_validate(r) for r in rows]

    # ==================== Licenças / Estoque ====================

    def get_licencas_estoque(
        self, actor: Dict[str, Any], query: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[LicencaEstoqueResponse]]:
        total, rows = self.repo.list_licencas_estoque(query=query, limit=limit, offset=offset)
        return total, [LicencaEstoqueResponse.model_validate(r) for r in rows]

    def ajustar_licenca_estoque(
        self,
        actor: Dict[str, Any], materia_id: str, tipo: str, delta: int,
        observacao: Optional[str] = None,
    ) -> LicencaEstoqueResponse:
        resultado = self.repo.ajustar_licenca_estoque(materia_id, tipo, delta, None)
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="ajuste_estoque", entidade="estoque", entidade_id=materia_id,
            dados_antes=None, dados_depois={"materia_id": materia_id, "tipo": tipo, "delta": delta, "observacao": observacao},
        )
        return LicencaEstoqueResponse.model_validate(resultado)

    def list_movimentacoes(
        self, actor: Dict[str, Any], filtros: Dict[str, Any],
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[MovimentacaoResponse]]:
        total, rows = self.repo.list_licencas_movimentacoes(filtros=filtros, limit=limit, offset=offset)
        return total, [MovimentacaoResponse.model_validate(r) for r in rows]

    # ==================== Aulas ====================

    def create_aula(self, actor: Dict[str, Any], data: AulaCreateRequest) -> str:
        aula_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": aula_id}
        self.repo.create_aula(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="aula", entidade_id=aula_id, dados_antes=None, dados_depois=payload)
        return aula_id

    def list_aulas(
        self, actor: Dict[str, Any], professor_id: Optional[str] = None,
        materia_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[AulaResponse]]:
        total, rows = self.repo.list_aulas(professor_id=professor_id, materia_id=materia_id, limit=limit, offset=offset)
        return total, [AulaResponse.model_validate(r) for r in rows]

    def get_aula(self, actor: Dict[str, Any], aula_id: str) -> AulaResponse:
        aula = self.repo.get_aula(aula_id)
        if not aula:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aula id {aula_id} não encontrada")
        return AulaResponse.model_validate(aula)

    # ==================== Presenças / Anexos / Atas ====================

    def registrar_presenca(self, actor: Dict[str, Any], aula_id: str, registros: List[Dict[str, Any]]) -> None:
        # RN-07: lista de chamada pelo professor
        self.repo.registrar_presencas(aula_id=aula_id, registros=registros, registrado_por=actor.get("user_id"))
        self.repo.record_audit_log(
            actor_user_id=actor.get("user_id"), acao="registrar_presencas", entidade="presenca", entidade_id=aula_id,
            dados_antes=None, dados_depois={"registros": registros},
        )

    def list_presencas(
        self, actor: Dict[str, Any], aula_id: Optional[str] = None,
        aluno_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[PresencaResponse]]:
        total, rows = self.repo.list_presencas(aula_id=aula_id, aluno_id=aluno_id, limit=limit, offset=offset)
        return total, [PresencaResponse.model_validate(r) for r in rows]

    def get_presencas_resumo_aluno(self, actor: Dict[str, Any], aluno_id: str) -> List[PresencaMateriaItem]:
        rows = self.repo.get_presencas_resumo_aluno(aluno_id)
        return [PresencaMateriaItem.model_validate(r) for r in rows]

    def get_presencas_resumo_professor(self, actor: Dict[str, Any], professor_id: str) -> List[PresencaProfessorItem]:
        rows = self.repo.get_presencas_resumo_professor(professor_id)
        return [PresencaProfessorItem.model_validate(r) for r in rows]

    def count_presencas_aluno(self, actor: Dict[str, Any], aluno_id: str) -> Tuple[int, float]:
        return self.repo.count_presencas_aluno(aluno_id)

    def list_anexos_aula(
        self, actor: Dict[str, Any], professor_id: Optional[str] = None,
        aula_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[AnexoAulaResponse]]:
        total, rows = self.repo.list_anexos_aula(professor_id=professor_id, aula_id=aula_id, limit=limit, offset=offset)
        return total, [AnexoAulaResponse.model_validate(r) for r in rows]

    def list_atas(
        self, actor: Dict[str, Any], professor_id: Optional[str] = None,
        aula_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[AtaResponse]]:
        total, rows = self.repo.list_atas(professor_id=professor_id, aula_id=aula_id, limit=limit, offset=offset)
        return total, [AtaResponse.model_validate(r) for r in rows]

    # ==================== Certificados (RN-05) ====================

    def _certificado_elegivel(self, aluno_id: str) -> Tuple[bool, Optional[str]]:
        """Verifica se aluno tem 2 estágios + histórico completo (RN-05)."""
        estagios = self.repo.get_estagios_aluno(aluno_id)
        estagios_nomes = {e.get("nome") for e in estagios if e.get("entregue")}
        teologia = any("teologia" in (n or "").lower() for n in estagios_nomes)
        homiletica = any("homiletica" in (n or "").lower() for n in estagios_nomes)
        if not (teologia and homiletica):
            return False, "Ausente entrega dos 2 estágios (Teologia + Homilética)"
        pendentes = self.repo.get_materias_pendentes_aluno(aluno_id)
        if pendentes:
            return False, "Histórico incompleto (matérias pendentes)"
        return True, None

    def emitir_certificado(self, actor: Dict[str, Any], aluno_id: str, data: CertificadoEmitirRequest) -> str:
        elegivel, motivo = self._certificado_elegivel(aluno_id)
        if not elegivel:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Não elegível para certificado: {moto}")
        certificado_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": certificado_id, "aluno_id": aluno_id, "status": "emitido"}
        self.repo.create_certificado(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="emitir_certificado", entidade="certificado", entidade_id=certificado_id, dados_antes=None, dados_depois=payload)
        return certificado_id

    def list_certificados(self, actor: Dict[str, Any], query: Optional[str] = None, limit: int = 50, offset: int = 0) -> Tuple[int, List[CertificadoResponse]]:
        total, rows = self.repo.list_certificados(query=query, limit=limit, offset=offset)
        return total, [CertificadoResponse.model_validate(r) for r in rows]

    def get_certificado(self, actor: Dict[str, Any], certificado_id: str) -> CertificadoDetalheResponse:
        cert = self.repo.get_certificado(certificado_id)
        if not cert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Certificado id {certificado_id} não encontrado")
        return CertificadoDetalheResponse.model_validate(cert)

    # ==================== Chat (RN-06) ====================

    def list_chat_conversas(
        self, actor: Dict[str, Any], usuario_id: Optional[str] = None,
        tipo: Optional[str] = None, status: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[ConversaResponse]]:
        total, rows = self.repo.list_chat_conversas(usuario_id=usuario_id, tipo=tipo, status=status, limit=limit, offset=offset)
        return total, [ConversaResponse.model_validate(r) for r in rows]

    def get_chat_conversa(self, actor: Dict[str, Any], conversa_id: str) -> ConversaDetalheResponse:
        conv = self.repo.get_chat_conversa(conversa_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversa id {conversa_id} não encontrada")
        return ConversaDetalheResponse.model_validate(conv)

    def create_chat_conversa(self, actor: Dict[str, Any], data: ConversaCreateRequest) -> str:
        # RN-06: proibir chat aluno↔aluno
        participantes = data.participantes or []
        participantes = list(dict.fromkeys(participantes))
        if actor.get("perfil") == "aluno" and len(participantes) >= 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chat aluno↔aluno é proibido (RN-06)")
        conversa_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": conversa_id, "criado_por": actor.get("user_id")}
        self.repo.create_chat_conversa(tipo=data.tipo, criado_por=actor.get("user_id"), nome=data.nome, participantes=participantes)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="chat", entidade_id=conversa_id, dados_antes=None, dados_depois=payload)
        return conversa_id

    def create_chat_mensagem(self, actor: Dict[str, Any], conversa_id: str, data: ChatMensagemCreateRequest) -> str:
        # RN-06: proibir chat aluno↔aluno (verificar participantes da conversa)
        conv = self.repo.get_chat_conversa(conversa_id)
        if conv and actor.get("perfil") == "aluno":
            participantes = conv.get("participantes") or []
            if len(participantes) >= 2 and all(p.get("perfil") == "aluno" for p in participantes if isinstance(p, dict)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chat aluno↔aluno é proibido (RN-06)")
        mensagem_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": mensagem_id, "conversa_id": conversa_id, "remetente_id": actor.get("user_id")}
        self.repo.create_chat_mensagem(conversa_id=conversa_id, remetente_id=actor.get("user_id"), conteudo=data.conteudo)
        return mensagem_id

    def marcar_mensagem_lida(self, actor: Dict[str, Any], mensagem_id: str) -> None:
        self.repo.marcar_mensagem_lida(mensagem_id=mensagem_id)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="marcar_lida", entidade="mensagem", entidade_id=mensagem_id, dados_antes=None, dados_depois={"status": "lida"})

    def excluir_chat_admin(self, actor: Dict[str, Any], conversa_id: str) -> None:
        if actor.get("perfil") not in ("admin", "secretario_geral"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas admin pode excluir chats")
        self.repo.delete_chat_conversa(conversa_id=conversa_id)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="delete", entidade="chat", entidade_id=conversa_id, dados_antes=None, dados_depois={"status": "excluido"})

    def baixar_conversa_admin(self, actor: Dict[str, Any], conversa_id: str) -> ConversaDetalheResponse:
        if actor.get("perfil") not in ("admin", "secretario_geral"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas admin pode baixar conversas")
        conv = self.repo.get_chat_conversa(conversa_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversa id {conversa_id} não encontrada")
        return ConversaDetalheResponse.model_validate(conv)

    # ==================== Financeiro ====================

    def list_vendas(
        self, actor: Dict[str, Any], filtros: Dict[str, Any],
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[VendaResponse], float]:
        total, rows, total_valor = self.repo.list_vendas(filtros=filtros, limit=limit, offset=offset)
        return total, [VendaResponse.model_validate(r) for r in rows], total_valor

    def create_venda(self, actor: Dict[str, Any], data: VendaCreateRequest) -> str:
        venda_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": venda_id}
        self.repo.create_venda(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="venda", entidade_id=venda_id, dados_antes=None, dados_depois=payload)
        return venda_id

    def list_boletos(
        self, actor: Dict[str, Any], filtros: Dict[str, Any],
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[BoletoResponse]]:
        total, rows = self.repo.list_boletos(filtros=filtros, limit=limit, offset=offset)
        return total, [BoletoResponse.model_validate(r) for r in rows]

    def create_boleto(self, actor: Dict[str, Any], data: BoletoCreateRequest) -> str:
        # TODO: integrar com API AsaaS (preparação)
        boleto_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": boleto_id, "status": "gerado"}
        self.repo.create_boleto(payload)
        return boleto_id

    # ==================== Logística ====================

    def list_pedidos_livros(
        self, actor: Dict[str, Any], filtros: Dict[str, Any],
        limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[PedidoLivroResponse]]:
        total, rows = self.repo.list_pedidos_livros(filtros=filtros, limit=limit, offset=offset)
        return total, [PedidoLivroResponse.model_validate(r) for r in rows]

    def create_pedido_livro(self, actor: Dict[str, Any], data: PedidoLivroCreateRequest) -> str:
        pedido_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": pedido_id, "status": "pendente"}
        self.repo.create_pedido_livro(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="pedido_livro", entidade_id=pedido_id, dados_antes=None, dados_depois=payload)
        return pedido_id

    def update_pedido_livro(self, actor: Dict[str, Any], pedido_id: str, data: PedidoLivroStatusRequest) -> None:
        existente = self.repo.get_pedido_livro(pedido_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pedido id {pedido_id} não encontrado")
        payload = data.model_dump()
        self.repo.update_pedido_livro(pedido_id, payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="update", entidade="pedido_livro", entidade_id=pedido_id, dados_antes=existente, dados_depois={**existente, **payload})

    # ==================== Churn (RN-04) ====================

    def list_churn_alunos(self, actor: Dict[str, Any], limit: int = 50, offset: int = 0) -> Tuple[int, List[AlunoDesistenteResponse]]:
        total, rows = self.repo.list_alunos_churn(limit=limit, offset=offset)
        return total, [AlunoDesistenteResponse.model_validate(r) for r in rows]

    def reativar_aluno_churn(self, actor: Dict[str, Any], aluno_id: str, data: ReingressoRequest) -> str:
        churn = self.repo.get_aluno_churn(aluno_id)
        if not churn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno desistente id {aluno_id} não encontrado")
        if data.pagamento_taxa:
            valor = REINGRESSO_TAXA_REAIS
            descricao = f"Taxa de reingresso R$ {valor:.2f}"
        else:
            valor = None
            descricao = "2 licenças serão cobradas do polo de destino"
        self.repo.update_aluno_churn(aluno_id, {"status": "reativado", "reingresso_em": datetime.now(timezone.utc)})
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="reativar", entidade="aluno_churn", entidade_id=aluno_id, dados_antes=churn, dados_depois={"status": "reativado", "descricao": descricao})
        return descricao

    # ==================== Requisições de Troca ====================

    def list_requisicoes_troca(
        self, actor: Dict[str, Any], status: Optional[str] = None,
        aluno_id: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> Tuple[int, List[RequisicaoTrocaResponse]]:
        total, rows = self.repo.list_requisicoes_troca(status=status, aluno_id=aluno_id, limit=limit, offset=offset)
        return total, [RequisicaoTrocaResponse.model_validate(r) for r in rows]

    def create_requisicao_troca(self, actor: Dict[str, Any], data: RequisicaoTrocaCreateRequest) -> str:
        req_id = str(uuid.uuid4())
        payload = data.model_dump() | {"id": req_id, "status": "pendente"}
        self.repo.create_requisicao_troca(payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="create", entidade="requisicao_troca", entidade_id=req_id, dados_antes=None, dados_depois=payload)
        return req_id

    def processar_requisicao_troca(self, actor: Dict[str, Any], requisicao_id: str, data: RequisicaoTrocaDecisaoRequest) -> None:
        existente = self.repo.get_requisicao_troca(requisicao_id)
        if not existente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Requisição id {requisicao_id} não encontrada")
        payload = data.model_dump() | {"status": "processada"}
        self.repo.update_requisicao_troca(requisicao_id=requisicao_id, data=payload)
        self.repo.record_audit_log(actor_user_id=actor.get("user_id"), acao="processar", entidade="requisicao_troca", entidade_id=requisicao_id, dados_antes=existente, dados_depois=payload)

    # ==================== Configurações / Perfil ====================

    def update_perfil_configuracao(self, actor: Dict[str, Any], data: PerfilMeUpdateRequest) -> UsuarioAdminResponse:
        user_id = actor.get("user_id")
        payload = data.model_dump(exclude_unset=True)
        if payload.get("senha"):
            senha = payload.pop("senha")
            payload["senha_hash"] = hash_password(senha)
        self.repo.update_usuario(user_id, payload)
        usuario = self.repo.get_usuario(user_id)
        if not usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        self.repo.record_audit_log(actor_user_id=user_id, acao="update_perfil", entidade="usuario", entidade_id=user_id, dados_antes=None, dados_depois=payload)
        return UsuarioAdminResponse.model_validate(usuario)
