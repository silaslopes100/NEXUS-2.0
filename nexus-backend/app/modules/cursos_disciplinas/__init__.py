"""Módulo de Cursos, Disciplinas e Conteúdos AVA do NEXUS 2.0."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/cursos-disciplinas", tags=["Cursos & Disciplinas (AVA)"])


class CursoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    nome: str
    descricao: Optional[str] = None
    modalidade: str = "hibrido"
    carga_horaria_total: Optional[int] = 0
    semestres: int = 3
    status: str = "ativo"


class DisciplinaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    curso_id: Optional[str] = None
    semestre: Optional[int] = 1
    nome: str
    ordem: int = 0
    carga_horaria: Optional[int] = 40
    qtd_aulas_prevista: Optional[int] = 10
    tipo: str = "presencial"
    eh_extra_grade: bool = False


class DisciplinaConteudoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    disciplina_id: str
    titulo: Optional[str] = None
    tipo_midia: Optional[str] = "video"
    url_arquivo: Optional[str] = None
    ordem: int = 0


_cursos_db: Dict[str, Dict[str, Any]] = {}
_disciplinas_db: Dict[str, Dict[str, Any]] = {}
_conteudos_db: Dict[str, Dict[str, Any]] = {}


@router.get("/cursos", response_model=List[CursoSchema])
async def list_cursos():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome, descricao, modalidade, carga_horaria_total, semestres, status FROM cursos")
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_cursos_db.values())


@router.post("/cursos", response_model=CursoSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_curso(dados: CursoSchema):
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO cursos (id, nome, descricao, modalidade, carga_horaria_total, semestres, status, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.nome, dados.descricao, dados.modalidade, dados.carga_horaria_total, dados.semestres, dados.status))
    except Exception:
        _cursos_db[new_id] = c_dict
    return c_dict


@router.get("/disciplinas", response_model=List[DisciplinaSchema])
async def list_disciplinas(curso_id: Optional[str] = None, semestre: Optional[int] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, curso_id, semestre, nome, ordem, carga_horaria, qtd_aulas_prevista, tipo, eh_extra_grade FROM disciplinas"
            conds = []
            params = []
            if curso_id:
                conds.append("curso_id = %s")
                params.append(curso_id)
            if semestre:
                conds.append("semestre = %s")
                params.append(semestre)
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            sql += " ORDER BY ordem ASC"
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        discs = list(_disciplinas_db.values())
        if curso_id:
            discs = [d for d in discs if d.get("curso_id") == curso_id]
        return discs


@router.post("/disciplinas", response_model=DisciplinaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_disciplina(dados: DisciplinaSchema):
    new_id = str(uuid.uuid4())
    d_dict = dados.model_dump()
    d_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO disciplinas (id, curso_id, semestre, nome, ordem, carga_horaria, qtd_aulas_prevista, tipo, eh_extra_grade, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.curso_id, dados.semestre, dados.nome, dados.ordem, dados.carga_horaria, dados.qtd_aulas_prevista, dados.tipo, dados.eh_extra_grade))
    except Exception:
        _disciplinas_db[new_id] = d_dict
    return d_dict


@router.get("/disciplinas/{disciplina_id}/conteudos", response_model=List[DisciplinaConteudoSchema])
async def list_disciplina_conteudos(disciplina_id: str):
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, disciplina_id, titulo, tipo_midia, url_arquivo, ordem FROM disciplina_conteudos WHERE disciplina_id = %s ORDER BY ordem ASC", (disciplina_id,))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return [c for c in _conteudos_db.values() if c.get("disciplina_id") == disciplina_id]


@router.post("/disciplinas/{disciplina_id}/conteudos", response_model=DisciplinaConteudoSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "professor"]))])
async def create_disciplina_conteudo(disciplina_id: str, dados: DisciplinaConteudoSchema):
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    c_dict["disciplina_id"] = disciplina_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO disciplina_conteudos (id, disciplina_id, titulo, tipo_midia, url_arquivo, ordem, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, disciplina_id, dados.titulo, dados.tipo_midia, dados.url_arquivo, dados.ordem))
    except Exception:
        _conteudos_db[new_id] = c_dict
    return c_dict
