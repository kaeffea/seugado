"""Producer-facing texts and buttons: pure functions producing Telegram HTML."""

import html
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from itertools import groupby
from uuid import UUID

from seugado.contratos import DiferencaLote, Movimentacao, PassoPlano, PlanoManejo
from seugado.core.models import Confianca
from seugado.delivery.canais.base import Botao

LIMITE_TEXTO_TELEGRAM = 4096

_DIAS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
_DIAS_CURTOS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
_CONFIANCA = {Confianca.ALTA: "alta", Confianca.MEDIA: "média", Confianca.BAIXA: "baixa"}

_RODAPE_PLANO = "Toque abaixo para dizer o que você fez, conferir as alturas ou mandar uma medição."
_AVISOS_OMITIDOS = "… (mais avisos omitidos)"
_RODAPE_ALTURAS = (
    "Se alguma estiver diferente do que você vê no pasto, toque no piquete e mande a altura"
    " medida com régua. Quando terminar, toque em Refazer o plano."
)

# Short bot replies (plain text, no names inside).
CANDIDATO_VENCIDO = "Essa atualização não vale mais."
CANDIDATO_JA_EM_USO = "Você já está usando esse plano. Toque em /plano para vê-lo."
PLANO_MANTIDO = "Combinado, seguimos com o plano que você já tem."
NAO_VINCULADO = "Este chat ainda não está ligado a uma fazenda. Peça o link à equipe SeuGado."
CODIGO_INVALIDO = "Não encontrei esse código. Confira o link que a equipe SeuGado mandou."
SEM_PLANO = "Ainda não há plano."
SEM_LOTES = "Ainda não há lotes cadastrados nesta fazenda."
NAO_ENTENDI = "Não entendi. Use /plano, /alturas, /mover ou toque nos botões."
MOVIMENTACAO_ANTIGA = "Esta movimentação é de um plano antigo. Use /plano."
JA_RESPONDIDA = "Você já respondeu esta movimentação."
QUAL_LOTE = "Qual lote você mudou de piquete?"
QUANDO = "Quando?"
OPCAO_VENCIDA = "Essa opção não vale mais. Comece de novo pelo /plano ou pelo /mover."
NUMERO_INVALIDO = "Não entendi o número. Digite só a altura em centímetros, por exemplo 35."
ALTURA_FORA_DA_FAIXA = "A altura precisa ser maior que 0 e no máximo 400 cm."
NAO_FIZ = "Entendido. Vou refazer o plano…"
REFAZENDO = "Refazendo o plano com as alturas novas…"
RECALCULANDO = "Recalculando o plano…"
RECALCULO_FALHOU = "Não consegui recalcular agora. Tento de novo na próxima rotina."
ERRO_INESPERADO = "Tive um problema para registrar isso. Tente de novo em alguns minutos."
AJUDA = "\n".join(
    [
        "🌱 <b>Como usar o SeuGado</b>",
        "/plano: ver o plano da semana",
        "/alturas: ver e corrigir a altura dos piquetes",
        "/mover: contar que você mudou um lote de piquete",
        "/ajuda: esta mensagem",
        "",
        "No plano, toque numa movimentação para dizer se fez (✅ Fiz), se não fez (❌ Não fiz)"
        " ou se fez diferente (🔄), levando o lote para outro piquete ou em outro dia.",
        "Para corrigir uma altura, toque no piquete e mande o número que você mediu com a régua,"
        " em centímetros.",
    ]
)


def _h(texto: str) -> str:
    """Escape names and planner sentences for parse_mode HTML (button labels are plain)."""
    return html.escape(texto, quote=False)


def _dia_curto(d: date) -> str:
    return f"{_DIAS_CURTOS[d.weekday()]} {d:%d/%m}"


def _dia_longo(d: date) -> str:
    return f"{_DIAS[d.weekday()]}, {d:%d/%m}"


def _cm(valor: float) -> str:
    """One decimal with comma, no trailing ',0': 31.5 -> '31,5', 34.0 -> '34'."""
    return f"{valor:.1f}".removesuffix(".0").replace(".", ",")


def _tamanho_telegram(texto: str) -> int:
    """Length in UTF-16 units of the raw HTML: never below what Telegram counts."""
    return len(texto.encode("utf-16-le")) // 2


def _rotulo_movimentacao(mov: Movimentacao) -> str:
    return f"{_dia_curto(mov.data)} · {mov.lote_nome} → {mov.piquete_destino_nome}"


def _bloco_movimentacao(mov: Movimentacao) -> str:
    lote, destino = _h(mov.lote_nome), _h(mov.piquete_destino_nome)
    if mov.piquete_origem_nome is None:
        titulo = f"▸ <b>Mover {lote} → {destino}</b>"
    else:
        titulo = f"▸ <b>Mover {lote}: {_h(mov.piquete_origem_nome)} → {destino}</b>"
    dias = "1 dia" if mov.dias_previstos == 1 else f"{mov.dias_previstos} dias"
    return "\n".join(
        [
            titulo,
            _h(mov.motivo),
            f"Previsão: {dias} no piquete · Confiança: {_CONFIANCA[mov.confianca]}",
            f"<i>({_h(mov.motivo_confianca)})</i>",
        ]
    )


