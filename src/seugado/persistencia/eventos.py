"""Validated write gateway for the append-only event log."""

from datetime import date, datetime
from typing import Any, Literal, cast
from uuid import UUID

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.types.json import Json
from pydantic import BaseModel, ConfigDict, Field

from seugado.core.models import OrigemEvento, TipoEvento


class _PayloadBase(BaseModel):
    """Shared config: payloads carry exactly their declared fields."""

    model_config = ConfigDict(extra="forbid")


class ComposicaoPayload(_PayloadBase):
    """One category group within a lote payload."""

    categoria: Literal["bezerro", "novilho", "adulto"]
    n_animais: int = Field(gt=0)
    peso_medio_kg: float = Field(gt=0)


class PayloadPiqueteCriado(_PayloadBase):
    entidade_id: UUID
    nome: str
    area_ha: float = Field(gt=0)
    cultivar_id: UUID
    metodo_pastejo: Literal["continuo", "rotacionado"]
    ativo: bool


class PayloadPiqueteAlterado(_PayloadBase):
    entidade_id: UUID
    nome: str
    area_ha: float = Field(gt=0)
    cultivar_id: UUID
    metodo_pastejo: Literal["continuo", "rotacionado"]
    ativo: bool


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
    piquete_real_id: UUID
    data_execucao: date
    observacao: str | None


class PayloadLeituraSatelite(_PayloadBase):
    entidade_id: UUID
    piquete_id: UUID
    data: date
    ndvi: float
    origem_ndvi: str
    pct_nuvem: float = Field(ge=0, le=100)
    pixels_validos: int = Field(gt=0)
    massa_kg_ms_ha: float = Field(gt=0)
    taxa_acumulo_kg_ms_ha_dia: float
    confianca: Literal["alta", "media", "baixa"]


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
