"""Módulo de Professores e Docência do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/professores", tags=["Professores & Docência"])


class ProfessorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    usuario_id: str
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    chave_pix: Optional[str] = None
    valor_hora_aula: Optional[float] = None
    data_inicio_aulas: Optional[datetime] = None


class ProfessorDisciplinaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    professor_id: str
    disciplina_id: str
    turma_id: Optional[str] = None
    qtd_aulas_prevista: Optional[int] = 0
    carga_horaria_total: Optional[int] = 0
    conteudo_programatico: Optional[str] = None


class ProfessorMaterialSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    professor_disciplina_id: str
    arquivo_url: str
    data_aula: Optional[date] = None
    descricao: Optional[str] = None


class AtaAulaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    professor_disciplina_id: str
    numero_aula: int
    data_aula: Optional[date] = None
    conteudo_ata: str


_professores_db: Dict[str, Dict[str, Any]] = {}
_prof_disc_db: Dict[str, Dict[str, Any]] = {}
_materiais_db: Dict[str, Dict[str, Any]] = {}
_atas_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[ProfessorSchema], dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def list_professores():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, usuario_id, polo_id, escola_id, chave_pix, valor_hora_aula, data_inicio_aulas FROM professores")
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_professores_db.values())


@router.post("", response_model=ProfessorSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_professor(dados: ProfessorSchema):
    new_id = str(uuid.uuid4())
    p_dict = dados.model_dump()
    p_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO professores (id, usuario_id, polo_id, escola_id, chave_pix, valor_hora_aula, data_inicio_aulas, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
            """
            cur.execute(sql, (new_id, dados.usuario_id, dados.polo_id, dados.escola_id, dados.chave_pix, dados.valor_hora_aula, dados.data_inicio_aulas))
    except Exception:
        _professores_db[new_id] = p_dict
    return p_dict


@router.get("/disciplinas", response_model=List[ProfessorDisciplinaSchema], dependencies=[Depends(require_role(["admin", "professor", "polo"]))])
async def list_professor_disciplinas(professor_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, professor_id, disciplina_id, turma_id, qtd_aulas_prevista, carga_horaria_total, conteudo_programatico FROM professor_disciplinas"
            if professor_id:
                sql += " WHERE professor_id = %s"
                cur.execute(sql, (professor_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        discs = list(_prof_disc_db.values())
        if professor_id:
            discs = [d for d in discs if d.get("professor_id") == professor_id]
        return discs


@router.post("/materiais", response_model=ProfessorMaterialSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "professor"]))])
async def create_material(dados: ProfessorMaterialSchema):
    new_id = str(uuid.uuid4())
    m_dict = dados.model_dump()
    m_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO professor_materiais (id, professor_disciplina_id, arquivo_url, data_aula, descricao, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.professor_disciplina_id, dados.arquivo_url, dados.data_aula, dados.descricao))
    except Exception:
        _materiais_db[new_id] = m_dict
    return m_dict


@router.post("/atas", response_model=AtaAulaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "professor"]))])
async def create_ata(dados: AtaAulaSchema):
    new_id = str(uuid.uuid4())
    a_dict = dados.model_dump()
    a_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO atas_aula (id, professor_disciplina_id, numero_aula, data_aula, conteudo_ata, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.professor_disciplina_id, dados.numero_aula, dados.data_aula, dados.conteudo_ata))
    except Exception:
        _atas_db[new_id] = a_dict
    return a_dict
