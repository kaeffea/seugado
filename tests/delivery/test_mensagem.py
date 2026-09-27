"""T2: producer texts and buttons, checked against the reference format in LEO.md."""

import re
import uuid
from dataclasses import replace
from datetime import date

from seugado.contratos import DiferencaLote, PassoPlano, PlanoManejo
from seugado.delivery.canais.base import Botao
from seugado.delivery.mensagem import (
    LIMITE_TEXTO_TELEGRAM,
    botoes_alturas,
    botoes_candidato,
    botoes_lembrete,
    botoes_movimentacao,
    botoes_plano,
    texto_alturas,
    texto_candidato,
    texto_diferencas,
    texto_lembrete,
    texto_movimentacao,
    texto_plano,
)

MOV_RECRIA = "m:92e04bc9-414c-5762-908d-ea434ca7500c"
MOV_VACAS_SEG = "m:be11b0ed-1839-5a1c-aa41-3e56bbc07fcc"
MOV_VACAS_QUI = "m:102b191b-0cd2-5b71-b473-f5b1d90907f3"
PIQUETE = "11111111-1111-4111-8111-00000000000{}"

CONFIANCA_MARANDU = (
    "<i>(a altura de entrada do Marandu no pastejo rotacionado vem de fonte com confiança"
    " média)</i>"
)

PLANO_EXEMPLO = "\n".join(
    [
        "🌱 <b>SeuGado — Fazenda Exemplo</b>",
        "Plano da semana: seg 28/09 a dom 04/10",
        "",
        "📅 <b>Segunda, 28/09</b>",
        "▸ <b>Mover Recria: Piquete 2 → Piquete 6</b>",
        "O Piquete 2 chegaria a 11,6 cm antes do próximo dia de manejo (qui 01/10), abaixo da"
        " saída de 15 cm. O Piquete 6 está em 34 cm (ponto de entrada: 30 cm).",
        "Previsão: 7 dias no piquete · Confiança: média",
        CONFIANCA_MARANDU,
        "",
        "▸ <b>Mover Vacas com bezerro: Piquete 5 → Piquete 1</b>",
        "O Piquete 5 chegaria a 11,7 cm antes do próximo dia de manejo (qui 01/10), abaixo da"
        " saída de 15 cm. O Piquete 1 está em 31,5 cm (ponto de entrada: 30 cm).",
        "Previsão: 3 dias no piquete · Confiança: média",
        CONFIANCA_MARANDU,
        "",
        "📅 <b>Quinta, 01/10</b>",
        "▸ <b>Mover Vacas com bezerro: Piquete 1 → Piquete 3</b>",
        "O Piquete 1 chegaria a 7,5 cm antes do próximo dia de manejo (seg 05/10), abaixo da"
        " saída de 15 cm. Nenhum piquete estará no ponto de entrada; o Piquete 3 é o mais"
        " próximo, com 28,6 cm (alvo: 30 cm).",
        "Previsão: 4 dias no piquete · Confiança: média",
        CONFIANCA_MARANDU,
        "",
        "⚠️ <b>Avisos</b>",
        "• O Piquete 8 (Mombaça) ainda não recebe recomendação: a cultivar Mombaça ainda não"
        " tem calibração no SeuGado.",
        "• O Piquete 7 (pastejo contínuo) está em 38 cm, acima da altura máxima do Marandu"
        " (35 cm). Considere colocar mais animais nele.",
        "",
        "📏 <b>Medições pedidas</b>",
        "• Piquete 4: última imagem de satélite sem nuvem há 18 dias. Meça a altura com uma régua.",
        "",
        "Toque abaixo para dizer o que você fez, conferir as alturas ou mandar uma medição.",
    ]
)

RODAPE_ALTURAS = (
    "Se alguma estiver diferente do que você vê no pasto, toque no piquete e mande a altura"
    " medida com régua. Quando terminar, toque em Refazer o plano."
)


def _utf16(texto: str) -> int:
    return len(texto.encode("utf-16-le")) // 2


def _todos_os_botoes(plano: PlanoManejo) -> list[Botao]:
    teclados = [
        botoes_plano(plano),
        botoes_alturas(plano),
        botoes_lembrete(plano.movimentacoes),
        botoes_candidato(plano.id),
    ]
    teclados += [botoes_movimentacao(mov) for mov in plano.movimentacoes]
    return [botao for teclado in teclados for linha in teclado for botao in linha]


def test_texto_plano_reproduz_a_referencia(plano: PlanoManejo) -> None:
    assert texto_plano(plano, "Fazenda Exemplo") == PLANO_EXEMPLO


def test_texto_plano_atualizado_troca_so_a_primeira_linha(plano: PlanoManejo) -> None:
    linhas = texto_plano(plano, "Fazenda Exemplo", atualizado=True).split("\n")
    assert linhas[0] == "🔄 <b>Plano atualizado — Fazenda Exemplo</b>"
    assert linhas[1:] == PLANO_EXEMPLO.split("\n")[1:]


