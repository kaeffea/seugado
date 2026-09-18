import uuid

import pytest

from seugado.core.models import (
    Confianca,
    Cultivar,
    MetodoPastejo,
    ParametrosRegime,
    QualidadeBase,
)
from seugado.core.regras import (
    apto_para_entrada,
    descanso_cumprido,
    precisa_sair,
    resolver_parametros,
    urgencia,
)

CULTIVAR_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

ROTACIONADO = ParametrosRegime(
    metodo=MetodoPastejo.ROTACIONADO,
    altura_entrada_cm=90.0,
    altura_saida_cm=40.0,
    altura_maxima_cm=None,
    altura_minima_cm=None,
    confianca=Confianca.ALTA,
    fonte="worked example",
)


def _cultivar(*blocos: ParametrosRegime) -> Cultivar:
    return Cultivar(
        id=CULTIVAR_ID,
        slug="fixture-grass",
        nome="Fixture Grass",
        parametros_por_regime=tuple(blocos),
        densidade_kg_ha_por_cm=1.0,
        temperatura_base_c=1.0,
        rue_max_g_por_mj=1.0,
        qualidade_base=QualidadeBase.ALTA,
    )


def test_resolver_returns_block_when_complete():
    r = resolver_parametros(_cultivar(ROTACIONADO), MetodoPastejo.ROTACIONADO)
    assert r.parametros == ROTACIONADO
    assert r.faltantes == ()


def test_resolver_names_all_fields_when_entry_absent():
    r = resolver_parametros(_cultivar(ROTACIONADO), MetodoPastejo.CONTINUO)
    assert r.parametros is None
    assert r.faltantes == ("altura_maxima_cm", "altura_minima_cm")


def test_resolver_rejects_partial_block():
    parcial = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=90.0,
        altura_saida_cm=None,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="partial",
    )
    r = resolver_parametros(_cultivar(parcial), MetodoPastejo.ROTACIONADO)
    assert r.parametros is None
    assert r.faltantes == ("altura_saida_cm",)


def test_entry_exit_urgency_at_two_heights():
    assert apto_para_entrada(88.0, ROTACIONADO, True) is False
    assert precisa_sair(88.0, ROTACIONADO) is False
    assert urgencia(88.0, ROTACIONADO) == pytest.approx(-48.0)
    assert precisa_sair(38.0, ROTACIONADO) is True
    assert urgencia(38.0, ROTACIONADO) == pytest.approx(2.0)
    assert apto_para_entrada(90.0, ROTACIONADO, True) is True
    assert apto_para_entrada(90.0, ROTACIONADO, False) is False


def test_descanso_uses_threshold():
    assert descanso_cumprido(21, 21) is True
    assert descanso_cumprido(20, 21) is False


def test_continuo_block_rejected_by_rotational_rules():
    continuo = ParametrosRegime(
        metodo=MetodoPastejo.CONTINUO,
        altura_entrada_cm=None,
        altura_saida_cm=None,
        altura_maxima_cm=75.0,
        altura_minima_cm=50.0,
        confianca=Confianca.MEDIA,
        fonte="fixture",
    )
    with pytest.raises(ValueError):
        apto_para_entrada(80.0, continuo, True)
    with pytest.raises(ValueError):
        precisa_sair(40.0, continuo)
    with pytest.raises(ValueError):
        urgencia(40.0, continuo)


def test_validation_errors():
    sem_entrada = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=None,
        altura_saida_cm=40.0,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="partial",
    )
    with pytest.raises(ValueError):
        apto_para_entrada(95.0, sem_entrada, True)
    sem_saida = ParametrosRegime(
        metodo=MetodoPastejo.ROTACIONADO,
        altura_entrada_cm=90.0,
        altura_saida_cm=None,
        altura_maxima_cm=None,
        altura_minima_cm=None,
        confianca=Confianca.ALTA,
        fonte="partial",
    )
    with pytest.raises(ValueError):
        precisa_sair(30.0, sem_saida)
    with pytest.raises(ValueError):
        urgencia(30.0, sem_saida)
    with pytest.raises(ValueError):
        descanso_cumprido(-1, 21)
    with pytest.raises(ValueError):
        descanso_cumprido(21, 0)
