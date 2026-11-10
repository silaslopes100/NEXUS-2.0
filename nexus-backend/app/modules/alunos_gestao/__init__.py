"""Central de Alunos: listagem unificada, Boletim, Churn e reingresso."""
from app.modules.alunos_gestao.router import router, router_aprendizado

__all__ = ["router", "router_aprendizado"]