def test_texto_plano_sem_movimentacoes(plano: PlanoManejo) -> None:
    texto = texto_plano(replace(plano, movimentacoes=()), "Fazenda Exemplo")
    assert texto.split("\n")[2:4] == ["", "Nenhuma movimentação necessária nesta semana."]
    assert "📅" not in texto


def test_texto_plano_esconde_secoes_vazias(plano: PlanoManejo) -> None:
    vazio = replace(plano, movimentacoes=(), alertas=(), pedidos_validacao=())
    assert texto_plano(vazio, "Fazenda Exemplo") == "\n".join(
        [
            "🌱 <b>SeuGado — Fazenda Exemplo</b>",
            "Plano da semana: seg 28/09 a dom 04/10",
            "",
            "Nenhuma movimentação necessária nesta semana.",
            "",
            "Toque abaixo para dizer o que você fez, conferir as alturas ou mandar uma medição.",
        ]
    )


def test_texto_plano_corta_avisos_no_limite(plano: PlanoManejo) -> None:
    modelo = plano.alertas[0]
    alertas = tuple(replace(modelo, texto=f"Aviso {i:02d}: " + "x" * 110) for i in range(80))
    texto = texto_plano(replace(plano, alertas=alertas), "Fazenda Exemplo")
    assert _utf16(texto) <= LIMITE_TEXTO_TELEGRAM
    linhas = texto.split("\n")
    fim_avisos = linhas.index("📏 <b>Medições pedidas</b>") - 2
    assert linhas[fim_avisos] == "… (mais avisos omitidos)"
    assert "Aviso 00" in texto
    assert "Aviso 79" not in texto
    assert linhas[-1].startswith("Toque abaixo")


def test_limite_conta_emoji_como_o_telegram(plano: PlanoManejo) -> None:
    """Emoji outside the BMP count twice in UTF-16; len() alone would let the text overflow."""
    alertas = tuple(replace(plano.alertas[0], texto="🐄" * 60) for _ in range(40))
    texto = texto_plano(replace(plano, alertas=alertas), "Fazenda Exemplo")
    assert len(texto) < LIMITE_TEXTO_TELEGRAM
    assert _utf16(texto) <= LIMITE_TEXTO_TELEGRAM
    assert "… (mais avisos omitidos)" in texto


def test_nomes_e_frases_sao_escapados_so_no_html(plano: PlanoManejo) -> None:
    mov = replace(plano.movimentacoes[0], lote_nome="Lote <1> & cia")
    plano = replace(plano, movimentacoes=(mov,))
    texto = texto_plano(plano, "Sítio <A&B>")
    assert "🌱 <b>SeuGado — Sítio &lt;A&amp;B&gt;</b>" in texto
    assert "Mover Lote &lt;1&gt; &amp; cia: Piquete 2 → Piquete 6" in texto
    assert "Lote &lt;1&gt; &amp; cia → Piquete 6" in texto_lembrete([mov])
    assert botoes_plano(plano)[0][0].texto == "1. seg 28/09 · Lote <1> & cia → Piquete 6"


def test_botoes_plano(plano: PlanoManejo) -> None:
    assert botoes_plano(plano) == [
        [Botao("1. seg 28/09 · Recria → Piquete 6", MOV_RECRIA)],
        [Botao("2. seg 28/09 · Vacas com bezerro → Piquete 1", MOV_VACAS_SEG)],
        [Botao("3. qui 01/10 · Vacas com bezerro → Piquete 3", MOV_VACAS_QUI)],
        [Botao("📏 Informar altura do Piquete 4", f"a:{PIQUETE.format(4)}")],
        [Botao("📏 Conferir alturas dos piquetes", "h:")],
    ]


def test_texto_e_botoes_movimentacao(plano: PlanoManejo) -> None:
    mov = plano.movimentacoes[2]
    assert texto_movimentacao(mov) == "\n".join(
        [
            "📅 <b>Quinta, 01/10</b>",
            *PLANO_EXEMPLO.split("\n")[15:19],
            "",
            "Você fez esta movimentação?",
        ]
    )
    id_ = str(mov.id)
    assert botoes_movimentacao(mov) == [
        [Botao("✅ Fiz", f"f:{id_}"), Botao("❌ Não fiz", f"n:{id_}")],
        [Botao("🔄 Fiz diferente", f"d:{id_}")],
    ]


def test_movimentacao_sem_origem_e_de_um_dia(plano: PlanoManejo) -> None:
    mov = replace(
        plano.movimentacoes[0], piquete_origem_id=None, piquete_origem_nome=None, dias_previstos=1
    )
    texto = texto_movimentacao(mov)
    assert "▸ <b>Mover Recria → Piquete 6</b>" in texto
    assert "Previsão: 1 dia no piquete" in texto


def test_texto_alturas(plano: PlanoManejo) -> None:
    assert texto_alturas(plano) == "\n".join(
        [
            "📏 <b>Altura dos piquetes</b> (estimativa de seg 28/09)",
            "• Piquete 1: ~31,5 cm (confiança alta)",
            "• Piquete 2: ~22 cm (confiança alta)",
            "• Piquete 3: ~27 cm (confiança alta)",
            "• Piquete 4: ~21 cm (confiança baixa)",
            "• Piquete 5: ~26 cm (confiança média)",
            "• Piquete 6: ~34 cm (confiança alta)",
            "• Piquete 7: ~38 cm (confiança alta)",
            "• Piquete 8: sem estimativa",
            "",
            RODAPE_ALTURAS,
        ]
    )


