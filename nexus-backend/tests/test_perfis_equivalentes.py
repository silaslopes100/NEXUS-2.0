"""Testes da equivalência entre os nomes curtos e longos de perfil."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.modules.auth.dependencies import require_role
from app.modules.auth.roles import nomes_equivalentes, perfil_canonico
from app.modules.auth.schemas import PerfilResponse, UserResponse


def _usuario(perfil: str) -> UserResponse:
    return UserResponse(
        id="u-1",
        nome="Teste",
        email="teste@nexus.com.br",
        status="ativo",
        perfil=PerfilResponse(id="p-1", nome=perfil),
    )


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("coordenador_polo", "polo"),
        (" Secretario_Escola ", "escola"),
        ("polo", "polo"),
        ("professor", "professor"),
        ("", ""),
        (None, ""),
    ],
)
def test_perfil_canonico(nome, esperado):
    assert perfil_canonico(nome) == esperado


def test_nomes_equivalentes_comeca_pelo_nome_informado():
    assert nomes_equivalentes("coordenador_polo") == ("coordenador_polo", "polo")
    assert nomes_equivalentes("polo") == ("polo", "coordenador_polo")
    assert nomes_equivalentes("secretario_escola") == ("secretario_escola", "escola")
    assert nomes_equivalentes("professor") == ("professor",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("permitidos", "perfil"),
    [
        (["admin", "polo"], "coordenador_polo"),
        (["admin", "coordenador_polo"], "polo"),
        (["secretario_escola"], "escola"),
        (["escola"], "secretario_escola"),
    ],
)
async def test_require_role_aceita_nomes_equivalentes(permitidos, perfil):
    usuario = _usuario(perfil)
    assert await require_role(permitidos)(current_user=usuario) is usuario


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("permitidos", "perfil"),
    [
        (["admin", "polo"], "escola"),
        (["admin", "polo"], "secretario_escola"),
        (["admin", "coordenador_polo"], "professor"),
        (["admin"], "coordenador_polo"),
    ],
)
async def test_require_role_recusa_outros_papeis(permitidos, perfil):
    with pytest.raises(HTTPException) as erro:
        await require_role(permitidos)(current_user=_usuario(perfil))
    assert erro.value.status_code == 403