def _montar_plano(
    plano: PlanoManejo, fazenda_nome: str, atualizado: bool, avisos: Sequence[str]
) -> str:
    fim = plano.data_inicio + timedelta(days=plano.horizonte_dias - 1)
    icone, rotulo = ("🔄", "Plano atualizado") if atualizado else ("🌱", "SeuGado")
    secoes = [
        f"{icone} <b>{rotulo} — {_h(fazenda_nome)}</b>\n"
        f"Plano da semana: {_dia_curto(plano.data_inicio)} a {_dia_curto(fim)}"
    ]
    if not plano.movimentacoes:
        secoes.append("Nenhuma movimentação necessária nesta semana.")
    for dia, movs in groupby(plano.movimentacoes, key=lambda mov: mov.data):
        blocos = "\n\n".join(_bloco_movimentacao(mov) for mov in movs)
        secoes.append(f"📅 <b>{_dia_longo(dia)}</b>\n{blocos}")
    if avisos:
        secoes.append("\n".join(["⚠️ <b>Avisos</b>", *avisos]))
    if plano.pedidos_validacao:
        pedidos = [
            f"• {_h(p.piquete_nome)}: {_h(p.motivo.rstrip('.'))}. Meça a altura com uma régua."
            for p in plano.pedidos_validacao
        ]
        secoes.append("\n".join(["📏 <b>Medições pedidas</b>", *pedidos]))
    secoes.append(_RODAPE_PLANO)
    return "\n\n".join(secoes)


def texto_plano(plano: PlanoManejo, fazenda_nome: str, atualizado: bool = False) -> str:
    """The weekly plan in one message; trailing alerts are cut to fit Telegram's limit."""
    avisos = [f"• {_h(alerta.texto)}" for alerta in plano.alertas]
    texto = _montar_plano(plano, fazenda_nome, atualizado, avisos)
    mantidos = len(avisos)
    while _tamanho_telegram(texto) > LIMITE_TEXTO_TELEGRAM and mantidos > 0:
        mantidos -= 1
        cortados = [*avisos[:mantidos], _AVISOS_OMITIDOS]
        texto = _montar_plano(plano, fazenda_nome, atualizado, cortados)
    return texto


def botoes_plano(plano: PlanoManejo) -> list[list[Botao]]:
    """One row per button: each movement, each requested measurement, then the heights."""
    linhas = [
        [Botao(f"{n}. {_rotulo_movimentacao(mov)}", f"m:{mov.id}")]
        for n, mov in enumerate(plano.movimentacoes, start=1)
    ]
    linhas += [
        [Botao(f"📏 Informar altura do {pedido.piquete_nome}", f"a:{pedido.piquete_id}")]
        for pedido in plano.pedidos_validacao
    ]
    linhas.append([Botao("📏 Conferir alturas dos piquetes", "h:")])
    return linhas


def texto_movimentacao(mov: Movimentacao) -> str:
    """One movement with its reason, asking what the producer did."""
    return "\n".join(
        [
            f"📅 <b>{_dia_longo(mov.data)}</b>",
            _bloco_movimentacao(mov),
            "",
            "Você fez esta movimentação?",
        ]
    )


def botoes_movimentacao(mov: Movimentacao) -> list[list[Botao]]:
    """Did it / did not / did it differently."""
    return [
        [Botao("✅ Fiz", f"f:{mov.id}"), Botao("❌ Não fiz", f"n:{mov.id}")],
        [Botao("🔄 Fiz diferente", f"d:{mov.id}")],
    ]


def texto_alturas(plano: PlanoManejo, medidas: Mapping[UUID, float] | None = None) -> str:
    """Estimated height of each piquete in the plan.

    `medidas` (piquete_id -> cm) holds ruler readings taken after the plan was generated;
    they replace the plan's estimate so the producer sees the number just sent.
    """
    medidas = medidas or {}
    linhas = [f"📏 <b>Altura dos piquetes</b> (estimativa de {_dia_curto(plano.data_inicio)})"]
    for piquete in plano.piquetes:
        nome = _h(piquete.nome)
        medida = medidas.get(piquete.piquete_id)
        if medida is not None:
            linhas.append(f"• {nome}: {_cm(medida)} cm (medida com régua)")
        elif piquete.altura_hoje_cm is None:
            linhas.append(f"• {nome}: sem estimativa")
        else:
            confianca = _CONFIANCA[piquete.confianca]
            linhas.append(f"• {nome}: ~{_cm(piquete.altura_hoje_cm)} cm (confiança {confianca})")
    return "\n".join([*linhas, "", _RODAPE_ALTURAS])


