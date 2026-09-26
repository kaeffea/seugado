"""Validated write gateway for the append-only event log."""

from datetime import date, datetime
from typing import Any, Literal, cast
from uuid import UUID

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.types.json import Json
from pydantic import BaseModel, ConfigDict, Field, field_validator

from seugado.core.models import OrigemEvento, TipoEvento


class _PayloadBase(BaseModel):
    """Shared config: payloads carry exactly their declared fields."""

    model_config = ConfigDict(extra="forbid")


class ComposicaoPayload(_PayloadBase):
    """One category group within a lote payload."""

    categoria: Literal["bezerro", "novilho", "adulto"]
    n_animais: int = Field(gt=0)
    peso_medio_kg: float = Field(gt=0)
    origem_peso: Literal["produtor", "ua_tabela"]


_MIN_POSICOES_ANEL = 4


def _validar_poligono(value: dict[str, Any]) -> dict[str, Any]:
    """Check that a GeoJSON dict is a Polygon with a closed-enough outer ring."""
    if value.get("type") != "Polygon":
        raise ValueError("geometria_geojson must have type Polygon")
    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) == 0:
        raise ValueError("geometria_geojson must carry a coordinates list")
    ring = coordinates[0]
    if not isinstance(ring, list) or len(ring) < _MIN_POSICOES_ANEL:
        raise ValueError("geometria_geojson first ring needs at least 4 positions")
    return value


