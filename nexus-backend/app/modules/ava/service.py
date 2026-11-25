"""Regras do gestor de conteúdo do AVA (admin).

Fluxo: a disciplina nasce no CRUD de Disciplinas; aqui o admin monta Capítulos >> Aulas >> Itens.
Uma aula do tipo 'avaliacao' aponta para uma avaliação de uma disciplina do mesmo curso.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.blob_upload import MB, EscopoUpload
from app.modules.ava import embed as embed_mod
from app.modules.ava.repository import Dono, PostgresAvaRepository, uuid_valido
from app.modules.ava.schemas import (
    AulaCreateIn,
    AulaIn,
    AulaOut,
    AvaliacaoOpcaoOut,
    CapituloIn,
    CapituloOut,
    ConfigIn,
    ConfigOut,
    DisciplinaAvaOut,
    EmbedOut,
    EstruturaOut,
    ItemIn,
    ItemOut,
    ReordenarIn,
)
from app.modules.comunicacao.sanitizar import sanitizar_html, texto_do_html

_IMAGENS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
_DOCS = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/plain": "txt",
    "application/zip": "zip",
}

AVA_UPLOAD = EscopoUpload(
    prefixo="ava",
    categorias={"imagem": (10 * MB, _IMAGENS), "documento": (50 * MB, _DOCS)},
    rota_local="/ava/arquivos/local",
    rotulo="AVA",
    nome_item="Arquivo",
)


def _texto(valor: Optional[str]) -> Optional[str]:
    limpo = (valor or "").strip()
    return limpo or None


def _item_out(r: Dict[str, Any]) -> ItemOut:
    return ItemOut(**{k: r.get(k) for k in ItemOut.model_fields if k in r})


def _aula_out(r: Dict[str, Any]) -> AulaOut:
    base = {k: r.get(k) for k in AulaOut.model_fields if k in r and k != "itens"}
    return AulaOut(**base, itens=[_item_out(i) for i in r.get("itens") or []])


def _capitulo_out(r: Dict[str, Any]) -> CapituloOut:
    return CapituloOut(id=r["id"], titulo=r["titulo"], descricao=r.get("descricao"), ordem=r.get("ordem") or 0,
                       publicado=bool(r.get("publicado")), aulas=[_aula_out(a) for a in r.get("aulas") or []])


class AvaAdminService:
    def __init__(self, repo: PostgresAvaRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------ disciplinas

    def disciplinas(self, curso_id: str, q: Optional[str]) -> List[DisciplinaAvaOut]:
        if not self.repo.curso_existe(curso_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Curso não encontrado.")
        return [DisciplinaAvaOut(**r) for r in self.repo.listar_disciplinas(curso_id, _texto(q))]

    def _disciplina(self, disciplina_id: str) -> Dict[str, Any]:
        d = self.repo.get_disciplina(disciplina_id)
        if not d:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada.")
        return d

    def config(self, disciplina_id: str) -> ConfigOut:
        self._disciplina(disciplina_id)
        return ConfigOut(**self.repo.get_config(disciplina_id))

    def salvar_config(self, disciplina_id: str, dados: ConfigIn) -> ConfigOut:
        self._disciplina(disciplina_id)
        registro = dados.model_dump()
        registro["capa_url"] = _texto(registro.get("capa_url"))
        registro["descricao_ava"] = _texto(registro.get("descricao_ava"))
        self.repo.salvar_config(disciplina_id, registro)
        return self.config(disciplina_id)

    def estrutura(self, disciplina_id: str) -> EstruturaOut:
        d = self._disciplina(disciplina_id)
        capitulos = self.repo.estrutura(("disciplina_id", disciplina_id))
        return EstruturaOut(disciplina=DisciplinaAvaOut(**d), config=ConfigOut(**self.repo.get_config(disciplina_id)),
                            capitulos=[_capitulo_out(c) for c in capitulos])

    # ------------------------------------------------------------------ capítulos

    def _capitulo(self, capitulo_id: str) -> Dict[str, Any]:
        cap = self.repo.get_capitulo(capitulo_id)
        if not cap:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Capítulo não encontrado.")
        return cap

    def _capitulo_da_estrutura(self, dono: Dono, capitulo_id: str) -> CapituloOut:
        for c in self.repo.estrutura(dono):
            if c["id"] == capitulo_id:
                return _capitulo_out(c)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Capítulo não encontrado.")

    @staticmethod
    def _dono(registro: Dict[str, Any]) -> Dono:
        if registro.get("disciplina_id"):
            return ("disciplina_id", str(registro["disciplina_id"]))
        return ("treinamento_id", str(registro["treinamento_id"]))

    def criar_capitulo(self, dono: Dono, dados: CapituloIn) -> CapituloOut:
        registro = {"titulo": dados.titulo.strip(), "descricao": _texto(dados.descricao), "publicado": dados.publicado}
        novo = self.repo.criar_capitulo(dono, registro)
        return self._capitulo_da_estrutura(dono, novo)

    def criar_capitulo_disciplina(self, disciplina_id: str, dados: CapituloIn) -> CapituloOut:
        self._disciplina(disciplina_id)
        return self.criar_capitulo(("disciplina_id", disciplina_id), dados)

    def atualizar_capitulo(self, capitulo_id: str, dados: CapituloIn) -> CapituloOut:
        cap = self._capitulo(capitulo_id)
        self.repo.atualizar_capitulo(capitulo_id, {"titulo": dados.titulo.strip(), "descricao": _texto(dados.descricao),
                                                   "publicado": dados.publicado})
        return self._capitulo_da_estrutura(self._dono(cap), capitulo_id)

    async def excluir_capitulo(self, capitulo_id: str) -> None:
        self._capitulo(capitulo_id)
        await self._limpar_arquivos(self.repo.excluir_capitulo(capitulo_id))

    def duplicar_capitulo(self, capitulo_id: str) -> CapituloOut:
        cap = self._capitulo(capitulo_id)
        novo = self.repo.duplicar_capitulo(capitulo_id)
        return self._capitulo_da_estrutura(self._dono(cap), novo)

    # ------------------------------------------------------------------ aulas

    def _aula(self, aula_id: str) -> Dict[str, Any]:
        aula = self.repo.get_aula(aula_id)
        if not aula:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aula não encontrada.")
        return aula

    def aula(self, aula_id: str) -> AulaOut:
        aula = self._aula(aula_id)
        for cap in self.repo.estrutura(self._dono(aula)):
            for a in cap["aulas"]:
                if a["id"] == aula_id:
                    return _aula_out(a)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aula não encontrada.")

    def _validar_avaliacao(self, dados: AulaIn, dono_cap: Dict[str, Any]) -> Optional[str]:
        if dados.tipo != "avaliacao":
            return None
        if not dados.avaliacao_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Escolha a avaliação da aula.")
        av = self.repo.get_avaliacao(dados.avaliacao_id)
        if not av:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Avaliação não encontrada.")
        if dono_cap.get("disciplina_id"):
            disciplina = self._disciplina(str(dono_cap["disciplina_id"]))
            if not disciplina.get("curso_id") or str(av.get("curso_id")) != str(disciplina["curso_id"]):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="A avaliação precisa ser de uma disciplina do mesmo curso.")
        return str(av["id"])

    def _registro_aula(self, dados: AulaIn, dono_cap: Dict[str, Any]) -> Dict[str, Any]:
        registro = dados.model_dump(exclude={"capitulo_id"})
        registro["titulo"] = dados.titulo.strip()
        registro["descricao"] = sanitizar_html(dados.descricao, variante="aviso") or None
        registro["capa_url"] = _texto(dados.capa_url)
        registro["avaliacao_id"] = self._validar_avaliacao(dados, dono_cap)
        return registro

    def criar_aula(self, dados: AulaCreateIn) -> AulaOut:
        cap = self._capitulo(dados.capitulo_id)
        novo = self.repo.criar_aula(dados.capitulo_id, self._registro_aula(dados, cap))
        return self.aula(novo)

    async def atualizar_aula(self, aula_id: str, dados: AulaIn) -> AulaOut:
        aula = self._aula(aula_id)
        self.repo.atualizar_aula(aula_id, self._registro_aula(dados, aula))
        if dados.tipo == "avaliacao" and aula.get("tipo") != "avaliacao":
            await self._limpar_arquivos(self.repo.remover_itens_da_aula(aula_id))
        return self.aula(aula_id)

    async def excluir_aula(self, aula_id: str) -> None:
        self._aula(aula_id)
        await self._limpar_arquivos(self.repo.excluir_aula(aula_id))

    # ------------------------------------------------------------------ itens

    def _registro_item(self, dados: ItemIn, anterior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        r: Dict[str, Any] = {"tipo": dados.tipo, "titulo": _texto(dados.titulo), "url": None, "provedor": None,
                             "embed_id": None, "conteudo_html": None, "arquivo_pathname": None, "arquivo_nome": None,
                             "arquivo_mime": None, "arquivo_tamanho": None,
                             "permite_download": dados.permite_download}
        if dados.tipo == "video_embed":
            if not dados.url:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o link do vídeo.")
            e = embed_mod.resolver_embed(dados.url)
            r.update(url=e["embed_url"], provedor=e["provedor"], embed_id=e["embed_id"])
        elif dados.tipo == "link":
            if not dados.url:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o link.")
            r["url"] = embed_mod.normalizar_url(dados.url)
        elif dados.tipo == "texto":
            html = sanitizar_html(dados.conteudo_html, variante="aviso")
            if not texto_do_html(html):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Escreva o texto.")
            r["conteudo_html"] = html
        elif not dados.arquivo and anterior and anterior.get("tipo") == dados.tipo and anterior.get("arquivo_pathname"):
            # Edição sem trocar o arquivo: mantém o já enviado.
            for k in ("url", "arquivo_pathname", "arquivo_nome", "arquivo_mime", "arquivo_tamanho"):
                r[k] = anterior.get(k)
            r["titulo"] = r["titulo"] or anterior.get("arquivo_nome")
        else:  # arquivo / imagem
            if not dados.arquivo:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie o arquivo.")
            a = AVA_UPLOAD.validar_anexo(url=dados.arquivo.url, pathname=dados.arquivo.pathname,
                                         nome=dados.arquivo.nome, mime=dados.arquivo.mime,
                                         tamanho=dados.arquivo.tamanho)
            if dados.tipo == "imagem" and AVA_UPLOAD.categoria_do_mime(a.mime) != "imagem":
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie uma imagem (JPG, PNG, WEBP).")
            r.update(url=a.url, arquivo_pathname=a.storage_key, arquivo_nome=a.nome, arquivo_mime=a.mime,
                     arquivo_tamanho=a.tamanho)
            r["titulo"] = r["titulo"] or a.nome
        return r

    def _item(self, item_id: str) -> Dict[str, Any]:
        item = self.repo.get_item(item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item não encontrado.")
        return item

    def criar_item(self, aula_id: str, dados: ItemIn) -> ItemOut:
        aula = self._aula(aula_id)
        if aula["tipo"] == "avaliacao":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Aulas de avaliação não têm conteúdos.")
        novo = self.repo.criar_item(aula_id, self._registro_item(dados))
        return _item_out(self.repo.get_item(novo))

    async def atualizar_item(self, item_id: str, dados: ItemIn) -> ItemOut:
        antigo = self._item(item_id)
        registro = self._registro_item(dados, antigo)
        self.repo.atualizar_item(item_id, registro)
        if antigo.get("arquivo_pathname") and antigo.get("url") != registro.get("url"):
            await self._limpar_arquivos([antigo["url"]])
        return _item_out(self.repo.get_item(item_id))

    async def excluir_item(self, item_id: str) -> None:
        item = self._item(item_id)
        self.repo.excluir_item(item_id)
        if item.get("arquivo_pathname"):
            await self._limpar_arquivos([item["url"]])

    # ------------------------------------------------------------------ ordenação / apoio

    def reordenar_disciplina(self, disciplina_id: str, dados: ReordenarIn) -> EstruturaOut:
        self._disciplina(disciplina_id)
        for lista in (dados.capitulos, dados.aulas, dados.itens):
            if any(not uuid_valido(x.id) for x in lista):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Identificador inválido.")
        if any(not uuid_valido(a.capitulo_id) for a in dados.aulas):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Identificador inválido.")
        self.repo.reordenar(("disciplina_id", disciplina_id), [c.model_dump() for c in dados.capitulos],
                            [a.model_dump() for a in dados.aulas], [i.model_dump() for i in dados.itens])
        return self.estrutura(disciplina_id)

    def avaliacoes_do_curso(self, curso_id: str) -> List[AvaliacaoOpcaoOut]:
        if not self.repo.curso_existe(curso_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Curso não encontrado.")
        return [AvaliacaoOpcaoOut(**r) for r in self.repo.avaliacoes_do_curso(curso_id)]

    @staticmethod
    def resolver_embed(url: str) -> EmbedOut:
        return EmbedOut(**embed_mod.resolver_embed(url))

    async def _limpar_arquivos(self, urls: List[str]) -> None:
        """Só remove do armazenamento os arquivos que nenhum outro item (ex.: cópia) ainda usa."""
        em_uso = self.repo.urls_em_uso(urls)
        await AVA_UPLOAD.excluir([u for u in urls if u not in em_uso])
