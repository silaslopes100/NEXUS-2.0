from __future__ import annotations

import runpy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from app.core import file_storage
from app.modules.alunos import perfil


@pytest.mark.parametrize(
    ("vercel_env", "environment"),
    [("production", "development"), ("preview", "development"), ("", "development"),
     ("production", None)],
)
def test_vercel_deploy_rejects_nonproduction_environment(monkeypatch, vercel_env, environment):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", vercel_env)
    if environment is None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
    else:
        monkeypatch.setenv("ENVIRONMENT", environment)

    with pytest.raises(RuntimeError, match="ENVIRONMENT=production"):
        runpy.run_path(str(Path(__file__).resolve().parents[1] / "app" / "core" / "config.py"))


@pytest.mark.parametrize(
    ("vercel", "vercel_env", "environment"),
    [("", "", "development"), ("1", "development", "development"),
     ("1", "production", "production"), ("1", "preview", "production")],
)
def test_environment_config_accepts_local_and_valid_deploys(
    monkeypatch, vercel, vercel_env, environment
):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("VERCEL", vercel)
    monkeypatch.setenv("VERCEL_ENV", vercel_env)
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("PG_DSN", "test-dsn")
    monkeypatch.setenv("CORS_ORIGINS", "https://example.test")

    config = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app" / "core" / "config.py"))
    assert config["settings"].ENVIRONMENT == environment


@pytest.mark.asyncio
async def test_production_academic_files_use_private_blob(monkeypatch):
    monkeypatch.setattr(file_storage.settings, "ENVIRONMENT", "production")
    put = AsyncMock()
    get = AsyncMock(return_value=SimpleNamespace(body=b"%PDF-1.7\nconteudo"))
    delete = AsyncMock()
    monkeypatch.setattr(file_storage.blob, "put_blob", put)
    monkeypatch.setattr(file_storage.blob, "get_blob", get)
    monkeypatch.setattr(file_storage.blob, "delete_blob", delete)

    upload = UploadFile(
        file=BytesIO(b"%PDF-1.7\nconteudo"),
        filename="aula.pdf",
        headers={"content-type": "application/pdf"},
    )
    stored = await file_storage.store_academic_file(upload)

    put.assert_awaited_once_with(
        stored.storage_key, b"%PDF-1.7\nconteudo",
        access="private", content_type="application/pdf",
    )
    assert await file_storage.read_academic_file(stored.storage_key) == b"%PDF-1.7\nconteudo"
    get.assert_awaited_once_with(stored.storage_key, access="private")
    await file_storage.delete_academic_file(stored.storage_key)
    delete.assert_awaited_once_with(stored.storage_key)
    assert perfil._uses_blob_storage()
