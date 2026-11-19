"""Schemas da Central de Estágio."""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Etapa = Literal["teologia_ministerio", "homiletica"]
StatusEstagio = Literal["em_analise", "aprovado", "negado"]
TipoArquivo = Literal["carta", "relatorio", "foto"]
ChaveBase = Literal["manual", "carta_modelo", "relatorio_modelo"]
Situacao = Literal["concluido", "pendente"]

ETAPAS: Dict[str, Dict[str, object]] = {
    "teologia_ministerio": {"titulo": "Teologia do Ministério", "ordem": 1, "descricao": "50 horas iniciais"},
    "homiletica": {"titulo": "Homilética", "ordem": 2, "descricao": "50 horas finais"},
}
ORDEM_ETAPAS = ["teologia_ministerio", "homiletica"]
HORAS_POR_ETAPA = 50
FOTOS_MIN = 5
FOTOS_MAX = 10

STATUS_LABEL = {"em_analise": "Em Análise", "aprovado": "Aprovado", "negado": "Negado"}
BASE_LABEL = {
    "manual": "Manual de Estágio",
    "carta_modelo": "Carta de Apresentação",
    "relatorio_modelo": "Relatório de Estágio",
}


class UploadIn(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    mime: str = Field(min_length=1, max_length=127)
    tamanho: int = Field(gt=0)


class UploadOut(BaseModel):
    modo: Literal["blob", "local"]
    pathname: str
    content_type: str
    token: Optional[str] = None
    upload_url: Optional[str] = None


class ArquivoIn(BaseModel):
    """Metadados de um arquivo já enviado ao armazenamento (upload direto)."""

    url: str = Field(max_length=1000)
    pathname: str = Field(max_length=200)
    nome: str = Field(max_length=255)
    mime: str = Field(max_length=127)
    tamanho: int = Field(gt=0)


class EnvioIn(BaseModel):
    carta: ArquivoIn
    relatorio: ArquivoIn
    fotos: List[ArquivoIn]

    @model_validator(mode="after")
    def _qtd_fotos(self) -> "EnvioIn":
        if not FOTOS_MIN <= len(self.fotos) <= FOTOS_MAX:
            raise ValueError(f"Envie de {FOTOS_MIN} a {FOTOS_MAX} fotos.")
        return self


class AvaliacaoIn(BaseModel):
    status: Literal["aprovado", "negado"]
    comentario: Optional[str] = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _comentario_na_negativa(self) -> "AvaliacaoIn":
        self.comentario = (self.comentario or "").strip() or None
        if self.status == "negado" and (not self.comentario or len(self.comentario) < 3):
            raise ValueError("Escreva o comentário de feedback para negar a solicitação.")
        return self


class ConfigIn(BaseModel):
    video_url: Optional[str] = Field(default=None, max_length=500)


class ArquivoOut(BaseModel):
    id: str
    tipo: TipoArquivo
    nome: str
    mime: str
    tamanho: int
    url: str
    criado_em: Optional[datetime] = None


class EventoOut(BaseModel):
    acao: str
    comentario: Optional[str] = None
    usuario_nome: Optional[str] = None
    criado_em: Optional[datetime] = None


class SubmissaoOut(BaseModel):
    id: str
    etapa: Etapa
    etapa_titulo: str
    status: StatusEstagio
    horas: int = HORAS_POR_ETAPA
    comentario_feedback: Optional[str] = None
    avaliado_em: Optional[datetime] = None
    avaliado_por_nome: Optional[str] = None
    enviado_em: Optional[datetime] = None
    codigo_comprovante: Optional[str] = None
    arquivos: List[ArquivoOut] = Field(default_factory=list)
    eventos: List[EventoOut] = Field(default_factory=list)


class EtapaAlunoOut(BaseModel):
    etapa: Etapa
    titulo: str
    ordem: int
    descricao: str
    horas: int = HORAS_POR_ETAPA
    bloqueada: bool
    pode_enviar: bool
    submissao: Optional[SubmissaoOut] = None


class ArquivoBaseOut(BaseModel):
    chave: ChaveBase
    titulo: str
    nome: Optional[str] = None
    mime: Optional[str] = None
    tamanho: Optional[int] = None
    url: Optional[str] = None
    atualizado_em: Optional[datetime] = None
    disponivel: bool = False


class CentralAlunoOut(BaseModel):
    video_url: Optional[str] = None
    arquivos_base: List[ArquivoBaseOut]
    etapas: List[EtapaAlunoOut]
    horas_cumpridas: int
    horas_totais: int = HORAS_POR_ETAPA * len(ORDEM_ETAPAS)


class ResumoOut(BaseModel):
    pendentes: int


class AlunoResumoOut(BaseModel):
    id: str
    usuario_id: Optional[str] = None
    nome: str
    numero_matricula: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    foto_url: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None


class SubmissaoListaOut(BaseModel):
    id: str
    etapa: Etapa
    etapa_titulo: str
    status: StatusEstagio
    enviado_em: Optional[datetime] = None
    avaliado_em: Optional[datetime] = None
    aluno: AlunoResumoOut
    total_fotos: int = 0
    miniatura_url: Optional[str] = None
    codigo_comprovante: Optional[str] = None


class SubmissoesPage(BaseModel):
    total: int
    itens: List[SubmissaoListaOut]


class SubmissaoDetalheOut(SubmissaoOut):
    aluno: AlunoResumoOut


class FiltrosSubmissoes(BaseModel):
    status: Optional[StatusEstagio] = None
    etapa: Optional[Etapa] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    de: Optional[date] = None
    ate: Optional[date] = None
    busca: Optional[str] = None

    @field_validator("busca")
    @classmethod
    def _busca(cls, v: Optional[str]) -> Optional[str]:
        v = (v or "").strip()
        return v[:100] or None


class FiltrosRelatorio(BaseModel):
    situacao: Optional[Situacao] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    de: Optional[date] = None
    ate: Optional[date] = None


class RelatorioLinhaOut(BaseModel):
    aluno_id: str
    aluno_nome: str
    numero_matricula: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    teologia_status: Optional[StatusEstagio] = None
    teologia_aprovado_em: Optional[datetime] = None
    homiletica_status: Optional[StatusEstagio] = None
    homiletica_aprovado_em: Optional[datetime] = None
    horas_cumpridas: int = 0
    situacao: Situacao


class RelatorioOut(BaseModel):
    total: int
    concluidos: int
    pendentes: int
    linhas: List[RelatorioLinhaOut]
