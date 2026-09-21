"""Schemas Pydantic para o módulo administrativo do NEXUS 2.0.

Contratos completos (Request/Response) da Dashboard Interativa:
Usuários & Staff, Polos/Escolas (RN-01), Cursos/Módulos/Matérias,
Matrículas, EAD, Licenças/Estoque, Aulas/Presenças, Certificados,
Chat, Financeiro, Logística, Alunos (incl. Churn) e Configurações.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    permissoes: List[str] = Field(default_factory=list)
    # RN-01: usuários coordenador_polo/secretario_escola vinculados a polo/escola
    # são "reflexo" do cadastro unificado — exibidos com aviso, nunca como cadastro independente
    gerenciado_via: Optional[str] = None
    aviso_gerenciamento: Optional[str] = None
    ultimo_login_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class UsuarioListResponse(BaseModel):
    total: int
    items: List[UsuarioAdminResponse]
    limit: int
    offset: int


# ---------- Perfil próprio (Configurações -> Gerenciamento de Perfil) ----------

class PerfilMeUpdateRequest(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    foto_url: Optional[str] = None


class PerfilMeSenhaRequest(BaseModel):
    senha_atual: str = Field(min_length=1, description="Senha atual para validação")
    nova_senha: str = Field(min_length=6, description="Nova senha com no mínimo 6 caracteres")


# ---------- Polos (gestão) — RN-01 ----------

class PoloCreateRequest(BaseModel):
    nome: str = Field(min_length=2, description="Nome do polo")
    # RN-01: dados do responsável do polo = dados do coordenador do polo (cadastro unificado)
    responsavel: str = Field(min_length=1, description="Nome do responsável/coordenador do polo")
    cpf: str = Field(min_length=11, max_length=14, description="CPF do responsável/coordenador")
    email: EmailStr = Field(description="E-mail do responsável/coordenador (login)")
    endereco: str = Field(min_length=1, description="Endereço completo do polo")
    senha: str = Field(min_length=6, description="Senha inicial do coordenador (mínimo 6 caracteres)")
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    status: str = Field(default="ativo", pattern="^(ativo|inativo)$")


class PoloUpdateRequest(BaseModel):
    nome: Optional[str] = None
    responsavel: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: Optional[str] = None
    senha: Optional[str] = Field(default=None, min_length=6, description="Se informada, sincroniza a senha do coordenador")
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")


class PoloResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    responsavel: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    # RN-01: vínculo 1:1 com o usuário coordenador criado automaticamente
    usuario_id: Optional[str] = None
    status: str = "ativo"
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class PoloListResponse(BaseModel):
    total: int
    items: List[PoloResponse]
    limit: int
    offset: int


class PoloDetalheResponse(PoloResponse):
    """Card clicável do polo (seção 1.3): detalhes + totais + escolas vinculadas."""
    total_alunos: int = 0
    total_escolas: int = 0
    total_licencas: int = 0
    escolas_vinculadas: List[PoloResponse] = Field(default_factory=list)


# ---------- Escolas (gestão) — RN-01 ----------

class EscolaCreateRequest(BaseModel):
    nome: str = Field(min_length=2, description="Nome da escola")
    polo_id: str = Field(description="Polo ao qual a escola está vinculada")
    # RN-01: dados do responsável da escola = dados do secretário de escola (cadastro unificado)
    responsavel: str = Field(min_length=1, description="Nome do responsável/secretário da escola")
    cpf: str = Field(min_length=11, max_length=14, description="CPF do responsável/secretário")
    email: EmailStr = Field(description="E-mail do responsável/secretário (login)")
    endereco: str = Field(min_length=1, description="Endereço completo da escola")
    senha: str = Field(min_length=6, description="Senha inicial do secretário (mínimo 6 caracteres)")
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    status: str = Field(default="ativo", pattern="^(ativo|inativo)$")


class EscolaUpdateRequest(BaseModel):
    nome: Optional[str] = None
    polo_id: Optional[str] = None
    responsavel: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: Optional[str] = None
    senha: Optional[str] = Field(default=None, min_length=6, description="Se informada, sincroniza a senha do secretário")
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")


class EscolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    polo_id: Optional[str] = None
    nome: str
    responsavel: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    usuario_id: Optional[str] = None
    status: str = "ativo"
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class EscolaListResponse(BaseModel):
    total: int
    items: List[EscolaResponse]
    limit: int
    offset: int


class EscolaDetalheResponse(EscolaResponse):
    """Card clicável da escola (seção 1.4): detalhes + polo vinculado + alunos."""
    polo_nome: Optional[str] = None
    total_alunos: int = 0


# ---------- Cursos e Módulos ----------

class CursoCreateRequest(BaseModel):
    nome: str = Field(min_length=2, description="Nome do curso")
    descricao: Optional[str] = None
    carga_horaria_horas: int = Field(default=0, ge=0, description="Carga horária total em horas")
    grade_curricular: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Grade curricular flexível (JSONB)"
    )
    status: str = Field(default="ativo", pattern="^(ativo|inativo)$")


class CursoUpdateRequest(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    carga_horaria_horas: Optional[int] = Field(default=None, ge=0)
    grade_curricular: Optional[List[Dict[str, Any]]] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")


class CursoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    descricao: Optional[str] = None
    carga_horaria_horas: int = 0
    grade_curricular: Optional[List[Dict[str, Any]]] = None
    status: str = "ativo"
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class CursoListResponse(BaseModel):
    total: int
    items: List[CursoResponse]
    limit: int
    offset: int


class ModuloCreateRequest(BaseModel):
    curso_id: str = Field(description="Curso ao qual o módulo pertence")
    nome: str = Field(min_length=2, description="Nome do módulo")
    ordem: int = Field(default=1, ge=1, description="Ordem de exibição/conclusão")
    conteudo: Optional[str] = None
    carga_horaria_horas: int = Field(default=0, ge=0)


class ModuloUpdateRequest(BaseModel):
    nome: Optional[str] = None
    ordem: Optional[int] = Field(default=None, ge=1)
    conteudo: Optional[str] = None
    carga_horaria_horas: Optional[int] = Field(default=None, ge=0)


class ModuloResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    curso_id: str
    nome: str
    ordem: int = 1
    conteudo: Optional[str] = None
    carga_horaria_horas: int = 0
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class ModuloListResponse(BaseModel):
    total: int
    items: List[ModuloResponse]
    limit: int
    offset: int


class MateriaCreateRequest(BaseModel):
    curso_id: str = Field(description="Curso ao qual a matéria pertence")
    modulo_id: Optional[str] = Field(default=None, description="Módulo ao qual a matéria está vinculada")
    nome: str = Field(min_length=2, description="Nome da matéria")
    ordem: int = Field(default=1, ge=1)
    carga_horaria_horas: int = Field(default=0, ge=0)
    total_aulas_previstas: int = Field(default=0, ge=0, description="RN-07: total de aulas previstas definido por matéria")
    tipo: str = Field(default="disciplina", pattern="^(disciplina|estagio)$", description="'estagio' para Teologia do Ministério / Homilética")
    conteudo: Optional[str] = None
    preco: float = Field(default=45.0, ge=0, description="Preço por matéria EAD (padrão R$ 45,00)")
    status: str = Field(default="ativo", pattern="^(ativo|inativo)$")


class MateriaUpdateRequest(BaseModel):
    modulo_id: Optional[str] = None
    nome: Optional[str] = None
    ordem: Optional[int] = Field(default=None, ge=1)
    carga_horaria_horas: Optional[int] = Field(default=None, ge=0)
    total_aulas_previstas: Optional[int] = Field(default=None, ge=0)
    tipo: Optional[str] = Field(default=None, pattern="^(disciplina|estagio)$")
    conteudo: Optional[str] = None
    preco: Optional[float] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")


class MateriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    curso_id: str
    modulo_id: Optional[str] = None
    nome: str
    ordem: int = 1
    carga_horaria_horas: int = 0
    total_aulas_previstas: int = 0
    tipo: str = "disciplina"
    conteudo: Optional[str] = None
    preco: float = 45.0
    status: str = "ativo"
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class MateriaListResponse(BaseModel):
    total: int
    items: List[MateriaResponse]
    limit: int
    offset: int


# ---------- Matrículas (Dashboard 1.2) ----------

class MatriculaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aluno_id: str
    aluno_nome: Optional[str] = None
    curso_id: Optional[str] = None
    curso_nome: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    modalidade: str = "polo"
    numero_matricula: Optional[str] = None
    semestre: Optional[int] = None
    ano: Optional[int] = None
    status: str = "ativa"
    data_matricula: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class MatriculaListResponse(BaseModel):
    total: int
    items: List[MatriculaResponse]
    limit: int
    offset: int


class MatriculaCreateRequest(BaseModel):
    aluno_id: str
    curso_id: str
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    modalidade: str = Field(default="polo", pattern="^(polo|escola|ead)$")
    numero_matricula: Optional[str] = None
    semestre: Optional[int] = Field(default=None, ge=1, le=3, description="1º, 2º ou 3º semestre")
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)
    status: str = Field(default="ativa", pattern="^(ativa|concluida|desistente|reprovada|trancada)$")


# ---------- Alunos (gestão / cadastro / churn) ----------

class AlunoCreateRequest(BaseModel):
    nome: str = Field(min_length=1, description="Nome do aluno")
    sobrenome: str = Field(min_length=1, description="Sobrenome do aluno")
    cpf: Optional[str] = None
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None
    eh_aluno_polo: bool = Field(default=False, description="É aluno de Polo? (sim/não)")
    polo_id: Optional[str] = Field(default=None, description="Obrigatório se eh_aluno_polo=true")
    pertence_escola: Optional[str] = Field(default=None, description="ID da escola à qual pertence (opcional)")
    eh_aluno_ead: bool = Field(default=False, description="É aluno EAD? (sim/não)")
    curso_id: Optional[str] = Field(default=None, description="Curso da matrícula inicial")
    semestre: Optional[int] = Field(default=None, ge=1, le=3)
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)
    senha: str = Field(min_length=6, description="Senha de acesso (mínimo 6 caracteres)")


class AlunoUpdateRequest(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    modalidade: Optional[str] = Field(default=None, pattern="^(polo|escola|ead)$")
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo|bloqueado|desistente)$")


class AlunoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: str
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    pais: Optional[str] = None
    estado: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    modalidade: str = "polo"
    numero_matricula: Optional[str] = None
    curso_id: Optional[str] = None
    curso_nome: Optional[str] = None
    semestre: Optional[int] = None
    ano: Optional[int] = None
    status: str = "ativo"
    # Colunas obrigatórias (seção 9.1): puxadas da lista de chamada do professor (RN-07)
    quantidade_presencas: int = 0
    percentual_presenca: float = 0.0
    ultima_movimentacao_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class AlunoListResponse(BaseModel):
    total: int
    items: List[AlunoResponse]
    limit: int
    offset: int


class PresencaMateriaItem(BaseModel):
    materia_id: str
    materia_nome: Optional[str] = None
    total_aulas_previstas: int = 0
    presencas: int = 0
    percentual: float = 0.0


class NotaHistoricoItem(BaseModel):
    materia_id: Optional[str] = None
    nome_materia: Optional[str] = None
    nota: Optional[float] = None
    frequencia_pct: Optional[float] = None
    ano: Optional[int] = None
    semestre: Optional[int] = None
    status: Optional[str] = None


class CertificadoResumoItem(BaseModel):
    id: str
    numero_certificado: Optional[str] = None
    data_emissao: Optional[datetime] = None
    status: str = "emitido"


class AlunoDetalheResponse(AlunoResponse):
    """Card clicável do aluno (seção 1.1): perfil + histórico + presenças."""
    perfil_nome: Optional[str] = None
    historico: List[NotaHistoricoItem] = Field(default_factory=list)
    presencas_por_materia: List[PresencaMateriaItem] = Field(default_factory=list)
    certificados: List[CertificadoResumoItem] = Field(default_factory=list)


class NotaCreateRequest(BaseModel):
    aluno_id: str
    materia_id: str
    matricula_id: Optional[str] = None
    nota: float = Field(ge=0, le=10, description="Nota da avaliação (0 a 10)")
    tipo_avaliacao: Optional[str] = Field(default="avaliacao", description="Ex: avaliacao, prova_final, trabalho")
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)
    semestre: Optional[int] = Field(default=None, ge=1, le=3)


class NotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aluno_id: str
    materia_id: str
    matricula_id: Optional[str] = None
    nota: float
    tipo_avaliacao: Optional[str] = None
    ano: Optional[int] = None
    semestre: Optional[int] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class HistoricoListResponse(BaseModel):
    aluno_id: str
    aluno_nome: Optional[str] = None
    items: List[NotaHistoricoItem]


# ---------- Alunos Desistentes (Churn — RN-04) ----------

WHATSAPP_CHURN = "(11) 1936-6880"
POPUP_MENSAGEM_CHURN = (
    "Você já tem cadastro, mas precisa regularizar sua situação, "
    f"entre em contato pelo WhatsApp {WHATSAPP_CHURN}"
)


class AlunoDesistenteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    aluno_id: str
    aluno_nome: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    motivo: Optional[str] = None
    data_marcacao: Optional[datetime] = None
    etiqueta: Optional[str] = Field(default=None, description="Etiqueta 'aluno revalidado' após reingresso")
    taxa_paga: bool = False
    reingresso_em: Optional[datetime] = None
    polo_id: Optional[str] = None
    ultima_movimentacao_em: Optional[datetime] = None
    sugerido_desistencia: bool = False
    popup_mensagem: Optional[str] = None


class AlunoDesistenteListResponse(BaseModel):
    total: int
    items: List[AlunoDesistenteResponse]
    limit: int
    offset: int


class ReingressoRequest(BaseModel):
    """RN-04: reingresso com taxa de R$ 100,00 OU 2 licenças cobradas do polo de destino.

    O aluno revalidado só entra em turmas que comecem do zero.
    """
    pagar_taxa: bool = Field(default=False, description="Pagamento da taxa de matrícula de R$ 100,00")
    usar_licencas_polo: bool = Field(default=False, description="Usar 2 licenças cobradas do polo de destino")
    polo_id: Optional[str] = Field(default=None, description="Polo de destino (obrigatório se usar_licencas_polo)")
    escola_id: Optional[str] = None
    curso_id: str = Field(description="Novo curso (turma que começa do zero)")
    semestre: Optional[int] = Field(default=None, ge=1, le=3)
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)
    observacao: Optional[str] = None


# ---------- Requisições de Troca de Polo / Modalidade ----------

class RequisicaoTrocaCreateRequest(BaseModel):
    aluno_id: str
    tipo: str = Field(pattern="^(troca_polo|migracao_modalidade)$", description="Troca de polo (sem nova matrícula) ou Migração de Modalidade (Polo↔EAD)")
    polo_origem_id: Optional[str] = None
    polo_destino_id: Optional[str] = None
    escola_destino_id: Optional[str] = None
    modalidade_destino: Optional[str] = Field(default=None, pattern="^(polo|escola|ead)$")
    observacao: Optional[str] = None


class RequisicaoTrocaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aluno_id: str
    aluno_nome: Optional[str] = None
    tipo: str
    polo_origem_id: Optional[str] = None
    polo_destino_id: Optional[str] = None
    escola_destino_id: Optional[str] = None
    modalidade_destino: Optional[str] = None
    solicitante_id: Optional[str] = None
    solicitante_nome: Optional[str] = None
    status: str = "pendente"
    observacao: Optional[str] = None
    resolvido_por: Optional[str] = None
    resolvido_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None


class RequisicaoTrocaListResponse(BaseModel):
    total: int
    items: List[RequisicaoTrocaResponse]
    limit: int
    offset: int


class RequisicaoTrocaDecisaoRequest(BaseModel):
    aprovar: bool = Field(description="True para aprovar, False para rejeitar")
    observacao: Optional[str] = None


# ---------- EAD (RN-03) ----------

class MatriculaEadCreateRequest(BaseModel):
    """Matrícula manual EAD: aluno sem vínculo com polo, acesso direto ao AVA.

    Preço por matéria: R$ 45,00 (constante PRECO_MATERIA_EAD no service).
    """
    aluno_id: str = Field(description="Usuário do aluno (sem vínculo com polo)")
    curso_id: str
    pagamento_confirmado: bool = Field(default=True, description="Pagamento da 1ª matéria confirmado (R$ 45,00)")
    semestre: Optional[int] = Field(default=None, ge=1, le=3)
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)


class MatriculaEadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    matricula_id: Optional[str] = None
    aluno_id: str
    aluno_nome: Optional[str] = None
    curso_id: str
    curso_nome: Optional[str] = None
    materia_atual_id: Optional[str] = None
    materia_atual_nome: Optional[str] = None
    progresso_pct: float = 0.0
    ultimo_acesso_em: Optional[datetime] = None
    origem: str = "manual"
    status: str = "ativa"
    materias_liberadas_no_mes: int = 0
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class MatriculaEadListResponse(BaseModel):
    total: int
    items: List[MatriculaEadResponse]
    limit: int
    offset: int


class EadCompraRequest(BaseModel):
    """Compra/liberação de nova matéria EAD (R$ 45,00).

    RN-03: 2 matérias por mês; matéria anterior permanece liberada até a
    abertura da próxima; se não finalizar no prazo, reprova e só libera
    nova matéria com novo pagamento.
    """
    materia_id: str = Field(description="Próxima matéria a liberar (conforme calendário)")
    pagamento_confirmado: bool = Field(default=False, description="Novo pagamento de R$ 45,00 confirmado")
    valor: Optional[float] = Field(default=None, ge=0, description="Valor pago (padrão: preço da matéria)")
    origem: str = Field(default="manual", pattern="^(manual|site)$", description="Origem: manual (admin) ou site oficial www.etadempcom.br")


class EadCalendarioCreateRequest(BaseModel):
    materia_id: str
    ordem: int = Field(default=1, ge=1, description="Ordem da matéria na grade")
    data_liberacao: date = Field(description="Data oficial de liberação da matéria")
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)


class EadCalendarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    materia_id: str
    materia_nome: Optional[str] = None
    ordem: int = 1
    data_liberacao: Optional[date] = None
    ano: Optional[int] = None
    criado_em: Optional[datetime] = None


class EadCalendarioListResponse(BaseModel):
    total: int
    items: List[EadCalendarioResponse]
    limit: int
    offset: int


class EadProgressoRequest(BaseModel):
    progresso_pct: float = Field(ge=0, le=100, description="Progresso na matéria atual (0 a 100)")


class FeedNoticiaCreateRequest(BaseModel):
    titulo: str = Field(min_length=2)
    conteudo: str = Field(min_length=1)
    status: str = Field(default="publicado", pattern="^(publicado|rascunho)$")


class FeedNoticiaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    conteudo: str
    autor_id: Optional[str] = None
    autor_nome: Optional[str] = None
    autor_perfil: Optional[str] = None
    status: str = "publicado"
    criado_em: Optional[datetime] = None


class FeedNoticiaListResponse(BaseModel):
    total: int
    items: List[FeedNoticiaResponse]
    limit: int
    offset: int


class LembreteCreateRequest(BaseModel):
    titulo: str = Field(min_length=2)
    mensagem: str = Field(min_length=1)
    tipo: str = Field(default="popup", pattern="^(popup|email)$")
    data_exibicao: Optional[date] = None
    destino_perfil: Optional[str] = None
    materia_id: Optional[str] = None


class LembreteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    mensagem: str
    tipo: str = "popup"
    data_exibicao: Optional[date] = None
    destino_perfil: Optional[str] = None
    materia_id: Optional[str] = None
    criado_em: Optional[datetime] = None


class LembreteListResponse(BaseModel):
    total: int
    items: List[LembreteResponse]
    limit: int
    offset: int


# ---------- Licenças / Estoque ----------

class LicencaEstoqueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    materia_id: str
    materia_nome: Optional[str] = None
    tipo: str = Field(default="licenca", pattern="^(licenca|livro)$")
    quantidade: int = 0
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class LicencaEstoqueListResponse(BaseModel):
    total: int
    items: List[LicencaEstoqueResponse]
    limit: int
    offset: int


class AjusteEstoqueRequest(BaseModel):
    """Edição manual do estoque pelo Secretário (adição/subtração) com auditoria."""
    materia_id: str
    tipo: str = Field(default="licenca", pattern="^(licenca|livro)$")
    tipo_movimento: str = Field(pattern="^(entrada|saida|ajuste)$")
    quantidade: int = Field(gt=0, description="Quantidade positiva; a direção é definida por tipo_movimento")
    observacao: Optional[str] = None


class DistribuicaoEstoqueRequest(BaseModel):
    """Distribuição: diminuição automática do estoque geral quando polo/escola adquire licença/livro."""
    materia_id: str
    tipo: str = Field(default="licenca", pattern="^(licenca|livro)$")
    destino: str = Field(pattern="^(polo|escola|ead)$")
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    quantidade: int = Field(gt=0)
    observacao: Optional[str] = None


class MovimentacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    materia_id: str
    materia_nome: Optional[str] = None
    tipo_item: str = "licenca"
    tipo_movimento: str
    quantidade: int
    destino_tipo: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    usuario_id: Optional[str] = None
    usuario_nome: Optional[str] = None
    observacao: Optional[str] = None
    criado_em: Optional[datetime] = None


class MovimentacaoListResponse(BaseModel):
    total: int
    items: List[MovimentacaoResponse]
    limit: int
    offset: int


# ---------- Aulas / Presenças / Anexos / Atas ----------

class AulaCreateRequest(BaseModel):
    materia_id: str
    professor_id: str
    data_aula: date
    assunto: Optional[str] = None
    total_aulas_previstas: Optional[int] = Field(default=None, ge=0, description="Se informado, atualiza o total de aulas previstas da matéria (RN-07)")


class AulaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    materia_id: str
    materia_nome: Optional[str] = None
    professor_id: str
    professor_nome: Optional[str] = None
    data_aula: Optional[date] = None
    assunto: Optional[str] = None
    criado_em: Optional[datetime] = None


class AulaListResponse(BaseModel):
    total: int
    items: List[AulaResponse]
    limit: int
    offset: int


class PresencaRegistroItem(BaseModel):
    aluno_id: str
    presente: bool


class PresencaListaRequest(BaseModel):
    """Lista de chamada alimentada pelo professor (RN-07)."""
    registros: List[PresencaRegistroItem] = Field(min_length=1)


class PresencaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aula_id: str
    aluno_id: str
    aluno_nome: Optional[str] = None
    presente: bool
    registrado_por: Optional[str] = None
    criado_em: Optional[datetime] = None


class AnexoAulaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aula_id: str
    materia_id: Optional[str] = None
    materia_nome: Optional[str] = None
    data_aula: Optional[date] = None
    nome_arquivo: Optional[str] = None
    url_arquivo: Optional[str] = None
    criado_em: Optional[datetime] = None


class AtaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aula_id: str
    materia_id: Optional[str] = None
    materia_nome: Optional[str] = None
    data_aula: Optional[date] = None
    professor_id: Optional[str] = None
    professor_nome: Optional[str] = None
    conteudo: Optional[str] = None
    criado_em: Optional[datetime] = None


class PresencaProfessorItem(BaseModel):
    aluno_id: str
    aluno_nome: Optional[str] = None
    aulas_registradas: int = 0
    presencas: int = 0
    percentual: float = 0.0


class ProfessorDetalheResponse(BaseModel):
    """Card clicável do professor (seção 1.5): perfil + anexos + atas + lista de chamada."""
    id: str
    nome: str
    email: Optional[str] = None
    cpf: Optional[str] = None
    status: str = "ativo"
    criado_em: Optional[datetime] = None
    anexos: List[AnexoAulaResponse] = Field(default_factory=list)
    atas: List[AtaResponse] = Field(default_factory=list)
    lista_chamada: List[PresencaProfessorItem] = Field(default_factory=list)


# ---------- Certificados (RN-05) ----------

class CertificadoEmitirRequest(BaseModel):
    aluno_id: str
    matricula_id: Optional[str] = None


class CertificadoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    aluno_id: str
    aluno_nome: Optional[str] = None
    matricula_id: Optional[str] = None
    numero_certificado: Optional[str] = None
    data_emissao: Optional[datetime] = None
    status: str = "emitido"
    criado_em: Optional[datetime] = None


class CertificadoDetalheResponse(CertificadoResponse):
    """Card clicável do certificado (seção 1.6): datas dos 2 estágios + emissão."""
    data_entrega_estagio_teologia: Optional[datetime] = None
    data_entrega_estagio_homiletica: Optional[datetime] = None
    historico_completo: bool = False


class CertificadoListResponse(BaseModel):
    total: int
    items: List[CertificadoDetalheResponse]
    limit: int
    offset: int


# ---------- Chat (RN-06) ----------

class ChatParticipanteItem(BaseModel):
    usuario_id: str
    nome: Optional[str] = None
    perfil: Optional[str] = None


class ConversaCreateRequest(BaseModel):
    tipo: str = Field(pattern="^(individual|grupo)$")
    nome: Optional[str] = Field(default=None, description="Nome do grupo (obrigatório para tipo=grupo)")
    participantes: List[str] = Field(min_length=2, description="IDs dos usuários participantes")
    mensagem_inicial: Optional[str] = None


class ChatMensagemCreateRequest(BaseModel):
    conteudo: str = Field(min_length=1)


class ChatMensagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversa_id: str
    remetente_id: str
    remetente_nome: Optional[str] = None
    conteudo: str
    lida: bool = False
    lida_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None


class ConversaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tipo: str = "individual"
    nome: Optional[str] = None
    status: str = "ativa"
    criado_por: Optional[str] = None
    participantes: List[ChatParticipanteItem] = Field(default_factory=list)
    ultima_mensagem: Optional[str] = None
    total_mensagens: int = 0
    criado_em: Optional[datetime] = None


class ConversaListResponse(BaseModel):
    total: int
    items: List[ConversaResponse]
    limit: int
    offset: int


class ConversaDetalheResponse(ConversaResponse):
    mensagens: List[ChatMensagemResponse] = Field(default_factory=list)


class ChatGrupoCreateRequest(BaseModel):
    nome: str = Field(min_length=2)
    descricao: Optional[str] = None
    participantes: List[str] = Field(min_length=1)
    mensagem_inicial: Optional[str] = None


# ---------- Financeiro ----------

class VendaCreateRequest(BaseModel):
    descricao: Optional[str] = None
    modalidade: str = Field(default="polo", pattern="^(polo|escola|ead)$")
    tipo_item: str = Field(default="licenca", pattern="^(licenca|livro|matricula_ead|taxa_reingresso|outro)$")
    valor: float = Field(ge=0, description="Valor total da venda")
    quantidade: int = Field(default=1, ge=1)
    materia_id: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    aluno_id: Optional[str] = None
    gerar_boleto: bool = Field(default=False, description="Gera boleto via integração AsaaS (stub)")
    boleto_vencimento: Optional[date] = None


class VendaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    descricao: Optional[str] = None
    modalidade: str = "polo"
    tipo_item: str = "licenca"
    valor: float = 0.0
    quantidade: int = 1
    materia_id: Optional[str] = None
    materia_nome: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    aluno_id: Optional[str] = None
    criado_por: Optional[str] = None
    criado_em: Optional[datetime] = None


class VendaListResponse(BaseModel):
    total: int
    items: List[VendaResponse]
    limit: int
    offset: int
    total_valor: float = 0.0


class BoletoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    venda_id: Optional[str] = None
    valor: float = 0.0
    data_vencimento: Optional[date] = None
    status: str = "gerado"
    nosso_numero: Optional[str] = None
    asaas_id: Optional[str] = None
    link_pdf: Optional[str] = None
    criado_em: Optional[datetime] = None


class BoletoListResponse(BaseModel):
    total: int
    items: List[BoletoResponse]
    limit: int
    offset: int


class BoletoCreateRequest(BaseModel):
    venda_id: Optional[str] = None
    valor: float = Field(ge=0)
    data_vencimento: Optional[date] = None
    polo_id: Optional[str] = None


# ---------- Logística (pedidos de livros) ----------

class PedidoLivroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    materia_id: Optional[str] = None
    materia_nome: Optional[str] = None
    quantidade: int = 1
    status: str = "pendente"
    solicitado_por: Optional[str] = None
    observacao: Optional[str] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class PedidoLivroListResponse(BaseModel):
    total: int
    items: List[PedidoLivroResponse]
    limit: int
    offset: int


class PedidoLivroCreateRequest(BaseModel):
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    materia_id: Optional[str] = None
    quantidade: int = Field(default=1, ge=1)
    observacao: Optional[str] = None


class PedidoLivroStatusRequest(BaseModel):
    status: str = Field(pattern="^(pendente|enviado|entregue|cancelado)$")
    observacao: Optional[str] = None


# ---------- Dashboard (cards clicáveis com contagem) ----------

class ContagemResponse(BaseModel):
    """Contagem de um visualizador da dashboard (cards clicáveis)."""
    titulo: str
    total: int
    filtros: Optional[Dict[str, Any]] = None


class DashboardResumoResponse(BaseModel):
    alunos_ativos: int = 0
    matriculas: int = 0
    polos_ativos: int = 0
    escolas_ativas: int = 0
    professores_ativos: int = 0
    certificados_emitidos: int = 0


class RankingPoloItem(BaseModel):
    polo_id: str
    polo_nome: Optional[str] = None
    total_licencas: int = 0
    total_livros: int = 0
    total_adquirido: int = 0


class RankingPolosResponse(BaseModel):
    items: List[RankingPoloItem]


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


class ArquivoPdfResponse(BaseModel):
    """Metadados do PDF gerado (conteúdo binário vai no StreamingResponse)."""
    nome_arquivo: str
    tamanho_bytes: int
