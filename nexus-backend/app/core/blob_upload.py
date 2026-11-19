"""Upload direto do navegador para o armazenamento (Vercel Blob em produção, disco em dev).

O navegador recebe um *client token* de curta duração e envia o arquivo direto ao Blob (store
PÚBLICO, caminho com 128 bits aleatórios). A API nunca trafega o arquivo, então não há o limite
de ~4,5 MB das funções serverless. Sem ``CHAT_BLOB_READ_WRITE_TOKEN`` (desenvolvimento), o arquivo
vai para ``uploads/<prefixo>`` via API.

Cada uso (chat, estágio…) é um :class:`EscopoUpload` com prefixo, tipos aceitos e limites próprios.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Sequence
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

logger = logging.getLogger(__name__)

MB = 1024 * 1024
_TOKEN_VALIDADE_S = 5 * 60
_NOME_LOCAL = re.compile(r"[a-f0-9]{32}\.[a-z0-9]{2,5}")
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


@dataclass(frozen=True)
class AnexoValidado:
    url: str
    storage_key: str
    nome: str
    mime: str
    tamanho: int


def normalizar_mime(mime: Optional[str]) -> str:
    return (mime or "").split(";", 1)[0].strip().lower()


def nome_seguro(nome: Optional[str]) -> str:
    base = (nome or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return (base or "arquivo")[:255]


def usa_blob() -> bool:
    return bool(settings.CHAT_BLOB_READ_WRITE_TOKEN)


def _store_id() -> str:
    partes = settings.CHAT_BLOB_READ_WRITE_TOKEN.split("_")
    if len(partes) < 5 or not partes[3]:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Armazenamento de arquivos mal configurado.")
    return partes[3]


def _gerar_client_token(pathname: str, mime: str, limite: int) -> str:
    """Equivalente a `generateClientTokenFromReadWriteToken` do @vercel/blob."""
    rw = settings.CHAT_BLOB_READ_WRITE_TOKEN
    payload = base64.b64encode(json.dumps({
        "pathname": pathname,
        "allowedContentTypes": [mime],
        "maximumSizeInBytes": limite,
        "addRandomSuffix": False,
        "validUntil": int((time.time() + _TOKEN_VALIDADE_S) * 1000),
    }, separators=(",", ":")).encode()).decode()
    assinatura = hmac.new(rw.encode(), payload.encode(), hashlib.sha256).hexdigest()
    corpo = base64.b64encode(f"{assinatura}.{payload}".encode()).decode()
    return f"vercel_blob_client_{_store_id()}_{corpo}"


@dataclass(frozen=True)
class EscopoUpload:
    """Configuração de um uso do upload direto.

    ``categorias``: nome -> (limite em bytes, {mime: extensão}).
    ``rota_local``: prefixo da API que recebe (POST ``{rota_local}?pathname=``) e serve
    (GET ``{rota_local}/{arquivo}``) os arquivos em desenvolvimento.
    """

    prefixo: str
    categorias: Dict[str, tuple]
    rota_local: str
    rotulo: str = "arquivo"
    nome_item: str = "Arquivo"
    _padrao: re.Pattern = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_padrao", re.compile(rf"^{re.escape(self.prefixo)}/[a-f0-9]{{32}}\.[a-z0-9]{{2,5}}$"))

    @property
    def local_dir(self) -> Path:
        return UPLOADS_DIR / self.prefixo

    @property
    def local_url_prefix(self) -> str:
        return f"{self.rota_local}/"

    def categoria_do_mime(self, mime: str) -> Optional[str]:
        for nome, (_, tipos) in self.categorias.items():
            if mime in tipos:
                return nome
        return None

    def validar_tipo_tamanho(self, mime: str, tamanho: int) -> tuple:
        categoria = self.categoria_do_mime(mime)
        if not categoria:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                detail=f"Tipo de arquivo não permitido no {self.rotulo}.")
        limite, tipos = self.categorias[categoria]
        if tamanho <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio.")
        if tamanho > limite:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                                detail=f"Arquivo muito grande: o limite para {categoria} é {limite // MB} MB.")
        return limite, tipos[mime]

    def emitir_upload(self, nome: str, mime: str, tamanho: int) -> Dict[str, object]:
        """Valida o arquivo pretendido e devolve como enviá-lo."""
        mime = normalizar_mime(mime)
        limite, extensao = self.validar_tipo_tamanho(mime, tamanho)
        pathname = f"{self.prefixo}/{uuid.uuid4().hex}.{extensao}"
        if usa_blob():
            return {"modo": "blob", "pathname": pathname, "token": _gerar_client_token(pathname, mime, limite),
                    "content_type": mime}
        return {"modo": "local", "pathname": pathname, "upload_url": f"{self.rota_local}?pathname={pathname}",
                "content_type": mime}

    def validar_anexo(self, *, url: str, pathname: str, nome: str, mime: str, tamanho: int) -> AnexoValidado:
        """Confere que o arquivo informado pelo cliente pertence a este escopo do store."""
        mime = normalizar_mime(mime)
        _, extensao = self.validar_tipo_tamanho(mime, int(tamanho or 0))
        if not self._padrao.fullmatch(pathname or "") or not pathname.endswith(f".{extensao}"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"{self.nome_item} inválido.")
        if usa_blob():
            alvo = urlparse(url or "")
            host_esperado = f"{_store_id().lower()}.public.blob.vercel-storage.com"
            if alvo.scheme != "https" or (alvo.hostname or "").lower() != host_esperado or alvo.path != f"/{pathname}":
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"{self.nome_item} inválido.")
            url_final = f"https://{host_esperado}/{pathname}"
        else:
            arquivo = self.local_dir / pathname.split("/", 1)[1]
            if not arquivo.is_file():
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"{self.nome_item} não encontrado. Envie o arquivo novamente.")
            url_final = f"{self.local_url_prefix}{arquivo.name}"
        return AnexoValidado(url=url_final, storage_key=pathname, nome=nome_seguro(nome), mime=mime,
                             tamanho=int(tamanho))

    async def salvar_local(self, pathname: str, arquivo: UploadFile) -> Dict[str, str]:
        """Upload em desenvolvimento (sem Blob)."""
        if usa_blob():
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Não encontrado")
        if not self._padrao.fullmatch(pathname or ""):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Caminho inválido.")
        mime = normalizar_mime(arquivo.content_type)
        limite = self.categorias.get(self.categoria_do_mime(mime) or "", (0, {}))[0]
        conteudo = await arquivo.read(limite + 1)
        _, extensao = self.validar_tipo_tamanho(mime, len(conteudo))
        if not pathname.endswith(f".{extensao}"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Tipo de arquivo diferente do informado.")
        self.local_dir.mkdir(parents=True, exist_ok=True)
        destino = self.local_dir / pathname.split("/", 1)[1]
        destino.write_bytes(conteudo)
        return {"url": f"{self.local_url_prefix}{destino.name}", "pathname": pathname}

    def caminho_local(self, arquivo: str) -> Path:
        if usa_blob() or not _NOME_LOCAL.fullmatch(arquivo or ""):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Não encontrado")
        caminho = self.local_dir / arquivo
        if not caminho.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Não encontrado")
        return caminho

    async def excluir(self, refs: Sequence[str]) -> None:
        """Remove arquivos do store (URLs do Blob ou caminhos locais). Falhas só são registradas."""
        refs = [r for r in refs if r]
        if not refs:
            return
        if usa_blob():
            try:
                from vercel import blob
                from vercel.api import session
                from vercel.blob import BlobCredentials, BlobServiceOptions

                credenciais = BlobCredentials(settings.CHAT_BLOB_READ_WRITE_TOKEN, _store_id())
                opcoes = BlobServiceOptions(credentials_factory=lambda: credenciais)
                async with session(service_options=[opcoes]):
                    for i in range(0, len(refs), 1000):
                        await blob.delete_blob(list(refs[i:i + 1000]))
            except Exception:  # noqa: BLE001 — limpeza é acessória
                logger.exception("Falha ao excluir %d arquivo(s) de %s no Blob", len(refs), self.prefixo)
            return
        for ref in refs:
            nome = ref.rsplit("/", 1)[-1]
            if _NOME_LOCAL.fullmatch(nome):
                try:
                    (self.local_dir / nome).unlink(missing_ok=True)
                except OSError:
                    logger.exception("Falha ao excluir arquivo local %s/%s", self.prefixo, nome)
