"""Acceptance suite for SPEC-019 (daily greedy engine and alert catalog), from KIT-ACEITE-019.

Self-contained: it builds its own projected states and never imports the implementer's tests.
"""

import ast
import inspect
import re
from dataclasses import fields, is_dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import pytest

from seugado.contratos import (
    Alerta,
    EstadoProjetado,
    LoteProjetado,
    PiqueteProjetado,
    PlanoManejo,
    TipoAlerta,
    plano_de_dict,
    plano_para_dict,
)
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
from seugado.planner import alertas as modulo_alertas
from seugado.planner import otimizador
from seugado.planner.alertas import DiaSimulado
from seugado.planner.otimizador import gerar_plano

ROOT = Path(__file__).resolve().parents[2]
PLANNER = ROOT / "src" / "seugado" / "planner"
NS = UUID("00000000-0000-4000-8000-0000000000aa")
SEGUNDA = date(2026, 10, 12)
AGORA = datetime(2026, 10, 12, 6, 0, tzinfo=UTC)
PLANO_ID = UUID("44444444-4444-4444-8444-000000000099")
TODOS_OS_DIAS = (0, 1, 2, 3, 4, 5, 6)


# ---- builders ----------------------------------------------------------------------------


def uid(chave: str) -> UUID:
    return uuid5(NS, chave)


def pq(
    nome: str,
    area_ha: float,
    altura_cm: float,
    descanso: int = 30,
    **kw: Any,
) -> PiqueteProjetado:
    """A rotational Marandu paddock: entry 30, exit 15, 110 kg/ha/cm, efficiency 0.72."""
    centroide = kw.get("centroide", (-9.6, -36.6))
    praca = kw.get("praca")
    modulo = kw.get("modulo")
    return PiqueteProjetado(
        piquete_id=uid(f"piquete:{nome}"),
        nome=nome,
        area_ha=area_ha,
        metodo_pastejo=MetodoPastejo.ROTACIONADO,
        cultivar_slug="marandu",
        cultivar_nome="Marandu",
        centroide_lat=centroide[0],
        centroide_lon=centroide[1],
        situacao=SituacaoPiquete.OCUPADO if kw.get("lote") else SituacaoPiquete.DESCANSANDO,
        lote_atual_id=uid(f"lote:{kw['lote']}") if kw.get("lote") else None,
        dias_descanso=descanso,
        parametros=ParametrosRegime(
            MetodoPastejo.ROTACIONADO, 30.0, 15.0, None, None, Confianca.ALTA, "teste"
        ),
        faltantes=(),
        descanso_min_dias=21.0,
        densidade_kg_ha_por_cm=110.0,
        eficiencia_pastejo=0.72,
        massa_hoje_kg_ms_ha=altura_cm * 110.0,
        altura_hoje_cm=altura_cm,
        taxa_acumulo_prevista_kg_ms_ha_dia=(kw.get("taxa", 50.0),) * 14,
        confianca=Confianca.ALTA,
        motivo_confianca=f"confiança de {nome}",
        dias_desde_imagem_limpa=2,
        modulo_id=uid(f"modulo:{modulo}") if modulo else None,
        praca_id=uid("praca:Q") if praca else None,
        praca_lat=praca[0] if praca else None,
        praca_lon=praca[1] if praca else None,
    )


def lt(
    nome: str, animais: int, consumo: float, em: str | None = None, modulo: str | None = None
) -> LoteProjetado:
    return LoteProjetado(
        lote_id=uid(f"lote:{nome}"),
        nome=nome,
        composicao=(ComposicaoLote(CategoriaAnimal.NOVILHO, animais, 337.5, OrigemPeso.UA_TABELA),),
        indissoluvel=False,
        piquete_atual_id=uid(f"piquete:{em}") if em else None,
        desde=SEGUNDA if em else None,
        peso_vivo_total_kg=animais * 337.5,
        consumo_kg_ms_dia=consumo,
        confianca_peso=Confianca.ALTA,
        motivo_confianca_peso=f"peso de {nome}",
        modulo_id=uid(f"modulo:{modulo}") if modulo else None,
    )


