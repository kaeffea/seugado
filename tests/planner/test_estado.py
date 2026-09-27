"""Smoke checks for the planner estado helpers."""

import pytest

from seugado.core.models import CategoriaAnimal, ComposicaoLote, Confianca, OrigemPeso
from seugado.planner.estado import (
    avancar_massa_um_dia,
    confianca_estimativa,
    confianca_peso,
    consumo_lote,
    peso_por_ua_kg,
)


def test_peso_por_ua_kg_novilho() -> None:
    assert peso_por_ua_kg(CategoriaAnimal.NOVILHO) == pytest.approx(337.5)


def test_consumo_lote_worked_example() -> None:
    composicao = (ComposicaoLote(CategoriaAnimal.NOVILHO, 150, 337.5, OrigemPeso.UA_TABELA),)
    assert consumo_lote(composicao) == pytest.approx(1113.75)


def test_avancar_massa_um_dia_worked_example() -> None:
    assert avancar_massa_um_dia(2420.0, 60.0, 1113.75, 3.5, 0.72) == pytest.approx(
        2038.04, abs=0.01
    )


def test_avancar_massa_um_dia_sem_consumo() -> None:
    assert avancar_massa_um_dia(2000.0, 50.0, 0.0, 3.0, None) == pytest.approx(2050.0)


def test_avancar_massa_um_dia_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        avancar_massa_um_dia(2000.0, 50.0, 100.0, 0.0, 0.7)
    with pytest.raises(ValueError):
        avancar_massa_um_dia(2000.0, 50.0, 100.0, 3.0, None)
    with pytest.raises(ValueError):
        avancar_massa_um_dia(2000.0, 50.0, 100.0, 3.0, 0.0)


def test_confianca_peso() -> None:
    informado = (ComposicaoLote(CategoriaAnimal.ADULTO, 10, 450.0, OrigemPeso.PRODUTOR),)
    assert confianca_peso(informado) == (Confianca.ALTA, "peso médio informado por você")
    estimado = (ComposicaoLote(CategoriaAnimal.NOVILHO, 150, 337.5, OrigemPeso.UA_TABELA),)
    assert confianca_peso(estimado) == (
        Confianca.MEDIA,
        "peso médio estimado pela tabela de Unidade Animal",
    )


def test_confianca_estimativa_worked_example() -> None:
    assert confianca_estimativa(3, 40, 20, False) == (
        Confianca.MEDIA,
        "última medição de altura há 20 dias",
    )


def test_confianca_estimativa_sem_imagem() -> None:
    nivel, frase = confianca_estimativa(None, None, 5, False)
    assert nivel == Confianca.BAIXA
    assert frase == "nenhuma imagem de satélite sem nuvem nos últimos 30 dias"
