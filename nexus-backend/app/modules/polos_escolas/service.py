"""Camada de serviço (regras de negócio) do módulo `polos_escolas`."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.modules.polos_escolas import dashboard as dash
from app.modules.polos_escolas import licencas as lic
from app.modules.polos_escolas.repository import (
    PolosEscolasRepositoryInterface,
    get_polos_escolas_repository,
)
from app.modules.polos_escolas.schemas import (
    AlertaListResponse,
    AlunoCreateRequest,
    AlunoDesistenteListResponse,
    AlunoDesistenteResponse,
    AlunoDrilldownEscolaListResponse,
    AlunoDrilldownEscolaResponse,
    AlunoPoloListResponse,
    AlunoPoloResponse,
    AlunoUpdateRequest,
    AnexoAulaResponse,
    AtaResponse,
    BoletoListResponse,
    BoletoResponse,
    CalendarioEadCreateRequest,
    CalendarioEadResponse,
    ChamadaAlunoResponse,
    ChamadaResponse,
    CompraLicencaListResponse,
    CompraLicencaResponse,
    DashboardDrilldownResponse,
    DashboardEscolaKpisResponse,
    DashboardFunilResponse,
    DashboardPoloKpisResponse,
    DashboardTreemapResponse,
    DonutResponse,
    EnderecoSchema,
    EscolaCreateRequest,
    EscolaListResponse,
    EscolaResponse,
    EscolaUpdateRequest,
    EvolucaoMesItem,
    EvolucaoResponse,
    FeedPostCreateRequest,
    FeedPostResponse,
    LembreteCreateRequest,
    LembreteResponse,
    LicencaCompraRequest,
    LicencaDevolverAlunoRequest,
    LicencaDevolverEscolaRequest,
    LicencaDistribuirRequest,
    LicencaVenderRequest,
    MessageResponse,
    MigracaoModalidadeRequest,
    MovimentacaoLicencaResponse,
    MovimentacaoListResponse,
    NotaCreateRequest,
    PerfilFotoResponse,
    PerfilSenhaUpdateRequest,
    PerfilUpdateRequest,
    PerfilUsuarioResponse,
    PoloCreateRequest,
    PoloListResponse,
    PoloResponse,
    PoloUpdateRequest,
    ProfessorCardResponse,
    ProfessorCreateRequest,
    ProfessorDashboardResponse,
    ProfessorListItemResponse,
    ProfessorListResponse,
    ProfessorUpdateRequest,
    RelatorioDrilldownResponse,
    RequisicaoListResponse,
    RequisicaoResponse,
    TopAlunoResponse,
    TreinamentoInscricaoResponse,
    TreinamentoResponse,
    TrocaPoloRequest,
)

# RN-08: perfis autorizados a publicar no feed pedagógico
_PERFIS_FEED_AUTORIZADOS = {"professor", "coordenador_polo", "secretario_escola", "admin", "diretor"}

# RN-05: 1 ano sem movimentação = churn
_DIAS_CHURN = 365


class PolosEscolasService:
    def __init__(self, repo: Optional[PolosEscolasRepositoryInterface] = None) -> None:
        self._repo = repo

    @property
    def repo(self) -> PolosEscolasRepositoryInterface:
        return self._repo or get_polos_escolas_repository()

    # ------------------------------------------------------------------
    # Helpers de montagem
    # ------------------------------------------------------------------

    def _endereco_from(self, data: Dict[str, Any]) -> EnderecoSchema:
        return EnderecoSchema(
            logradouro=data.get("logradouro", "") or "",
            numero=data.get("numero", "") or "",
            bairro=data.get("bairro", "") or "",
            cidade=data.get("cidade", "") or "",
            estado=data.get("estado", "") or "",
            cep=data.get("cep", "") or "",
        )

    def _build_polo_response(self, polo: Dict[str, Any]) -> PoloResponse:
        coordenador = None
        coord_id = polo.get("coordenador_usuario_id")
        if coord_id:
            coordenador = self.repo.get_usuario_by_id(str(coord_id))
        return PoloResponse(
            id=str(polo["id"]),
            nome=polo["nome"],
            endereco=self._endereco_from(polo),
            status=polo.get("status", "ativo"),
            coordenador_id=str(coord_id) if coord_id else None,
            coordenador_nome=coordenador.get("nome") if coordenador else None,
            coordenador_email=coordenador.get("email") if coordenador else None,
            criado_em=polo.get("criado_em"),
            atualizado_em=polo.get("atualizado_em"),
        )

    def _build_escola_response(self, escola: Dict[str, Any]) -> EscolaResponse:
        secretario = None
        sec_id = escola.get("secretario_usuario_id")
        if sec_id:
            secretario = self.repo.get_usuario_by_id(str(sec_id))
        return EscolaResponse(
            id=str(escola["id"]),
            polo_id=str(escola["polo_id"]),
            nome=escola["nome"],
            endereco=self._endereco_from(escola),
            status=escola.get("status", "ativo"),
            secretario_id=str(sec_id) if sec_id else None,
            secretario_nome=secretario.get("nome") if secretario else None,
            secretario_email=secretario.get("email") if secretario else None,
            criado_em=escola.get("criado_em"),
            atualizado_em=escola.get("atualizado_em"),
        )

    def _validar_email_cpf_unicos(self, email: str, cpf: str) -> None:
        if self.repo.get_usuario_by_email(email):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"O e-mail '{email}' já está em uso")
        if self.repo.get_usuario_by_cpf(cpf):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="O CPF informado já está cadastrado")

    # ------------------------------------------------------------------
    # 1. Polos (RN-01)
    # ------------------------------------------------------------------

    def create_polo(self, dados: PoloCreateRequest, actor_id: Optional[str], ip: Optional[str]) -> PoloResponse:
        # RN-01: cadastro do Polo cria o usuário coordenador na mesma transação
        self._validar_email_cpf_unicos(dados.coordenador_email, dados.coordenador_cpf)

        perfil_id = self.repo.get_perfil_id_by_nome("coordenador_polo")
        if not perfil_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Perfil 'coordenador_polo' não configurado")

        endereco = dados.endereco or EnderecoSchema()
        polo_id = self.repo.create_polo(
            {
                "nome": dados.nome,
                "logradouro": endereco.logradouro,
                "numero": endereco.numero,
                "bairro": endereco.bairro,
                "cidade": endereco.cidade,
                "estado": endereco.estado,
                "cep": endereco.cep,
            }
        )

        # RN-01: usuário coordenador criado automaticamente, sem endpoint separado
        coordenador_id = self.repo.create_usuario(
            {
                "nome": dados.coordenador_nome,
                "email": dados.coordenador_email,
                "cpf": dados.coordenador_cpf,
                "senha_hash": hash_password(dados.coordenador_senha),
                "senha_algoritmo": "argon2id",
                "perfil_id": perfil_id,
                "polo_id": polo_id,
            }
        )
        self.repo.update_polo(polo_id, {"coordenador_usuario_id": coordenador_id})

        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="polo_criado",
            entidade="polos",
            entidade_id=polo_id,
            dados_depois={"nome": dados.nome, "coordenador_id": coordenador_id},
            ip=ip,
        )
        return self.get_polo(polo_id)

    def update_polo(
        self, polo_id: str, dados: PoloUpdateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> PoloResponse:
        polo = self.repo.get_polo(polo_id)
        if not polo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Polo não encontrado")

        update_dict: Dict[str, Any] = {}
        if dados.nome is not None:
            update_dict["nome"] = dados.nome
        if dados.endereco is not None:
            update_dict.update(dados.endereco.model_dump())
        if dados.status is not None:
            update_dict["status"] = dados.status
        if update_dict:
            self.repo.update_polo(polo_id, update_dict)

        # RN-01: sincroniza dados do coordenador ao editar o Polo
        coord_id = polo.get("coordenador_usuario_id")
        if coord_id:
            coord_update: Dict[str, Any] = {}
            if dados.coordenador_nome is not None:
                coord_update["nome"] = dados.coordenador_nome
            if dados.coordenador_cpf is not None:
                coord_update["cpf"] = dados.coordenador_cpf
            if dados.coordenador_email is not None:
                coord_update["email"] = dados.coordenador_email
            if dados.coordenador_senha:
                coord_update["senha_hash"] = hash_password(dados.coordenador_senha)
                coord_update["senha_algoritmo"] = "argon2id"
            if coord_update:
                self.repo.update_usuario(str(coord_id), coord_update)

        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="polo_atualizado",
            entidade="polos",
            entidade_id=polo_id,
            dados_antes=polo,
            dados_depois=update_dict,
            ip=ip,
        )
        return self.get_polo(polo_id)

    def delete_polo(self, polo_id: str, actor_id: Optional[str], ip: Optional[str]) -> MessageResponse:
        polo = self.repo.get_polo(polo_id)
        if not polo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Polo não encontrado")
        self.repo.update_polo(polo_id, {"status": "inativo"})
        # RN-01: desativa o usuário coordenador vinculado
        coord_id = polo.get("coordenador_usuario_id")
        if coord_id:
            self.repo.update_usuario(str(coord_id), {"status": "inativo"})
        self.repo.record_audit_log(
            usuario_id=actor_id, acao="polo_desativado", entidade="polos", entidade_id=polo_id, ip=ip
        )
        return MessageResponse(message="Polo desativado com sucesso")

    def get_polo(self, polo_id: str) -> PoloResponse:
        polo = self.repo.get_polo(polo_id)
        if not polo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Polo não encontrado")
        return self._build_polo_response(polo)

    def list_polos(self, limit: int = 50, offset: int = 0) -> PoloListResponse:
        total, items = self.repo.list_polos(limit=limit, offset=offset)
        return PoloListResponse(
            total=total, items=[self._build_polo_response(p) for p in items], limit=limit, offset=offset
        )

    # ------------------------------------------------------------------
    # 2. Escolas (RN-01)
    # ------------------------------------------------------------------

    def create_escola(
        self, polo_id: str, dados: EscolaCreateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> EscolaResponse:
        if not self.repo.get_polo(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Polo não encontrado")

        # RN-01: cadastro da Escola cria o usuário secretário na mesma transação
        self._validar_email_cpf_unicos(dados.secretario_email, dados.secretario_cpf)

        perfil_id = self.repo.get_perfil_id_by_nome("secretario_escola")
        if not perfil_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Perfil 'secretario_escola' não configurado")

        endereco = dados.endereco or EnderecoSchema()
        escola_id = self.repo.create_escola(
            {
                "polo_id": polo_id,
                "nome": dados.nome,
                "logradouro": endereco.logradouro,
                "numero": endereco.numero,
                "bairro": endereco.bairro,
                "cidade": endereco.cidade,
                "estado": endereco.estado,
                "cep": endereco.cep,
            }
        )

        secretario_id = self.repo.create_usuario(
            {
                "nome": dados.secretario_nome,
                "email": dados.secretario_email,
                "cpf": dados.secretario_cpf,
                "senha_hash": hash_password(dados.secretario_senha),
                "senha_algoritmo": "argon2id",
                "perfil_id": perfil_id,
                "polo_id": polo_id,
                "escola_id": escola_id,
            }
        )
        self.repo.update_escola(escola_id, {"secretario_usuario_id": secretario_id})

        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="escola_criada",
            entidade="escolas",
            entidade_id=escola_id,
            dados_depois={"nome": dados.nome, "polo_id": polo_id, "secretario_id": secretario_id},
            ip=ip,
        )
        return self.get_escola(escola_id)

    def update_escola(
        self, escola_id: str, dados: EscolaUpdateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> EscolaResponse:
        escola = self.repo.get_escola(escola_id)
        if not escola:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")

        update_dict: Dict[str, Any] = {}
        if dados.nome is not None:
            update_dict["nome"] = dados.nome
        if dados.endereco is not None:
            update_dict.update(dados.endereco.model_dump())
        if dados.status is not None:
            update_dict["status"] = dados.status
        if update_dict:
            self.repo.update_escola(escola_id, update_dict)

        sec_id = escola.get("secretario_usuario_id")
        if sec_id:
            sec_update: Dict[str, Any] = {}
            if dados.secretario_nome is not None:
                sec_update["nome"] = dados.secretario_nome
            if dados.secretario_cpf is not None:
                sec_update["cpf"] = dados.secretario_cpf
            if dados.secretario_email is not None:
                sec_update["email"] = dados.secretario_email
            if dados.secretario_senha:
                sec_update["senha_hash"] = hash_password(dados.secretario_senha)
                sec_update["senha_algoritmo"] = "argon2id"
            if sec_update:
                self.repo.update_usuario(str(sec_id), sec_update)

        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="escola_atualizada",
            entidade="escolas",
            entidade_id=escola_id,
            dados_antes=escola,
            dados_depois=update_dict,
            ip=ip,
        )
        return self.get_escola(escola_id)

    def get_escola(self, escola_id: str) -> EscolaResponse:
        escola = self.repo.get_escola(escola_id)
        if not escola:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
        return self._build_escola_response(escola)

    def list_escolas(self, polo_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> EscolaListResponse:
        total, items = self.repo.list_escolas(polo_id=polo_id, limit=limit, offset=offset)
        return EscolaListResponse(
            total=total, items=[self._build_escola_response(e) for e in items], limit=limit, offset=offset
        )

    # ------------------------------------------------------------------
    # 3. Dashboard do Polo (RN-03, RN-04)
    # ------------------------------------------------------------------

    def dashboard_kpis_polo(self, polo_id: str) -> DashboardPoloKpisResponse:
        self.get_polo(polo_id)
        return dash.calcular_kpis_polo(self.repo, polo_id)

    def dashboard_funil(self, polo_id: str) -> DashboardFunilResponse:
        self.get_polo(polo_id)
        return dash.calcular_funil(self.repo, polo_id)

    def dashboard_treemap(self, polo_id: str) -> DashboardTreemapResponse:
        self.get_polo(polo_id)
        return dash.calcular_treemap(self.repo, polo_id)

    def dashboard_drilldown(self, polo_id: str) -> DashboardDrilldownResponse:
        self.get_polo(polo_id)
        return dash.calcular_drilldown(self.repo, polo_id)

    def dashboard_alertas(self, polo_id: str) -> AlertaListResponse:
        self.get_polo(polo_id)
        itens = dash.calcular_alertas_polo(self.repo, polo_id)
        return AlertaListResponse(total=len(itens), items=itens)

    def relatorio_drilldown(self, polo_id: str) -> RelatorioDrilldownResponse:
        self.get_polo(polo_id)
        return dash.gerar_relatorio_drilldown(self.repo, polo_id)

    # ------------------------------------------------------------------
    # 4. Fluxo de Licenças (RN-02)
    # ------------------------------------------------------------------

    def comprar_licencas(
        self, polo_id: str, dados: LicencaCompraRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> MessageResponse:
        self.get_polo(polo_id)
        resultado = lic.comprar_licencas(self.repo, polo_id, dados, actor_id)
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="licencas_compradas",
            entidade="compras_licencas",
            entidade_id=resultado["compra_id"],
            dados_depois={"quantidade": dados.quantidade, "fornecedor": dados.fornecedor},
            ip=ip,
        )
        return MessageResponse(message=f"{dados.quantidade} licenças adquiridas com sucesso")

    def distribuir_licencas(
        self, polo_id: str, dados: LicencaDistribuirRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> MessageResponse:
        self.get_polo(polo_id)
        if not self.repo.get_escola(dados.escola_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
        mov_id = lic.distribuir_para_escola(self.repo, polo_id, dados, actor_id)
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="licencas_distribuidas",
            entidade="licencas_movimentacoes",
            entidade_id=mov_id,
            dados_depois={"escola_id": dados.escola_id, "quantidade": dados.quantidade},
            ip=ip,
        )
        return MessageResponse(message=f"{dados.quantidade} licenças distribuídas para a escola")

    def vender_licencas(
        self, escola_id: str, dados: LicencaVenderRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> MessageResponse:
        escola = self.repo.get_escola(escola_id)
        if not escola:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
        mov_id = lic.vender_para_aluno(self.repo, escola_id, escola.get("polo_id"), dados, actor_id)
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="licenca_vendida",
            entidade="licencas_movimentacoes",
            entidade_id=mov_id,
            dados_depois={"aluno_id": dados.aluno_id},
            ip=ip,
        )
        return MessageResponse(message="Licença vendida ao aluno com sucesso")

    def devolver_escola(
        self, escola_id: str, dados: LicencaDevolverEscolaRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> MessageResponse:
        escola = self.repo.get_escola(escola_id)
        if not escola:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
        mov_id = lic.devolver_de_escola_para_polo(self.repo, escola_id, escola["polo_id"], dados, actor_id)
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="licencas_devolvidas_polo",
            entidade="licencas_movimentacoes",
            entidade_id=mov_id,
            dados_depois={"quantidade": dados.quantidade},
            ip=ip,
        )
        return MessageResponse(message=f"{dados.quantidade} licenças devolvidas ao Polo")

    def devolver_aluno(self, aluno_id: str, actor_id: Optional[str], ip: Optional[str]) -> MessageResponse:
        mov_id = lic.devolver_de_aluno_para_escola(self.repo, aluno_id, actor_id)
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="licenca_devolvida_escola",
            entidade="licencas_movimentacoes",
            entidade_id=mov_id,
            dados_depois={"aluno_id": aluno_id},
            ip=ip,
        )
        return MessageResponse(message="Licença devolvida à escola com sucesso")

    def list_movimentacoes(self, polo_id: str, limit: int = 50, offset: int = 0) -> MovimentacaoListResponse:
        self.get_polo(polo_id)
        total, items = self.repo.list_movimentacoes(polo_id, limit=limit, offset=offset)
        return MovimentacaoListResponse(
            total=total,
            items=[MovimentacaoLicencaResponse(**{**m, "id": str(m["id"])}) for m in items],
            limit=limit,
            offset=offset,
        )

    # ------------------------------------------------------------------
    # 5. Dashboard da Escola
    # ------------------------------------------------------------------

    def dashboard_kpis_escola(self, escola_id: str) -> DashboardEscolaKpisResponse:
        self.get_escola(escola_id)
        return dash.calcular_kpis_escola(self.repo, escola_id)

    def dashboard_donut(self, escola_id: str) -> DonutResponse:
        kpis = self.dashboard_kpis_escola(escola_id)
        return DonutResponse(vendidas=kpis.licencas_vendidas, nao_vendidas=kpis.licencas_nao_vendidas)

    def top_alunos_escola(self, escola_id: str, limit: int = 10) -> List[TopAlunoResponse]:
        self.get_escola(escola_id)
        itens = self.repo.top_alunos_escola(escola_id, limit=limit)
        return [
            TopAlunoResponse(
                aluno_id=str(i["aluno_id"]),
                nome=f"{i.get('nome', '')} {i.get('sobrenome', '')}".strip(),
                qtd_licencas=i["qtd_licencas"],
            )
            for i in itens
        ]

    def alunos_drilldown_escola(
        self, escola_id: str, limit: int = 50, offset: int = 0
    ) -> AlunoDrilldownEscolaListResponse:
        self.get_escola(escola_id)
        total, items = self.repo.list_alunos_licenciados_escola(escola_id, limit=limit, offset=offset)
        return AlunoDrilldownEscolaListResponse(
            total=total,
            items=[
                AlunoDrilldownEscolaResponse(
                    aluno_id=str(i["aluno_id"]),
                    nome=f"{i.get('nome', '')} {i.get('sobrenome', '')}".strip(),
                    qtd_licencas=1,
                    data_venda_ativacao=i.get("ativada_em"),
                    status=i["status"],
                )
                for i in items
            ],
            limit=limit,
            offset=offset,
        )

    def evolucao_escola(self, escola_id: str, meses: int = 12) -> EvolucaoResponse:
        self.get_escola(escola_id)
        itens = self.repo.evolucao_escola(escola_id, meses=meses)
        return EvolucaoResponse(
            escola_id=escola_id,
            items=[EvolucaoMesItem(ano=i["ano"], mes=i["mes"], vendidas=i["vendidas"], distribuidas=i["distribuidas"]) for i in itens],
        )

    def alertas_escola(self, escola_id: str) -> AlertaListResponse:
        self.get_escola(escola_id)
        itens = dash.calcular_alertas_escola(self.repo, escola_id)
        return AlertaListResponse(total=len(itens), items=itens)

    # ------------------------------------------------------------------
    # 6. Financeiro
    # ------------------------------------------------------------------

    def list_compras(
        self, polo_id: str, data_inicio: Optional[date], data_fim: Optional[date], limit: int, offset: int
    ) -> CompraLicencaListResponse:
        self.get_polo(polo_id)
        total, items = self.repo.list_compras(polo_id, data_inicio, data_fim, limit, offset)
        return CompraLicencaListResponse(
            total=total, items=[CompraLicencaResponse(**{**c, "id": str(c["id"])}) for c in items], limit=limit, offset=offset
        )

    def list_boletos(
        self, polo_id: str, data_inicio: Optional[date], data_fim: Optional[date], limit: int, offset: int
    ) -> BoletoListResponse:
        self.get_polo(polo_id)
        total, items = self.repo.list_boletos(polo_id, data_inicio, data_fim, limit, offset)
        return BoletoListResponse(
            total=total, items=[BoletoResponse(**{**b, "id": str(b["id"])}) for b in items], limit=limit, offset=offset
        )

    def get_boleto(self, polo_id: str, boleto_id: str) -> Dict[str, Any]:
        self.get_polo(polo_id)
        boleto = self.repo.get_boleto(boleto_id)
        if not boleto or str(boleto.get("polo_id")) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Boleto não encontrado")
        return boleto

    # ------------------------------------------------------------------
    # 7. Alunos do Polo
    # ------------------------------------------------------------------

    def list_alunos_polo(
        self,
        polo_id: str,
        q: Optional[str],
        escola_id: Optional[str],
        status_filter: Optional[str],
        limit: int,
        offset: int,
    ) -> AlunoPoloListResponse:
        self.get_polo(polo_id)
        total, items = self.repo.list_alunos_polo(polo_id, q, escola_id, status_filter, limit, offset)
        out = []
        for a in items:
            presentes, total_aulas = self.repo.contar_presencas_aluno(str(a["id"]))
            out.append(
                AlunoPoloResponse(
                    id=str(a["id"]),
                    nome=a.get("nome", ""),
                    sobrenome=a.get("sobrenome", ""),
                    email=a.get("email"),
                    cpf=a.get("cpf"),
                    escola_id=str(a["escola_id"]) if a.get("escola_id") else None,
                    modalidade=a.get("modalidade", "polo"),
                    status=a.get("status", "ativo"),
                    quantidade_presencas=presentes,
                    percentual_presenca=round((presentes / total_aulas) * 100, 2) if total_aulas else 0.0,
                    criado_em=a.get("criado_em"),
                )
            )
        return AlunoPoloListResponse(total=total, items=out, limit=limit, offset=offset)

    def update_aluno(
        self, polo_id: str, aluno_id: str, dados: AlunoUpdateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> MessageResponse:
        aluno = self.repo.get_aluno_usuario(aluno_id)
        if not aluno or str(aluno.get("polo_id")) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado neste Polo")
        update_dict = {k: v for k, v in dados.model_dump(exclude_unset=True).items() if v is not None}
        if update_dict:
            self.repo.update_usuario(aluno_id, update_dict)
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="aluno_atualizado",
            entidade="usuarios",
            entidade_id=aluno_id,
            dados_antes=aluno,
            dados_depois=update_dict,
            ip=ip,
        )
        return MessageResponse(message="Aluno atualizado com sucesso")

    def registrar_nota(
        self, polo_id: str, aluno_id: str, dados: NotaCreateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> MessageResponse:
        aluno = self.repo.get_aluno_usuario(aluno_id)
        if not aluno or str(aluno.get("polo_id")) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado neste Polo")
        nota_id = self.repo.registrar_nota(
            {"aluno_id": aluno_id, "materia_id": dados.materia_id, "valor": dados.valor, "descricao": dados.descricao}
        )
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="nota_registrada",
            entidade="notas_alunos",
            entidade_id=nota_id,
            dados_depois={"aluno_id": aluno_id, "valor": dados.valor},
            ip=ip,
        )
        return MessageResponse(message="Nota registrada com sucesso")

    def create_aluno(
        self, polo_id: str, dados: AlunoCreateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> AlunoPoloResponse:
        self.get_polo(polo_id)
        if self.repo.get_usuario_by_email(dados.email):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"O e-mail '{dados.email}' já está em uso")
        if self.repo.get_usuario_by_cpf(dados.cpf):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="O CPF informado já está cadastrado")
        perfil_id = self.repo.get_perfil_id_by_nome("aluno")
        if not perfil_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Perfil 'aluno' não configurado")

        aluno_id = self.repo.create_aluno(
            {
                "nome": dados.nome,
                "sobrenome": dados.sobrenome,
                "cpf": dados.cpf,
                "email": dados.email,
                "senha_hash": hash_password(str(uuid_token())),
                "senha_algoritmo": "argon2id",
                "perfil_id": perfil_id,
                "polo_id": polo_id,
                "escola_id": dados.escola_id,
                "modalidade": dados.modalidade,
            }
        )
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="aluno_cadastrado",
            entidade="usuarios",
            entidade_id=aluno_id,
            dados_depois={"nome": dados.nome, "modalidade": dados.modalidade},
            ip=ip,
        )
        return AlunoPoloResponse(
            id=aluno_id,
            nome=dados.nome,
            sobrenome=dados.sobrenome or "",
            email=dados.email,
            cpf=dados.cpf,
            escola_id=dados.escola_id,
            modalidade=dados.modalidade,
            status="ativo",
            quantidade_presencas=0,
            percentual_presenca=0.0,
            criado_em=None,
        )

    def solicitar_troca_polo(
        self, polo_id: str, aluno_id: str, dados: TrocaPoloRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> RequisicaoResponse:
        """RN-05: só permite troca sem nova matrícula se < 1 ano sem movimentação."""
        aluno = self.repo.get_aluno_usuario(aluno_id)
        if not aluno or str(aluno.get("polo_id")) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado neste Polo")

        referencia = aluno.get("atualizado_em") or aluno.get("criado_em")
        if referencia and _dias_desde(referencia) >= _DIAS_CHURN:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Aluno sem movimentação há mais de 1 ano: deve ser tratado como desistente (RN-05)",
            )
        if not self.repo.get_polo(dados.polo_destino_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Polo de destino não encontrado")

        req_id = self.repo.create_requisicao(
            {
                "aluno_id": aluno_id,
                "tipo": "troca_polo",
                "polo_origem_id": polo_id,
                "polo_destino_id": dados.polo_destino_id,
                "solicitado_por": actor_id,
            }
        )
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="requisicao_troca_polo",
            entidade="requisicoes_troca",
            entidade_id=req_id,
            dados_depois={"aluno_id": aluno_id, "polo_destino_id": dados.polo_destino_id},
            ip=ip,
        )
        return RequisicaoResponse(
            id=req_id,
            aluno_id=aluno_id,
            tipo="troca_polo",
            polo_origem_id=polo_id,
            polo_destino_id=dados.polo_destino_id,
            status="pendente",
            solicitado_por=actor_id,
        )

    def solicitar_migracao_modalidade(
        self,
        polo_id: str,
        aluno_id: str,
        dados: MigracaoModalidadeRequest,
        actor_id: Optional[str],
        ip: Optional[str],
    ) -> RequisicaoResponse:
        """RN-06: Migração de Modalidade (Polo <-> EAD)."""
        aluno = self.repo.get_aluno_usuario(aluno_id)
        if not aluno or str(aluno.get("polo_id")) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado neste Polo")

        req_id = self.repo.create_requisicao(
            {
                "aluno_id": aluno_id,
                "tipo": "migracao_modalidade",
                "polo_origem_id": polo_id,
                "modalidade_destino": dados.modalidade_destino,
                "solicitado_por": actor_id,
            }
        )
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="requisicao_migracao_modalidade",
            entidade="requisicoes_troca",
            entidade_id=req_id,
            dados_depois={"aluno_id": aluno_id, "modalidade_destino": dados.modalidade_destino},
            ip=ip,
        )
        return RequisicaoResponse(
            id=req_id,
            aluno_id=aluno_id,
            tipo="migracao_modalidade",
            polo_origem_id=polo_id,
            modalidade_destino=dados.modalidade_destino,
            status="pendente",
            solicitado_por=actor_id,
        )

    def list_requisicoes(
        self, polo_id: str, tipo: Optional[str], status_filter: Optional[str], limit: int, offset: int
    ) -> RequisicaoListResponse:
        self.get_polo(polo_id)
        total, items = self.repo.list_requisicoes(polo_id, tipo, status_filter, limit, offset)
        return RequisicaoListResponse(
            total=total, items=[RequisicaoResponse(**{**r, "id": str(r["id"])}) for r in items], limit=limit, offset=offset
        )

    def list_alunos_desistentes(self, polo_id: str) -> AlunoDesistenteListResponse:
        """RN-05: alunos > 1 ano sem movimentação são marcados como desistentes."""
        self.get_polo(polo_id)
        candidatos = self.repo.list_alunos_desistentes(polo_id, dias_limite=_DIAS_CHURN)
        itens = []
        for c in candidatos:
            self.repo.marcar_aluno_desistente(str(c["id"]))
            itens.append(
                AlunoDesistenteResponse(
                    aluno_id=str(c["id"]),
                    nome=f"{c.get('nome', '')} {c.get('sobrenome', '')}".strip(),
                    polo_id=polo_id,
                    ultima_movimentacao_em=c.get("atualizado_em") or c.get("criado_em"),
                    dias_sem_movimentacao=c["dias_sem_movimentacao"],
                )
            )
        return AlunoDesistenteListResponse(total=len(itens), items=itens)

    # ------------------------------------------------------------------
    # 8. Professores
    # ------------------------------------------------------------------

    def dashboard_professores(
        self, polo_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> ProfessorDashboardResponse:
        self.get_polo(polo_id)
        r = self.repo.dashboard_professores(polo_id, data_inicio, data_fim)
        return ProfessorDashboardResponse(**r)

    def list_professores(
        self, polo_id: str, data_inicio: Optional[date], data_fim: Optional[date], limit: int, offset: int
    ) -> ProfessorListResponse:
        self.get_polo(polo_id)
        total, items = self.repo.list_professores(polo_id, data_inicio, data_fim, limit, offset)
        return ProfessorListResponse(
            total=total,
            items=[
                ProfessorListItemResponse(
                    id=str(p["id"]),
                    usuario_id=str(p["usuario_id"]),
                    nome=p.get("nome", ""),
                    email=p.get("email"),
                    polo_id=str(p["polo_id"]) if p.get("polo_id") else None,
                    escola_id=str(p["escola_id"]) if p.get("escola_id") else None,
                    status=p.get("status", "ativo"),
                    quantidade_aulas=p.get("quantidade_aulas", 0),
                    horas_totais=p.get("horas_totais", 0),
                )
                for p in items
            ],
            limit=limit,
            offset=offset,
        )

    def get_professor_card(self, professor_id: str) -> ProfessorCardResponse:
        p = self.repo.get_professor(professor_id)
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
        return ProfessorCardResponse(
            id=str(p["id"]),
            usuario_id=str(p["usuario_id"]),
            nome=p.get("nome", ""),
            email=p.get("email"),
            polo_id=str(p["polo_id"]) if p.get("polo_id") else None,
            escola_id=str(p["escola_id"]) if p.get("escola_id") else None,
            materias=p.get("materias") or [],
            data_inicio=p.get("data_inicio"),
            quantidade_aulas=p.get("quantidade_aulas", 0),
            horas_totais=p.get("horas_totais", 0),
            valor_hora_aula=p.get("valor_hora_aula"),
            pix=p.get("pix"),
            conteudo_programatico=p.get("conteudo_programatico"),
            status=p.get("status", "ativo"),
        )

    def list_anexos_professor(
        self, professor_id: str, data_inicio: Optional[date], data_fim: Optional[date]
    ) -> List[AnexoAulaResponse]:
        itens = self.repo.list_anexos_professor(professor_id, data_inicio, data_fim)
        return [AnexoAulaResponse(**{**i, "id": str(i["id"]), "aula_id": str(i["aula_id"])}) for i in itens]

    def list_atas_professor(self, professor_id: str) -> List[AtaResponse]:
        itens = self.repo.list_atas_professor(professor_id)
        return [AtaResponse(**{**i, "id": str(i["id"]), "aula_id": str(i["aula_id"]), "professor_id": str(i["professor_id"])}) for i in itens]

    def list_chamada(self, professor_id: str, materia_id: str) -> ChamadaResponse:
        """RN-07: percentual = (presenças / total_aulas_previstas) * 100."""
        itens = self.repo.list_chamada(professor_id, materia_id)
        out = []
        for i in itens:
            total_previsto = i.get("total_previsto") or i.get("total_previsto") or 0
            presencas = i.get("presencas", 0)
            pct = round((presencas / total_previsto) * 100, 2) if total_previsto else 0.0
            out.append(
                ChamadaAlunoResponse(
                    aluno_id=str(i["aluno_id"]),
                    nome=i.get("nome", ""),
                    presencas=presencas,
                    total_aulas_previstas=total_previsto,
                    percentual_presenca=pct,
                )
            )
        return ChamadaResponse(materia_id=materia_id, itens=out)

    def update_professor(
        self, professor_id: str, dados: ProfessorUpdateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> MessageResponse:
        if not self.repo.get_professor(professor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
        update_dict = {k: v for k, v in dados.model_dump(exclude_unset=True).items() if v is not None and k != "perfil"}
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
        return MessageResponse(message="Professor atualizado com sucesso")

    def create_professor(
        self, polo_id: str, dados: ProfessorCreateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> ProfessorCardResponse:
        self.get_polo(polo_id)
        self._validar_email_cpf_unicos(dados.email, dados.cpf)
        perfil_id = self.repo.get_perfil_id_by_nome("professor")
        if not perfil_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Perfil 'professor' não configurado")

        usuario_id = self.repo.create_usuario(
            {
                "nome": dados.nome,
                "cpf": dados.cpf,
                "email": dados.email,
                "senha_hash": hash_password(dados.senha),
                "senha_algoritmo": "argon2id",
                "perfil_id": perfil_id,
                "polo_id": polo_id,
                "escola_id": dados.escola_id,
            }
        )
        professor_id = self.repo.create_professor(
            {
                "usuario_id": usuario_id,
                "polo_id": polo_id,
                "escola_id": dados.escola_id,
                "materias": dados.materias,
                "data_inicio": dados.data_inicio,
                "quantidade_aulas": dados.quantidade_aulas,
                "horas_totais": dados.horas_totais,
                "valor_hora_aula": dados.valor_hora_aula,
                "pix": dados.pix,
                "conteudo_programatico": dados.conteudo_programatico,
            }
        )
        self.repo.record_audit_log(
            usuario_id=actor_id,
            acao="professor_cadastrado",
            entidade="professores",
            entidade_id=professor_id,
            dados_depois={"nome": dados.nome, "polo_id": polo_id},
            ip=ip,
        )
        return self.get_professor_card(professor_id)

    # ------------------------------------------------------------------
    # 9. Gestão Pedagógica (RN-08)
    # ------------------------------------------------------------------

    def create_feed_post(
        self, dados: FeedPostCreateRequest, actor_id: str, perfil_nome: str, ip: Optional[str]
    ) -> FeedPostResponse:
        if perfil_nome.lower() not in _PERFIS_FEED_AUTORIZADOS:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado a publicar no feed")
        post_id = self.repo.create_feed_post(
            {"autor_id": actor_id, "titulo": dados.titulo, "conteudo": dados.conteudo, "tags": dados.tags, "polo_id": dados.polo_id}
        )
        self.repo.record_audit_log(
            usuario_id=actor_id, acao="feed_post_criado", entidade="feed_noticias", entidade_id=post_id, ip=ip
        )
        return FeedPostResponse(
            id=post_id, autor_id=actor_id, titulo=dados.titulo, conteudo=dados.conteudo, tags=dados.tags, polo_id=dados.polo_id
        )

    def list_feed(self, polo_id: Optional[str], limit: int, offset: int) -> List[FeedPostResponse]:
        _, items = self.repo.list_feed_posts(polo_id, limit, offset)
        return [FeedPostResponse(**{**i, "id": str(i["id"]), "tags": i.get("tags") or []}) for i in items]

    def create_lembrete(
        self, dados: LembreteCreateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> LembreteResponse:
        lembrete_id = self.repo.create_lembrete(
            {
                "usuario_id": dados.usuario_id,
                "titulo": dados.titulo,
                "mensagem": dados.mensagem,
                "data_expiracao": dados.data_expiracao,
            }
        )
        self.repo.record_audit_log(
            usuario_id=actor_id, acao="lembrete_criado", entidade="lembretes", entidade_id=lembrete_id, ip=ip
        )
        return LembreteResponse(
            id=lembrete_id,
            usuario_id=dados.usuario_id,
            titulo=dados.titulo,
            mensagem=dados.mensagem,
            data_expiracao=dados.data_expiracao,
            lido=False,
        )

    def list_lembretes(self, usuario_id: Optional[str], limit: int, offset: int) -> List[LembreteResponse]:
        _, items = self.repo.list_lembretes(usuario_id, limit, offset)
        return [LembreteResponse(**{**i, "id": str(i["id"])}) for i in items]

    def create_calendario_ead(
        self, dados: CalendarioEadCreateRequest, actor_id: Optional[str], ip: Optional[str]
    ) -> CalendarioEadResponse:
        cal_id = self.repo.create_calendario_ead(
            {
                "materia_id": dados.materia_id,
                "data_liberacao": dados.data_liberacao,
                "semestre": dados.semestre,
                "ano": dados.ano,
                "criado_por": actor_id,
            }
        )
        self.repo.record_audit_log(
            usuario_id=actor_id, acao="calendario_ead_criado", entidade="calendario_ead", entidade_id=cal_id, ip=ip
        )
        return CalendarioEadResponse(
            id=cal_id,
            materia_id=dados.materia_id,
            data_liberacao=dados.data_liberacao,
            semestre=dados.semestre,
            ano=dados.ano,
            criado_por=actor_id,
        )

    def list_calendario_ead(self, limit: int, offset: int) -> List[CalendarioEadResponse]:
        _, items = self.repo.list_calendario_ead(limit, offset)
        return [CalendarioEadResponse(**{**i, "id": str(i["id"])}) for i in items]

    # ------------------------------------------------------------------
    # 10. Treinamentos
    # ------------------------------------------------------------------

    def list_treinamentos(self, limit: int, offset: int) -> List[TreinamentoResponse]:
        _, items = self.repo.list_treinamentos(limit, offset)
        return [TreinamentoResponse(**{**i, "id": str(i["id"])}) for i in items]

    def inscrever_treinamento(self, treinamento_id: str, professor_id: str) -> TreinamentoInscricaoResponse:
        if not self.repo.get_professor(professor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
        insc_id = self.repo.inscrever_treinamento(treinamento_id, professor_id)
        return TreinamentoInscricaoResponse(
            id=insc_id, treinamento_id=treinamento_id, professor_id=professor_id, status="inscrito"
        )

    def list_treinamentos_professor(self, professor_id: str) -> List[TreinamentoInscricaoResponse]:
        items = self.repo.list_treinamentos_professor(professor_id)
        return [TreinamentoInscricaoResponse(**{**i, "id": str(i["id"])}) for i in items]

    # ------------------------------------------------------------------
    # 11. Perfil
    # ------------------------------------------------------------------

    def get_perfil(self, usuario_id: str) -> PerfilUsuarioResponse:
        u = self.repo.get_usuario_by_id(usuario_id)
        if not u:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        return PerfilUsuarioResponse(
            id=str(u["id"]),
            nome=u.get("nome", ""),
            sobrenome=u.get("sobrenome", ""),
            email=u.get("email"),
            telefone=u.get("telefone"),
            celular=u.get("celular"),
            foto_url=u.get("foto_url"),
            perfil_nome=u.get("perfil_nome"),
            polo_id=str(u["polo_id"]) if u.get("polo_id") else None,
            escola_id=str(u["escola_id"]) if u.get("escola_id") else None,
        )

    def update_perfil(self, usuario_id: str, dados: PerfilUpdateRequest, ip: Optional[str]) -> PerfilUsuarioResponse:
        update_dict = {k: v for k, v in dados.model_dump(exclude_unset=True).items() if v is not None}
        if update_dict:
            self.repo.update_usuario(usuario_id, update_dict)
        self.repo.record_audit_log(
            usuario_id=usuario_id, acao="perfil_atualizado", entidade="usuarios", entidade_id=usuario_id, ip=ip
        )
        return self.get_perfil(usuario_id)

    def update_foto(self, usuario_id: str, foto_url: str, ip: Optional[str]) -> PerfilFotoResponse:
        self.repo.update_usuario(usuario_id, {"foto_url": foto_url})
        self.repo.record_audit_log(
            usuario_id=usuario_id, acao="perfil_foto_atualizada", entidade="usuarios", entidade_id=usuario_id, ip=ip
        )
        return PerfilFotoResponse(foto_url=foto_url)

    def update_senha(self, usuario_id: str, dados: PerfilSenhaUpdateRequest, ip: Optional[str]) -> MessageResponse:
        u = self.repo.get_usuario_by_id(usuario_id)
        if not u:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        valido, _ = verify_password(dados.senha_atual, u.get("senha_hash", ""), u.get("senha_algoritmo", "argon2id"))
        if not valido:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
        self.repo.update_usuario(usuario_id, {"senha_hash": hash_password(dados.nova_senha), "senha_algoritmo": "argon2id"})
        self.repo.record_audit_log(
            usuario_id=usuario_id, acao="perfil_senha_atualizada", entidade="usuarios", entidade_id=usuario_id, ip=ip
        )
        return MessageResponse(message="Senha atualizada com sucesso")


def _dias_desde(referencia: datetime) -> int:
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - referencia).days


def uuid_token() -> str:
    """Gera uma senha aleatória temporária para alunos cadastrados sem login direto."""
    import secrets

    return secrets.token_urlsafe(16)
