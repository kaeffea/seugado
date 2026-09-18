"""Pure fold from a farm's event log to its current state."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID

from seugado.core.models import (
    CategoriaAnimal,
    ComposicaoLote,
    Confianca,
    Evento,
    MetodoPastejo,
    TipoEvento,
)


class SituacaoPiquete(StrEnum):
    """Whether a piquete currently holds a lote or is resting."""

    OCUPADO = "ocupado"
    DESCANSANDO = "descansando"


@dataclass(frozen=True, slots=True)
class EstadoPiquete:
    """Current projected state of one piquete."""

    piquete_id: UUID
    fazenda_id: UUID
    nome: str
    area_ha: float
    cultivar_id: UUID
    metodo_pastejo: MetodoPastejo
    ativo: bool
    situacao: SituacaoPiquete
    lote_atual_id: UUID | None
    desde: date
    dias_descanso: int


@dataclass(frozen=True, slots=True)
class EstadoLote:
    """Current projected state of one lote."""

    lote_id: UUID
    fazenda_id: UUID
    nome: str
    composicao: tuple[ComposicaoLote, ...]
    indissoluvel: bool
    piquete_atual_id: UUID | None
    desde: date | None
    peso_vivo_total_kg: float


@dataclass(frozen=True, slots=True)
class Leitura:
    """Most recent satellite reading projected for one piquete."""

    id: UUID
    piquete_id: UUID
    data: date
    ndvi: float
    origem_ndvi: str
    pct_nuvem: float
    pixels_validos: int
    massa_kg_ms_ha: float
    taxa_acumulo_kg_ms_ha_dia: float
    confianca: Confianca


@dataclass(frozen=True, slots=True)
class EstadoFazenda:
    """Current projected state of one farm, folded from its event log."""

    fazenda_id: UUID
    piquetes: dict[UUID, EstadoPiquete]
    lotes: dict[UUID, EstadoLote]
    leituras: dict[UUID, Leitura]


def _as_uuid(value: UUID | str) -> UUID:
    """Coerce a payload identifier to UUID."""
    return value if isinstance(value, UUID) else UUID(str(value))


def _as_date(value: date | str) -> date:
    """Coerce a payload ISO string to date."""
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _composicao(payload_composicao: list[dict[str, Any]]) -> tuple[ComposicaoLote, ...]:
    """Parse a lote payload's category list into immutable composition."""
    return tuple(
        ComposicaoLote(
            categoria=CategoriaAnimal(item["categoria"]),
            n_animais=item["n_animais"],
            peso_medio_kg=item["peso_medio_kg"],
        )
        for item in payload_composicao
    )


def _peso_vivo_total_kg(composicao: tuple[ComposicaoLote, ...]) -> float:
    """Sum live weight over every category group."""
    return float(sum(c.n_animais * c.peso_medio_kg for c in composicao))


def _descansar(piquete: EstadoPiquete, desde: date, data_referencia: date) -> EstadoPiquete:
    """Transition a piquete to resting, recomputing rest days."""
    return replace(
        piquete,
        situacao=SituacaoPiquete.DESCANSANDO,
        lote_atual_id=None,
        desde=desde,
        dias_descanso=(data_referencia - desde).days,
    )


def projetar(eventos: Sequence[Evento]) -> EstadoFazenda:
    """Fold a farm's full event history into its current state."""
    if len(eventos) == 0:
        raise ValueError("eventos must not be empty")
    fazenda_id = eventos[0].fazenda_id
    if any(e.fazenda_id != fazenda_id for e in eventos):
        raise ValueError("all events must share one fazenda_id")
    por_id = {e.id: e for e in eventos}
    corrigidos: dict[UUID, Evento] = {}
    for e in eventos:
        if e.corrige_evento_id is not None:
            if e.corrige_evento_id in corrigidos:
                raise ValueError("two events correct the same id")
            if e.corrige_evento_id not in por_id:
                raise ValueError("dangling corrige_evento_id")
            corrigidos[e.corrige_evento_id] = e
    corretivas = {e.id for e in corrigidos.values()}
    ordenados = sorted(
        (e for e in eventos if e.id not in corretivas),
        key=lambda e: (e.ocorrido_em, e.sequencia),
    )
    data_referencia = max(e.ocorrido_em for e in eventos).date()
    piquetes: dict[UUID, EstadoPiquete] = {}
    lotes: dict[UUID, EstadoLote] = {}
    leituras: dict[UUID, Leitura] = {}
    for original in ordenados:
        corretivo = corrigidos.get(original.id)
        payload = corretivo.payload if corretivo is not None else original.payload
        _aplicar(original, payload, piquetes, lotes, leituras, data_referencia)
    return EstadoFazenda(fazenda_id=fazenda_id, piquetes=piquetes, lotes=lotes, leituras=leituras)


