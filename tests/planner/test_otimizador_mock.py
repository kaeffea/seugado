"""The MOCK optimizer honours the PlanoManejo contract (it is not the J3 algorithm)."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from seugado.contratos import (
    EstadoProjetado,
    TipoAlerta,
    estado_de_dict,
    plano_de_dict,
    plano_para_dict,
)
from seugado.core.models import Confianca, Fazenda
from seugado.planner.otimizador import DIAS_PREVISTOS_MOCK, gerar_plano

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "estado_projetado_exemplo.json"
PLANO_ID = UUID("44444444-4444-4444-8444-000000000001")
AGORA = datetime(2026, 9, 28, 8, 0, tzinfo=UTC)


def _estado() -> EstadoProjetado:
    return estado_de_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def _fazenda(estado: EstadoProjetado, dias: tuple[int, ...] = (1, 3)) -> Fazenda:
    return Fazenda(
        id=estado.fazenda_id,
        nome="Fazenda Exemplo",
        timezone="America/Fortaleza",
        funcionarios_disponiveis=2,
        animais_por_funcionario_dia=50,
        dias_preferenciais_manejo=dias,
        envio_plano_dia=0,
        envio_plano_hora=6,
    )


def test_plano_mock_da_fixture_e_valido() -> None:
    estado = _estado()
    fazenda = _fazenda(estado)
    plano = gerar_plano(estado, fazenda, AGORA, PLANO_ID)

    assert plano_de_dict(plano_para_dict(plano)) == plano
    assert plano.data_inicio == estado.data_base
    assert plano.horizonte_dias == 7
    assert [r.nome for r in plano.piquetes] == sorted(p.nome for p in estado.piquetes)

    assert plano.movimentacoes, "the fixture has free, plannable piquetes"
    for m in plano.movimentacoes:
        assert m.data.weekday() in fazenda.dias_preferenciais_manejo
        assert m.confianca == Confianca.BAIXA
        assert m.dias_previstos == DIAS_PREVISTOS_MOCK
    destinos = [m.piquete_destino_id for m in plano.movimentacoes]
    assert len(destinos) == len(set(destinos))
    assert [m.lote_nome for m in plano.movimentacoes] == sorted(
        m.lote_nome for m in plano.movimentacoes
    )
    # Tallest free piquetes first, lotes by name: Recria → Piquete 6, Vacas → Piquete 1.
    assert [(m.lote_nome, m.piquete_destino_nome) for m in plano.movimentacoes] == [
        ("Recria", "Piquete 6"),
        ("Vacas com bezerro", "Piquete 1"),
    ]


def test_sem_dia_de_manejo_gera_alerta_e_nenhuma_movimentacao() -> None:
    estado = _estado()
    plano = gerar_plano(estado, _fazenda(estado, dias=()), AGORA, PLANO_ID)
    assert plano.movimentacoes == ()
    assert [a.tipo for a in plano.alertas] == [TipoAlerta.SEM_DIA_DE_MANEJO]


def test_mesmo_plano_id_gera_mesmos_ids_de_movimentacao() -> None:
    estado = _estado()
    a = gerar_plano(estado, _fazenda(estado), AGORA, PLANO_ID)
    b = gerar_plano(replace(estado), _fazenda(estado), AGORA, PLANO_ID)
    assert [m.id for m in a.movimentacoes] == [m.id for m in b.movimentacoes]
