"""What changed between the plan in force and a new one, lote by lote (J4b)."""

from datetime import date
from uuid import UUID

from seugado.contratos import DiferencaLote, PassoPlano, PlanoManejo


def _passos(
    plano: PlanoManejo, lote_id: UUID, hoje: date, ignorar: frozenset[UUID]
) -> tuple[PassoPlano, ...]:
    movs = sorted(
        (
            m
            for m in plano.movimentacoes
            if m.lote_id == lote_id and m.data >= hoje and m.id not in ignorar
        ),
        key=lambda m: m.data,
    )
    return tuple(PassoPlano(m.data, m.piquete_destino_nome) for m in movs)


def comparar_planos(
    anterior: PlanoManejo,
    novo: PlanoManejo,
    respondidas: frozenset[UUID],
    hoje: date,
) -> tuple[DiferencaLote, ...]:
    """Lotes whose upcoming, still unanswered steps differ; empty means nothing relevant changed.

    Pure function: `antes` skips movements already answered, `depois` keeps all of them.
    """
    nomes: dict[UUID, str] = {}
    for plano in (anterior, novo):
        for m in plano.movimentacoes:
            nomes.setdefault(m.lote_id, m.lote_nome)

    diferencas: list[DiferencaLote] = []
    for lote_id, lote_nome in nomes.items():
        antes = _passos(anterior, lote_id, hoje, respondidas)
        depois = _passos(novo, lote_id, hoje, frozenset())
        if antes != depois:
            diferencas.append(DiferencaLote(lote_id, lote_nome, antes, depois))
    return tuple(sorted(diferencas, key=lambda d: d.lote_nome))
