"""Camada de serviço (regras de negócio) do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.modules.professores.repository import (
    ProfessoresRepositoryInterface,
    get_professores_repository,
)
from app.modules.professores.schemas import (
    MessageResponse,
    ProfessorCreateRequest,
    ProfessorListResponse,
    ProfessorResponse,
    ProfessorUpdateRequest,
)


class ProfessoresService:
    def __init__(self, repo: Optional[ProfessoresRepositoryInterface] = None) -> None:
        self._repo = repo

    @property
    def repo(self) -> ProfessoresRepositoryInterface:
        return self._repo or get_professores_repository()

    # ------------------------------------------------------------------
    # Listagem / consulta
    # ------------------------------------------------------------------

    def list_professores(
        self,
        search: Optional[str] = None,
        polo_id: Optional[str] = None,
        escola_id: Optional[str] = None,
        disciplina: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        escopo_polo_id: Optional[str] = None,
        escopo_escola_id: Optional[str] = None,
    ) -> ProfessorListResponse:
        # RN-09: escopo de visibilidade do usuário logado (quando informado)
        if escopo_polo_id:
            polo_id = escopo_polo_id
        if escopo_escola_id:
            escola_id = escopo_escola_id

        total, rows = self.repo.list_professores(
            search=search,
            polo_id=polo_id,
            escola_id=escola_id,
            disciplina=disciplina,
            status_filter=status_filter,
            limit=limit,
            offset=offset,
        )
        return ProfessorListResponse(
            total=total,
            items=[self._build_response(row) for row in rows],
            limit=limit,
            offset=offset,
        )

    def get_professor(self, professor_id: str) -> ProfessorResponse:
        row = self.repo.get_professor(professor_id)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
        return self._build_response(row)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def create_professor(
        self,
        dados: ProfessorCreateRequest,
        actor_id: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> ProfessorResponse:
        usuario = self.repo.get_usuario_by_id(dados.usuario_id)
        if not usuario:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário vinculado não encontrado")

        if self.repo.get_professor_by_usuario_id(dados.usuario_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Este usuário já está vinculado a um professor",
            )

        professor_id = self.repo.create_professor(dados.model_dump())
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="professor_cadastrado",
            entidade="professores",
            entidade_id=professor_id,
            dados_depois={"usuario_id": dados.usuario_id, "polo_id": dados.polo_id},
            ip=ip,
        )
        return self.get_professor(professor_id)

    def update_professor(
        self,
        professor_id: str,
        dados: ProfessorUpdateRequest,
        actor_id: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> ProfessorResponse:
        atual = self.repo.get_professor(professor_id)
        if not atual:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")

        update_dict: Dict[str, Any] = {
            k: v for k, v in dados.model_dump(exclude_unset=True).items() if v is not None
        }

        novo_usuario_id = update_dict.get("usuario_id")
        if novo_usuario_id and str(novo_usuario_id) != str(atual.get("usuario_id")):
            if not self.repo.get_usuario_by_id(novo_usuario_id):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário vinculado não encontrado")
            if self.repo.get_professor_by_usuario_id(novo_usuario_id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Este usuário já está vinculado a um professor",
                )

        if update_dict:
            self.repo.update_professor(professor_id, update_dict)
            self.repo.record_audit_log(
                usuario_id=actor_id,
                acao="professor_atualizado",
                entidade="professores",
                entidade_id=professor_id,
                dados_depois=update_dict,
                ip=ip,
            )
        return self.get_professor(professor_id)

    def delete_professor(
        self,
        professor_id: str,
        actor_id: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> MessageResponse:
        """Soft delete: o cadastro permanece no histórico com status 'inativo'."""
        professor = self.repo.get_professor(professor_id)
        if not professor:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")

        self.repo.update_professor(professor_id, {"status": "inativo"})
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="professor_desativado",
            entidade="professores",
            entidade_id=professor_id,
            dados_antes={"status": professor.get("status")},
            dados_depois={"status": "inativo"},
            ip=ip,
        )
        return MessageResponse(message="Professor desativado com sucesso")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_response(self, row: Dict[str, Any]) -> ProfessorResponse:
        valor = row.get("valor_hora_aula")
        return ProfessorResponse(
            id=str(row["id"]),
            usuario_id=str(row["usuario_id"]) if row.get("usuario_id") else None,
            nome=row.get("nome"),
            email=row.get("email"),
            polo_id=str(row["polo_id"]) if row.get("polo_id") else None,
            polo_nome=row.get("polo_nome"),
            escola_id=str(row["escola_id"]) if row.get("escola_id") else None,
            escola_nome=row.get("escola_nome"),
            materias=row.get("materias") or [],
            data_inicio=row.get("data_inicio"),
            quantidade_aulas=int(row.get("quantidade_aulas") or 0),
            horas_totais=int(row.get("horas_totais") or 0),
            valor_hora_aula=float(valor) if valor is not None else None,
            pix=row.get("pix"),
            conteudo_programatico=row.get("conteudo_programatico"),
            status=row.get("status") or "ativo",
            criado_em=row.get("criado_em"),
            atualizado_em=row.get("atualizado_em"),
        )
