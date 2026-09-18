import pytest

from seugado.core.forragem import (
    altura_para_massa,
    consumo_individual_kg_ms_dia,
    consumo_lote_kg_ms_dia,
    consumo_pct_pv,
    dias_ocupacao,
    massa_para_altura,
    taxa_utilizacao,
)


def test_mass_height_are_exact_inverses():
    assert altura_para_massa(40.0, 100.0) == 4000.0
    assert massa_para_altura(4000.0, 100.0) == 40.0


def test_consumo_lote_literature_example():
    assert consumo_lote_kg_ms_dia([(1, 300.0, 0.022)]) == pytest.approx(6.6)


def test_consumo_lote_empty_returns_zero():
    assert consumo_lote_kg_ms_dia([]) == 0.0


def test_canonical_case_reproduces_expected_values():
    assert taxa_utilizacao(4000.0, 2240.0) == pytest.approx(0.44, abs=0.01)
    consumo_ind = consumo_individual_kg_ms_dia(1760.0, 5.81, 4.0, 220)
    assert consumo_ind == pytest.approx(11.62, abs=0.05)
    assert consumo_pct_pv(11.62, 479.0) == pytest.approx(2.42, abs=0.02)
    assert dias_ocupacao(4000.0, 2240.0, 0.0, 5.81, 1.0, 2556.4) == pytest.approx(4.0, abs=0.05)


def test_dias_ocupacao_returns_inf_when_growth_covers_intake():
    assert dias_ocupacao(4000.0, 2240.0, 1000.0, 5.81, 1.0, 10.0) == float("inf")


def test_dias_ocupacao_returns_zero_at_or_below_residue():
    assert dias_ocupacao(2240.0, 2240.0, 0.0, 5.81, 1.0, 2556.4) == 0.0
    assert dias_ocupacao(2000.0, 2240.0, 0.0, 5.81, 1.0, 2556.4) == 0.0


def test_validation_errors():
    with pytest.raises(ValueError):
        massa_para_altura(-1.0, 100.0)
    with pytest.raises(ValueError):
        massa_para_altura(4000.0, 0.0)
    with pytest.raises(ValueError):
        altura_para_massa(-1.0, 100.0)
    with pytest.raises(ValueError):
        altura_para_massa(40.0, 0.0)
    with pytest.raises(ValueError):
        consumo_lote_kg_ms_dia([(-1, 300.0, 0.022)])
    with pytest.raises(ValueError):
        consumo_lote_kg_ms_dia([(1, 0.0, 0.022)])
    with pytest.raises(ValueError):
        consumo_lote_kg_ms_dia([(1, 300.0, 0.0)])
    with pytest.raises(ValueError):
        dias_ocupacao(4000.0, 2240.0, 0.0, 5.81, 1.5, 2556.4)
    with pytest.raises(ValueError):
        dias_ocupacao(4000.0, 2240.0, 0.0, 0.0, 1.0, 2556.4)
    with pytest.raises(ValueError):
        dias_ocupacao(4000.0, 2240.0, 0.0, 5.81, 1.0, 0.0)
    with pytest.raises(ValueError):
        taxa_utilizacao(0.0, 2240.0)
    with pytest.raises(ValueError):
        taxa_utilizacao(4000.0, 5000.0)
    with pytest.raises(ValueError):
        consumo_individual_kg_ms_dia(1760.0, 5.81, 4.0, 0)
    with pytest.raises(ValueError):
        consumo_pct_pv(11.62, 0.0)
