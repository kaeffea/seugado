"""Pure event-log helpers for projetar_estado: anchors, readings, occupation and sentences."""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from seugado.contratos import LoteProjetado
from seugado.core.models import Confianca, Evento, MetodoPastejo, OrigemEvento, TipoEvento
from seugado.core.projecao import AlturaMedida, EstadoLote, EstadoPiquete, Leitura
from seugado.persistencia.catalogo import CultivarCatalogo, faltantes_calibracao, resolver_alturas
from seugado.sensing.clima import ClimaDia, radiacao_extraterrestre_mj_m2_dia
from seugado.sensing.safer import SaferForaDaFaixa, taxa_acumulo_safer

logger = logging.getLogger(__name__)

_JANELA_SATELITE_DIAS = 30  # satellite lookback, HIPOTESE-CALIBRAR (ADR-023)
BLOQUEIAM_ESTIMATIVA = frozenset(
    {"altura_inicial", "imagem_satelite", "densidade_kg_ha_por_cm", "rue_max_g_por_mj"}
)

_FRASE_ALTURA = {
    "altura_entrada_cm": "entrada",
    "altura_saida_cm": "saída",
    "altura_maxima_cm": "máxima",
    "altura_minima_cm": "mínima",
}
_FRASE_METODO = {MetodoPastejo.ROTACIONADO: "rotacionado", MetodoPastejo.CONTINUO: "contínuo"}
_CALIBRACAO = ("densidade_kg_ha_por_cm", "rue_max_g_por_mj", "eficiencia_pastejo")
_FRASES_FIXAS = {
    "altura_inicial": "nenhuma medição de altura com régua registrada para este piquete",
    "imagem_satelite": "nenhuma imagem de satélite sem nuvem nos últimos 30 dias",
    "clima": "faltam dados de clima para o período",
    "estimativa_invalida": "o cálculo por satélite saiu da faixa esperada",
}


@dataclass(frozen=True, slots=True)
class Movimento:
    """One executed move of a lote into a piquete."""

    lote_id: UUID
    piquete_id: UUID
    data_execucao: date
    origem: OrigemEvento


def _as_uuid(value: UUID | str) -> UUID:
    """Coerce a payload identifier to UUID."""
    return value if isinstance(value, UUID) else UUID(str(value))


def _as_date(value: date | str) -> date:
    """Coerce a payload ISO string to date."""
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _ordenados(eventos: Sequence[Evento]) -> list[Evento]:
    """Events in (ocorrido_em, sequencia) order."""
    return sorted(eventos, key=lambda e: (e.ocorrido_em, e.sequencia))


def _medicoes(eventos: Sequence[Evento], tipo: TipoEvento) -> list[dict[str, Any]]:
    """Effective payloads of one measurement type, in event order, with corrections applied."""
    corretivos = {e.corrige_evento_id: e for e in eventos if e.corrige_evento_id is not None}
    ids_corretivos = {e.id for e in corretivos.values()}
    payloads: list[dict[str, Any]] = []
    for e in _ordenados(eventos):
        if e.tipo != tipo or e.id in ids_corretivos:
            continue
        corretivo = corretivos.get(e.id)
        payloads.append(corretivo.payload if corretivo is not None else e.payload)
    return payloads


def ancora_altura(
    eventos: Sequence[Evento], piquete_id: UUID, data_base: date
) -> AlturaMedida | None:
    """The piquete's ruler measurement with the greatest date on or before data_base."""
    ancora: AlturaMedida | None = None
    for payload in _medicoes(eventos, TipoEvento.ALTURA_MEDIDA):
        if _as_uuid(payload["piquete_id"]) != piquete_id:
            continue
        medida = AlturaMedida(
            _as_uuid(payload["entidade_id"]), piquete_id, _as_date(payload["data"]),
            float(payload["altura_cm"]), str(payload["meio"]),
        )  # fmt: skip
        if medida.data <= data_base and (ancora is None or medida.data >= ancora.data):
            ancora = medida
    return ancora


def leituras_piquete(
    eventos: Sequence[Evento], piquete_id: UUID, data_base: date
) -> tuple[Leitura, ...]:
    """The piquete's satellite readings dated on or before data_base, sorted by date."""
    leituras: list[Leitura] = []
    for payload in _medicoes(eventos, TipoEvento.LEITURA_SATELITE):
        if _as_uuid(payload["piquete_id"]) != piquete_id:
            continue
        leitura = Leitura(
            _as_uuid(payload["entidade_id"]), piquete_id, _as_date(payload["data"]),
            float(payload["ndvi"]), float(payload["refletancia_red"]),
            float(payload["refletancia_nir"]), str(payload["origem_ndvi"]),
            float(payload["pct_nuvem"]), int(payload["pixels_validos"]),
        )  # fmt: skip
        if leitura.data <= data_base:
            leituras.append(leitura)
    return tuple(sorted(leituras, key=lambda lt: lt.data))