def botoes_alturas(plano: PlanoManejo) -> list[list[Botao]]:
    """One "Corrigir" button per piquete, two per row, then "Terminei"."""
    corrigir = [Botao(f"Corrigir {p.nome}", f"a:{p.piquete_id}") for p in plano.piquetes]
    linhas = [corrigir[i : i + 2] for i in range(0, len(corrigir), 2)]
    linhas.append([Botao("✅ Terminei — refazer o plano", "r:")])
    return linhas


def _passos(passos: Sequence[PassoPlano]) -> str:
    if not passos:
        return "nenhuma movimentação"
    return "; ".join(f"{_dia_curto(p.data)} → {_h(p.piquete_destino_nome)}" for p in passos)


def texto_diferencas(diferencas: Sequence[DiferencaLote]) -> str:
    """What the candidate plan changes, lote by lote (before / now)."""
    if not diferencas:
        return "O plano novo não muda nada do que você ainda não fez."
    blocos = [
        f"▸ <b>{_h(d.lote_nome)}</b>\n  antes: {_passos(d.antes)}\n  agora: {_passos(d.depois)}"
        for d in diferencas
    ]
    return "\n\n".join(
        ["🛰️ <b>O que muda no plano</b>", *blocos, "Quer usar o plano novo ou manter o anterior?"]
    )


def texto_candidato(diferencas: Sequence[DiferencaLote]) -> str:
    """Mid-week notice that new satellite data changed what the producer has not done yet."""
    lotes = "1 lote" if len(diferencas) == 1 else f"{len(diferencas)} lotes"
    return (
        f"🛰️ Chegaram imagens novas do satélite e o plano da semana mudou para {lotes}."
        " Você pode manter o seu plano ou ver as mudanças."
    )


def botoes_candidato(plano_id: UUID) -> list[list[Botao]]:
    """See the changes or keep the current plan."""
    return [
        [Botao("👀 Ver mudanças", f"pv:{plano_id}"), Botao("👍 Manter meu plano", f"pk:{plano_id}")]
    ]


def botoes_diferencas(plano_id: UUID) -> list[list[Botao]]:
    """After seeing the changes: switch to the candidate or keep the current plan."""
    return [
        [
            Botao("✅ Usar o plano novo", f"pu:{plano_id}"),
            Botao("↩️ Manter o anterior", f"pk:{plano_id}"),
        ]
    ]


def texto_lembrete(pendentes: Sequence[Movimentacao]) -> str:
    """Daily reminder of past movements still without an answer."""
    linhas = [
        f"• {_dia_curto(m.data)} · {_h(m.lote_nome)} → {_h(m.piquete_destino_nome)}"
        for m in pendentes
    ]
    return "\n".join(
        [
            "Você ainda não me disse se fez estas movimentações:",
            *linhas,
            "",
            "Toque em uma delas para responder.",
        ]
    )


def botoes_lembrete(pendentes: Sequence[Movimentacao]) -> list[list[Botao]]:
    """One "m:" button per pending movement, labelled like the reminder lines."""
    return [[Botao(_rotulo_movimentacao(mov), f"m:{mov.id}")] for mov in pendentes]


def texto_vinculado(fazenda_nome: str) -> str:
    return f"Pronto! A {_h(fazenda_nome)} está conectada. Você vai receber o plano da semana aqui."


def texto_ja_vinculado(fazenda_nome: str) -> str:
    return (
        f"Este chat já está ligado à {_h(fazenda_nome)}."
        " Para trocar de fazenda, fale com a equipe SeuGado."
    )


def texto_fiz(lote_nome: str, piquete_nome: str) -> str:
    return f"✅ Anotado: {_h(lote_nome)} no {_h(piquete_nome)}."


def texto_anotado_recalculando(lote_nome: str, piquete_nome: str) -> str:
    return f"✅ Anotado: {_h(lote_nome)} no {_h(piquete_nome)}. {RECALCULANDO}"


def texto_para_qual_piquete(lote_nome: str) -> str:
    return f"Para qual piquete o {_h(lote_nome)} foi?"


def texto_sem_piquete_livre(lote_nome: str) -> str:
    return f"Não há piquete ativo e vazio para onde o {_h(lote_nome)} possa ter ido."


def texto_pedir_altura(piquete_nome: str) -> str:
    return f"Digite a altura do {_h(piquete_nome)} em centímetros (só o número)."


def texto_altura_anotada(piquete_nome: str, altura_cm: float) -> str:
    return f"Anotado: {_h(piquete_nome)} com {_cm(altura_cm)} cm hoje."


def botoes_opcoes(rotulos: Sequence[str]) -> list[list[Botao]]:
    """One "o:<n>" button per option of the current conversation step, two per row."""
    botoes = [Botao(rotulo, f"o:{n}") for n, rotulo in enumerate(rotulos)]
    return [botoes[i : i + 2] for i in range(0, len(botoes), 2)]


def botoes_quando() -> list[list[Botao]]:
    """o:0 / o:1 / o:2 = today / yesterday / the day before."""
    return [[Botao("Hoje", "o:0"), Botao("Ontem", "o:1"), Botao("Anteontem", "o:2")]]
