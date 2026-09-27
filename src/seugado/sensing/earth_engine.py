"""Sentinel-2 sampling on Google Earth Engine (plus pure row extraction)."""

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, cast
from uuid import UUID

import ee

_COLECAO_S2 = "COPERNICUS/S2_SR_HARMONIZED"
_COLECAO_NUVEM = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
_LIMIAR_CS_CDF = 0.60
_BANDA_RED = "B4"
_BANDA_NIR = "B8"
_ESCALA_M = 10
_BUFFER_M = -5
_MINIMOS_PIXELS_VALIDOS = 3
_FATOR_ESCALA_REFLETANCIA = 0.0001


@dataclass(frozen=True, slots=True)
class ObservacaoSatelite:
    """Mean clear-pixel reflectance of one piquete on one date."""

    piquete_id: UUID
    data: date
    ndvi: float
    refletancia_red: float
    refletancia_nir: float
    pixels_validos: int
    pixels_totais: int
    pct_nuvem: float


def inicializar_earth_engine() -> None:
    """Authenticate with a service account taken from the environment."""
    conteudo_json = os.environ.get("SEUGADO_GEE_SERVICE_ACCOUNT_JSON")
    if conteudo_json is None:
        raise RuntimeError("missing environment variable SEUGADO_GEE_SERVICE_ACCOUNT_JSON")
    projeto = os.environ.get("SEUGADO_GEE_PROJECT")
    if projeto is None:
        raise RuntimeError("missing environment variable SEUGADO_GEE_PROJECT")
    info = json.loads(conteudo_json)
    credenciais = ee.ServiceAccountCredentials(
        email=info["client_email"], key_data=conteudo_json
    )
    ee.Initialize(credenciais, project=projeto)


def amostrar_sentinel2(
    piquetes: Sequence[tuple[UUID, dict[str, Any]]],
    data_inicio: date,
    data_fim: date,
) -> list[ObservacaoSatelite]:
    """Sample mean red/NIR reflectance per piquete per date on Earth Engine."""
    if data_inicio > data_fim:
        raise ValueError(f"data_inicio {data_inicio} after data_fim {data_fim}")
    for piquete_id, geometria in piquetes:
        coordenadas = geometria.get("coordinates")
        if (
            geometria.get("type") != "Polygon"
            or not isinstance(coordenadas, list)
            or not coordenadas
        ):
            raise ValueError(f"piquete {piquete_id} geometry is not a GeoJSON Polygon")
    if not piquetes:
        return []

    colecao_piquetes = ee.FeatureCollection(
        [
            ee.Feature(
                ee.Geometry(poligono).buffer(_BUFFER_M),
                {"piquete_id": str(piquete_id)},
            )
            for piquete_id, poligono in piquetes
        ]
    )
    s2 = (
        ee.ImageCollection(_COLECAO_S2)
        .filterBounds(colecao_piquetes)
        .filterDate(data_inicio.isoformat(), (data_fim + timedelta(days=1)).isoformat())
        .map(lambda img: img.set("geo_area", img.geometry().area(1000)))
        .filter(ee.Filter.lt("geo_area", 1e12))
    )
    cs_mais = ee.ImageCollection(_COLECAO_NUVEM).select("cs_cdf")
    ligadas = s2.linkCollection(cs_mais, ["cs_cdf"])

    def _amostrar_imagem(imagem: ee.Image) -> ee.FeatureCollection:
        mascara = imagem.select("cs_cdf").gte(_LIMIAR_CS_CDF)
        bandas = (
            imagem.select(_BANDA_RED)
            .updateMask(mascara)
            .rename("red")
            .addBands(imagem.select(_BANDA_NIR).updateMask(mascara).rename("nir"))
            .addBands(mascara.rename("pixels_validos"))
            .addBands(ee.Image.constant(1).rename("pixels_totais"))
        )
        redutor = ee.Reducer.mean().combine(reducer2=ee.Reducer.sum(), sharedInputs=True)
        reduzidas = bandas.reduceRegions(
            collection=colecao_piquetes, reducer=redutor, scale=_ESCALA_M
        )
        data_str = ee.Date(imagem.get("system:time_start")).format("YYYY-MM-dd")

        def _com_data(feicao: ee.Feature) -> ee.Feature:
            saida = ee.Feature(
                None,
                {
                    "piquete_id": feicao.get("piquete_id"),
                    "data": data_str,
                    "red": feicao.get("red_mean"),
                    "nir": feicao.get("nir_mean"),
                    "pixels_validos": feicao.get("pixels_validos_sum"),
                    "pixels_totais": feicao.get("pixels_totais_sum"),
                },
            )
            return cast(ee.Feature, saida)

        return cast(ee.FeatureCollection, reduzidas.map(_com_data))

    todas = ligadas.map(_amostrar_imagem).flatten()
    info = todas.getInfo()
    linhas = [f["properties"] for f in info.get("features", [])]
    return extrair_observacoes(linhas)


def _extrair_linha(linha: Mapping[str, Any]) -> ObservacaoSatelite | None:
    """Convert one raw GEE row into an observation, or None when unusable."""
    red = linha.get("red")
    nir = linha.get("nir")
    validos = linha.get("pixels_validos")
    totais = linha.get("pixels_totais")
    if red is None or nir is None or validos is None or totais is None:
        return None
    pixels_validos = int(round(float(validos)))
    pixels_totais = int(round(float(totais)))
    if pixels_validos < _MINIMOS_PIXELS_VALIDOS:
        return None
    refletancia_red = float(red)
    refletancia_nir = float(nir)
    if refletancia_red > 1.0 or refletancia_nir > 1.0:
        refletancia_red *= _FATOR_ESCALA_REFLETANCIA
        refletancia_nir *= _FATOR_ESCALA_REFLETANCIA
    if refletancia_red + refletancia_nir <= 0:
        return None
    if not 0.0 <= refletancia_red <= 1.0 or not 0.0 <= refletancia_nir <= 1.0:
        return None
    ndvi = (refletancia_nir - refletancia_red) / (refletancia_nir + refletancia_red)
    if ndvi <= 0:
        return None
    pct_nuvem = (
        100.0 * (1 - pixels_validos / pixels_totais) if pixels_totais > 0 else 100.0
    )
    pct_nuvem = min(100.0, max(0.0, pct_nuvem))
    return ObservacaoSatelite(
        piquete_id=UUID(str(linha["piquete_id"])),
        data=date.fromisoformat(str(linha["data"])),
        ndvi=ndvi,
        refletancia_red=refletancia_red,
        refletancia_nir=refletancia_nir,
        pixels_validos=pixels_validos,
        pixels_totais=pixels_totais,
        pct_nuvem=pct_nuvem,
    )


def extrair_observacoes(
    linhas: Sequence[Mapping[str, Any]],
) -> list[ObservacaoSatelite]:
    """Filter, scale and deduplicate raw GEE rows into observations, sorted."""
    melhores: dict[tuple[UUID, date], ObservacaoSatelite] = {}
    for linha in linhas:
        obs = _extrair_linha(linha)
        if obs is None:
            continue
        chave = (obs.piquete_id, obs.data)
        atual = melhores.get(chave)
        if atual is None or obs.pixels_validos > atual.pixels_validos:
            melhores[chave] = obs
    return sorted(melhores.values(), key=lambda o: (o.piquete_id, o.data))
