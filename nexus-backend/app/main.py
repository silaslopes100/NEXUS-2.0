"""Ponto de entrada da aplicação FastAPI NEXUS 2.0."""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import close_connection_pool
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.certificados import router as certificados_router
from app.modules.comunicacao import router as comunicacao_router
from app.modules.cupons import router as cupons_router
from app.modules.cursos_disciplinas import router as cursos_disciplinas_router
from app.modules.ead import router as ead_router
from app.modules.notas_historico import router as notas_historico_router
from app.modules.pedidos_livros import router as pedidos_livros_router
from app.modules.polos_escolas import router as polos_escolas_router
from app.modules.transferencias import router as transferencias_router
from app.modules.turmas import router as turmas_router

# Nota: os módulos legados `alunos`, `licencas`, `financeiro`, `professores` e
# `presencas` foram absorvidos pelo módulo `polos_escolas` (ver
# docs/Requisitos_Nexus2.0(Polo_Escola).md) e não são mais registrados aqui.


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_connection_pool()


app = FastAPI(
    title="NEXUS 2.0 API",
    description="Backend unificado e modernizado do ecossistema educacional NEXUS 2.0 com os 18 módulos integrados.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos Módulos do Sistema
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(polos_escolas_router)
app.include_router(cursos_disciplinas_router)
app.include_router(turmas_router)
app.include_router(ead_router)
app.include_router(notas_historico_router)
app.include_router(certificados_router)
app.include_router(cupons_router)
app.include_router(pedidos_livros_router)
app.include_router(transferencias_router)
app.include_router(comunicacao_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "2.0.0", "environment": settings.ENVIRONMENT}
