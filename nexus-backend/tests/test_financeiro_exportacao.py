"""Fase 4: exportações PDF/XLSX e etiqueta 10×15 (Code128 + declaração de conteúdo)."""
from __future__ import annotations

import re
from datetime import timedelta
from io import BytesIO

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook

from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.security import create_access_token
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.auth.schemas import PerfilResponse, UserResponse
from app.modules.financeiro import exportacao
from app.modules.financeiro.cobranca_service import CobrancaService
from app.modules.financeiro.etiqueta import CODE128_PADROES, code128b_simbolos
from app.modules.financeiro.gateways import fake
from app.modules.financeiro.operacao_service import OperacaoService
from app.modules.financeiro.relatorios import RelatoriosService
from app.modules.financeiro.repository import InMemoryFinanceiroRepository, set_financeiro_repository
from app.modules.financeiro.schemas import CheckoutRequest, EnvioCreate, FiltrosPeriodo, PedidoItemIn, ProdutoCreate
from app.modules.financeiro.service import FinanceiroService

POLO = "polo-a"
FISCAL = {
    "nome": "Polo Alfa", "cep": "01001000", "logradouro": "Praça da Sé", "numero": "1", "bairro": "Sé",
    "cidade": "São Paulo", "uf": "SP", "documento_fiscal": "11222333000181",
    "razao_social": "Polo Alfa LTDA", "email_financeiro": "fin@polo.com.br", "telefone_financeiro": None,
}
REMETENTE = {"nome": "Editora Nexus", "documento": "11222333000181", "logradouro": "Rua A", "numero": "10",
             "bairro": "Centro", "cidade": "Curitiba", "uf": "PR", "cep": "80000000", "telefone": "4133334444"}
ADMIN = UserResponse(id="adm", nome="adm", perfil=PerfilResponse(id="p-admin", nome="admin"))
POLO_USER = UserResponse(id="u-polo", nome="u", perfil=PerfilResponse(id="p-polo", nome="polo"), polo_id=POLO)


def _paginas(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf))


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_SECRETS_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "PAYMENT_ENV", "sandbox")
    fake.resetar()
    yield
    fake.resetar()


@pytest.fixture
def repo():
    r = InMemoryFinanceiroRepository()
    r.polos[POLO] = dict(FISCAL)
    r.salvar_gateway_config("fake", "sandbox", {"webhook_token_cripto": encrypt_secret("t"), "ativo": True, "padrao": True})
    r.regras.append({"id": "padrao", "nome": "Padrão", "meios_permitidos": ["BOLETO", "PIX"], "dias_vencimento": 3,
                     "prioridade": 1000, "ativo": True, "valor_minimo": 0})
    return r


@pytest.fixture
def op(repo):
    return OperacaoService(repo, CobrancaService(repo, creditar_licencas=lambda p, u: None))


@pytest.fixture
def rel(repo, op):
    return RelatoriosService(repo, op)


def _pedido_pago(op, repo, qtd=3, preco=40.0):
    prod = FinanceiroService(repo).create_produto(ProdutoCreate(
        tipo="livro", sku=f"LIV-{len(repo.produtos)}", nome="Matemática Vol. 1 — Ensino Médio", preco=preco, peso_g=250))
    res = op.checkout(CheckoutRequest(tipo="livro", itens=[PedidoItemIn(produto_id=prod.id, quantidade=qtd)], meio="BOLETO"), POLO_USER)
    op.cobranca.simular(res.pagamento.id, "pago", ADMIN)
    return res


# ---------------------------------------------------------------------------
# Code128
# ---------------------------------------------------------------------------

def test_tabela_code128_consistente():
    assert len(CODE128_PADROES) == 107
    assert all(sum(int(d) for d in p) == 11 for p in CODE128_PADROES[:106])
    assert sum(int(d) for d in CODE128_PADROES[106]) == 13
    assert len(set(CODE128_PADROES)) == 107  # sem padrões repetidos


def test_code128_checksum():
    # Conjunto B: valor = ASCII - 32. "PJJ123C": 104 + 48·1 + 42·2 + 42·3 + 17·4 + 18·5 + 19·6 + 35·7 = 879;
    # 879 mod 103 = 55.
    assert code128b_simbolos("PJJ123C")[-2] == 55
    simbolos = code128b_simbolos("PED-2026-000001")
    assert simbolos[0] == 104 and simbolos[-1] == 106


# ---------------------------------------------------------------------------
# Exportações
# ---------------------------------------------------------------------------

def test_exportar_pedidos_pdf_e_xlsx(op, repo, rel):
    res = _pedido_pago(op, repo)
    op.marcar_enviado(res.pedido.id, EnvioCreate(transportadora="Correios", codigo_rastreio="BR123"), ADMIN)

    pdf = rel.pedidos(FiltrosPeriodo(), "pdf", ADMIN)
    assert pdf.body.startswith(b"%PDF") and "pedidos-" in pdf.headers["content-disposition"]

    xlsx = rel.pedidos(FiltrosPeriodo(), "xlsx", ADMIN)
    wb = load_workbook(BytesIO(xlsx.body))
    assert wb.sheetnames == ["Pedidos", "Itens", "Filtros"]
    linha = [c.value for c in wb["Pedidos"][2]]
    assert linha[0] == res.pedido.numero and linha[7] == 120.0 and "BR123" in linha
    assert wb["Itens"]["C2"].value == 3


