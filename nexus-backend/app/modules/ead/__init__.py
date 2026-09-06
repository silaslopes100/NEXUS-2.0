"""Módulo de Educação a Distância (EAD) do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/ead", tags=["Educação a Distância (EAD)"])


class MatriculaEadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    curso_id: Optional[str] = None
    ativa_automaticamente: bool = False
    data_matricula: Optional[datetime] = None


class CompraDisciplinaEadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    disciplina_id: Optional[str] = None
    valor_pago: Optional[float] = 0.0
    status_pagamento: str = "pendente"
    liberada_em: Optional[datetime] = None
    prazo_conclusao: Optional[datetime] = None
    reprovado_por_prazo: bool = False


class AvisoLiberacaoEadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    disciplina_id: str
    data_liberacao: Optional[date] = None
    notificado_em: Optional[datetime] = None


_matriculas_ead_db: Dict[str, Dict[str, Any]] = {}
_compras_ead_db: Dict[str, Dict[str, Any]] = {}
_avisos_ead_db: Dict[str, Dict[str, Any]] = {}


@router.get("/matriculas", response_model=List[MatriculaEadSchema], dependencies=[Depends(require_role(["admin", "aluno", "polo"]))])
async def list_matriculas_ead(aluno_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, aluno_id, curso_id, ativa_automaticamente, data_matricula FROM matriculas_ead"
            if aluno_id:
                sql += " WHERE aluno_id = %s"
                cur.execute(sql, (aluno_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        mats = list(_matriculas_ead_db.values())
        if aluno_id:
            mats = [m for m in mats if m.get("aluno_id") == aluno_id]
        return mats


@router.post("/matriculas", response_model=MatriculaEadSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo", "aluno"]))])
async def create_matricula_ead(dados: MatriculaEadSchema):
    new_id = str(uuid.uuid4())
    m_dict = dados.model_dump()
    m_dict["id"] = new_id
    m_dict["data_matricula"] = m_dict.get("data_matricula") or datetime.now(timezone.utc)
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO matriculas_ead (id, aluno_id, curso_id, ativa_automaticamente, data_matricula, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.aluno_id, dados.curso_id, dados.ativa_automaticamente, m_dict["data_matricula"]))
    except Exception:
        _matriculas_ead_db[new_id] = m_dict
    return m_dict


@router.get("/compras", response_model=List[CompraDisciplinaEadSchema], dependencies=[Depends(require_role(["admin", "aluno", "polo"]))])
async def list_compras_ead(aluno_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, aluno_id, disciplina_id, valor_pago, status_pagamento, liberada_em, prazo_conclusao, reprovado_por_prazo FROM compras_disciplina_ead"
            if aluno_id:
                sql += " WHERE aluno_id = %s"
                cur.execute(sql, (aluno_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_compras_ead_db.values())


@router.post("/compras", response_model=CompraDisciplinaEadSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "aluno", "polo"]))])
async def create_compra_ead(dados: CompraDisciplinaEadSchema):
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO compras_disciplina_ead (id, aluno_id, disciplina_id, valor_pago, status_pagamento, liberada_em, prazo_conclusao, reprovado_por_prazo, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.aluno_id, dados.disciplina_id, dados.valor_pago, dados.status_pagamento, dados.liberada_em, dados.prazo_conclusao, dados.reprovado_por_prazo))
    except Exception:
        _compras_ead_db[new_id] = c_dict
    return c_dict