def est(piquetes: list[PiqueteProjetado], lotes: list[LoteProjetado]) -> EstadoProjetado:
    return EstadoProjetado(
        fazenda_id=uid("fazenda"),
        data_base=SEGUNDA,
        horizonte_previsao_dias=14,
        piquetes=tuple(piquetes),
        lotes=tuple(lotes),
    )


def faz(
    dias: tuple[int, ...] = TODOS_OS_DIAS, funcionarios: int = 1, animais: int = 100
) -> Fazenda:
    return Fazenda(
        id=uid("fazenda"),
        nome="Fazenda",
        timezone="America/Maceio",
        funcionarios_disponiveis=funcionarios,
        animais_por_funcionario_dia=animais,
        dias_preferenciais_manejo=dias,
        envio_plano_dia=0,
        envio_plano_hora=6,
    )


def plano(estado: EstadoProjetado, fazenda: Fazenda | None = None) -> PlanoManejo:
    return gerar_plano(estado, fazenda or faz(), AGORA, PLANO_ID)


def do_tipo(p: PlanoManejo, tipo: TipoAlerta) -> list[Alerta]:
    return [a for a in p.alertas if a.tipo is tipo]


def dd_mm(d: date) -> str:
    return f"{d:%d/%m}"


# ---- scenarios of the kit ---------------------------------------------------------------


def canonico() -> EstadoProjetado:
    return est(
        [
            pq("P1", 2.0, 17.0, 0, modulo="M1", lote="L1"),
            pq("P2", 1.0, 33.0, 25, modulo="M1"),
            pq("P3", 1.5, 36.0, 30, modulo="M1"),
            pq("P4", 1.0, 40.0, 10, modulo="M1"),
            pq("P5", 2.0, 45.0, 40, modulo="M2"),
        ],
        [lt("L1", 50, 405.0, em="P1", modulo="M1")],
    )


def oculto_1() -> EstadoProjetado:
    return est(
        [
            pq("A", 1.0, 15.0, 0, taxa=40.0, lote="L1"),
            pq("B", 1.0, 14.0, 0, taxa=40.0, lote="L2"),
            pq("C", 3.0, 35.0, 30, taxa=40.0),
            pq("D", 2.0, 32.0, 30, taxa=40.0),
        ],
        [lt("L1", 40, 400.0, em="A"), lt("L2", 30, 300.0, em="B")],
    )


def oculto_2() -> EstadoProjetado:
    q = (-9.6010, -36.6000)
    return est(
        [
            pq("P1", 1.0, 15.0, 0, taxa=40.0, lote="L", centroide=(-9.6000, -36.6000), praca=q),
            pq("P2", 1.0, 28.0, 30, taxa=40.0, centroide=(-9.6020, -36.6000), praca=q),
            pq("P3", 1.0, 28.0, 30, taxa=40.0, centroide=(-9.6100, -36.6000)),
        ],
        [lt("L", 20, 200.0, em="P1")],
    )


def oculto_3() -> EstadoProjetado:
    return est([pq("P", 1.0, 17.0, 0, taxa=40.0, lote="L")], [lt("L", 40, 400.0, em="P")])


# ---- structural checks ------------------------------------------------------------------


def test_assinatura_de_gerar_plano() -> None:
    sig = inspect.signature(gerar_plano)
    assert list(sig.parameters) == ["estado", "fazenda", "agora", "plano_id"]
    assert sig.return_annotation is PlanoManejo or sig.return_annotation == "PlanoManejo"


def test_tipo_alerta_tem_13_membros_exatos() -> None:
    assert {m.name: m.value for m in TipoAlerta} == {
        "SEM_PIQUETE_APTO": "sem_piquete_apto",
        "CAPACIDADE_EXCEDIDA": "capacidade_excedida",
        "AGUARDANDO_PARAMETRO": "aguardando_parametro",
        "ESTIMATIVA_INDISPONIVEL": "estimativa_indisponivel",
        "CONTINUO_ACIMA_MAXIMA": "continuo_acima_maxima",
        "CONTINUO_ABAIXO_MINIMA": "continuo_abaixo_minima",
        "LOTE_SEM_PIQUETE": "lote_sem_piquete",
        "SEM_DIA_DE_MANEJO": "sem_dia_de_manejo",
        "PASSANDO_DO_PONTO": "passando_do_ponto",
        "ABAIXO_DA_SAIDA": "abaixo_da_saida",
        "PRONTO_EM": "pronto_em",
        "SOBRA_DE_CAPIM": "sobra_de_capim",
        "FALTA_DE_CAPIM": "falta_de_capim",
    }


