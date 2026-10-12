"""Alert catalog of the daily engine (SPEC-019 R7-R9).

Pure functions. A paddock's group is its `modulo_id` (None = the implicit "farm group"); a lote
belongs to the group `lote.modulo_id`. No alert ever states a number of animals.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from statistics import fmean
from uuid import UUID

from seugado.contratos import (
    Alerta,
    EstadoProjetado,
    LoteProjetado,
    Movimentacao,
    PiqueteProjetado,
    TipoAlerta,
)
from seugado.core.models import Confianca
from seugado.core.regras import combinar_confianca

# HIPOTESE-CALIBRAR: height ratio over the entry height from which an empty paddock is "past its
# point". Fix it in the threshold calibration ADR.
FATOR_PASSANDO_DO_PONTO = 1.2
# HIPOTESE-CALIBRAR: offer/demand ratio from which a group has surplus forage.
RAZAO_SOBRA = 1.2
# HIPOTESE-CALIBRAR: offer/demand ratio up to which a group lacks forage.
RAZAO_FALTA = 0.8


@dataclass(frozen=True, slots=True)
class DiaSimulado:
    """Start-of-day state of one simulated day, as the alert catalog needs it."""

    data: date
    dia_de_manejo: bool
    altura_cm: Mapping[UUID, float]  # plannable piquete_id -> start-of-day height
    descanso_dias: Mapping[UUID, int]  # plannable piquete_id -> rest at start of day
    posicao_lote: Mapping[UUID, UUID | None]  # lote_id -> piquete_id at start of day


def altura_entrada_cm(p: PiqueteProjetado) -> float:
    """Entry height of a plannable paddock."""
    assert p.parametros is not None and p.parametros.altura_entrada_cm is not None
    return p.parametros.altura_entrada_cm


def altura_saida_cm(p: PiqueteProjetado) -> float:
    """Exit height of a plannable paddock."""
    assert p.parametros is not None and p.parametros.altura_saida_cm is not None
    return p.parametros.altura_saida_cm


def eficiencia(p: PiqueteProjetado) -> float:
    """Grazing efficiency of a plannable paddock."""
    assert p.eficiencia_pastejo is not None
    return p.eficiencia_pastejo


def taxa_do_dia(p: PiqueteProjetado, d: int) -> float:
    """Forecast growth on day offset `d`; the last forecast value beyond the series."""
    taxa = p.taxa_acumulo_prevista_kg_ms_ha_dia
    return taxa[min(d, len(taxa) - 1)]


def _dd_mm(dia: date) -> str:
    return f"{dia:%d/%m}"


def _alerta(
    tipo: TipoAlerta,
    dia: date,
    textos: tuple[str, str],
    fonte: tuple[Confianca, str],
    ids: tuple[UUID | None, UUID | None, UUID | None],
) -> Alerta:
    """`textos` = (texto, acao); `fonte` = (confianca, motivo); `ids` = (piquete, lote, modulo)."""
    return Alerta(tipo, dia, textos[0], fonte[0], fonte[1], ids[0], ids[1], textos[1], ids[2])


def _do_piquete(
    tipo: TipoAlerta, dia: date, p: PiqueteProjetado, textos: tuple[str, str], lote_id: UUID | None
) -> Alerta:
    """Alert about a paddock: it carries the paddock's confidence, id and group."""
    ids = (p.piquete_id, lote_id, p.modulo_id)
    return _alerta(tipo, dia, textos, (p.confianca, p.motivo_confianca), ids)


def _ids_lote(
    lote: LoteProjetado, p: PiqueteProjetado | None
) -> tuple[UUID | None, UUID | None, UUID | None]:
    """(piquete, lote, modulo) of an alert about a lote standing in `p` (None = unplaced)."""
    return (None if p is None else p.piquete_id, lote.lote_id, lote.modulo_id)


def alerta_sem_piquete_apto(dia: date, lote: LoteProjetado, p: PiqueteProjetado | None) -> Alerta:
    """No paddock of the module is apt for the lote on `dia`; `p` is where it stands now."""
    textos = (
        f"Nenhum pasto pronto para o lote {lote.nome} em {_dd_mm(dia)}.",
        f"Manter o lote {lote.nome} onde está e conferir as alturas dos pastos do módulo "
        "com /alturas.",
    )
    if p is None:
        fonte = (Confianca.ALTA, "Lote sem pasto registrado.")
    else:
        fonte = (p.confianca, p.motivo_confianca)
    return _alerta(TipoAlerta.SEM_PIQUETE_APTO, dia, textos, fonte, _ids_lote(lote, p))


