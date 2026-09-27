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


class _CursorFalso:
    """Minimal cursor stub: execute is a no-op, fetchone returns one fixed row."""

    def __init__(self, linha: tuple[int, ...] | None) -> None:
        self._linha = linha

    def __enter__(self) -> "_CursorFalso":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, *args: object) -> None:
        return None

    def fetchone(self) -> tuple[int, ...] | None:
        return self._linha


class _ConexaoFalsa:
    """Minimal connection stub exposing cursor()."""

    def __init__(self, linha: tuple[int, ...] | None) -> None:
        self._linha = linha

    def cursor(self) -> _CursorFalso:
        return _CursorFalso(self._linha)


def test_exigir_fazenda_existente_retorna_id() -> None:
    """Any existing farm is returned; every authenticated user is an admin."""
    fazenda_id = uuid.uuid4()
    usuario = auth.UsuarioAtual(id=uuid.uuid4(), email=None)
    assert (
        auth.exigir_fazenda(fazenda_id, usuario, _ConexaoFalsa((1,)))  # type: ignore[arg-type]
        == fazenda_id
    )


def test_exigir_fazenda_desconhecida_retorna_404() -> None:
    """Unknown farm id raises 404."""
    usuario = auth.UsuarioAtual(id=uuid.uuid4(), email=None)
    with pytest.raises(HTTPException) as excinfo:
        auth.exigir_fazenda(uuid.uuid4(), usuario, _ConexaoFalsa(None))  # type: ignore[arg-type]
    assert excinfo.value.status_code == 404


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