def test_alerta_termina_em_acao_e_modulo_id_com_defaults() -> None:
    campos = fields(Alerta)
    assert [f.name for f in campos[-2:]] == ["acao", "modulo_id"]
    assert campos[-2].default == "" and campos[-1].default is None
    assert len(campos) == 9


def test_plano_antigo_sem_acao_nem_modulo_id_desserializa() -> None:
    dados = plano_para_dict(plano(canonico()))
    for a in dados["alertas"]:
        a.pop("acao")
        a.pop("modulo_id")
    lido = plano_de_dict(dados)
    assert lido.alertas and all(a.acao == "" and a.modulo_id is None for a in lido.alertas)


def test_dia_simulado_frozen_slots_cinco_campos() -> None:
    assert is_dataclass(DiaSimulado)
    params = DiaSimulado.__dataclass_params__  # type: ignore[attr-defined]
    assert params.frozen is True and hasattr(DiaSimulado, "__slots__")
    assert [f.name for f in fields(DiaSimulado)] == [
        "data",
        "dia_de_manejo",
        "altura_cm",
        "descanso_dias",
        "posicao_lote",
    ]


def _imports(arquivo: Path) -> set[str]:
    nomes: set[str] = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes |= {a.name for a in no.names}
        elif isinstance(no, ast.ImportFrom):
            nomes.add(no.module or "")
            nomes |= {f"{no.module}.{a.name}" for a in no.names}
    return nomes


def test_imports_proibidos_e_sem_ciclo() -> None:
    proibidos = (
        "seugado.api",
        "seugado.persistencia",
        "seugado.delivery",
        "seugado.jobs",
        "seugado.sensing",
        "psycopg",
    )
    for nome in ("alertas.py", "otimizador.py"):
        for imp in _imports(PLANNER / nome):
            assert not imp.startswith(proibidos), (nome, imp)
    assert not any("otimizador" in i for i in _imports(PLANNER / "alertas.py"))


def test_arquivos_curtos_init_vazios_e_sem_mock() -> None:
    for nome in ("alertas.py", "otimizador.py"):
        texto = (PLANNER / nome).read_text(encoding="utf-8")
        assert len(texto.splitlines()) <= 300, nome
        assert "MOCK" not in texto and "demonstração" not in texto, nome
    assert not (ROOT / "tests" / "planner" / "test_otimizador_mock.py").exists()
    for init in (ROOT / "src").rglob("__init__.py"):
        assert init.read_text(encoding="utf-8").strip() == "", init


def test_constantes_calibraveis_marcadas() -> None:
    assert otimizador.HORIZONTE_DIAS == 7
    assert otimizador.FATOR_FALLBACK_ENTRADA == 0.9
    assert modulo_alertas.FATOR_PASSANDO_DO_PONTO == 1.2
    assert modulo_alertas.RAZAO_SOBRA == 1.2
    assert modulo_alertas.RAZAO_FALTA == 0.8
    marcados = (PLANNER / "otimizador.py").read_text(encoding="utf-8").count("HIPOTESE-CALIBRAR")
    marcados += (PLANNER / "alertas.py").read_text(encoding="utf-8").count("HIPOTESE-CALIBRAR")
    assert marcados >= 4


# ---- canonical case ---------------------------------------------------------------------


