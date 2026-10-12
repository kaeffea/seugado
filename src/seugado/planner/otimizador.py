"""Daily greedy engine (SPEC-019): simulates 7 days one at a time, herds stay in their module.

Deterministic and pure. Every alert is built in `alertas.py`.
"""

import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID, uuid5

from seugado.contratos import (
    Alerta,
    EstadoProjetado,
    LoteProjetado,
    Movimentacao,
    PiqueteProjetado,
    PlanoManejo,
    ResumoPiquete,
    TipoAlerta,
)
from seugado.core import forragem
from seugado.core.models import Confianca, Fazenda, MetodoPastejo
from seugado.core.regras import combinar_confianca
from seugado.planner import alertas as catalogo
from seugado.planner.estado import avancar_massa_um_dia
from seugado.planner.estrutura import distancia_manejo_m, piquetes_candidatos

HORIZONTE_DIAS = 7
_entrada, _saida, _taxa = (
    catalogo.altura_entrada_cm,
    catalogo.altura_saida_cm,
    catalogo.taxa_do_dia,
)
# HIPOTESE-CALIBRAR: fraction of the entry height accepted when no paddock reaches the entry
# height. Fix it in the threshold calibration ADR.
FATOR_FALLBACK_ENTRADA = 0.9


def _plannable(p: PiqueteProjetado) -> bool:
    prm = p.parametros
    campos = (p.massa_hoje_kg_ms_ha, p.densidade_kg_ha_por_cm, p.eficiencia_pastejo)
    return (
        p.metodo_pastejo == MetodoPastejo.ROTACIONADO
        and p.faltantes == ()
        and prm is not None
        and None not in (prm.altura_entrada_cm, prm.altura_saida_cm, *campos)
        and len(p.taxa_acumulo_prevista_kg_ms_ha_dia) > 0
    )


def _resumos(estado: EstadoProjetado) -> tuple[ResumoPiquete, ...]:
    nome_lote = {lote.lote_id: lote.nome for lote in estado.lotes}
    return tuple(
        ResumoPiquete(
            piquete_id=p.piquete_id,
            nome=p.nome,
            situacao=p.situacao,
            lote_atual_nome=None if p.lote_atual_id is None else nome_lote.get(p.lote_atual_id),
            altura_hoje_cm=p.altura_hoje_cm,
            altura_entrada_alvo_cm=None if p.parametros is None else p.parametros.altura_entrada_cm,
            altura_saida_alvo_cm=None if p.parametros is None else p.parametros.altura_saida_cm,
            confianca=p.confianca,
            motivo_confianca=p.motivo_confianca,
            faltantes=p.faltantes,
        )
        for p in sorted(estado.piquetes, key=lambda p: p.nome)
    )


def _deve_sair(
    p: PiqueteProjetado, massa_kg_ms_ha: float, consumo_kg_ms_dia: float, d: int, k: int
) -> bool:
    """Height <= exit height on any of the days d..d+k, keeping today's occupants."""
    massa = massa_kg_ms_ha
    for j in range(k + 1):
        if massa / cast("float", p.densidade_kg_ha_por_cm) <= _saida(p):
            return True
        massa = avancar_massa_um_dia(
            massa, _taxa(p, d + j), consumo_kg_ms_dia, p.area_ha, p.eficiencia_pastejo
        )
    return False


def _escolher(
    candidatos: Sequence[PiqueteProjetado],
    origem: PiqueteProjetado | None,
    altura_cm: Mapping[UUID, float],
    descanso: Mapping[UUID, int],
) -> tuple[PiqueteProjetado, bool] | None:
    """Best apt candidate, else the best one within the fallback height: (paddock, fallback)."""

    def ordem(c: PiqueteProjetado) -> tuple[float, float, str]:
        distancia_m = 0.0 if origem is None else distancia_manejo_m(origem, c)
        return (_entrada(c) - altura_cm[c.piquete_id], distancia_m, c.nome)

    for fator, fallback in ((1.0, False), (FATOR_FALLBACK_ENTRADA, True)):
        elegiveis = [
            c
            for c in candidatos
            if altura_cm[c.piquete_id] >= fator * _entrada(c)
            and descanso[c.piquete_id] >= c.descanso_min_dias
        ]
        if elegiveis:
            return min(elegiveis, key=ordem), fallback
    return None


