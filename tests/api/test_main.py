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


def test_obter_token_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /auth/token with valid credentials returns access_token."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    class RespostaToken:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"access_token": "token123", "token_type": "bearer"}

    def fake_post(*args: object, **kwargs: object) -> RespostaToken:
        return RespostaToken()

    monkeypatch.setattr(httpx, "post", fake_post)
    response = client.post("/auth/token", data={"username": "user@test.com", "password": "pass"})
    assert response.status_code == 200
    assert response.json() == {"access_token": "token123", "token_type": "bearer"}


def test_obter_token_credenciais_invalidas(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /auth/token with invalid credentials returns 401."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    class RespostaErro:
        status_code = 400

        def json(self) -> dict[str, str]:
            return {"error": "invalid_grant"}

    def fake_post(*args: object, **kwargs: object) -> RespostaErro:
        return RespostaErro()

    monkeypatch.setattr(httpx, "post", fake_post)
    response = client.post("/auth/token", data={"username": "user@test.com", "password": "wrong"})
    assert response.status_code == 401


def test_openapi_authorize_button_and_security() -> None:
    """OpenAPI schema defines OAuth2PasswordBearer with /auth/token and secures routes."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()

    sec_schemes = schema["components"]["securitySchemes"]
    assert "OAuth2PasswordBearer" in sec_schemes
    oauth_config = sec_schemes["OAuth2PasswordBearer"]
    assert oauth_config["type"] == "oauth2"
    assert oauth_config["flows"]["password"]["tokenUrl"] == "/auth/token"

    # Verify that POST /clientes requires the OAuth2 scheme
    post_clientes = schema["paths"]["/clientes"]["post"]
    assert any("OAuth2PasswordBearer" in s for s in post_clientes.get("security", []))


def test_criar_cliente_apos_autorizacao(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /clientes works when authenticated with bearer token."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    user_id = str(uuid.uuid4())

    class RespostaUserOk:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"id": user_id, "email": "admin@seugado.com"}

    monkeypatch.setattr(httpx, "get", lambda *a, **k: RespostaUserOk())

    from seugado.cadastro import clientes
    from seugado.cadastro.clientes import Cliente

    cliente_mock = Cliente(
        id=uuid.uuid4(),
        nome="Cliente Teste",
        telefone="82999990000",
        observacoes=None,
    )
    monkeypatch.setattr(clientes, "criar_cliente", lambda conn, dados: cliente_mock)

    # 1. Without token: returns 401
    resp_unauth = client.post(
        "/clientes", json={"nome": "Cliente Teste", "telefone": "82999990000"}
    )
    assert resp_unauth.status_code == 401

    # 2. With token: returns 201
    resp_auth = client.post(
        "/clientes",
        json={"nome": "Cliente Teste", "telefone": "82999990000"},
        headers={"Authorization": "Bearer valid_token"},
    )
    assert resp_auth.status_code == 201
    assert resp_auth.json()["nome"] == "Cliente Teste"
