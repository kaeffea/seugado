import os
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia.eventos import (
    PAYLOAD_POR_TIPO,
    PayloadAlturaMedida,
    PayloadFotoValidacao,
    PayloadLeituraSatelite,
    PayloadLoteAlterado,
    PayloadLoteCriado,
    PayloadLoteDissolvido,
    PayloadManejoConfirmado,
    PayloadManejoDivergente,
    PayloadManejoRecomendado,
    PayloadManejoRecusado,
    PayloadParametroAlterado,
    PayloadPiqueteAlterado,
    PayloadPiqueteCriado,
    registrar_evento,
)

GEOMETRIA = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
}
PIQUETE = {
    "entidade_id": uuid.uuid4(),
    "nome": "Piquete 7",
    "area_ha": 5.81,
    "cultivar_id": uuid.uuid4(),
    "metodo_pastejo": "rotacionado",
    "ativo": True,
    "geometria_geojson": GEOMETRIA,
}
LOTE = {
    "entidade_id": uuid.uuid4(),
    "nome": "Lote A",
    "composicao": [
        {
            "categoria": "adulto",
            "n_animais": 20,
            "peso_medio_kg": 450.0,
            "origem_peso": "produtor",
        }
    ],
    "indissoluvel": False,
}

CASOS = [
    (PayloadPiqueteCriado, PIQUETE, {**PIQUETE, "area_ha": 0}),
    (PayloadPiqueteAlterado, PIQUETE, {**PIQUETE, "metodo_pastejo": "diario"}),
    (
        PayloadLoteCriado,
        LOTE,
        {
            **LOTE,
            "composicao": [
                {
                    "categoria": "adulto",
                    "n_animais": 0,
                    "peso_medio_kg": 450.0,
                    "origem_peso": "produtor",
                }
            ],
        },
    ),
    (
        PayloadLoteAlterado,
        {**LOTE, "ativo": True},
        {
            **LOTE,
            "ativo": True,
            "composicao": [
                {
                    "categoria": "adulto",
                    "n_animais": 20,
                    "peso_medio_kg": -1.0,
                    "origem_peso": "produtor",
                }
            ],
        },
    ),
    (PayloadLoteDissolvido, {"entidade_id": uuid.uuid4()}, {}),
    (
        PayloadManejoRecomendado,
        {
            "entidade_id": uuid.uuid4(),
            "lote_id": uuid.uuid4(),
            "piquete_origem_id": None,
            "piquete_destino_id": uuid.uuid4(),
            "data_prevista": "2026-09-10",
            "dias_previstos": 2,
            "motivo": "entry height reached",
            "confianca": "alta",
            "motivo_confianca": "clear sky",
        },
        {
            "entidade_id": uuid.uuid4(),
            "lote_id": uuid.uuid4(),
            "piquete_origem_id": None,
            "piquete_destino_id": uuid.uuid4(),
            "data_prevista": "2026-09-10",
            "dias_previstos": 2,
            "motivo": "entry height reached",
            "confianca": "total",
            "motivo_confianca": "clear sky",
        },
    ),
    (
        PayloadManejoConfirmado,
        {
            "entidade_id": uuid.uuid4(),
            "lote_id": uuid.uuid4(),
            "piquete_destino_id": uuid.uuid4(),
            "data_execucao": "2026-09-10",
        },
        {
            "entidade_id": uuid.uuid4(),
            "lote_id": uuid.uuid4(),
            "piquete_destino_id": uuid.uuid4(),
            "data_execucao": "10/09/2026",
        },
    ),
    (
        PayloadManejoRecusado,
        {"entidade_id": uuid.uuid4(), "motivo": None},
        {"entidade_id": uuid.uuid4()},
    ),
    (
        PayloadManejoDivergente,
        {
            "entidade_id": uuid.uuid4(),
            "lote_id": uuid.uuid4(),
            "piquete_real_id": uuid.uuid4(),
            "data_execucao": "2026-09-10",
            "observacao": None,
        },
        {
            "entidade_id": uuid.uuid4(),
            "lote_id": uuid.uuid4(),
            "piquete_real_id": uuid.uuid4(),
            "data_execucao": "2026-09-10",
        },
    ),
    (
        PayloadLeituraSatelite,
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": uuid.uuid4(),
            "data": "2026-09-10",
            "ndvi": 0.62,
            "refletancia_red": 0.08,
            "refletancia_nir": 0.35,
            "origem_ndvi": "optico",
            "pct_nuvem": 5.0,
            "pixels_validos": 340,
        },
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": uuid.uuid4(),
            "data": "2026-09-10",
            "ndvi": 0.62,
            "refletancia_red": 0.08,
            "refletancia_nir": 0.35,
            "origem_ndvi": "optico",
            "pct_nuvem": 5.0,
            "pixels_validos": 0,
        },
    ),
    (
        PayloadAlturaMedida,
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": uuid.uuid4(),
            "data": "2026-09-10",
            "altura_cm": 28.0,
            "meio": "bot",
        },
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": uuid.uuid4(),
            "data": "2026-09-10",
            "altura_cm": 0.0,
            "meio": "bot",
        },
    ),
    (
        PayloadFotoValidacao,
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": uuid.uuid4(),
            "url_foto": "https://example.com/foto.jpg",
            "altura_informada_cm": None,
            "data": "2026-09-10",
        },
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": uuid.uuid4(),
            "url_foto": "https://example.com/foto.jpg",
            "altura_informada_cm": "alta",
            "data": "2026-09-10",
        },
    ),
    (
        PayloadParametroAlterado,
        {
            "entidade_id": uuid.uuid4(),
            "cultivar_id": uuid.uuid4(),
            "metodo_pastejo": "continuo",
            "campo": "altura_maxima_cm",
            "valor": 75.0,
            "origem": "produtor",
            "confianca": "media",
        },
        {
            "entidade_id": uuid.uuid4(),
            "cultivar_id": uuid.uuid4(),
            "metodo_pastejo": "continuo",
            "campo": "altura_maxima_cm",
            "valor": 75.0,
            "origem": "sistema",
            "confianca": "media",
        },
    ),
]


