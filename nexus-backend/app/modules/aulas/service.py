"""Regras de negócio do módulo `aulas`."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.aulas.repository import (
    AulasRepositoryInterface,
    dias_atras,
    get_aulas_repository,
)
from app.modules.aulas.schemas import (
    AlunoChamadaAula,
    AtividadeDocenteResponse,
    AulaCreateRequest,
    AulaDetalhe,
    AulaListResponse,
    AulaResumo,
    AulaUpdateRequest,
    DisciplinaAulasResumo,
    FiltrosAuditoriaResponse,
    MaterialAula,
)
from app.modules.auth.schemas import UserResponse
from app.modules.professores.access import usuario_eh_professor


def _texto(valor: Optional[str]) -> Optional[str]:
    limpo = (valor or "").strip()
    return limpo or None


class AulasService:
    def __init__(self, repo: Optional[AulasRepositoryInterface] = None) -> None:
        self._repo = repo

    @property
    def repo(self) -> AulasRepositoryInterface:
        return self._repo or get_aulas_repository()

    # ---------- Acesso ----------

    def _vinculo_permitido(self, user: UserResponse, vinculo_id: str) -> Dict[str, Any]:
        vinculo = self.repo.get_vinculo(vinculo_id)
        if not vinculo or not vinculo.get("ativo", True):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vínculo docente não encontrado ou inativo")
        if not vinculo.get("turma_id"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="A aula precisa estar vinculada a uma turma.",
            )
        if usuario_eh_professor(user) and str(vinculo.get("professor_usuario_id")) != str(user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Professor sem vínculo com esta turma")
        return vinculo

    def _aula_permitida(self, user: UserResponse, aula_id: str) -> Dict[str, Any]:
        aula = self.repo.obter(aula_id)
        if not aula:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aula não encontrada")
        if usuario_eh_professor(user) and str(aula.get("professor_usuario_id")) != str(user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Esta aula pertence a outro professor")
        return aula

    def _garantir_chave_livre(
        self, vinculo_id: str, data_aula: date, numero_aula: int, ignorar_id: Optional[str] = None
    ) -> None:
        if self.repo.chave_em_uso(vinculo_id, data_aula, numero_aula, ignorar_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Já existe a aula nº {numero_aula} desta turma em {data_aula:%d/%m/%Y}.",
            )

    # ---------- Leitura ----------

    def listar(
        self, user: Optional[UserResponse], filtros: Dict[str, Any], limit: int, offset: int
    ) -> AulaListResponse:
        if user is not None and usuario_eh_professor(user):
            filtros = {**filtros, "professor_usuario_id": str(user.id)}
        total, rows = self.repo.listar(filtros, limit, offset)
        return AulaListResponse(
            total=total,
            items=[AulaResumo(**row) for row in rows],
            limit=limit,
            offset=offset,
        )

    def detalhe(self, user: UserResponse, aula_id: str) -> AulaDetalhe:
        aula = self._aula_permitida(user, aula_id)
        return AulaDetalhe(
            **aula,
            materiais=[MaterialAula(**m) for m in self.repo.listar_materiais(aula_id)],
            chamada=[AlunoChamadaAula(**a) for a in self.repo.listar_chamada(aula)],
        )

    def aula_do_material(self, user: UserResponse, aula_id: str, vinculo_id: str) -> Dict[str, Any]:
        """Usado ao anexar material: a aula precisa ser do mesmo vínculo e do usuário."""
        aula = self._aula_permitida(user, aula_id)
        if str(aula["professor_disciplina_id"]) != str(vinculo_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="O material precisa ser da mesma turma e disciplina da aula.",
            )
        return aula

    # ---------- Escrita ----------

    def criar(self, user: UserResponse, dados: AulaCreateRequest) -> AulaDetalhe:
        self._vinculo_permitido(user, dados.professor_disciplina_id)
        self._garantir_chave_livre(dados.professor_disciplina_id, dados.data_aula, dados.numero_aula)
        aula_id = self.repo.criar(
            {
                "professor_disciplina_id": dados.professor_disciplina_id,
                "data_aula": dados.data_aula,
                "numero_aula": dados.numero_aula,
                "conteudo_ministrado": _texto(dados.conteudo_ministrado),
                "observacoes": _texto(dados.observacoes),
                "visivel_aluno": dados.visivel_aluno,
                "criado_por": str(user.id),
            }
        )
        return self.detalhe(user, aula_id)

    def atualizar(self, user: UserResponse, aula_id: str, dados: AulaUpdateRequest) -> AulaDetalhe:
        aula = self._aula_permitida(user, aula_id)
        enviados = dados.model_dump(exclude_unset=True)
        mudancas: Dict[str, Any] = {}
        for campo in ("conteudo_ministrado", "observacoes"):
            if campo in enviados:
                mudancas[campo] = _texto(enviados[campo])
        if enviados.get("visivel_aluno") is not None:
            mudancas["visivel_aluno"] = enviados["visivel_aluno"]

        nova_data = enviados.get("data_aula") or aula["data_aula"]
        novo_numero = enviados.get("numero_aula") or aula["numero_aula"]
        if (nova_data, novo_numero) != (aula["data_aula"], aula["numero_aula"]):
            self._garantir_chave_livre(aula["professor_disciplina_id"], nova_data, novo_numero, aula_id)
            # Sempre os dois juntos: a chamada é movida para a nova chave.
            mudancas["data_aula"] = nova_data
            mudancas["numero_aula"] = novo_numero

        if mudancas:
            self.repo.atualizar(aula_id, mudancas)
        return self.detalhe(user, aula_id)

    def excluir(self, user: UserResponse, aula_id: str) -> List[str]:
        self._aula_permitida(user, aula_id)
        return self.repo.excluir(aula_id)

    def excluir_material(self, user: UserResponse, aula_id: str, material_id: str) -> Optional[str]:
        self._aula_permitida(user, aula_id)
        removido, chave = self.repo.excluir_material(aula_id, material_id)
        if not removido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Material não encontrado nesta aula")
        return chave

    # ---------- Auditoria (admin) ----------

    def filtros_auditoria(self, disciplina_id: Optional[str]) -> FiltrosAuditoriaResponse:
        return FiltrosAuditoriaResponse(**self.repo.opcoes_filtro(disciplina_id))

    def resumo_disciplinas(self) -> List[DisciplinaAulasResumo]:
        return [DisciplinaAulasResumo(**row) for row in self.repo.resumo_por_disciplina()]

    def atividade(self, dias: int, dias_sem_registro: int, top: int = 5) -> AtividadeDocenteResponse:
        data_inicio = dias_atras(dias)
        dados = self.repo.atividade(data_inicio, dias_atras(dias_sem_registro), top)
        return AtividadeDocenteResponse(
            dias=dias,
            dias_sem_registro=dias_sem_registro,
            data_inicio=data_inicio,
            **dados,
        )
