"""Independent conformance suite covering SPEC-016 (Web admin shell).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-016 and verification scenarios in KIT-ACEITE-016.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
TIPOS_PATH = SRC_DIR / "lib" / "tipos.ts"
FAZENDA_TSX = SRC_DIR / "lib" / "fazenda.tsx"
LAYOUT_TSX = SRC_DIR / "componentes" / "Layout.tsx"
ROTA_PROTEGIDA_TSX = SRC_DIR / "componentes" / "RotaProtegida.tsx"
APP_TSX = SRC_DIR / "App.tsx"
ONBOARDING_PATH = SRC_DIR / "paginas" / "Onboarding.tsx"


# ==============================================================================
# Structural Checks (KIT-ACEITE-016)
# ==============================================================================


def test_onboarding_removed_and_no_onboarding_route() -> None:
    """paginas/Onboarding.tsx does not exist; no route or reference to /onboarding."""
    assert not ONBOARDING_PATH.exists(), "paginas/Onboarding.tsx must be deleted"

    for file_path in SRC_DIR.rglob("*.tsx"):
        content = file_path.read_text(encoding="utf-8")
        assert "/onboarding" not in content, f"Found '/onboarding' in {file_path}"
        assert "Onboarding" not in content, f"Found 'Onboarding' import/reference in {file_path}"


def test_tipos_ts_r1_declarations_and_unchanged_contracts() -> None:
    """tipos.ts: R1 blocks are identical; other types remain unchanged."""
    content = TIPOS_PATH.read_text(encoding="utf-8")

    # R1 verbatim declarations
    r1_categoria = (
        'export type Categoria = "bezerro" | "bezerra" | "novilho" | "novilha" | "vaca" | "boi"'
        ' | "touro";'
    )
    r1_cliente = (
        "export interface Cliente { id: string; nome: string; telefone: string | null;"
        " observacoes: string | null; }"
    )
    r1_me = "export interface Me { usuario_id: string; email: string | null; }"

    assert r1_categoria in content
    assert r1_cliente in content
    assert r1_me in content

    # Fazenda interface in R1
    assert "export interface Fazenda {" in content
    assert "cliente_id: string | null; cliente_nome: string | null;" in content
    assert "animais_por_funcionario_dia: number;" in content
    assert "envio_plano_dia: number;" in content
    assert "envio_plano_hora: number;" in content
    assert "manejos_por_funcionario_dia" not in content

    # Existing types unchanged
    for t in (
        "export type Confianca =",
        "export type MetodoPastejo =",
        "export type SituacaoPiquete =",
        "export interface Cultivar {",
        "export interface Piquete {",
        "export interface Lote {",
        "export interface Movimentacao {",
        "export interface Alerta {",
        "export interface PlanoManejo {",
    ):
        assert t in content, f"Missing expected unchanged contract {t}"


def test_localstorage_access_in_try_catch() -> None:
    """All accesses to localStorage in lib/fazenda.tsx are wrapped in try/catch."""
    content = FAZENDA_TSX.read_text(encoding="utf-8")
    assert "localStorage" in content, "fazenda.tsx should use localStorage"

    # Find occurrences of localStorage and verify they are inside a try block
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "localStorage" in line:
            # Look backwards for try {
            preceding = "\n".join(lines[max(0, i - 5) : i])
            assert "try {" in preceding or "try" in line, (
                f"localStorage access on line {i + 1} not in try/catch: {line}"
            )


# ==============================================================================
# Hidden Cases (KIT-ACEITE-016)
# ==============================================================================


def test_hidden_case_1_localstorage_unknown_farm_falls_back_to_first() -> None:
    """Caso 1: localStorage com id que não está na lista -> seleciona a primeira fazenda."""
    content = FAZENDA_TSX.read_text(encoding="utf-8")
    # Verify fallback pattern: find by id ?? fazendas[0] ?? null
    pattern = re.compile(r"fazendas\.find\(.*?\)\s*\?\?\s*fazendas\[0\]\s*\?\?\s*null")
    assert pattern.search(content), (
        "Expected fallback to first farm (fazendas.find(...) ?? fazendas[0] ?? null) in fazenda.tsx"
    )


def test_hidden_case_2_empty_fazendas_shows_warning_and_clientes_accessible() -> None:
    """Caso 2: fazendas vazio -> Layout mostra aviso com link para /clientes, e /clientes abre."""
    content = LAYOUT_TSX.read_text(encoding="utf-8")
    assert "Nenhuma fazenda selecionada. Cadastre uma em" in content
    assert '<Link to="/clientes">Clientes e fazendas</Link>' in content
    # Verify exception when pathname is /clientes
    assert 'localizacao.pathname !== "/clientes"' in content
    assert "<Outlet />" in content


def test_hidden_case_3_no_session_plano_redirects_to_login() -> None:
    """Caso 3: Sem sessão -> /plano redireciona para /login."""
    rota_content = ROTA_PROTEGIDA_TSX.read_text(encoding="utf-8")
    app_content = APP_TSX.read_text(encoding="utf-8")

    # RotaProtegida redirects to /login when usuario is null
    assert 'usuario === null' in rota_content
    assert '<Navigate to="/login" replace />' in rota_content

    # /plano is nested within RotaProtegida
    assert '<Route path="/plano" element={<Plano />} />' in app_content
    rota_idx = app_content.find("RotaProtegida")
    plano_idx = app_content.find('path="/plano"')
    assert rota_idx != -1 and plano_idx != -1 and rota_idx < plano_idx
