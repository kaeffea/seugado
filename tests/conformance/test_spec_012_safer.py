"""Independent conformance suite covering SPEC-012 (SAFER daily forage accumulation rate).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-012 and verification scenarios in KIT-ACEITE-012.
"""

import ast
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

from seugado.sensing.safer import ResultadoSafer, SaferForaDaFaixa, taxa_acumulo_safer

ROOT = Path(__file__).resolve().parents[2]
SAFER_PY = ROOT / "src" / "seugado" / "sensing" / "safer.py"


# ==============================================================================
# Structural Checks (KIT-ACEITE-012)
# ==============================================================================


def test_file_under_300_lines() -> None:
    """src/seugado/sensing/safer.py must stay under 300 lines."""
    lines = SAFER_PY.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 300, f"File exceeds 300 lines: {len(lines)}"


def test_only_allowed_imports_math_and_dataclasses() -> None:
    """Module imports only math and dataclasses (pure functions, no numpy, no I/O)."""
    tree = ast.parse(SAFER_PY.read_text(encoding="utf-8"))
    allowed = {"math", "dataclasses"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg in allowed, f"Disallowed import: {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_pkg = node.module.split(".")[0]
            assert root_pkg in allowed, f"Disallowed from-import: {node.module}"


def test_safer_fora_da_faixa_subclasses_value_error() -> None:
    """SaferForaDaFaixa is a subclass of ValueError."""
    assert issubclass(SaferForaDaFaixa, ValueError)


def test_resultado_safer_frozen_slotted_and_fields_order() -> None:
    """ResultadoSafer is frozen, slotted, and defines exact 6 fields in order."""
    assert is_dataclass(ResultadoSafer)
    params = getattr(ResultadoSafer, "__dataclass_params__", None)
    assert params is not None and params.frozen is True
    assert hasattr(ResultadoSafer, "__slots__")

    expected_fields = [
        "albedo",
        "rn_w_m2",
        "t0_c",
        "etf",
        "rfa_absorvida_w_m2",
        "taxa_acumulo_kg_ms_ha_dia",
    ]
    actual_fields = [f.name for f in fields(ResultadoSafer)]
    assert actual_fields == expected_fields


def test_etf_formula_uses_t0_c_not_kelvin() -> None:
    """Verify in source code that ETf equation uses t0_c in Celsius, not kelvin."""
    content = SAFER_PY.read_text(encoding="utf-8")
    assert "t0_c / (albedo * ndvi)" in content or "t0_c / (albedo*ndvi)" in content


# ==============================================================================
# Canonical Case (KIT-ACEITE-012)
# ==============================================================================


def test_canonical_worked_example() -> None:
    """Worked example from spec reproduces all variables within tolerance (taxa 107.6 +- 1.0)."""
    r = taxa_acumulo_safer(
        ndvi=0.80,
        refletancia_red=0.04,
        refletancia_nir=0.35,
        rg_mj_m2_dia=20.0,
        t_media_c=26.0,
        ra_mj_m2_dia=35.0,
        et0_media_anual_mm_dia=4.5,
        rue_max_g_por_mj=2.31,
    )
    assert r.albedo == pytest.approx(0.1454, abs=0.0005)
    assert r.rn_w_m2 == pytest.approx(116.79, abs=0.5)
    assert r.t0_c == pytest.approx(31.44, abs=0.1)
    assert r.etf == pytest.approx(0.627, abs=0.005)
    assert r.rfa_absorvida_w_m2 == pytest.approx(86.02, abs=0.3)
    assert r.taxa_acumulo_kg_ms_ha_dia == pytest.approx(107.6, abs=1.0)


# ==============================================================================
# Casos que a spec não mostra (KIT-ACEITE-012)
# ==============================================================================


def test_hidden_case_1_intermediate_and_final_values() -> None:
    """Caso 1: ndvi=0.62, red=0.06, nir=0.28, rg=17.5, t=24.0, ra=33.4, et0=4.2, rue=2.31."""
    r = taxa_acumulo_safer(
        ndvi=0.62,
        refletancia_red=0.06,
        refletancia_nir=0.28,
        rg_mj_m2_dia=17.5,
        t_media_c=24.0,
        ra_mj_m2_dia=33.4,
        et0_media_anual_mm_dia=4.2,
        rue_max_g_por_mj=2.31,
    )
    assert r.albedo == pytest.approx(0.1438, abs=0.0005)
    assert r.t0_c == pytest.approx(29.66, abs=0.1)
    assert r.etf == pytest.approx(0.355, abs=0.005)
    assert r.taxa_acumulo_kg_ms_ha_dia == pytest.approx(39.0, abs=0.5)


def test_hidden_case_2_f_rfa_less_or_equal_zero_returns_zero_taxa() -> None:
    """Caso 2: ndvi=0.10 (f_rfa <= 0) -> taxa 0.0, sem exceção (ETf check skipped)."""
    # 1.257 * 0.10 - 0.161 = -0.0353 <= 0
    r = taxa_acumulo_safer(
        ndvi=0.10,
        refletancia_red=0.04,
        refletancia_nir=0.35,
        rg_mj_m2_dia=20.0,
        t_media_c=26.0,
        ra_mj_m2_dia=35.0,
        et0_media_anual_mm_dia=4.5,
        rue_max_g_por_mj=2.31,
    )
    assert r.rfa_absorvida_w_m2 == 0.0
    assert r.taxa_acumulo_kg_ms_ha_dia == 0.0


def test_hidden_case_3_tau_greater_or_equal_one_raises_value_error() -> None:
    """Caso 3: rg=40, ra=35 (tau >= 1) -> ValueError."""
    # tau_sw = 40 / 35 = 1.1428 >= 1.0
    with pytest.raises(ValueError, match="tau_sw"):
        taxa_acumulo_safer(
            ndvi=0.80,
            refletancia_red=0.04,
            refletancia_nir=0.35,
            rg_mj_m2_dia=40.0,
            t_media_c=26.0,
            ra_mj_m2_dia=35.0,
            et0_media_anual_mm_dia=4.5,
            rue_max_g_por_mj=2.31,
        )


# ==============================================================================
# Additional Sanity Check Rules (SPEC-012)
# ==============================================================================


@pytest.mark.parametrize(
    "param_name,bad_val",
    [
        ("ndvi", -0.1),
        ("ndvi", 0.0),
        ("ndvi", 1.05),
        ("refletancia_red", -0.01),
        ("refletancia_red", 1.01),
        ("refletancia_nir", -0.01),
        ("refletancia_nir", 1.01),
        ("rg_mj_m2_dia", 0.0),
        ("rg_mj_m2_dia", -5.0),
        ("ra_mj_m2_dia", 0.0),
        ("ra_mj_m2_dia", -5.0),
        ("rue_max_g_por_mj", 0.0),
        ("rue_max_g_por_mj", -1.0),
        ("et0_media_anual_mm_dia", 0.0),
        ("et0_media_anual_mm_dia", -2.0),
    ],
)
def test_input_range_violations_raise_plain_value_error(param_name: str, bad_val: float) -> None:
    """Input boundary violations raise plain ValueError, not SaferForaDaFaixa."""
    base = {
        "ndvi": 0.80,
        "refletancia_red": 0.04,
        "refletancia_nir": 0.35,
        "rg_mj_m2_dia": 20.0,
        "t_media_c": 26.0,
        "ra_mj_m2_dia": 35.0,
        "et0_media_anual_mm_dia": 4.5,
        "rue_max_g_por_mj": 2.31,
    }
    base[param_name] = bad_val
    with pytest.raises(ValueError):
        taxa_acumulo_safer(**base)


def test_etf_outside_range_raises_safer_fora_da_faixa() -> None:
    """etf outside [0.05, 1.3] raises SaferForaDaFaixa."""
    base = {
        "ndvi": 0.80,
        "refletancia_red": 0.04,
        "refletancia_nir": 0.35,
        "rg_mj_m2_dia": 20.0,
        "t_media_c": 26.0,
        "ra_mj_m2_dia": 35.0,
        "et0_media_anual_mm_dia": 4.5,
        "rue_max_g_por_mj": 2.31,
    }
    # High ET0 pushes ETf > 1.3
    with pytest.raises(SaferForaDaFaixa, match="etf"):
        taxa_acumulo_safer(**{**base, "et0_media_anual_mm_dia": 15.0})

    # Very low ET0 pushes ETf < 0.05
    with pytest.raises(SaferForaDaFaixa, match="etf"):
        taxa_acumulo_safer(**{**base, "et0_media_anual_mm_dia": 0.2})


def test_taxa_outside_range_raises_safer_fora_da_faixa() -> None:
    """taxa outside [0, 150] raises SaferForaDaFaixa."""
    base = {
        "ndvi": 0.80,
        "refletancia_red": 0.04,
        "refletancia_nir": 0.35,
        "rg_mj_m2_dia": 20.0,
        "t_media_c": 26.0,
        "ra_mj_m2_dia": 35.0,
        "et0_media_anual_mm_dia": 4.5,
        "rue_max_g_por_mj": 2.31,
    }
    # Huge rue_max pushes taxa > 150
    with pytest.raises(SaferForaDaFaixa, match="taxa"):
        taxa_acumulo_safer(**{**base, "rue_max_g_por_mj": 4.0})
