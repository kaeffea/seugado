"""Pure grazing management rules and single parameter gateway."""

from dataclasses import dataclass

from seugado.core.models import Cultivar, MetodoPastejo, ParametrosRegime


@dataclass(frozen=True, slots=True)
class ResolucaoParametros:
    """Outcome of resolving a cultivar's height parameters for one grazing method."""

    parametros: ParametrosRegime | None
    faltantes: tuple[str, ...]


def resolver_parametros(
    cultivar: Cultivar,
    metodo: MetodoPastejo,
) -> ResolucaoParametros:
    """Resolve the height parameter block a cultivar carries for one grazing method.

    This is the only function in the codebase allowed to read
    `cultivar.parametros_por_regime`. Everyone else calls this and acts on its result.
    """
    if metodo == MetodoPastejo.ROTACIONADO:
        required = ("altura_entrada_cm", "altura_saida_cm")
    else:
        required = ("altura_maxima_cm", "altura_minima_cm")
    entry: ParametrosRegime | None = None
    for candidate in cultivar.parametros_por_regime:
        if candidate.metodo == metodo:
            entry = candidate
            break
    if entry is None:
        return ResolucaoParametros(parametros=None, faltantes=required)
    missing = tuple(field for field in required if getattr(entry, field) is None)
    if missing:
        return ResolucaoParametros(parametros=None, faltantes=missing)
    return ResolucaoParametros(parametros=entry, faltantes=())


def apto_para_entrada(
    altura_atual_cm: float,
    parametros: ParametrosRegime,
    descanso_cumprido: bool,
) -> bool:
    """Return whether a rotational piquete is ready to receive a lote."""
    if parametros.metodo != MetodoPastejo.ROTACIONADO:
        raise ValueError("apto_para_entrada is defined only for rotacionado blocks")
    if parametros.altura_entrada_cm is None:
        raise ValueError("altura_entrada_cm must be resolved before calling")
    return altura_atual_cm >= parametros.altura_entrada_cm and descanso_cumprido


def precisa_sair(
    altura_atual_cm: float,
    parametros: ParametrosRegime,
) -> bool:
    """Return whether the lote grazing a rotational piquete must leave now."""
    if parametros.metodo != MetodoPastejo.ROTACIONADO:
        raise ValueError("precisa_sair is defined only for rotacionado blocks")
    if parametros.altura_saida_cm is None:
        raise ValueError("altura_saida_cm must be resolved before calling")
    return altura_atual_cm <= parametros.altura_saida_cm


def urgencia(
    altura_atual_cm: float,
    parametros: ParametrosRegime,
) -> float:
    """Return a signed urgency score, in cm, for leaving a rotational piquete.

    Score = altura_saida_cm - altura_atual_cm. Zero or positive means the piquete has
    already reached (or passed) its exit target — `precisa_sair` would be True. More
    negative means more headroom above the exit target, i.e. less urgent. Sorting lotes by
    this score, descending, ranks "must leave now" above "at the point" above "can wait" —
    the ordering `07-MOTOR-DE-OTIMIZACAO.md` §5 (Estágio 1) needs for the greedy heuristic.
    """
    if parametros.metodo != MetodoPastejo.ROTACIONADO:
        raise ValueError("urgencia is defined only for rotacionado blocks")
    if parametros.altura_saida_cm is None:
        raise ValueError("altura_saida_cm must be resolved before calling")
    return parametros.altura_saida_cm - altura_atual_cm


def descanso_cumprido(
    dias_desde_ultima_saida: int,
    descanso_min_dias: float,
) -> bool:
    """Return whether the minimum rest period since the last exit has been met."""
    if dias_desde_ultima_saida < 0:
        raise ValueError("dias_desde_ultima_saida must be non-negative")
    if descanso_min_dias <= 0:
        raise ValueError("descanso_min_dias must be positive")
    return dias_desde_ultima_saida >= descanso_min_dias
