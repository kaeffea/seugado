"""Pure forage mass, height, and occupation-time calculations."""

from collections.abc import Sequence


def massa_para_altura(
    massa_kg_ms_ha: float,
    densidade_kg_ha_por_cm: float,
) -> float:
    """Convert standing forage mass to canopy height via a linear density."""
    if densidade_kg_ha_por_cm <= 0:
        raise ValueError("densidade_kg_ha_por_cm must be positive")
    if massa_kg_ms_ha < 0:
        raise ValueError("massa_kg_ms_ha must be non-negative")
    return massa_kg_ms_ha / densidade_kg_ha_por_cm


def altura_para_massa(
    altura_cm: float,
    densidade_kg_ha_por_cm: float,
) -> float:
    """Convert canopy height to standing forage mass via a linear density."""
    if densidade_kg_ha_por_cm <= 0:
        raise ValueError("densidade_kg_ha_por_cm must be positive")
    if altura_cm < 0:
        raise ValueError("altura_cm must be non-negative")
    return altura_cm * densidade_kg_ha_por_cm


def consumo_lote_kg_ms_dia(
    composicao: Sequence[tuple[int, float, float]],
) -> float:
    """Total daily dry-matter intake of a lote, summed across category groups.

    Each item of `composicao` is `(n_animais, peso_medio_kg, fracao_consumo_pv)`:
    the head count, mean live weight in kg, and daily intake as a fraction of
    live weight (e.g. 0.022 for 2.2%) for one category group within the lote.
    """
    total = 0.0
    for n_animais, peso_medio_kg, fracao_consumo_pv in composicao:
        if n_animais < 0:
            raise ValueError("n_animais must be non-negative")
        if peso_medio_kg <= 0:
            raise ValueError("peso_medio_kg must be positive")
        if not 0.0 < fracao_consumo_pv <= 1.0:
            raise ValueError("fracao_consumo_pv must be in (0.0, 1.0]")
        total += n_animais * peso_medio_kg * fracao_consumo_pv
    return total


def dias_ocupacao(  # noqa: PLR0913, PLR0917
    massa_atual_kg_ms_ha: float,
    massa_residuo_kg_ms_ha: float,
    taxa_acumulo_kg_ms_ha_dia: float,
    area_ha: float,
    eficiencia_pastejo: float,
    consumo_lote_kg_ms_dia: float,
) -> float:
    """Return the number of days a lote can graze a piquete."""
    if not 0.0 <= eficiencia_pastejo <= 1.0:
        raise ValueError("eficiencia_pastejo must be in [0.0, 1.0]")
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if consumo_lote_kg_ms_dia <= 0:
        raise ValueError("consumo_lote_kg_ms_dia must be positive")
    if massa_atual_kg_ms_ha <= massa_residuo_kg_ms_ha:
        return 0.0
    numerador = (massa_atual_kg_ms_ha - massa_residuo_kg_ms_ha) * area_ha * eficiencia_pastejo
    denominador = consumo_lote_kg_ms_dia - (
        taxa_acumulo_kg_ms_ha_dia * area_ha * eficiencia_pastejo
    )
    if denominador <= 0:
        return float("inf")
    return numerador / denominador


def taxa_utilizacao(
    massa_pre_pastejo_kg_ms_ha: float,
    massa_pos_pastejo_kg_ms_ha: float,
) -> float:
    """Fraction of pre-grazing forage mass that disappeared during grazing."""
    if massa_pre_pastejo_kg_ms_ha <= 0:
        raise ValueError("massa_pre_pastejo_kg_ms_ha must be positive")
    if massa_pos_pastejo_kg_ms_ha < 0:
        raise ValueError("massa_pos_pastejo_kg_ms_ha must be non-negative")
    if massa_pos_pastejo_kg_ms_ha > massa_pre_pastejo_kg_ms_ha:
        raise ValueError("massa_pos_pastejo_kg_ms_ha must not exceed pre-grazing mass")
    return (massa_pre_pastejo_kg_ms_ha - massa_pos_pastejo_kg_ms_ha) / massa_pre_pastejo_kg_ms_ha


def consumo_individual_kg_ms_dia(
    consumo_total_kg_ms_ha: float,
    area_ha: float,
    dias_ocupacao: float,
    n_animais: int,
) -> float:
    """Descriptive per-animal daily intake, back-calculated from an observed mass loss."""
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if dias_ocupacao <= 0:
        raise ValueError("dias_ocupacao must be positive")
    if n_animais <= 0:
        raise ValueError("n_animais must be positive")
    return consumo_total_kg_ms_ha * area_ha / dias_ocupacao / n_animais


def consumo_pct_pv(
    consumo_individual_kg_ms_dia: float,
    peso_medio_kg: float,
) -> float:
    """Descriptive daily intake as a percentage of live weight (e.g. 2.42, not 0.0242)."""
    if peso_medio_kg <= 0:
        raise ValueError("peso_medio_kg must be positive")
    return consumo_individual_kg_ms_dia / peso_medio_kg * 100
