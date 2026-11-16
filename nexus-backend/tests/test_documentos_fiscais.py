"""Validação de CPF/CNPJ e dados fiscais do Polo (pagador das cobranças)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.documentos import documento_valido, normalizar_documento
from app.modules.polos_escolas.schemas import DadosFiscaisSchema, PoloUpdateRequest


@pytest.mark.parametrize("doc", ["529.982.247-25", "52998224725", "11.222.333/0001-81", "11222333000181"])
def test_documentos_validos(doc):
    assert documento_valido(doc)


@pytest.mark.parametrize("doc", ["529.982.247-24", "111.111.111-11", "11.222.333/0001-80", "123", "", None])
def test_documentos_invalidos(doc):
    assert not documento_valido(doc)


def test_dados_fiscais_normaliza_e_valida():
    dados = DadosFiscaisSchema(documento_fiscal="11.222.333/0001-81", razao_social="  Polo X LTDA ",
                               email_financeiro="", telefone_financeiro="")
    assert dados.documento_fiscal == "11222333000181"
    assert dados.razao_social == "Polo X LTDA"
    assert dados.email_financeiro is None and dados.telefone_financeiro is None
    with pytest.raises(ValidationError):
        DadosFiscaisSchema(documento_fiscal="000.000.000-00")
    assert normalizar_documento("529.982.247-25") == "52998224725"


def test_polo_update_aceita_dados_fiscais():
    req = PoloUpdateRequest(dados_fiscais={"documento_fiscal": "52998224725", "razao_social": "Fulano"})
    assert req.dados_fiscais.documento_fiscal == "52998224725"
