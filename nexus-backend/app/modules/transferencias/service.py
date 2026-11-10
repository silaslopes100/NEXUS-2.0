"""Regras de negócio de Transferências (RN-05 e RN-06)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.auth.roles import perfil_canonico, perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.transferencias.repository import (
    DIAS_CHURN,
    Decisao,
    EscopoListagem,
    Resolucao,
    SolicitacaoPendenteError,
    TransferenciasRepositoryInterface,
)
from app.modules.transferencias.schemas import (
    AlunoElegivelResponse,
    OpcaoResponse,
    PendenciasResumoResponse,
    TransferenciaCreateRequest,
    TransferenciaListResponse,
    TransferenciaResolverRequest,
    TransferenciaResponse,
)

_TIPOS_COM_DESTINO = ("troca_polo", "ead_para_polo", "reingresso")


@dataclass(frozen=True)
class Ator:
    perfil: str
    usuario_id: str
    polo_id: Optional[str]
    escola_id: Optional[str]


def ator_de(user: UserResponse, escopo: Optional[str] = None) -> Ator:
    """Polo e Escola que também são alunos agem como aluno apenas na própria área."""
    perfil = perfil_do_usuario(user)
    if escopo == "aluno":
        if perfil != "aluno" and not user.tambem_aluno:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário sem cadastro de aluno")
        perfil = "aluno"
    return Ator(perfil=perfil, usuario_id=user.id, polo_id=user.polo_id, escola_id=user.escola_id)


def _erro(codigo: int, detalhe: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=detalhe)


def validar_destino(
    repo: Any, polo_id: Optional[str], escola_id: Optional[str], codigo_erro: int
) -> None:
    """Confirma que Polo e Escola estão ativos e que a Escola pertence ao Polo."""
    polo = repo.get_polo(polo_id) if polo_id else None
    if not polo or polo.get("status") != "ativo":
        raise _erro(codigo_erro, "Polo de destino inválido ou inativo")
    escola = repo.get_escola(escola_id) if escola_id else None
    if not escola or escola.get("status") != "ativo" or str(escola.get("polo_id")) != str(polo_id):
        raise _erro(codigo_erro, "Escola de destino inválida, inativa ou de outro Polo")


def _sem_movimentacao_ha_mais_de_um_ano(referencia: Optional[datetime]) -> bool:
    if referencia is None:
        return False
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - referencia > timedelta(days=DIAS_CHURN)


class TransferenciasService:
    def __init__(self, repo: TransferenciasRepositoryInterface) -> None:
        self.repo = repo

    # ---------- Consultas ----------

    def _escopo_listagem(self, ator: Ator) -> EscopoListagem:
        if ator.perfil in ("admin", "secretario_geral"):
            return EscopoListagem()
        if ator.perfil == "aluno":
            return EscopoListagem(aluno_usuario_id=ator.usuario_id)
        if ator.perfil == "escola" and ator.escola_id:
            return EscopoListagem(escola_id=ator.escola_id, solicitante_id=ator.usuario_id)
        if ator.perfil == "polo" and ator.polo_id:
            return EscopoListagem(polo_id=ator.polo_id, solicitante_id=ator.usuario_id)
        raise _erro(status.HTTP_403_FORBIDDEN, "Usuário sem vínculo com Polo ou Escola")

    def listar(
        self,
        ator: Ator,
        status_filter: Optional[str],
        tipo: Optional[str],
        q: Optional[str],
        limit: int,
        offset: int,
    ) -> TransferenciaListResponse:
        total, itens = self.repo.listar(self._escopo_listagem(ator), status_filter, tipo, q, limit, offset)
        return TransferenciaListResponse(
            total=total,
            items=[TransferenciaResponse.model_validate(item) for item in itens],
            limit=limit,
            offset=offset,
        )

    def resumo_pendentes(self) -> PendenciasResumoResponse:
        total, itens = self.repo.listar(EscopoListagem(), "pendente", None, None, 5, 0)
        return PendenciasResumoResponse(
            total=total, items=[TransferenciaResponse.model_validate(item) for item in itens]
        )

    def meu_cadastro(self, ator: Ator) -> AlunoElegivelResponse:
        aluno = self.repo.get_aluno_por_usuario(ator.usuario_id)
        if not aluno:
            raise _erro(status.HTTP_404_NOT_FOUND, "Cadastro de aluno não encontrado")
        return AlunoElegivelResponse.model_validate(aluno)

    def buscar_alunos(
        self, ator: Ator, q: str, desistentes: bool = False
    ) -> List[AlunoElegivelResponse]:
        escopo = self._escopo_listagem(ator)
        itens = (
            self.repo.buscar_desistentes(q.strip(), 20)
            if desistentes
            else self.repo.buscar_alunos(q.strip(), escopo.polo_id, escopo.escola_id, 20)
        )
        return [AlunoElegivelResponse.model_validate(item) for item in itens]

    def listar_polos(self) -> List[OpcaoResponse]:
        return [OpcaoResponse.model_validate(polo) for polo in self.repo.listar_polos_ativos()]

    def listar_escolas(self, polo_id: str) -> List[OpcaoResponse]:
        return [OpcaoResponse.model_validate(e) for e in self.repo.listar_escolas_ativas(polo_id)]

    # ---------- Solicitação ----------

    def _resolver_aluno(self, ator: Ator, dados: TransferenciaCreateRequest) -> Dict[str, Any]:
        if dados.tipo == "reingresso":
            # Aluno em Churn não tem Polo: quem solicita é a unidade que vai recebê-lo.
            if ator.perfil not in ("polo", "escola"):
                raise _erro(status.HTTP_403_FORBIDDEN, "Reingresso é solicitado pelo Polo ou pela Escola")
            aluno = self.repo.get_aluno(str(dados.aluno_id)) if dados.aluno_id else None
            if not aluno:
                raise _erro(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
            return aluno

        if ator.perfil == "aluno":
            aluno = self.repo.get_aluno_por_usuario(ator.usuario_id)
            if not aluno:
                raise _erro(status.HTTP_404_NOT_FOUND, "Cadastro de aluno não encontrado")
            return aluno

        if not dados.aluno_id:
            raise _erro(status.HTTP_400_BAD_REQUEST, "Informe o aluno da solicitação")
        aluno = self.repo.get_aluno(str(dados.aluno_id))
        if not aluno:
            raise _erro(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")

        escopo = self._escopo_listagem(ator)
        no_escopo = (
            str(aluno.get("modalidade")) == "ead"
            or (bool(escopo.escola_id) and str(aluno.get("escola_id")) == escopo.escola_id)
            or (not escopo.escola_id and str(aluno.get("polo_id")) == escopo.polo_id)
        )
        if not no_escopo:
            raise _erro(status.HTTP_403_FORBIDDEN, "Aluno fora da sua unidade")
        return aluno

    def criar(
        self, ator: Ator, dados: TransferenciaCreateRequest, ip: Optional[str]
    ) -> TransferenciaResponse:
        aluno = self._resolver_aluno(ator, dados)
        reingresso = dados.tipo == "reingresso"
        if reingresso and aluno.get("status") != "desistente":
            raise _erro(status.HTTP_400_BAD_REQUEST, "Reingresso é exclusivo para alunos em Churn")
        if not reingresso and aluno.get("status") != "ativo":
            raise _erro(status.HTTP_400_BAD_REQUEST, "Somente alunos ativos podem solicitar transferência")

        eh_ead = aluno.get("modalidade") == "ead"
        if dados.tipo == "ead_para_polo" and not eh_ead:
            raise _erro(status.HTTP_400_BAD_REQUEST, "Esta migração é exclusiva para alunos EAD")
        if not reingresso and dados.tipo != "ead_para_polo" and eh_ead:
            raise _erro(status.HTTP_400_BAD_REQUEST, "Aluno EAD só pode solicitar migração para Polo")
        if reingresso:
            # As 2 licenças do reingresso são cobradas da unidade que solicita.
            fora_da_unidade = str(dados.polo_destino_id) != ator.polo_id or (
                ator.perfil == "escola" and str(dados.escola_destino_id) != ator.escola_id
            )
            if fora_da_unidade:
                raise _erro(status.HTTP_400_BAD_REQUEST, "O destino do reingresso deve ser a sua unidade")

        polo_destino = None
        escola_destino = None
        if dados.tipo in _TIPOS_COM_DESTINO:
            if not dados.polo_destino_id or not dados.escola_destino_id:
                raise _erro(status.HTTP_400_BAD_REQUEST, "Informe o Polo e a Escola de destino")
            polo_destino = str(dados.polo_destino_id)
            escola_destino = str(dados.escola_destino_id)
            if dados.tipo == "troca_polo" and polo_destino == str(aluno.get("polo_id")):
                raise _erro(status.HTTP_400_BAD_REQUEST, "O Polo de destino deve ser diferente do atual")
            validar_destino(self.repo, polo_destino, escola_destino, status.HTTP_400_BAD_REQUEST)

        modalidade_origem = aluno.get("modalidade")
        modalidade_destino = {
            "troca_polo": modalidade_origem,
            "polo_para_ead": "ead",
            "ead_para_polo": "polo",
            "reingresso": "polo",
        }[dados.tipo]

        observacao = (dados.observacao or "").strip() or None
        try:
            solicitacao_id = self.repo.criar(
                {
                    "aluno_id": str(aluno["id"]),
                    "tipo": dados.tipo,
                    "polo_origem_id": str(aluno["polo_id"]) if aluno.get("polo_id") else None,
                    "polo_destino_id": polo_destino,
                    "escola_origem_id": str(aluno["escola_id"]) if aluno.get("escola_id") else None,
                    "escola_destino_id": escola_destino,
                    "modalidade_origem": modalidade_origem,
                    "modalidade_destino": modalidade_destino,
                    "solicitado_por": ator.usuario_id,
                    "observacao": observacao,
                },
                ip,
            )
        except SolicitacaoPendenteError as exc:
            raise _erro(
                status.HTTP_409_CONFLICT, "O aluno já possui uma solicitação aguardando análise"
            ) from exc

        criada = self.repo.get(solicitacao_id)
        return TransferenciaResponse.model_validate(criada)

    # ---------- Aprovação ----------

    def _decisao(self, solicitacao_id: str, dados: TransferenciaResolverRequest) -> Decisao:
        def decidir(solicitacao: Dict[str, Any], aluno: Optional[Dict[str, Any]]) -> Resolucao:
            if solicitacao.get("status") != "pendente":
                raise _erro(status.HTTP_409_CONFLICT, "Esta solicitação já foi resolvida")

            if not dados.aprovado:
                motivo = (dados.motivo or "").strip() or None
                return Resolucao(
                    status="rejeitada", acao_auditoria="transferencia_rejeitada", motivo_rejeicao=motivo
                )

            if solicitacao["tipo"] == "reingresso":
                raise _erro(
                    status.HTTP_409_CONFLICT,
                    "Reingresso é aprovado ao gerar a nova matrícula na tela de Alunos",
                )

            if not aluno:
                raise _erro(status.HTTP_409_CONFLICT, "O aluno desta solicitação não existe mais")
            if aluno.get("status") != "ativo":
                raise _erro(status.HTTP_409_CONFLICT, "O aluno não está mais ativo")

            # Só o perfil Aluno muda em `usuarios`: em Polo e Escola, esses campos
            # definem a unidade que a pessoa gerencia, não onde ela estuda.
            atualizar_usuario = perfil_canonico(aluno.get("perfil_nome")) == "aluno"

            if _sem_movimentacao_ha_mais_de_um_ano(aluno.get("referencia_movimentacao")):
                if not dados.confirmar_churn:
                    raise _erro(
                        status.HTTP_409_CONFLICT,
                        "Aluno sem movimentação há mais de 1 ano: confirme o envio para o Churn",
                    )
                return Resolucao(
                    status="churn",
                    acao_auditoria="transferencia_churn",
                    aluno_campos={"status": "desistente", "polo_id": None, "escola_id": None},
                    atualizar_usuario=atualizar_usuario,
                    motivo_churn=f"Sem movimentação há mais de 1 ano (solicitação {solicitacao_id})",
                    remover_turmas=True,
                )

            tipo = solicitacao["tipo"]
            if tipo in _TIPOS_COM_DESTINO:
                validar_destino(
                    self.repo,
                    solicitacao.get("polo_destino_id"),
                    solicitacao.get("escola_destino_id"),
                    status.HTTP_409_CONFLICT,
                )
                campos = {
                    "polo_id": solicitacao["polo_destino_id"],
                    "escola_id": solicitacao["escola_destino_id"],
                    "modalidade": solicitacao["modalidade_destino"],
                }
            else:
                campos = {"polo_id": None, "escola_id": None, "modalidade": "ead"}

            return Resolucao(
                status="aprovada",
                acao_auditoria="transferencia_aprovada",
                aluno_campos=campos,
                atualizar_usuario=atualizar_usuario,
                renovar_movimentacao=True,
                remover_turmas=True,
            )

        return decidir

    def resolver(
        self,
        solicitacao_id: str,
        dados: TransferenciaResolverRequest,
        resolvido_por: str,
        ip: Optional[str],
    ) -> TransferenciaResponse:
        resolvida = self.repo.resolver(
            solicitacao_id, self._decisao(solicitacao_id, dados), resolvido_por, ip
        )
        if resolvida is None:
            raise _erro(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada")
        return TransferenciaResponse.model_validate(resolvida)
