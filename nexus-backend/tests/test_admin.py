"""Testes automatizados completos do módulo administrativo do NEXUS 2.0."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.admin.repository import InMemoryAdminRepository, set_admin_repository
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository


@pytest.fixture
def repos_setup():
    auth_repo = InMemoryAuthRepository()
    admin_repo = InMemoryAdminRepository()

    # Cria usuário Admin
    admin_hash = hash_password("admin123")
    admin_repo.usuarios["admin-1"] = {
        "id": "admin-1",
        "nome": "Super",
        "sobrenome": "Admin",
        "email": "admin@nexus.com.br",
        "cpf": "11111111111",
        "senha_hash": admin_hash,
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-admin",
        "polo_id": None,
        "escola_id": None,
        "telefone": "11999999999",
        "celular": "11988888888",
        "foto_url": None,
        "ultimo_login_em": None,
        "criado_em": datetime.now(timezone.utc),
        "atualizado_em": datetime.now(timezone.utc),
    }
    # Espelha no auth repo para permitir validação do JWT
    auth_repo.usuarios["admin-1"] = admin_repo.usuarios["admin-1"].copy()

    # Cria usuário Professor (não admin)
    prof_hash = hash_password("prof123")
    admin_repo.usuarios["prof-1"] = {
        "id": "prof-1",
        "nome": "Professor",
        "sobrenome": "Silva",
        "email": "prof@nexus.com.br",
        "cpf": "22222222222",
        "senha_hash": prof_hash,
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-prof",
        "polo_id": None,
        "escola_id": None,
        "telefone": None,
        "celular": None,
        "foto_url": None,
        "ultimo_login_em": None,
        "criado_em": datetime.now(timezone.utc),
        "atualizado_em": datetime.now(timezone.utc),
    }
    auth_repo.usuarios["prof-1"] = admin_repo.usuarios["prof-1"].copy()

    # Popula dados de ETL e Configurações iniciais
    admin_repo.configuracoes["sistema.nome"] = {
        "id": "cfg-1",
        "chave": "sistema.nome",
        "valor": "NEXUS 2.0",
        "criado_em": datetime.now(timezone.utc),
        "atualizado_em": datetime.now(timezone.utc),
    }

    admin_repo.etl_sync_runs.append({
        "id": 1,
        "modo": "full",
        "iniciado_em": datetime.now(timezone.utc) - timedelta(hours=2),
        "finalizado_em": datetime.now(timezone.utc) - timedelta(hours=1),
        "total_lido": 25000,
        "total_inserido": 24980,
        "total_atualizado": 20,
        "total_erro": 0,
        "status": "sucesso",
        "duracao_segundos": 3600.0,
        "total_erros_detalhados": 0,
    })

    admin_repo.etl_sync_runs.append({
        "id": 2,
        "modo": "incremental",
        "iniciado_em": datetime.now(timezone.utc) - timedelta(minutes=30),
        "finalizado_em": datetime.now(timezone.utc) - timedelta(minutes=25),
        "total_lido": 150,
        "total_inserido": 148,
        "total_atualizado": 1,
        "total_erro": 1,
        "status": "sucesso_com_avisos",
        "duracao_segundos": 300.0,
        "total_erros_detalhados": 1,
    })

    admin_repo.etl_erros.append({
        "id": 101,
        "execucao_id": 2,
        "tabela_origem": "users",
        "id_origem": "999",
        "erro": "E-mail duplicado ignorado",
        "linha_raw": {"id": 999, "email": "dup@nexus.com.br"},
        "criado_em": datetime.now(timezone.utc),
    })

    set_auth_repository(auth_repo)
    set_admin_repository(admin_repo)
    return auth_repo, admin_repo


@pytest_asyncio.fixture
async def client(repos_setup):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _get_admin_token() -> str:
    return create_access_token({
        "sub": "admin-1",
        "email": "admin@nexus.com.br",
        "perfil": "admin",
        "permissoes": [],
    })


def _get_prof_token() -> str:
    return create_access_token({
        "sub": "prof-1",
        "email": "prof@nexus.com.br",
        "perfil": "professor",
        "permissoes": [],
    })


# ==========================================
# 1. Controle de Acesso ao Módulo Admin
# ==========================================

@pytest.mark.asyncio
async def test_admin_access_unauthorized_sem_token(client: AsyncClient):
    res = await client.get("/admin/usuarios")
    assert res.status_code == 401
    assert "não informado" in res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_access_forbidden_para_nao_admin(client: AsyncClient):
    prof_token = _get_prof_token()
    res = await client.get("/admin/usuarios", headers={"Authorization": f"Bearer {prof_token}"})
    assert res.status_code == 403
    assert "apenas administradores" in res.json()["detail"]


@pytest.mark.asyncio
async def test_dashboard_metrics_retornam_dados_do_repositorio(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    admin_repo.dashboard_metrics.update({
        "alunos_ativos": 125,
        "matriculas_total": 240,
        "polos_ativos": 8,
        "escolas_ativas": 15,
        "professores_ativos": 12,
        "certificados_emitidos": 4,
        "licencas_em_estoque": 30,
    })

    res = await client.get(
        "/admin/dashboard/metrics",
        headers={"Authorization": f"Bearer {_get_admin_token()}"},
    )

    assert res.status_code == 200
    assert res.json() == {
        "alunos_ativos": 125,
        "matriculas_total": 240,
        "polos_ativos": 8,
        "escolas_ativas": 15,
        "professores_ativos": 12,
        "certificados_emitidos": 4,
        "licencas_em_estoque": 30,
    }


# ==========================================
# 2. CRUD Completo de Usuários Internos / Staff
# ==========================================

@pytest.mark.asyncio
async def test_create_usuario_secretaria_com_permissoes(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    admin_token = _get_admin_token()

    payload = {
        "nome": "Fernanda",
        "sobrenome": "Secretaria",
        "email": "fernanda.sec@nexus.com.br",
        "cpf": "33344455566",
        "senha": "senhaSegura123",
        "perfil_nome": "admin",
        "status": "ativo",
        "permissoes": [
            "p_cadastro",
            "p_edicao",
            "p_matriculas",
            "p_academico",
            "p_chat",
        ],
    }

    res = await client.post(
        "/admin/usuarios",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["nome"] == "Fernanda"
    assert data["email"] == "fernanda.sec@nexus.com.br"
    assert data["perfil_nome"] == "admin"
    assert "p_cadastro" in data["permissoes"]
    assert "p_matriculas" in data["permissoes"]
    assert len(data["permissoes"]) == 5

    # Valida auditoria gravada
    audit = [l for l in admin_repo.logs_auditoria if l["acao"] == "usuario_criado"]
    assert len(audit) == 1
    assert audit[0]["usuario_id"] == "admin-1"
    assert audit[0]["entidade"] == "usuarios"
    assert audit[0]["dados_depois"]["email"] == "fernanda.sec@nexus.com.br"


@pytest.mark.asyncio
async def test_list_and_get_usuarios_com_filtros(client: AsyncClient, repos_setup):
    admin_token = _get_admin_token()

    # Listagem geral
    res = await client.get("/admin/usuarios", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    # Filtro por busca (query)
    res_search = await client.get("/admin/usuarios?q=Super", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["nome"] == "Super"

    # Filtro por perfil
    res_prof = await client.get("/admin/usuarios?perfil=professor", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_prof.status_code == 200
    assert res_prof.json()["total"] == 1
    assert res_prof.json()["items"][0]["email"] == "prof@nexus.com.br"

    # Detalhes por ID
    res_get = await client.get("/admin/usuarios/admin-1", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_get.status_code == 200
    assert res_get.json()["id"] == "admin-1"


@pytest.mark.asyncio
async def test_update_usuario_e_permissoes(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    admin_token = _get_admin_token()

    # Atualiza dados cadastrais
    update_res = await client.put(
        "/admin/usuarios/prof-1",
        json={"nome": "Professor Atualizado", "telefone": "11977776666"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["nome"] == "Professor Atualizado"

    # Atualiza permissões granulares especificamente
    perm_res = await client.put(
        "/admin/usuarios/prof-1/permissoes",
        json={"permissoes": ["p_academico", "p_chat", "p_ranking"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert perm_res.status_code == 200
    assert set(perm_res.json()["permissoes"]) == {"p_academico", "p_chat", "p_ranking"}

    # Valida registros de auditoria com dados_antes e dados_depois
    audit_perms = [l for l in admin_repo.logs_auditoria if l["acao"] == "usuario_permissoes_atualizadas"]
    assert len(audit_perms) >= 1
    assert "p_ranking" in audit_perms[-1]["dados_depois"]["permissoes"]


@pytest.mark.asyncio
async def test_reset_senha_administrativo(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    admin_token = _get_admin_token()

    res = await client.post(
        "/admin/usuarios/prof-1/reset-senha",
        json={"nova_senha": "novaSenhaAdmin2026"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert "redefinida com sucesso" in res.json()["message"]

    # Valida que hash foi atualizado em Argon2id
    prof = admin_repo.usuarios["prof-1"]
    assert prof["senha_hash"].startswith("$argon2id$")

    audit = [l for l in admin_repo.logs_auditoria if l["acao"] == "senha_alterada_admin"]
    assert len(audit) == 1


@pytest.mark.asyncio
async def test_delete_usuario_e_prevencao_auto_exclusao(client: AsyncClient, repos_setup):
    admin_token = _get_admin_token()

    # Tentativa de auto-exclusão do admin logado -> 400 Bad Request
    self_del = await client.delete("/admin/usuarios/admin-1", headers={"Authorization": f"Bearer {admin_token}"})
    assert self_del.status_code == 400
    assert "Não é permitido excluir o próprio usuário" in self_del.json()["detail"]

    # Exclusão de outro usuário -> 200
    del_res = await client.delete("/admin/usuarios/prof-1", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_res.status_code == 200
    assert "excluído com sucesso" in del_res.json()["message"]


# ==========================================
# 3. Perfis e Permissões do Sistema
# ==========================================

@pytest.mark.asyncio
async def test_list_perfis_e_permissoes(client: AsyncClient):
    admin_token = _get_admin_token()

    perfis_res = await client.get("/admin/perfis", headers={"Authorization": f"Bearer {admin_token}"})
    assert perfis_res.status_code == 200
    nomes_perfis = [p["nome"] for p in perfis_res.json()]
    assert "admin" in nomes_perfis
    assert "polo" in nomes_perfis

    perm_res = await client.get("/admin/permissoes", headers={"Authorization": f"Bearer {admin_token}"})
    assert perm_res.status_code == 200
    chaves_perms = [p["chave"] for p in perm_res.json()]
    assert "p_cadastro" in chaves_perms
    assert "p_vendas" in chaves_perms


# ==========================================
# 4. Logs de Auditoria
# ==========================================

@pytest.mark.asyncio
async def test_list_logs_auditoria_com_filtros(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    admin_token = _get_admin_token()

    # Registra alguns logs manuais
    admin_repo.record_audit_log(
        usuario_id="admin-1",
        acao="teste_auditoria_filtro",
        entidade="configuracoes",
        dados_antes={"param": 1},
        dados_depois={"param": 2},
    )

    res = await client.get("/admin/logs-auditoria", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    # Filtro por entidade
    res_ent = await client.get("/admin/logs-auditoria?entidade=configuracoes", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_ent.status_code == 200
    assert res_ent.json()["total"] >= 1


# ==========================================
# 5. Configurações Gerais do Sistema
# ==========================================

@pytest.mark.asyncio
async def test_configuracoes_get_and_put(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    admin_token = _get_admin_token()

    # Lista todas as configurações
    list_res = await client.get("/admin/configuracoes", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    assert any(c["chave"] == "sistema.nome" for c in list_res.json())

    # Atualiza configuração específica via PUT /admin/configuracoes/{chave}
    put_res = await client.put(
        "/admin/configuracoes/sistema.manutencao",
        json={"valor": {"ativo": False, "motivo": ""}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert put_res.status_code == 200
    assert put_res.json()["chave"] == "sistema.manutencao"
    assert put_res.json()["valor"] == {"ativo": False, "motivo": ""}

    # Obtém a configuração atualizada
    get_res = await client.get("/admin/configuracoes/sistema.manutencao", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["valor"]["ativo"] is False

    # Valida auditoria
    audit = [l for l in admin_repo.logs_auditoria if l["acao"] == "configuracao_atualizada"]
    assert len(audit) >= 1
    assert audit[-1]["dados_depois"]["chave"] == "sistema.manutencao"


# ==========================================
# 6. Monitoramento de Execuções do ETL
# ==========================================

@pytest.mark.asyncio
async def test_etl_execucoes_e_erros(client: AsyncClient):
    admin_token = _get_admin_token()

    # Lista execuções
    runs_res = await client.get("/admin/etl/execucoes", headers={"Authorization": f"Bearer {admin_token}"})
    assert runs_res.status_code == 200
    data = runs_res.json()
    assert data["total"] == 2
    assert data["items"][0]["modo"] in ["full", "incremental"]
    assert data["taxa_sucesso_geral"] is not None

    # Detalhes de erros da execução 2
    err_res = await client.get("/admin/etl/execucoes/2/erros", headers={"Authorization": f"Bearer {admin_token}"})
    assert err_res.status_code == 200
    erros = err_res.json()
    assert len(erros) == 1
    assert erros[0]["tabela_origem"] == "users"
    assert "E-mail duplicado" in erros[0]["erro"]


# ==========================================
# 7. Ficha Cadastral & Métricas de Usuário
# ==========================================

def _seed_aluno_com_dados(admin_repo):
    """Cria um usuário aluno com vínculo e dados acadêmicos de exemplo."""
    from datetime import date

    admin_repo.polos["polo-1"] = {"id": "polo-1", "nome": "Polo Centro", "status": "ativo"}
    admin_repo.escolas["esc-1"] = {"id": "esc-1", "polo_id": "polo-1", "nome": "Escola Modelo", "status": "ativo"}

    admin_repo.usuarios["aluno-1"] = {
        "id": "aluno-1",
        "nome": "Maria",
        "sobrenome": "Aluna",
        "email": "maria@nexus.com.br",
        "cpf": "55566677788",
        "senha_hash": "x",
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-aluno",
        "polo_id": "polo-1",
        "escola_id": "esc-1",
        "telefone": None,
        "celular": "11911112222",
        "foto_url": None,
        "ultimo_login_em": None,
        "criado_em": datetime.now(timezone.utc),
        "atualizado_em": datetime.now(timezone.utc),
    }
    admin_repo.alunos["al-1"] = {
        "id": "al-1",
        "usuario_id": "aluno-1",
        "polo_id": "polo-1",
        "escola_id": "esc-1",
        "modalidade": "polo",
        "numero_matricula": "20240001",
        "data_nascimento": date(2000, 5, 20),
        "status": "ativo",
    }
    admin_repo.notas.extend([
        {"aluno_id": "al-1", "valor": 8.5},
        {"aluno_id": "al-1", "valor": 7.0},
    ])
    admin_repo.presencas.extend([
        {"aluno_id": "al-1", "presente": True},
        {"aluno_id": "al-1", "presente": True},
        {"aluno_id": "al-1", "presente": False},
    ])
    admin_repo.matriculas_ead.append({"aluno_id": "al-1", "curso_id": "c-1"})
    admin_repo.certificados.append({"aluno_id": "al-1", "curso_id": "c-1"})
    return admin_repo


@pytest.mark.asyncio
async def test_usuario_ficha_sem_vinculos(client: AsyncClient):
    admin_token = _get_admin_token()
    res = await client.get("/admin/usuarios/admin-1/ficha", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "admin-1"
    assert data["nome"] == "Super"
    assert data["aluno"] is None
    assert data["professor"] is None
    assert data["polo_nome"] is None
    assert data["escola_nome"] is None


@pytest.mark.asyncio
async def test_usuario_ficha_404(client: AsyncClient):
    admin_token = _get_admin_token()
    res = await client.get("/admin/usuarios/nao-existe/ficha", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_usuario_ficha_com_vinculo_aluno(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    _seed_aluno_com_dados(admin_repo)
    admin_token = _get_admin_token()

    res = await client.get("/admin/usuarios/aluno-1/ficha", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["polo_nome"] == "Polo Centro"
    assert data["escola_nome"] == "Escola Modelo"
    assert data["aluno"] is not None
    assert data["aluno"]["id"] == "al-1"
    assert data["aluno"]["numero_matricula"] == "20240001"
    assert data["aluno"]["modalidade"] == "polo"
    assert data["aluno"]["data_nascimento"] == "2000-05-20"
    assert data["professor"] is None


@pytest.mark.asyncio
async def test_usuario_resumo_metricas_aluno(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    _seed_aluno_com_dados(admin_repo)
    admin_token = _get_admin_token()

    res = await client.get("/admin/usuarios/aluno-1/resumo", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["usuario_id"] == "aluno-1"

    aluno = data["aluno"]
    assert aluno is not None
    assert aluno["matriculas_total"] == 1
    assert aluno["total_notas"] == 2
    assert aluno["media_notas"] == 7.75
    assert aluno["total_presencas"] == 3
    assert aluno["presencas_positivas"] == 2
    assert aluno["percentual_presenca"] == 66.7
    assert aluno["certificados_total"] == 1

    # Unidade derivada do polo do usuário
    unidade = data["unidade"]
    assert unidade is not None
    assert unidade["escolas"] == 1
    assert unidade["alunos"] == 1

    assert data["consolidado"]["status"] == "ativo"
    assert data["consolidado"]["perfil_nome"] == "aluno"


@pytest.mark.asyncio
async def test_usuario_ficha_e_resumo_professor(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    admin_repo.professores["prof-db-1"] = {
        "id": "prof-db-1",
        "usuario_id": "prof-1",
        "polo_id": None,
        "escola_id": None,
        "materias": ["Matemática", "Física"],
        "data_inicio": None,
        "quantidade_aulas": 40,
        "horas_totais": 60.0,
        "valor_hora_aula": 85.5,
        "status": "ativo",
    }
    admin_repo.aulas.extend([
        {"professor_id": "prof-db-1", "polo_id": None},
        {"professor_id": "prof-db-1", "polo_id": None},
        {"professor_id": "outro", "polo_id": None},
    ])
    admin_token = _get_admin_token()

    ficha_res = await client.get("/admin/usuarios/prof-1/ficha", headers={"Authorization": f"Bearer {admin_token}"})
    assert ficha_res.status_code == 200
    ficha = ficha_res.json()
    assert ficha["professor"] is not None
    assert ficha["professor"]["materias"] == ["Matemática", "Física"]
    assert ficha["professor"]["quantidade_aulas"] == 40
    assert ficha["aluno"] is None

    resumo_res = await client.get("/admin/usuarios/prof-1/resumo", headers={"Authorization": f"Bearer {admin_token}"})
    assert resumo_res.status_code == 200
    resumo = resumo_res.json()
    assert resumo["professor"] is not None
    assert resumo["professor"]["aulas_registradas"] == 2
    assert resumo["professor"]["treinamentos_total"] == 0
    assert resumo["aluno"] is None
    assert resumo["unidade"] is None


@pytest.mark.asyncio
async def test_list_usuarios_exibe_polo_nome_e_escola_nome(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    _seed_aluno_com_dados(admin_repo)
    admin_token = _get_admin_token()

    res = await client.get("/admin/usuarios?q=maria", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["polo_nome"] == "Polo Centro"
    assert items[0]["escola_nome"] == "Escola Modelo"


@pytest.mark.asyncio
async def test_update_usuario_limpa_vinculo_polo_escola_com_string_vazia(client: AsyncClient, repos_setup):
    _, admin_repo = repos_setup
    _seed_aluno_com_dados(admin_repo)
    admin_token = _get_admin_token()

    res = await client.put(
        "/admin/usuarios/aluno-1",
        json={"polo_id": "", "escola_id": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["polo_id"] is None
    assert data["escola_id"] is None
    assert data["polo_nome"] is None
    assert admin_repo.usuarios["aluno-1"]["polo_id"] is None
    assert admin_repo.usuarios["aluno-1"]["escola_id"] is None
