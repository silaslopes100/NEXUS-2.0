"""Módulo de Professores & Docentes do NEXUS 2.0.

Gestão administrativa de docentes: vínculo com usuário, polo e escola,
disciplinas ministradas, carga horária, contraprestação e status.
(ver docs/Requisitos_Nexus2.0(Polo_Escola).md).
"""
from __future__ import annotations

from app.modules.professores.router import router

__all__ = ["router"]