def alerta_capacidade_excedida(
    dia: date, lote: LoteProjetado, p: PiqueteProjetado | None
) -> Alerta:
    """The team cannot move one more herd on `dia`; `p` is where the lote stands now."""
    textos = (
        f"A equipe não dá conta de mover o lote {lote.nome} em {_dd_mm(dia)}.",
        f"Reforçar a equipe nesse dia ou mover o lote {lote.nome} no próximo dia de manejo.",
    )
    fonte = (Confianca.ALTA, "Mão de obra cadastrada da fazenda.")
    return _alerta(TipoAlerta.CAPACIDADE_EXCEDIDA, dia, textos, fonte, _ids_lote(lote, p))


def alerta_sem_dia_cadastrado(dia: date) -> Alerta:
    """The farm has no handling day registered; a farm-level alert (no ids)."""
    textos = (
        "Nenhum dia de manejo cadastrado na fazenda.",
        "Cadastrar os dias da semana em que a fazenda troca o gado de pasto.",
    )
    fonte = (Confianca.ALTA, "Configuração da fazenda.")
    return _alerta(TipoAlerta.SEM_DIA_DE_MANEJO, dia, textos, fonte, (None, None, None))


def _abaixo_da_saida(
    por_id: Mapping[UUID, PiqueteProjetado],
    lotes: Mapping[UUID, LoteProjetado],
    dia: DiaSimulado,
    movimentacoes: Sequence[Movimentacao],
) -> list[Alerta]:
    """Day 0 only: an occupied paddock already at or below its exit height."""
    ocupantes: dict[UUID, list[LoteProjetado]] = {}
    for lote_id, pid in dia.posicao_lote.items():
        if pid is not None and pid in por_id and lote_id in lotes:
            ocupantes.setdefault(pid, []).append(lotes[lote_id])
    alertas: list[Alerta] = []
    for pid, no_piquete in ocupantes.items():
        p, altura = por_id[pid], dia.altura_cm[pid]
        if altura > altura_saida_cm(p):
            continue
        lote = min(no_piquete, key=lambda x: x.nome)
        mov = next(
            (m for m in movimentacoes if m.lote_id == lote.lote_id and m.data == dia.data), None
        )
        if mov is not None:
            acao = f"Retirar o lote {lote.nome} hoje e levar para o {mov.piquete_destino_nome}."
        else:
            acao = (
                f"Retirar o lote {lote.nome} hoje. Nenhum pasto do módulo está pronto no plano: "
                "conferir as alturas com /alturas."
            )
        limite = altura_saida_cm(p)
        texto = f"{p.nome} está com {altura:.0f} cm, no limite de saída ({limite:.0f} cm)."
        alertas.append(
            _do_piquete(TipoAlerta.ABAIXO_DA_SAIDA, dia.data, p, (texto, acao), lote.lote_id)
        )
    return alertas


def _sem_dia_de_manejo(
    por_id: Mapping[UUID, PiqueteProjetado],
    lotes: Mapping[UUID, LoteProjetado],
    dias: Sequence[DiaSimulado],
) -> list[Alerta]:
    """A herd reaches its exit height on a day the farm does not handle cattle."""
    alertas: dict[UUID, Alerta] = {}
    for dia in dias:
        if dia.dia_de_manejo:
            continue
        for lote_id, pid in dia.posicao_lote.items():
            if lote_id in alertas or pid is None or pid not in por_id or lote_id not in lotes:
                continue
            p, lote = por_id[pid], lotes[lote_id]
            if dia.altura_cm[pid] > altura_saida_cm(p):
                continue
            quando = _dd_mm(dia.data)
            textos = (
                f"O lote {lote.nome} passa da altura de saída no {p.nome} em {quando}, "
                "antes do próximo dia de manejo.",
                f"Antecipar a troca do lote {lote.nome} para {quando}.",
            )
            alertas[lote_id] = _do_piquete(
                TipoAlerta.SEM_DIA_DE_MANEJO, dia.data, p, textos, lote_id
            )
    return list(alertas.values())


