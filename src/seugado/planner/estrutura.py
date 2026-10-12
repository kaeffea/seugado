"""Walking distance through the feeding squares and the candidate paddocks of a group.

Pure functions: no I/O, no database, no network.
"""

import math

from seugado.contratos import EstadoProjetado, LoteProjetado, PiqueteProjetado

RAIO_TERRA_M = 6_371_008.8  # IUGG mean Earth radius of GRS80 (Moritz 2000)

_LAT_MAX = 90.0
_LON_MAX = 180.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points given in degrees."""
    if abs(lat1) > _LAT_MAX or abs(lat2) > _LAT_MAX:
        raise ValueError(f"latitude out of [-90, 90]: {lat1}, {lat2}")
    if abs(lon1) > _LON_MAX or abs(lon2) > _LON_MAX:
        raise ValueError(f"longitude out of [-180, 180]: {lon1}, {lon2}")
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = phi2 - phi1
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * RAIO_TERRA_M * math.asin(math.sqrt(min(1.0, a)))


def ponto_acesso(piquete: PiqueteProjetado) -> tuple[float, float]:
    """(lat, lon) where cattle leave/enter the paddock: its feeding square, else its centroid."""
    if (piquete.praca_lat is None) != (piquete.praca_lon is None):
        raise ValueError(f"piquete {piquete.piquete_id}: praca_lat/praca_lon must come together")
    if piquete.praca_lat is not None and piquete.praca_lon is not None:
        return piquete.praca_lat, piquete.praca_lon
    return piquete.centroide_lat, piquete.centroide_lon


def distancia_manejo_m(origem: PiqueteProjetado, destino: PiqueteProjetado) -> float:
    """Walking distance in metres from origem to destino through the feeding squares."""
    if origem.piquete_id == destino.piquete_id:
        return 0.0
    acesso_origem = ponto_acesso(origem)
    acesso_destino = ponto_acesso(destino)
    return (
        haversine_m(origem.centroide_lat, origem.centroide_lon, *acesso_origem)
        + haversine_m(*acesso_origem, *acesso_destino)
        + haversine_m(*acesso_destino, destino.centroide_lat, destino.centroide_lon)
    )


def piquetes_candidatos(
    estado: EstadoProjetado, lote: LoteProjetado
) -> tuple[PiqueteProjetado, ...]:
    """Paddocks the lote may be sent to, in the order they appear in estado.piquetes."""
    if lote.modulo_id is None:
        return estado.piquetes
    return tuple(p for p in estado.piquetes if p.modulo_id == lote.modulo_id)
