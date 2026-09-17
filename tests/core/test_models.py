import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from seugado.core.models import (
    CategoriaAnimal,
    ComposicaoLote,
    Confianca,
    Cultivar,
    Evento,
    Fazenda,
    Lote,
    Manejo,
    OrigemEvento,
    Piquete,
    QualidadeBase,
    StatusManejo,
    TipoEvento,
)

FAZENDA_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CULTIVAR_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PIQUETE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
LOTE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def test_cultivar_carries_every_parameter_explicitly():
    c = Cultivar(
        id=CULTIVAR_ID,
        slug="fixture-grass",
        nome="Fixture Grass",
        altura_entrada_cm=1.0,
        altura_saida_cm=1.0,
        densidade_kg_ha_por_cm=1.0,
        temperatura_base_c=1.0,
        rue_max_g_por_mj=1.0,
        qualidade_base=QualidadeBase.ALTA,
    )
    assert c.slug == "fixture-grass"
    assert c.qualidade_base == "alta"  # StrEnum compares equal to its value


def test_entities_are_frozen():
    p = Piquete(
        id=PIQUETE_ID,
        fazenda_id=FAZENDA_ID,
        nome="Piquete 7",
        area_ha=1.0,
        cultivar_id=CULTIVAR_ID,
    )
    with pytest.raises(FrozenInstanceError):
        p.area_ha = 2.0  # type: ignore[misc]  # intentional: verifying frozen mutation raises at runtime


def test_piquete_geometry_is_opaque_and_optional():
    p = Piquete(
        id=PIQUETE_ID,
        fazenda_id=FAZENDA_ID,
        nome="Piquete 7",
        area_ha=1.0,
        cultivar_id=CULTIVAR_ID,
        geometria_geojson={"type": "Polygon", "coordinates": []},
    )
    assert p.geometria_geojson is not None
    assert p.geometria_geojson["type"] == "Polygon"
    assert (
        Piquete(
            id=PIQUETE_ID,
            fazenda_id=FAZENDA_ID,
            nome="x",
            area_ha=1.0,
            cultivar_id=CULTIVAR_ID,
        ).geometria_geojson
        is None
    )


def test_lote_holds_composition_as_tuple():
    lote = Lote(
        id=LOTE_ID,
        fazenda_id=FAZENDA_ID,
        nome="Lote A",
        composicao=(
            ComposicaoLote(categoria=CategoriaAnimal.BEZERRO, n_animais=3, peso_medio_kg=1.0),
            ComposicaoLote(categoria=CategoriaAnimal.ADULTO, n_animais=20, peso_medio_kg=1.0),
        ),
    )
    assert isinstance(lote.composicao, tuple)
    assert len(lote.composicao) == 2
    assert lote.indissoluvel is False
    assert not hasattr(lote, "peso_vivo_total_kg")  # derived values live elsewhere


def test_manejo_allows_first_entry_and_pending_execution():
    m = Manejo(
        id=uuid.uuid4(),
        fazenda_id=FAZENDA_ID,
        lote_id=LOTE_ID,
        piquete_destino_id=PIQUETE_ID,
        data_prevista=date(2026, 3, 12),
        dias_previstos=2,
        motivo="Piquete 7 atingiu a altura de entrada.",
        confianca=Confianca.ALTA,
        status=StatusManejo.RECOMENDADO,
        origem=OrigemEvento.SISTEMA,
    )
    assert m.piquete_origem_id is None
    assert m.data_execucao is None


def test_evento_payload_is_opaque():
    e = Evento(
        id=uuid.uuid4(),
        fazenda_id=FAZENDA_ID,
        tipo=TipoEvento.LEITURA_SATELITE,
        ocorrido_em=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 3, 12, 9, 5, tzinfo=UTC),
        payload={"anything": [1, 2, 3]},
        origem=OrigemEvento.SATELITE,
    )
    assert e.payload["anything"] == [1, 2, 3]
    assert e.ocorrido_em < e.registrado_em


def test_tipo_evento_has_twelve_members():
    assert len(list(TipoEvento)) == 12


def test_fazenda_preferred_days_are_immutable():
    f = Fazenda(
        id=FAZENDA_ID,
        nome="Fazenda Fixture",
        timezone="America/Fortaleza",
        funcionarios_disponiveis=1,
        manejos_por_funcionario_dia=1,
        dias_preferenciais_manejo=(0, 2, 4),
    )
    assert isinstance(f.dias_preferenciais_manejo, tuple)
