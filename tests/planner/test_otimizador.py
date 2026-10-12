"""Smoke checks of the daily greedy engine (SPEC-019)."""

from dataclasses import replace
from datetime import timedelta

import pytest

from seugado.contratos import (
    EstadoProjetado,
    PlanoManejo,
    TipoAlerta,
    plano_de_dict,
    plano_para_dict,
)
from seugado.core.models import Confianca, Fazenda
from seugado.planner.otimizador import gerar_plano
from tests.planner.construtores import (
    AGORA,
    DATA_BASE,
    PLANO_ID,
    estado,
    fazenda,
    lote,
    piquete,
    uid,
)


def _plano(est: EstadoProjetado, faz: Fazenda | None = None) -> PlanoManejo:
    return gerar_plano(est, faz or fazenda(), AGORA, PLANO_ID)


def _exemplo_da_spec() -> EstadoProjetado:
    return estado(
        [
            piquete("P1", 2.0, 17.0, 0, modulo="M1", lote="L1"),
            piquete("P2", 1.0, 33.0, 25, modulo="M1"),
            piquete("P3", 1.5, 36.0, 30, modulo="M1"),
            piquete("P4", 1.0, 40.0, 10, modulo="M1"),
            piquete("P5", 2.0, 45.0, 40, modulo="M2"),
        ],
        [lote("L1", 50, 405.0, em="P1", modulo="M1")],
    )


def test_exemplo_trabalhado_da_spec() -> None:
    plano = _plano(_exemplo_da_spec())
    (mov,) = plano.movimentacoes
    assert (mov.lote_nome, mov.piquete_origem_nome, mov.piquete_destino_nome) == ("L1", "P1", "P3")
    assert mov.data == DATA_BASE
    assert mov.dias_previstos == 7
    assert (mov.altura_origem_cm, mov.altura_destino_cm) == (17.0, 36.0)
    assert mov.motivo == (
        "P1 chega à altura de saída (15 cm). P3 está com 36 cm, acima da entrada (30 cm)."
    )
    alertas = {(a.tipo, a.texto.split(" ")[0]) for a in plano.alertas}
    assert {a.tipo for a in plano.alertas} == {
        TipoAlerta.PRONTO_EM,
        TipoAlerta.PASSANDO_DO_PONTO,
        TipoAlerta.FALTA_DE_CAPIM,
    }
    assert (TipoAlerta.PRONTO_EM, "P2") in alertas
    assert (TipoAlerta.PRONTO_EM, "P5") in alertas
    assert (TipoAlerta.PASSANDO_DO_PONTO, "P4") in alertas
    assert (TipoAlerta.PASSANDO_DO_PONTO, "P5") in alertas
    (falta,) = [a for a in plano.alertas if a.tipo is TipoAlerta.FALTA_DE_CAPIM]
    assert "49%" in falta.texto
    assert falta.modulo_id == uid("modulo:M1")


def test_todo_alerta_tem_acao_e_nenhum_texto_de_mock() -> None:
    plano = _plano(_exemplo_da_spec())
    for a in plano.alertas:
        assert a.acao
    textos = [a.texto + a.acao for a in plano.alertas] + [m.motivo for m in plano.movimentacoes]
    assert not any("MOCK" in t or "demonstração" in t for t in textos)


def test_determinismo_e_roundtrip_json() -> None:
    est = _exemplo_da_spec()
    a, b = _plano(est), _plano(replace(est))
    assert plano_para_dict(a) == plano_para_dict(b)
    assert plano_de_dict(plano_para_dict(a)) == a


def test_lote_com_modulo_nunca_sai_do_modulo() -> None:
    est = estado(
        [
            piquete("A", 1.0, 15.0, 0, modulo="M1", lote="L"),
            piquete("B", 1.0, 40.0, 30, modulo="M2"),  # taller, but another module
        ],
        [lote("L", 20, 200.0, em="A", modulo="M1")],
    )
    plano = _plano(est)
    assert plano.movimentacoes == ()
    assert any(a.tipo is TipoAlerta.SEM_PIQUETE_APTO for a in plano.alertas)


