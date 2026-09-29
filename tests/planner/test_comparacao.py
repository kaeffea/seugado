"""J4b: comparar_planos is pure and reports only unanswered, upcoming changes per lote."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from seugado.contratos import DiferencaLote, Movimentacao, PassoPlano, PlanoManejo, plano_de_dict
from seugado.planner.comparacao import comparar_planos

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "plano_exemplo.json"
HOJE = date(2026, 9, 28)  # Monday, the fixture's first day
QUINTA = date(2026, 10, 1)


def _base() -> PlanoManejo:
    return plano_de_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def _recria(plano: PlanoManejo) -> Movimentacao:
    return next(m for m in plano.movimentacoes if m.lote_nome == "Recria")


def _com_recria_na_quinta(plano: PlanoManejo, destino: str) -> PlanoManejo:
    """A copy of the plan (new ids) where Recria also moves on Thursday to `destino`."""
    extra = replace(
        _recria(plano),
        id=uuid4(),
        data=QUINTA,
        piquete_destino_id=uuid4(),
        piquete_destino_nome=destino,
    )
    movs = tuple(replace(m, id=uuid4()) for m in plano.movimentacoes) + (extra,)
    return replace(
        plano, id=uuid4(), movimentacoes=tuple(sorted(movs, key=lambda m: (m.data, m.lote_nome)))
    )


def test_planos_iguais_devolvem_vazio() -> None:
    plano = _base()
    assert comparar_planos(plano, plano, frozenset(), HOJE) == ()
    # A regenerated plan with the same steps but new movement ids is also "no change".
    igual = replace(
        plano, id=uuid4(), movimentacoes=tuple(replace(m, id=uuid4()) for m in plano.movimentacoes)
    )
    assert comparar_planos(plano, igual, frozenset(), HOJE) == ()


def test_mudanca_so_em_movimentacao_respondida_devolve_vazio() -> None:
    anterior = _com_recria_na_quinta(_base(), "Piquete 4")
    segunda_recria = next(
        m for m in anterior.movimentacoes if m.lote_nome == "Recria" and m.data == HOJE
    )
    # The producer already answered Monday's Recria move; the new plan no longer carries it.
    novo = replace(
        anterior,
        id=uuid4(),
        movimentacoes=tuple(m for m in anterior.movimentacoes if m.id != segunda_recria.id),
    )
    assert comparar_planos(anterior, novo, frozenset({segunda_recria.id}), HOJE) == ()


def test_destino_diferente_na_quinta_para_recria() -> None:
    base = _base()
    anterior = _com_recria_na_quinta(base, "Piquete 4")
    novo = _com_recria_na_quinta(base, "Piquete 3")
    difs = comparar_planos(anterior, novo, frozenset(), HOJE)

    recria = _recria(base)
    assert difs == (
        DiferencaLote(
            lote_id=recria.lote_id,
            lote_nome="Recria",
            antes=(PassoPlano(HOJE, "Piquete 6"), PassoPlano(QUINTA, "Piquete 4")),
            depois=(PassoPlano(HOJE, "Piquete 6"), PassoPlano(QUINTA, "Piquete 3")),
        ),
    )


def test_passado_nao_conta_e_resultado_por_nome_de_lote() -> None:
    base = _base()
    anterior = _com_recria_na_quinta(base, "Piquete 4")
    novo = _com_recria_na_quinta(base, "Piquete 3")
    # After Thursday nothing is upcoming any more, so nothing differs.
    assert comparar_planos(anterior, novo, frozenset(), date(2026, 10, 2)) == ()

    # Both lotes changing come back sorted by lote_nome.
    vacas: UUID = next(m.lote_id for m in base.movimentacoes if m.lote_nome == "Vacas com bezerro")
    novo2 = replace(
        novo,
        movimentacoes=tuple(
            replace(m, piquete_destino_nome="Piquete 8") if m.lote_id == vacas else m
            for m in novo.movimentacoes
        ),
    )
    nomes = [d.lote_nome for d in comparar_planos(anterior, novo2, frozenset(), HOJE)]
    assert nomes == ["Recria", "Vacas com bezerro"]
