"""Schemas da ficha cadastral do usuário: seções editáveis, inativação e histórico."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

UFS = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)
Sexo = Literal["feminino", "masculino", "outro", "nao_informado"]
EstadoCivil = Literal["solteiro", "casado", "divorciado", "viuvo", "uniao_estavel", "separado"]


def _texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    limpo = valor.strip()
    return limpo or None


def _digitos(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    return re.sub(r"\D", "", valor) or None


def _uf(valor: Optional[str]) -> Optional[str]:
    limpo = _texto(valor)
    if limpo is None:
        return None
    limpo = limpo.upper()
    if limpo not in UFS:
        raise ValueError("UF inválida")
    return limpo


def _telefone(valor: Optional[str]) -> Optional[str]:
    digitos = _digitos(valor)
    if digitos is not None and len(digitos) not in (10, 11):
        raise ValueError("Telefone deve ter DDD + 8 ou 9 dígitos")
    return digitos


# ---------- Seções editáveis ----------

class IdentificacaoUpdate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    sobrenome: Optional[str] = Field(default=None, max_length=255)
    email: EmailStr
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None

    @field_validator("nome", "sobrenome")
    @classmethod
    def _limpar_nome(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else None

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: Optional[str]) -> Optional[str]:
        digitos = _digitos(v)
        if digitos is not None and len(digitos) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return digitos

    @field_validator("telefone", "celular")
    @classmethod
    def _fone(cls, v: Optional[str]) -> Optional[str]:
        return _telefone(v)


class DadosPessoaisUpdate(BaseModel):
    data_nascimento: Optional[date] = None
    rg: Optional[str] = Field(default=None, max_length=20)
    rg_orgao_emissor: Optional[str] = Field(default=None, max_length=20)
    rg_uf: Optional[str] = None
    sexo: Optional[Sexo] = None
    estado_civil: Optional[EstadoCivil] = None
    naturalidade_cidade: Optional[str] = Field(default=None, max_length=120)
    naturalidade_uf: Optional[str] = None
    nacionalidade: Optional[str] = Field(default=None, max_length=60)

    @field_validator("rg", "rg_orgao_emissor", "naturalidade_cidade", "nacionalidade")
    @classmethod
    def _limpar(cls, v: Optional[str]) -> Optional[str]:
        return _texto(v)

    @field_validator("rg_uf", "naturalidade_uf")
    @classmethod
    def _validar_uf(cls, v: Optional[str]) -> Optional[str]:
        return _uf(v)

    @field_validator("data_nascimento")
    @classmethod
    def _nascimento(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and (v > date.today() or v.year < 1900):
            raise ValueError("Data de nascimento inválida")
        return v


class EnderecoUpdate(BaseModel):
    cep: Optional[str] = None
    logradouro: Optional[str] = Field(default=None, max_length=255)
    numero: Optional[str] = Field(default=None, max_length=20)
    complemento: Optional[str] = Field(default=None, max_length=120)
    bairro: Optional[str] = Field(default=None, max_length=120)
    cidade: Optional[str] = Field(default=None, max_length=120)
    uf: Optional[str] = None

    @field_validator("cep")
    @classmethod
    def _cep(cls, v: Optional[str]) -> Optional[str]:
        digitos = _digitos(v)
        if digitos is not None and len(digitos) != 8:
            raise ValueError("CEP deve ter 8 dígitos")
        return digitos

    @field_validator("logradouro", "numero", "complemento", "bairro", "cidade")
    @classmethod
    def _limpar(cls, v: Optional[str]) -> Optional[str]:
        return _texto(v)

    @field_validator("uf")
    @classmethod
    def _validar_uf(cls, v: Optional[str]) -> Optional[str]:
        return _uf(v)


class ContatoEmergenciaUpdate(BaseModel):
    contato_emergencia_nome: Optional[str] = Field(default=None, max_length=255)
    contato_emergencia_parentesco: Optional[str] = Field(default=None, max_length=60)
    contato_emergencia_telefone: Optional[str] = None

    @field_validator("contato_emergencia_nome", "contato_emergencia_parentesco")
    @classmethod
    def _limpar(cls, v: Optional[str]) -> Optional[str]:
        return _texto(v)

    @field_validator("contato_emergencia_telefone")
    @classmethod
    def _fone(cls, v: Optional[str]) -> Optional[str]:
        return _telefone(v)


class AcessoUpdate(BaseModel):
    """O status não muda aqui: inativar/bloquear exige motivo (`/inativar`) e volta por `/reativar`."""
    perfil_id: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    permissoes: List[str] = Field(default_factory=list)


class VinculoAlunoUpdate(BaseModel):
    """Polo, escola e modalidade não se editam: a troca vai pelo fluxo de transferência."""
    numero_matricula: str = Field(min_length=1, max_length=50)
    data_nascimento: Optional[date] = None

    @field_validator("numero_matricula")
    @classmethod
    def _matricula(cls, v: str) -> str:
        limpo = v.strip()
        if not limpo:
            raise ValueError("Informe o número de matrícula")
        return limpo


class VinculoProfessorUpdate(BaseModel):
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    valor_hora_aula: Optional[float] = Field(default=None, ge=0)
    chave_pix: Optional[str] = Field(default=None, max_length=255)
    status: Literal["ativo", "inativo"] = "ativo"

    @field_validator("polo_id", "escola_id", "chave_pix")
    @classmethod
    def _limpar(cls, v: Optional[str]) -> Optional[str]:
        return _texto(v)


class InativarRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)
    status: Literal["inativo", "bloqueado"] = "inativo"


class PodeExcluirResponse(BaseModel):
    pode_excluir: bool
    motivos: List[str] = Field(default_factory=list)


# ---------- Ficha: blocos novos ----------

class DadosCadastraisFicha(BaseModel):
    data_nascimento: Optional[date] = None
    rg: Optional[str] = None
    rg_orgao_emissor: Optional[str] = None
    rg_uf: Optional[str] = None
    sexo: Optional[str] = None
    estado_civil: Optional[str] = None
    naturalidade_cidade: Optional[str] = None
    naturalidade_uf: Optional[str] = None
    nacionalidade: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    contato_emergencia_nome: Optional[str] = None
    contato_emergencia_parentesco: Optional[str] = None
    contato_emergencia_telefone: Optional[str] = None
    inativado_em: Optional[datetime] = None
    inativado_por_nome: Optional[str] = None
    motivo_inativacao: Optional[str] = None


class TransferenciaPendenteFicha(BaseModel):
    id: str
    tipo: str
    criado_em: Optional[datetime] = None
    polo_destino_nome: Optional[str] = None
    escola_destino_nome: Optional[str] = None


class VinculoDocenteItem(BaseModel):
    professor_disciplina_id: str
    turma_id: Optional[str] = None
    turma_nome: Optional[str] = None
    curso_nome: Optional[str] = None
    disciplina_id: Optional[str] = None
    disciplina_nome: Optional[str] = None
    carga_horaria: Optional[float] = None
    aulas_previstas: Optional[int] = None
    aulas_ministradas: int = 0
    horas_ministradas: float = 0.0
    ativo: bool = True


# ---------- Histórico ----------

AbaHistorico = Literal["academico", "financeiro", "movimentacoes", "auditoria"]


class HistoricoItem(BaseModel):
    """Linha genérica de histórico: `grupo` separa as tabelas da aba no frontend."""
    grupo: str
    id: Optional[str] = None
    data: Optional[datetime] = None
    titulo: str
    detalhe: Optional[str] = None
    status: Optional[str] = None
    valor: Optional[float] = None
    link: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class HistoricoResponse(BaseModel):
    aba: AbaHistorico
    total: int
    limit: int
    offset: int
    items: List[HistoricoItem]
