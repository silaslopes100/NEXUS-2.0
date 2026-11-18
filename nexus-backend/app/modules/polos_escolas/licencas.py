"""Lógica do fluxo de licenças (RN-02) do módulo `polos_escolas`.

Fase 3A: o estoque é por disciplina. `disciplina_id=None` representa o saldo
"Sem disciplina" (anterior à migração 020), que o admin pode reclassificar.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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


def distribuir_para_alunos(
    repo: PolosEscolasRepositoryInterface,
    polo_id: str,
    disciplina_id: str,
    turma_id: str,
    aluno_ids: List[str],
    actor_id: Optional[str],
) -> Dict[str, Any]:
    """Polo → Alunos de uma turma: 1 licença da disciplina por aluno, com número de acesso.

    Quem já tem licença ativa da disciplina é pulado (não consome saldo).
    """
    turma = repo.get_turma(turma_id)
    if not turma or str(turma.get("polo_id")) != str(polo_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada neste Polo")
    da_turma = {str(a["aluno_id"]): a for a in repo.list_alunos_da_turma(turma_id)}
    fora = [a for a in aluno_ids if str(a) not in da_turma]
    if fora:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"{len(fora)} aluno(s) selecionado(s) não pertencem a esta turma")
    alvos = [str(a) for a in dict.fromkeys(aluno_ids) if not repo.get_licenca_aluno_ativa(a, materia_id=disciplina_id)]
    ja_possuiam = len(dict.fromkeys(aluno_ids)) - len(alvos)
    if not alvos:
        return {"distribuidas": 0, "ja_possuiam": ja_possuiam, "licencas": []}
    if len(alvos) > _saldo(repo, polo_id=polo_id, disciplina_id=disciplina_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saldo insuficiente: {len(alvos)} licença(s) necessária(s) nesta disciplina",
        )
    repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=-len(alvos), materia_id=disciplina_id)
    licencas = []
    for aluno_id in alvos:
        aluno = da_turma[aluno_id]
        mov_id = repo.registrar_movimentacao({
            "tipo": "distribuicao_polo_aluno",
            "polo_id": polo_id,
            "escola_id": aluno.get("escola_id"),
            "aluno_id": aluno_id,
            "materia_id": disciplina_id,
            "quantidade": 1,
            "status": "vendida_ativa",
            "actor_id": actor_id,
            "observacao": f"Licença atribuída pelo Polo (turma {turma.get('nome') or turma_id})",
        })
        licenca_id = repo.vincular_licenca_aluno({
            "aluno_id": aluno_id, "escola_id": aluno.get("escola_id"), "polo_id": polo_id,
            "materia_id": disciplina_id, "movimentacao_id": mov_id,
        })
        licencas.append({
            "licenca_id": licenca_id,
            "aluno_id": aluno_id,
            "aluno_nome": aluno.get("nome"),
            "numero_licenca": repo.get_licenca_aluno(licenca_id)["numero_licenca"],
        })
    return {"distribuidas": len(licencas), "ja_possuiam": ja_possuiam, "licencas": licencas}


def liberar_pelo_admin(
    repo: PolosEscolasRepositoryInterface,
    polo_id: str,
    itens: List[Dict[str, Any]],
    actor_id: Optional[str],
    actor_email: str,
    observacao: Optional[str] = None,
) -> List[str]:
    """Admin → Polo sem cobrança: credita o estoque e registra "Enviada pelo Admin: <email>"."""
    texto = f"Enviada pelo Admin: {actor_email}" + (f" - {observacao.strip()}" if observacao and observacao.strip() else "")
    movimentos = []
    for item in itens:
        disciplina_id = _disciplina(item.get("disciplina_id"))
        quantidade = int(item["quantidade"])
        repo.ajustar_estoque(polo_id=polo_id, escola_id=None, delta_disponivel=quantidade, materia_id=disciplina_id)
        movimentos.append(repo.registrar_movimentacao({
            "tipo": "liberacao_admin",
            "polo_id": polo_id,
            "materia_id": disciplina_id,
            "quantidade": quantidade,
            "valor_unitario": 0,
            "status": "disponivel_polo",
            "actor_id": actor_id,
            "observacao": texto,
        }))
    return movimentos


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