def _vazios(
    plannable: Sequence[PiqueteProjetado], dias: Sequence[DiaSimulado], destinos: set[UUID]
) -> list[Alerta]:
    """`passando_do_ponto` and `pronto_em` for empty paddocks that are not plan destinations."""
    passando: dict[UUID, Alerta] = {}
    pronto: dict[UUID, tuple[date, PiqueteProjetado]] = {}
    for dia in dias:
        ocupados = {pid for pid in dia.posicao_lote.values() if pid is not None}
        for p in plannable:
            pid = p.piquete_id
            if pid in ocupados or pid in destinos:
                continue
            altura, entrada = dia.altura_cm[pid], altura_entrada_cm(p)
            if altura >= FATOR_PASSANDO_DO_PONTO * entrada and pid not in passando:
                quando = _dd_mm(dia.data)
                textos = (
                    f"{p.nome} está passando do ponto: {altura:.0f} cm em {quando} "
                    f"(entrada {entrada:.0f} cm).",
                    f"Entrar com um lote do módulo no {p.nome} até {quando}; "
                    "se nenhum puder, ver o alerta de sobra de capim.",
                )
                passando[pid] = _do_piquete(TipoAlerta.PASSANDO_DO_PONTO, dia.data, p, textos, None)
            if altura >= entrada and dia.descanso_dias[pid] >= p.descanso_min_dias:
                pronto.setdefault(pid, (dia.data, p))
    primeiro_do_grupo: dict[UUID | None, tuple[date, PiqueteProjetado]] = {}
    for pronto_dia, p in pronto.values():
        atual = primeiro_do_grupo.get(p.modulo_id)
        if atual is None or (pronto_dia, p.nome) < (atual[0], atual[1].nome):
            primeiro_do_grupo[p.modulo_id] = (pronto_dia, p)
    alertas = list(passando.values())
    for pronto_dia, p in primeiro_do_grupo.values():
        quando = _dd_mm(pronto_dia)
        textos = (
            f"{p.nome} fica pronto para pastejo em {quando}.",
            f"Programar um lote do módulo para entrar no {p.nome} em {quando}.",
        )
        alertas.append(_do_piquete(TipoAlerta.PRONTO_EM, pronto_dia, p, textos, None))
    return alertas


def _oferta_e_demanda(
    estado: EstadoProjetado,
    plannable: Sequence[PiqueteProjetado],
    lotes: Sequence[LoteProjetado],
    n_dias: int,
) -> list[Alerta]:
    """Surplus or lack of forage per group: mean daily growth against daily intake."""
    grupos = {p.modulo_id for p in plannable} & {lote.modulo_id for lote in lotes}
    alertas: list[Alerta] = []
    for grupo in sorted(grupos, key=lambda g: (g is not None, str(g))):
        ps = sorted((p for p in plannable if p.modulo_id == grupo), key=lambda p: p.nome)
        ls = sorted((x for x in lotes if x.modulo_id == grupo), key=lambda x: x.nome)
        demanda_kg_ms_dia = sum(x.consumo_kg_ms_dia for x in ls)
        if demanda_kg_ms_dia == 0:
            continue
        oferta_kg_ms_dia = fmean(
            sum(taxa_do_dia(p, d) * p.area_ha * eficiencia(p) for p in ps) for d in range(n_dias)
        )
        razao = oferta_kg_ms_dia / demanda_kg_ms_dia
        if razao >= RAZAO_SOBRA:
            tipo, verbo = TipoAlerta.SOBRA_DE_CAPIM, "Sobra"
            acao = "Trazer mais animais para o módulo ou tirar piquetes do rodízio."
        elif razao <= RAZAO_FALTA:
            tipo, verbo = TipoAlerta.FALTA_DE_CAPIM, "Falta"
            acao = "Reduzir os animais do módulo ou juntar mais piquetes a ele."
        else:
            continue
        nomes = ", ".join(p.nome for p in ps)
        rotulo = "pastos sem módulo" if grupo is None else f"módulo de {nomes}"
        pct = round(razao * 100)
        texto = f"{verbo} capim no {rotulo}: o pasto cresce {pct}% do que os animais comem."
        fatores = [(p.confianca, p.motivo_confianca) for p in ps]
        fatores += [(x.confianca_peso, x.motivo_confianca_peso) for x in ls]
        fraco = combinar_confianca(*(c for c, _ in fatores))
        fonte = (fraco, next(m for c, m in fatores if c == fraco))
        alertas.append(_alerta(tipo, estado.data_base, (texto, acao), fonte, (None, None, grupo)))
    return alertas


def alertas_do_catalogo(
    estado: EstadoProjetado,
    plannable: Sequence[PiqueteProjetado],
    dias: Sequence[DiaSimulado],
    movimentacoes: Sequence[Movimentacao],
) -> tuple[Alerta, ...]:
    """Catalog alerts of a simulated plan; empty when there are no simulated days."""
    if not dias:
        return ()
    por_id = {p.piquete_id: p for p in plannable}
    geridos = [x for x in estado.lotes if x.lote_id in dias[0].posicao_lote]
    lotes = {x.lote_id: x for x in geridos}
    destinos = {m.piquete_destino_id for m in movimentacoes}
    alertas = [
        *_abaixo_da_saida(por_id, lotes, dias[0], movimentacoes),
        *_sem_dia_de_manejo(por_id, lotes, dias),
        *_vazios(plannable, dias, destinos),
        *_oferta_e_demanda(estado, plannable, geridos, len(dias)),
    ]
    return tuple(sorted(alertas, key=lambda a: (a.data, a.tipo.value, a.texto)))
