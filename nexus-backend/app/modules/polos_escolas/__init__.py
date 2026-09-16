"""Módulo de Polos & Escolas do NEXUS 2.0.

Consolida gestão de Polos, Escolas, licenças, professores, financeiro,
alunos, presenças, gestão pedagógica e treinamentos
(ver docs/Requisitos_Nexus2.0(Polo_Escola).md).
"""
from __future__ import annotations

from app.modules.polos_escolas.router import router

__all__ = ["router"]
