"""Lógica do fluxo de licenças (RN-02) do módulo `polos_escolas`.

Fase 3A: o estoque é por disciplina. `disciplina_id=None` representa o saldo
"Sem disciplina" (anterior à migração 020), que o admin pode reclassificar.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.modules.polos_escolas.repository import PolosEscolasRepositoryInterface
from app.modules.polos_escolas.schemas import (
    LicencaCompraRequest,
    LicencaDevolverEscolaRequest,
    LicencaDistribuirRequest,
    LicencaReclassificarRequest,
    LicencaVenderRequest,
)


def _disciplina(valor: Optional[str]) -> Optional[str]:
    return str(valor) if valor else None


def _rotulo(disciplina_id: Optional[str]) -> str:
    return "" if disciplina_id else " (sem disciplina)"


def _saldo(repo: PolosEscolasRepositoryInterface, *, polo_id=None, escola_id=None, disciplina_id=None) -> int:
    return int(repo.get_estoque(polo_id=polo_id, escola_id=escola_id, materia_id=disciplina_id)["quantidade_disponivel"])


def comprar_licencas(
    repo: PolosEscolasRepositoryInterface,
    polo_id: str,
    dados: LicencaCompraRequest,
    actor_id: Optional[str],
) -> Dict[str, Any]:
    """RN-02.1: Fornecedor → Polo. Credita o estoque da disciplina no Polo (status disponivel_polo)."""
    disciplina_id = _disciplina(dados.disciplina_id)
    compra_id = repo.registrar_compra(
        {
            "polo_id": polo_id,
            "fornecedor": dados.fornecedor,
            "quantidade": dados.quantidade,
            "valor_unitario": dados.valor_unitario,
            "data_compra": dados.data,
            "actor_id": actor_id,
            "materia_id": disciplina_id,
        }
    )
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=dados.quantidade, materia_id=disciplina_id)
    mov_id = repo.registrar_movimentacao(
        {
            "tipo": "compra_fornecedor",
            "polo_id": polo_id,
            "materia_id": disciplina_id,
            "quantidade": dados.quantidade,
            "valor_unitario": dados.valor_unitario,
            "status": "disponivel_polo",
            "actor_id": actor_id,
            "observacao": f"Compra de {dados.quantidade} licenças do fornecedor {dados.fornecedor}{_rotulo(disciplina_id)}",
        }
    )
    return {"compra_id": compra_id, "movimentacao_id": mov_id}


def distribuir_para_escola(
    repo: PolosEscolasRepositoryInterface,
    polo_id: str,
    dados: LicencaDistribuirRequest,
    actor_id: Optional[str],
) -> str:
    """RN-02.2: Polo → Escola, na mesma disciplina."""
    disciplina_id = _disciplina(dados.disciplina_id)
    if dados.quantidade > _saldo(repo, polo_id=polo_id, disciplina_id=disciplina_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantidade solicitada excede o estoque disponível no Polo{_rotulo(disciplina_id) or ' nesta disciplina'}",
        )
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=-dados.quantidade, materia_id=disciplina_id)
    repo.ajustar_estoque(polo_id=None, escola_id=dados.escola_id, delta_disponivel=dados.quantidade, materia_id=disciplina_id)
    return repo.registrar_movimentacao(
        {
            "tipo": "distribuicao_polo_escola",
            "polo_id": polo_id,
            "escola_id": dados.escola_id,
            "materia_id": disciplina_id,
            "quantidade": dados.quantidade,
            "status": "disponivel_escola",
            "actor_id": actor_id,
            "observacao": f"Distribuição de {dados.quantidade} licenças para a escola{_rotulo(disciplina_id)}",
        }
    )


def vender_para_aluno(
    repo: PolosEscolasRepositoryInterface,
    escola_id: str,
    polo_id: Optional[str],
    dados: LicencaVenderRequest,
    actor_id: Optional[str],
) -> str:
    """RN-02.3: Escola → Aluno. Uma licença ativa por aluno e disciplina."""
    disciplina_id = _disciplina(dados.disciplina_id)
    if dados.quantidade > _saldo(repo, escola_id=escola_id, disciplina_id=disciplina_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantidade solicitada excede o estoque disponível na Escola{_rotulo(disciplina_id) or ' nesta disciplina'}",
        )
    if repo.get_licenca_aluno_ativa(dados.aluno_id, materia_id=disciplina_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aluno já possui uma licença ativa nesta disciplina",
        )
    repo.ajustar_estoque(polo_id=None, escola_id=escola_id, delta_disponivel=-dados.quantidade,
                         delta_vendida=dados.quantidade, materia_id=disciplina_id)
    mov_id = repo.registrar_movimentacao(
        {
            "tipo": "venda_aluno",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "aluno_id": dados.aluno_id,
            "materia_id": disciplina_id,
            "quantidade": dados.quantidade,
            "status": "vendida_ativa",
            "actor_id": actor_id,
            "observacao": f"Venda de licença ao aluno{_rotulo(disciplina_id)}",
        }
    )
    repo.vincular_licenca_aluno(
        {"aluno_id": dados.aluno_id, "escola_id": escola_id, "polo_id": polo_id,
         "materia_id": disciplina_id, "movimentacao_id": mov_id}
    )
    return mov_id


def devolver_de_escola_para_polo(
    repo: PolosEscolasRepositoryInterface,
    escola_id: str,
    polo_id: str,
    dados: LicencaDevolverEscolaRequest,
    actor_id: Optional[str],
) -> str:
    """RN-02.4: Escola → Polo, na mesma disciplina."""
    disciplina_id = _disciplina(dados.disciplina_id)
    if dados.quantidade > _saldo(repo, escola_id=escola_id, disciplina_id=disciplina_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantidade a devolver excede o estoque disponível na Escola{_rotulo(disciplina_id) or ' nesta disciplina'}",
        )
    repo.ajustar_estoque(polo_id=None, escola_id=escola_id, delta_disponivel=-dados.quantidade, materia_id=disciplina_id)
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=dados.quantidade, materia_id=disciplina_id)
    return repo.registrar_movimentacao(
        {
            "tipo": "devolucao_escola_polo",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "materia_id": disciplina_id,
            "quantidade": dados.quantidade,
            "status": "devolvida_polo",
            "actor_id": actor_id,
            "observacao": f"Devolução de {dados.quantidade} licenças da escola ao polo{_rotulo(disciplina_id)}",
        }
    )


def devolver_de_aluno_para_escola(
    repo: PolosEscolasRepositoryInterface,
    aluno_id: str,
    actor_id: Optional[str],
    licenca_id: Optional[str] = None,
) -> str:
    """RN-02.5: Aluno → Escola. Com mais de uma licença ativa, `licenca_id` é obrigatório."""
    if licenca_id:
        licenca = repo.get_licenca_aluno(licenca_id)
        if not licenca or str(licenca.get("aluno_id")) != str(aluno_id) or licenca.get("status") != "ativa":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Licença ativa não encontrada para este aluno")
    else:
        ativas = repo.list_licencas_aluno_ativas(aluno_id)
        if not ativas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não possui licença ativa para devolver",
            )
        if len(ativas) > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Aluno possui mais de uma licença ativa: informe qual devolver (licenca_id)",
            )
        licenca = ativas[0]
    repo.devolver_licenca_aluno(licenca["id"])
    escola_id = licenca.get("escola_id")
    polo_id = licenca.get("polo_id")
    disciplina_id = _disciplina(licenca.get("materia_id"))
    repo.ajustar_estoque(polo_id=None, escola_id=escola_id, delta_disponivel=1, delta_vendida=-1, materia_id=disciplina_id)
    return repo.registrar_movimentacao(
        {
            "tipo": "devolucao_aluno_escola",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "aluno_id": aluno_id,
            "materia_id": disciplina_id,
            "quantidade": 1,
            "status": "disponivel_escola",
            "actor_id": actor_id,
            "observacao": f"Devolução da licença do aluno à escola (cancelamento de curso){_rotulo(disciplina_id)}",
        }
    )


def reclassificar_saldo_polo(
    repo: PolosEscolasRepositoryInterface,
    polo_id: str,
    dados: LicencaReclassificarRequest,
    actor_id: Optional[str],
) -> str:
    """Admin: move saldo do Polo entre disciplinas (tipicamente do balde "Sem disciplina")."""
    de = _disciplina(dados.de_disciplina_id)
    para = _disciplina(dados.para_disciplina_id)
    if de == para:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Origem e destino da reclassificação devem ser diferentes")
    if dados.quantidade > _saldo(repo, polo_id=polo_id, disciplina_id=de):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Quantidade excede o saldo disponível na origem")
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=-dados.quantidade, materia_id=de)
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=dados.quantidade, materia_id=para)
    return repo.registrar_movimentacao(
        {
            "tipo": "reclassificacao",
            "polo_id": polo_id,
            "materia_id": para,
            "quantidade": dados.quantidade,
            "status": "disponivel_polo",
            "actor_id": actor_id,
            "observacao": f"Reclassificação de {dados.quantidade} licenças "
                          f"de {de or 'Sem disciplina'} para {para or 'Sem disciplina'}",
        }
    )
