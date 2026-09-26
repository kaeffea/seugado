"""Cultivar catalog with per-farm height overrides applied."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

import psycopg

from seugado.core.models import (
    Confianca,
    Cultivar,
    Evento,
    MetodoPastejo,
    ParametrosRegime,
    QualidadeBase,
    TipoEvento,
)
from seugado.core.regras import ResolucaoParametros, resolver_parametros
from seugado.persistencia.projecao_db import carregar_eventos


@dataclass(frozen=True, slots=True)
class CultivarCatalogo:
    """A catalog cultivar with this farm's overrides applied; numeric gaps stay None."""

    id: UUID
    slug: str
    nome: str
    parametros_por_regime: tuple[ParametrosRegime, ...]
    eficiencia_por_metodo: tuple[tuple[MetodoPastejo, float], ...]
    densidade_kg_ha_por_cm: float | None
    rue_max_g_por_mj: float | None
    temperatura_base_c: float | None
    descanso_min_dias: float
    qualidade_base: QualidadeBase | None


CAMPOS_ALTURA = ("altura_entrada_cm", "altura_saida_cm", "altura_maxima_cm", "altura_minima_cm")

_SELECT_CULTIVARES = "SELECT id, slug, nome, parametros FROM cultivar ORDER BY nome"


def _numero(valor: float | int | str | None) -> float | None:
    """Coerce an optional JSON number to float."""
    return None if valor is None else float(valor)


def _as_uuid(value: UUID | str) -> UUID:
    """Coerce a payload identifier to UUID."""
    return value if isinstance(value, UUID) else UUID(str(value))


def cultivar_de_linha(
    id: UUID, slug: str, nome: str, parametros: dict[str, Any]
) -> CultivarCatalogo:
    """Parse one cultivar row into a catalog entry, keeping numeric gaps as None."""
    regimes = parametros.get("por_regime")
    if not isinstance(regimes, list):
        raise ValueError("parametros misses por_regime")
    blocos: list[ParametrosRegime] = []
    eficiencias: list[tuple[MetodoPastejo, float]] = []
    for entry in regimes:
        try:
            metodo = MetodoPastejo(entry["metodo"])
            confianca = Confianca(entry["confianca"])
        except KeyError as exc:
            raise ValueError(f"regime entry misses {exc}") from exc
        blocos.append(
            ParametrosRegime(
                metodo=metodo,
                altura_entrada_cm=_numero(entry.get("altura_entrada_cm")),
                altura_saida_cm=_numero(entry.get("altura_saida_cm")),
                altura_maxima_cm=_numero(entry.get("altura_maxima_cm")),
                altura_minima_cm=_numero(entry.get("altura_minima_cm")),
                confianca=confianca,
                fonte=entry["fonte"],
            )
        )
        eficiencia = entry.get("eficiencia_pastejo")
        if eficiencia is not None:
            eficiencias.append((metodo, float(eficiencia)))
    qualidade = parametros.get("qualidade_base")
    return CultivarCatalogo(
        id=id,
        slug=slug,
        nome=nome,
        parametros_por_regime=tuple(blocos),
        eficiencia_por_metodo=tuple(eficiencias),
        densidade_kg_ha_por_cm=_numero(parametros.get("densidade_kg_ha_por_cm")),
        rue_max_g_por_mj=_numero(parametros.get("rue_max_g_por_mj")),
        temperatura_base_c=_numero(parametros.get("temperatura_base_c")),
        descanso_min_dias=float(parametros["descanso_min_dias"]),
        qualidade_base=None if qualidade is None else QualidadeBase(qualidade),
    )


def overrides_da_fazenda(
    eventos: Sequence[Evento],
) -> dict[UUID, tuple[tuple[MetodoPastejo, str, float], ...]]:
    """Collect each farm override cell's latest value, keyed by cultivar id."""
    ordenados = sorted(
        (e for e in eventos if e.tipo == TipoEvento.PARAMETRO_ALTERADO),
        key=lambda e: (e.ocorrido_em, e.sequencia),
    )
    celulas: dict[tuple[UUID, MetodoPastejo, str], float] = {}
    for e in ordenados:
        chave = (
            _as_uuid(e.payload["cultivar_id"]),
            MetodoPastejo(e.payload["metodo_pastejo"]),
            str(e.payload["campo"]),
        )
        celulas[chave] = float(e.payload["valor"])
    agrupados: dict[UUID, list[tuple[MetodoPastejo, str, float]]] = {}
    for (cultivar_id, metodo, campo), valor in celulas.items():
        agrupados.setdefault(cultivar_id, []).append((metodo, campo, valor))
    return {cultivar_id: tuple(cells) for cultivar_id, cells in agrupados.items()}


