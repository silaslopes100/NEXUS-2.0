"""Lógica do fluxo de licenças (RN-02) do módulo `polos_escolas`."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.modules.polos_escolas.repository import PolosEscolasRepositoryInterface
from app.modules.polos_escolas.schemas import (
    LicencaCompraRequest,
    LicencaDevolverAlunoRequest,
    LicencaDevolverEscolaRequest,
    LicencaDistribuirRequest,
    LicencaVenderRequest,
)


def comprar_licencas(
    repo: PolosEscolasRepositoryInterface,
    polo_id: str,
    dados: LicencaCompraRequest,
    actor_id: Optional[str],
) -> Dict[str, Any]:
    """RN-02.1: Fornecedor → Polo. Credita estoque do Polo (status disponivel_polo)."""
    compra_id = repo.registrar_compra(
        {
            "polo_id": polo_id,
            "fornecedor": dados.fornecedor,
            "quantidade": dados.quantidade,
            "valor_unitario": dados.valor_unitario,
            "data_compra": dados.data,
        }
    )
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=dados.quantidade)
    mov_id = repo.registrar_movimentacao(
        {
            "tipo": "compra_fornecedor",
            "polo_id": polo_id,
            "quantidade": dados.quantidade,
            "valor_unitario": dados.valor_unitario,
            "status": "disponivel_polo",
            "actor_id": actor_id,
            "observacao": f"Compra de {dados.quantidade} licenças do fornecedor {dados.fornecedor}",
        }
    )
    return {"compra_id": compra_id, "movimentacao_id": mov_id}


def distribuir_para_escola(
    repo: PolosEscolasRepositoryInterface,
    polo_id: str,
    dados: LicencaDistribuirRequest,
    actor_id: Optional[str],
) -> str:
    """RN-02.2: Polo → Escola. Debita estoque do Polo, credita estoque da Escola."""
    estoque_polo = repo.get_estoque(polo_id=polo_id)
    if dados.quantidade > estoque_polo["quantidade_disponivel"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade solicitada excede o estoque disponível no Polo",
        )
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=-dados.quantidade)
    repo.ajustar_estoque(polo_id=None, escola_id=dados.escola_id, delta_disponivel=dados.quantidade)
    return repo.registrar_movimentacao(
        {
            "tipo": "distribuicao_polo_escola",
            "polo_id": polo_id,
            "escola_id": dados.escola_id,
            "quantidade": dados.quantidade,
            "status": "disponivel_escola",
            "actor_id": actor_id,
            "observacao": f"Distribuição de {dados.quantidade} licenças para a escola",
        }
    )


def vender_para_aluno(
    repo: PolosEscolasRepositoryInterface,
    escola_id: str,
    polo_id: Optional[str],
    dados: LicencaVenderRequest,
    actor_id: Optional[str],
) -> str:
    """RN-02.3: Escola → Aluno. Debita estoque da Escola e vincula ao aluno."""
    estoque_escola = repo.get_estoque(escola_id=escola_id)
    if dados.quantidade > estoque_escola["quantidade_disponivel"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade solicitada excede o estoque disponível na Escola",
        )
    existente = repo.get_licenca_aluno_ativa(dados.aluno_id)
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aluno já possui uma licença ativa",
        )
    repo.ajustar_estoque(polo_id=None, escola_id=escola_id, delta_disponivel=-dados.quantidade, delta_vendida=dados.quantidade)
    mov_id = repo.registrar_movimentacao(
        {
            "tipo": "venda_aluno",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "aluno_id": dados.aluno_id,
            "quantidade": dados.quantidade,
            "status": "vendida_ativa",
            "actor_id": actor_id,
            "observacao": "Venda de licença ao aluno",
        }
    )
    repo.vincular_licenca_aluno(
        {"aluno_id": dados.aluno_id, "escola_id": escola_id, "polo_id": polo_id, "movimentacao_id": mov_id}
    )
    return mov_id


def devolver_de_escola_para_polo(
    repo: PolosEscolasRepositoryInterface,
    escola_id: str,
    polo_id: str,
    dados: LicencaDevolverEscolaRequest,
    actor_id: Optional[str],
) -> str:
    """RN-02.4: Escola → Polo. Debita estoque da Escola, credita estoque do Polo."""
    estoque_escola = repo.get_estoque(escola_id=escola_id)
    if dados.quantidade > estoque_escola["quantidade_disponivel"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade a devolver excede o estoque disponível na Escola",
        )
    repo.ajustar_estoque(polo_id=None, escola_id=escola_id, delta_disponivel=-dados.quantidade)
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=dados.quantidade)
    return repo.registrar_movimentacao(
        {
            "tipo": "devolucao_escola_polo",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "quantidade": dados.quantidade,
            "status": "devolvida_polo",
            "actor_id": actor_id,
            "observacao": f"Devolução de {dados.quantidade} licenças da escola ao polo",
        }
    )


def devolver_de_aluno_para_escola(
    repo: PolosEscolasRepositoryInterface,
    aluno_id: str,
    actor_id: Optional[str],
) -> str:
    """RN-02.5: Aluno → Escola. Remove o vínculo e devolve ao estoque da escola."""
    licenca = repo.get_licenca_aluno_ativa(aluno_id)
    if not licenca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não possui licença ativa para devolver",
        )
    repo.devolver_licenca_aluno(licenca["id"])
    escola_id = licenca.get("escola_id")
    polo_id = licenca.get("polo_id")
    repo.ajustar_estoque(polo_id=None, escola_id=escola_id, delta_disponivel=1, delta_vendida=-1)
    return repo.registrar_movimentacao(
        {
            "tipo": "devolucao_aluno_escola",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "aluno_id": aluno_id,
            "quantidade": 1,
            "status": "disponivel_escola",
            "actor_id": actor_id,
            "observacao": "Devolução da licença do aluno à escola (cancelamento de curso)",
        }
    )
