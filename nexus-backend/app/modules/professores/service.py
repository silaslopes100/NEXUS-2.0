"""Camada de serviço (regras de negócio) do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.professores.repository import (
    ProfessoresRepositoryInterface,
    get_professores_repository,
)
from app.modules.professores.schemas import (
    MessageResponse,
    ProfessorCreateRequest,
    ProfessorConteudosResponse,
    ProfessorDisciplinaListResponse,
    ProfessorMaterialResumo,
    ProfessorConteudoItem,
    ProfessorListResponse,
    ProfessorDisciplinaConteudosResumo,
    ProfessorResponse,
    ProfessorTurmaVinculoResumo,
    ProfessorTurmaVinculosResponse,
    ProfessorTurmaResumo,
    ProfessorUpdateRequest,
)


_CAMPOS_CADASTRO_DOCENTE = (
    "materias",
    "disciplina_ids",
    "data_inicio",
    "valor_hora_aula",
    "pix",
    "conteudo_programatico",
    "quantidade_aulas",
    "horas_totais",
)


def _registro_a_completar(row: Dict[str, Any]) -> bool:
    """Inativo ou sem nenhum dado docente preenchido (criado só pelo perfil)."""
    if row.get("status") != "ativo":
        return True
    return not any(row.get(campo) for campo in _CAMPOS_CADASTRO_DOCENTE)


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

    def list_minhas_disciplinas_turmas(self, usuario_id: str) -> ProfessorDisciplinaListResponse:
        rows = self.repo.list_disciplinas_turmas_by_usuario(usuario_id)
        disciplinas: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            disciplina_id = str(row["disciplina_id"])
            disciplina = disciplinas.setdefault(
                disciplina_id,
                {
                    "id": disciplina_id,
                    "nome": row["disciplina_nome"],
                    "curso_nome": row.get("curso_nome"),
                    "semestre": row.get("semestre"),
                    "carga_horaria": row.get("carga_horaria"),
                    "qtd_aulas_prevista": row.get("qtd_aulas_prevista"),
                    "turmas": [],
                },
            )
            turma_id = row.get("turma_id")
            if turma_id and all(str(turma["id"]) != str(turma_id) for turma in disciplina["turmas"]):
                disciplina["turmas"].append(
                    {
                        "id": str(turma_id),
                        "nome": row["turma_nome"],
                        "professor_disciplina_id": row.get("professor_disciplina_id"),
                        "data_inicio": row.get("data_inicio"),
                        "data_fim": row.get("data_fim"),
                        "polo_nome": row.get("polo_nome"),
                        "escola_nome": row.get("escola_nome"),
                    }
                )
        return ProfessorDisciplinaListResponse(items=list(disciplinas.values()))

    def list_meus_conteudos_materiais(self, usuario_id: str) -> ProfessorConteudosResponse:
        disciplinas: Dict[str, Dict[str, Any]] = {}
        for row in self.repo.list_disciplinas_turmas_by_usuario(usuario_id):
                disciplina_id = str(row["disciplina_id"])
                disciplina = disciplinas.setdefault(
                    disciplina_id,
                    {
                        "id": disciplina_id,
                        "nome": row["disciplina_nome"],
                        "curso_nome": row.get("curso_nome"),
                        "turmas": {},
                        "conteudos": [],
                        "materiais": [],
                    },
                )
                turma_id = row.get("turma_id")
                if turma_id:
                    turma_key = str(turma_id)
                    disciplina["turmas"].setdefault(
                        turma_key,
                        ProfessorTurmaResumo(
                            id=turma_key,
                            nome=row["turma_nome"],
                            professor_disciplina_id=row.get("professor_disciplina_id"),
                            data_inicio=row.get("data_inicio"),
                            data_fim=row.get("data_fim"),
                            polo_nome=row.get("polo_nome"),
                            escola_nome=row.get("escola_nome"),
                        ),
                    )

        for row in self.repo.list_conteudos_by_usuario(usuario_id):
                disciplina = disciplinas.get(str(row["disciplina_id"]))
                if disciplina and row.get("id"):
                    disciplina["conteudos"].append(
                        ProfessorConteudoItem(
                            id=str(row["id"]),
                            disciplina_id=str(row["disciplina_id"]),
                            titulo=row.get("titulo"),
                            tipo_midia=row.get("tipo_midia"),
                            url_arquivo=row.get("url_arquivo"),
                            ordem=row.get("ordem") or 0,
                            arquivo_nome=row.get("arquivo_nome"),
                            arquivo_mime_type=row.get("arquivo_mime_type"),
                            arquivo_tamanho_bytes=row.get("arquivo_tamanho_bytes"),
                            tem_arquivo=bool(row.get("tem_arquivo") or row.get("arquivo_storage_key")),
                        )
                    )

        for row in self.repo.list_materiais_by_usuario(usuario_id):
                disciplina = disciplinas.get(str(row["disciplina_id"]))
                if disciplina:
                    disciplina["materiais"].append(ProfessorMaterialResumo(**row))

        items = []
        for disciplina in disciplinas.values():
                disciplina["turmas"] = list(disciplina["turmas"].values())
                items.append(ProfessorDisciplinaConteudosResumo(**disciplina))
        return ProfessorConteudosResponse(items=items)

    def listar_vinculos_turma(
        self, turma_id: str, current_user: UserResponse
    ) -> ProfessorTurmaVinculosResponse:
        self._turma_no_escopo(turma_id, current_user)
        scope_column, scope_id = self._escopo_vinculo(current_user)
        items = [
            ProfessorTurmaVinculoResumo(**row)
            for row in self.repo.list_vinculos_ativos_por_turma(
                turma_id, scope_column, scope_id
            )
        ]
        return ProfessorTurmaVinculosResponse(items=items)

    def criar_vinculo_turma(
        self,
        turma_id: str,
        professor_id: str,
        disciplina_id: str,
        current_user: UserResponse,
        ip: Optional[str] = None,
    ) -> ProfessorTurmaVinculoResumo:
        turma = self._turma_no_escopo(turma_id, current_user)
        if not turma.get("curso_id"):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="A turma precisa estar vinculada a um curso.",
            )

        professor = self.repo.get_professor(professor_id)
        if not professor or professor.get("status") != "ativo":
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Professor ativo não encontrado.",
            )
        self._validar_escopo_professor(professor, current_user)
        usuario = self.repo.get_usuario_by_id(str(professor.get("usuario_id") or ""))
        if not usuario or usuario.get("status") != "ativo":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="O usuário associado ao professor está inativo.",
            )

        curso_disciplina = self.repo.get_disciplina_curso(disciplina_id)
        if not curso_disciplina:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Disciplina não encontrada ou sem curso associado.",
            )
        if str(curso_disciplina) != str(turma["curso_id"]):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="A disciplina selecionada não pertence ao curso da turma.",
            )

        scope_column, scope_id = self._escopo_vinculo(current_user)
        vinculo_id, resultado = self.repo.create_or_reactivate_vinculo_turma(
            professor_id, disciplina_id, turma_id, scope_column, scope_id
        )
        if resultado == "missing_turma":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")
        if resultado == "missing_discipline":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada.")
        if resultado in {"out_of_scope", "professor_out_of_scope"}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Turma ou professor fora do seu escopo.")
        if resultado == "course_mismatch":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="A disciplina selecionada não pertence ao curso da turma.",
            )
        if resultado == "inactive_professor":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="O professor ou seu usuário está inativo.",
            )
        if resultado == "exists":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Este professor já está vinculado à disciplina nesta turma.",
            )
        self.repo.record_audit_log(
            usuario_id=current_user.id,
            acao=(
                "vinculo_professor_turma_reativado"
                if resultado == "reactivated"
                else "vinculo_professor_turma_criado"
            ),
            entidade="professor_disciplinas",
            entidade_id=vinculo_id,
            dados_depois={
                "professor_id": professor_id,
                "disciplina_id": disciplina_id,
                "turma_id": turma_id,
            },
            ip=ip,
        )
        row = next(
            (
                item
                for item in self.repo.list_vinculos_ativos_por_turma(
                    turma_id, scope_column, scope_id
                )
                if str(item["id"]) == vinculo_id
            ),
            None,
        )
        if not row:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="O vínculo foi salvo, mas não pôde ser recuperado.",
            )
        return ProfessorTurmaVinculoResumo(**row)

    def arquivar_vinculo_turma(
        self,
        turma_id: str,
        vinculo_id: str,
        current_user: UserResponse,
        ip: Optional[str] = None,
    ) -> MessageResponse:
        self._turma_no_escopo(turma_id, current_user)
        scope_column, scope_id = self._escopo_vinculo(current_user)
        antes, resultado = self.repo.archive_vinculo_turma(
            turma_id, vinculo_id, scope_column, scope_id
        )
        if resultado == "missing_turma":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")
        if resultado == "out_of_scope":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Turma fora do seu escopo.")
        if not antes:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Vínculo ativo não encontrado nesta turma.",
            )
        self.repo.record_audit_log(
            usuario_id=current_user.id,
            acao="vinculo_professor_turma_arquivado",
            entidade="professor_disciplinas",
            entidade_id=vinculo_id,
            dados_antes=antes,
            dados_depois={**antes, "ativo": False},
            ip=ip,
        )
        return MessageResponse(message="Vínculo arquivado; materiais e atas foram preservados.")

    @staticmethod
    def _escopo_vinculo(
        current_user: UserResponse,
    ) -> tuple[Optional[str], Optional[str]]:
        perfil = perfil_do_usuario(current_user)
        if perfil == "polo":
            return "polo_id", str(current_user.polo_id)
        if perfil == "escola":
            return "escola_id", str(current_user.escola_id)
        return None, None

    def _turma_no_escopo(
        self, turma_id: str, current_user: UserResponse
    ) -> Dict[str, Any]:
        turma = self.repo.get_turma_vinculo_scope(turma_id)
        if not turma:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")
        perfil = perfil_do_usuario(current_user)
        if perfil == "admin":
            return turma
        if perfil == "polo":
            if not current_user.polo_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo.")
            if str(turma.get("polo_id")) != str(current_user.polo_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Turma fora do seu escopo.")
            return turma
        if perfil == "escola":
            if not current_user.escola_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Escola sem vínculo.")
            if str(turma.get("escola_id")) != str(current_user.escola_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Turma fora do seu escopo.")
            return turma
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado para esta operação.")

    @staticmethod
    def _validar_escopo_professor(
        professor: Dict[str, Any], current_user: UserResponse
    ) -> None:
        perfil = perfil_do_usuario(current_user)
        if perfil == "polo" and str(professor.get("polo_id")) != str(current_user.polo_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Professor fora do seu escopo.")
        if perfil == "escola" and str(professor.get("escola_id")) != str(current_user.escola_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Professor fora do seu escopo.")

    def get_conteudo(self, conteudo_id: str) -> Dict[str, Any]:
        row = self.repo.get_conteudo(conteudo_id)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado")
        return row

    def create_conteudo(self, data: Dict[str, Any]) -> ProfessorConteudoItem:
        return self._conteudo_response(self.repo.create_conteudo(data))

    def update_conteudo(self, conteudo_id: str, data: Dict[str, Any]) -> ProfessorConteudoItem:
        row = self.repo.update_conteudo(conteudo_id, data)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conteúdo não encontrado")
        return self._conteudo_response(row)

    def get_material(self, material_id: str) -> Dict[str, Any]:
        row = self.repo.get_material(material_id)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Material não encontrado")
        return row

    def create_material(self, data: Dict[str, Any]) -> ProfessorMaterialResumo:
        return self._material_response(self.repo.create_material(data))

    def update_material(self, material_id: str, data: Dict[str, Any]) -> ProfessorMaterialResumo:
        row = self.repo.update_material(material_id, data)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Material não encontrado")
        return self._material_response(row)

    def get_vinculo_academico(self, vinculo_id: str) -> Optional[Dict[str, Any]]:
        return self.repo.get_vinculo_academico(vinculo_id)

    @staticmethod
    def _conteudo_response(row: Dict[str, Any]) -> ProfessorConteudoItem:
        return ProfessorConteudoItem(
            id=str(row["id"]),
            disciplina_id=str(row["disciplina_id"]),
            titulo=row.get("titulo"),
            tipo_midia=row.get("tipo_midia"),
            url_arquivo=row.get("url_arquivo"),
            ordem=row.get("ordem") or 0,
            arquivo_nome=row.get("arquivo_nome"),
            arquivo_mime_type=row.get("arquivo_mime_type"),
            arquivo_tamanho_bytes=row.get("arquivo_tamanho_bytes"),
            tem_arquivo=bool(row.get("tem_arquivo") or row.get("arquivo_storage_key")),
        )

    @staticmethod
    def _material_response(row: Dict[str, Any]) -> ProfessorMaterialResumo:
        return ProfessorMaterialResumo(
            id=str(row["id"]),
            professor_disciplina_id=str(row["professor_disciplina_id"]),
            disciplina_id=str(row["disciplina_id"]),
            turma_id=str(row["turma_id"]) if row.get("turma_id") else None,
            turma_nome=row.get("turma_nome"),
            arquivo_url=row.get("arquivo_url"),
            data_aula=row.get("data_aula"),
            descricao=row.get("descricao"),
            expira_em=row.get("expira_em"),
            arquivo_nome=row.get("arquivo_nome"),
            arquivo_mime_type=row.get("arquivo_mime_type"),
            arquivo_tamanho_bytes=row.get("arquivo_tamanho_bytes"),
            tem_arquivo=bool(row.get("tem_arquivo") or row.get("arquivo_storage_key")),
        )

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

        existente = self.repo.get_professor_by_usuario_id(dados.usuario_id)
        if existente and not _registro_a_completar(existente):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Este usuário já está vinculado a um professor",
            )

        if existente:
            # Registro criado automaticamente pela tela de Usuários (ou desativado):
            # completa-o em vez de duplicar.
            professor_id = str(existente["id"])
            self._validar_disciplinas(dados.disciplina_ids)
            self.repo.update_professor(professor_id, {**dados.model_dump(), "status": "ativo"})
        else:
            self._validar_disciplinas(dados.disciplina_ids)
            professor_id = self.repo.create_professor(dados.model_dump())
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="professor_cadastrado",
            entidade="professores",
            entidade_id=professor_id,
            dados_depois={"usuario_id": dados.usuario_id, "polo_id": dados.polo_id},
            ip=ip,
        )
        self._garantir_perfil_professor(dados.usuario_id, actor_id, ip)
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
            if "disciplina_ids" in update_dict:
                self._validar_disciplinas(update_dict["disciplina_ids"])
            self.repo.update_professor(professor_id, update_dict)
            self.repo.record_audit_log(
                usuario_id=actor_id,
                acao="professor_atualizado",
                entidade="professores",
                entidade_id=professor_id,
                dados_depois=update_dict,
                ip=ip,
            )
        if novo_usuario_id:
            self._garantir_perfil_professor(str(novo_usuario_id), actor_id, ip)
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

    def _validar_disciplinas(self, disciplina_ids: list[Any]) -> None:
        invalidas = self.repo.get_invalid_disciplina_ids([str(item) for item in disciplina_ids])
        if invalidas:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Uma ou mais disciplinas vinculadas não foram encontradas.",
            )

    def _garantir_perfil_professor(
        self, usuario_id: str, actor_id: Optional[str], ip: Optional[str]
    ) -> None:
        """Quem está no Corpo Docente tem perfil `professor` em Usuários."""
        anterior = self.repo.set_usuario_perfil(usuario_id, "professor")
        if anterior is None:
            return
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="usuario_perfil_alterado",
            entidade="usuarios",
            entidade_id=usuario_id,
            dados_antes={"perfil": anterior or None},
            dados_depois={"perfil": "professor"},
            ip=ip,
        )

    def _build_response(self, row: Dict[str, Any]) -> ProfessorResponse:
        valor = row.get("valor_hora_aula")
        materias: list[str] = []
        for materia in [*(row.get("materias") or []), *(row.get("disciplina_nomes") or [])]:
            nome = str(materia).strip()
            if nome and nome.casefold() not in {item.casefold() for item in materias}:
                materias.append(nome)
        return ProfessorResponse(
            id=str(row["id"]),
            usuario_id=str(row["usuario_id"]) if row.get("usuario_id") else None,
            nome=row.get("nome"),
            email=row.get("email"),
            polo_id=str(row["polo_id"]) if row.get("polo_id") else None,
            polo_nome=row.get("polo_nome"),
            escola_id=str(row["escola_id"]) if row.get("escola_id") else None,
            escola_nome=row.get("escola_nome"),
            materias=materias,
            disciplina_ids=[str(item) for item in (row.get("disciplina_ids") or [])],
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
