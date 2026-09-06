"""Testes automatizados completos do módulo de autenticação NEXUS 2.0."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import bcrypt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.email import sent_emails_history
from app.core.security import hash_password, hash_token
from app.main import app
from app.modules.auth.dependencies import require_permissao, require_role
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from fastapi import APIRouter, Depends


@pytest.fixture
def memory_repo() -> InMemoryAuthRepository:
    repo = InMemoryAuthRepository()

    # Cria usuário com senha Argon2id
    argon_hash = hash_password("senha123")
    repo.usuarios["user-1"] = {
        "id": "user-1",
        "nome": "Carlos",
        "sobrenome": "Silva",
        "email": "carlos@nexus.com.br",
        "cpf": "12345678901",
        "senha_hash": argon_hash,
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-admin",
        "polo_id": None,
        "escola_id": None,
        "telefone": "11999999999",
        "celular": "11988888888",
        "foto_url": None,
        "ultimo_login_em": None,
    }

    # Cria usuário legado com senha Bcrypt
    salt = bcrypt.gensalt()
    bcrypt_hash = bcrypt.hashpw("legado123".encode("utf-8"), salt).decode("utf-8")
    repo.usuarios["user-2"] = {
        "id": "user-2",
        "nome": "Marcos",
        "sobrenome": "Professor",
        "email": "marcos@nexus.com.br",
        "cpf": "98765432100",
        "senha_hash": bcrypt_hash,
        "senha_algoritmo": "legacy_bcrypt",
        "status": "ativo",
        "perfil_id": "p-prof",
        "polo_id": None,
        "escola_id": None,
        "telefone": None,
        "celular": None,
        "foto_url": None,
        "ultimo_login_em": None,
    }

    # Cria usuário Polo com permissão de vendas
    repo.usuarios["user-3"] = {
        "id": "user-3",
        "nome": "Patricia",
        "sobrenome": "Polo",
        "email": "patricia@nexus.com.br",
        "cpf": "11122233344",
        "senha_hash": hash_password("polo123"),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-polo",
        "polo_id": "polo-uuid-1",
        "escola_id": None,
        "telefone": None,
        "celular": None,
        "foto_url": None,
        "ultimo_login_em": None,
    }
    repo.usuario_permissoes.append({"usuario_id": "user-3", "permissao_id": "perm-vendas"})

    # Cria usuário inativo
    repo.usuarios["user-inativo"] = {
        "id": "user-inativo",
        "nome": "Inativo",
        "sobrenome": "Bloqueado",
        "email": "inativo@nexus.com.br",
        "cpf": "00000000000",
        "senha_hash": hash_password("senha123"),
        "senha_algoritmo": "argon2id",
        "status": "inativo",
        "perfil_id": "p-aluno",
        "polo_id": None,
        "escola_id": None,
        "ultimo_login_em": None,
    }

    set_auth_repository(repo)
    sent_emails_history.clear()
    return repo


@pytest_asyncio.fixture
async def client(memory_repo: InMemoryAuthRepository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_login_sucesso_argon2id(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    res = await client.post(
        "/auth/login",
        json={"email": "carlos@nexus.com.br", "senha": "senha123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["usuario"]["email"] == "carlos@nexus.com.br"
    assert data["usuario"]["perfil"]["nome"] == "admin"

    # Valida registro de tentativas e auditoria
    assert len(memory_repo.login_tentativas) == 1
    assert memory_repo.login_tentativas[0]["sucesso"] is True
    assert memory_repo.login_tentativas[0]["email"] == "carlos@nexus.com.br"

    audit_actions = [log["acao"] for log in memory_repo.logs_auditoria]
    assert "login_sucesso" in audit_actions

    # Valida atualização do ultimo_login_em
    assert memory_repo.usuarios["user-1"]["ultimo_login_em"] is not None


@pytest.mark.asyncio
async def test_login_lazy_rehash_legacy_bcrypt(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    # Antes do login: senha_algoritmo é legacy_bcrypt
    assert memory_repo.usuarios["user-2"]["senha_algoritmo"] == "legacy_bcrypt"
    old_hash = memory_repo.usuarios["user-2"]["senha_hash"]

    res = await client.post(
        "/auth/login",
        json={"email": "marcos@nexus.com.br", "senha": "legado123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["usuario"]["email"] == "marcos@nexus.com.br"

    # Após o login: lazy rehash atualizou para argon2id
    updated_user = memory_repo.usuarios["user-2"]
    assert updated_user["senha_algoritmo"] == "argon2id"
    assert updated_user["senha_hash"] != old_hash
    assert updated_user["senha_hash"].startswith("$argon2id$")

    audit_actions = [log["acao"] for log in memory_repo.logs_auditoria]
    assert "senha_lazy_rehash" in audit_actions
    assert "login_sucesso" in audit_actions

    # Novo login com a mesma senha funciona diretamente via Argon2id
    res2 = await client.post(
        "/auth/login",
        json={"email": "marcos@nexus.com.br", "senha": "legado123"},
    )
    assert res2.status_code == 200


@pytest.mark.asyncio
async def test_login_falha_senha_incorreta(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    res = await client.post(
        "/auth/login",
        json={"email": "carlos@nexus.com.br", "senha": "senha_errada"},
    )
    assert res.status_code == 401
    assert "Credenciais inválidas" in res.json()["detail"]

    assert len(memory_repo.login_tentativas) == 1
    assert memory_repo.login_tentativas[0]["sucesso"] is False

    audit_actions = [log["acao"] for log in memory_repo.logs_auditoria]
    assert "login_falha" in audit_actions


@pytest.mark.asyncio
async def test_login_falha_usuario_inativo(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    res = await client.post(
        "/auth/login",
        json={"email": "inativo@nexus.com.br", "senha": "senha123"},
    )
    assert res.status_code == 401
    assert "Credenciais inválidas" in res.json()["detail"]


@pytest.mark.asyncio
async def test_bloqueio_apos_5_tentativas(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    # Simula 5 tentativas falhas consecutivas
    for _ in range(5):
        res = await client.post(
            "/auth/login",
            json={"email": "carlos@nexus.com.br", "senha": "senha_errada"},
        )
        assert res.status_code == 401

    # Na 6ª tentativa (mesmo com a senha correta), deve retornar 429 Bloqueado
    res6 = await client.post(
        "/auth/login",
        json={"email": "carlos@nexus.com.br", "senha": "senha123"},
    )
    assert res6.status_code == 429
    assert "bloqueada temporariamente" in res6.json()["detail"]

    audit_actions = [log["acao"] for log in memory_repo.logs_auditoria]
    assert "login_bloqueado" in audit_actions


@pytest.mark.asyncio
async def test_refresh_token_rotacao_e_uso_unico(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    # 1. Login
    login_res = await client.post(
        "/auth/login",
        json={"email": "carlos@nexus.com.br", "senha": "senha123"},
    )
    assert login_res.status_code == 200
    r_token_1 = login_res.json()["refresh_token"]

    # 2. Refresh com r_token_1
    refresh_res = await client.post(
        "/auth/refresh",
        json={"refresh_token": r_token_1},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    r_token_2 = data["refresh_token"]
    assert "access_token" in data
    assert r_token_2 != r_token_1

    # 3. Tentar usar r_token_1 novamente deve falhar (uso único / revogado)
    reused_res = await client.post(
        "/auth/refresh",
        json={"refresh_token": r_token_1},
    )
    assert reused_res.status_code == 401
    assert "revogado" in reused_res.json()["detail"]

    # 4. Usar r_token_2 deve funcionar perfeitamente
    refresh_res_2 = await client.post(
        "/auth/refresh",
        json={"refresh_token": r_token_2},
    )
    assert refresh_res_2.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token_expirado(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    # Cria token já expirado manualmente no repositório
    expired_token = "token_super_expirado"
    token_hash = hash_token(expired_token)
    memory_repo.refresh_tokens[token_hash] = {
        "id": "r-exp",
        "usuario_id": "user-1",
        "token_hash": token_hash,
        "expira_em": datetime.now(timezone.utc) - timedelta(days=1),
        "revogado_em": None,
        "criado_por_ip": None,
        "criado_em": datetime.now(timezone.utc) - timedelta(days=8),
        "atualizado_em": datetime.now(timezone.utc) - timedelta(days=8),
    }

    res = await client.post(
        "/auth/refresh",
        json={"refresh_token": expired_token},
    )
    assert res.status_code == 401
    assert "expirado" in res.json()["detail"]


@pytest.mark.asyncio
async def test_logout_revoga_refresh_token(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    login_res = await client.post(
        "/auth/login",
        json={"email": "carlos@nexus.com.br", "senha": "senha123"},
    )
    r_token = login_res.json()["refresh_token"]

    # Executa logout
    logout_res = await client.post(
        "/auth/logout",
        json={"refresh_token": r_token},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logout realizado com sucesso"

    # Refresh token foi revogado
    token_hash = hash_token(r_token)
    assert memory_repo.refresh_tokens[token_hash]["revogado_em"] is not None

    # Tentar dar refresh falha
    refresh_res = await client.post(
        "/auth/refresh",
        json={"refresh_token": r_token},
    )
    assert refresh_res.status_code == 401

    audit_actions = [log["acao"] for log in memory_repo.logs_auditoria]
    assert "logout" in audit_actions


@pytest.mark.asyncio
async def test_esqueci_senha_e_redefinir_senha(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    # 1. Solicita recuperação de senha
    res_forgot = await client.post(
        "/auth/esqueci-senha",
        json={"email": "carlos@nexus.com.br"},
    )
    assert res_forgot.status_code == 200

    # Valida envio do e-mail em PT-BR
    assert len(sent_emails_history) == 1
    email = sent_emails_history[0]
    assert email.to == "carlos@nexus.com.br"
    assert "Recuperação de Senha" in email.subject
    assert "Olá, Carlos!" in email.body
    assert "Token:" in email.body

    # Extrai token de recuperação gerado no repositório
    reset_entry = list(memory_repo.password_reset.values())[0]
    token_hash = reset_entry["token_hash"]

    # Localiza o raw_token a partir do corpo do e-mail
    import re
    match = re.search(r"Token:\s*([^\s]+)", email.body)
    assert match is not None
    raw_token = match.group(1)

    # 2. Redefine a senha
    res_reset = await client.post(
        "/auth/redefinir-senha",
        json={"token": raw_token, "nova_senha": "nova_senha_segura_456"},
    )
    assert res_reset.status_code == 200
    assert res_reset.json()["message"] == "Senha redefinida com sucesso"

    # Valida que o token foi marcado como usado
    assert memory_repo.password_reset[token_hash]["usado_em"] is not None

    # 3. Tentar reutilizar o token deve falhar
    res_reused = await client.post(
        "/auth/redefinir-senha",
        json={"token": raw_token, "nova_senha": "outra_senha_789"},
    )
    assert res_reused.status_code == 400
    assert "já utilizado" in res_reused.json()["detail"]

    # 4. Login com senha antiga falha
    res_old = await client.post(
        "/auth/login",
        json={"email": "carlos@nexus.com.br", "senha": "senha123"},
    )
    assert res_old.status_code == 401

    # 5. Login com a nova senha funciona
    res_new = await client.post(
        "/auth/login",
        json={"email": "carlos@nexus.com.br", "senha": "nova_senha_segura_456"},
    )
    assert res_new.status_code == 200


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    # Login como Patricia (Polo com permissão de vendas)
    login_res = await client.post(
        "/auth/login",
        json={"email": "patricia@nexus.com.br", "senha": "polo123"},
    )
    access_token = login_res.json()["access_token"]

    # Chama /auth/me com o Bearer token
    me_res = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == "patricia@nexus.com.br"
    assert data["perfil"]["nome"] == "polo"
    assert "vendas" in data["permissoes"]
    assert data["polo_id"] == "polo-uuid-1"

    # Chamada sem token retorna 401
    unauth_res = await client.get("/auth/me")
    assert unauth_res.status_code == 401


@pytest.mark.asyncio
async def test_dependencias_require_role_e_require_permissao(
    client: AsyncClient, memory_repo: InMemoryAuthRepository
):
    # Cria rotas protegidas de teste usando as dependências reutilizáveis
    test_router = APIRouter(prefix="/test-rbac")

    @test_router.get("/admin-only", dependencies=[Depends(require_role(["admin"]))])
    async def admin_only():
        return {"ok": True}

    @test_router.get("/polo-ou-admin", dependencies=[Depends(require_role(["admin", "polo"]))])
    async def polo_ou_admin():
        return {"ok": True}

    @test_router.get("/vendas-only", dependencies=[Depends(require_permissao("vendas"))])
    async def vendas_only():
        return {"ok": True}

    @test_router.get("/financeiro-only", dependencies=[Depends(require_permissao("financeiro"))])
    async def financeiro_only():
        return {"ok": True}

    app.include_router(test_router)

    # Obter tokens para Admin (carlos) e Polo (patricia)
    admin_login = await client.post(
        "/auth/login", json={"email": "carlos@nexus.com.br", "senha": "senha123"}
    )
    admin_token = admin_login.json()["access_token"]

    polo_login = await client.post(
        "/auth/login", json={"email": "patricia@nexus.com.br", "senha": "polo123"}
    )
    polo_token = polo_login.json()["access_token"]

    # 1. Admin acessa admin-only -> 200
    res = await client.get("/test-rbac/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # 2. Polo acessa admin-only -> 403 Forbidden
    res = await client.get("/test-rbac/admin-only", headers={"Authorization": f"Bearer {polo_token}"})
    assert res.status_code == 403
    assert "não possui autorização" in res.json()["detail"]

    # 3. Polo acessa polo-ou-admin -> 200
    res = await client.get("/test-rbac/polo-ou-admin", headers={"Authorization": f"Bearer {polo_token}"})
    assert res.status_code == 200

    # 4. Polo tem permissão 'vendas' -> 200
    res = await client.get("/test-rbac/vendas-only", headers={"Authorization": f"Bearer {polo_token}"})
    assert res.status_code == 200

    # 5. Polo NÃO tem permissão 'financeiro' -> 403 Forbidden
    res = await client.get("/test-rbac/financeiro-only", headers={"Authorization": f"Bearer {polo_token}"})
    assert res.status_code == 403
    assert "permissão 'financeiro' necessária" in res.json()["detail"] or "não possui a permissão" in res.json()["detail"]

    # 6. Admin tem bypass automático em qualquer require_permissao -> 200
    res = await client.get("/test-rbac/financeiro-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