class PayloadPiqueteCriado(_PayloadBase):
    entidade_id: UUID
    nome: str
    area_ha: float = Field(gt=0)
    cultivar_id: UUID
    metodo_pastejo: Literal["continuo", "rotacionado"]
    ativo: bool
    geometria_geojson: dict[str, Any]

    @field_validator("geometria_geojson")
    @classmethod
    def _check_geometria(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validar_poligono(value)


class PayloadPiqueteAlterado(_PayloadBase):
    entidade_id: UUID
    nome: str
    area_ha: float = Field(gt=0)
    cultivar_id: UUID
    metodo_pastejo: Literal["continuo", "rotacionado"]
    ativo: bool
    geometria_geojson: dict[str, Any]

    @field_validator("geometria_geojson")
    @classmethod
    def _check_geometria(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validar_poligono(value)


class PayloadLoteCriado(_PayloadBase):
    entidade_id: UUID
    nome: str
    composicao: list[ComposicaoPayload]
    indissoluvel: bool


class PayloadLoteAlterado(_PayloadBase):
    entidade_id: UUID
    nome: str
    composicao: list[ComposicaoPayload]
    indissoluvel: bool
    ativo: bool


class PayloadLoteDissolvido(_PayloadBase):
    entidade_id: UUID


class PayloadManejoRecomendado(_PayloadBase):
    entidade_id: UUID
    lote_id: UUID
    piquete_origem_id: UUID | None
    piquete_destino_id: UUID
    data_prevista: date
    dias_previstos: int
    motivo: str
    confianca: Literal["alta", "media", "baixa"]
    motivo_confianca: str


class PayloadManejoConfirmado(_PayloadBase):
    entidade_id: UUID
    lote_id: UUID
    piquete_destino_id: UUID
    data_execucao: date


class PayloadManejoRecusado(_PayloadBase):
    entidade_id: UUID
    motivo: str | None


class PayloadManejoDivergente(_PayloadBase):
    entidade_id: UUID
    lote_id: UUID
    piquete_real_id: UUID
    data_execucao: date
    observacao: str | None


class PayloadLeituraSatelite(_PayloadBase):
    entidade_id: UUID
    piquete_id: UUID
    data: date
    ndvi: float = Field(gt=0, le=1)
    refletancia_red: float = Field(ge=0, le=1)
    refletancia_nir: float = Field(ge=0, le=1)
    origem_ndvi: Literal["optico"]
    pct_nuvem: float = Field(ge=0, le=100)
    pixels_validos: int = Field(gt=0)


class PayloadFotoValidacao(_PayloadBase):
    entidade_id: UUID
    piquete_id: UUID
    url_foto: str
    altura_informada_cm: float | None
    data: date


class PayloadParametroAlterado(_PayloadBase):
    entidade_id: UUID
    cultivar_id: UUID
    metodo_pastejo: Literal["continuo", "rotacionado"]
    campo: str
    valor: float
    origem: Literal["produtor"]
    confianca: Literal["alta", "media", "baixa"]


class PayloadAlturaMedida(_PayloadBase):
    entidade_id: UUID
    piquete_id: UUID
    data: date
    altura_cm: float = Field(gt=0, le=400)
    meio: Literal["cadastro", "bot", "web"]


PAYLOAD_POR_TIPO: dict[TipoEvento, type[BaseModel]] = {
    TipoEvento.PIQUETE_CRIADO: PayloadPiqueteCriado,
    TipoEvento.PIQUETE_ALTERADO: PayloadPiqueteAlterado,
    TipoEvento.LOTE_CRIADO: PayloadLoteCriado,
    TipoEvento.LOTE_ALTERADO: PayloadLoteAlterado,
    TipoEvento.LOTE_DISSOLVIDO: PayloadLoteDissolvido,
    TipoEvento.MANEJO_RECOMENDADO: PayloadManejoRecomendado,
    TipoEvento.MANEJO_CONFIRMADO: PayloadManejoConfirmado,
    TipoEvento.MANEJO_RECUSADO: PayloadManejoRecusado,
    TipoEvento.MANEJO_DIVERGENTE: PayloadManejoDivergente,
    TipoEvento.LEITURA_SATELITE: PayloadLeituraSatelite,
    TipoEvento.FOTO_VALIDACAO: PayloadFotoValidacao,
    TipoEvento.PARAMETRO_ALTERADO: PayloadParametroAlterado,
    TipoEvento.ALTURA_MEDIDA: PayloadAlturaMedida,
}

_INSERT_EVENTO = (
    "INSERT INTO evento (fazenda_id, tipo, origem, ocorrido_em, payload, ator,"
    " corrige_evento_id, chave_idempotencia)"
    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
)

_SELECT_ID_POR_CHAVE = "SELECT id FROM evento WHERE fazenda_id = %s AND chave_idempotencia = %s"


def registrar_evento(  # noqa: PLR0913, PLR0917 — arity is the R3 contract
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    tipo: TipoEvento,
    origem: OrigemEvento,
    ocorrido_em: datetime,
    payload: dict[str, Any],
    ator: str | None = None,
    corrige_evento_id: UUID | None = None,
    chave_idempotencia: str | None = None,
) -> UUID:
    """Validate payload against tipo's schema, insert the event, return its id."""
    modelo = PAYLOAD_POR_TIPO.get(tipo)
    if modelo is None:
        raise ValueError(f"no payload model for tipo {tipo!r}")
    validado = modelo.model_validate(payload)
    with conn.cursor() as cur:
        savepoint = not conn.autocommit
        if savepoint:
            cur.execute("SAVEPOINT registrar_evento_sp")
        try:
            cur.execute(
                _INSERT_EVENTO,
                (
                    fazenda_id,
                    tipo.value,
                    origem.value,
                    ocorrido_em,
                    Json(validado.model_dump(mode="json")),
                    ator,
                    corrige_evento_id,
                    chave_idempotencia,
                ),
            )
            row = cur.fetchone()
            assert row is not None
        except UniqueViolation:
            if chave_idempotencia is None:
                raise
            if savepoint:
                cur.execute("ROLLBACK TO SAVEPOINT registrar_evento_sp")
            cur.execute(_SELECT_ID_POR_CHAVE, (fazenda_id, chave_idempotencia))
            found = cur.fetchone()
            if found is None:
                raise
            return cast(UUID, found[0])
        if savepoint:
            cur.execute("RELEASE SAVEPOINT registrar_evento_sp")
        return cast(UUID, row[0])
