"""Independent conformance suite covering SPEC-003 (core/forragem.py).

Written by the tester role, not the implementer. Tests map to requirements
and acceptance criteria of SPEC-003 and verification scenarios in KIT-ACEITE-003.
"""

import ast
import inspect
from pathlib import Path

import pytest

from seugado.core import forragem

ROOT = Path(__file__).resolve().parents[2]
FORRAGEM_PATH = ROOT / "src" / "seugado" / "core" / "forragem.py"
SOURCE = FORRAGEM_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

ALLOWED_MODULES = {"collections.abc"}
EXPECTED_FUNCTIONS = {
    "massa_para_altura",
    "altura_para_massa",
    "consumo_lote_kg_ms_dia",
    "dias_ocupacao",
    "taxa_utilizacao",
    "consumo_individual_kg_ms_dia",
    "consumo_pct_pv",
}


# ==============================================================================
# Structural & Hygiene Conformance (SPEC-003, KIT-ACEITE-003)
# ==============================================================================


def test_file_length_under_300_lines():
    lines = SOURCE.splitlines()
    assert len(lines) <= 300, f"forragem.py has {len(lines)} lines, exceeding 300."


def test_imports_whitelist():
    """Verify that forragem.py only imports from allowed standard modules."""
    for node in ast.walk(TREE):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                assert root_mod in ALLOWED_MODULES, f"Disallowed import: {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_mod = node.module.split(".")[0]
            assert node.module in ALLOWED_MODULES or root_mod in ALLOWED_MODULES, (
                f"Disallowed from-import: {node.module}"
            )


def test_public_api_exact_match():
    """Verify exactly the 7 expected public functions exist in forragem.py."""
    funcs = {
        node.name
        for node in TREE.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    assert funcs == EXPECTED_FUNCTIONS, f"Public API mismatch: {funcs ^ EXPECTED_FUNCTIONS}"


def test_no_default_arguments_on_any_function():
    """CRITICAL (Regra 1 / ADR-010): no function may have default parameter values."""
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef):
            assert len(node.args.defaults) == 0, (
                f"Function '{node.name}' has positional default arguments: {node.args.defaults}"
            )
            assert len(node.args.kw_defaults) == 0 or all(
                kw is None for kw in node.args.kw_defaults
            ), f"Function '{node.name}' has keyword default arguments: {node.args.kw_defaults}"


def test_all_functions_have_type_annotations():
    """Every public function must have type annotations for all args and return."""
    for name in EXPECTED_FUNCTIONS:
        fn = getattr(forragem, name)
        sig = inspect.signature(fn)
        assert sig.return_annotation is not inspect.Signature.empty, (
            f"{name} missing return type annotation"
        )
        for param_name, param in sig.parameters.items():
            assert param.annotation is not inspect.Signature.empty, (
                f"{name} parameter '{param_name}' missing type annotation"
            )


# ==============================================================================
# Canonical Regression Case (05-PARAMETROS-CULTIVARES.md / SPEC-003)
# ==============================================================================


def test_canonical_regression_case():
    # Pre: 4000 kg MS/ha, Pos: 2240 kg MS/ha -> Consumo total = 1760 kg MS/ha
    utilizacao = forragem.taxa_utilizacao(4000.0, 2240.0)
    assert utilizacao == pytest.approx(0.44, abs=0.01)

    # 220 animais, 5.81 ha, 4 dias
    consumo_ind = forragem.consumo_individual_kg_ms_dia(1760.0, 5.81, 4.0, 220)
    assert consumo_ind == pytest.approx(11.62, abs=0.05)

    # Peso medio 479 kg
    consumo_pv = forragem.consumo_pct_pv(consumo_ind, 479.0)
    assert consumo_pv == pytest.approx(2.42, abs=0.02)

    # Dias de ocupacao: consumo do lote = 220 * 11.62 = 2556.4 kg MS/dia
    # Neutralizado: eficiencia = 1.0, taxa_acumulo = 0.0
    dias = forragem.dias_ocupacao(
        massa_atual_kg_ms_ha=4000.0,
        massa_residuo_kg_ms_ha=2240.0,
        taxa_acumulo_kg_ms_ha_dia=0.0,
        area_ha=5.81,
        eficiencia_pastejo=1.0,
        consumo_lote_kg_ms_dia=2556.4,
    )
    assert dias == pytest.approx(4.0, abs=0.05)


def test_consumo_lote_literature_and_multi_category():
    # Literature case: 1 animal, 300 kg, 2.2% PV -> 6.6 kg MS/dia
    assert forragem.consumo_lote_kg_ms_dia([(1, 300.0, 0.022)]) == pytest.approx(6.6)

    # Empty composition -> 0.0
    assert forragem.consumo_lote_kg_ms_dia([]) == 0.0

    # Multi-category composition:
    # 10 animais x 400 kg x 0.02 = 80.0
    # 20 animais x 300 kg x 0.025 = 150.0
    # Total = 230.0
    comp = [(10, 400.0, 0.02), (20, 300.0, 0.025)]
    assert forragem.consumo_lote_kg_ms_dia(comp) == pytest.approx(230.0)


