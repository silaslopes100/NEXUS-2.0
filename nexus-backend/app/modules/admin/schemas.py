"""Schemas Pydantic para o módulo administrativo do NEXUS 2.0."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Dashboard Administrativa ----------

class AdminDashboardMetricsResponse(BaseModel):
    alunos_ativos: int
    matriculas_total: int
    polos_ativos: int
    escolas_ativas: int
    professores_ativos: int
    certificados_emitidos: int
    licencas_em_estoque: int


# ---------- Dashboard Executiva (indicadores estratégicos) ----------

class PeriodoResolvido(BaseModel):
    inicio: date
    fim: date


class SerieMensalItem(BaseModel):
    mes: str  # "AAAA-MM"
    novos_alunos: int = 0
    matriculas: int = 0  # matrículas EAD
    desistencias: int = 0


class CrescimentoBloco(BaseModel):
    alunos_ativos: int = 0
    # Alunos cadastrados no NEXUS 2.0 (exclui a carga migrada do legado: legacy_id preenchido).
    novos_alunos: int = 0
    novos_alunos_anterior: int = 0
    variacao_novos_alunos_pct: Optional[float] = None
    # Matrículas EAD (matriculas_ead.data_matricula).
    novas_matriculas: int = 0
    novas_matriculas_anterior: int = 0
    variacao_matriculas_pct: Optional[float] = None
    desistencias: int = 0
    desistencias_anterior: int = 0
    serie_12m: List[SerieMensalItem] = Field(default_factory=list)


class AcademicoBloco(BaseModel):
    presenca_media_pct: Optional[float] = None
    presenca_media_anterior_pct: Optional[float] = None
    registros_presenca: int = 0
    certificados_periodo: int = 0
    certificados_anterior: int = 0


class LicencasBloco(BaseModel):
    estoque_disponivel: int = 0
    consumo_periodo: int = 0
    consumo_anterior: int = 0
    variacao_consumo_pct: Optional[float] = None
    cobertura_dias: Optional[int] = None  # None = sem consumo no período


class PendenciasBloco(BaseModel):
    """Fila atual de trabalho (não depende do período filtrado)."""
    solicitacoes_unidade_pendentes: int = 0
    transferencias_pendentes: int = 0
    pedidos_aguardando_envio: int = 0
    cobrancas_vencidas_qtd: int = 0
    cobrancas_vencidas_valor: float = 0.0
    estagios_em_analise: int = 0
    turmas_atrasadas: int = 0  # RN06: aula prevista até hoje sem ata (nem reposição)


class DashboardExecutivoResponse(BaseModel):
    periodo: PeriodoResolvido
    periodo_anterior: PeriodoResolvido
    crescimento: CrescimentoBloco
    academico: AcademicoBloco
    licencas: LicencasBloco
    pendencias: PendenciasBloco


class RankingPoloItem(BaseModel):
    posicao: int
    polo_id: str
    polo_nome: str
    alunos_ativos: int = 0
    escolas_ativas: int = 0
    novas_licencas: int = 0
    receita_paga: float = 0.0
    presenca_pct: Optional[float] = None


class RankingPolosResponse(BaseModel):
    periodo: PeriodoResolvido
    ordenar_por: str
    items: List[RankingPoloItem]


class MatriculaDashboardItem(BaseModel):
    id: str
    aluno_id: Optional[str] = None
    aluno_nome: str
    numero_matricula: Optional[str] = None
    curso_nome: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    data_matricula: Optional[datetime] = None


class MatriculaDashboardListResponse(BaseModel):
    total: int
    items: List[MatriculaDashboardItem]


class CertificadoDashboardItem(BaseModel):
    id: str
    aluno_id: Optional[str] = None
    aluno_nome: str
    numero_matricula: Optional[str] = None
    curso_nome: Optional[str] = None
    polo_nome: Optional[str] = None
    emitido_em: Optional[datetime] = None
    data_estagio_teologia_ministerio: Optional[date] = None
    data_estagio_homiletica: Optional[date] = None
    url_arquivo: Optional[str] = None


class CertificadoDashboardListResponse(BaseModel):
    total: int
    items: List[CertificadoDashboardItem]


# ---------- Perfis & Permissões ----------

class PerfilItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    descricao: Optional[str] = None


class PermissaoItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chave: str
    descricao: Optional[str] = None


# ---------- Gestão de Usuários ----------

class UsuarioCreateRequest(BaseModel):
    nome: str = Field(min_length=1, description="Nome do usuário")
    sobrenome: Optional[str] = ""
    email: EmailStr
    cpf: Optional[str] = None
    senha: str = Field(min_length=6, description="Senha inicial com no mínimo 6 caracteres")
    perfil_id: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    status: str = Field(default="ativo", pattern="^(ativo|inativo|bloqueado)$")
    permissoes: List[str] = Field(
        default_factory=list,
        description="Lista de chaves de permissões granulares (ex: p_cadastro, p_edicao, p_vendas, etc.)",
    )


class UsuarioUpdateRequest(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    email: Optional[EmailStr] = None
    cpf: Optional[str] = None
    perfil_id: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo|bloqueado)$")
    permissoes: Optional[List[str]] = None


class UsuarioPermissoesUpdateRequest(BaseModel):
    permissoes: List[str] = Field(
        description="Lista completa de permissões granulares que o usuário passará a ter",
    )


class UsuarioSenhaResetRequest(BaseModel):
    nova_senha: str = Field(min_length=6, description="Nova senha com no mínimo 6 caracteres")


class UsuarioAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    sobrenome: Optional[str] = ""
    email: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    foto_url: Optional[str] = None
    status: str = "ativo"
    perfil_id: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    permissoes: List[str] = Field(default_factory=list)
    ultimo_login_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    transferencia_pendente: bool = False


class UsuarioListResponse(BaseModel):
    total: int
    items: List[UsuarioAdminResponse]
    limit: int
    offset: int


# ---------- Ficha Cadastral de Usuário ----------

class AlunoVinculoFicha(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: Optional[str] = None
    numero_matricula: Optional[str] = None
    modalidade: Optional[str] = None
    status: Optional[str] = None
    data_nascimento: Optional[date] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None


class ProfessorVinculoFicha(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: Optional[str] = None
    materias: List[str] = Field(default_factory=list)
    data_inicio: Optional[date] = None
    quantidade_aulas: int = 0
    horas_totais: Optional[float] = None
    valor_hora_aula: Optional[float] = None
    status: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None


class UsuarioFichaResponse(UsuarioAdminResponse):
    aluno: Optional[AlunoVinculoFicha] = None
    professor: Optional[ProfessorVinculoFicha] = None


# ---------- Métricas da Ficha de Usuário ----------

class MetricasAlunoFicha(BaseModel):
    matriculas_total: int = 0
    total_notas: int = 0
    media_notas: Optional[float] = None
    total_presencas: int = 0
    presencas_positivas: int = 0
    percentual_presenca: Optional[float] = None
    certificados_total: int = 0


class MetricasProfessorFicha(BaseModel):
    aulas_registradas: int = 0
    treinamentos_total: int = 0


class MetricasUnidadeFicha(BaseModel):
    escolas: int = 0
    turmas: int = 0
    professores: int = 0
    alunos: int = 0
    aulas: int = 0
    licencas_estoque: int = 0
    licencas_atribuidas: int = 0
    licencas_movimentacoes: int = 0
    pedidos_licencas: int = 0
    pedidos_livros: int = 0


class ConsolidadoAcessoFicha(BaseModel):
    status: str = "ativo"
    perfil_nome: Optional[str] = None
    ultimo_login_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    permissoes: List[str] = Field(default_factory=list)


class ResumoMetricasUsuarioResponse(BaseModel):
    usuario_id: str
    aluno: Optional[MetricasAlunoFicha] = None
    professor: Optional[MetricasProfessorFicha] = None
    unidade: Optional[MetricasUnidadeFicha] = None
    consolidado: ConsolidadoAcessoFicha


# ---------- Logs de Auditoria ----------

class LogAuditoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: Optional[str] = None
    usuario_nome: Optional[str] = None
    usuario_email: Optional[str] = None
    acao: str
    entidade: Optional[str] = None
    entidade_id: Optional[str] = None
    dados_antes: Optional[Dict[str, Any]] = None
    dados_depois: Optional[Dict[str, Any]] = None
    ip: Optional[str] = None
    criado_em: Optional[datetime] = None


class LogAuditoriaListResponse(BaseModel):
    total: int
    items: List[LogAuditoriaResponse]
    limit: int
    offset: int


# ---------- Configurações Gerais ----------

class ConfiguracaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    chave: str
    valor: Any
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class ConfiguracaoSetRequest(BaseModel):
    chave: str
    valor: Any


class ConfiguracaoBulkUpdateRequest(BaseModel):
    configuracoes: Dict[str, Any]


# ---------- ETL / Execuções ----------

class EtlErroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execucao_id: Optional[int] = None
    tabela_origem: Optional[str] = None
    id_origem: Optional[str] = None
    erro: Optional[str] = None
    linha_raw: Optional[Any] = None
    criado_em: Optional[datetime] = None


class EtlSyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    modo: str
    iniciado_em: datetime
    finalizado_em: Optional[datetime] = None
    total_lido: int = 0
    total_inserido: int = 0
    total_atualizado: int = 0
    total_erro: int = 0
    status: str = "rodando"
    duracao_segundos: Optional[float] = None
    total_erros_detalhados: Optional[int] = 0


class EtlSyncRunListResponse(BaseModel):
    total: int
    items: List[EtlSyncRunResponse]
    taxa_sucesso_geral: Optional[float] = None


class MessageResponse(BaseModel):
    message: str
