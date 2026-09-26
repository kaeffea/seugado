"""Rebuild one farm's derived tables from its event log."""

import json
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Json

from seugado.core.models import Evento, OrigemEvento, TipoEvento
from seugado.core.projecao import EstadoFazenda, projetar

_SELECT_EVENTOS = (
    "SELECT id, fazenda_id, tipo, ocorrido_em, registrado_em, payload, origem,"
    " sequencia, corrige_evento_id"
    " FROM evento WHERE fazenda_id = %s ORDER BY ocorrido_em, sequencia"
)

_LOCK_FAZENDA = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 0))"

_DELETE_PIQUETE = "DELETE FROM estado_piquete WHERE fazenda_id = %s"
_DELETE_LOTE = "DELETE FROM estado_lote WHERE fazenda_id = %s"
_DELETE_LEITURA = "DELETE FROM leitura WHERE fazenda_id = %s"
_DELETE_ALTURA = "DELETE FROM altura_atual WHERE fazenda_id = %s"

_INSERT_PIQUETE = (
    "INSERT INTO estado_piquete (fazenda_id, piquete_id, nome, area_ha, cultivar_id,"
    " metodo_pastejo, ativo, geometria, situacao, lote_atual_id, desde, dias_descanso,"
    " derivado_ate_sequencia)"
    " VALUES (%s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),"
    " %s, %s, %s, %s, %s)"
)

_INSERT_LOTE = (
    "INSERT INTO estado_lote (fazenda_id, lote_id, nome, indissoluvel, composicao,"
    " piquete_atual_id, desde, peso_vivo_total_kg, derivado_ate_sequencia)"
    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_LEITURA = (
    "INSERT INTO leitura (id, fazenda_id, piquete_id, data, ndvi, refletancia_red,"
    " refletancia_nir, origem, pct_nuvem, pixels_validos, derivado_ate_sequencia)"
    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_ALTURA = (
    "INSERT INTO altura_atual (fazenda_id, piquete_id, data, altura_cm, meio,"
    " derivado_ate_sequencia)"
    " VALUES (%s, %s, %s, %s, %s, %s)"
)


def carregar_eventos(conn: psycopg.Connection[Any], fazenda_id: UUID) -> list[Evento]:
    """Load every event of one farm ordered by (ocorrido_em, sequencia)."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_EVENTOS, (fazenda_id,))
        linhas = cur.fetchall()
    return [
        Evento(
            id=row[0],
            fazenda_id=row[1],
            tipo=TipoEvento(row[2]),
            ocorrido_em=row[3],
            registrado_em=row[4],
            payload=dict(row[5]),
            origem=OrigemEvento(row[6]),
            sequencia=row[7],
            corrige_evento_id=row[8],
        )
        for row in linhas
    ]


def _limpar(conn: psycopg.Connection[Any], fazenda_id: UUID) -> None:
    """Delete one farm's rows from the four derived tables."""
    with conn.cursor() as cur:
        cur.execute(_DELETE_PIQUETE, (fazenda_id,))
        cur.execute(_DELETE_LOTE, (fazenda_id,))
        cur.execute(_DELETE_LEITURA, (fazenda_id,))
        cur.execute(_DELETE_ALTURA, (fazenda_id,))


def reconstruir_projecao(conn: psycopg.Connection[Any], fazenda_id: UUID) -> EstadoFazenda:
    """Rebuild all derived tables of one farm from its events, inside the caller's transaction."""
    with conn.cursor() as cur:
        cur.execute(_LOCK_FAZENDA, (str(fazenda_id),))
    eventos = carregar_eventos(conn, fazenda_id)
    if len(eventos) == 0:
        _limpar(conn, fazenda_id)
        return EstadoFazenda(fazenda_id=fazenda_id, piquetes={}, lotes={}, leituras={}, alturas={})
    estado = projetar(eventos)
    seq = max(e.sequencia for e in eventos)
    _limpar(conn, fazenda_id)
    with conn.cursor() as cur:
        for p in estado.piquetes.values():
            cur.execute(
                _INSERT_PIQUETE,
                (
                    fazenda_id,
                    p.piquete_id,
                    p.nome,
                    p.area_ha,
                    p.cultivar_id,
                    p.metodo_pastejo.value,
                    p.ativo,
                    json.dumps(p.geometria_geojson),
                    p.situacao.value,
                    p.lote_atual_id,
                    p.desde,
                    p.dias_descanso,
                    seq,
                ),
            )
        for lote in estado.lotes.values():
            composicao = Json(
                [
                    {
                        "categoria": item.categoria.value,
                        "n_animais": item.n_animais,
                        "peso_medio_kg": item.peso_medio_kg,
                        "origem_peso": item.origem_peso.value,
                    }
                    for item in lote.composicao
                ]
            )
            cur.execute(
                _INSERT_LOTE,
                (
                    fazenda_id,
                    lote.lote_id,
                    lote.nome,
                    lote.indissoluvel,
                    composicao,
                    lote.piquete_atual_id,
                    lote.desde,
                    lote.peso_vivo_total_kg,
                    seq,
                ),
            )
        for leitura in estado.leituras.values():
            cur.execute(
                _INSERT_LEITURA,
                (
                    leitura.id,
                    fazenda_id,
                    leitura.piquete_id,
                    leitura.data,
                    leitura.ndvi,
                    leitura.refletancia_red,
                    leitura.refletancia_nir,
                    leitura.origem_ndvi,
                    leitura.pct_nuvem,
                    leitura.pixels_validos,
                    seq,
                ),
            )
        for altura in estado.alturas.values():
            cur.execute(
                _INSERT_ALTURA,
                (fazenda_id, altura.piquete_id, altura.data, altura.altura_cm, altura.meio, seq),
            )
    return estado
