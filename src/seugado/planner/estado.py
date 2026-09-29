"""Forage-state helpers used by the weekly planner and by lot registration."""

from collections.abc import Mapping, Sequence
from datetime import date
from uuid import UUID

from seugado.contratos import EstadoProjetado, PiqueteProjetado
from seugado.core import forragem, projecao
from seugado.core.models import CategoriaAnimal, ComposicaoLote, Confianca, Evento, OrigemPeso
from seugado.core.projecao import AlturaMedida, EstadoFazenda, EstadoPiquete, Leitura
from seugado.core.regras import combinar_confianca
from seugado.persistencia.catalogo import CultivarCatalogo, eficiencia_pastejo, resolver_alturas
from seugado.planner import estado_util as util
from seugado.sensing.clima import ClimaDia

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


def _estimar(  # noqa: PLR0913, PLR0917
    piquete: EstadoPiquete,
    densidade_kg_ha_por_cm: float,
    rue_max_g_por_mj: float,
    eficiencia: float | None,
    ancora: AlturaMedida,
    leituras: Sequence[Leitura],
    ctx: util.Contexto,
) -> tuple[float, tuple[float, ...]] | str:
    """(stock today, forecast rates) of one piquete, or the name of what stopped the estimate."""
    entradas = util.entradas_safer(
        piquete.piquete_id, ancora.data, leituras, rue_max_g_por_mj, eficiencia, ctx
    )
    if isinstance(entradas, str):
        return entradas
    dias, previstas = entradas
    try:
        massa_kg_ms_ha = forragem.altura_para_massa(ancora.altura_cm, densidade_kg_ha_por_cm)
        for taxa, consumo_kg_ms_dia in dias:
            massa_kg_ms_ha = avancar_massa_um_dia(
                massa_kg_ms_ha, taxa, consumo_kg_ms_dia, piquete.area_ha, eficiencia
            )
    except ValueError:
        return "estimativa_invalida"
    return massa_kg_ms_ha, previstas


def _projetar_piquete(
    piquete: EstadoPiquete,
    eventos: Sequence[Evento],
    cultivar: CultivarCatalogo,
    centroide: tuple[float, float],
    ctx: util.Contexto,
) -> PiqueteProjetado:
    """Project one active piquete (R3 steps 1-8)."""
    metodo = piquete.metodo_pastejo
    faltantes, ancora, leituras = util.preparar_piquete(piquete, eventos, cultivar, ctx.data_base)
    ultima = leituras[-1] if leituras else None
    dias_imagem = None if ultima is None else (ctx.data_base - ultima.data).days
    densidade = cultivar.densidade_kg_ha_por_cm
    rue = cultivar.rue_max_g_por_mj
    eficiencia = eficiencia_pastejo(cultivar, metodo)
    massa_hoje: float | None = None
    altura_hoje: float | None = None
    taxas: tuple[float, ...] = ()
    resultado: tuple[float, tuple[float, ...]] | str | None = None
    podem_estimar = util.BLOQUEIAM_ESTIMATIVA.isdisjoint(faltantes)
    if podem_estimar and ancora and ultima and densidade is not None and rue is not None:
        resultado = _estimar(piquete, densidade, rue, eficiencia, ancora, leituras, ctx)
    if isinstance(resultado, tuple) and ancora and ultima and densidade is not None:
        massa_hoje, taxas = resultado
        altura_hoje = forragem.massa_para_altura(massa_hoje, densidade)
        confianca, motivo = confianca_estimativa(
            dias_imagem,
            ultima.pixels_validos,
            (ctx.data_base - ancora.data).days,
            util.posicao_por_omissao(ctx.movimentos, piquete.lote_atual_id, piquete.piquete_id),
        )
    else:
        if isinstance(resultado, str):
            util.adicionar(faltantes, resultado)
        confianca = Confianca.BAIXA
        motivo = util.frase_faltante(faltantes[0], cultivar.nome, metodo)
    descansando = piquete.situacao == projecao.SituacaoPiquete.DESCANSANDO
    return PiqueteProjetado(
        piquete_id=piquete.piquete_id,
        nome=piquete.nome,
        area_ha=piquete.area_ha,
        metodo_pastejo=metodo,
        cultivar_slug=cultivar.slug,
        cultivar_nome=cultivar.nome,
        centroide_lat=centroide[0],
        centroide_lon=centroide[1],
        situacao=piquete.situacao,
        lote_atual_id=piquete.lote_atual_id,
        dias_descanso=(ctx.data_base - piquete.desde).days if descansando else 0,
        parametros=resolver_alturas(cultivar, metodo).parametros,
        faltantes=tuple(faltantes),
        descanso_min_dias=cultivar.descanso_min_dias,
        densidade_kg_ha_por_cm=densidade,
        eficiencia_pastejo=eficiencia,
        massa_hoje_kg_ms_ha=massa_hoje,
        altura_hoje_cm=altura_hoje,
        taxa_acumulo_prevista_kg_ms_ha_dia=taxas,
        confianca=confianca,
        motivo_confianca=motivo,
        dias_desde_imagem_limpa=dias_imagem,
    )


def projetar_estado(  # noqa: PLR0913, PLR0917 — arity is the R3 contract
    estado: EstadoFazenda,
    eventos: Sequence[Evento],
    catalogo: Mapping[UUID, CultivarCatalogo],
    centroides: Mapping[UUID, tuple[float, float]],  # piquete_id -> (lat, lon)
    clima: Sequence[ClimaDia],
    et0_media_anual_mm_dia: float,
    lat_fazenda: float,
    data_base: date,
    horizonte_previsao_dias: int = 14,
) -> EstadoProjetado:
    """Forage stock today and forecast growth of every active piquete, plus lote intakes."""
    lotes = sorted(estado.lotes.values(), key=lambda lt: lt.nome)
    consumos = {lt.lote_id: consumo_lote(lt.composicao) for lt in lotes}
    ctx = util.Contexto(
        clima_por_data={c.data: c for c in clima},
        et0_media_anual_mm_dia=et0_media_anual_mm_dia,
        lat_fazenda=lat_fazenda,
        data_base=data_base,
        horizonte_previsao_dias=horizonte_previsao_dias,
        movimentos=util.movimentos_por_lote(eventos, [lt.lote_id for lt in lotes]),
        consumo_por_lote_kg_ms_dia=consumos,
    )
    ativos = sorted((p for p in estado.piquetes.values() if p.ativo), key=lambda p: p.nome)
    return EstadoProjetado(
        fazenda_id=estado.fazenda_id,
        data_base=data_base,
        horizonte_previsao_dias=horizonte_previsao_dias,
        piquetes=tuple(
            _projetar_piquete(p, eventos, catalogo[p.cultivar_id], centroides[p.piquete_id], ctx)
            for p in ativos
        ),
        lotes=tuple(
            util.lote_projetado(lt, consumos[lt.lote_id], confianca_peso(lt.composicao))
            for lt in lotes
        ),
    )
