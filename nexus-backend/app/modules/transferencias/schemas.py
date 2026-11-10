"""Schemas do módulo de Transferências."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TipoTransferencia = Literal["troca_polo", "polo_para_ead", "ead_para_polo", "reingresso"]


class TransferenciaCreateRequest(BaseModel):
    # Omitido quando o próprio aluno faz a solicitação.
    aluno_id: Optional[uuid.UUID] = None
    tipo: TipoTransferencia
    polo_destino_id: Optional[uuid.UUID] = None
    escola_destino_id: Optional[uuid.UUID] = None
    observacao: Optional[str] = Field(default=None, max_length=1000)


class TransferenciaResolverRequest(BaseModel):
    aprovado: bool
    motivo: Optional[str] = Field(default=None, max_length=1000)
    confirmar_churn: bool = False


class TransferenciaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aluno_id: Optional[str] = None
    aluno_nome: Optional[str] = None
    numero_matricula: Optional[str] = None
    tipo: str
    status: str
    polo_origem_id: Optional[str] = None
    polo_origem_nome: Optional[str] = None
    escola_origem_id: Optional[str] = None
    escola_origem_nome: Optional[str] = None
    polo_destino_id: Optional[str] = None
    polo_destino_nome: Optional[str] = None
    escola_destino_id: Optional[str] = None
    escola_destino_nome: Optional[str] = None
    modalidade_origem: Optional[str] = None
    modalidade_destino: Optional[str] = None
    solicitado_por: Optional[str] = None
    solicitado_por_nome: Optional[str] = None
    observacao: Optional[str] = None
    motivo_rejeicao: Optional[str] = None
    alerta_churn: bool = False
    resolvido_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None


class TransferenciaListResponse(BaseModel):
    total: int
    items: List[TransferenciaResponse]
    limit: int
    offset: int


class PendenciasResumoResponse(BaseModel):
    total: int
    items: List[TransferenciaResponse]


class AlunoElegivelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    numero_matricula: Optional[str] = None
    modalidade: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None


class OpcaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
