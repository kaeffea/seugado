"""Pure domain entities for pasture management.

Entities are immutable because current state is derived from an append-only
event log, never mutated in place.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class CategoriaAnimal(StrEnum):
    """Animal category of a cattle group member."""

    BEZERRO = "bezerro"
    NOVILHO = "novilho"
    ADULTO = "adulto"


class QualidadeBase(StrEnum):
    """Nutritional quality tier of a cultivar."""

    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class Confianca(StrEnum):
    """Reliability tier of an estimate or recommendation."""

    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class StatusManejo(StrEnum):
    """Lifecycle status of a manejo read model."""

    RECOMENDADO = "recomendado"
    CONFIRMADO = "confirmado"
    RECUSADO = "recusado"
    DIVERGENTE = "divergente"


class OrigemEvento(StrEnum):
    """Source that produced an event."""

    PRODUTOR = "produtor"
    SISTEMA = "sistema"
    SATELITE = "satelite"
    SAR_INFERIDO = "sar_inferido"


class TipoEvento(StrEnum):
    """Kind of occurrence recorded in the event log."""

    PIQUETE_CRIADO = "piquete_criado"
    PIQUETE_ALTERADO = "piquete_alterado"
    LOTE_CRIADO = "lote_criado"
    LOTE_ALTERADO = "lote_alterado"
    LOTE_DISSOLVIDO = "lote_dissolvido"
    MANEJO_RECOMENDADO = "manejo_recomendado"
    MANEJO_CONFIRMADO = "manejo_confirmado"
    MANEJO_RECUSADO = "manejo_recusado"
    MANEJO_DIVERGENTE = "manejo_divergente"
    LEITURA_SATELITE = "leitura_satelite"
    FOTO_VALIDACAO = "foto_validacao"
    PARAMETRO_ALTERADO = "parametro_alterado"


@dataclass(frozen=True, slots=True)
class Fazenda:
    """Farm; the top-level owner of everything else."""

    id: UUID
    nome: str
    timezone: str  # IANA name
    funcionarios_disponiveis: int
    manejos_por_funcionario_dia: int
    dias_preferenciais_manejo: tuple[int, ...]  # weekday numbers, Monday first
    ativo: bool = True


@dataclass(frozen=True, slots=True)
class Cultivar:
    """Grass variety with its explicit management parameters."""

    id: UUID
    slug: str  # stable machine key
    nome: str  # display name
    altura_entrada_cm: float
    altura_saida_cm: float
    densidade_kg_ha_por_cm: float
    temperatura_base_c: float
    rue_max_g_por_mj: float
    qualidade_base: QualidadeBase


@dataclass(frozen=True, slots=True)
class Piquete:
    """Fenced paddock where one lote grazes for a period."""

    id: UUID
    fazenda_id: UUID
    nome: str
    area_ha: float
    cultivar_id: UUID
    geometria_geojson: dict[str, Any] | None = None
    ativo: bool = True


@dataclass(frozen=True, slots=True)
class ComposicaoLote:
    """Count of animals of one category within a lote."""

    categoria: CategoriaAnimal
    n_animais: int
    peso_medio_kg: float


@dataclass(frozen=True, slots=True)
class Lote:
    """Group of cattle managed as a single unit."""

    id: UUID
    fazenda_id: UUID
    nome: str
    composicao: tuple[ComposicaoLote, ...]
    indissoluvel: bool = False
    ativo: bool = True


@dataclass(frozen=True, slots=True)
class Manejo:
    """Read model: convenience projection of what the event log already contains.

    Nothing in this module writes it and nothing treats it as the source of truth.
    """

    id: UUID
    fazenda_id: UUID
    lote_id: UUID
    piquete_destino_id: UUID
    data_prevista: date
    dias_previstos: int
    motivo: str  # human-readable text shown to the farmer
    confianca: Confianca
    status: StatusManejo
    origem: OrigemEvento
    piquete_origem_id: UUID | None = None
    data_execucao: date | None = None


@dataclass(frozen=True, slots=True)
class Evento:
    """Immutable record of something that happened; mirrors the event log row."""

    id: UUID
    fazenda_id: UUID
    tipo: TipoEvento
    ocorrido_em: datetime  # when it happened in the real world
    registrado_em: datetime  # when the system learned about it
    payload: dict[str, Any]
    origem: OrigemEvento