def test_so_move_em_dia_de_manejo() -> None:
    est = _exemplo_da_spec()
    # Only Wednesday (weekday 2); the herd must leave on Monday but waits.
    plano = _plano(est, fazenda(dias=(2,)))
    assert all(m.data.weekday() == 2 for m in plano.movimentacoes)
    assert not any(m.data < DATA_BASE + timedelta(days=2) for m in plano.movimentacoes)


def test_sem_dia_de_manejo_cadastrado() -> None:
    plano = _plano(_exemplo_da_spec(), fazenda(dias=()))
    assert plano.movimentacoes == ()
    fazenda_nivel = [a for a in plano.alertas if a.tipo is TipoAlerta.SEM_DIA_DE_MANEJO]
    assert any(a.lote_id is None and a.piquete_id is None for a in fazenda_nivel)
    assert not any(a.tipo is TipoAlerta.SEM_PIQUETE_APTO for a in plano.alertas)


def test_capacidade_nao_positiva_e_erro() -> None:
    with pytest.raises(ValueError):
        _plano(_exemplo_da_spec(), fazenda(funcionarios=0))
    with pytest.raises(ValueError):
        _plano(_exemplo_da_spec(), fazenda(animais=0))


def test_lote_maior_que_a_equipe_vai_sozinho() -> None:
    est = estado(
        [piquete("A", 1.0, 15.0, 0, lote="G"), piquete("B", 3.0, 40.0, 30)],
        [lote("G", 200, 800.0, em="A")],
    )
    plano = _plano(est, fazenda(animais=50))
    (mov,) = plano.movimentacoes
    assert mov.lote_nome == "G"
    assert not any(a.tipo is TipoAlerta.CAPACIDADE_EXCEDIDA for a in plano.alertas)


def test_lote_sem_piquete_e_colocado_primeiro() -> None:
    est = estado(
        [
            piquete("A", 2.0, 15.0, 0, lote="V"),
            piquete("B", 2.0, 40.0, 30),
            piquete("C", 2.0, 38.0),
        ],
        [lote("V", 10, 100.0, em="A"), lote("Z", 10, 100.0, em=None)],
    )
    por_lote = {m.lote_nome: m for m in _plano(est).movimentacoes}
    sem_pasto = por_lote["Z"]
    assert sem_pasto.data == DATA_BASE
    assert sem_pasto.piquete_origem_id is None and sem_pasto.altura_origem_cm is None
    assert sem_pasto.motivo.startswith("Z está sem pasto registrado.")
    assert sem_pasto.piquete_destino_nome == "B"  # unplaced goes first: tallest above entry
    assert por_lote["V"].piquete_destino_nome == "C"


def test_confianca_e_a_mais_fraca_dos_fatores() -> None:
    est = estado(
        [
            piquete("A", 1.0, 15.0, 0, lote="L", confianca=Confianca.ALTA),
            piquete("B", 3.0, 40.0, 30, confianca=Confianca.MEDIA),
        ],
        [lote("L", 20, 200.0, em="A", confianca=Confianca.BAIXA)],
    )
    (mov,) = _plano(est).movimentacoes
    assert mov.confianca is Confianca.BAIXA
    assert mov.motivo_confianca == "peso de L"


def test_piquete_nao_plannable_e_ignorado() -> None:
    sem_parametros = replace(piquete("X", 2.0, 40.0, 40), parametros=None)
    est = estado(
        [piquete("A", 1.0, 15.0, 0, lote="L"), sem_parametros],
        [lote("L", 20, 200.0, em="A")],
    )
    plano = _plano(est)
    assert plano.movimentacoes == ()  # X is not a destination
    assert [r.nome for r in plano.piquetes] == ["A", "X"]


def test_nenhum_destino_fora_da_regra() -> None:
    plano = _plano(_exemplo_da_spec())
    est = _exemplo_da_spec()
    por_id = {p.piquete_id: p for p in est.piquetes}
    for m in plano.movimentacoes:
        destino = por_id[m.piquete_destino_id]
        assert destino.lote_atual_id is None
        assert m.altura_destino_cm >= 0.9 * m.altura_entrada_alvo_cm
