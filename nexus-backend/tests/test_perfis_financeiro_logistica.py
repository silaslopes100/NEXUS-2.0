"""Opção B: perfis financeiro e logística — o que cada um acessa e o que continua bloqueado."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.financeiro.repository import InMemoryFinanceiroRepository, set_financeiro_repository
from app.modules.polos_escolas.repository import InMemoryPolosEscolasRepository, set_polos_escolas_repository

USUARIOS = {"adm": "admin", "fin": "financeiro", "log": "logistica"}


@pytest_asyncio.fixture
async def client():
    auth = InMemoryAuthRepository()
    for nome in ("admin", "financeiro", "logistica"):
        auth.perfis[f"p-{nome}"] = {"id": f"p-{nome}", "nome": nome, "descricao": nome}
    for uid, perfil in USUARIOS.items():
        auth.usuarios[uid] = {"id": uid, "nome": uid, "email": f"{uid}@nexus.com.br", "status": "ativo",
                              "perfil_id": f"p-{perfil}", "polo_id": None, "escola_id": None}
    set_auth_repository(auth)
    polos = InMemoryPolosEscolasRepository()
    set_polos_escolas_repository(polos)
    set_financeiro_repository(InMemoryFinanceiroRepository())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    set_financeiro_repository(None)
    set_polos_escolas_repository(None)


def _h(uid: str):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("uid", ["fin", "log"])
async def test_leituras_auxiliares_liberadas(client, uid):
    assert (await client.get("/polos", headers=_h(uid))).status_code == 200
    assert (await client.get("/escolas", headers=_h(uid))).status_code == 200
    # filtro por um Polo específico também funciona (escopo global)
    assert (await client.get("/escolas?polo_id=00000000-0000-0000-0000-000000000001", headers=_h(uid))).status_code == 200
    assert (await client.get("/financeiro/pedidos", headers=_h(uid))).status_code == 200


@pytest.mark.asyncio
async def test_financeiro_acessa_area_mas_nao_administra(client):
    h = _h("fin")
    assert (await client.get("/cursos-disciplinas/disciplinas", headers=h)).status_code == 200
    assert (await client.get("/financeiro/vendas/kpis", headers=h)).status_code == 200
    assert (await client.get("/financeiro/regras", headers=h)).status_code == 200
    assert (await client.get("/financeiro/gateways", headers=h)).status_code == 200
    # bloqueios (hierarquia preservada)
    assert (await client.post("/polos", json={"nome": "X"}, headers=h)).status_code == 403
    assert (await client.put("/financeiro/gateways/fake/sandbox", json={"ativo": True}, headers=h)).status_code == 403
    assert (await client.post("/financeiro/pagamentos/x/simular", json={"status": "pago"}, headers=h)).status_code == 403
    assert (await client.post("/financeiro/pedidos/x/envio", json={"transportadora": "Correios"}, headers=h)).status_code == 403
    assert (await client.get("/admin/usuarios", headers=h)).status_code in (401, 403)


@pytest.mark.asyncio
async def test_logistica_so_opera_envio(client):
    h = _h("log")
    # rota da área: passa da permissão (pedido inexistente -> 404, não 403)
    assert (await client.post("/financeiro/pedidos/x/envio", json={"transportadora": "Correios"}, headers=h)).status_code == 404
    assert (await client.get("/financeiro/regras", headers=h)).status_code == 403
    assert (await client.get("/financeiro/vendas/kpis", headers=h)).status_code == 403
    assert (await client.post("/financeiro/pagamentos/x/cancelar", headers=h)).status_code == 403
    assert (await client.get("/cursos-disciplinas/disciplinas", headers=h)).status_code == 403
    assert (await client.post("/polos", json={"nome": "X"}, headers=h)).status_code == 403
    assert (await client.get("/admin/usuarios", headers=h)).status_code in (401, 403)
