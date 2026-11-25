"""Serviço contendo as regras de negócio do módulo administrativo."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, Response, status

from app.core.security import hash_password
from app.modules.admin.dashboard_repository import ORDENACOES_RANKING
from app.modules.admin.repository import AdminRepositoryInterface, get_admin_repository
from app.modules.financeiro import exportacao as exp
from app.modules.financeiro.schemas import FiltrosPeriodo
from app.modules.admin.ficha_schemas import (
    DadosCadastraisFicha,
    TransferenciaPendenteFicha,
    VinculoDocenteItem,
)
from app.modules.admin.ficha_service import FichaServiceMixin
from app.modules.admin.schemas import (
    AlunoVinculoFicha,
    ConfiguracaoResponse,
    ConfiguracaoSetRequest,
    AdminDashboardMetricsResponse,
    AcademicoBloco,
    CertificadoDashboardItem,
    CertificadoDashboardListResponse,
    CrescimentoBloco,
    DashboardExecutivoResponse,
    LicencasBloco,
    MatriculaDashboardItem,
    MatriculaDashboardListResponse,
    PendenciasBloco,
    PeriodoResolvido,
    RankingPoloItem,
    RankingPolosResponse,
    SerieMensalItem,
    ConsolidadoAcessoFicha,
    EtlErroResponse,
    EtlSyncRunListResponse,
    EtlSyncRunResponse,
    LogAuditoriaListResponse,
    LogAuditoriaResponse,
    MetricasAlunoFicha,
    MetricasProfessorFicha,
    MetricasUnidadeFicha,
    PerfilItemResponse,
    PermissaoItemResponse,
    ProfessorVinculoFicha,
    ResumoMetricasUsuarioResponse,
    UsuarioAdminResponse,
    UsuarioCreateRequest,
    UsuarioFichaResponse,
    UsuarioListResponse,
    UsuarioPermissoesUpdateRequest,
    UsuarioUpdateRequest,
)


DIAS_PERIODO_PADRAO = 30


def _ultimo_dia_mes(ano: int, mes: int) -> date:
    return date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)


def resolver_periodo(filtros: FiltrosPeriodo, hoje: Optional[date] = None) -> Tuple[date, date]:
    """Converte os filtros (datas, mês, semestre, ano) em um intervalo fechado.

    Prioridade: datas explícitas > mês/semestre/ano > últimos 30 dias.
    Mês ou semestre sem ano usam o ano corrente.
    """
    hoje = hoje or date.today()
    if filtros.data_inicio or filtros.data_fim:
        fim = filtros.data_fim or hoje
        inicio = filtros.data_inicio or fim - timedelta(days=DIAS_PERIODO_PADRAO - 1)
        return inicio, fim
    if filtros.ano or filtros.mes or filtros.semestre:
        ano = filtros.ano or hoje.year
        if filtros.mes:
            return date(ano, filtros.mes, 1), _ultimo_dia_mes(ano, filtros.mes)
        if filtros.semestre == 1:
            return date(ano, 1, 1), date(ano, 6, 30)
        if filtros.semestre == 2:
            return date(ano, 7, 1), date(ano, 12, 31)
        return date(ano, 1, 1), date(ano, 12, 31)
    return hoje - timedelta(days=DIAS_PERIODO_PADRAO - 1), hoje


def periodo_anterior(inicio: date, fim: date) -> Tuple[date, date]:
    """Intervalo de mesma duração imediatamente antes de ``inicio``."""
    dias = (fim - inicio).days + 1
    ant_fim = inicio - timedelta(days=1)
    return ant_fim - timedelta(days=dias - 1), ant_fim


def variacao_pct(atual: float, anterior: float) -> Optional[float]:
    """Variação percentual; None quando não há base de comparação."""
    if not anterior:
        return None
    return round((atual - anterior) / anterior * 100, 1)


def percentual(parte: float, total: float) -> Optional[float]:
    return round(parte / total * 100, 1) if total else None


ROTULOS_ORDENACAO = {
    "novas_licencas": "Novas licenças",
    "receita_paga": "Receita paga",
    "alunos_ativos": "Alunos ativos",
    "presenca_pct": "Presença média",
}


class AdminService(FichaServiceMixin):
    def __init__(self, repo: Optional[AdminRepositoryInterface] = None) -> None:
        self._repo = repo

    @property
    def repo(self) -> AdminRepositoryInterface:
        return self._repo or get_admin_repository()

    def get_dashboard_metrics(self) -> AdminDashboardMetricsResponse:
        return AdminDashboardMetricsResponse(**self.repo.get_dashboard_metrics())

    # ---------- Dashboard Executiva ----------

    def get_dashboard_executivo(
        self, filtros: FiltrosPeriodo, hoje: Optional[date] = None
    ) -> DashboardExecutivoResponse:
        inicio, fim = resolver_periodo(filtros, hoje)
        ant_inicio, ant_fim = periodo_anterior(inicio, fim)
        polo, escola = filtros.polo_id, filtros.escola_id
        atual = self.repo.dashboard_contagens_periodo(inicio, fim, polo, escola)
        anterior = self.repo.dashboard_contagens_periodo(ant_inicio, ant_fim, polo, escola)
        foto = self.repo.dashboard_foto_atual(polo, escola)
        serie = self.repo.dashboard_serie_mensal(fim, 12, polo, escola)

        dias = (fim - inicio).days + 1
        estoque = int(foto.get("estoque_disponivel") or 0)
        consumo = int(atual.get("consumo_licencas") or 0)
        consumo_ant = int(anterior.get("consumo_licencas") or 0)
        # Quantos dias o estoque dura no ritmo de consumo do período (None = sem consumo).
        cobertura = int(estoque * dias / consumo) if consumo else None

        return DashboardExecutivoResponse(
            periodo=PeriodoResolvido(inicio=inicio, fim=fim),
            periodo_anterior=PeriodoResolvido(inicio=ant_inicio, fim=ant_fim),
            crescimento=CrescimentoBloco(
                alunos_ativos=int(foto.get("alunos_ativos") or 0),
                novos_alunos=atual["novos_alunos"],
                novos_alunos_anterior=anterior["novos_alunos"],
                variacao_novos_alunos_pct=variacao_pct(atual["novos_alunos"], anterior["novos_alunos"]),
                novas_matriculas=atual["novas_matriculas"],
                novas_matriculas_anterior=anterior["novas_matriculas"],
                variacao_matriculas_pct=variacao_pct(atual["novas_matriculas"], anterior["novas_matriculas"]),
                desistencias=atual["desistencias"],
                desistencias_anterior=anterior["desistencias"],
                serie_12m=[SerieMensalItem(**item) for item in serie],
            ),
            academico=AcademicoBloco(
                presenca_media_pct=percentual(atual["presencas_positivas"], atual["presencas_total"]),
                presenca_media_anterior_pct=percentual(anterior["presencas_positivas"], anterior["presencas_total"]),
                registros_presenca=atual["presencas_total"],
                certificados_periodo=atual["certificados"],
                certificados_anterior=anterior["certificados"],
            ),
            licencas=LicencasBloco(
                estoque_disponivel=estoque,
                consumo_periodo=consumo,
                consumo_anterior=consumo_ant,
                variacao_consumo_pct=variacao_pct(consumo, consumo_ant),
                cobertura_dias=cobertura,
            ),
            pendencias=PendenciasBloco(
                solicitacoes_unidade_pendentes=int(foto.get("solicitacoes_unidade_pendentes") or 0),
                transferencias_pendentes=int(foto.get("transferencias_pendentes") or 0),
                pedidos_aguardando_envio=int(foto.get("pedidos_aguardando_envio") or 0),
                cobrancas_vencidas_qtd=int(foto.get("cobrancas_vencidas_qtd") or 0),
                cobrancas_vencidas_valor=round(float(foto.get("cobrancas_vencidas_valor") or 0), 2),
                estagios_em_analise=int(foto.get("estagios_em_analise") or 0),
                turmas_atrasadas=int(foto.get("turmas_atrasadas") or 0),
            ),
        )

    def get_ranking_polos(
        self, filtros: FiltrosPeriodo, ordenar_por: str = "novas_licencas", hoje: Optional[date] = None
    ) -> RankingPolosResponse:
        if ordenar_por not in ORDENACOES_RANKING:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"ordenar_por inválido. Use: {', '.join(ORDENACOES_RANKING)}",
            )
        inicio, fim = resolver_periodo(filtros, hoje)
        linhas: List[Dict[str, Any]] = []
        for r in self.repo.dashboard_ranking_polos(inicio, fim):
            linhas.append({
                "polo_id": str(r["polo_id"]),
                "polo_nome": r.get("polo_nome") or "Polo sem nome",
                "alunos_ativos": int(r.get("alunos_ativos") or 0),
                "escolas_ativas": int(r.get("escolas_ativas") or 0),
                "novas_licencas": int(r.get("novas_licencas") or 0),
                "receita_paga": round(float(r.get("receita_paga") or 0), 2),
                "presenca_pct": percentual(
                    int(r.get("presencas_positivas") or 0), int(r.get("presencas_total") or 0)
                ),
            })
        # Decrescente pelo critério (sem dado de presença vai para o fim); empate pelo nome.
        linhas.sort(key=lambda l: (
            -(l[ordenar_por] if l[ordenar_por] is not None else -1),
            l["polo_nome"].lower(),
        ))
        return RankingPolosResponse(
            periodo=PeriodoResolvido(inicio=inicio, fim=fim),
            ordenar_por=ordenar_por,
            items=[RankingPoloItem(posicao=i + 1, **l) for i, l in enumerate(linhas)],
        )

    def exportar_ranking_polos(self, filtros: FiltrosPeriodo, ordenar_por: str, formato: str) -> Response:
        ranking = self.get_ranking_polos(filtros, ordenar_por)
        colunas: List[exp.Coluna] = [
            ("Posição", 14, "C", "int"), ("Polo", 70, "L", "texto"), ("Novas licenças", 26, "R", "int"),
            ("Receita paga", 30, "R", "moeda"), ("Alunos ativos", 24, "R", "int"),
            ("Escolas ativas", 24, "R", "int"), ("Presença", 20, "R", "texto"),
        ]
        dados = [[
            i.posicao, i.polo_nome, i.novas_licencas, i.receita_paga, i.alunos_ativos, i.escolas_ativas,
            f"{i.presenca_pct:.1f}%".replace(".", ",") if i.presenca_pct is not None else "-",
        ] for i in ranking.items]
        filtros_txt = (
            f"Período: {ranking.periodo.inicio:%d/%m/%Y} a {ranking.periodo.fim:%d/%m/%Y} | "
            f"Ordenado por: {ROTULOS_ORDENACAO[ordenar_por]}"
        )
        if formato == "xlsx":
            conteudo = exp.planilha_xlsx([("Ranking de Polos", colunas, dados)], filtros_txt)
        else:
            pdf = exp.RelatorioPDF("Ranking de Polos", filtros_txt, paisagem=True)
            pdf.add_page()
            pdf.pares([
                ("Polos ativos", str(len(ranking.items))),
                ("Novas licenças", str(sum(i.novas_licencas for i in ranking.items))),
                ("Receita paga", exp.brl(sum(i.receita_paga for i in ranking.items))),
                ("Alunos ativos", str(sum(i.alunos_ativos for i in ranking.items))),
            ])
            pdf.secao("Polos")
            pdf.tabela(colunas, dados)
            conteudo = pdf.bytes()
        return exp.resposta_arquivo(conteudo, "ranking-polos", formato)

    def list_matriculas_dashboard(
        self, filtros: FiltrosPeriodo, q: Optional[str] = None
    ) -> MatriculaDashboardListResponse:
        total, itens = self.repo.dashboard_list_matriculas(filtros, q)
        return MatriculaDashboardListResponse(total=total, items=[MatriculaDashboardItem(**i) for i in itens])

    def list_certificados_dashboard(
        self, filtros: FiltrosPeriodo, q: Optional[str] = None
    ) -> CertificadoDashboardListResponse:
        total, itens = self.repo.dashboard_list_certificados(filtros, q)
        return CertificadoDashboardListResponse(total=total, items=[CertificadoDashboardItem(**i) for i in itens])

    def _build_user_response(
        self, user_data: Dict[str, Any], permissoes: Optional[List[str]] = None
    ) -> UsuarioAdminResponse:
        uid = str(user_data["id"])
        if permissoes is None:
            permissoes = self.repo.get_user_permissions(uid)

        return UsuarioAdminResponse(
            id=uid,
            nome=user_data.get("nome", ""),
            sobrenome=user_data.get("sobrenome", ""),
            email=user_data.get("email"),
            cpf=user_data.get("cpf"),
            telefone=user_data.get("telefone"),
            celular=user_data.get("celular"),
            foto_url=user_data.get("foto_url"),
            status=user_data.get("status", "ativo"),
            perfil_id=str(user_data["perfil_id"]) if user_data.get("perfil_id") else None,
            perfil_nome=user_data.get("perfil_nome"),
            polo_id=str(user_data["polo_id"]) if user_data.get("polo_id") else None,
            escola_id=str(user_data["escola_id"]) if user_data.get("escola_id") else None,
            polo_nome=user_data.get("polo_nome"),
            escola_nome=user_data.get("escola_nome"),
            permissoes=permissoes,
            ultimo_login_em=user_data.get("ultimo_login_em"),
            criado_em=user_data.get("criado_em"),
            atualizado_em=user_data.get("atualizado_em"),
            transferencia_pendente=bool(user_data.get("transferencia_pendente")),
        )

    # ---------- CRUD de Usuários ----------

    def list_usuarios(
        self,
        query: Optional[str] = None,
        perfil_id: Optional[str] = None,
        perfil_nome: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> UsuarioListResponse:
        total, raw_users = self.repo.list_users(
            query=query,
            perfil_id=perfil_id,
            perfil_nome=perfil_nome,
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        user_ids = [str(user["id"]) for user in raw_users]
        permissions_by_user = self.repo.get_users_permissions(user_ids)

        items: List[UsuarioAdminResponse] = []
        for u in raw_users:
            perms = permissions_by_user.get(str(u["id"]), [])
            items.append(self._build_user_response(u, perms))

        return UsuarioListResponse(
            total=total,
            items=items,
            limit=limit,
            offset=offset,
        )

    def get_usuario(self, user_id: str) -> UsuarioAdminResponse:
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        perms = self.repo.get_user_permissions(user_id)
        return self._build_user_response(user, perms)

    # ---------- Ficha cadastral & métricas ----------

    def _require_user(self, user_id: str) -> Dict[str, Any]:
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        return user

    @staticmethod
    def _coerce_materias(raw: Any) -> List[str]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(m) for m in raw]
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(m) for m in parsed]
            except (ValueError, TypeError):
                return [raw] if raw.strip() else []
        return []

    def get_usuario_ficha(self, user_id: str) -> UsuarioFichaResponse:
        user = self._require_user(user_id)
        perms = self.repo.get_user_permissions(user_id)
        base = self._build_user_response(user, perms)
        dados = DadosCadastraisFicha(**{
            k: v for k, v in {**user, **self.repo.get_dados_cadastrais(user_id)}.items()
            if k in DadosCadastraisFicha.model_fields
        })

        aluno_raw = self.repo.get_aluno_by_usuario_id(user_id)
        professor_raw = self.repo.get_professor_vinculo_by_usuario_id(user_id)

        def _id(valor: Any) -> Optional[str]:
            return str(valor) if valor else None

        def _data(valor: Any) -> Any:
            return valor.date() if isinstance(valor, datetime) else valor

        aluno = None
        if aluno_raw:
            nomes = self.repo.nomes_unidade(_id(aluno_raw.get("polo_id")), _id(aluno_raw.get("escola_id")))
            pendente = self.repo.transferencia_pendente(str(aluno_raw["id"]))
            aluno = AlunoVinculoFicha(
                id=str(aluno_raw["id"]),
                usuario_id=_id(aluno_raw.get("usuario_id")),
                numero_matricula=aluno_raw.get("numero_matricula"),
                modalidade=aluno_raw.get("modalidade"),
                status=aluno_raw.get("status"),
                data_nascimento=_data(aluno_raw.get("data_nascimento")),
                polo_id=_id(aluno_raw.get("polo_id")),
                escola_id=_id(aluno_raw.get("escola_id")),
                polo_nome=nomes.get("polo_nome"),
                escola_nome=nomes.get("escola_nome"),
                transferencia_pendente=TransferenciaPendenteFicha(**pendente) if pendente else None,
            )
            if dados.data_nascimento is None and aluno.data_nascimento:
                dados.data_nascimento = aluno.data_nascimento

        professor = None
        if professor_raw:
            horas = professor_raw.get("horas_totais")
            nomes = self.repo.nomes_unidade(_id(professor_raw.get("polo_id")), _id(professor_raw.get("escola_id")))
            professor = ProfessorVinculoFicha(
                id=str(professor_raw["id"]),
                usuario_id=_id(professor_raw.get("usuario_id")),
                materias=self._coerce_materias(professor_raw.get("materias")),
                data_inicio=_data(professor_raw.get("data_inicio")),
                quantidade_aulas=int(professor_raw.get("quantidade_aulas") or 0),
                horas_totais=float(horas) if horas is not None else None,
                valor_hora_aula=(
                    float(professor_raw["valor_hora_aula"])
                    if professor_raw.get("valor_hora_aula") is not None
                    else None
                ),
                chave_pix=professor_raw.get("chave_pix") or professor_raw.get("pix"),
                status=professor_raw.get("status"),
                polo_id=_id(professor_raw.get("polo_id")),
                escola_id=_id(professor_raw.get("escola_id")),
                polo_nome=nomes.get("polo_nome"),
                escola_nome=nomes.get("escola_nome"),
                vinculos=[VinculoDocenteItem(**v) for v in self.repo.vinculos_docentes(str(professor_raw["id"]))],
            )

        return UsuarioFichaResponse(
            **base.model_dump(),
            dados=dados,
            aluno=aluno,
            professor=professor,
        )

    def get_resumo_metricas(self, user_id: str) -> ResumoMetricasUsuarioResponse:
        user = self._require_user(user_id)
        perms = self.repo.get_user_permissions(user_id)

        aluno_raw = self.repo.get_aluno_by_usuario_id(user_id)
        professor_raw = self.repo.get_professor_vinculo_by_usuario_id(user_id)

        metricas_aluno = None
        if aluno_raw:
            m = self.repo.get_metricas_aluno(str(aluno_raw["id"]))
            total_presencas = int(m.get("total_presencas") or 0)
            positivas = int(m.get("presencas_positivas") or 0)
            percentual = round(positivas / total_presencas * 100.0, 1) if total_presencas > 0 else None
            turmas = self.repo.turmas_do_aluno(str(aluno_raw["id"]))
            frequencias = self.frequencias_do_aluno(str(aluno_raw["id"]), turmas)
            pcts = [f["frequencia_pct"] for f in frequencias.values() if f.get("frequencia_pct") is not None]
            minimo = next((f["minimo_pct"] for f in frequencias.values() if f.get("minimo_pct") is not None), None)
            metricas_aluno = MetricasAlunoFicha(
                matriculas_total=int(m.get("matriculas_total") or 0),
                turmas_total=len(turmas),
                frequencia_pct=round(sum(pcts) / len(pcts), 1) if pcts else None,
                frequencia_minima_pct=minimo,
                frequencia_em_risco=any(f.get("em_risco") for f in frequencias.values()),
                total_notas=int(m.get("total_notas") or 0),
                media_notas=float(m["media_notas"]) if m.get("media_notas") is not None else None,
                total_presencas=total_presencas,
                presencas_positivas=positivas,
                percentual_presenca=percentual,
                certificados_total=int(m.get("certificados_total") or 0),
            )

        metricas_professor = None
        if professor_raw:
            m = self.repo.get_metricas_professor(str(professor_raw["id"]))
            vinculos = self.repo.vinculos_docentes(str(professor_raw["id"]))
            metricas_professor = MetricasProfessorFicha(
                aulas_registradas=int(m.get("aulas_registradas") or 0)
                + sum(int(v.get("aulas_ministradas") or 0) for v in vinculos),
                treinamentos_total=int(m.get("treinamentos_total") or 0),
                turmas_total=len({v.get("turma_id") for v in vinculos if v.get("turma_id")}),
                disciplinas_total=len({v.get("disciplina_id") for v in vinculos if v.get("disciplina_id")}),
                horas_previstas=round(sum(float(v.get("carga_horaria") or 0) for v in vinculos), 2),
                horas_ministradas=round(sum(float(v.get("horas_ministradas") or 0) for v in vinculos), 2),
            )

        polo_id = user.get("polo_id") or (aluno_raw or {}).get("polo_id") or (professor_raw or {}).get("polo_id")
        escola_id = user.get("escola_id") or (aluno_raw or {}).get("escola_id") or (professor_raw or {}).get("escola_id")

        # O resumo da unidade só faz sentido para quem gere a unidade (perfis polo e escola).
        perfil = str(user.get("perfil_nome") or "").lower()
        unidade = None
        if perfil in ("polo", "escola") and (polo_id or escola_id):
            c = self.repo.contagens_unidade(
                polo_id=str(polo_id) if polo_id else None,
                escola_id=str(escola_id) if escola_id else None,
            )
            unidade = MetricasUnidadeFicha(
                escolas=int(c.get("escolas") or 0),
                turmas=int(c.get("turmas") or 0),
                professores=int(c.get("professores") or 0),
                alunos=int(c.get("alunos") or 0),
                aulas=int(c.get("aulas") or 0),
                licencas_estoque=int(c.get("licencas_estoque") or 0),
                licencas_atribuidas=int(c.get("licencas_atribuidas") or 0),
                licencas_movimentacoes=int(c.get("licencas_movimentacoes") or 0),
                pedidos_licencas=int(c.get("pedidos_licencas") or 0),
                pedidos_livros=int(c.get("pedidos_livros") or 0),
            )

        return ResumoMetricasUsuarioResponse(
            usuario_id=str(user_id),
            aluno=metricas_aluno,
            professor=metricas_professor,
            unidade=unidade,
            consolidado=ConsolidadoAcessoFicha(
                status=user.get("status", "ativo"),
                perfil_nome=user.get("perfil_nome"),
                ultimo_login_em=user.get("ultimo_login_em"),
                criado_em=user.get("criado_em"),
                atualizado_em=user.get("atualizado_em"),
                permissoes=perms,
            ),
        )

    def create_usuario(
        self,
        dados: UsuarioCreateRequest,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> UsuarioAdminResponse:
        # 1. Verifica duplicidade de e-mail
        if dados.email:
            existing = self.repo.get_user_by_email(dados.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O e-mail '{dados.email}' já está em uso por outro usuário",
                )

        # 2. Verifica duplicidade de CPF
        if dados.cpf:
            existing_cpf = self.repo.get_user_by_cpf(dados.cpf)
            if existing_cpf:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O CPF informado já está cadastrado",
                )

        # 3. Resolve perfil
        perfil_id = dados.perfil_id
        if not perfil_id and dados.perfil_nome:
            p = self.repo.get_perfil_by_nome(dados.perfil_nome)
            if p:
                perfil_id = p["id"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Perfil '{dados.perfil_nome}' não encontrado no sistema",
                )

        # 4. Gera hash Argon2id da senha inicial
        senha_hash = hash_password(dados.senha)

        # 5. Cria usuário no repositório
        user_dict = {
            "nome": dados.nome.strip(),
            "sobrenome": dados.sobrenome.strip() if dados.sobrenome else "",
            "email": dados.email.strip().lower(),
            "cpf": dados.cpf.strip() if dados.cpf else None,
            "senha_hash": senha_hash,
            "senha_algoritmo": "argon2id",
            "perfil_id": perfil_id,
            "polo_id": dados.polo_id,
            "escola_id": dados.escola_id,
            "telefone": dados.telefone,
            "celular": dados.celular,
            "status": dados.status,
        }
        new_id = self.repo.create_user(user_dict)

        # 6. Atribui permissões granulares
        if dados.permissoes:
            self.repo.set_user_permissions(new_id, dados.permissoes)

        # 7. Registra auditoria
        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_criado",
            entidade="usuarios",
            entidade_id=new_id,
            dados_depois={
                "nome": dados.nome,
                "email": dados.email,
                "perfil_id": perfil_id,
                "status": dados.status,
                "permissoes": dados.permissoes,
            },
            ip=client_ip,
        )

        self._sincronizar_corpo_docente(
            new_id, perfil_id, dados.polo_id, dados.escola_id, actor_user_id, client_ip
        )
        return self.get_usuario(new_id)

    def update_usuario(
        self,
        user_id: str,
        dados: UsuarioUpdateRequest,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> UsuarioAdminResponse:
        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        old_perms = self.repo.get_user_permissions(user_id)

        # Valida duplicidade se o e-mail for alterado
        if dados.email and dados.email.strip().lower() != (old_user.get("email") or "").lower():
            existing = self.repo.get_user_by_email(dados.email)
            if existing and str(existing["id"]) != str(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O e-mail '{dados.email}' já está em uso",
                )

        # Valida CPF se for alterado
        if dados.cpf and dados.cpf.strip() != (old_user.get("cpf") or ""):
            existing_cpf = self.repo.get_user_by_cpf(dados.cpf)
            if existing_cpf and str(existing_cpf["id"]) != str(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O CPF informado já está em uso",
                )

        # Resolve perfil se fornecido perfil_nome
        perfil_id = dados.perfil_id
        if not perfil_id and dados.perfil_nome:
            p = self.repo.get_perfil_by_nome(dados.perfil_nome)
            if p:
                perfil_id = p["id"]

        update_dict: Dict[str, Any] = {}
        if dados.nome is not None:
            update_dict["nome"] = dados.nome.strip()
        if dados.sobrenome is not None:
            update_dict["sobrenome"] = dados.sobrenome.strip()
        if dados.email is not None:
            update_dict["email"] = dados.email.strip().lower()
        if dados.cpf is not None:
            update_dict["cpf"] = dados.cpf.strip() if dados.cpf else None
        if perfil_id is not None:
            update_dict["perfil_id"] = perfil_id
        if dados.polo_id is not None:
            update_dict["polo_id"] = dados.polo_id or None
        if dados.escola_id is not None:
            update_dict["escola_id"] = dados.escola_id or None
        if dados.telefone is not None:
            update_dict["telefone"] = dados.telefone
        if dados.celular is not None:
            update_dict["celular"] = dados.celular
        if dados.status is not None:
            update_dict["status"] = dados.status

        if update_dict:
            self.repo.update_user(user_id, update_dict)

        # Atualiza permissões se enviadas
        if dados.permissoes is not None:
            self.repo.set_user_permissions(user_id, dados.permissoes)

        new_perms = self.repo.get_user_permissions(user_id)

        # Registra auditoria com dados_antes e dados_depois
        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_atualizado",
            entidade="usuarios",
            entidade_id=user_id,
            dados_antes={
                "nome": old_user.get("nome"),
                "email": old_user.get("email"),
                "status": old_user.get("status"),
                "perfil_id": old_user.get("perfil_id"),
                "permissoes": old_perms,
            },
            dados_depois={
                "nome": update_dict.get("nome", old_user.get("nome")),
                "email": update_dict.get("email", old_user.get("email")),
                "status": update_dict.get("status", old_user.get("status")),
                "perfil_id": update_dict.get("perfil_id", old_user.get("perfil_id")),
                "permissoes": new_perms,
            },
            ip=client_ip,
        )

        if "perfil_id" in update_dict:
            self._sincronizar_corpo_docente(
                user_id,
                update_dict["perfil_id"],
                update_dict.get("polo_id", old_user.get("polo_id")),
                update_dict.get("escola_id", old_user.get("escola_id")),
                actor_user_id,
                client_ip,
            )
        return self.get_usuario(user_id)

    def _sincronizar_corpo_docente(
        self,
        user_id: str,
        perfil_id: Optional[str],
        polo_id: Optional[str],
        escola_id: Optional[str],
        actor_user_id: Optional[str],
        client_ip: Optional[str],
    ) -> None:
        """Perfil `professor` em Usuários ⇔ registro ativo no Corpo Docente."""
        perfil = self.repo.get_perfil_by_id(str(perfil_id)) if perfil_id else None
        eh_professor = bool(perfil) and str(perfil.get("nome") or "").lower() == "professor"
        vinculo = self.repo.get_professor_vinculo_by_usuario_id(user_id)

        if eh_professor and not vinculo:
            novo_id = self.repo.create_professor_vinculo(
                user_id, str(polo_id) if polo_id else None, str(escola_id) if escola_id else None
            )
            acao, entidade_id, novo_status = "professor_cadastrado", novo_id, "ativo"
        elif eh_professor and vinculo.get("status") != "ativo":
            acao, entidade_id, novo_status = "professor_reativado", str(vinculo["id"]), "ativo"
            self.repo.set_professor_status(entidade_id, novo_status)
        elif not eh_professor and vinculo and vinculo.get("status") == "ativo":
            acao, entidade_id, novo_status = "professor_desativado", str(vinculo["id"]), "inativo"
            self.repo.set_professor_status(entidade_id, novo_status)
        else:
            return

        if entidade_id:
            self.repo.record_audit_log(
                usuario_id=actor_user_id,
                acao=acao,
                entidade="professores",
                entidade_id=entidade_id,
                dados_depois={"usuario_id": str(user_id), "status": novo_status, "origem": "usuarios"},
                ip=client_ip,
            )

    def update_usuario_permissoes(
        self,
        user_id: str,
        dados: UsuarioPermissoesUpdateRequest,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> UsuarioAdminResponse:
        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        old_perms = self.repo.get_user_permissions(user_id)
        self.repo.set_user_permissions(user_id, dados.permissoes)
        new_perms = self.repo.get_user_permissions(user_id)

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_permissoes_atualizadas",
            entidade="usuario_permissoes",
            entidade_id=user_id,
            dados_antes={"permissoes": old_perms},
            dados_depois={"permissoes": new_perms},
            ip=client_ip,
        )

        return self.get_usuario(user_id)

    def reset_usuario_senha(
        self,
        user_id: str,
        nova_senha: str,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> dict[str, str]:
        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        if len(nova_senha) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A nova senha deve possuir no mínimo 6 caracteres",
            )

        new_hash = hash_password(nova_senha)
        self.repo.update_user(
            user_id,
            {"senha_hash": new_hash, "senha_algoritmo": "argon2id"},
        )

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="senha_alterada_admin",
            entidade="usuarios",
            entidade_id=user_id,
            dados_depois={"algoritmo": "argon2id", "alterado_por_admin": True},
            ip=client_ip,
        )

        return {"message": "Senha do usuário redefinida com sucesso para Argon2id."}

    def delete_usuario(
        self,
        user_id: str,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> dict[str, str]:
        if actor_user_id and str(actor_user_id) == str(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é permitido excluir o próprio usuário administrador logado",
            )

        old_user = self.repo.get_user_by_id(user_id)
        if not old_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )

        # A exclusão apaga em cascata aluno, notas, presenças e turmas: só sem histórico.
        self._exigir_sem_historico(user_id)
        self.repo.delete_user(user_id)

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="usuario_excluido",
            entidade="usuarios",
            entidade_id=user_id,
            dados_antes={"nome": old_user.get("nome"), "email": old_user.get("email")},
            ip=client_ip,
        )

        return {"message": "Usuário excluído com sucesso."}

    # ---------- Perfis & Permissões ----------

    def list_perfis(self) -> List[PerfilItemResponse]:
        rows = self.repo.list_perfis()
        return [PerfilItemResponse(id=str(r["id"]), nome=r["nome"], descricao=r.get("descricao")) for r in rows]

    def list_permissoes(self) -> List[PermissaoItemResponse]:
        rows = self.repo.list_permissoes()
        return [PermissaoItemResponse(id=str(r["id"]), chave=r["chave"], descricao=r.get("descricao")) for r in rows]

    # ---------- Logs de Auditoria ----------

    def list_audit_logs(
        self,
        usuario_id: Optional[str] = None,
        entidade: Optional[str] = None,
        acao: Optional[str] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LogAuditoriaListResponse:
        total, rows = self.repo.list_audit_logs(
            usuario_id=usuario_id,
            entidade=entidade,
            acao=acao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=limit,
            offset=offset,
        )

        items = [
            LogAuditoriaResponse(
                id=str(r["id"]),
                usuario_id=str(r["usuario_id"]) if r.get("usuario_id") else None,
                usuario_nome=r.get("usuario_nome"),
                usuario_email=r.get("usuario_email"),
                acao=r["acao"],
                entidade=r.get("entidade"),
                entidade_id=str(r["entidade_id"]) if r.get("entidade_id") else None,
                dados_antes=r.get("dados_antes") if isinstance(r.get("dados_antes"), dict) else None,
                dados_depois=r.get("dados_depois") if isinstance(r.get("dados_depois"), dict) else None,
                ip=r.get("ip"),
                criado_em=r.get("criado_em"),
            )
            for r in rows
        ]

        return LogAuditoriaListResponse(
            total=total,
            items=items,
            limit=limit,
            offset=offset,
        )

    # ---------- Configurações Gerais ----------

    def list_configuracoes(self) -> List[ConfiguracaoResponse]:
        rows = self.repo.list_configuracoes()
        return [
            ConfiguracaoResponse(
                id=str(r["id"]) if r.get("id") else None,
                chave=r["chave"],
                valor=r["valor"],
                criado_em=r.get("criado_em"),
                atualizado_em=r.get("atualizado_em"),
            )
            for r in rows
        ]

    def get_configuracao(self, chave: str) -> ConfiguracaoResponse:
        row = self.repo.get_configuracao(chave)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuração '{chave}' não encontrada",
            )
        return ConfiguracaoResponse(
            id=str(row["id"]) if row.get("id") else None,
            chave=row["chave"],
            valor=row["valor"],
            criado_em=row.get("criado_em"),
            atualizado_em=row.get("atualizado_em"),
        )

    def set_configuracao(
        self,
        chave: str,
        valor: Any,
        actor_user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> ConfiguracaoResponse:
        old = self.repo.get_configuracao(chave)
        old_val = old.get("valor") if old else None

        updated = self.repo.set_configuracao(chave, valor)

        self.repo.record_audit_log(
            usuario_id=actor_user_id,
            acao="configuracao_atualizada",
            entidade="configuracoes",
            entidade_id=chave,
            dados_antes={"chave": chave, "valor": old_val},
            dados_depois={"chave": chave, "valor": valor},
            ip=client_ip,
        )

        return ConfiguracaoResponse(
            id=str(updated["id"]) if updated.get("id") else None,
            chave=updated["chave"],
            valor=updated["valor"],
            criado_em=updated.get("criado_em"),
            atualizado_em=updated.get("atualizado_em"),
        )

    # ---------- ETL Sync Runs ----------

    def list_etl_execucoes(
        self,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EtlSyncRunListResponse:
        total, rows = self.repo.list_etl_sync_runs(status=status_filter, limit=limit, offset=offset)

        items: List[EtlSyncRunResponse] = []
        total_lidos = 0
        total_inseridos = 0

        for r in rows:
            duracao = r.get("duracao_segundos")
            if duracao is not None:
                duracao = float(duracao)

            total_lidos += int(r.get("total_lido") or 0)
            total_inseridos += int(r.get("total_inserido") or 0)

            items.append(
                EtlSyncRunResponse(
                    id=int(r["id"]),
                    modo=r["modo"],
                    iniciado_em=r["iniciado_em"],
                    finalizado_em=r.get("finalizado_em"),
                    total_lido=int(r.get("total_lido") or 0),
                    total_inserido=int(r.get("total_inserido") or 0),
                    total_atualizado=int(r.get("total_atualizado") or 0),
                    total_erro=int(r.get("total_erro") or 0),
                    status=r.get("status", "rodando"),
                    duracao_segundos=duracao,
                    total_erros_detalhados=int(r.get("total_erros_detalhados") or 0),
                )
            )

        taxa_sucesso = (total_inseridos / total_lidos * 100.0) if total_lidos > 0 else 100.0

        return EtlSyncRunListResponse(
            total=total,
            items=items,
            taxa_sucesso_geral=round(taxa_sucesso, 2),
        )

    def get_etl_execucao_erros(
        self,
        execucao_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EtlErroResponse]:
        run = self.repo.get_etl_sync_run(execucao_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execução ETL id {execucao_id} não encontrada",
            )

        _, rows = self.repo.list_etl_erros(execucao_id, limit=limit, offset=offset)
        return [
            EtlErroResponse(
                id=int(r["id"]),
                execucao_id=int(r["execucao_id"]) if r.get("execucao_id") else None,
                tabela_origem=r.get("tabela_origem"),
                id_origem=r.get("id_origem"),
                erro=r.get("erro"),
                linha_raw=r.get("linha_raw"),
                criado_em=r.get("criado_em"),
            )
            for r in rows
        ]
