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
    Evento,
    MetodoPastejo,
    OrigemPeso,
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
    geometria_geojson: dict[str, Any]
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
    refletancia_red: float
    refletancia_nir: float
    origem_ndvi: str
    pct_nuvem: float
    pixels_validos: int


@dataclass(frozen=True, slots=True)
class AlturaMedida:
    """Most recent ruler measurement projected for one piquete."""

    id: UUID
    piquete_id: UUID
    data: date
    altura_cm: float
    meio: str


@dataclass(frozen=True, slots=True)
class EstadoFazenda:
    """Current projected state of one farm, folded from its event log."""

    fazenda_id: UUID
    piquetes: dict[UUID, EstadoPiquete]
    lotes: dict[UUID, EstadoLote]
    leituras: dict[UUID, Leitura]
    alturas: dict[UUID, AlturaMedida]


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
            origem_peso=OrigemPeso(item.get("origem_peso", "produtor")),
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
    alturas: dict[UUID, AlturaMedida] = {}
    for original in ordenados:
        corretivo = corrigidos.get(original.id)
        payload = corretivo.payload if corretivo is not None else original.payload
        _aplicar(original, payload, piquetes, lotes, leituras, alturas, data_referencia)
    return EstadoFazenda(
        fazenda_id=fazenda_id, piquetes=piquetes, lotes=lotes, leituras=leituras, alturas=alturas
    )


def _aplicar(  # noqa: PLR0912, PLR0913, PLR0915, PLR0917
    evento: Evento,
    payload: dict[str, Any],
    piquetes: dict[UUID, EstadoPiquete],
    lotes: dict[UUID, EstadoLote],
    leituras: dict[UUID, Leitura],
    alturas: dict[UUID, AlturaMedida],
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
                geometria_geojson=payload["geometria_geojson"],
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
                geometria_geojson=payload["geometria_geojson"],
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
        case TipoEvento.MANEJO_CONFIRMADO | TipoEvento.MANEJO_DIVERGENTE:
            lote_id = _as_uuid(payload["lote_id"])
            chave = (
                "piquete_destino_id"
                if evento.tipo == TipoEvento.MANEJO_CONFIRMADO
                else "piquete_real_id"
            )
            destino_id = _as_uuid(payload[chave])
            if lote_id not in lotes:
                raise ValueError(f"{evento.tipo.value} for an unknown lote")
            if destino_id not in piquetes:
                raise ValueError(f"{evento.tipo.value} for an unknown piquete")
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
                refletancia_red=payload["refletancia_red"],
                refletancia_nir=payload["refletancia_nir"],
                origem_ndvi=payload["origem_ndvi"],
                pct_nuvem=payload["pct_nuvem"],
                pixels_validos=payload["pixels_validos"],
            )
            atual = leituras.get(leitura.piquete_id)
            if atual is None or leitura.data >= atual.data:
                leituras[leitura.piquete_id] = leitura
        case TipoEvento.ALTURA_MEDIDA:
            medida = AlturaMedida(
                id=_as_uuid(payload["entidade_id"]),
                piquete_id=_as_uuid(payload["piquete_id"]),
                data=_as_date(payload["data"]),
                altura_cm=payload["altura_cm"],
                meio=payload["meio"],
            )
            atual_altura = alturas.get(medida.piquete_id)
            if atual_altura is None or medida.data >= atual_altura.data:
                alturas[medida.piquete_id] = medida
        case _:
            pass  # R7: valid events with no projection effect in this fatia
