"""Smoke checks for the SAFER chain."""

import inspect
from dataclasses import FrozenInstanceError

import pytest

from seugado.sensing.safer import ResultadoSafer, SaferForaDaFaixa, taxa_acumulo_safer

BASE = {
    "ndvi": 0.80,
    "refletancia_red": 0.04,
    "refletancia_nir": 0.35,
    "rg_mj_m2_dia": 20.0,
    "t_media_c": 26.0,
    "ra_mj_m2_dia": 35.0,
    "et0_media_anual_mm_dia": 4.5,
    "rue_max_g_por_mj": 2.31,
}


def test_worked_example() -> None:
    r = taxa_acumulo_safer(**BASE)
    assert isinstance(r, ResultadoSafer)
    assert r.albedo == pytest.approx(0.1454, abs=0.0005)
    assert r.rn_w_m2 == pytest.approx(116.79, abs=0.5)
    assert r.t0_c == pytest.approx(31.44, abs=0.1)
    assert r.etf == pytest.approx(0.627, abs=0.005)
    assert r.rfa_absorvida_w_m2 == pytest.approx(86.02, abs=0.3)
    assert r.taxa_acumulo_kg_ms_ha_dia == pytest.approx(107.6, abs=1.0)


def test_signature_result_and_error_shape() -> None:
    assert list(inspect.signature(taxa_acumulo_safer).parameters) == [
        "ndvi",
        "refletancia_red",
        "refletancia_nir",
        "rg_mj_m2_dia",
        "t_media_c",
        "ra_mj_m2_dia",
        "et0_media_anual_mm_dia",
        "rue_max_g_por_mj",
    ]
    assert issubclass(SaferForaDaFaixa, ValueError)
    r = taxa_acumulo_safer(**BASE)
    assert not hasattr(r, "__dict__")
    with pytest.raises(FrozenInstanceError):
        r.etf = 0.0  # type: ignore[misc]  # intentional: verifying frozen raises


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("ndvi", 0.0),
        ("ndvi", 1.5),
        ("refletancia_red", -0.1),
        ("refletancia_nir", 1.2),
        ("rg_mj_m2_dia", 0.0),
        ("ra_mj_m2_dia", 0.0),
        ("et0_media_anual_mm_dia", 0.0),
        ("rue_max_g_por_mj", 0.0),
    ],
)
def test_invalid_inputs_raise_value_error(campo: str, valor: float) -> None:
    with pytest.raises(ValueError, match=campo):  # noqa: PT011 — message asserted via match
        taxa_acumulo_safer(**{**BASE, campo: valor})


def test_tau_above_one_raises_value_error() -> None:
    with pytest.raises(ValueError, match="tau_sw"):  # noqa: PT011 — message asserted via match
        taxa_acumulo_safer(**{**BASE, "rg_mj_m2_dia": 40.0})


def test_bare_soil_returns_zero_taxa() -> None:
    r = taxa_acumulo_safer(**{**BASE, "ndvi": 0.10})
    assert r.rfa_absorvida_w_m2 == 0.0
    assert r.taxa_acumulo_kg_ms_ha_dia == 0.0


def test_etf_out_of_range_raises() -> None:
    with pytest.raises(SaferForaDaFaixa, match="etf"):
        taxa_acumulo_safer(**{**BASE, "et0_media_anual_mm_dia": 12.0})
    with pytest.raises(SaferForaDaFaixa, match="etf"):
        taxa_acumulo_safer(**{**BASE, "et0_media_anual_mm_dia": 0.3})


def test_taxa_out_of_range_raises() -> None:
    with pytest.raises(SaferForaDaFaixa, match="taxa"):
        taxa_acumulo_safer(**{**BASE, "rue_max_g_por_mj": 3.5})
