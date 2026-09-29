"""Independent conformance suite covering SPEC-010 (Esqueleto API e Frontend).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-010 and verification scenarios in KIT-ACEITE-010.
"""

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from seugado.api import auth
from seugado.api.main import app

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "src" / "seugado" / "api"
FRONTEND_DIR = ROOT / "frontend"
SPEC_010_FILE = ROOT / "specs" / "SPEC-010-esqueleto-api-frontend.md"


# ==============================================================================
# Structural Checks (KIT-ACEITE-010)
# ==============================================================================


def test_deps_py_no_commit_and_closed_in_finally() -> None:
    """api/deps.py must not call commit() and must close connection in finally."""
    deps_path = API_DIR / "deps.py"
    content = deps_path.read_text(encoding="utf-8")
    assert "commit(" not in content, "deps.py must never call commit()"

    tree = ast.parse(content)
    has_try_finally_close = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for stmt in node.finalbody:
                if (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Attribute)
                    and stmt.value.func.attr == "close"
                ):
                    has_try_finally_close = True
    assert has_try_finally_close, "deps.py must close connection in finally block"


def test_five_router_modules_are_empty_stubs() -> None:
    """Five router files instantiate APIRouter; unimplemented ones remain stubs."""
    router_files = (
        "rotas_fazenda.py",
        "rotas_lotes.py",
        "rotas_piquetes.py",
        "rotas_plano.py",
        "rotas_telegram.py",
    )
    # rotas_fazenda.py, rotas_lotes.py, rotas_piquetes.py and rotas_telegram.py are implemented
    implemented = {
        "rotas_fazenda.py",
        "rotas_lotes.py",
        "rotas_piquetes.py",
        "rotas_telegram.py",
    }
    for name in router_files:
        path = API_DIR / name
        assert path.exists(), f"Missing router stub: {name}"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        has_router = any(
            isinstance(stmt, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "router"
                for target in stmt.targets
            )
            and isinstance(stmt.value, ast.Call)
            for stmt in tree.body
        )
        assert has_router, f"Router not instantiated in {name}"
        if name in implemented:
            continue
        # Unimplemented routers must only contain docstring, imports, and router = APIRouter(...)
        for stmt in tree.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                continue
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(stmt, ast.Assign):
                target = stmt.targets[0]
                assert isinstance(target, ast.Name) and target.id == "router"
                assert isinstance(stmt.value, ast.Call)
                continue
            pytest.fail(f"Unexpected statement in router stub {name}: {ast.dump(stmt)}")


def test_frontend_tipos_ts_matches_spec() -> None:
    """frontend/src/lib/tipos.ts contains contract types updated for ADR-025/SPEC-016."""
    tipos_path = FRONTEND_DIR / "src" / "lib" / "tipos.ts"
    assert tipos_path.exists(), "frontend/src/lib/tipos.ts does not exist"
    content = tipos_path.read_text(encoding="utf-8")

    # Common contract types unchanged from SPEC-010
    required_types = [
        "export type Confianca =",
        "export type MetodoPastejo =",
        "export type SituacaoPiquete =",
        "export interface Cultivar {",
        "export interface GeoJsonPolygon {",
        "export interface Piquete {",
        "export interface ParametroPendente {",
        "export interface ComposicaoItem {",
        "export interface Lote {",
        "export interface Movimentacao {",
        "export interface Alerta {",
        "export interface PedidoValidacao {",
        "export interface ResumoPiquete {",
        "export interface PlanoManejo {",
    ]
    for req in required_types:
        assert req in content, f"Missing {req} in tipos.ts"

    # Updated types per ADR-025 / SPEC-016
    assert (
        'export type Categoria = "bezerro" | "bezerra" | "novilho" | "novilha" | "vaca" | "boi"'
        ' | "touro";' in content
    )
    assert "export interface Cliente {" in content
    assert "animais_por_funcionario_dia: number;" in content
    assert "manejos_por_funcionario_dia" not in content
    assert "export interface Me { usuario_id: string; email: string | null; }" in content


def test_frontend_package_json_dependencies() -> None:
    """package.json contains only the authorized precondition dependencies."""
    pkg_path = FRONTEND_DIR / "package.json"
    assert pkg_path.exists(), "frontend/package.json missing"
    data = json.loads(pkg_path.read_text(encoding="utf-8"))

    allowed_deps = {
        "react",
        "react-dom",
        "react-router",
        "@supabase/supabase-js",
        "leaflet",
        "react-leaflet",
        "@geoman-io/leaflet-geoman-free",
    }
    actual_deps = set(data.get("dependencies", {}).keys())
    assert actual_deps <= allowed_deps, (
        f"Unauthorized dependencies found: {actual_deps - allowed_deps}"
    )


# ==============================================================================
# Hidden Cases (KIT-ACEITE-010)
# ==============================================================================


def test_hidden_case_1_exigir_fazenda_404() -> None:
    """Caso 1: exigir_fazenda com UUID inexistente dá 404; com existente dá id (ADR-025)."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = None
    path_fazenda_id = uuid4()
    usuario = auth.UsuarioAtual(id=uuid4(), email="user@test.com")

    with pytest.raises(HTTPException) as exc_info:
        auth.exigir_fazenda(path_fazenda_id, usuario, mock_conn)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Fazenda não encontrada"

    # When it exists in the database, it succeeds and returns the UUID
    mock_cur.fetchone.return_value = (1,)
    res = auth.exigir_fazenda(path_fazenda_id, usuario, mock_conn)
    assert res == path_fazenda_id


def test_hidden_case_2_usuario_atual_token_sem_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Caso 2: usuario_atual com Authorization: Token abc levanta 401 sem chamar httpx.get."""
    http_get_called = False

    def fake_get(*args: object, **kwargs: object) -> MagicMock:
        nonlocal http_get_called
        http_get_called = True
        return MagicMock(status_code=200)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(HTTPException) as exc_info:
        auth.usuario_atual("Token abc")

    assert exc_info.value.status_code == 401
    assert not http_get_called, (
        "httpx.get must not be called when Authorization does not start with Bearer"
    )


def test_hidden_case_3_saude_sem_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Caso 3: GET /saude com DATABASE_URL ausente do ambiente retorna 200."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    client = TestClient(app)
    response = client.get("/saude")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
