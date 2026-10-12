"""Smoke checks of the alert catalog, fed with hand-built simulated days (SPEC-019 R8-R9)."""

import re
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

import pytest

from seugado.contratos import Alerta, Movimentacao, PiqueteProjetado, TipoAlerta
from seugado.core.models import Confianca
from seugado.planner.alertas import (
    RAZAO_FALTA,
    RAZAO_SOBRA,
    DiaSimulado,
    alertas_do_catalogo,
    taxa_do_dia,
)
from tests.planner.construtores import DATA_BASE, estado, lote, piquete, uid


def _dias(
    piquetes: list[PiqueteProjetado],
    posicao: dict[UUID, UUID | None],
    n: int = 7,
    manejo: tuple[bool, ...] = (True,) * 7,
) -> list[DiaSimulado]:
    """`n` days with constant heights and rest growing by 1 per day (nothing is simulated)."""
    return [
        DiaSimulado(
            data=DATA_BASE + timedelta(days=d),
            dia_de_manejo=manejo[d],
            altura_cm={p.piquete_id: float(p.altura_hoje_cm or 0.0) for p in piquetes},
            descanso_dias={p.piquete_id: p.dias_descanso + d for p in piquetes},
            posicao_lote=dict(posicao),
        )
        for d in range(n)
    ]


def _tipos(alertas: Sequence[Alerta]) -> list[TipoAlerta]:
    return [a.tipo for a in alertas]


def test_taxa_do_dia_repete_o_ultimo_valor_alem_da_serie() -> None:
    p = piquete("A", 1.0, 20.0)
    assert taxa_do_dia(p, 0) == 50.0
    assert taxa_do_dia(p, 99) == 50.0


def test_sobra_de_capim_quando_a_oferta_e_20_por_cento_maior() -> None:
    assert RAZAO_SOBRA == 1.2 and RAZAO_FALTA == 0.8
    # offer 100 kg/ha/day * 2 ha * 0.72 = 144; demand 100 -> 144%
    p = piquete("A", 2.0, 20.0, taxa=100.0)
    l1 = lote("L", 10, 100.0, em="A")
    est = estado([p], [l1])
    dias = _dias([p], {l1.lote_id: p.piquete_id})
    (alerta,) = [
        a
        for a in alertas_do_catalogo(est, [p], dias, [])
        if a.tipo in (TipoAlerta.SOBRA_DE_CAPIM, TipoAlerta.FALTA_DE_CAPIM)
    ]
    assert alerta.tipo is TipoAlerta.SOBRA_DE_CAPIM
    assert "144%" in alerta.texto and "pastos sem módulo" in alerta.texto
    assert alerta.piquete_id is None and alerta.lote_id is None and alerta.modulo_id is None
    assert alerta.acao == "Trazer mais animais para o módulo ou tirar piquetes do rodízio."
    assert alerta.data == DATA_BASE


def test_oferta_equilibrada_nao_gera_alerta() -> None:
    p = piquete("A", 2.0, 20.0, taxa=70.0)  # 70*2*0.72 = 100.8 vs 100 -> 101%
    l1 = lote("L", 10, 100.0, em="A")
    dias = _dias([p], {l1.lote_id: p.piquete_id})
    alertas = alertas_do_catalogo(estado([p], [l1]), [p], dias, [])
    assert not {TipoAlerta.SOBRA_DE_CAPIM, TipoAlerta.FALTA_DE_CAPIM} & set(_tipos(alertas))


def test_grupo_sem_lote_ou_sem_consumo_nao_gera_oferta_e_demanda() -> None:
    p = piquete("A", 2.0, 20.0, modulo="M1", taxa=500.0)
    dias = _dias([p], {})
    assert alertas_do_catalogo(estado([p], []), [p], dias, []) == ()
    parado = lote("L", 10, 0.0, em="A", modulo="M1")
    dias = _dias([p], {parado.lote_id: p.piquete_id})
    sobra = {TipoAlerta.SOBRA_DE_CAPIM, TipoAlerta.FALTA_DE_CAPIM}
    assert not sobra & set(_tipos(alertas_do_catalogo(estado([p], [parado]), [p], dias, [])))