def _aplicar(  # noqa: PLR0912, PLR0913, PLR0917
    evento: Evento,
    payload: dict[str, Any],
    piquetes: dict[UUID, EstadoPiquete],
    lotes: dict[UUID, EstadoLote],
    leituras: dict[UUID, Leitura],
    data_referencia: date,
) -> None:
    """Apply one event's effective content to the folded state."""
    match evento.tipo:
        case TipoEvento.PIQUETE_CRIADO:
            desde = evento.ocorrido_em.date()
            piquetes[_as_uuid(payload["entidade_id"])] = EstadoPiquete(
                piquete_id=_as_uuid(payload["entidade_id"]),
                fazenda_id=evento.fazenda_id,
                nome=payload["nome"],
                area_ha=payload["area_ha"],
                cultivar_id=_as_uuid(payload["cultivar_id"]),
                metodo_pastejo=MetodoPastejo(payload["metodo_pastejo"]),
                ativo=payload["ativo"],
                situacao=SituacaoPiquete.DESCANSANDO,
                lote_atual_id=None,
                desde=desde,
                dias_descanso=(data_referencia - desde).days,
            )
        case TipoEvento.PIQUETE_ALTERADO:
            piquete_id = _as_uuid(payload["entidade_id"])
            if piquete_id not in piquetes:
                raise ValueError("piquete_alterado for an unknown piquete")
            piquetes[piquete_id] = replace(
                piquetes[piquete_id],
                nome=payload["nome"],
                area_ha=payload["area_ha"],
                cultivar_id=_as_uuid(payload["cultivar_id"]),
                metodo_pastejo=MetodoPastejo(payload["metodo_pastejo"]),
                ativo=payload["ativo"],
            )
        case TipoEvento.LOTE_CRIADO:
            composicao = _composicao(payload["composicao"])
            lotes[_as_uuid(payload["entidade_id"])] = EstadoLote(
                lote_id=_as_uuid(payload["entidade_id"]),
                fazenda_id=evento.fazenda_id,
                nome=payload["nome"],
                composicao=composicao,
                indissoluvel=payload["indissoluvel"],
                piquete_atual_id=None,
                desde=None,
                peso_vivo_total_kg=_peso_vivo_total_kg(composicao),
            )
        case TipoEvento.LOTE_ALTERADO:
            lote_id = _as_uuid(payload["entidade_id"])
            if lote_id not in lotes:
                raise ValueError("lote_alterado for an unknown lote")
            composicao = _composicao(payload["composicao"])
            lotes[lote_id] = replace(
                lotes[lote_id],
                nome=payload["nome"],
                composicao=composicao,
                indissoluvel=payload["indissoluvel"],
                peso_vivo_total_kg=_peso_vivo_total_kg(composicao),
            )
        case TipoEvento.LOTE_DISSOLVIDO:
            lote_id = _as_uuid(payload["entidade_id"])
            if lote_id not in lotes:
                raise ValueError("lote_dissolvido for an unknown lote")
            lote = lotes.pop(lote_id)
            if lote.piquete_atual_id is not None and lote.piquete_atual_id in piquetes:
                piquetes[lote.piquete_atual_id] = _descansar(
                    piquetes[lote.piquete_atual_id],
                    evento.ocorrido_em.date(),
                    data_referencia,
                )
        case TipoEvento.MANEJO_CONFIRMADO:
            lote_id = _as_uuid(payload["lote_id"])
            destino_id = _as_uuid(payload["piquete_destino_id"])
            if lote_id not in lotes:
                raise ValueError("manejo_confirmado for an unknown lote")
            if destino_id not in piquetes:
                raise ValueError("manejo_confirmado for an unknown piquete")
            data_execucao = _as_date(payload["data_execucao"])
            lote = lotes[lote_id]
            if lote.piquete_atual_id is not None and lote.piquete_atual_id in piquetes:
                piquetes[lote.piquete_atual_id] = _descansar(
                    piquetes[lote.piquete_atual_id], data_execucao, data_referencia
                )
            piquetes[destino_id] = replace(
                piquetes[destino_id],
                situacao=SituacaoPiquete.OCUPADO,
                lote_atual_id=lote_id,
                desde=data_execucao,
                dias_descanso=0,
            )
            lotes[lote_id] = replace(lote, piquete_atual_id=destino_id, desde=data_execucao)
        case TipoEvento.LEITURA_SATELITE:
            leitura = Leitura(
                id=_as_uuid(payload["entidade_id"]),
                piquete_id=_as_uuid(payload["piquete_id"]),
                data=_as_date(payload["data"]),
                ndvi=payload["ndvi"],
                origem_ndvi=payload["origem_ndvi"],
                pct_nuvem=payload["pct_nuvem"],
                pixels_validos=payload["pixels_validos"],
                massa_kg_ms_ha=payload["massa_kg_ms_ha"],
                taxa_acumulo_kg_ms_ha_dia=payload["taxa_acumulo_kg_ms_ha_dia"],
                confianca=Confianca(payload["confianca"]),
            )
            atual = leituras.get(leitura.piquete_id)
            if atual is None or leitura.data >= atual.data:
                leituras[leitura.piquete_id] = leitura
        case _:
            pass  # R7: valid events with no projection effect in this fatia
