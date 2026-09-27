"""Ingest Sentinel-2 readings as idempotent satellite events."""

import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg

from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia.eventos import registrar_evento
from seugado.sensing.earth_engine import amostrar_sentinel2, inicializar_earth_engine

_SELECT_PIQUETES_ATIVOS = (
    "SELECT piquete_id, ST_AsGeoJSON(geometria) FROM estado_piquete"
    " WHERE fazenda_id = %s AND ativo"
)
_SELECT_POR_CHAVE = "SELECT 1 FROM evento WHERE fazenda_id = %s AND chave_idempotencia = %s"


def ingerir_leituras(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    data_inicio: date,
    data_fim: date,
) -> int:
    """Sample Sentinel-2 for the farm's active piquetes; record one event per new reading.

    Returns how many readings were NEW (not already stored).
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_PIQUETES_ATIVOS, (fazenda_id,))
        linhas = cur.fetchall()
    piquetes = [
        (linha[0] if isinstance(linha[0], UUID) else UUID(str(linha[0])), json.loads(linha[1]))
        for linha in linhas
        if linha[1] is not None
    ]
    if not piquetes:
        return 0
    inicializar_earth_engine()
    observacoes = amostrar_sentinel2(piquetes, data_inicio, data_fim)
    novas = 0
    agora = datetime.now(UTC)
    with conn.cursor() as cur:
        for obs in observacoes:
            chave = f"leitura:{obs.piquete_id}:{obs.data.isoformat()}"
            cur.execute(_SELECT_POR_CHAVE, (fazenda_id, chave))
            if cur.fetchone() is not None:
                continue
            registrar_evento(
                conn,
                fazenda_id,
                TipoEvento.LEITURA_SATELITE,
                OrigemEvento.SATELITE,
                ocorrido_em=agora,
                payload={
                    "entidade_id": uuid5(NAMESPACE_URL, chave),
                    "piquete_id": obs.piquete_id,
                    "data": obs.data,
                    "ndvi": obs.ndvi,
                    "refletancia_red": obs.refletancia_red,
                    "refletancia_nir": obs.refletancia_nir,
                    "origem_ndvi": "optico",
                    "pct_nuvem": obs.pct_nuvem,
                    "pixels_validos": obs.pixels_validos,
                },
                ator="ingestao_sentinel2",
                chave_idempotencia=chave,
            )
            novas += 1
    return novas
