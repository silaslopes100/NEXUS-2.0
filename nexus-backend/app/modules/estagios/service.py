"""Regras da Central de Estágio: etapas encadeadas, envio/reenvio, avaliação, relatórios e arquivos-base."""
from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, quote, urlparse

from fastapi import HTTPException, Response, status

from app.core.blob_upload import MB, EscopoUpload
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.estagios import pdf as pdf_mod
from app.modules.estagios.repository import EstagiosRepositoryInterface, SubmissaoIndisponivel
from app.modules.estagios.schemas import (
    BASE_LABEL,
    ETAPAS,
    FOTOS_MAX,
    FOTOS_MIN,
    HORAS_POR_ETAPA,
    ORDEM_ETAPAS,
    STATUS_LABEL,
    ArquivoBaseOut,
    ArquivoIn,
    AvaliacaoIn,
    CentralAlunoOut,
    EnvioIn,
    EtapaAlunoOut,
    FiltrosRelatorio,
    FiltrosSubmissoes,
    RelatorioLinhaOut,
    RelatorioOut,
    SubmissaoDetalheOut,
    SubmissaoOut,
    SubmissoesPage,
)
from app.modules.financeiro import exportacao as exp
from app.modules.notificacoes import notificar, notificar_perfil

logger = logging.getLogger(__name__)

_DOCS = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
_IMAGENS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

ESCOPO_UPLOAD = EscopoUpload(
    prefixo="estagio",
    categorias={"documento": (30 * MB, _DOCS), "imagem": (10 * MB, _IMAGENS)},
    rota_local="/estagios/arquivos/local",
    rotulo="estágio",
)

