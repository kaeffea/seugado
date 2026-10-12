"""Literal builders of projected states for the engine tests (no database, no weather)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid5

from seugado.contratos import EstadoProjetado, LoteProjetado, PiqueteProjetado
from seugado.core.models import (
    CategoriaAnimal,
    ComposicaoLote,
    Confianca,
    Fazenda,
    MetodoPastejo,
    OrigemPeso,
    ParametrosRegime,
)
from seugado.core.projecao import SituacaoPiquete

NS = UUID("00000000-0000-4000-8000-0000000000ff")
DATA_BASE = date(2026, 10, 12)  # a Monday
AGORA = datetime(2026, 10, 12, 6, 0, tzinfo=UTC)
PLANO_ID = UUID("44444444-4444-4444-8444-000000000019")
DENSIDADE = 110.0
EFICIENCIA = 0.72


def uid(nome: str) -> UUID:
    return uuid5(NS, nome)


def piquete(  # noqa: PLR0913 — a literal builder: one keyword per domain attribute
    nome: str,
    area_ha: float,
    altura_cm: float,
    descanso: int = 30,
    *,
    modulo: str | None = None,
    entrada: float = 30.0,
    saida: float = 15.0,
    taxa: float = 50.0,
    min_descanso: float = 21.0,
    centroide: tuple[float, float] = (-9.6, -36.6),
    praca: tuple[float, float] | None = None,
    lote: str | None = None,
    confianca: Confianca = Confianca.ALTA,
) -> PiqueteProjetado:
    return PiqueteProjetado(
        piquete_id=uid(f"piquete:{nome}"),
        nome=nome,
        area_ha=area_ha,
        metodo_pastejo=MetodoPastejo.ROTACIONADO,
        cultivar_slug="marandu",
        cultivar_nome="Marandu",
        centroide_lat=centroide[0],
        centroide_lon=centroide[1],
        situacao=SituacaoPiquete.DESCANSANDO if lote is None else SituacaoPiquete.OCUPADO,
        lote_atual_id=None if lote is None else uid(f"lote:{lote}"),
        dias_descanso=descanso,
        parametros=ParametrosRegime(
            MetodoPastejo.ROTACIONADO, entrada, saida, None, None, Confianca.ALTA, "teste"
        ),
        faltantes=(),
        descanso_min_dias=min_descanso,
        densidade_kg_ha_por_cm=DENSIDADE,
        eficiencia_pastejo=EFICIENCIA,
        massa_hoje_kg_ms_ha=altura_cm * DENSIDADE,
        altura_hoje_cm=altura_cm,
        taxa_acumulo_prevista_kg_ms_ha_dia=(taxa,) * 14,
        confianca=confianca,
        motivo_confianca=f"confiança de {nome}",
        dias_desde_imagem_limpa=3,
        modulo_id=None if modulo is None else uid(f"modulo:{modulo}"),
        praca_id=None if praca is None else uid(f"praca:{nome}"),
        praca_lat=None if praca is None else praca[0],
        praca_lon=None if praca is None else praca[1],
    )


def lote(
    nome: str,
    animais: int,
    consumo: float,
    *,
    em: str | None = None,
    modulo: str | None = None,
    confianca: Confianca = Confianca.ALTA,
) -> LoteProjetado:
    return LoteProjetado(
        lote_id=uid(f"lote:{nome}"),
        nome=nome,
        composicao=(ComposicaoLote(CategoriaAnimal.NOVILHO, animais, 337.5, OrigemPeso.UA_TABELA),),
        indissoluvel=False,
        piquete_atual_id=None if em is None else uid(f"piquete:{em}"),
        desde=None if em is None else DATA_BASE,
        peso_vivo_total_kg=animais * 337.5,
        consumo_kg_ms_dia=consumo,
        confianca_peso=confianca,
        motivo_confianca_peso=f"peso de {nome}",
        modulo_id=None if modulo is None else uid(f"modulo:{modulo}"),
    )


def estado(
    piquetes: list[PiqueteProjetado], lotes: list[LoteProjetado], data_base: date = DATA_BASE
) -> EstadoProjetado:
    return EstadoProjetado(
        fazenda_id=uid("fazenda"),
        data_base=data_base,
        horizonte_previsao_dias=14,
        piquetes=tuple(piquetes),
        lotes=tuple(lotes),
    )


def fazenda(
    dias: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6), funcionarios: int = 1, animais: int = 100
) -> Fazenda:
    return Fazenda(
        id=uid("fazenda"),
        nome="Fazenda de teste",
        timezone="America/Maceio",
        funcionarios_disponiveis=funcionarios,
        animais_por_funcionario_dia=animais,
        dias_preferenciais_manejo=dias,
        envio_plano_dia=0,
        envio_plano_hora=6,
    )