def leitura_do_dia(leituras: Sequence[Leitura], dia: date) -> Leitura:
    """Latest reading dated on or before `dia`; the earliest one when none is."""
    escolhida = leituras[0]
    for leitura in leituras:
        if leitura.data <= dia:
            escolhida = leitura
    return escolhida


def movimentos_por_lote(
    eventos: Sequence[Evento], lote_ids: Sequence[UUID]
) -> dict[UUID, tuple[Movimento, ...]]:
    """Executed moves of each known lote, in (ocorrido_em, sequencia) order."""
    conhecidos = set(lote_ids)
    por_lote: dict[UUID, list[Movimento]] = {}
    for e in _ordenados(eventos):
        if e.tipo == TipoEvento.MANEJO_CONFIRMADO:
            chave = "piquete_destino_id"
        elif e.tipo == TipoEvento.MANEJO_DIVERGENTE:
            chave = "piquete_real_id"
        else:
            continue
        lote_id = _as_uuid(e.payload["lote_id"])
        if lote_id not in conhecidos:
            continue
        destino_id = _as_uuid(e.payload[chave])
        data_execucao = _as_date(e.payload["data_execucao"])
        por_lote.setdefault(lote_id, []).append(
            Movimento(lote_id, destino_id, data_execucao, e.origem)
        )
    return {lote_id: tuple(movs) for lote_id, movs in por_lote.items()}


def lotes_no_piquete(
    movimentos: Mapping[UUID, Sequence[Movimento]], piquete_id: UUID, dia: date
) -> list[UUID]:
    """Lotes occupying the piquete on `dia`: from a move's date until the lote's next move."""
    ocupantes: list[UUID] = []
    for lote_id, movs in movimentos.items():
        fins = [m.data_execucao for m in movs[1:]] + [date.max]
        if any(
            m.piquete_id == piquete_id and m.data_execucao <= dia < fim
            for m, fim in zip(movs, fins, strict=True)
        ):
            ocupantes.append(lote_id)
    return ocupantes


def posicao_por_omissao(
    movimentos: Mapping[UUID, Sequence[Movimento]], lote_id: UUID | None, piquete_id: UUID
) -> bool:
    """Whether the move that put the current lote in this piquete was assumed by the system."""
    if lote_id is None or not movimentos.get(lote_id):
        return False
    ultimo = movimentos[lote_id][-1]
    return ultimo.piquete_id == piquete_id and ultimo.origem == OrigemEvento.SISTEMA


def frase_faltante(item: str, cultivar_nome: str, metodo: MetodoPastejo) -> str:
    """Portuguese confidence sentence for a missing item."""
    if item in _FRASE_ALTURA:
        return (
            f"falta a altura de {_FRASE_ALTURA[item]} do {cultivar_nome}"
            f" no pastejo {_FRASE_METODO[metodo]}"
        )
    if item in _CALIBRACAO:
        return f"a cultivar {cultivar_nome} ainda não tem calibração no SeuGado"
    return _FRASES_FIXAS[item]


def adicionar(faltantes: list[str], item: str) -> None:
    """Append an item keeping insertion order without duplicates."""
    if item not in faltantes:
        faltantes.append(item)


def imagem_recente(leitura: Leitura, data_base: date) -> bool:
    """Whether a reading is within the satellite lookback window."""
    return leitura.data >= data_base - timedelta(days=_JANELA_SATELITE_DIAS)


def preparar_piquete(
    piquete: EstadoPiquete, eventos: Sequence[Evento], cultivar: CultivarCatalogo, data_base: date
) -> tuple[list[str], AlturaMedida | None, tuple[Leitura, ...]]:
    """R3 steps 1-3: the piquete's gaps so far, its ruler anchor and its readings."""
    metodo = piquete.metodo_pastejo
    faltantes: list[str] = []
    for item in (
        *resolver_alturas(cultivar, metodo).faltantes,
        *faltantes_calibracao(cultivar, metodo),
    ):
        adicionar(faltantes, item)
    ancora = ancora_altura(eventos, piquete.piquete_id, data_base)
    if ancora is None:
        adicionar(faltantes, "altura_inicial")
    leituras = leituras_piquete(eventos, piquete.piquete_id, data_base)
    if not any(imagem_recente(lt, data_base) for lt in leituras):
        adicionar(faltantes, "imagem_satelite")
    return faltantes, ancora, leituras


