"""Camada de serviço (regras de negócio) do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.professores.repository import (
    ProfessoresRepositoryInterface,
    get_professores_repository,
    lotacao_cobre_unidade,
)
from app.modules.professores.schemas import (
    LotacaoInput,
    LotacaoItem,
    MessageResponse,
    ProfessorDisponivel,
    ProfessorDisponiveisResponse,
    ProfessorCreateRequest,
    ProfessorConteudosResponse,
    ProfessorDisciplinaListResponse,
    ProfessorDetalheResponse,
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

    def get_detalhe(
        self, professor: ProfessorResponse, polo_id: Optional[str], escola_id: Optional[str]
    ) -> ProfessorDetalheResponse:
        disciplinas = self.repo.list_disciplinas_cadastro(professor.id)
        turmas: Dict[str, Dict[str, Any]] = {}
        alunos_por_turma: Dict[str, set[str]] = {}
        for row in self.repo.list_turmas_alunos(professor.id, polo_id, escola_id):
            turma_id = str(row["turma_id"])
            turma = turmas.setdefault(turma_id, {
                "id": turma_id,
                "nome": row["turma_nome"],
                "polo_id": row.get("polo_id"),
                "polo_nome": row.get("polo_nome"),
                "escola_id": row.get("escola_id"),
                "escola_nome": row.get("escola_nome"),
                "alunos": [],
            })
            aluno_id = row.get("aluno_id")
            vistos = alunos_por_turma.setdefault(turma_id, set())
            if aluno_id and str(aluno_id) not in vistos:
                vistos.add(str(aluno_id))
                turma["alunos"].append({
                    "id": str(aluno_id), "nome": row.get("aluno_nome"),
                    "numero_matricula": row.get("numero_matricula"), "email": row.get("aluno_email"),
                    "ultimo_acesso": row.get("aluno_ultimo_acesso"),
                    "ultima_presenca": row.get("ultima_presenca_data"),
                    "ultima_presenca_numero": row.get("ultima_presenca_numero"),
                })
        return ProfessorDetalheResponse(professor=professor, disciplinas=disciplinas, turmas=list(turmas.values()))

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
        self._lotar_na_turma(professor_id, turma, current_user, ip)
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

    # ------------------------------------------------------------------
    # Lotações (N polos / N escolas)
    # ------------------------------------------------------------------

    @staticmethod
    def professor_visivel(
        lotacoes: List[Any], polo_id: Optional[str], escola_id: Optional[str]
    ) -> bool:
        """RN-09: o gestor vê o professor que tem alguma lotação na sua unidade."""

        def campo(lotacao: Any, nome: str) -> Optional[str]:
            valor = lotacao.get(nome) if isinstance(lotacao, dict) else getattr(lotacao, nome, None)
            return str(valor) if valor else None

        if polo_id and not any(campo(l, "polo_id") == str(polo_id) for l in lotacoes):
            return False
        if escola_id and not any(campo(l, "escola_id") == str(escola_id) for l in lotacoes):
            return False
        return True

    def list_disponiveis(self, search: Optional[str], limit: int = 20) -> ProfessorDisponiveisResponse:
        """Professores ativos de qualquer unidade, para associar a uma turma."""
        _, rows = self.repo.list_professores(search=search, status_filter="ativo", limit=limit, offset=0)
        return ProfessorDisponiveisResponse(
            items=[
                ProfessorDisponivel(
                    id=str(row["id"]),
                    nome=row.get("nome"),
                    email=row.get("email"),
                    lotacoes=self._lotacoes_response(row.get("lotacoes")),
                )
                for row in rows
            ]
        )

    def adicionar_lotacao(
        self,
        professor_id: str,
        dados: LotacaoInput,
        current_user: UserResponse,
        ip: Optional[str] = None,
    ) -> ProfessorResponse:
        if not self.repo.get_professor(professor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
        polo_id, escola_id = self._resolver_unidade(dados)
        self._exigir_unidade_do_gestor(current_user, polo_id, escola_id)
        lotacao, criada = self.repo.add_lotacao(professor_id, polo_id, escola_id, current_user.id)
        if criada:
            self.repo.record_audit_log(
                usuario_id=current_user.id,
                acao="professor_lotacao_incluida",
                entidade="professor_lotacoes",
                entidade_id=str(lotacao["id"]),
                dados_depois={"professor_id": professor_id, "polo_id": polo_id, "escola_id": escola_id},
                ip=ip,
            )
        return self.get_professor(professor_id)

    def remover_lotacao(
        self,
        professor_id: str,
        lotacao_id: str,
        current_user: UserResponse,
        ip: Optional[str] = None,
    ) -> ProfessorResponse:
        lotacoes = self.repo.list_lotacoes(professor_id)
        alvo = next((l for l in lotacoes if str(l["id"]) == str(lotacao_id)), None)
        if not alvo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lotação não encontrada.")
        self._exigir_unidade_do_gestor(current_user, alvo["polo_id"], alvo.get("escola_id"))
        restantes = [l for l in lotacoes if str(l["id"]) != str(lotacao_id)]
        if not restantes:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="O professor precisa de ao menos um polo. Inclua outro antes de remover este.",
            )
        for unidade in self.repo.list_unidades_turmas_ativas(professor_id):
            polo_id, escola_id = unidade.get("polo_id"), unidade.get("escola_id")
            coberta_pelo_alvo = lotacao_cobre_unidade(alvo, polo_id, escola_id)
            coberta_por_outra = any(lotacao_cobre_unidade(l, polo_id, escola_id) for l in restantes)
            if coberta_pelo_alvo and not coberta_por_outra:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail=(
                        "O professor ainda leciona em turmas desta unidade. "
                        "Arquive os vínculos com as turmas antes de remover a lotação."
                    ),
                )
        self.repo.remove_lotacao(professor_id, lotacao_id)
        self.repo.record_audit_log(
            usuario_id=current_user.id,
            acao="professor_lotacao_removida",
            entidade="professor_lotacoes",
            entidade_id=str(lotacao_id),
            dados_antes={
                "professor_id": professor_id,
                "polo_id": alvo["polo_id"],
                "escola_id": alvo.get("escola_id"),
            },
            ip=ip,
        )
        return self.get_professor(professor_id)

    def _lotar_na_turma(
        self, professor_id: str, turma: Dict[str, Any], current_user: UserResponse, ip: Optional[str]
    ) -> None:
        """Quem leciona numa turma passa a ser lotado no polo/escola dela."""
        escola_id = str(turma["escola_id"]) if turma.get("escola_id") else None
        polo_id = turma.get("polo_id") or (self.repo.get_escola_polo(escola_id) if escola_id else None)
        if not polo_id:
            return
        lotacao, criada = self.repo.add_lotacao(professor_id, str(polo_id), escola_id, current_user.id)
        if criada:
            self.repo.record_audit_log(
                usuario_id=current_user.id,
                acao="professor_lotacao_incluida",
                entidade="professor_lotacoes",
                entidade_id=str(lotacao["id"]),
                dados_depois={
                    "professor_id": professor_id,
                    "polo_id": str(polo_id),
                    "escola_id": escola_id,
                    "origem": "vinculo_turma",
                    "turma_id": str(turma.get("id")),
                },
                ip=ip,
            )

    def _resolver_unidade(self, dados: LotacaoInput) -> Tuple[str, Optional[str]]:
        """Valida polo/escola; o polo pode ser deduzido da escola."""
        polo_id = str(dados.polo_id) if dados.polo_id else None
        escola_id = str(dados.escola_id) if dados.escola_id else None
        if escola_id:
            polo_da_escola = self.repo.get_escola_polo(escola_id)
            if not polo_da_escola:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Escola não encontrada.")
            if polo_id and polo_id != polo_da_escola:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="A escola informada não pertence ao polo selecionado.",
                )
            polo_id = polo_da_escola
        if not polo_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Informe o polo da lotação.")
        if not escola_id and not self.repo.polo_existe(polo_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Polo não encontrado.")
        return polo_id, escola_id

    def _normalizar_lotacoes(self, lotacoes: List[LotacaoInput]) -> List[Dict[str, Any]]:
        resultado: List[Dict[str, Any]] = []
        for item in lotacoes:
            polo_id, escola_id = self._resolver_unidade(item)
            unidade = {"polo_id": polo_id, "escola_id": escola_id}
            if unidade not in resultado:
                resultado.append(unidade)
        return resultado

    @staticmethod
    def _exigir_unidade_do_gestor(
        current_user: UserResponse, polo_id: str, escola_id: Optional[str]
    ) -> None:
        """Admin altera qualquer lotação; gestor só a da própria unidade."""
        perfil = perfil_do_usuario(current_user)
        if perfil == "admin":
            return
        if perfil == "polo" and current_user.polo_id and str(polo_id) == str(current_user.polo_id):
            return
        if (
            perfil == "escola"
            and current_user.escola_id
            and escola_id
            and str(escola_id) == str(current_user.escola_id)
        ):
            return
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Você só pode incluir ou remover a sua própria unidade.",
        )

    @staticmethod
    def _lotacoes_response(rows: Any) -> List[LotacaoItem]:
        return [
            LotacaoItem(
                id=str(row["id"]),
                polo_id=str(row["polo_id"]),
                polo_nome=row.get("polo_nome"),
                escola_id=str(row["escola_id"]) if row.get("escola_id") else None,
                escola_nome=row.get("escola_nome"),
            )
            for row in (rows or [])
        ]

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

        payload = dados.model_dump(exclude={"horas_totais", "quantidade_aulas", "lotacoes"})
        if dados.lotacoes is not None:
            payload["lotacoes"] = self._normalizar_lotacoes(dados.lotacoes)
        elif dados.polo_id or dados.escola_id:
            payload["lotacoes"] = self._normalizar_lotacoes(
                [LotacaoInput(polo_id=dados.polo_id, escola_id=dados.escola_id)]
            )
        payload["criado_por"] = actor_id

        if existente:
            # Registro criado automaticamente pela tela de Usuários (ou desativado):
            # completa-o em vez de duplicar.
            professor_id = str(existente["id"])
            self._validar_disciplinas(dados.disciplina_ids)
            self.repo.update_professor(professor_id, {**payload, "status": "ativo"})
        else:
            self._validar_disciplinas(dados.disciplina_ids)
            professor_id = self.repo.create_professor(payload)
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="professor_cadastrado",
            entidade="professores",
            entidade_id=professor_id,
            dados_depois={"usuario_id": dados.usuario_id, "lotacoes": payload.get("lotacoes")},
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
            k: v for k, v in dados.model_dump(
                exclude_unset=True, exclude={"horas_totais", "quantidade_aulas", "lotacoes"}
            ).items() if v is not None
        }
        if dados.lotacoes is not None:
            update_dict["lotacoes"] = self._normalizar_lotacoes(dados.lotacoes)
        elif update_dict.get("polo_id") or update_dict.get("escola_id"):
            # Cliente antigo (um polo/escola): inclui a unidade sem apagar as demais.
            polo_id, escola_id = self._resolver_unidade(
                LotacaoInput(polo_id=update_dict.get("polo_id"), escola_id=update_dict.get("escola_id"))
            )
            self.repo.add_lotacao(professor_id, polo_id, escola_id, actor_id)

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
            self.repo.update_professor(professor_id, {**update_dict, "criado_por": actor_id})
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
            lotacoes=self._lotacoes_response(row.get("lotacoes")),
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
