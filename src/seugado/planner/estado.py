"""Forage-state helpers used by the weekly planner and by lot registration."""

from collections.abc import Sequence

from seugado.core import forragem
from seugado.core.models import CategoriaAnimal, ComposicaoLote, Confianca, OrigemPeso
from seugado.core.regras import combinar_confianca

CONSUMO_FRACAO_PV: dict[CategoriaAnimal, float] = {
    CategoriaAnimal.BEZERRO: 0.024,
    CategoriaAnimal.BEZERRA: 0.024,
    CategoriaAnimal.NOVILHO: 0.022,
    CategoriaAnimal.NOVILHA: 0.022,
    CategoriaAnimal.VACA: 0.024,
    CategoriaAnimal.BOI: 0.024,
    CategoriaAnimal.TOURO: 0.024,
}

UA_POR_CATEGORIA: dict[CategoriaAnimal, float] = {
    CategoriaAnimal.BEZERRO: 0.25,
    CategoriaAnimal.BEZERRA: 0.25,
    CategoriaAnimal.NOVILHO: 0.75,
    CategoriaAnimal.NOVILHA: 0.75,
    CategoriaAnimal.VACA: 1.00,
    CategoriaAnimal.BOI: 1.00,
    CategoriaAnimal.TOURO: 1.25,
}

UNIDADE_ANIMAL_KG = 450.0

_SEM_IMAGEM = "nenhuma imagem de satélite sem nuvem nos últimos 30 dias"

# Estimate-confidence thresholds (HIPOTESE-CALIBRAR, ADR-023).
_IMAGEM_ALTA_MAX_DIAS = 5
_IMAGEM_MEDIA_MAX_DIAS = 15
_ALTURA_ALTA_MAX_DIAS = 14
_ALTURA_MEDIA_MAX_DIAS = 42
_PIXELS_ALTA_MIN = 9
_PIXELS_MEDIA_MIN = 3


def peso_por_ua_kg(categoria: CategoriaAnimal) -> float:
    """Fallback mean live weight when the farmer does not know it: UA coefficient × 450 kg."""
    return UA_POR_CATEGORIA[categoria] * UNIDADE_ANIMAL_KG


def consumo_lote(composicao: Sequence[ComposicaoLote]) -> float:
    """Daily dry-matter intake of a lote, kg/day (uses core.forragem.consumo_lote_kg_ms_dia)."""
    return forragem.consumo_lote_kg_ms_dia(
        [
            (item.n_animais, item.peso_medio_kg, CONSUMO_FRACAO_PV[item.categoria])
            for item in composicao
        ]
    )


def confianca_peso(composicao: Sequence[ComposicaoLote]) -> tuple[Confianca, str]:
    """Weight confidence: ALTA when the farmer reported every mean weight, else MEDIA."""
    for item in composicao:
        if item.origem_peso == OrigemPeso.UA_TABELA:
            return (
                Confianca.MEDIA,
                "peso médio estimado pela tabela de Unidade Animal",
            )
    return Confianca.ALTA, "peso médio informado por você"


def avancar_massa_um_dia(
    massa_kg_ms_ha: float,
    taxa_acumulo_kg_ms_ha_dia: float,
    consumo_lote_kg_ms_dia: float,
    area_ha: float,
    eficiencia_pastejo: float | None,
) -> float:
    """Stock at the start of the next day."""
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if consumo_lote_kg_ms_dia == 0:
        return massa_kg_ms_ha + taxa_acumulo_kg_ms_ha_dia
    if eficiencia_pastejo is None or not 0.0 < eficiencia_pastejo <= 1.0:
        raise ValueError("eficiencia_pastejo must be in (0.0, 1.0]")
    return max(
        0.0,
        massa_kg_ms_ha
        + taxa_acumulo_kg_ms_ha_dia
        - consumo_lote_kg_ms_dia / (eficiencia_pastejo * area_ha),
    )


def _ha_dias(dias: int) -> str:
    """Portuguese age fragment: "de hoje" for 0, singular for 1, plural otherwise."""
    if dias == 0:
        return "de hoje"
    if dias == 1:
        return "há 1 dia"
    return f"há {dias} dias"


def _nivel_imagem(dias_desde_imagem: int | None) -> tuple[Confianca, str]:
    """Confidence level and sentence for the cloud-free satellite image age."""
    if dias_desde_imagem is None:
        return Confianca.BAIXA, _SEM_IMAGEM
    if dias_desde_imagem <= _IMAGEM_ALTA_MAX_DIAS:
        nivel = Confianca.ALTA
    elif dias_desde_imagem <= _IMAGEM_MEDIA_MAX_DIAS:
        nivel = Confianca.MEDIA
    else:
        nivel = Confianca.BAIXA
    return nivel, f"última imagem de satélite sem nuvem {_ha_dias(dias_desde_imagem)}"


def _nivel_altura(dias_desde_altura: int) -> tuple[Confianca, str]:
    """Confidence level and sentence for the ruler height measurement age."""
    if dias_desde_altura <= _ALTURA_ALTA_MAX_DIAS:
        nivel = Confianca.ALTA
    elif dias_desde_altura <= _ALTURA_MEDIA_MAX_DIAS:
        nivel = Confianca.MEDIA
    else:
        nivel = Confianca.BAIXA
    return nivel, f"última medição de altura {_ha_dias(dias_desde_altura)}"


def _nivel_pixels(pixels_validos: int | None) -> tuple[Confianca, str]:
    """Confidence level and sentence for the count of clear satellite pixels."""
    if pixels_validos is None:
        return Confianca.BAIXA, _SEM_IMAGEM
    if pixels_validos >= _PIXELS_ALTA_MIN:
        nivel = Confianca.ALTA
    elif pixels_validos >= _PIXELS_MEDIA_MIN:
        nivel = Confianca.MEDIA
    else:
        nivel = Confianca.BAIXA
    frase = f"piquete pequeno para a resolução do satélite ({pixels_validos} pixels úteis)"
    return nivel, frase


def _nivel_posicao(posicao_por_omissao: bool) -> tuple[Confianca, str]:
    """Confidence level and sentence for an unconfirmed assumed last move."""
    if posicao_por_omissao:
        return Confianca.MEDIA, "a última movimentação foi assumida sem confirmação sua"
    return Confianca.ALTA, ""


def confianca_estimativa(
    dias_desde_imagem: int | None,
    pixels_validos: int | None,
    dias_desde_altura: int,
    posicao_por_omissao: bool,
) -> tuple[Confianca, str]:
    """Weakest confidence across the four estimate factors with its sentence."""
    nivel_imagem, frase_imagem = _nivel_imagem(dias_desde_imagem)
    nivel_altura, frase_altura = _nivel_altura(dias_desde_altura)
    nivel_pixels, frase_pixels = _nivel_pixels(pixels_validos)
    nivel_posicao, frase_posicao = _nivel_posicao(posicao_por_omissao)
    resultado = combinar_confianca(nivel_imagem, nivel_altura, nivel_pixels, nivel_posicao)
    if nivel_imagem == resultado:
        return resultado, frase_imagem
    if nivel_altura == resultado:
        return resultado, frase_altura
    if nivel_pixels == resultado:
        return resultado, frase_pixels
    return resultado, frase_posicao