# Tipos aceitos em cada campo (o limite de tamanho vem do escopo).
_ACEITOS_ENVIO = {"carta": {**_DOCS, **_IMAGENS}, "relatorio": {**_DOCS, **_IMAGENS}, "foto": _IMAGENS}
_ACEITOS_BASE = {"manual": {"application/pdf"}, "carta_modelo": set(_DOCS), "relatorio_modelo": set(_DOCS)}
_ROTULO_CAMPO = {"carta": "Carta de Apresentação", "relatorio": "Relatório de Estágio", "foto": "foto"}

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_embed(url: Optional[str]) -> Optional[str]:
    """Converte links do YouTube (watch, youtu.be, shorts, live, embed) para o formato embed."""
    url = (url or "").strip()
    if not url:
        return None
    alvo = urlparse(url if "://" in url else f"https://{url}")
    host = (alvo.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    video_id = None
    if host == "youtu.be":
        video_id = alvo.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "youtube-nocookie.com"}:
        if alvo.path == "/watch":
            video_id = (parse_qs(alvo.query).get("v") or [""])[0]
        else:
            partes = [p for p in alvo.path.split("/") if p]
            if len(partes) >= 2 and partes[0] in {"embed", "shorts", "live", "v"}:
                video_id = partes[1]
    if not video_id or not _YOUTUBE_ID.fullmatch(video_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Informe um link válido do YouTube (ex.: https://www.youtube.com/watch?v=...).")
    return f"https://www.youtube.com/embed/{video_id}"


def _escopo_unidade(user: UserResponse) -> Dict[str, Optional[str]]:
    perfil = perfil_do_usuario(user)
    if perfil == "admin":
        return {}
    if perfil == "polo" and user.polo_id:
        return {"polo_id": str(user.polo_id)}
    if perfil == "escola" and user.escola_id:
        return {"escola_id": str(user.escola_id)}
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil sem acesso aos estágios da unidade.")


def _codigo_comprovante() -> str:
    return f"EST-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"


class EstagiosService:
    def __init__(self, repo: EstagiosRepositoryInterface,
                 notificar_fn: Callable[..., Any] = notificar,
                 notificar_admins: Callable[..., Any] = lambda **kw: notificar_perfil("admin", **kw)) -> None:
        self.repo = repo
        self._notificar = notificar_fn
        self._notificar_admins = notificar_admins

    # ------------------------------------------------------------------ helpers

    def _aluno(self, user: UserResponse) -> Dict[str, Any]:
        aluno = self.repo.get_aluno_por_usuario(str(user.id))
        if not aluno:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cadastro de aluno não encontrado.")
        return aluno

    @staticmethod
    def _submissao_out(s: Dict[str, Any]) -> SubmissaoOut:
        return SubmissaoOut(**{**s, "etapa_titulo": ETAPAS[s["etapa"]]["titulo"],
                               "arquivos": s.get("arquivos") or [], "eventos": s.get("eventos") or []})

    @staticmethod
    def _detalhe_out(s: Dict[str, Any]) -> SubmissaoDetalheOut:
        return SubmissaoDetalheOut(**{**s, "etapa_titulo": ETAPAS[s["etapa"]]["titulo"],
                                      "arquivos": s.get("arquivos") or [], "eventos": s.get("eventos") or []})

    def _arquivos_base(self) -> List[ArquivoBaseOut]:
        salvos = {b["chave"]: b for b in self.repo.arquivos_base()}
        saida = []
        for chave, titulo in BASE_LABEL.items():
            b = salvos.get(chave)
            saida.append(ArquivoBaseOut(chave=chave, titulo=titulo, disponivel=bool(b),
                                        **({k: b.get(k) for k in ("nome", "mime", "tamanho", "url", "atualizado_em")}
                                           if b else {})))
        return saida

    def _validar_arquivo(self, arquivo: ArquivoIn, campo: str) -> Dict[str, Any]:
        mime = (arquivo.mime or "").split(";", 1)[0].strip().lower()
        if mime not in _ACEITOS_ENVIO[campo]:
            esperado = "imagem JPG, PNG ou WEBP" if campo == "foto" else "PDF, DOC, DOCX ou imagem"
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                detail=f"{_ROTULO_CAMPO[campo].capitalize()}: envie {esperado}.")
        validado = ESCOPO_UPLOAD.validar_anexo(url=arquivo.url, pathname=arquivo.pathname, nome=arquivo.nome,
                                               mime=mime, tamanho=arquivo.tamanho)
        return {"tipo": campo, "nome": validado.nome, "mime": validado.mime, "tamanho": validado.tamanho,
                "url": validado.url, "storage_key": validado.storage_key}

    # ------------------------------------------------------------------ uploads

    def emitir_upload(self, nome: str, mime: str, tamanho: int) -> Dict[str, object]:
        return ESCOPO_UPLOAD.emitir_upload(nome, mime, tamanho)

    # ------------------------------------------------------------------ aluno

    def central(self, user: UserResponse) -> CentralAlunoOut:
        aluno = self._aluno(user)
        por_etapa = {s["etapa"]: s for s in self.repo.submissoes_do_aluno(aluno["id"])}
        etapas: List[EtapaAlunoOut] = []
        anterior_aprovada = True
        horas = 0
        for etapa in ORDEM_ETAPAS:
            info = ETAPAS[etapa]
            s = por_etapa.get(etapa)
            bloqueada = not anterior_aprovada
            if s and s["status"] == "aprovado":
                horas += int(s.get("horas") or HORAS_POR_ETAPA)
            etapas.append(EtapaAlunoOut(
                etapa=etapa, titulo=str(info["titulo"]), ordem=int(info["ordem"]), descricao=str(info["descricao"]),
                bloqueada=bloqueada, pode_enviar=not bloqueada and (s is None or s["status"] == "negado"),
                submissao=self._submissao_out(s) if s else None,
            ))
            anterior_aprovada = bool(s and s["status"] == "aprovado")
        try:
            self.repo.marcar_vistos(aluno["id"])
        except Exception:  # noqa: BLE001 — contador do menu é acessório
            logger.exception("Falha ao marcar avaliações de estágio como vistas")
        return CentralAlunoOut(video_url=self.repo.get_config().get("video_url"),
                               arquivos_base=self._arquivos_base(), etapas=etapas, horas_cumpridas=horas)

    def resumo_aluno(self, user: UserResponse) -> int:
        aluno = self.repo.get_aluno_por_usuario(str(user.id))
        return self.repo.contar_nao_vistos(aluno["id"]) if aluno else 0

    async def enviar(self, user: UserResponse, etapa: str, dados: EnvioIn) -> SubmissaoOut:
        if etapa not in ETAPAS:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Etapa de estágio inexistente.")
        aluno = self._aluno(user)
        por_etapa = {s["etapa"]: s for s in self.repo.submissoes_do_aluno(aluno["id"])}
        indice = ORDEM_ETAPAS.index(etapa)
        if indice > 0:
            anterior = por_etapa.get(ORDEM_ETAPAS[indice - 1])
            if not anterior or anterior["status"] != "aprovado":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail=f"{ETAPAS[etapa]['titulo']} é liberada após a aprovação do estágio de "
                           f"{ETAPAS[ORDEM_ETAPAS[indice - 1]]['titulo']}.",
                )
        atual = por_etapa.get(etapa)
        if atual and atual["status"] != "negado":
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail=f"Esta etapa já está {STATUS_LABEL[atual['status']].lower()}.")
        if not FOTOS_MIN <= len(dados.fotos) <= FOTOS_MAX:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Envie de {FOTOS_MIN} a {FOTOS_MAX} fotos.")
        arquivos = [self._validar_arquivo(dados.carta, "carta"), self._validar_arquivo(dados.relatorio, "relatorio")]
        arquivos += [self._validar_arquivo(f, "foto") for f in dados.fotos]
        if len({a["storage_key"] for a in arquivos}) != len(arquivos):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="O mesmo arquivo foi informado mais de uma vez.")
        try:
            submissao_id, antigos, reenvio = self.repo.salvar_envio(aluno["id"], etapa, arquivos, str(user.id))
        except SubmissaoIndisponivel:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail="Esta etapa já tem uma documentação em análise ou aprovada.") from None
        if antigos:
            await ESCOPO_UPLOAD.excluir(antigos)
        titulo_etapa = ETAPAS[etapa]["titulo"]
        self._notificar_admins(
            titulo=f"{'Reenvio' if reenvio else 'Nova documentação'} de estágio: {aluno.get('nome') or 'Aluno'}",
            mensagem=f"Estágio de {titulo_etapa} aguardando análise.",
            link=f"/admin/estagios?submissao={submissao_id}",
        )
        s = self.repo.get_submissao(submissao_id)
        return self._submissao_out(s)

    # ------------------------------------------------------------------ comprovante

    def comprovante(self, user: UserResponse, submissao_id: str) -> Response:
        s = self.repo.get_submissao(submissao_id)
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação de estágio não encontrada.")
        perfil = perfil_do_usuario(user)
        aluno = s.get("aluno") or {}
        dono = aluno.get("usuario_id") == str(user.id)
        if not dono and perfil != "admin":
            escopo = _escopo_unidade(user)
            if (escopo.get("polo_id") and aluno.get("polo_id") != escopo["polo_id"]) or \
                    (escopo.get("escola_id") and aluno.get("escola_id") != escopo["escola_id"]):
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação de estágio não encontrada.")
        if s["status"] != "aprovado":
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail="O comprovante fica disponível após a aprovação do estágio.")
        conteudo = pdf_mod.gerar_comprovante(s, str(ETAPAS[s["etapa"]]["titulo"]))
        nome = f"comprovante-estagio-{s['etapa']}-{s.get('codigo_comprovante') or s['id']}.pdf"
        return Response(content=conteudo, media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}",
                                 "Cache-Control": "private, no-store"})

    # ------------------------------------------------------------------ admin / unidade

    def listar(self, user: UserResponse, filtros: FiltrosSubmissoes, limit: int, offset: int) -> SubmissoesPage:
        total, itens = self.repo.listar(filtros, _escopo_unidade(user), limit, offset)
        return SubmissoesPage(total=total, itens=[
            {**i, "etapa_titulo": ETAPAS[i["etapa"]]["titulo"]} for i in itens
        ])

    def detalhe(self, user: UserResponse, submissao_id: str) -> SubmissaoDetalheOut:
        s = self.repo.get_submissao(submissao_id)
        escopo = _escopo_unidade(user)
        aluno = (s or {}).get("aluno") or {}
        if not s or (escopo.get("polo_id") and aluno.get("polo_id") != escopo["polo_id"]) or \
                (escopo.get("escola_id") and aluno.get("escola_id") != escopo["escola_id"]):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação de estágio não encontrada.")
        return self._detalhe_out(s)

    def resumo_admin(self) -> int:
        return self.repo.contar_pendentes()

    def avaliar(self, user: UserResponse, submissao_id: str, dados: AvaliacaoIn) -> SubmissaoDetalheOut:
        s = self.repo.get_submissao(submissao_id)
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação de estágio não encontrada.")
        if s["status"] != "em_analise":
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail=f"Esta solicitação já foi avaliada ({STATUS_LABEL[s['status']]}).")
        codigo = _codigo_comprovante() if dados.status == "aprovado" else None
        if not self.repo.avaliar(submissao_id, dados.status, dados.comentario, str(user.id), codigo):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta solicitação já foi avaliada.")
        etapa_titulo = ETAPAS[s["etapa"]]["titulo"]
        destino = (s.get("aluno") or {}).get("usuario_id")
        if dados.status == "aprovado":
            mensagem = "Seu comprovante de cumprimento do estágio já está disponível para download."
            if s["etapa"] == ORDEM_ETAPAS[0]:
                mensagem += f" O estágio de {ETAPAS[ORDEM_ETAPAS[1]]['titulo']} foi liberado."
            if dados.comentario:
                mensagem += f" Comentário: {dados.comentario}"
            self._notificar(titulo=f"Estágio de {etapa_titulo} aprovado", mensagem=mensagem,
                            link="/aluno/estagio", destino_usuario_id=destino)
        else:
            self._notificar(titulo=f"Estágio de {etapa_titulo} negado",
                            mensagem=f"Comentário do Coordenador: {dados.comentario} Corrija e reenvie a documentação.",
                            link="/aluno/estagio", destino_usuario_id=destino)
        return self._detalhe_out(self.repo.get_submissao(submissao_id))

    # ------------------------------------------------------------------ relatórios

    def relatorio(self, user: UserResponse, filtros: FiltrosRelatorio) -> RelatorioOut:
        linhas = []
        for r in self.repo.relatorio(filtros, _escopo_unidade(user)):
            situacao = "concluido" if r.get("teologia_status") == "aprovado" and \
                r.get("homiletica_status") == "aprovado" else "pendente"
            if filtros.situacao and filtros.situacao != situacao:
                continue
            linhas.append(RelatorioLinhaOut(**{**r, "horas_cumpridas": int(r.get("horas_cumpridas") or 0),
                                               "situacao": situacao}))
        concluidos = sum(1 for l in linhas if l.situacao == "concluido")
        return RelatorioOut(total=len(linhas), concluidos=concluidos, pendentes=len(linhas) - concluidos,
                            linhas=linhas)

    def exportar(self, user: UserResponse, filtros: FiltrosRelatorio, formato: str) -> Response:
        rel = self.relatorio(user, filtros)
        exp.garantir_limite(rel.total)
        colunas: List[exp.Coluna] = [
            ("Aluno", 52, "L", "texto"), ("Matrícula", 22, "L", "texto"), ("Polo", 38, "L", "texto"),
            ("Escola", 38, "L", "texto"), ("Teologia do Ministério", 30, "L", "texto"), ("Aprovado em", 20, "C", "data"),
            ("Homilética", 26, "L", "texto"), ("Aprovado em", 20, "C", "data"), ("Horas", 14, "C", "int"),
            ("Situação", 20, "L", "texto"),
        ]
        rotulo = lambda st: STATUS_LABEL.get(st, "Não enviado") if st else "Não enviado"  # noqa: E731
        dados = [[
            l.aluno_nome, l.numero_matricula, l.polo_nome, l.escola_nome, rotulo(l.teologia_status),
            l.teologia_aprovado_em, rotulo(l.homiletica_status), l.homiletica_aprovado_em, l.horas_cumpridas,
            "Concluído" if l.situacao == "concluido" else "Pendente",
        ] for l in rel.linhas]
        partes = []
        if filtros.situacao:
            partes.append(f"Situação: {'Concluído' if filtros.situacao == 'concluido' else 'Pendente'}")
        if filtros.polo_id:
            partes.append(f"Polo: {next((l.polo_nome for l in rel.linhas if l.polo_nome), filtros.polo_id)}")
        if filtros.escola_id:
            partes.append(f"Escola: {next((l.escola_nome for l in rel.linhas if l.escola_nome), filtros.escola_id)}")
        if filtros.de or filtros.ate:
            ini = filtros.de.strftime("%d/%m/%Y") if filtros.de else "início"
            fim = filtros.ate.strftime("%d/%m/%Y") if filtros.ate else "hoje"
            partes.append(f"Período de envio: {ini} a {fim}")
        filtros_txt = " | ".join(partes) or "Sem filtros (todos os registros)"
        if formato == "csv":
            saida = io.StringIO()
            escritor = csv.writer(saida, delimiter=";")
            escritor.writerow([c[0] for c in colunas])
            for linha in dados:
                escritor.writerow(["" if v is None else exp.formatar(v, c[3]) if c[3] == "data" else v
                                   for c, v in zip(colunas, linha)])
            conteudo = ("﻿" + saida.getvalue()).encode("utf-8")  # BOM: acentos corretos no Excel
            return Response(content=conteudo, media_type="text/csv; charset=utf-8",
                            headers={"Content-Disposition":
                                     f'attachment; filename="{exp.nome_arquivo("estagios", "csv")}"'})
        if formato == "xlsx":
            conteudo = exp.planilha_xlsx([("Estágios", colunas, dados)], filtros_txt)
        else:
            pdf = exp.RelatorioPDF("Central de Estágio", filtros_txt, paisagem=True)
            pdf.add_page()
            pdf.pares([("Alunos", str(rel.total)), ("Concluídos", str(rel.concluidos)),
                       ("Pendentes", str(rel.pendentes)), ("Horas cumpridas",
                                                           str(sum(l.horas_cumpridas for l in rel.linhas)))])
            pdf.secao("Alunos")
            pdf.tabela(colunas, dados)
            conteudo = pdf.bytes()
        return exp.resposta_arquivo(conteudo, "estagios", formato)

    # ------------------------------------------------------------------ arquivos-base e config

    def arquivos_base(self) -> List[ArquivoBaseOut]:
        return self._arquivos_base()

    def config(self) -> Dict[str, Any]:
        return {"video_url": self.repo.get_config().get("video_url")}

    async def substituir_base(self, user: UserResponse, chave: str, arquivo: ArquivoIn) -> List[ArquivoBaseOut]:
        if chave not in BASE_LABEL:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Arquivo-base inexistente.")
        mime = (arquivo.mime or "").split(";", 1)[0].strip().lower()
        if mime not in _ACEITOS_BASE[chave]:
            esperado = "PDF" if chave == "manual" else "DOCX, DOC ou PDF"
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                detail=f"{BASE_LABEL[chave]}: envie um arquivo {esperado}.")
        v = ESCOPO_UPLOAD.validar_anexo(url=arquivo.url, pathname=arquivo.pathname, nome=arquivo.nome, mime=mime,
                                        tamanho=arquivo.tamanho)
        antigo = self.repo.salvar_arquivo_base(chave, {"nome": v.nome, "mime": v.mime, "tamanho": v.tamanho,
                                                       "url": v.url, "storage_key": v.storage_key}, str(user.id))
        if antigo and antigo != v.storage_key:
            await ESCOPO_UPLOAD.excluir([antigo])
        return self._arquivos_base()

    def salvar_config(self, video_url: Optional[str]) -> Dict[str, Any]:
        embed = youtube_embed(video_url)
        self.repo.salvar_config(embed)
        return {"video_url": embed}