def test_abaixo_da_saida_so_no_dia_zero_e_com_acao_do_movimento() -> None:
    a = piquete("A", 1.0, 14.0, 0, lote="L")
    b = piquete("B", 1.0, 35.0, 30)
    l1 = lote("L", 10, 100.0, em="A")
    est = estado([a, b], [l1])
    dias = _dias([a, b], {l1.lote_id: a.piquete_id})
    sem_mov = [
        x for x in alertas_do_catalogo(est, [a, b], dias, []) if x.tipo.value == "abaixo_da_saida"
    ]
    assert len(sem_mov) == 1  # one per paddock, never repeated on later days
    assert sem_mov[0].data == DATA_BASE and sem_mov[0].lote_id == l1.lote_id
    assert sem_mov[0].acao.startswith("Retirar o lote L hoje. Nenhum pasto do módulo")

    mov = Movimentacao(
        id=uid("m"), data=DATA_BASE, lote_id=l1.lote_id, lote_nome="L",
        piquete_origem_id=a.piquete_id, piquete_origem_nome="A",
        piquete_destino_id=b.piquete_id, piquete_destino_nome="B",
        altura_destino_cm=35.0, altura_entrada_alvo_cm=30.0, altura_origem_cm=14.0,
        altura_saida_alvo_cm=15.0, dias_previstos=3, motivo="m",
        confianca=Confianca.ALTA, motivo_confianca="c",
    )  # fmt: skip
    com_mov = [
        x
        for x in alertas_do_catalogo(est, [a, b], dias, [mov])
        if x.tipo.value == "abaixo_da_saida"
    ]
    assert com_mov[0].acao == "Retirar o lote L hoje e levar para o B."


def test_sem_dia_de_manejo_leva_a_data_do_dia_que_cruza() -> None:
    a = piquete("A", 1.0, 40.0, 0, lote="L")
    l1 = lote("L", 10, 100.0, em="A")
    dias = _dias([a], {l1.lote_id: a.piquete_id}, manejo=(False,) * 7)
    dias[2] = DiaSimulado(
        data=dias[2].data,
        dia_de_manejo=False,
        altura_cm={a.piquete_id: 14.0},
        descanso_dias=dict(dias[2].descanso_dias),
        posicao_lote=dict(dias[2].posicao_lote),
    )
    (alerta,) = [
        x
        for x in alertas_do_catalogo(estado([a], [l1]), [a], dias, [])
        if x.tipo is TipoAlerta.SEM_DIA_DE_MANEJO
    ]
    assert alerta.data == DATA_BASE + timedelta(days=2)
    assert alerta.acao == "Antecipar a troca do lote L para 14/10."
    assert alerta.lote_id == l1.lote_id and alerta.piquete_id == a.piquete_id


def test_pronto_em_so_o_primeiro_de_cada_grupo_e_desempate_por_nome() -> None:
    a = piquete("A", 1.0, 35.0, 30, modulo="M1")
    b = piquete("B", 1.0, 35.0, 30, modulo="M1")
    c = piquete("C", 1.0, 35.0, 30, modulo="M2")
    dias = _dias([a, b, c], {})
    prontos = [
        x
        for x in alertas_do_catalogo(estado([a, b, c], []), [a, b, c], dias, [])
        if x.tipo is TipoAlerta.PRONTO_EM
    ]
    assert sorted(x.texto.split(" ")[0] for x in prontos) == ["A", "C"]


def test_passando_do_ponto_exclui_destino_do_plano() -> None:
    a = piquete("A", 1.0, 40.0, 30)  # 40 >= 1.2 * 30
    dias = _dias([a], {})
    est = estado([a], [])
    assert TipoAlerta.PASSANDO_DO_PONTO in _tipos(alertas_do_catalogo(est, [a], dias, []))
    mov = Movimentacao(
        id=uid("m"), data=DATA_BASE, lote_id=uid("lote:x"), lote_nome="x",
        piquete_origem_id=None, piquete_origem_nome=None,
        piquete_destino_id=a.piquete_id, piquete_destino_nome="A",
        altura_destino_cm=40.0, altura_entrada_alvo_cm=30.0, altura_origem_cm=None,
        altura_saida_alvo_cm=None, dias_previstos=3, motivo="m",
        confianca=Confianca.ALTA, motivo_confianca="c",
    )  # fmt: skip
    depois = alertas_do_catalogo(est, [a], dias, [mov])
    assert not {TipoAlerta.PASSANDO_DO_PONTO, TipoAlerta.PRONTO_EM} & set(_tipos(depois))


def test_sem_dias_simulados_nao_gera_alertas() -> None:
    assert alertas_do_catalogo(estado([], []), [], [], []) == ()


@pytest.mark.parametrize("taxa", [40.0, 120.0])
def test_nenhum_texto_diz_numero_de_animais(taxa: float) -> None:
    p = piquete("A", 2.0, 20.0, taxa=taxa)
    l1 = lote("L", 10, 100.0, em="A")
    dias = _dias([p], {l1.lote_id: p.piquete_id})
    alertas = alertas_do_catalogo(estado([p], [l1]), [p], dias, [])
    assert alertas
    for a in alertas:
        assert not re.search(r"\d+\s+animais", a.texto + a.acao)
