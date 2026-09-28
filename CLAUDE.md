# CLAUDE.md — base comum aos três papéis

Este arquivo é carregado automaticamente em toda sessão aberta neste repositório.
Ele contém **só o que vale para os três papéis**. O que é específico de cada um vive em
`papeis/`.

---

## Antes de qualquer coisa: qual é o seu papel?

O trabalho neste repositório é dividido em três terminais, um por papel, justamente para que
os contextos não se misturem. **Você é exatamente um deles**, e o usuário diz qual na primeira
mensagem apontando o arquivo:

| Terminal | Papel | Arquivo a ler | Produz |
|---|---|---|---|
| 1 | **Arquiteto** | `papeis/ARQUITETO.md` | specs, kits de aceite, ADRs, pesquisa de parâmetro |
| 2 | **Programador** | `papeis/PROGRAMADOR.md` | `src/seugado/` e `tests/core/` |
| 3 | **Testador** | `papeis/TESTADOR.md` | `tests/conformance/`, relatório, commit |

**Se o usuário não disse qual papel você é, pergunte em uma linha e pare.** Não deduza pelo
pedido: o pedido "implemente a F-005" pode vir por engano no terminal do Arquiteto, e
adivinhar é exatamente a falha que a divisão existe para evitar.

Nunca acumule papéis numa sessão. Se o trabalho que aparecer for de outro papel, diga em uma
linha de qual papel é e pare — não faça "só essa parte".

---

## A regra que nenhum papel pode violar

**Nenhum número entra em spec, código, teste ou documento sem fonte rastreável.**

Parâmetros agronômicos vivem em `docs/05-PARAMETROS-CULTIVARES.md`, com fonte e nível de
confiança. Se um valor não está lá:

- marque `TODO-PARAM` e **pare** — quem resolve é o Arquiteto, em pesquisa;
- nunca preencha com valor plausível, nem como default, nem "só para o teste passar".

Número que **nós escolhemos** em vez de medir (peso de função objetivo, limiar de alerta,
tolerância numérica) é diferente: marque `HIPOTESE-CALIBRAR` e nomeie a ADR de calibração.

Por que isso é a regra nº 1: código errado quebra e aparece. Parâmetro agronômico inventado é
plausível, não quebra nada, e contamina silenciosamente tudo que vem depois dele.

---

## O muro entre os papéis (ADR-011)

A independência entre quem especifica, quem implementa e quem verifica é a defesa medida
contra código escrito para a asserção em vez de para o requisito. Sete defeitos estruturais
foram plantados de propósito em `models.py`: a suíte copiada da spec deixou passar quase
todos; a suíte independente pegou todos.

Com os três papéis no mesmo programa, o muro depende destas proibições de leitura:

| Papel | Nunca abre |
|---|---|
| Arquiteto | `src/`, `tests/` (escrita); não decide aprovação |
| **Programador** | **`revisoes/**` inteiro, `tests/conformance/**`, `docs/**`** |
| Testador | a seção `Worked example` da spec antes de escrever a suíte |

`revisoes/KIT-ACEITE-<NNN>.md` é o artefato que o Programador **não pode ter visto**. Se você
é o Programador e já leu um kit, mesmo sem querer, **diga isso ao usuário** — a fatia precisa
de sessão limpa. Esconder isso invalida a verificação.

---

## Layout do repositório (ADR-013)

```
README.md · CLAUDE.md · pyproject.toml · uv.lock · .gitignore
papeis/             ARQUITETO.md · PROGRAMADOR.md · TESTADOR.md
docs/               00–13, a base de conhecimento
specs/              specs por fatia
src/seugado/        o pacote (src-layout; import é `from seugado.core...`)
tests/core/         suíte de fumaça, escrita pelo Programador
tests/conformance/  suíte independente, escrita pelo Testador
tests/persistencia/ testes de I/O de banco (podem ser skipped sem banco)
db/migrations/      SQL puro, numerado
revisoes/           KIT-ACEITE-* e RELATORIO-* · arquivo/ é legado, não se lê
```

Onde está cada assunto:

| Assunto | Arquivo |
|---|---|
| Mapa do projeto | `README.md` |
| Estado, bloqueios, próxima fatia | `docs/11-ESTADO-ATUAL.md` |
| Vocabulário canônico | `docs/02-GLOSSARIO.md` |
| **Todo número agronômico** | `docs/05-PARAMETROS-CULTIVARES.md` |
| Stack, contratos entre módulos, regras de código | `docs/06-ARQUITETURA-E-STACK.md` |
| Decisões fechadas, com o porquê | `docs/12-REGISTRO-DE-DECISOES-ADR.md` |
| Arqueologia: bloqueios fechados, handoffs antigos | `docs/13-HISTORICO.md` — não se lê por padrão |

---

## Ambiente

O repositório vive em `/Users/leandro/Documents/Empreendedorismo/seugado` (macOS).

⚠️ `docs/06` §8 e o `README.md` §7 ainda descrevem WSL Ubuntu e `C:\code\seugado`, de uma
máquina anterior. **Ignore essas duas seções**; elas estão desatualizadas e precisam de
correção por edição cirúrgica.

Ambiente gerido por `uv`. Se `uv --version` falhar, o ambiente ainda não foi montado nesta
máquina — veja a seção de bootstrap em `papeis/TESTADOR.md`.

Verificação padrão, nesta ordem:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

`uv.lock` é versionado: isto é aplicação, não biblioteca, e o pipeline roda em GitHub Actions.

---

## Regras de escrita de documento

**Edição cirúrgica.** Ao alterar qualquer arquivo de `docs/`, mude só as linhas necessárias.
Nunca reescreva um documento de 300 linhas para trocar uma tabela.

**Sem runbooks, sem manifestos SHA-256.** Estão abolidos: cada papel roda seus próprios
comandos. Nunca crie `RUNBOOK-*.md` nem `MANIFESTO-*.sha256`.

**Um commit por fatia**, mensagem `F-NNN: <título>`. Commit de documentação: `docs: <assunto>`.
Quem commita é o Testador.
