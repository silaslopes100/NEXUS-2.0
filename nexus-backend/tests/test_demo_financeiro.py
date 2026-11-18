"""Script de dados de demonstração: plano de pedidos e travas de ambiente."""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.config import settings

_spec = importlib.util.spec_from_file_location(
    "demo_financeiro", Path(__file__).resolve().parents[1] / "scripts" / "demo_financeiro.py")
demo = importlib.util.module_from_spec(_spec)
sys.modules["demo_financeiro"] = demo  # dataclasses exigem o módulo registrado
_spec.loader.exec_module(demo)


def test_plano_cobre_todas_as_situacoes_e_datas_no_passado():
    agora = datetime(2026, 11, 17, 12, tzinfo=timezone(timedelta(hours=-3)))
    plano = demo.montar_plano(agora)
    status = Counter(p.status for p in plano)
    assert status["pago_aguardando_envio"] == 4 and status["enviado"] == 3 and status["entregue"] == 5
    assert status["cancelado"] == 1 and status["aguardando_pagamento"] == 7
    assert Counter(p.status_pagamento for p in plano)["vencido"] == 2
    assert any(p.tipo == "licenca" and p.status_pagamento == "pendente" for p in plano)
    assert all(p.criado_em <= agora for p in plano)
    assert all((p.pago_em or agora) <= agora and (p.entregue_em or agora) <= agora for p in plano)
    vencidos = [p for p in plano if p.status_pagamento == "vencido"]
    assert all(p.vencimento < agora for p in vencidos)
    meses = {p.criado_em.strftime("%Y-%m") for p in plano if p.pago_em}
    assert len(meses) >= 4  # receita espalhada para o gráfico de Vendas
    assert all(i["sku"].startswith(demo.PREFIXO_SKU) for p in plano for i in p.itens)


def test_recusa_producao(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_ENV", "producao")
    with pytest.raises(SystemExit):
        demo.verificar_ambiente(False)
    monkeypatch.setattr(settings, "PAYMENT_ENV", "sandbox")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(SystemExit):
        demo.verificar_ambiente(False)