def aplicar_overrides(
    cultivar: CultivarCatalogo,
    overrides: Sequence[tuple[MetodoPastejo, str, float]],
    fazenda_id: UUID,
) -> CultivarCatalogo:
    """Return a copy of the cultivar with farm height overrides applied."""
    for _, campo, _ in overrides:
        if campo not in CAMPOS_ALTURA:
            raise ValueError(f"unknown override campo {campo!r}")
    fonte = f"produtor:{fazenda_id}"
    blocos: dict[MetodoPastejo, ParametrosRegime] = {
        b.metodo: b for b in cultivar.parametros_por_regime
    }
    for metodo, campo, valor in overrides:
        atual = blocos.get(metodo)
        entrada = atual.altura_entrada_cm if atual is not None else None
        saida = atual.altura_saida_cm if atual is not None else None
        maxima = atual.altura_maxima_cm if atual is not None else None
        minima = atual.altura_minima_cm if atual is not None else None
        if campo == "altura_entrada_cm":
            entrada = valor
        elif campo == "altura_saida_cm":
            saida = valor
        elif campo == "altura_maxima_cm":
            maxima = valor
        else:  # validated above: the only remaining CAMPOS_ALTURA member
            minima = valor
        blocos[metodo] = ParametrosRegime(
            metodo=metodo,
            altura_entrada_cm=entrada,
            altura_saida_cm=saida,
            altura_maxima_cm=maxima,
            altura_minima_cm=minima,
            confianca=Confianca.BAIXA,
            fonte=fonte,
        )
    return replace(cultivar, parametros_por_regime=tuple(blocos.values()))


def carregar_catalogo(
    conn: psycopg.Connection[Any], fazenda_id: UUID | None
) -> dict[UUID, CultivarCatalogo]:
    """Load the catalog, applying one farm's overrides when fazenda_id is given."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_CULTIVARES)
        linhas = cur.fetchall()
    catalogo = {row[0]: cultivar_de_linha(row[0], row[1], row[2], dict(row[3])) for row in linhas}
    if fazenda_id is None:
        return catalogo
    overrides = overrides_da_fazenda(carregar_eventos(conn, fazenda_id))
    for cultivar_id, cells in overrides.items():
        atual = catalogo.get(cultivar_id)
        if atual is not None:
            catalogo[cultivar_id] = aplicar_overrides(atual, cells, fazenda_id)
    return catalogo


def resolver_alturas(cultivar: CultivarCatalogo, metodo: MetodoPastejo) -> ResolucaoParametros:
    """Resolve one method's height block through the single parameter gateway."""
    ponte = Cultivar(
        id=cultivar.id,
        slug=cultivar.slug,
        nome=cultivar.nome,
        parametros_por_regime=cultivar.parametros_por_regime,
        densidade_kg_ha_por_cm=(
            0.0 if cultivar.densidade_kg_ha_por_cm is None else cultivar.densidade_kg_ha_por_cm
        ),
        temperatura_base_c=(
            0.0 if cultivar.temperatura_base_c is None else cultivar.temperatura_base_c
        ),
        rue_max_g_por_mj=(0.0 if cultivar.rue_max_g_por_mj is None else cultivar.rue_max_g_por_mj),
        qualidade_base=(
            QualidadeBase.MEDIA if cultivar.qualidade_base is None else cultivar.qualidade_base
        ),
    )
    return resolver_parametros(ponte, metodo)


def eficiencia_pastejo(cultivar: CultivarCatalogo, metodo: MetodoPastejo) -> float | None:
    """Return grazing efficiency for one method, or None when unknown."""
    for par_metodo, valor in cultivar.eficiencia_por_metodo:
        if par_metodo == metodo:
            return valor
    return None


def faltantes_calibracao(cultivar: CultivarCatalogo, metodo: MetodoPastejo) -> tuple[str, ...]:
    """Name calibration gaps in fixed order for one method."""
    faltantes: list[str] = []
    if cultivar.densidade_kg_ha_por_cm is None:
        faltantes.append("densidade_kg_ha_por_cm")
    if cultivar.rue_max_g_por_mj is None:
        faltantes.append("rue_max_g_por_mj")
    if metodo == MetodoPastejo.ROTACIONADO and eficiencia_pastejo(cultivar, metodo) is None:
        faltantes.append("eficiencia_pastejo")
    return tuple(faltantes)