def test_caso_canonico() -> None:
    p = plano(canonico())
    (mov,) = p.movimentacoes
    assert (mov.lote_nome, mov.piquete_origem_nome, mov.piquete_destino_nome) == ("L1", "P1", "P3")
    assert mov.data == SEGUNDA and mov.dias_previstos == 7
    assert {
        (a.tipo, a.texto.split(" ")[0])
        for a in p.alertas
        if a.tipo is not TipoAlerta.FALTA_DE_CAPIM
    } == {
        (TipoAlerta.PRONTO_EM, "P2"),
        (TipoAlerta.PRONTO_EM, "P5"),
        (TipoAlerta.PASSANDO_DO_PONTO, "P4"),
        (TipoAlerta.PASSANDO_DO_PONTO, "P5"),
    }
    (falta,) = do_tipo(p, TipoAlerta.FALTA_DE_CAPIM)
    assert "49%" in falta.texto and falta.modulo_id == uid("modulo:M1")
    assert len(p.alertas) == 5
    assert all(a.data == SEGUNDA for a in p.alertas)


# ---- hidden case 1: capacity and below-exit ---------------------------------------------


def test_oculto_1_capacidade_e_abaixo_da_saida() -> None:
    p = plano(oculto_1(), faz(animais=60))
    por_lote = {m.lote_nome: m for m in p.movimentacoes}
    assert por_lote["L2"].data == SEGUNDA
    assert (por_lote["L2"].piquete_origem_nome, por_lote["L2"].piquete_destino_nome) == ("B", "C")
    seguinte = SEGUNDA + timedelta(days=1)
    assert por_lote["L1"].data == seguinte
    assert (por_lote["L1"].piquete_origem_nome, por_lote["L1"].piquete_destino_nome) == ("A", "D")
    assert por_lote["L1"].altura_origem_cm == 10.3
    assert por_lote["L1"].altura_destino_cm == 32.4

    (cap,) = do_tipo(p, TipoAlerta.CAPACIDADE_EXCEDIDA)
    assert cap.lote_id == uid("lote:L1") and cap.data == SEGUNDA

    abaixo = {a.texto.split(" ")[0]: a for a in do_tipo(p, TipoAlerta.ABAIXO_DA_SAIDA)}
    assert set(abaixo) == {"A", "B"}
    assert all(a.data == SEGUNDA for a in abaixo.values())
    assert abaixo["A"].acao.startswith("Retirar o lote L1 hoje. Nenhum pasto")
    assert abaixo["B"].acao == "Retirar o lote L2 hoje e levar para o C."

    (falta,) = do_tipo(p, TipoAlerta.FALTA_DE_CAPIM)
    assert "29%" in falta.texto and "pastos sem módulo" in falta.texto and falta.modulo_id is None
    for ausente in (
        TipoAlerta.PRONTO_EM,
        TipoAlerta.PASSANDO_DO_PONTO,
        TipoAlerta.SEM_PIQUETE_APTO,
    ):
        assert do_tipo(p, ausente) == []


# ---- hidden case 2: fallback and distance through the square -----------------------------


def test_oculto_2_fallback_e_distancia_pela_praca() -> None:
    p = plano(oculto_2(), faz(funcionarios=2, animais=100))
    por_data = {m.data: m for m in p.movimentacoes}
    primeira = por_data[SEGUNDA]
    assert (primeira.piquete_origem_nome, primeira.piquete_destino_nome) == ("P1", "P2")
    assert "o mais perto da entrada" in primeira.motivo
    sexta = SEGUNDA + timedelta(days=6)  # 18/10
    assert sexta.day == 18
    assert (por_data[sexta].piquete_origem_nome, por_data[sexta].piquete_destino_nome) == (
        "P2",
        "P3",
    )
    assert len(p.movimentacoes) == 2
    assert do_tipo(p, TipoAlerta.PRONTO_EM) == []
    (falta,) = do_tipo(p, TipoAlerta.FALTA_DE_CAPIM)
    assert "43%" in falta.texto


# ---- hidden case 3: no handling day -------------------------------------------------------


def test_oculto_3_so_quarta_e_dia_de_manejo() -> None:
    p = plano(oculto_3(), faz(dias=(2,)))
    assert p.movimentacoes == ()
    terca = SEGUNDA + timedelta(days=1)
    (sem_dia,) = do_tipo(p, TipoAlerta.SEM_DIA_DE_MANEJO)
    assert sem_dia.lote_id == uid("lote:L") and sem_dia.data == terca
    assert sem_dia.acao == f"Antecipar a troca do lote L para {dd_mm(terca)}."
    (sem_apto,) = do_tipo(p, TipoAlerta.SEM_PIQUETE_APTO)
    assert sem_apto.lote_id == uid("lote:L") and sem_apto.data == SEGUNDA + timedelta(days=2)
    (falta,) = do_tipo(p, TipoAlerta.FALTA_DE_CAPIM)
    assert "7%" in falta.texto


