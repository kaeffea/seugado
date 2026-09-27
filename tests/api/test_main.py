"""API smoke tests."""

import uuid

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from seugado.api import auth
from seugado.api.main import app

client = TestClient(app)


def test_saude() -> None:
    """GET /saude returns ok without auth."""
    response = client.get("/saude")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_usuario_atual_sem_header() -> None:
    """Missing header returns 401."""
    with pytest.raises(HTTPException) as excinfo:
        auth.usuario_atual(None)
    assert excinfo.value.status_code == 401


def test_usuario_atual_sem_bearer() -> None:
    """Header without Bearer prefix returns 401."""
    with pytest.raises(HTTPException) as excinfo:
        auth.usuario_atual("Token abc")
    assert excinfo.value.status_code == 401


def test_usuario_atual_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid token returns the user."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    usuario_id = str(uuid.uuid4())

    class RespostaOk:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"id": usuario_id, "email": "a@b.c"}

    def fake_get(*args: object, **kwargs: object) -> RespostaOk:
        return RespostaOk()

    monkeypatch.setattr(httpx, "get", fake_get)
    usuario = auth.usuario_atual("Bearer token")
    assert str(usuario.id) == usuario_id
    assert usuario.email == "a@b.c"


def test_usuario_atual_token_invalido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-200 from Supabase returns 401."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    class RespostaErro:
        status_code = 401

        def json(self) -> dict[str, str]:
            return {}

    def fake_get(*args: object, **kwargs: object) -> RespostaErro:
        return RespostaErro()

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(HTTPException) as excinfo:
        auth.usuario_atual("Bearer bad")
    assert excinfo.value.status_code == 401
