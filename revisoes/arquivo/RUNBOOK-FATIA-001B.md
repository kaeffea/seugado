# RUNBOOK-FATIA-001B — commit da SPEC-002 e do KIT-ACEITE-002

**Data:** 17/09/2026 · **Origem:** `[FATIA-001B] Modelo de domínio: parâmetro por regime`
**Modelo recomendado:** Sonnet, esforço médio.

Este runbook **só commita documentação de planejamento** — a spec para o Muse Code, o kit de
aceite e a atualização de estado. Nenhum arquivo de `src/` ou `tests/` deve aparecer no diff.
Se aparecer, pare e relate: significa que algo tocou código de produção fora do fluxo
combinado (spec → Muse Code → Claude Code).

---

## Passo 0 — árvore de trabalho

```bash
cd /mnt/c/code/seugado
git status --short
git diff --stat
```

**Critério de aceite:** nada em `src/` nem em `tests/`. Modificação em `docs/`, `specs/`,
`CLAUDE.md` ou `revisoes/` é do Arquiteto e entra no commit deste runbook. Arquivo de
documentação **a mais** no diff não é motivo para parar — commite junto e registre no
relatório qual entrou (`CLAUDE.md` §"Passo zero de todo runbook").

---

## Passo 1 — verificação por manifesto

Uma linha. Nenhum número escrito à mão, nada que possa ter envelhecido desde a emissão:

```bash
cd /mnt/c/code/seugado
sha256sum -c revisoes/MANIFESTO-FATIA-001B.sha256
```

**Critério de aceite:** as três linhas em `OK`.

- Qualquer `FAILED` → **pare e relate**, nomeando os arquivos marcados. Não commite: significa
  que o disco não é o que o Arquiteto gravou.
- Manifesto ausente → pare e relate. Não substitua por verificação improvisada.

O manifesto cobre `docs/11-ESTADO-ATUAL.md`, `specs/SPEC-002-domain-model-regime.md` e
`revisoes/KIT-ACEITE-002.md`. Ele **não** cobre a si mesmo nem este runbook — os dois são
arquivos novos e o `git status` do passo 0 já os mostra.

---

## Passo 2 — commit

```bash
cd /mnt/c/code/seugado
git add -A docs/ specs/ revisoes/
git status --short
git commit -m "F-001B: spec e kit de aceite para parametro por regime em models.py"
git log --oneline -3
```

**Critério de aceite:** um commit novo, contendo só `docs/`, `specs/` e `revisoes/`.
`git status --short` volta vazio para esses caminhos.

---

## Passo 3 — as quatro ferramentas

Nenhum arquivo de código mudou; isto é confirmação de que a árvore de `src/`/`tests/` segue
exatamente como estava — o modelo aprovado (157 testes) não foi tocado por este runbook.

```bash
cd /mnt/c/code/seugado
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

**Critério de aceite:** quatro limpas, 157 testes passando. Regressão aqui é achado fora da
implementação — relate, não conserte.

---

## Passo 4 — push

```bash
cd /mnt/c/code/seugado
git push
```

**Critério de aceite:** push aceito, sem divergência com o remoto.

---

## Relatório

`revisoes/RELATORIO-FATIA-001B-emissao.md`, formato do `CLAUDE.md`. Registre no mínimo:
- a saída do `sha256sum -c` ("3/3 OK" basta se tudo passar);
- a lista final de arquivos commitados;
- o hash do commit.

## Ação manual depois deste runbook

Este runbook só coloca a spec e o kit no repositório e no histórico do git. Ele **não**
implementa nada. O próximo passo é humano: abrir `specs/SPEC-002-domain-model-regime.md` e
colar o conteúdo inteiro no Muse Code. Quando o Muse Code terminar, volte com o código
produzido para um chat `[REVISAO]` ou `[FATIA-001B] parte 2`, que vai ler
`revisoes/KIT-ACEITE-002.md` e escrever a suíte independente.
