"""Cross-module contracts and their JSON form."""

import types
import typing
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import Enum, StrEnum
from typing import Any, cast, get_args, get_origin, get_type_hints
from uuid import UUID

from seugado.core.models import (
    CategoriaAnimal,
    ComposicaoLote,
    Confianca,
    MetodoPastejo,
    OrigemPeso,
    ParametrosRegime,
)
from seugado.core.projecao import SituacaoPiquete


class TipoAlerta(StrEnum):
    SEM_PIQUETE_APTO = "sem_piquete_apto"
    CAPACIDADE_EXCEDIDA = "capacidade_excedida"
    AGUARDANDO_PARAMETRO = "aguardando_parametro"
    ESTIMATIVA_INDISPONIVEL = "estimativa_indisponivel"
    CONTINUO_ACIMA_MAXIMA = "continuo_acima_maxima"
    CONTINUO_ABAIXO_MINIMA = "continuo_abaixo_minima"
    LOTE_SEM_PIQUETE = "lote_sem_piquete"
    SEM_DIA_DE_MANEJO = "sem_dia_de_manejo"


@dataclass(frozen=True, slots=True)
class PiqueteProjetado:
    piquete_id: UUID
    nome: str
    area_ha: float
    metodo_pastejo: MetodoPastejo
    cultivar_slug: str
    cultivar_nome: str
    centroide_lat: float
    centroide_lon: float
    situacao: SituacaoPiquete
    lote_atual_id: UUID | None
    dias_descanso: int
    parametros: ParametrosRegime | None
    faltantes: tuple[str, ...]
    descanso_min_dias: float
    densidade_kg_ha_por_cm: float | None
    eficiencia_pastejo: float | None
    massa_hoje_kg_ms_ha: float | None
    altura_hoje_cm: float | None
    taxa_acumulo_prevista_kg_ms_ha_dia: tuple[float, ...]
    confianca: Confianca
    motivo_confianca: str
    dias_desde_imagem_limpa: int | None


@dataclass(frozen=True, slots=True)
class LoteProjetado:
    lote_id: UUID
    nome: str
    composicao: tuple[ComposicaoLote, ...]
    indissoluvel: bool
    piquete_atual_id: UUID | None
    desde: date | None
    peso_vivo_total_kg: float
    consumo_kg_ms_dia: float
    confianca_peso: Confianca
    motivo_confianca_peso: str


@dataclass(frozen=True, slots=True)
class EstadoProjetado:
    fazenda_id: UUID
    data_base: date
    horizonte_previsao_dias: int
    piquetes: tuple[PiqueteProjetado, ...]
    lotes: tuple[LoteProjetado, ...]


@dataclass(frozen=True, slots=True)
class Movimentacao:
    id: UUID
    data: date
    lote_id: UUID
    lote_nome: str
    piquete_origem_id: UUID | None
    piquete_origem_nome: str | None
    piquete_destino_id: UUID
    piquete_destino_nome: str
    altura_destino_cm: float
    altura_entrada_alvo_cm: float
    altura_origem_cm: float | None
    altura_saida_alvo_cm: float | None
    dias_previstos: int
    motivo: str
    confianca: Confianca
    motivo_confianca: str


@dataclass(frozen=True, slots=True)
class Alerta:
    tipo: TipoAlerta
    data: date
    texto: str
    confianca: Confianca
    motivo_confianca: str
    piquete_id: UUID | None
    lote_id: UUID | None


@dataclass(frozen=True, slots=True)
class PedidoValidacao:
    piquete_id: UUID
    piquete_nome: str
    motivo: str


@dataclass(frozen=True, slots=True)
class ResumoPiquete:
    piquete_id: UUID
    nome: str
    situacao: SituacaoPiquete
    lote_atual_nome: str | None
    altura_hoje_cm: float | None
    altura_entrada_alvo_cm: float | None
    altura_saida_alvo_cm: float | None
    confianca: Confianca
    motivo_confianca: str
    faltantes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanoManejo:
    id: UUID
    fazenda_id: UUID
    data_geracao: datetime
    data_inicio: date
    horizonte_dias: int
    movimentacoes: tuple[Movimentacao, ...]
    alertas: tuple[Alerta, ...]
    pedidos_validacao: tuple[PedidoValidacao, ...]
    piquetes: tuple[ResumoPiquete, ...]


def _serialize(obj: object) -> object:
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _serialize(getattr(obj, f.name)) for f in fields(obj)}
    raise TypeError(f"cannot serialize {type(obj)}")


def _uuid(v: object) -> UUID:
    try:
        return v if isinstance(v, UUID) else UUID(str(v))
    except (ValueError, TypeError, AttributeError) as e:
        raise ValueError(f"invalid UUID: {v!r}") from e


def _date(v: object) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    try:
        return date.fromisoformat(str(v))
    except (ValueError, TypeError) as e:
        raise ValueError(f"invalid date: {v!r}") from e


def _dt(v: object) -> datetime:
    try:
        dt = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
    except (ValueError, TypeError) as e:
        raise ValueError(f"invalid datetime: {v!r}") from e
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"naive datetime: {v!r}")
    return dt


def _enum[E: StrEnum](cls: type[E], v: object) -> E:
    try:
        return cls(str(v))
    except (ValueError, TypeError) as e:
        raise ValueError(f"unknown {cls.__name__}: {v!r}") from e


_KNOWN_ENUMS: tuple[type[StrEnum], ...] = (
    TipoAlerta,
    MetodoPastejo,
    SituacaoPiquete,
    Confianca,
    CategoriaAnimal,
    OrigemPeso,
)


def _parse_primitive(t: object, v: object) -> object:
    if t is UUID:
        return _uuid(v)
    if t is date:
        return _date(v)
    if t is datetime:
        return _dt(v)
    if isinstance(t, type) and issubclass(t, StrEnum):
        return _enum(t, v)
    return v


def _missing(name: str) -> typing.NoReturn:
    raise ValueError(f"missing key: '{name}'")


def _deserialize(t: object, v: object) -> object:
    origin = get_origin(t)
    if origin in (types.UnionType, typing.Union):
        args = get_args(t)
        if v is None:
            if type(None) in args:
                return None
            raise ValueError(f"expected {t}, got None")
        return _deserialize(next(a for a in args if a is not type(None)), v)
    if v is None:
        return None
    if origin is tuple:
        args = get_args(t)
        elem_t = args[0] if args else object
        if not isinstance(v, (list, tuple)):
            raise ValueError(f"expected tuple, got {type(v)}")
        return tuple(_deserialize(elem_t, x) for x in v)
    if is_dataclass(t) and isinstance(t, type):
        if not isinstance(v, Mapping):
            raise ValueError(f"expected mapping for {t}, got {type(v)}")
        hints = get_type_hints(t)
        return t(
            **{
                f.name: _deserialize(hints[f.name], v[f.name])
                for f in fields(t)
                if f.name in v or _missing(f.name)
            }
        )
    return _parse_primitive(t, v)


def estado_para_dict(estado: EstadoProjetado) -> dict[str, Any]:
    return cast("dict[str, Any]", _serialize(estado))


def estado_de_dict(dados: Mapping[str, Any]) -> EstadoProjetado:
    return cast("EstadoProjetado", _deserialize(EstadoProjetado, dados))


def plano_para_dict(plano: PlanoManejo) -> dict[str, Any]:
    return cast("dict[str, Any]", _serialize(plano))


def plano_de_dict(dados: Mapping[str, Any]) -> PlanoManejo:
    return cast("PlanoManejo", _deserialize(PlanoManejo, dados))