def test_texto_alturas_mostra_medida_recente(plano: PlanoManejo) -> None:
    piquete_4 = uuid.UUID(PIQUETE.format(4))
    linhas = texto_alturas(plano, {piquete_4: 28.0}).split("\n")
    assert linhas[4] == "• Piquete 4: 28 cm (medida com régua)"
    assert linhas[1] == "• Piquete 1: ~31,5 cm (confiança alta)"


def test_botoes_alturas(plano: PlanoManejo) -> None:
    teclado = botoes_alturas(plano)
    assert teclado[0] == [
        Botao("Corrigir Piquete 1", f"a:{PIQUETE.format(1)}"),
        Botao("Corrigir Piquete 2", f"a:{PIQUETE.format(2)}"),
    ]
    assert [botao.dados for linha in teclado[:-1] for botao in linha] == [
        f"a:{PIQUETE.format(n)}" for n in range(1, 9)
    ]
    assert teclado[-1] == [Botao("✅ Terminei — refazer o plano", "r:")]


def test_texto_diferencas() -> None:
    diferencas = [
        DiferencaLote(
            uuid.uuid4(),
            "Recria",
            (PassoPlano(date(2026, 10, 1), "Piquete 3"),),
            (PassoPlano(date(2026, 10, 1), "Piquete 4"),),
        ),
        DiferencaLote(
            uuid.uuid4(),
            "Vacas com bezerro",
            (),
            (
                PassoPlano(date(2026, 9, 30), "Piquete 6"),
                PassoPlano(date(2026, 10, 3), "Piquete 1"),
            ),
        ),
    ]
    assert texto_diferencas(diferencas) == "\n".join(
        [
            "🛰️ <b>O que muda no plano</b>",
            "",
            "▸ <b>Recria</b>",
            "  antes: qui 01/10 → Piquete 3",
            "  agora: qui 01/10 → Piquete 4",
            "",
            "▸ <b>Vacas com bezerro</b>",
            "  antes: nenhuma movimentação",
            "  agora: qua 30/09 → Piquete 6; sáb 03/10 → Piquete 1",
            "",
            "Quer usar o plano novo ou manter o anterior?",
        ]
    )


def test_texto_diferencas_vazio() -> None:
    assert texto_diferencas([]) == "O plano novo não muda nada do que você ainda não fez."


def test_lembrete(plano: PlanoManejo) -> None:
    pendentes = plano.movimentacoes[:2]
    assert texto_lembrete(pendentes) == "\n".join(
        [
            "Você ainda não me disse se fez estas movimentações:",
            "• seg 28/09 · Recria → Piquete 6",
            "• seg 28/09 · Vacas com bezerro → Piquete 1",
            "",
            "Toque em uma delas para responder.",
        ]
    )
    assert botoes_lembrete(pendentes) == [
        [Botao("seg 28/09 · Recria → Piquete 6", MOV_RECRIA)],
        [Botao("seg 28/09 · Vacas com bezerro → Piquete 1", MOV_VACAS_SEG)],
    ]


def test_texto_e_botoes_candidato(plano: PlanoManejo) -> None:
    diferenca = DiferencaLote(uuid.uuid4(), "Recria", (), ())
    assert texto_candidato([diferenca, diferenca]) == (
        "🛰️ Chegaram imagens novas do satélite e o plano da semana mudou para 2 lotes."
        " Você pode manter o seu plano ou ver as mudanças."
    )
    assert "mudou para 1 lote." in texto_candidato([diferenca])
    assert botoes_candidato(plano.id) == [
        [
            Botao("👀 Ver mudanças", f"pv:{plano.id}"),
            Botao("👍 Manter meu plano", f"pk:{plano.id}"),
        ]
    ]


def test_nenhum_texto_tem_termo_tecnico(plano: PlanoManejo) -> None:
    diferencas = [DiferencaLote(uuid.uuid4(), "Recria", (), (PassoPlano(date(2026, 10, 1), "P"),))]
    textos = [
        texto_plano(plano, "Fazenda Exemplo"),
        texto_plano(plano, "Fazenda Exemplo", atualizado=True),
        texto_alturas(plano),
        texto_diferencas(diferencas),
        texto_candidato(diferencas),
        texto_lembrete(plano.movimentacoes),
        *(texto_movimentacao(mov) for mov in plano.movimentacoes),
        *(botao.texto for botao in _todos_os_botoes(plano)),
    ]
    proibido = re.compile(r"\b(NDVI|kg|MS)\b", re.IGNORECASE)
    for texto in textos:
        assert proibido.search(texto) is None, texto


def test_dados_de_todos_os_botoes_cabem_em_64_bytes(plano: PlanoManejo) -> None:
    botoes = _todos_os_botoes(plano)
    assert botoes
    assert all(len(botao.dados.encode("utf-8")) <= 64 for botao in botoes)
