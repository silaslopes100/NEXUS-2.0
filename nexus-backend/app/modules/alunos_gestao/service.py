"""Regras de negócio da Central de Alunos (RN-04: Churn e reingresso)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.alunos_gestao.repository import (
    LICENCAS_REINGRESSO,
    AlunosGestaoRepositoryInterface,
    ConflitoNegocio,
    DadosReingresso,
    FiltrosAlunos,
)
from app.modules.alunos_gestao.schemas import (
    AcademicoResponse,
    AlunoGestaoListResponse,
    AlunoGestaoResponse,
    ConteudoAprendizadoResponse,
    CursoAcademicoResponse,
    CursoAprendizadoResponse,
    DisciplinaAcademicaResponse,
    DisciplinaAprendizadoResponse,
    ReingressoRequest,
    ReingressoResponse,
)
from app.modules.transferencias.repository import DIAS_CHURN
from app.modules.transferencias.service import Ator, validar_destino

_ENCERRADAS = ("aprovado", "reprovado")
_SITUACAO_LABEL_EM_CURSO = "cursando"


def _erro(codigo: int, detalhe: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=detalhe)


def _texto(valor: Any) -> Optional[str]:
    return str(valor) if valor else None


def _parado(referencia: Optional[datetime]) -> bool:
    if referencia is None:
        return False
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - referencia > timedelta(days=DIAS_CHURN)


def _observacoes(aluno: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    if aluno.get("tem_certificado"):
        tags.append("formado")
    if aluno.get("status") == "desistente":
        tags.append("churn")
    if aluno.get("transferido"):
        tags.append("transferido")
    if aluno.get("revalidado_em"):
        tags.append("revalidado")
    if aluno.get("status") == "ativo" and _parado(aluno.get("referencia_movimentacao")):
        tags.append("sem_movimentacao")
    return tags


class AlunosGestaoService:
    def __init__(self, repo: AlunosGestaoRepositoryInterface) -> None:
        self.repo = repo

    # ---------- Escopo ----------

    def _filtros(
        self,
        ator: Ator,
        polo_id: Optional[str],
        escola_id: Optional[str],
        somente_ead: bool,
        observacao: Optional[str],
        q: Optional[str],
    ) -> FiltrosAlunos:
        if ator.perfil in ("admin", "secretario_geral"):
            return FiltrosAlunos(polo_id, escola_id, somente_ead, observacao, q)
        if ator.perfil == "polo" and ator.polo_id:
            return FiltrosAlunos(ator.polo_id, escola_id, False, observacao, q)
        if ator.perfil == "escola" and ator.escola_id:
            return FiltrosAlunos(None, ator.escola_id, False, observacao, q)
        raise _erro(status.HTTP_403_FORBIDDEN, "Usuário sem vínculo com Polo ou Escola")

    def _aluno_no_escopo(self, ator: Ator, aluno_id: str) -> Dict[str, Any]:
        aluno = self.repo.get_aluno(aluno_id)
        if not aluno:
            raise _erro(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
        if ator.perfil in ("admin", "secretario_geral"):
            return aluno
        autorizado = (ator.perfil == "polo" and _texto(aluno.get("polo_id")) == ator.polo_id) or (
            ator.perfil == "escola" and _texto(aluno.get("escola_id")) == ator.escola_id
        )
        if not autorizado or not (ator.polo_id or ator.escola_id):
            raise _erro(status.HTTP_403_FORBIDDEN, "Aluno fora da sua unidade")
        return aluno

    # ---------- Listagem e Boletim ----------

    def listar(
        self,
        ator: Ator,
        polo_id: Optional[str],
        escola_id: Optional[str],
        somente_ead: bool,
        observacao: Optional[str],
        q: Optional[str],
        limit: int,
        offset: int,
    ) -> AlunoGestaoListResponse:
        filtros = self._filtros(ator, polo_id, escola_id, somente_ead, observacao, q)
        total, linhas = self.repo.listar(filtros, limit, offset)
        itens = []
        for a in linhas:
            aulas = int(a.get("total_aulas") or 0)
            presentes = int(a.get("presentes") or 0)
            itens.append(
                AlunoGestaoResponse(
                    id=str(a["id"]),
                    usuario_id=str(a["usuario_id"]),
                    numero_matricula=a.get("numero_matricula"),
                    nome=a.get("nome") or "",
                    email=a.get("email"),
                    modalidade=a.get("modalidade"),
                    status=a.get("status") or "ativo",
                    polo_id=_texto(a.get("polo_id")),
                    polo_nome=a.get("polo_nome"),
                    escola_id=_texto(a.get("escola_id")),
                    escola_nome=a.get("escola_nome"),
                    turmas=a.get("turmas") or [],
                    percentual_presenca=round(presentes / aulas * 100, 2) if aulas else 0.0,
                    ultimo_acesso_em=a.get("ultimo_login_em"),
                    disciplinas_em_curso=int(a.get("disciplinas_em_curso") or 0),
                    observacoes=_observacoes(a),
                    reingresso_polo_destino_id=_texto(a.get("reingresso_polo_destino_id")),
                    reingresso_escola_destino_id=_texto(a.get("reingresso_escola_destino_id")),
                )
            )
        return AlunoGestaoListResponse(total=total, items=itens, limit=limit, offset=offset)

    def academico(self, ator: Ator, aluno_id: str) -> AcademicoResponse:
        aluno = self._aluno_no_escopo(ator, aluno_id)
        cursos: Dict[str, CursoAcademicoResponse] = {}
        for linha in self.repo.academico(aluno_id):
            curso_id = str(linha["curso_id"])
            curso = cursos.setdefault(
                curso_id,
                CursoAcademicoResponse(id=curso_id, nome=linha["curso_nome"], disciplinas=[]),
            )
            situacao = linha.get("situacao") or _SITUACAO_LABEL_EM_CURSO
            total = int(linha.get("total_conteudos") or 0)
            concluidos = int(linha.get("conteudos_concluidos") or 0)
            nota = linha.get("nota")
            curso.disciplinas.append(
                DisciplinaAcademicaResponse(
                    id=str(linha["disciplina_id"]),
                    nome=linha["disciplina_nome"],
                    semestre=linha.get("semestre"),
                    carga_horaria=linha.get("carga_horaria"),
                    nota=float(nota) if nota is not None else None,
                    situacao=situacao,
                    em_curso=aluno.get("status") == "ativo" and situacao not in _ENCERRADAS,
                    total_conteudos=total,
                    conteudos_concluidos=concluidos,
                    progresso=round(concluidos / total * 100) if total else None,
                )
            )
        return AcademicoResponse(
            aluno_id=str(aluno["id"]),
            aluno_nome=aluno.get("nome") or "",
            numero_matricula=aluno.get("numero_matricula"),
            cursos=list(cursos.values()),
        )

    # ---------- Churn ----------

    def confirmar_churn(self, aluno_id: str, ator_id: str, ip: Optional[str]) -> None:
        try:
            encontrado = self.repo.confirmar_churn(aluno_id, ator_id, ip)
        except ConflitoNegocio as exc:
            raise _erro(status.HTTP_409_CONFLICT, str(exc)) from exc
        if not encontrado:
            raise _erro(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")

    def reingressar(
        self, aluno_id: str, dados: ReingressoRequest, ator_id: str, ip: Optional[str]
    ) -> ReingressoResponse:
        if not dados.taxa_confirmada:
            raise _erro(status.HTTP_400_BAD_REQUEST, "Confirme o pagamento da taxa de R$ 100,00")

        polo_id = _texto(dados.polo_destino_id)
        escola_id = _texto(dados.escola_destino_id)
        if dados.modalidade == "ead":
            polo_id = escola_id = None
        else:
            validar_destino(self.repo, polo_id, escola_id, status.HTTP_400_BAD_REQUEST)
        licencas = LICENCAS_REINGRESSO if dados.modalidade == "polo" else 0

        try:
            matricula = self.repo.reingressar(
                aluno_id, DadosReingresso(dados.modalidade, polo_id, escola_id, licencas), ator_id, ip
            )
        except ConflitoNegocio as exc:
            raise _erro(status.HTTP_409_CONFLICT, str(exc)) from exc
        if matricula is None:
            raise _erro(status.HTTP_404_NOT_FOUND, "Aluno não encontrado")
        return ReingressoResponse(
            aluno_id=aluno_id, numero_matricula=matricula, licencas_debitadas=licencas
        )

    # ---------- Aprendizado do aluno ----------

    def _aluno_do_usuario(self, usuario_id: str) -> Dict[str, Any]:
        aluno = self.repo.get_aluno_por_usuario(usuario_id)
        if not aluno:
            raise _erro(status.HTTP_404_NOT_FOUND, "Cadastro de aluno não encontrado")
        return aluno

    def aprendizado(self, usuario_id: str) -> List[CursoAprendizadoResponse]:
        aluno = self._aluno_do_usuario(usuario_id)
        cursos: Dict[str, CursoAprendizadoResponse] = {}
        disciplinas: Dict[str, DisciplinaAprendizadoResponse] = {}
        for linha in self.repo.aprendizado(str(aluno["id"])):
            curso_id = str(linha["curso_id"])
            curso = cursos.setdefault(
                curso_id,
                CursoAprendizadoResponse(id=curso_id, nome=linha["curso_nome"], disciplinas=[]),
            )
            disciplina_id = str(linha["disciplina_id"])
            chave = f"{curso_id}:{disciplina_id}"
            if chave not in disciplinas:
                disciplinas[chave] = DisciplinaAprendizadoResponse(
                    id=disciplina_id, nome=linha["disciplina_nome"], conteudos=[]
                )
                curso.disciplinas.append(disciplinas[chave])
            if linha.get("conteudo_id"):
                disciplinas[chave].conteudos.append(
                    ConteudoAprendizadoResponse(
                        id=str(linha["conteudo_id"]),
                        titulo=linha.get("titulo"),
                        tipo_midia=linha.get("tipo_midia"),
                        url_arquivo=linha.get("url_arquivo"),
                        arquivo_nome=linha.get("arquivo_nome"),
                        arquivo_mime_type=linha.get("arquivo_mime_type"),
                        arquivo_tamanho_bytes=linha.get("arquivo_tamanho_bytes"),
                        tem_arquivo=bool(linha.get("tem_arquivo")),
                        concluido=bool(linha.get("concluido")),
                    )
                )
        return list(cursos.values())

    def arquivo_conteudo(self, usuario_id: str, conteudo_id: str) -> Dict[str, Any]:
        aluno = self._aluno_do_usuario(usuario_id)
        if aluno.get("status") != "ativo":
            raise _erro(status.HTTP_403_FORBIDDEN, "Regularize sua situação para continuar os estudos")
        arquivo = self.repo.arquivo_conteudo_do_aluno(str(aluno["id"]), conteudo_id)
        if not arquivo:
            raise _erro(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado nos seus cursos")
        return arquivo

    def marcar_conteudo(self, usuario_id: str, conteudo_id: str, concluido: bool) -> None:
        aluno = self._aluno_do_usuario(usuario_id)
        if aluno.get("status") != "ativo":
            raise _erro(status.HTTP_403_FORBIDDEN, "Regularize sua situação para continuar os estudos")
        aluno_id = str(aluno["id"])
        if not self.repo.conteudo_do_aluno(aluno_id, conteudo_id):
            raise _erro(status.HTTP_404_NOT_FOUND, "Conteúdo não encontrado nos seus cursos")
        self.repo.marcar_conteudo(aluno_id, conteudo_id, concluido)
