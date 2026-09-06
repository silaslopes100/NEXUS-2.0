"""Módulo de Alunos e Matrículas do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/alunos", tags=["Alunos & Matrículas"])


class AlunoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    usuario_id: str
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    modalidade: str = "polo"
    numero_matricula: Optional[str] = None
    data_nascimento: Optional[date] = None
    status: str = "ativo"
    ultima_movimentacao_em: Optional[datetime] = None


class AlunoDesistenteSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    motivo: Optional[str] = None
    taxa_regularizacao_paga: bool = False
    data_marcacao: Optional[datetime] = None


_alunos_db: Dict[str, Dict[str, Any]] = {}
_desistentes_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[AlunoSchema], dependencies=[Depends(require_role(["admin", "polo", "escola", "professor"]))])
async def list_alunos(polo_id: Optional[str] = None, modalidade: Optional[str] = None, q: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, usuario_id, polo_id, escola_id, modalidade, numero_matricula, data_nascimento, status, ultima_movimentacao_em FROM alunos"
            conds = []
            params = []
            if polo_id:
                conds.append("polo_id = %s")
                params.append(polo_id)
            if modalidade:
                conds.append("modalidade = %s")
                params.append(modalidade)
            if q:
                conds.append("numero_matricula ILIKE %s")
                params.append(f"%{q}%")
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        alunos = list(_alunos_db.values())
        if polo_id:
            alunos = [a for a in alunos if a.get("polo_id") == polo_id]
        if modalidade:
            alunos = [a for a in alunos if a.get("modalidade") == modalidade]
        return alunos


@router.post("", response_model=AlunoSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def create_aluno(dados: AlunoSchema):
    new_id = str(uuid.uuid4())
    matricula = dados.numero_matricula or f"NX-{uuid.uuid4().hex[:8].upper()}"
    a_dict = dados.model_dump()
    a_dict["id"] = new_id
    a_dict["numero_matricula"] = matricula
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO alunos (id, usuario_id, polo_id, escola_id, modalidade, numero_matricula, data_nascimento, status, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            """
            cur.execute(sql, (new_id, dados.usuario_id, dados.polo_id, dados.escola_id, dados.modalidade, matricula, dados.data_nascimento, dados.status))
    except Exception:
        _alunos_db[new_id] = a_dict
    return a_dict


@router.post("/{aluno_id}/desistir", response_model=AlunoDesistenteSchema, dependencies=[Depends(require_role(["admin", "polo"]))])
async def marcar_desistencia(aluno_id: str, motivo: str):
    new_id = str(uuid.uuid4())
    record = {
        "id": new_id,
        "aluno_id": aluno_id,
        "motivo": motivo,
        "taxa_regularizacao_paga": False,
        "data_marcacao": datetime.now(timezone.utc),
    }
    try:
        with get_db_cursor() as cur:
            cur.execute("UPDATE alunos SET status = 'desistente', atualizado_em = now() WHERE id = %s", (aluno_id,))
            cur.execute("INSERT INTO alunos_desistentes (id, aluno_id, motivo, criado_em, atualizado_em) VALUES (%s, %s, %s, now(), now())", (new_id, aluno_id, motivo))
    except Exception:
        _desistentes_db[new_id] = record
        if aluno_id in _alunos_db:
            _alunos_db[aluno_id]["status"] = "desistente"
    return record
