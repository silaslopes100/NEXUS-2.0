"""Schemas Pydantic v2 do módulo `polos_escolas` do NEXUS 2.0."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================================================================
# Comuns
# =========================================================================

class MessageResponse(BaseModel):
    message: str


class EnderecoSchema(BaseModel):
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    estado: str = ""
    cep: str = ""


# =========================================================================
# 1. Polos
# =========================================================================

class PoloCreateRequest(BaseModel):
    """Cria o Polo e, na mesma transação, o usuário coordenador (RN-01)."""

    nome: str = Field(min_length=2)
    endereco: Optional[EnderecoSchema] = None
    # Dados do coordenador (RN-01: mesmo cadastro do responsável do polo)
    coordenador_nome: str = Field(min_length=1)
    coordenador_cpf: str = Field(min_length=11, max_length=14)
    coordenador_email: EmailStr
    coordenador_senha: str = Field(min_length=8)


class PoloUpdateRequest(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[EnderecoSchema] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")
    # RN-01: ao editar o Polo, sincroniza dados do coordenador
    coordenador_nome: Optional[str] = None
    coordenador_cpf: Optional[str] = None
    coordenador_email: Optional[EmailStr] = None
    coordenador_senha: Optional[str] = Field(default=None, min_length=8)


class PoloResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    endereco: EnderecoSchema
    status: str = "ativo"
    coordenador_id: Optional[str] = None
    coordenador_nome: Optional[str] = None
    coordenador_email: Optional[str] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class PoloListResponse(BaseModel):
    total: int
    items: List[PoloResponse]
    limit: int
    offset: int


# =========================================================================
# 2. Escolas
# =========================================================================

class EscolaCreateRequest(BaseModel):
    """Cria a Escola e, na mesma transação, o usuário secretário (RN-01)."""

    nome: str = Field(min_length=2)
    endereco: Optional[EnderecoSchema] = None
    secretario_nome: str = Field(min_length=1)
    secretario_cpf: str = Field(min_length=11, max_length=14)
    secretario_email: EmailStr
    secretario_senha: str = Field(min_length=8)


class EscolaUpdateRequest(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[EnderecoSchema] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")
    secretario_nome: Optional[str] = None
    secretario_cpf: Optional[str] = None
    secretario_email: Optional[EmailStr] = None
    secretario_senha: Optional[str] = Field(default=None, min_length=8)


class EscolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    polo_id: str
    nome: str
    endereco: EnderecoSchema
    status: str = "ativo"
    secretario_id: Optional[str] = None
    secretario_nome: Optional[str] = None
    secretario_email: Optional[str] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class EscolaListResponse(BaseModel):
    total: int
    items: List[EscolaResponse]
    limit: int
    offset: int


# =========================================================================
# 3. Dashboard do Polo (RN-03, RN-04)
# =========================================================================

class DashboardPoloKpisResponse(BaseModel):
    total_licencas_compradas: int
    total_licencas_vendidas_alunos: int
    total_licencas_nao_vendidas: int
    total_nao_vendidas_escolas: int
    total_nao_vendidas_polo: int
    taxa_conversao_global: float
    taxa_distribuicao: float


class FunilSerieItem(BaseModel):
    escola_id: Optional[str] = None
    escola_nome: str
    compradas: int = 0
    distribuidas_escolas: int = 0
    vendidas_alunos: int = 0
    nao_vendidas_escolas: int = 0
    nao_vendidas_polo: int = 0


class DashboardFunilResponse(BaseModel):
    polo_id: str
    series: List[FunilSerieItem]


class TreemapNode(BaseModel):
    nome: str
    valor: int
    tipo: str  # 'polo' | 'escola' | 'status'
    filhos: List["TreemapNode"] = Field(default_factory=list)


TreemapNode.model_rebuild()


class DashboardTreemapResponse(BaseModel):
    polo_id: str
    raiz: TreemapNode


class DrilldownAluno(BaseModel):
    nivel: str = "Aluno"
    aluno_id: str
    nome: str
    qtd_comprada: int = 0
    qtd_vendida: int
    qtd_nao_vendida: int = 0
    percentual_ociosidade: float = 0.0


class DrilldownEscola(BaseModel):
    nivel: str = "Escola"
    escola_id: str
    nome: str
    qtd_comprada: int
    qtd_vendida: int
    qtd_nao_vendida: int
    percentual_ociosidade: float
    alunos: List[DrilldownAluno] = Field(default_factory=list)


class DrilldownPolo(BaseModel):
    nivel: str = "Polo"
    polo_id: str
    nome: str
    qtd_comprada: int
    qtd_vendida: int
    qtd_nao_vendida: int
    percentual_ociosidade: float
    escolas: List[DrilldownEscola] = Field(default_factory=list)


class DashboardDrilldownResponse(BaseModel):
    polo: DrilldownPolo


class AlertaResponse(BaseModel):
    nivel: str  # 'vermelho' | 'amarelo' | 'laranja'
    escopo: str  # 'polo' | 'escola'
    referencia_id: str
    referencia_nome: str
    mensagem: str


class AlertaListResponse(BaseModel):
    total: int
    items: List[AlertaResponse]


# =========================================================================
# 4. Relatório Dinâmico Hierárquico
# =========================================================================

class RelatorioDrilldownLinha(BaseModel):
    nivel: str  # 'Polo' | 'Escola' | 'Aluno'
    campo: str
    descricao: str
    formula: str


class RelatorioDrilldownTotais(BaseModel):
    total_vendidas_por_escola: int
    total_nao_vendidas_por_escola: int
    total_nao_vendidas_por_polo: int


class RelatorioDrilldownResponse(BaseModel):
    polo_id: str
    linhas: List[RelatorioDrilldownLinha]
    totais: RelatorioDrilldownTotais


# =========================================================================
# 5. Fluxo de Licenças (RN-02)
# =========================================================================

class LicencaCompraRequest(BaseModel):
    quantidade: int = Field(gt=0)
    fornecedor: str = Field(min_length=1)
    valor_unitario: float = Field(ge=0)
    data: date


class LicencaDistribuirRequest(BaseModel):
    escola_id: str
    quantidade: int = Field(gt=0)


class LicencaVenderRequest(BaseModel):
    aluno_id: str
    quantidade: int = Field(gt=0, le=1)


class LicencaDevolverEscolaRequest(BaseModel):
    quantidade: int = Field(gt=0)


class LicencaDevolverAlunoRequest(BaseModel):
    aluno_id: str


class MovimentacaoLicencaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tipo: str
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    aluno_id: Optional[str] = None
    quantidade: int
    valor_unitario: Optional[float] = None
    status: str
    actor_id: Optional[str] = None
    observacao: Optional[str] = None
    criado_em: Optional[datetime] = None


class MovimentacaoListResponse(BaseModel):
    total: int
    items: List[MovimentacaoLicencaResponse]
    limit: int
    offset: int


# =========================================================================
# 6. Dashboard da Escola
# =========================================================================

class DashboardEscolaKpisResponse(BaseModel):
    licencas_recebidas: int
    licencas_vendidas: int
    licencas_nao_vendidas: int
    taxa_conversao: float
    taxa_ociosidade: float


class DonutResponse(BaseModel):
    vendidas: int
    nao_vendidas: int


class TopAlunoResponse(BaseModel):
    aluno_id: str
    nome: str
    qtd_licencas: int


class AlunoDrilldownEscolaResponse(BaseModel):
    aluno_id: str
    nome: str
    qtd_licencas: int
    data_venda_ativacao: Optional[datetime] = None
    status: str


class AlunoDrilldownEscolaListResponse(BaseModel):
    total: int
    items: List[AlunoDrilldownEscolaResponse]
    limit: int
    offset: int


class EvolucaoMesItem(BaseModel):
    ano: int
    mes: int
    vendidas: int
    distribuidas: int


class EvolucaoResponse(BaseModel):
    escola_id: str
    items: List[EvolucaoMesItem]


# =========================================================================
# 7. Financeiro
# =========================================================================

class CompraLicencaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    polo_id: str
    fornecedor: Optional[str] = None
    quantidade: int
    valor_unitario: Optional[float] = None
    valor_total: Optional[float] = None
    data_compra: date
    boleto_id: Optional[str] = None
    criado_em: Optional[datetime] = None


class CompraLicencaListResponse(BaseModel):
    total: int
    items: List[CompraLicencaResponse]
    limit: int
    offset: int


class BoletoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    polo_id: str
    compra_id: Optional[str] = None
    valor: Optional[float] = None
    status: str
    data_vencimento: Optional[date] = None
    asaas_id: Optional[str] = None
    url_pdf: Optional[str] = None
    criado_em: Optional[datetime] = None


class BoletoListResponse(BaseModel):
    total: int
    items: List[BoletoResponse]
    limit: int
    offset: int


# =========================================================================
# 8. Alunos do Polo
# =========================================================================

class AlunoPoloResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    sobrenome: Optional[str] = ""
    email: Optional[str] = None
    cpf: Optional[str] = None
    escola_id: Optional[str] = None
    modalidade: str = "polo"
    status: str = "ativo"
    quantidade_presencas: int = 0
    percentual_presenca: float = 0.0
    criado_em: Optional[datetime] = None


class AlunoPoloListResponse(BaseModel):
    total: int
    items: List[AlunoPoloResponse]
    limit: int
    offset: int


class AlunoUpdateRequest(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    email: Optional[EmailStr] = None
    escola_id: Optional[str] = None
    modalidade: Optional[str] = Field(default=None, pattern="^(polo|escola|ead)$")
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo|desistente)$")


class NotaCreateRequest(BaseModel):
    materia_id: str
    valor: float = Field(ge=0, le=10)
    descricao: Optional[str] = None


class AlunoCreateRequest(BaseModel):
    nome: str = Field(min_length=1)
    sobrenome: Optional[str] = ""
    cpf: str = Field(min_length=11, max_length=14)
    email: EmailStr
    data_nascimento: date
    escola_id: Optional[str] = None
    modalidade: str = Field(default="polo", pattern="^(polo|escola|ead)$")


class TrocaPoloRequest(BaseModel):
    polo_destino_id: str


class MigracaoModalidadeRequest(BaseModel):
    modalidade_destino: str = Field(pattern="^(polo|escola|ead)$")


class RequisicaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aluno_id: str
    tipo: str
    polo_origem_id: Optional[str] = None
    polo_destino_id: Optional[str] = None
    modalidade_destino: Optional[str] = None
    status: str
    solicitado_por: Optional[str] = None
    criado_em: Optional[datetime] = None


class RequisicaoListResponse(BaseModel):
    total: int
    items: List[RequisicaoResponse]
    limit: int
    offset: int


class AlunoDesistenteResponse(BaseModel):
    aluno_id: str
    nome: str
    polo_id: Optional[str] = None
    ultima_movimentacao_em: Optional[datetime] = None
    dias_sem_movimentacao: int


class AlunoDesistenteListResponse(BaseModel):
    total: int
    items: List[AlunoDesistenteResponse]


# =========================================================================
# 9. Professores
# =========================================================================

class ProfessorDashboardResponse(BaseModel):
    quantidade_aulas: int
    horas_aulas: float


class ProfessorListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: str
    nome: str
    email: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    status: str = "ativo"
    quantidade_aulas: int = 0
    horas_totais: int = 0


class ProfessorListResponse(BaseModel):
    total: int
    items: List[ProfessorListItemResponse]
    limit: int
    offset: int


class ProfessorCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: str
    nome: str
    email: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    materias: List[str] = Field(default_factory=list)
    data_inicio: Optional[date] = None
    quantidade_aulas: int = 0
    horas_totais: int = 0
    valor_hora_aula: Optional[float] = None
    pix: Optional[str] = None
    conteudo_programatico: Optional[str] = None
    status: str = "ativo"


class AnexoAulaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aula_id: str
    nome: str
    url: str
    tipo: Optional[str] = None
    data_aula: Optional[date] = None
    materia_id: Optional[str] = None
    criado_em: Optional[datetime] = None


class AtaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aula_id: str
    professor_id: str
    conteudo: Optional[str] = None
    url_pdf: Optional[str] = None
    criado_em: Optional[datetime] = None


class ChamadaAlunoResponse(BaseModel):
    aluno_id: str
    nome: str
    presencas: int
    total_aulas_previstas: int
    percentual_presenca: float


class ChamadaResponse(BaseModel):
    materia_id: str
    itens: List[ChamadaAlunoResponse]


class ProfessorUpdateRequest(BaseModel):
    perfil: Optional[str] = None
    materias: Optional[List[str]] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    data_inicio: Optional[date] = None
    quantidade_aulas: Optional[int] = None
    horas_totais: Optional[int] = None
    pix: Optional[str] = None
    valor_hora_aula: Optional[float] = None
    conteudo_programatico: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")


class ProfessorCreateRequest(BaseModel):
    nome: str = Field(min_length=1)
    cpf: str = Field(min_length=11, max_length=14)
    email: EmailStr
    senha: str = Field(min_length=8)
    escola_id: Optional[str] = None
    materias: List[str] = Field(default_factory=list)
    data_inicio: Optional[date] = None
    quantidade_aulas: int = 0
    horas_totais: int = 0
    valor_hora_aula: Optional[float] = None
    pix: Optional[str] = None
    conteudo_programatico: Optional[str] = None


# ---------- Gestão Pedagógica (RN-08) ----------

class FeedPostCreateRequest(BaseModel):
    titulo: str = Field(min_length=1)
    conteudo: str = Field(min_length=1)
    tags: List[str] = Field(default_factory=list)
    polo_id: Optional[str] = None


class FeedPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    autor_id: str
    titulo: str
    conteudo: str
    tags: List[str] = Field(default_factory=list)
    polo_id: Optional[str] = None
    criado_em: Optional[datetime] = None


class LembreteCreateRequest(BaseModel):
    titulo: str = Field(min_length=1)
    mensagem: str = Field(min_length=1)
    data_expiracao: Optional[date] = None
    usuario_id: Optional[str] = None


class LembreteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: Optional[str] = None
    titulo: str
    mensagem: str
    data_expiracao: Optional[date] = None
    lido: bool = False
    criado_em: Optional[datetime] = None


class CalendarioEadCreateRequest(BaseModel):
    materia_id: str
    data_liberacao: date
    semestre: int
    ano: int


class CalendarioEadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    materia_id: str
    data_liberacao: date
    semestre: int
    ano: int
    criado_por: Optional[str] = None
    criado_em: Optional[datetime] = None


# =========================================================================
# 10. Treinamentos
# =========================================================================

class TreinamentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    descricao: Optional[str] = None
    url_conteudo: Optional[str] = None
    carga_horaria: Optional[int] = None
    criado_em: Optional[datetime] = None


class TreinamentoInscricaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    treinamento_id: str
    professor_id: str
    status: str = "inscrito"
    concluido_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None


# =========================================================================
# 11. Perfil
# =========================================================================

class PerfilUsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    sobrenome: Optional[str] = ""
    email: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    foto_url: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None


class PerfilUpdateRequest(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None


class PerfilFotoResponse(BaseModel):
    foto_url: str


class PerfilSenhaUpdateRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8)