@pytest.mark.parametrize(
    ("modelo", "valido", "invalido"),
    CASOS,
    ids=[c[0].__name__ for c in CASOS],
)
def test_modelo_aceita_valido_rejeita_invalido(modelo, valido, invalido):
    modelo.model_validate(valido)
    with pytest.raises(ValidationError):
        modelo.model_validate(invalido)


def test_payload_por_tipo_has_thirteen_entries():
    assert len(PAYLOAD_POR_TIPO) == 13
    assert PAYLOAD_POR_TIPO[TipoEvento.ALTURA_MEDIDA] is PayloadAlturaMedida


def test_leitura_has_exactly_nine_fields():
    assert set(PayloadLeituraSatelite.model_fields) == {
        "entidade_id",
        "piquete_id",
        "data",
        "ndvi",
        "refletancia_red",
        "refletancia_nir",
        "origem_ndvi",
        "pct_nuvem",
        "pixels_validos",
    }


def test_geometria_rejects_non_polygon_and_short_ring():
    bad_type = {**PIQUETE, "geometria_geojson": {"type": "Point", "coordinates": [0, 0]}}
    with pytest.raises(ValidationError):
        PayloadPiqueteCriado.model_validate(bad_type)
    short_ring = {
        **PIQUETE,
        "geometria_geojson": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1]]]},
    }
    with pytest.raises(ValidationError):
        PayloadPiqueteCriado.model_validate(short_ring)
    with pytest.raises(ValidationError):
        PayloadPiqueteAlterado.model_validate(short_ring)


def test_leitura_rejects_non_positive_ndvi():
    base = {
        "entidade_id": uuid.uuid4(),
        "piquete_id": uuid.uuid4(),
        "data": "2026-09-10",
        "ndvi": 0.0,
        "refletancia_red": 0.08,
        "refletancia_nir": 0.35,
        "origem_ndvi": "optico",
        "pct_nuvem": 5.0,
        "pixels_validos": 10,
    }
    with pytest.raises(ValidationError):
        PayloadLeituraSatelite.model_validate(base)


@pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"),
    reason="needs SEUGADO_TEST_DATABASE_URL",
)
def test_registrar_evento_idempotente_sem_commit():
    import psycopg

    url = os.environ["SEUGADO_TEST_DATABASE_URL"]
    conn = psycopg.connect(url)
    try:
        fazenda_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO fazenda (id) VALUES (%s)", (fazenda_id,))
        chave = f"smoke-{uuid.uuid4()}"
        primeiro = registrar_evento(
            conn,
            fazenda_id,
            TipoEvento.PIQUETE_CRIADO,
            OrigemEvento.SISTEMA,
            datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            dict(PIQUETE),
            chave_idempotencia=chave,
        )
        segundo = registrar_evento(
            conn,
            fazenda_id,
            TipoEvento.PIQUETE_CRIADO,
            OrigemEvento.SISTEMA,
            datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            dict(PIQUETE),
            chave_idempotencia=chave,
        )
        assert primeiro == segundo
        probe = psycopg.connect(url)
        try:
            with probe.cursor() as cur:
                cur.execute("SELECT count(*) FROM evento WHERE id = %s", (primeiro,))
                row = cur.fetchone()
                assert row is not None and row[0] == 0  # uncommitted: invisible
        finally:
            probe.close()
    finally:
        conn.rollback()
        conn.close()
