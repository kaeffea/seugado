import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest

from seugado.core.models import Evento, OrigemEvento, TipoEvento
from seugado.core.projecao import SituacaoPiquete, projetar

FAZENDA = uuid.UUID("11111111-1111-1111-1111-111111111111")
P1 = uuid.UUID("33333333-3333-3333-3333-333333333333")
L1 = uuid.UUID("44444444-4444-4444-4444-444444444444")
C1 = uuid.UUID("22222222-2222-2222-2222-222222222222")
M1 = uuid.UUID("55555555-5555-5555-5555-555555555555")
E1 = uuid.UUID("66666666-0000-0000-0000-000000000001")
E2 = uuid.UUID("66666666-0000-0000-0000-000000000002")
E3 = uuid.UUID("66666666-0000-0000-0000-000000000003")


def _evento(
    id: uuid.UUID,
    tipo: TipoEvento,
    dia: int,
    sequencia: int,
    payload: dict[str, Any],
    corrige_evento_id: uuid.UUID | None = None,
) -> Evento:
    return Evento(
        id=id,
        fazenda_id=FAZENDA,
        tipo=tipo,
        ocorrido_em=datetime(2026, 9, dia, 9, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 9, dia, 9, 5, tzinfo=UTC),
        payload=payload,
        origem=OrigemEvento.SISTEMA,
        sequencia=sequencia,
        corrige_evento_id=corrige_evento_id,
    )


def _piquete_criado() -> Evento:
    return _evento(
        E1,
        TipoEvento.PIQUETE_CRIADO,
        1,
        1,
        {
            "entidade_id": P1,
            "nome": "Piquete 7",
            "area_ha": 5.81,
            "cultivar_id": C1,
            "metodo_pastejo": "rotacionado",
            "ativo": True,
        },
    )


def _lote_criado() -> Evento:
    return _evento(
        E2,
        TipoEvento.LOTE_CRIADO,
        5,
        2,
        {
            "entidade_id": L1,
            "nome": "Lote A",
            "composicao": [{"categoria": "adulto", "n_animais": 20, "peso_medio_kg": 450}],
            "indissoluvel": False,
        },
    )


def _manejo_confirmado() -> Evento:
    return _evento(
        E3,
        TipoEvento.MANEJO_CONFIRMADO,
        10,
        3,
        {
            "entidade_id": M1,
            "lote_id": L1,
            "piquete_destino_id": P1,
            "data_execucao": "2026-09-10",
        },
    )


def test_canonical_fold_occupies_piquete():
    estado = projetar([_piquete_criado(), _lote_criado(), _manejo_confirmado()])
    assert estado.piquetes[P1].situacao == SituacaoPiquete.OCUPADO
    assert estado.piquetes[P1].lote_atual_id == L1
    assert estado.piquetes[P1].desde == date(2026, 9, 10)
    assert estado.piquetes[P1].dias_descanso == 0
    assert estado.lotes[L1].piquete_atual_id == P1
    assert estado.lotes[L1].peso_vivo_total_kg == 9000.0


def test_correction_applies_at_original_position():
    corretivo = _evento(
        uuid.uuid4(),
        TipoEvento.PIQUETE_ALTERADO,
        15,
        4,
        {
            "entidade_id": P1,
            "nome": "Piquete 7",
            "area_ha": 6.02,
            "cultivar_id": C1,
            "metodo_pastejo": "rotacionado",
            "ativo": True,
        },
        corrige_evento_id=E1,
    )
    estado = projetar([_piquete_criado(), _lote_criado(), _manejo_confirmado(), corretivo])
    assert estado.piquetes[P1].area_ha == 6.02
    assert estado.piquetes[P1].situacao == SituacaoPiquete.OCUPADO


def test_dissolution_frees_piquete_with_rest_days():
    dissolver = _evento(uuid.uuid4(), TipoEvento.LOTE_DISSOLVIDO, 12, 4, {"entidade_id": L1})
    estado = projetar([_piquete_criado(), _lote_criado(), _manejo_confirmado(), dissolver])
    assert L1 not in estado.lotes
    assert estado.piquetes[P1].situacao == SituacaoPiquete.DESCANSANDO
    assert estado.piquetes[P1].lote_atual_id is None
    assert estado.piquetes[P1].desde == date(2026, 9, 12)
    assert estado.piquetes[P1].dias_descanso == 0


def test_latest_reading_wins_and_no_effect_events_are_skipped():
    leitura_antiga = _evento(
        uuid.uuid4(),
        TipoEvento.LEITURA_SATELITE,
        5,
        4,
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": P1,
            "data": "2026-09-05",
            "ndvi": 0.5,
            "origem_ndvi": "sentinel",
            "pct_nuvem": 10.0,
            "pixels_validos": 100,
            "massa_kg_ms_ha": 3000.0,
            "taxa_acumulo_kg_ms_ha_dia": 20.0,
            "confianca": "media",
        },
    )
    leitura_nova = _evento(
        uuid.uuid4(),
        TipoEvento.LEITURA_SATELITE,
        10,
        5,
        {
            "entidade_id": uuid.uuid4(),
            "piquete_id": P1,
            "data": "2026-09-10",
            "ndvi": 0.6,
            "origem_ndvi": "sentinel",
            "pct_nuvem": 5.0,
            "pixels_validos": 120,
            "massa_kg_ms_ha": 4000.0,
            "taxa_acumulo_kg_ms_ha_dia": 25.0,
            "confianca": "alta",
        },
    )
    foto = _evento(uuid.uuid4(), TipoEvento.FOTO_VALIDACAO, 10, 6, {})
    estado = projetar([_piquete_criado(), leitura_antiga, leitura_nova, foto])
    assert estado.leituras[P1].massa_kg_ms_ha == 4000.0
    assert estado.leituras[P1].data == date(2026, 9, 10)


def test_validation_errors():
    with pytest.raises(ValueError):
        projetar([])
    outra_fazenda = Evento(
        id=uuid.uuid4(),
        fazenda_id=uuid.uuid4(),
        tipo=TipoEvento.PIQUETE_CRIADO,
        ocorrido_em=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        registrado_em=datetime(2026, 9, 1, 9, 5, tzinfo=UTC),
        payload={},
        origem=OrigemEvento.SISTEMA,
        sequencia=1,
    )
    with pytest.raises(ValueError):
        projetar([_piquete_criado(), outra_fazenda])
    pendente = _evento(
        uuid.uuid4(), TipoEvento.PIQUETE_ALTERADO, 15, 4, {}, corrige_evento_id=uuid.uuid4()
    )
    with pytest.raises(ValueError):
        projetar([_piquete_criado(), pendente])
    duplo_a = _evento(
        uuid.uuid4(),
        TipoEvento.PIQUETE_ALTERADO,
        15,
        4,
        {},
        corrige_evento_id=E1,
    )
    duplo_b = _evento(
        uuid.uuid4(),
        TipoEvento.PIQUETE_ALTERADO,
        16,
        5,
        {},
        corrige_evento_id=E1,
    )
    with pytest.raises(ValueError):
        projetar([_piquete_criado(), duplo_a, duplo_b])
    with pytest.raises(ValueError):
        projetar([_lote_criado(), _manejo_confirmado()])