def lote_projetado(
    lote: EstadoLote, consumo_kg_ms_dia: float, confianca_peso: tuple[Confianca, str]
) -> LoteProjetado:
    """A lote with its current composition's intake and weight confidence."""
    return LoteProjetado(
        lote_id=lote.lote_id,
        nome=lote.nome,
        composicao=lote.composicao,
        indissoluvel=lote.indissoluvel,
        piquete_atual_id=lote.piquete_atual_id,
        desde=lote.desde,
        peso_vivo_total_kg=lote.peso_vivo_total_kg,
        consumo_kg_ms_dia=consumo_kg_ms_dia,
        confianca_peso=confianca_peso[0],
        motivo_confianca_peso=confianca_peso[1],
    )


@dataclass(frozen=True, slots=True)
class Contexto:
    """Farm-wide inputs shared by every piquete's estimate."""

    clima_por_data: Mapping[date, ClimaDia]
    et0_media_anual_mm_dia: float
    lat_fazenda: float
    data_base: date
    horizonte_previsao_dias: int
    movimentos: Mapping[UUID, Sequence[Movimento]]
    consumo_por_lote_kg_ms_dia: Mapping[UUID, float]


def taxa_dia(
    leitura: Leitura, clima_dia: ClimaDia, rue_max_g_por_mj: float, ctx: Contexto
) -> float:
    """SAFER growth rate for one day, kg DM/ha/day (SaferForaDaFaixa propagates)."""
    return taxa_acumulo_safer(
        leitura.ndvi,
        leitura.refletancia_red,
        leitura.refletancia_nir,
        clima_dia.rg_mj_m2_dia,
        clima_dia.t_media_c,
        radiacao_extraterrestre_mj_m2_dia(ctx.lat_fazenda, clima_dia.data),
        ctx.et0_media_anual_mm_dia,
        rue_max_g_por_mj,
    ).taxa_acumulo_kg_ms_ha_dia


def entradas_safer(  # noqa: PLR0913, PLR0917
    piquete_id: UUID,
    inicio: date,
    leituras: Sequence[Leitura],
    rue_max_g_por_mj: float,
    eficiencia_pastejo: float | None,
    ctx: Contexto,
) -> tuple[list[tuple[float, float]], tuple[float, ...], Leitura] | str:
    """Inputs of the stock simulation and forecast, or the name of what is missing.

    First item: (growth rate, lote intake) for each day from `inicio` to data_base − 1.
    Second item: forecast growth rates from data_base on, the latest reading held constant.
    Third item: latest surviving reading, for image age and confidence.
    """
    dias: list[tuple[float, float]] = []
    previstas: list[float] = []
    validas = list(leituras)
    dia = inicio
    fim = ctx.data_base + timedelta(days=ctx.horizonte_previsao_dias)
    try:
        while validas and dia < fim:
            clima_dia = ctx.clima_por_data.get(dia)
            if clima_dia is None:
                return "clima"
            ocupantes = (
                lotes_no_piquete(ctx.movimentos, piquete_id, dia) if dia < ctx.data_base else []
            )
            if ocupantes and eficiencia_pastejo is None:
                return "eficiencia_pastejo"
            leitura = leitura_do_dia(validas, min(dia, ctx.data_base))
            try:
                taxa = taxa_dia(leitura, clima_dia, rue_max_g_por_mj, ctx)
            except SaferForaDaFaixa as exc:
                logger.warning(
                    "Leitura %s de %s do piquete %s descartada no cálculo de %s: %s",
                    leitura.id, leitura.data, piquete_id, dia, exc,
                )
                validas.remove(leitura)
                # Recompute earlier days too: a discarded reading must contribute nothing.
                dias.clear()
                previstas.clear()
                dia = inicio
                continue
            if dia < ctx.data_base:
                dias.append((taxa, sum(ctx.consumo_por_lote_kg_ms_dia[lt] for lt in ocupantes)))
            else:
                previstas.append(taxa)
            dia += timedelta(days=1)
    except ValueError:
        return "estimativa_invalida"
    if not validas:
        return "estimativa_invalida"
    return dias, tuple(previstas), leitura_do_dia(validas, ctx.data_base)