def _dias_previstos(
    destino: PiqueteProjetado, massa_kg_ms_ha: float, d: int, lote: LoteProjetado
) -> int:
    if lote.consumo_kg_ms_dia <= 0:
        return HORIZONTE_DIAS
    dias = forragem.dias_ocupacao(
        massa_kg_ms_ha,
        _saida(destino) * cast("float", destino.densidade_kg_ha_por_cm),
        _taxa(destino, d),
        destino.area_ha,
        catalogo.eficiencia(destino),
        lote.consumo_kg_ms_dia,
    )
    return HORIZONTE_DIAS if math.isinf(dias) else min(HORIZONTE_DIAS, max(1, math.floor(dias)))


def _motivo(
    lote: LoteProjetado,
    origem: PiqueteProjetado | None,
    destino: PiqueteProjetado,
    altura_destino_cm: float,
    fallback: bool,
) -> str:
    saiu = f"{lote.nome} está sem pasto registrado."
    if origem is not None:
        saiu = f"{origem.nome} chega à altura de saída ({_saida(origem):.0f} cm)."
    entrada = f"({_entrada(destino):.0f} cm)"
    fim = f"acima da entrada {entrada}."
    if fallback:
        fim = f"o mais perto da entrada {entrada} entre os disponíveis."
    return f"{saiu} {destino.nome} está com {altura_destino_cm:.0f} cm, {fim}"


def _confianca(
    destino: PiqueteProjetado, origem: PiqueteProjetado | None, lote: LoteProjetado
) -> tuple[Confianca, str]:
    """Weakest of destination, origin (if any) and lote weight; the first factor's motivo."""
    fatores = [(destino.confianca, destino.motivo_confianca)]
    if origem is not None:
        fatores.append((origem.confianca, origem.motivo_confianca))
    fatores.append((lote.confianca_peso, lote.motivo_confianca_peso))
    fraco = combinar_confianca(*(c for c, _ in fatores))
    return fraco, next(motivo for c, motivo in fatores if c == fraco)


