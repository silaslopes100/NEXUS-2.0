"""Regras de negócio do módulo `aulas`.

RN03 (Regras de Negócio – Carga Horária): em turmas com cronograma gerado, toda ata cumpre
uma aula prevista pendente, ou é uma aula não prevista com tipo e justificativa. Turmas sem
cronograma continuam aceitando a ata livre (não abate horas) até o cronograma ser gerado.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.auth.roles import perfil_do_usuario
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
    AulasPendentesResponse,
    AulaTipoUpdateRequest,
    AulaUpdateRequest,
    DisciplinaAulasResumo,
    FiltrosAuditoriaResponse,
    MaterialAula,
)
from app.modules.auth.schemas import UserResponse
from app.modules.carga_horaria.repository import (
    CargaHorariaRepositoryInterface,
    get_carga_horaria_repository,
)
from app.modules.carga_horaria.schemas import (
    ROTULO_TIPO,
    TIPOS_COMPLEMENTARES,
    TIPOS_QUE_ABATEM,
    AulaPrevistaResponse,
    RegrasCalendario,
)
from app.modules.carga_horaria.service import regras_do_calendario
from app.modules.professores.access import usuario_eh_professor

# Tipos que exigem aula prevista de referência (Extra é opcional).
_REFERENCIA_OBRIGATORIA = ("prevista", "reposicao", "reforco", "complemento", "revisao")


def _texto(valor: Optional[str]) -> Optional[str]:
    limpo = (valor or "").strip()
    return limpo or None


class AulasService:
    def __init__(
        self,
        repo: Optional[AulasRepositoryInterface] = None,
        carga_repo: Optional[CargaHorariaRepositoryInterface] = None,
    ) -> None:
        self._repo = repo
        self._carga_repo = carga_repo

    @property
    def repo(self) -> AulasRepositoryInterface:
        return self._repo or get_aulas_repository()

    @property
    def carga(self) -> CargaHorariaRepositoryInterface:
        return self._carga_repo or get_carga_horaria_repository()

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

    def _proximo_numero_livre(self, vinculo_id: str, data_aula: date, inicial: int) -> int:
        numero = inicial
        while self.repo.chave_em_uso(vinculo_id, data_aula, numero):
            numero += 1
        return numero

    # ---------- Contexto de carga horária (calendário da turma) ----------

    def _contexto(self, turma_id: Optional[str], disciplina_id: Optional[str]) -> Dict[str, Any]:
        turma = self.carga.contexto_turma(turma_id) if turma_id else None
        regras = regras_do_calendario(turma.get("calendario")) if turma else RegrasCalendario()
        previstas = self.carga.listar_aulas_previstas(turma_id) if turma else []
        return {
            "turma": turma,
            "regras": regras,
            "cronograma": bool(previstas),
            "previstas": [a for a in previstas if str(a["disciplina_id"]) == str(disciplina_id)],
        }

    @staticmethod
    def _validar_periodo(ctx: Dict[str, Any], data_aula: date) -> None:
        turma = ctx["turma"]
        if not turma or not ctx["regras"].bloquear_ata_fora_periodo:
            return
        inicio, fim = turma.get("data_inicio"), turma.get("data_fim")
        if (inicio and data_aula < inicio) or (fim and data_aula > fim):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"A data da aula precisa estar dentro do período da turma "
                       f"({inicio:%d/%m/%Y} a {fim:%d/%m/%Y})." if inicio and fim else
                       "A data da aula está fora do período da turma.",
            )

    def _validar_tipo(
        self,
        ctx: Dict[str, Any],
        tipo: str,
        aula_prevista_id: Optional[str],
        justificativa: Optional[str],
        ignorar_ata_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Regras RN03.1–RN03.3. Devolve a aula prevista de referência (ou None)."""
        if ctx["turma"] and ctx["turma"].get("concluida_em"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Turma concluída: não aceita novas atas.")
        previstas = {str(a["id"]): a for a in ctx["previstas"]}
        referencia = previstas.get(str(aula_prevista_id)) if aula_prevista_id else None
        if aula_prevista_id and not referencia:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A aula prevista de referência não pertence a esta turma e disciplina.",
            )

        if tipo in TIPOS_COMPLEMENTARES:
            if not justificativa:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Informe a justificativa da aula não prevista ({ROTULO_TIPO[tipo]}).",
                )
            if ctx["cronograma"] and tipo in _REFERENCIA_OBRIGATORIA and not referencia:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{ROTULO_TIPO[tipo]} precisa indicar a aula prevista de referência.",
                )
            return referencia

        # prevista / reposição: cumprem uma aula prevista pendente.
        if not ctx["cronograma"]:
            if tipo == "reposicao":
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Reposição exige o cronograma da turma (gere o cronograma primeiro).",
                )
            return None  # turma sem cronograma: ata livre, não abate horas
        if tipo == "reposicao" and not justificativa:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe a justificativa da Reposição.")
        if not referencia:
            pendentes = [a for a in ctx["previstas"] if a["status"] == "pendente"]
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Escolha a aula prevista pendente que esta ata cumpre." if pendentes else
                "Esta disciplina não tem aula prevista pendente: registre como Extra, Reforço, "
                "Complemento ou Revisão.",
            )
        if referencia["status"] != "pendente" and referencia.get("ata_id") != ignorar_ata_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"A aula prevista nº {referencia['numero']} já foi realizada"
                       + (" (por reposição)." if referencia["status"] == "realizada_reposicao" else "."),
            )
        return referencia

    def pendentes(self, user: UserResponse, vinculo_id: str) -> AulasPendentesResponse:
        vinculo = self._vinculo_permitido(user, vinculo_id)
        ctx = self._contexto(vinculo.get("turma_id"), vinculo.get("disciplina_id"))
        pendentes = [a for a in ctx["previstas"] if a["status"] == "pendente"]
        if not ctx["cronograma"]:
            tipos = ["prevista", "extra", "reforco", "complemento", "revisao"]
        elif pendentes:
            tipos = ["prevista", "reposicao", "extra", "reforco", "complemento", "revisao"]
        else:
            tipos = list(TIPOS_COMPLEMENTARES)  # RN03.5: sem pendente, só os que não abatem horas
        turma = ctx["turma"] or {}
        return AulasPendentesResponse(
            cronograma_gerado=ctx["cronograma"],
            turma_data_inicio=turma.get("data_inicio"),
            turma_data_fim=turma.get("data_fim"),
            tipos_permitidos=tipos,
            pendentes=[AulaPrevistaResponse(**a) for a in pendentes],
            previstas=[AulaPrevistaResponse(**a) for a in ctx["previstas"]],
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
        vinculo = self._vinculo_permitido(user, dados.professor_disciplina_id)
        ctx = self._contexto(vinculo.get("turma_id"), vinculo.get("disciplina_id"))
        self._validar_periodo(ctx, dados.data_aula)
        justificativa = _texto(dados.justificativa)
        referencia = self._validar_tipo(ctx, dados.tipo, dados.aula_prevista_id, justificativa)

        numero = dados.numero_aula
        if dados.tipo in TIPOS_QUE_ABATEM and referencia:
            numero = int(referencia["numero"])
            self._garantir_chave_livre(dados.professor_disciplina_id, dados.data_aula, numero)
        elif dados.tipo in TIPOS_COMPLEMENTARES:
            # Aula não prevista no mesmo dia de outra: usa o próximo número livre.
            numero = self._proximo_numero_livre(dados.professor_disciplina_id, dados.data_aula, numero)
        else:
            self._garantir_chave_livre(dados.professor_disciplina_id, dados.data_aula, numero)

        horas = dados.horas
        if horas is None and referencia and dados.tipo in TIPOS_QUE_ABATEM:
            horas = float(referencia["horas_previstas"])
        aula_id = self.repo.criar(
            {
                "professor_disciplina_id": dados.professor_disciplina_id,
                "data_aula": dados.data_aula,
                "numero_aula": numero,
                "conteudo_ministrado": _texto(dados.conteudo_ministrado),
                "observacoes": _texto(dados.observacoes),
                "visivel_aluno": dados.visivel_aluno,
                "criado_por": str(user.id),
                "tipo": dados.tipo,
                "aula_prevista_id": str(referencia["id"]) if referencia else None,
                "horas": horas,
                "justificativa": justificativa,
            }
        )
        return self.detalhe(user, aula_id)

    def atualizar(self, user: UserResponse, aula_id: str, dados: AulaUpdateRequest) -> AulaDetalhe:
        aula = self._aula_permitida(user, aula_id)
        enviados = dados.model_dump(exclude_unset=True)
        mudancas: Dict[str, Any] = {}
        for campo in ("conteudo_ministrado", "observacoes", "justificativa"):
            if campo in enviados:
                mudancas[campo] = _texto(enviados[campo])
        if enviados.get("visivel_aluno") is not None:
            mudancas["visivel_aluno"] = enviados["visivel_aluno"]
        if enviados.get("horas") is not None:
            mudancas["horas"] = enviados["horas"]
        if "justificativa" in mudancas and aula.get("tipo") in TIPOS_COMPLEMENTARES and not mudancas["justificativa"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A aula não prevista exige justificativa.")

        nova_data = enviados.get("data_aula") or aula["data_aula"]
        novo_numero = enviados.get("numero_aula") or aula["numero_aula"]
        if nova_data != aula["data_aula"]:
            self._validar_periodo(self._contexto(aula.get("turma_id"), aula.get("disciplina_id")), nova_data)
        if (nova_data, novo_numero) != (aula["data_aula"], aula["numero_aula"]):
            self._garantir_chave_livre(aula["professor_disciplina_id"], nova_data, novo_numero, aula_id)
            # Sempre os dois juntos: a chamada é movida para a nova chave.
            mudancas["data_aula"] = nova_data
            mudancas["numero_aula"] = novo_numero

        if mudancas:
            self.repo.atualizar(aula_id, mudancas)
        return self.detalhe(user, aula_id)

    def alterar_tipo(
        self, user: UserResponse, aula_id: str, dados: AulaTipoUpdateRequest, ip: Optional[str] = None
    ) -> AulaDetalhe:
        """RN03.5: o tipo só muda por perfil de coordenação (parâmetro do calendário), com auditoria."""
        aula = self._aula_permitida(user, aula_id)
        ctx = self._contexto(aula.get("turma_id"), aula.get("disciplina_id"))
        perfil = perfil_do_usuario(user)
        if perfil not in ctx["regras"].perfis_alteram_tipo_aula:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Somente a coordenação pode alterar o tipo da aula depois do registro.",
            )
        justificativa = _texto(dados.justificativa) if dados.justificativa is not None else aula.get("justificativa")
        referencia = self._validar_tipo(ctx, dados.tipo, dados.aula_prevista_id, justificativa, ignorar_ata_id=aula_id)
        mudancas: Dict[str, Any] = {
            "tipo": dados.tipo,
            "aula_prevista_id": str(referencia["id"]) if referencia else None,
            "justificativa": justificativa,
        }
        if dados.tipo in TIPOS_QUE_ABATEM and referencia and int(referencia["numero"]) != int(aula["numero_aula"]):
            self._garantir_chave_livre(aula["professor_disciplina_id"], aula["data_aula"], int(referencia["numero"]), aula_id)
            mudancas.update(data_aula=aula["data_aula"], numero_aula=int(referencia["numero"]))
        self.repo.atualizar(aula_id, mudancas)
        self.carga.auditar(
            user.id, "aula_tipo_alterado", "aulas_ministradas", aula_id,
            antes={"tipo": aula.get("tipo"), "aula_prevista_id": aula.get("aula_prevista_id")},
            depois={"tipo": dados.tipo, "aula_prevista_id": mudancas["aula_prevista_id"]}, ip=ip,
        )
        return self.detalhe(user, aula_id)

    def excluir(self, user: UserResponse, aula_id: str, ip: Optional[str] = None) -> List[str]:
        aula = self._aula_permitida(user, aula_id)
        abate = aula.get("tipo", "prevista") in TIPOS_QUE_ABATEM and aula.get("aula_prevista_id")
        if abate:
            ctx = self._contexto(aula.get("turma_id"), aula.get("disciplina_id"))
            if not ctx["regras"].excluir_ata_devolve_saldo and perfil_do_usuario(user) != "admin":
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail="Esta ata abate horas da disciplina: só a Diretoria pode excluí-la.",
                )
        chaves = self.repo.excluir(aula_id)
        if abate:
            # A aula prevista volta a Pendente (o status é derivado da ata) e as horas voltam ao saldo.
            self.carga.auditar(
                user.id, "ata_excluida_saldo_devolvido", "aulas_ministradas", aula_id,
                antes={"tipo": aula.get("tipo"), "aula_prevista_id": aula.get("aula_prevista_id"),
                       "data_aula": str(aula.get("data_aula")), "horas": aula.get("horas")}, ip=ip,
            )
        return chaves

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
