# RUNBOOK-REV-009 — commit dos documentos da ADR-014 (substitui o REV-008)

**Data:** 17/09/2026 · **Origem:** `[ARQUITETURA] Método de pastejo — ADR-014`
**Modelo recomendado:** Sonnet, esforço médio.
**Substitui:** `RUNBOOK-REV-008`, reprovado corretamente. As duas falhas do RELATORIO-REV-008
eram premissas erradas do runbook, não corrupção de disco — ver `08` §7.3. Não reexecute o 008.

Este runbook **só commita documentação**. Nenhum arquivo de `src/` ou `tests/` deve aparecer
no diff. Se aparecer, pare e relate.

---

## Passo 0 — árvore de trabalho

```bash
cd /mnt/c/code/seugado
git status --short
git diff --stat
```

**Critério de aceite:** nada em `src/` nem em `tests/`. Modificação em `docs/`, `CLAUDE.md` e
`revisoes/` é do Arquiteto e entra no commit deste runbook. Arquivo de documentação **a mais**
no diff não é motivo para parar — commite junto e registre no relatório qual entrou.

---

## Passo 1 — verificação por manifesto

Uma linha. Nenhum número escrito à mão, nada que possa ter envelhecido desde a emissão:

```bash
cd /mnt/c/code/seugado
sha256sum -c revisoes/MANIFESTO-REV-009.sha256
```

**Critério de aceite:** todas as 14 linhas em `OK`.

- Qualquer `FAILED` → **pare e relate**, nomeando os arquivos marcados. Não commite: significa
  que o disco não é o que o Arquiteto gravou.
- Manifesto ausente → pare e relate. Não substitua por verificação improvisada.

O manifesto cobre `CLAUDE.md` e os treze arquivos de `docs/`. Ele **não** cobre a si mesmo nem
este runbook — os dois são arquivos novos e o `git status` do passo 0 já os mostra.

---

## Passo 2 — commit

```bash
cd /mnt/c/code/seugado
git add -A docs/ CLAUDE.md revisoes/
git status --short
git commit -m "docs: ADR-014 metodo de pastejo, correcao do status do F-002 e verificacao por manifesto"
git log --oneline -3
```

**Critério de aceite:** um commit novo, contendo só `docs/`, `CLAUDE.md` e `revisoes/`.
`git status --short` volta vazio para esses caminhos.

---

## Passo 3 — as quatro ferramentas

Nenhum arquivo de código mudou; isto é confirmação de que a árvore segue limpa.

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

`revisoes/RELATORIO-REV-009.md`, formato do `CLAUDE.md`. Registre no mínimo:
- a saída do `sha256sum -c` (resumida: "14/14 OK" basta se tudo passar);
- a lista final de arquivos commitados;
- o hash do commit.
