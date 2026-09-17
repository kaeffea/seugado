# SeuGado — leia isto primeiro

Mapa simples do projeto. Os outros arquivos são densos de propósito; este não é.
Se você se perder, volte aqui.

---

## 1. O que o sistema faz

Olha o pasto por satélite e manda uma mensagem ao pecuarista dizendo **qual lote de gado
mover para qual piquete, e por quantos dias**.

Três palavras que aparecem em tudo:

- **piquete** — um pedaço cercado do pasto. É onde o gado fica.
- **lote** — um grupo de bois manejado junto. Nunca se move um boi sozinho, só o lote.
- **massa de forragem** — quanto capim existe ali, medido em quilos de matéria seca por
  hectare (`kg MS/ha`). Mede-se seco porque capim verde é quase todo água, e água não alimenta.

O problema que ele resolve: se o gado entra tarde, o capim já virou talo e alimenta pouco.
Se o gado sai tarde, a planta gasta reserva de raiz e o pasto degrada. As duas perdas se
evitam com a mesma decisão — **quando mover, para onde, por quanto tempo** — e hoje essa
decisão é tomada no olho ou em calendário fixo.

## 2. O que já existe

| Coisa | Estado |
|---|---|
| Base de conhecimento (13 documentos) | pronta |
| Repositório com git, ambiente e ferramentas | pronto |
| Modelo de domínio em código (`src/seugado/core/models.py`) | pronto, 157 testes passando |
| Cálculos de forragem, regras, satélite, otimizador, mensagem | **nada ainda** |

Estamos na fundação. Duas fatias concluídas de 22. O que trava o avanço agora **não é código**:
são números agronômicos que ainda não têm fonte confiável (ver `11-ESTADO-ATUAL.md`).

## 3. Quem faz o quê

Quatro participantes, e é importante não confundir:

| Quem | Faz | Nunca faz |
|---|---|---|
| **Você** | decide, aprova, cola a spec no Muse, roda o Claude Code | escrever documento à mão |
| **Claude (Arquiteto)**, neste Project | decide arquitetura, escreve os documentos, as specs, os kits de aceite e os runbooks | escrever código de produção |
| **Muse Code** | escreve o código, a partir de uma spec autocontida | decidir arquitetura; ver o kit de aceite |
| **Claude Code**, no terminal | roda comando, escreve a suíte independente, relata conformidade | alterar spec, ADR ou documento |

Por que o Muse não decide nada: ele é um modelo barato, de contexto curto. Se ele puder
escolher, escolhe diferente a cada chamada, e o sistema fica incoerente.

Por que quem escreve o código não é quem aprova: o Muse escreve testes próprios — é só um
teste de fumaça, para o código ter rodado ao menos uma vez. A verificação que vale é do
Claude Code, que **não vê** os números esperados da spec. Isso foi medido: plantaram-se 7
defeitos no código e a suíte que veio junto com a spec deixou passar quase todos.

## 4. O ciclo de uma fatia

```
1. Você abre um chat aqui:  [FATIA-002] Cálculos de forragem
2. O Arquiteto escreve:     specs/SPEC-002-*.md         → o Muse Code lê este
                            revisoes/KIT-ACEITE-002.md  → o Muse não deve abrir
3. No Muse Code:            "leia specs/SPEC-002-*.md e implemente"
4. No Claude Code:          "continue"
                            (ele acha sozinho o que está pendente em revisoes/)
5. Claude Code              → testa e escreve revisoes/RELATORIO-002.md
6. Você volta aqui e diz    "relatório 002 gerado, leia"
7. O Arquiteto atualiza os documentos e diz qual é o próximo chat
```

As suas ações, no total: **apontar o Muse para a spec, dizer "continue" ao Claude Code,
avisar aqui que o relatório saiu.** Mais alguns comandos de git. Nada de redigir documento,
nada de subir arquivo.

## 5. Onde fica cada coisa

Na raiz ficam só dois arquivos para ler — este, para você, e o `CLAUDE.md`, para o Claude
Code — mais a configuração. Todo o resto está em pasta.

```
docs/
  00-INSTRUCOES    o texto que vai no campo de instruções do Project (não é Knowledge)
  01-VISAO         o que o produto é e o que está fora de escopo
  02-GLOSSARIO     o nome certo de cada coisa. Em dúvida de vocabulário, é aqui
  03-DOMINIO       a agronomia, explicada para quem não é da área
  04-SENSORIAMENTO como o satélite vira número
  05-PARAMETROS    TODO número agronômico, com fonte. Nada entra em código sem estar aqui
  06-ARQUITETURA   stack, módulos, contratos, regras de código, ambiente
  07-MOTOR         o otimizador: formulação e restrições
  08-METODO        como os quatro participantes trabalham
  09-TEMPLATE      o molde de toda spec para o Muse
  10-ROTEIRO       as 22 fatias, na ordem
  11-ESTADO        ⬅ o que está feito, o que está travado, qual o próximo chat
  12-ADR           toda decisão fechada, com o porquê

src/seugado/       o código do app
tests/             core = testes do Muse · conformance = testes do Claude Code
specs/             as specs já emitidas
revisoes/          kits de aceite, runbooks e relatórios
```

`src/seugado/` em vez de `seugado/seugado/` é convenção de Python (*src-layout*): evita que
um comando rodado na raiz importe a pasta local em vez do pacote. O caminho de import não
muda — continua `from seugado.core...`.

**Comece sempre pelo `docs/11-ESTADO-ATUAL.md`.** É o único que muda toda semana.

## 6. Duas regras que explicam quase todas as decisões

1. **Nenhum número sem fonte.** Um parâmetro agronômico plausível e falso passa
   despercebido e contamina tudo depois dele. Se falta fonte, marca-se `TODO-PARAM` e a
   implementação espera. É por isso que o projeto parece travado: está travado de propósito.
2. **Custo R$ 0,00 até o MVP.** Toda escolha de stack cabe em camada gratuita.

## 7. Ambiente

O código roda no **WSL Ubuntu**, não no Windows — o Windows desta máquina não tem Python.
`.venv` criada com `uv`. Comandos: `uv sync --group dev`, `uv run pytest`, `uv run ruff check .`,
`uv run mypy`.
