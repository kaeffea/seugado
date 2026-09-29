"""MOCK — substituto de demonstração até o otimizador do João (J3). Não é o algoritmo do JOAO.md.

Rule: on the first preferred handling day of the week, each lote (by name) goes to the tallest
still-free rotational piquete that can be planned. Nothing is simulated day by day.
"""

from datetime import date, datetime, timedelta
from uuid import UUID, uuid5

from seugado.contratos import (
    Alerta,
    EstadoProjetado,
    Movimentacao,
    PiqueteProjetado,
    PlanoManejo,
    ResumoPiquete,
    TipoAlerta,
)
from seugado.core.models import Confianca, Fazenda, MetodoPastejo

HORIZONTE_DIAS = 7
DIAS_PREVISTOS_MOCK = 3  # MOCK: valor de demonstração, sem fonte agronômica

MOTIVO_MOCK = "Plano de demonstração: mover para o piquete com o capim mais alto disponível."
MOTIVO_CONFIANCA_MOCK = (
    "Plano de demonstração — o otimizador definitivo ainda está em desenvolvimento."
)


def _dia_manejo(data_base: date, dias_preferenciais: tuple[int, ...]) -> date | None:
    """First day in [data_base, data_base + 6] whose weekday the farm handles cattle on."""
    for i in range(HORIZONTE_DIAS):
        dia = data_base + timedelta(days=i)
        if dia.weekday() in dias_preferenciais:
            return dia
    return None


def _apto(p: PiqueteProjetado) -> bool:
    return (
        p.metodo_pastejo == MetodoPastejo.ROTACIONADO
        and not p.faltantes
        and p.parametros is not None
        and p.parametros.altura_entrada_cm is not None
        and p.altura_hoje_cm is not None
        and p.lote_atual_id is None
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


def gerar_plano(
    estado: EstadoProjetado, fazenda: Fazenda, agora: datetime, plano_id: UUID
) -> PlanoManejo:
    """MOCK weekly plan with the real contract, so the rest of the system can run end to end."""
    piquetes_por_id = {p.piquete_id: p for p in estado.piquetes}
    dia = _dia_manejo(estado.data_base, fazenda.dias_preferenciais_manejo)

    movimentacoes: list[Movimentacao] = []
    alertas: list[Alerta] = []
    if dia is None:
        alertas.append(
            Alerta(
                tipo=TipoAlerta.SEM_DIA_DE_MANEJO,
                data=estado.data_base,
                texto="Nenhum dia de manejo nesta semana: confira os dias preferidos da fazenda.",
                confianca=Confianca.ALTA,
                motivo_confianca="Configuração da fazenda.",
                piquete_id=None,
                lote_id=None,
            )
        )
    else:
        aptos = sorted(
            (p for p in estado.piquetes if _apto(p)),
            key=lambda p: (-(p.altura_hoje_cm or 0.0), p.nome),
        )
        for lote in sorted(estado.lotes, key=lambda lote: lote.nome):
            if not aptos:
                break
            destino = aptos.pop(0)
            assert destino.parametros is not None and destino.altura_hoje_cm is not None
            assert destino.parametros.altura_entrada_cm is not None
            origem = (
                None
                if lote.piquete_atual_id is None
                else piquetes_por_id.get(lote.piquete_atual_id)
            )
            movimentacoes.append(
                Movimentacao(
                    id=uuid5(plano_id, str(lote.lote_id)),
                    data=dia,
                    lote_id=lote.lote_id,
                    lote_nome=lote.nome,
                    piquete_origem_id=None if origem is None else origem.piquete_id,
                    piquete_origem_nome=None if origem is None else origem.nome,
                    piquete_destino_id=destino.piquete_id,
                    piquete_destino_nome=destino.nome,
                    altura_destino_cm=round(destino.altura_hoje_cm, 1),
                    altura_entrada_alvo_cm=destino.parametros.altura_entrada_cm,
                    altura_origem_cm=(
                        None
                        if origem is None or origem.altura_hoje_cm is None
                        else round(origem.altura_hoje_cm, 1)
                    ),
                    altura_saida_alvo_cm=(
                        None
                        if origem is None or origem.parametros is None
                        else origem.parametros.altura_saida_cm
                    ),
                    dias_previstos=DIAS_PREVISTOS_MOCK,
                    motivo=MOTIVO_MOCK,
                    confianca=Confianca.BAIXA,
                    motivo_confianca=MOTIVO_CONFIANCA_MOCK,
                )
            )

    return PlanoManejo(
        id=plano_id,
        fazenda_id=estado.fazenda_id,
        data_geracao=agora,
        data_inicio=estado.data_base,
        horizonte_dias=HORIZONTE_DIAS,
        movimentacoes=tuple(sorted(movimentacoes, key=lambda m: (m.data, m.lote_nome))),
        alertas=tuple(sorted(alertas, key=lambda a: (a.data, a.tipo.value, a.texto))),
        pedidos_validacao=(),
        piquetes=_resumos(estado),
    )