# ==============================================================================
# Hidden Test Cases (KIT-ACEITE-003)
# ==============================================================================


def test_hidden_case_1_dias_ocupacao_with_growth():
    """Hidden Case 1: Closed-form occupation days with non-zero forage accumulation."""
    massa_atual = 3000.0
    massa_residuo = 2000.0
    taxa_acumulo = 50.0
    area = 10.0
    eficiencia = 0.8
    consumo = 4000.0

    # Numerador = (3000 - 2000) * 10 * 0.8 = 8000
    # Denominador = 4000 - (50 * 10 * 0.8) = 4000 - 400 = 3600
    # Esperado = 8000 / 3600 ≈ 2.2222
    resultado = forragem.dias_ocupacao(
        massa_atual_kg_ms_ha=massa_atual,
        massa_residuo_kg_ms_ha=massa_residuo,
        taxa_acumulo_kg_ms_ha_dia=taxa_acumulo,
        area_ha=area,
        eficiencia_pastejo=eficiencia,
        consumo_lote_kg_ms_dia=consumo,
    )
    assert resultado == pytest.approx(8000.0 / 3600.0, abs=0.01)

    # Must NOT equal the naive formula without growth (8000 / 4000 = 2.0)
    assert abs(resultado - 2.0) > 0.1


def test_hidden_case_1_denominador_non_positive_returns_inf():
    """When accumulation replenishes as fast as or faster than herd intake, return inf."""
    # Denominador == 0: consumo = 4000, acumulo_efetivo = 500 * 10 * 0.8 = 4000
    res_zero_denom = forragem.dias_ocupacao(
        massa_atual_kg_ms_ha=3000.0,
        massa_residuo_kg_ms_ha=2000.0,
        taxa_acumulo_kg_ms_ha_dia=500.0,
        area_ha=10.0,
        eficiencia_pastejo=0.8,
        consumo_lote_kg_ms_dia=4000.0,
    )
    assert res_zero_denom == float("inf")

    # Denominador < 0: acumulo_efetivo > consumo
    res_neg_denom = forragem.dias_ocupacao(
        massa_atual_kg_ms_ha=3000.0,
        massa_residuo_kg_ms_ha=2000.0,
        taxa_acumulo_kg_ms_ha_dia=600.0,
        area_ha=10.0,
        eficiencia_pastejo=0.8,
        consumo_lote_kg_ms_dia=4000.0,
    )
    assert res_neg_denom == float("inf")


def test_hidden_case_1_at_or_below_residue_returns_zero():
    """When current mass is at or below residue, occupation days is 0.0."""
    res_equal = forragem.dias_ocupacao(
        massa_atual_kg_ms_ha=2000.0,
        massa_residuo_kg_ms_ha=2000.0,
        taxa_acumulo_kg_ms_ha_dia=50.0,
        area_ha=10.0,
        eficiencia_pastejo=0.8,
        consumo_lote_kg_ms_dia=4000.0,
    )
    assert res_equal == 0.0

    res_below = forragem.dias_ocupacao(
        massa_atual_kg_ms_ha=1500.0,
        massa_residuo_kg_ms_ha=2000.0,
        taxa_acumulo_kg_ms_ha_dia=50.0,
        area_ha=10.0,
        eficiencia_pastejo=0.8,
        consumo_lote_kg_ms_dia=4000.0,
    )
    assert res_below == 0.0


def test_hidden_case_2_exact_inverses_differing_densities():
    """Hidden Case 2: Exact inverses across different densities."""
    # Test case: densidade 250.0, altura 12.0
    densidade_1 = 250.0
    altura_1 = 12.0
    massa_1 = forragem.altura_para_massa(altura_1, densidade_1)
    assert massa_1 == pytest.approx(3000.0, abs=1e-9)
    assert forragem.massa_para_altura(massa_1, densidade_1) == pytest.approx(altura_1, abs=1e-9)

    # Test case: densidade 180.0, altura 25.5
    densidade_2 = 180.0
    altura_2 = 25.5
    massa_2 = forragem.altura_para_massa(altura_2, densidade_2)
    assert massa_2 == pytest.approx(4590.0, abs=1e-9)
    assert forragem.massa_para_altura(massa_2, densidade_2) == pytest.approx(altura_2, abs=1e-9)

    # Test case: densidade 320.0, massa 6400.0
    densidade_3 = 320.0
    massa_3 = 6400.0
    altura_3 = forragem.massa_para_altura(massa_3, densidade_3)
    assert altura_3 == pytest.approx(20.0, abs=1e-9)
    assert forragem.altura_para_massa(altura_3, densidade_3) == pytest.approx(massa_3, abs=1e-9)


