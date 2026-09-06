"""Módulo de Certificados e Diplomas Digitais do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/certificados", tags=["Certificados & Diplomas"])


class CertificadoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: Optional[str] = None
    curso_id: Optional[str] = None
    data_estagio_teologia_ministerio: Optional[date] = None
    data_estagio_homiletica: Optional[date] = None
    emitido_em: Optional[datetime] = None
    url_arquivo: Optional[str] = None


_certificados_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[CertificadoSchema], dependencies=[Depends(require_role(["admin", "polo", "escola", "aluno"]))])
async def list_certificados(aluno_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, aluno_id, curso_id, data_estagio_teologia_ministerio, data_estagio_homiletica, emitido_em, url_arquivo FROM certificados"
            if aluno_id:
                sql += " WHERE aluno_id = %s"
                cur.execute(sql, (aluno_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        certs = list(_certificados_db.values())
        if aluno_id:
            certs = [c for c in certs if c.get("aluno_id") == aluno_id]
        return certs


@router.post("/emitir", response_model=CertificadoSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo"]))])
async def emitir_certificado(dados: CertificadoSchema):
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    c_dict["emitido_em"] = c_dict.get("emitido_em") or datetime.now(timezone.utc)
    c_dict["url_arquivo"] = c_dict.get("url_arquivo") or f"https://cdn.nexus.com.br/certificados/{new_id}.pdf"
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO certificados (id, aluno_id, curso_id, data_estagio_teologia_ministerio, data_estagio_homiletica, emitido_em, url_arquivo, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
            """
            cur.execute(sql, (new_id, dados.aluno_id, dados.curso_id, dados.data_estagio_teologia_ministerio, dados.data_estagio_homiletica, c_dict["emitido_em"], c_dict["url_arquivo"]))
    except Exception:
        _certificados_db[new_id] = c_dict
    return c_dict
