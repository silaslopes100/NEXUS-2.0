from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.modules.auth.dependencies import require_role
from app.modules.auth.repository import InMemoryAuthRepository
from app.modules.auth.schemas import PerfilResponse, UserResponse
from app.modules.auth.service import AuthService


def _usuario(perfil: str, tambem_aluno: bool) -> UserResponse:
    return UserResponse(
        id="u-1",
        nome="Usuário",
        perfil=PerfilResponse(nome=perfil),
        tambem_aluno=tambem_aluno,
    )


@pytest.mark.parametrize(
    ("perfil", "possui_cadastro", "esperado"),
    [
        ("polo", True, True),
        ("coordenador_polo", True, True),
        ("polo", False, False),
        ("escola", True, True),
        ("secretario_escola", True, True),
        ("escola", False, False),
        ("aluno", True, False),
        ("admin", True, False),
    ],
)
def test_tambem_aluno_exige_perfil_polo_e_cadastro_de_aluno(perfil, possui_cadastro, esperado):
    service = AuthService(repo=InMemoryAuthRepository())

    usuario = service._build_user_response(
        {"id": "u-1", "nome": "Usuário", "perfil_nome": perfil, "possui_cadastro_aluno": possui_cadastro},
        [],
    )

    assert usuario.tambem_aluno is esperado


@pytest.mark.asyncio
async def test_polo_que_tambem_e_aluno_acessa_rotas_de_aluno():
    usuario = _usuario("polo", tambem_aluno=True)

    assert await require_role(["aluno"])(current_user=usuario) is usuario


@pytest.mark.asyncio
async def test_secretario_que_tambem_e_aluno_acessa_apenas_rotas_de_aluno():
    usuario = _usuario("escola", tambem_aluno=True)

    assert await require_role(["aluno"])(current_user=usuario) is usuario
    with pytest.raises(HTTPException) as exc_info:
        await require_role(["admin", "polo"])(current_user=usuario)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_polo_sem_cadastro_de_aluno_nao_acessa_rotas_de_aluno():
    with pytest.raises(HTTPException) as exc_info:
        await require_role(["aluno"])(current_user=_usuario("polo", tambem_aluno=False))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cadastro_de_aluno_nao_libera_outros_perfis():
    with pytest.raises(HTTPException) as exc_info:
        await require_role(["admin", "escola"])(current_user=_usuario("polo", tambem_aluno=True))

    assert exc_info.value.status_code == 403