def test_hidden_case_3_and_validation_rules():
    """Hidden Case 3: Validation raises ValueError (distinct from 0.0 and inf)."""
    # dias_ocupacao validation
    with pytest.raises(ValueError, match="consumo_lote_kg_ms_dia must be positive"):
        forragem.dias_ocupacao(3000.0, 2000.0, 50.0, 10.0, 0.8, 0.0)
    with pytest.raises(ValueError, match="consumo_lote_kg_ms_dia must be positive"):
        forragem.dias_ocupacao(3000.0, 2000.0, 50.0, 10.0, 0.8, -100.0)
    with pytest.raises(ValueError, match="eficiencia_pastejo"):
        forragem.dias_ocupacao(3000.0, 2000.0, 50.0, 10.0, -0.01, 4000.0)
    with pytest.raises(ValueError, match="eficiencia_pastejo"):
        forragem.dias_ocupacao(3000.0, 2000.0, 50.0, 10.0, 1.01, 4000.0)
    with pytest.raises(ValueError, match="area_ha must be positive"):
        forragem.dias_ocupacao(3000.0, 2000.0, 50.0, 0.0, 0.8, 4000.0)
    with pytest.raises(ValueError, match="area_ha must be positive"):
        forragem.dias_ocupacao(3000.0, 2000.0, 50.0, -5.0, 0.8, 4000.0)

    # massa_para_altura validation
    with pytest.raises(ValueError, match="densidade_kg_ha_por_cm must be positive"):
        forragem.massa_para_altura(1000.0, 0.0)
    with pytest.raises(ValueError, match="densidade_kg_ha_por_cm must be positive"):
        forragem.massa_para_altura(1000.0, -10.0)
    with pytest.raises(ValueError, match="massa_kg_ms_ha must be non-negative"):
        forragem.massa_para_altura(-1.0, 100.0)

    # altura_para_massa validation
    with pytest.raises(ValueError, match="densidade_kg_ha_por_cm must be positive"):
        forragem.altura_para_massa(20.0, 0.0)
    with pytest.raises(ValueError, match="densidade_kg_ha_por_cm must be positive"):
        forragem.altura_para_massa(20.0, -5.0)
    with pytest.raises(ValueError, match="altura_cm must be non-negative"):
        forragem.altura_para_massa(-0.5, 100.0)

    # consumo_lote_kg_ms_dia validation
    with pytest.raises(ValueError, match="n_animais must be non-negative"):
        forragem.consumo_lote_kg_ms_dia([(-1, 300.0, 0.022)])
    with pytest.raises(ValueError, match="peso_medio_kg must be positive"):
        forragem.consumo_lote_kg_ms_dia([(1, 0.0, 0.022)])
    with pytest.raises(ValueError, match="peso_medio_kg must be positive"):
        forragem.consumo_lote_kg_ms_dia([(1, -50.0, 0.022)])
    with pytest.raises(ValueError, match="fracao_consumo_pv"):
        forragem.consumo_lote_kg_ms_dia([(1, 300.0, 0.0)])
    with pytest.raises(ValueError, match="fracao_consumo_pv"):
        forragem.consumo_lote_kg_ms_dia([(1, 300.0, -0.01)])
    with pytest.raises(ValueError, match="fracao_consumo_pv"):
        forragem.consumo_lote_kg_ms_dia([(1, 300.0, 1.01)])

    # taxa_utilizacao validation
    with pytest.raises(ValueError, match="massa_pre_pastejo_kg_ms_ha must be positive"):
        forragem.taxa_utilizacao(0.0, 2000.0)
    with pytest.raises(ValueError, match="massa_pre_pastejo_kg_ms_ha must be positive"):
        forragem.taxa_utilizacao(-100.0, 2000.0)
    with pytest.raises(ValueError, match="massa_pos_pastejo_kg_ms_ha must be non-negative"):
        forragem.taxa_utilizacao(4000.0, -10.0)
    with pytest.raises(ValueError, match="must not exceed pre-grazing mass"):
        forragem.taxa_utilizacao(4000.0, 4001.0)

    # consumo_individual_kg_ms_dia validation
    with pytest.raises(ValueError, match="area_ha must be positive"):
        forragem.consumo_individual_kg_ms_dia(1760.0, 0.0, 4.0, 220)
    with pytest.raises(ValueError, match="area_ha must be positive"):
        forragem.consumo_individual_kg_ms_dia(1760.0, -1.0, 4.0, 220)
    with pytest.raises(ValueError, match="dias_ocupacao must be positive"):
        forragem.consumo_individual_kg_ms_dia(1760.0, 5.81, 0.0, 220)
    with pytest.raises(ValueError, match="dias_ocupacao must be positive"):
        forragem.consumo_individual_kg_ms_dia(1760.0, 5.81, -2.0, 220)
    with pytest.raises(ValueError, match="n_animais must be positive"):
        forragem.consumo_individual_kg_ms_dia(1760.0, 5.81, 4.0, 0)
    with pytest.raises(ValueError, match="n_animais must be positive"):
        forragem.consumo_individual_kg_ms_dia(1760.0, 5.81, 4.0, -5)

    # consumo_pct_pv validation
    with pytest.raises(ValueError, match="peso_medio_kg must be positive"):
        forragem.consumo_pct_pv(11.62, 0.0)
    with pytest.raises(ValueError, match="peso_medio_kg must be positive"):
        forragem.consumo_pct_pv(11.62, -100.0)
