"""Camada de serviço contendo as regras de negócio de autenticação."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.email import send_password_reset_email
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.repository import AuthRepositoryInterface, get_auth_repository
from app.modules.auth.schemas import (
    LoginResponse,
    PerfilResponse,
    RefreshTokenResponse,
    UserResponse,
)


class AuthService:
    def __init__(self, repo: Optional[AuthRepositoryInterface] = None) -> None:
        self._repo = repo

    @property
    def repo(self) -> AuthRepositoryInterface:
        return self._repo or get_auth_repository()

    def _ensure_utc(self, dt: Any) -> datetime:
        """Garante que o datetime possui fuso horário UTC para comparações seguras."""
        if not isinstance(dt, datetime):
            return dt
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _build_user_response(
        self, user_data: Dict[str, Any], permissoes: List[str]
    ) -> UserResponse:
        perfil = None
        if user_data.get("perfil_nome"):
            perfil = PerfilResponse(
                id=str(user_data.get("perfil_id")) if user_data.get("perfil_id") else None,
                nome=user_data["perfil_nome"],
                descricao=user_data.get("perfil_descricao"),
            )
        return UserResponse(
            id=str(user_data["id"]),
            nome=user_data.get("nome", ""),
            sobrenome=user_data.get("sobrenome", ""),
            email=user_data.get("email"),
            cpf=user_data.get("cpf"),
            telefone=user_data.get("telefone"),
            celular=user_data.get("celular"),
            foto_url=user_data.get("foto_url"),
            status=user_data.get("status", "ativo"),
            perfil=perfil,
            polo_id=str(user_data["polo_id"]) if user_data.get("polo_id") else None,
            escola_id=str(user_data["escola_id"]) if user_data.get("escola_id") else None,
            permissoes=permissoes,
            ultimo_login_em=user_data.get("ultimo_login_em"),
        )

    def login(
        self, email: str, senha: str, client_ip: Optional[str] = None
    ) -> LoginResponse:
        """Efetua login com verificação de bloqueio, lazy rehash de senha legado e geração de JWT."""
        email_clean = email.strip()

        # 1. Checagem de bloqueio por tentativas (5 tentativas incorretas nos últimos 15 min)
        failed_count = self.repo.count_recent_failed_attempts(
            email=email_clean,
            ip=client_ip,
            minutes=settings.LOGIN_ATTEMPTS_WINDOW_MINUTES,
        )
        if failed_count >= settings.MAX_LOGIN_ATTEMPTS:
            self.repo.record_audit_log(
                usuario_id=None,
                acao="login_bloqueado",
                entidade="usuarios",
                dados_depois={"email": email_clean, "motivo": "tentativas_excedidas", "falhas_recentes": failed_count},
                ip=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas incorretas. Conta bloqueada temporariamente por 15 minutos.",
            )

        # 2. Busca o usuário
        user = self.repo.get_user_by_email(email_clean)
        if not user or user.get("status") != "ativo":
            self.repo.record_login_attempt(
                usuario_id=str(user["id"]) if user else None,
                email=email_clean,
                ip=client_ip,
                sucesso=False,
            )
            self.repo.record_audit_log(
                usuario_id=str(user["id"]) if user else None,
                acao="login_falha",
                entidade="usuarios",
                entidade_id=str(user["id"]) if user else None,
                dados_depois={"email": email_clean, "motivo": "usuario_inexistente_ou_inativo"},
                ip=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Validação de senha
        stored_hash = user.get("senha_hash") or ""
        algorithm = user.get("senha_algoritmo") or "legacy_bcrypt"
        valido, precisa_rehash = verify_password(senha, stored_hash, algorithm)

        if not valido:
            self.repo.record_login_attempt(
                usuario_id=str(user["id"]),
                email=email_clean,
                ip=client_ip,
                sucesso=False,
            )
            self.repo.record_audit_log(
                usuario_id=str(user["id"]),
                acao="login_falha",
                entidade="usuarios",
                entidade_id=str(user["id"]),
                dados_depois={"email": email_clean, "motivo": "senha_incorreta"},
                ip=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 4. Lazy rehash para Argon2id se a senha era legacy_bcrypt
        if precisa_rehash or algorithm == "legacy_bcrypt":
            new_argon2_hash = hash_password(senha)
            self.repo.update_user_password(str(user["id"]), new_argon2_hash, "argon2id")
            user["senha_hash"] = new_argon2_hash
            user["senha_algoritmo"] = "argon2id"
            self.repo.record_audit_log(
                usuario_id=str(user["id"]),
                acao="senha_lazy_rehash",
                entidade="usuarios",
                entidade_id=str(user["id"]),
                dados_depois={"algoritmo": "argon2id"},
                ip=client_ip,
            )

        # 5. Registro de sucesso e atualização de login
        self.repo.record_login_attempt(
            usuario_id=str(user["id"]),
            email=email_clean,
            ip=client_ip,
            sucesso=True,
        )
        self.repo.update_user_last_login(str(user["id"]))
        self.repo.record_audit_log(
            usuario_id=str(user["id"]),
            acao="login_sucesso",
            entidade="usuarios",
            entidade_id=str(user["id"]),
            dados_depois={"email": email_clean},
            ip=client_ip,
        )

        # 6. Carrega permissões e monta o usuário
        permissoes = self.repo.get_usuario_permissoes(str(user["id"]))
        user_response = self._build_user_response(user, permissoes)

        # 7. Gera tokens
        token_data = {
            "sub": str(user["id"]),
            "email": user.get("email"),
            "perfil": user.get("perfil_nome"),
            "permissoes": permissoes,
        }
        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        raw_refresh_token = generate_secure_token(48)
        refresh_hash = hash_token(raw_refresh_token)
        refresh_exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.repo.create_refresh_token(
            usuario_id=str(user["id"]),
            token_hash=refresh_hash,
            expira_em=refresh_exp,
            criado_por_ip=client_ip,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            usuario=user_response,
            perfil=user_response.perfil,
            permissoes=permissoes,
        )

    def refresh(
        self, refresh_token_str: str, client_ip: Optional[str] = None
    ) -> RefreshTokenResponse:
        """Valida e rotaciona o refresh token (uso único, revogando o anterior)."""
        token_hash = hash_token(refresh_token_str.strip())
        record = self.repo.get_refresh_token(token_hash)

        if not record or record.get("revogado_em") is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou revogado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        expira_em = self._ensure_utc(record["expira_em"])
        if expira_em < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = str(record["usuario_id"])
        user = self.repo.get_user_by_id(user_id)
        if not user or user.get("status") != "ativo":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo ou inexistente",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 1. Revoga o refresh token atual (uso único)
        self.repo.revoke_refresh_token(token_hash)

        # 2. Gera novo access token
        permissoes = self.repo.get_usuario_permissoes(user_id)
        token_data = {
            "sub": user_id,
            "email": user.get("email"),
            "perfil": user.get("perfil_nome"),
            "permissoes": permissoes,
        }
        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        # 3. Gera novo refresh token (rotação)
        new_raw_refresh = generate_secure_token(48)
        new_refresh_hash = hash_token(new_raw_refresh)
        new_refresh_exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.repo.create_refresh_token(
            usuario_id=user_id,
            token_hash=new_refresh_hash,
            expira_em=new_refresh_exp,
            criado_por_ip=client_ip,
        )

        return RefreshTokenResponse(
            access_token=access_token,
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def logout(
        self,
        refresh_token_str: Optional[str] = None,
        current_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> dict[str, str]:
        """Revoga o refresh token e registra auditoria."""
        user_id_logged = current_user_id
        if refresh_token_str:
            token_hash = hash_token(refresh_token_str.strip())
            token_rec = self.repo.get_refresh_token(token_hash)
            self.repo.revoke_refresh_token(token_hash)
            if not user_id_logged and token_rec:
                user_id_logged = str(token_rec["usuario_id"])

        self.repo.record_audit_log(
            usuario_id=user_id_logged,
            acao="logout",
            entidade="usuarios",
            entidade_id=user_id_logged,
            ip=client_ip,
        )
        return {"message": "Logout realizado com sucesso"}

    def forgot_password(self, email: str, client_ip: Optional[str] = None) -> dict[str, str]:
        """Gera token de recuperação em password_reset e envia e-mail em PT-BR."""
        email_clean = email.strip()
        user = self.repo.get_user_by_email(email_clean)

        if user and user.get("status") == "ativo":
            raw_token = generate_secure_token(32)
            token_hash = hash_token(raw_token)
            expira_em = datetime.now(timezone.utc) + timedelta(
                minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
            )
            self.repo.create_password_reset(
                usuario_id=str(user["id"]),
                token_hash=token_hash,
                expira_em=expira_em,
            )
            send_password_reset_email(
                to_email=user["email"],
                nome=user.get("nome", ""),
                reset_token=raw_token,
            )
            self.repo.record_audit_log(
                usuario_id=str(user["id"]),
                acao="senha_esquecida_solicitada",
                entidade="usuarios",
                entidade_id=str(user["id"]),
                dados_depois={"email": email_clean},
                ip=client_ip,
            )

        # Mensagem genérica para evitar enumeração de usuários
        return {
            "message": "Se o e-mail estiver cadastrado, as instruções para redefinição de senha foram enviadas."
        }

    def reset_password(
        self, token: str, nova_senha: str, client_ip: Optional[str] = None
    ) -> dict[str, str]:
        """Valida token, atualiza senha em Argon2id e registra auditoria."""
        token_hash = hash_token(token.strip())
        record = self.repo.get_password_reset(token_hash)

        if not record or record.get("usado_em") is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de recuperação inválido ou já utilizado",
            )

        expira_em = self._ensure_utc(record["expira_em"])
        if expira_em < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de recuperação expirado",
            )

        if len(nova_senha) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A nova senha deve possuir no mínimo 6 caracteres",
            )

        user_id = str(record["usuario_id"])
        new_argon2_hash = hash_password(nova_senha)

        # 1. Atualiza senha para Argon2id
        self.repo.update_user_password(user_id, new_argon2_hash, "argon2id")

        # 2. Marca o token como utilizado
        self.repo.mark_password_reset_used(token_hash)

        # 3. Revoga refresh tokens ativos por segurança
        self.repo.revoke_all_user_refresh_tokens(user_id)

        # 4. Registra auditoria
        self.repo.record_audit_log(
            usuario_id=user_id,
            acao="senha_redefinida",
            entidade="usuarios",
            entidade_id=user_id,
            dados_depois={"algoritmo": "argon2id"},
            ip=client_ip,
        )

        return {"message": "Senha redefinida com sucesso"}

    def get_me(self, user_id: str) -> UserResponse:
        """Retorna os dados do usuário autenticado + perfil + permissões."""
        user = self.repo.get_user_by_id(str(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        permissoes = self.repo.get_usuario_permissoes(str(user_id))
        return self._build_user_response(user, permissoes)