def test_exportacao_respeita_filtros_e_escopo(op, repo, rel):
    _pedido_pago(op, repo)
    ano_passado = FiltrosPeriodo(ano=2000)
    wb = load_workbook(BytesIO(rel.pedidos(ano_passado, "xlsx", ADMIN).body))
    assert wb["Pedidos"].max_row == 1  # só o cabeçalho
    assert "Ano: 2000" in wb["Filtros"]["B1"].value
    outro_polo = UserResponse(id="x", nome="x", perfil=PerfilResponse(id="p-polo", nome="polo"), polo_id="polo-b")
    wb = load_workbook(BytesIO(rel.pedidos(FiltrosPeriodo(), "xlsx", outro_polo).body))
    assert wb["Pedidos"].max_row == 1


def test_exportar_pagamentos_e_vendas(op, repo, rel):
    _pedido_pago(op, repo, qtd=2, preco=50)
    wb = load_workbook(BytesIO(rel.pagamentos(FiltrosPeriodo(), "xlsx", ADMIN).body))
    assert wb["Por status"]["A2"].value == "pago" and wb["Por status"]["C2"].value == 100.0
    assert rel.pagamentos(FiltrosPeriodo(), "pdf", ADMIN).body.startswith(b"%PDF")

    wb = load_workbook(BytesIO(rel.vendas(FiltrosPeriodo(), "xlsx", ADMIN).body))
    assert wb.sheetnames[:5] == ["Resumo", "Mensal", "Top Polos", "Por status", "Pedidos pagos"]
    assert wb["Pedidos pagos"].max_row == 2
    assert rel.vendas(FiltrosPeriodo(), "pdf", ADMIN).body.startswith(b"%PDF")


def test_limite_de_linhas(op, repo, rel, monkeypatch):
    _pedido_pago(op, repo)
    _pedido_pago(op, repo)
    monkeypatch.setattr(exportacao, "MAX_LINHAS_EXPORT", 1)
    with pytest.raises(HTTPException) as exc:
        rel.pedidos(FiltrosPeriodo(), "pdf", ADMIN)
    assert exc.value.status_code == 422 and "Refine os filtros" in exc.value.detail


# ---------------------------------------------------------------------------
# Etiqueta
# ---------------------------------------------------------------------------

def test_etiqueta_exige_remetente_e_status(op, repo, rel):
    res = _pedido_pago(op, repo)
    with pytest.raises(HTTPException) as exc:
        rel.etiqueta(res.pedido.id, ADMIN)
    assert exc.value.status_code == 409 and "remetente" in exc.value.detail

    repo.configuracoes = {"remetente_etiqueta": REMETENTE}
    prod = FinanceiroService(repo).create_produto(ProdutoCreate(tipo="livro", sku="LIV-X", nome="Livro X", preco=10))
    aguardando = op.checkout(CheckoutRequest(tipo="livro", itens=[PedidoItemIn(produto_id=prod.id, quantidade=1)], meio="PIX"), POLO_USER)
    with pytest.raises(HTTPException) as exc:
        rel.etiqueta(aguardando.pedido.id, ADMIN)
    assert exc.value.status_code == 409


def test_etiqueta_uma_pagina_por_volume_mais_declaracao(op, repo, rel):
    repo.configuracoes = {"remetente_etiqueta": REMETENTE}
    res = _pedido_pago(op, repo)
    pre_envio = rel.etiqueta(res.pedido.id, ADMIN)  # sem envio: 1 volume + declaração
    assert pre_envio.body.startswith(b"%PDF") and _paginas(pre_envio.body) == 2

    op.marcar_enviado(res.pedido.id, EnvioCreate(transportadora="Correios", volumes=3), ADMIN)
    etiqueta = rel.etiqueta(res.pedido.id, ADMIN)
    assert _paginas(etiqueta.body) == 4
    assert "inline" in etiqueta.headers["content-disposition"]
    assert repo.envios[-1]["etiqueta_gerada_em"] is not None


# ---------------------------------------------------------------------------
# API: permissões
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(repo):
    auth = InMemoryAuthRepository()
    for nome in ("financeiro", "logistica"):
        auth.perfis[f"p-{nome}"] = {"id": f"p-{nome}", "nome": nome, "descricao": nome}
    for uid, perfil in {"fin": "p-financeiro", "log": "p-logistica"}.items():
        auth.usuarios[uid] = {"id": uid, "nome": uid, "email": f"{uid}@nexus.com.br", "status": "ativo",
                              "perfil_id": perfil, "polo_id": None, "escola_id": None}
    set_auth_repository(auth)
    set_financeiro_repository(repo)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    set_financeiro_repository(None)


def _h(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


@pytest.mark.asyncio
async def test_api_exportacao_permissoes(client, repo, op):
    repo.configuracoes = {"remetente_etiqueta": REMETENTE}
    res = _pedido_pago(op, repo)
    assert (await client.get("/financeiro/vendas/exportar?formato=pdf", headers=_h("log"))).status_code == 403
    r = await client.get("/financeiro/pedidos/exportar?formato=xlsx&tipo=livro", headers=_h("log"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert (await client.get("/financeiro/pagamentos/exportar?formato=pdf", headers=_h("fin"))).status_code == 200
    assert (await client.get("/financeiro/pedidos/exportar?formato=doc", headers=_h("fin"))).status_code == 422
    assert (await client.get(f"/financeiro/pedidos/{res.pedido.id}/etiqueta", headers=_h("fin"))).status_code == 403
    etiqueta = await client.get(f"/financeiro/pedidos/{res.pedido.id}/etiqueta", headers=_h("log"))
    assert etiqueta.status_code == 200 and etiqueta.content.startswith(b"%PDF")
