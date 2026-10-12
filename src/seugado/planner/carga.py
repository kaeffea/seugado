"""Load everything projetar_estado needs from the database and the weather API (read only)."""

from dataclasses import replace
from datetime import date, timedelta
from typing import Any
from uuid import UUID

import psycopg

from seugado.contratos import EstadoProjetado
from seugado.core.projecao import projetar
from seugado.persistencia.catalogo import carregar_catalogo
from seugado.persistencia.projecao_db import carregar_eventos
from seugado.planner.estado import projetar_estado
from seugado.planner.estado_util import ancora_altura
from seugado.sensing.clima import buscar_clima, et0_media_anual_mm_dia

_HORIZONTE_PREVISAO_DIAS = 14

_SELECT_CENTROIDES = (
    "SELECT piquete_id, ST_Y(ST_Centroid(geometria)), ST_X(ST_Centroid(geometria))"
    " FROM estado_piquete WHERE fazenda_id = %s AND ativo"
)
_SELECT_TIMEZONE = "SELECT timezone FROM fazenda WHERE id = %s"
_SELECT_ESTRUTURA_PIQUETES = (
    "SELECT pe.piquete_id, pe.modulo_id, pe.praca_id, ST_Y(pr.ponto), ST_X(pr.ponto)"
    " FROM piquete_estrutura pe LEFT JOIN praca pr ON pr.id = pe.praca_id"
    " WHERE pe.fazenda_id = %s"
)
_SELECT_MODULO_LOTES = "SELECT lote_id, modulo_id FROM lote_modulo WHERE fazenda_id = %s"


def _vazio(fazenda_id: UUID, data_base: date) -> EstadoProjetado:
    """Projected state of a farm with nothing to project."""
    return EstadoProjetado(
        fazenda_id=fazenda_id,
        data_base=data_base,
        horizonte_previsao_dias=_HORIZONTE_PREVISAO_DIAS,
        piquetes=(),
        lotes=(),
    )


def _com_estrutura(
    conn: psycopg.Connection[Any], fazenda_id: UUID, estado: EstadoProjetado
) -> EstadoProjetado:
    """Copy of `estado` with each paddock's module/square and each group's module filled in."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_ESTRUTURA_PIQUETES, (fazenda_id,))
        linhas_piquetes = cur.fetchall()
        cur.execute(_SELECT_MODULO_LOTES, (fazenda_id,))
        linhas_lotes = cur.fetchall()
    estrutura = {row[0]: row[1:] for row in linhas_piquetes}
    modulo_do_lote = {row[0]: row[1] for row in linhas_lotes}
    piquetes = []
    for p in estado.piquetes:
        if p.piquete_id not in estrutura:
            piquetes.append(p)
            continue
        modulo_id, praca_id, lat, lon = estrutura[p.piquete_id]
        piquetes.append(
            replace(
                p,
                modulo_id=modulo_id,
                praca_id=praca_id,
                praca_lat=None if lat is None else float(lat),
                praca_lon=None if lon is None else float(lon),
            )
        )
    lotes = tuple(
        replace(lote, modulo_id=modulo_do_lote[lote.lote_id])
        if lote.lote_id in modulo_do_lote
        else lote
        for lote in estado.lotes
    )
    return replace(estado, piquetes=tuple(piquetes), lotes=lotes)


def montar_estado_projetado(
    conn: psycopg.Connection[Any], fazenda_id: UUID, data_base: date
) -> EstadoProjetado:
    """Build the farm's projected state for data_base; never commits."""
    eventos = carregar_eventos(conn, fazenda_id)
    if len(eventos) == 0:
        return _vazio(fazenda_id, data_base)
    estado = projetar(eventos)
    catalogo = carregar_catalogo(conn, fazenda_id)
    with conn.cursor() as cur:
        cur.execute(_SELECT_CENTROIDES, (fazenda_id,))
        linhas = cur.fetchall()
        cur.execute(_SELECT_TIMEZONE, (fazenda_id,))
        linha_fazenda = cur.fetchone()
    if len(linhas) == 0:
        return _vazio(fazenda_id, data_base)
    if linha_fazenda is None:
        raise ValueError(f"fazenda {fazenda_id} not found")
    timezone = str(linha_fazenda[0])
    centroides = {row[0]: (float(row[1]), float(row[2])) for row in linhas}
    lat_fazenda = sum(lat for lat, _ in centroides.values()) / len(centroides)
    lon_fazenda = sum(lon for _, lon in centroides.values()) / len(centroides)

    ancoras = [
        ancora_altura(eventos, p.piquete_id, data_base) for p in estado.piquetes.values() if p.ativo
    ]
    inicio = min((a.data for a in ancoras if a is not None), default=data_base)
    clima = buscar_clima(
        lat_fazenda,
        lon_fazenda,
        inicio,
        data_base + timedelta(days=_HORIZONTE_PREVISAO_DIAS - 1),
        hoje=data_base,
        timezone=timezone,
    )
    et0 = et0_media_anual_mm_dia(lat_fazenda, lon_fazenda, data_base, timezone)
    projetado = projetar_estado(
        estado,
        eventos,
        catalogo,
        centroides,
        clima,
        et0,
        lat_fazenda,
        data_base,
        _HORIZONTE_PREVISAO_DIAS,
    )
    return _com_estrutura(conn, fazenda_id, projetado)