def test_oculto_3_sem_dias_cadastrados() -> None:
    p = plano(oculto_3(), faz(dias=()))
    assert p.movimentacoes == ()
    assert do_tipo(p, TipoAlerta.SEM_PIQUETE_APTO) == []
    sem_dia = do_tipo(p, TipoAlerta.SEM_DIA_DE_MANEJO)
    farm = [a for a in sem_dia if a.lote_id is None]
    do_lote = [a for a in sem_dia if a.lote_id == uid("lote:L")]
    assert len(farm) == 1 and farm[0].piquete_id is None and farm[0].data == SEGUNDA
    assert len(do_lote) == 1 and do_lote[0].data == SEGUNDA + timedelta(days=1)


# ---- properties -------------------------------------------------------------------------


def _cenarios() -> list[tuple[EstadoProjetado, Fazenda]]:
    return [
        (canonico(), faz()),
        (oculto_1(), faz(animais=60)),
        (oculto_2(), faz(funcionarios=2, animais=100)),
        (oculto_3(), faz(dias=(2,))),
        (oculto_3(), faz(dias=())),
        (canonico(), faz(dias=(0, 3))),
    ]


def test_lote_com_modulo_nunca_vai_para_fora_do_modulo() -> None:
    e = est(
        [
            pq("A", 1.0, 15.0, 0, modulo="M1", lote="L"),
            pq("B", 2.0, 40.0, 30, modulo="M2"),
            pq("C", 2.0, 33.0, 30, modulo="M1"),
        ],
        [lt("L", 20, 200.0, em="A", modulo="M1")],
    )
    p = plano(e)
    por_id = {x.piquete_id: x for x in e.piquetes}
    assert p.movimentacoes
    for m in p.movimentacoes:
        assert por_id[m.piquete_destino_id].modulo_id == uid("modulo:M1")


def test_invariantes_em_todos_os_cenarios() -> None:
    for estado, fazenda in _cenarios():
        p = plano(estado, fazenda)
        capacidade = fazenda.funcionarios_disponiveis * fazenda.animais_por_funcionario_dia
        tamanho = {x.lote_id: sum(c.n_animais for c in x.composicao) for x in estado.lotes}
        por_dia: dict[date, list[int]] = {}
        for m in p.movimentacoes:
            assert m.data.weekday() in fazenda.dias_preferenciais_manejo
            por_dia.setdefault(m.data, []).append(tamanho[m.lote_id])
        for tamanhos in por_dia.values():
            assert sum(tamanhos) <= capacidade or len(tamanhos) == 1
        assert all(a.acao != "" for a in p.alertas)
        textos = " ".join(a.texto + a.acao for a in p.alertas) + " ".join(
            m.motivo for m in p.movimentacoes
        )
        assert "MOCK" not in textos and "demonstração" not in textos
        assert not re.search(r"\d+\s+animais", textos)


def test_destino_nunca_ocupado_nem_abaixo_do_fallback() -> None:
    for estado, fazenda in _cenarios():
        p = plano(estado, fazenda)
        por_id = {x.piquete_id: x for x in estado.piquetes}
        for m in p.movimentacoes:
            destino = por_id[m.piquete_destino_id]
            assert m.altura_destino_cm >= 0.9 * m.altura_entrada_alvo_cm - 0.05
            assert destino.parametros is not None and destino.faltantes == ()


def test_determinismo() -> None:
    for estado, fazenda in _cenarios():
        a = plano_para_dict(plano(estado, fazenda))
        b = plano_para_dict(plano(replace(estado), fazenda))
        assert a == b


def test_capacidade_nao_positiva_e_erro() -> None:
    with pytest.raises(ValueError):
        plano(canonico(), faz(funcionarios=0))
    with pytest.raises(ValueError):
        plano(canonico(), faz(animais=0))