def gerar_plano(  # noqa: PLR0915 — the simulation state lives in this scope, as closures
    estado: EstadoProjetado, fazenda: Fazenda, agora: datetime, plano_id: UUID
) -> PlanoManejo:
    """7-day plan: day-by-day greedy simulation, then the alert catalog."""
    capacidade = fazenda.funcionarios_disponiveis * fazenda.animais_por_funcionario_dia
    if capacidade <= 0:
        raise ValueError("a capacidade diária de manejo da fazenda deve ser positiva")
    plannable = tuple(p for p in estado.piquetes if _plannable(p))
    por_id = {p.piquete_id: p for p in plannable}
    lotes = {x.lote_id: x for x in estado.lotes if x.piquete_atual_id in {None, *por_id}}
    dias_manejo = tuple(fazenda.dias_preferenciais_manejo)
    posicao: dict[UUID, UUID | None] = {i: x.piquete_atual_id for i, x in lotes.items()}
    massa = {pid: cast("float", p.massa_hoje_kg_ms_ha) for pid, p in por_id.items()}
    ocupados0 = set(posicao.values())
    descanso = {pid: 0 if pid in ocupados0 else p.dias_descanso for pid, p in por_id.items()}
    movs: list[Movimentacao] = []
    emitidos: dict[tuple[TipoAlerta, UUID], Alerta] = {}
    dias: list[catalogo.DiaSimulado] = []

    def consumo() -> dict[UUID, float]:
        """Daily intake per occupied paddock (an occupied paddock is always a key)."""
        total: dict[UUID, float] = {}
        for lote_id, pid in posicao.items():
            if pid is not None:
                total[pid] = total.get(pid, 0.0) + lotes[lote_id].consumo_kg_ms_dia
        return total

    def fila(hoje: catalogo.DiaSimulado, d: int) -> list[LoteProjetado]:
        """Lotes that must leave today: unplaced first, then the most urgent, then by name."""
        k = next(j for j in range(1, 8) if (hoje.data + timedelta(days=j)).weekday() in dias_manejo)
        total = consumo()
        itens: list[tuple[tuple[int, float, str], LoteProjetado]] = []
        for lote_id, lote in lotes.items():
            pid = posicao[lote_id]
            if pid is None:
                itens.append(((0, 0.0, lote.nome), lote))
            elif _deve_sair(por_id[pid], massa[pid], total.get(pid, 0.0), d, k):
                folga_cm = hoje.altura_cm[pid] - _saida(por_id[pid])  # lower = urgent
                itens.append(((1, folga_cm, lote.nome), lote))
        return [lote for _, lote in sorted(itens, key=lambda item: item[0])]

    def mover(hoje: catalogo.DiaSimulado, d: int, lote: LoteProjetado) -> bool:
        """Send the lote to a destination, or record that no paddock is apt."""
        origem_id = posicao[lote.lote_id]
        origem = None if origem_id is None else por_id[origem_id]
        ocupado = consumo()
        candidatos = [
            c
            for c in piquetes_candidatos(estado, lote)
            if c.piquete_id in por_id and c.piquete_id not in ocupado
        ]
        escolha = _escolher(candidatos, origem, hoje.altura_cm, descanso)
        if escolha is None:
            alerta = catalogo.alerta_sem_piquete_apto(hoje.data, lote, origem)
            emitidos.setdefault((TipoAlerta.SEM_PIQUETE_APTO, lote.lote_id), alerta)
            return False
        destino, fallback = escolha
        altura_destino_cm = hoje.altura_cm[destino.piquete_id]
        confianca, motivo_confianca = _confianca(destino, origem, lote)
        movs.append(
            Movimentacao(
                id=uuid5(plano_id, f"{lote.lote_id}:{hoje.data.isoformat()}"),
                data=hoje.data,
                lote_id=lote.lote_id,
                lote_nome=lote.nome,
                piquete_origem_id=None if origem is None else origem.piquete_id,
                piquete_origem_nome=None if origem is None else origem.nome,
                piquete_destino_id=destino.piquete_id,
                piquete_destino_nome=destino.nome,
                altura_destino_cm=round(altura_destino_cm, 1),
                altura_entrada_alvo_cm=_entrada(destino),
                altura_origem_cm=(
                    None if origem is None else round(hoje.altura_cm[origem.piquete_id], 1)
                ),
                altura_saida_alvo_cm=None if origem is None else _saida(origem),
                dias_previstos=_dias_previstos(destino, massa[destino.piquete_id], d, lote),
                motivo=_motivo(lote, origem, destino, altura_destino_cm, fallback),
                confianca=confianca,
                motivo_confianca=motivo_confianca,
            )
        )
        posicao[lote.lote_id] = destino.piquete_id
        descanso[destino.piquete_id] = 0
        if origem is not None:
            descanso[origem.piquete_id] = 0
        return True

    def dia_de_manejo(hoje: catalogo.DiaSimulado, d: int) -> None:
        """Walk the exit queue within the team's capacity (animals per day)."""
        usados = 0
        for lote in fila(hoje, d):
            tamanho = sum(c.n_animais for c in lote.composicao)
            cabe = usados + tamanho <= capacidade
            if not cabe and usados > 0:
                pid = posicao[lote.lote_id]
                alerta = catalogo.alerta_capacidade_excedida(
                    hoje.data, lote, None if pid is None else por_id[pid]
                )
                emitidos.setdefault((TipoAlerta.CAPACIDADE_EXCEDIDA, lote.lote_id), alerta)
            elif mover(hoje, d, lote):
                usados += tamanho
            elif not cabe:
                break  # a herd bigger than the team is tried alone; if it cannot move, stop

    for d in range(HORIZONTE_DIAS):
        dia = estado.data_base + timedelta(days=d)
        hoje = catalogo.DiaSimulado(
            data=dia,
            dia_de_manejo=dia.weekday() in dias_manejo,
            altura_cm={
                pid: massa[pid] / cast("float", p.densidade_kg_ha_por_cm)
                for pid, p in por_id.items()
            },
            descanso_dias=dict(descanso),
            posicao_lote=dict(posicao),
        )
        dias.append(hoje)
        if hoje.dia_de_manejo:
            dia_de_manejo(hoje, d)
        total = consumo()
        for pid, p in por_id.items():
            massa[pid] = avancar_massa_um_dia(
                massa[pid], _taxa(p, d), total.get(pid, 0.0), p.area_ha, p.eficiencia_pastejo
            )
            if pid not in total:
                descanso[pid] += 1

    movimentacoes = tuple(sorted(movs, key=lambda m: (m.data, m.lote_nome)))
    todos = [
        *emitidos.values(),
        *catalogo.alertas_do_catalogo(estado, plannable, dias, movimentacoes),
    ]
    if not dias_manejo:
        todos.append(catalogo.alerta_sem_dia_cadastrado(estado.data_base))
    return PlanoManejo(
        id=plano_id,
        fazenda_id=estado.fazenda_id,
        data_geracao=agora,
        data_inicio=estado.data_base,
        horizonte_dias=HORIZONTE_DIAS,
        movimentacoes=movimentacoes,
        alertas=tuple(sorted(todos, key=lambda a: (a.data, a.tipo.value, a.texto))),
        pedidos_validacao=(),
        piquetes=_resumos(estado),
    )
