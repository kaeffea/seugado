# RUNBOOK-FATIA-001B-commit — commit do código da F-001B

**Data:** 17/09/2026 · **Origem:** `[FATIA-001B]` — fechamento, depois de
`SPEC-002-CORRECAO-A` aplicada pelo Muse Code e reverificada.

Este runbook **só roda depois** de você confirmar que `SPEC-002-CORRECAO-A-mypy-annotation.md`
foi colada no Muse Code, o Muse devolveu `tests/core/test_models.py` corrigido, e você
reverificou. Se isso ainda não aconteceu, pare — os passos 0 e 1 abaixo checam exatamente essa
pré-condição antes de deixar o runbook prosseguir para o commit.

---

## Passo 0 — árvore de trabalho

```bash
cd /mnt/c/code/seugado
git status --short
git diff --stat
```

Classifique antes de agir (`CLAUDE.md`, "Passo zero de todo runbook"): mudança em `docs/`,
`specs/` ou `revisoes/` é do Arquiteto — commite à parte, agora, antes de tocar em `src/`/
`tests/`:

```bash
cd /mnt/c/code/seugado
git add docs/ specs/ revisoes/
git status --short
git commit -m "docs: SPEC-002-CORRECAO-A e RUNBOOK-FATIA-001B-commit"
```

Se `git status --short` não mostrar nada pendente em `docs/`, `specs/` ou `revisoes/` (por
exemplo, se um commit anterior já os pegou), pule este commit e siga — não é erro.

**Critério de aceite:** depois deste passo, as únicas mudanças restantes em `src/` e `tests/`
são `src/seugado/core/models.py`, `tests/core/test_models.py` e
`tests/conformance/test_spec_001_models.py` — as três já cobertas pelo RELATORIO-FATIA-001B e
pela correção A. Qualquer outro arquivo de código modificado é inesperado: pare e relate antes
de prosseguir.

## Passo 1 — pré-condição: a correção A está aplicada e mypy está limpo

```bash
cd /mnt/c/code/seugado
grep -n "type: ignore\[comparison-overlap\]" tests/core/test_models.py
uv run mypy
```

**Critério de aceite:** o `grep` mostra as duas linhas de `test_metodo_pastejo_has_two_members`
com a anotação; `uv run mypy` termina em `Success: no issues found`, sem exceção para nenhum
arquivo.

- Se a anotação não aparecer, ou `mypy` ainda falhar: **pare e relate**. Significa que
  `SPEC-002-CORRECAO-A` ainda não foi aplicada ou foi aplicada incompleta — não prossiga para
  o commit, e não tente corrigir você mesmo.

## Passo 2 — as quatro ferramentas, na íntegra

```bash
cd /mnt/c/code/seugado
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

**Critério de aceite:** quatro limpas; `pytest` mostra 177 testes passando (167 em
`tests/conformance/` + 10 em `tests/core/test_models.py`), zero falhas, zero pulados. Qualquer
número diferente é achado a relatar, não a ajustar.

## Passo 3 — commit

```bash
cd /mnt/c/code/seugado
git add src/seugado/core/models.py tests/core/test_models.py tests/conformance/test_spec_001_models.py
git status --short
git commit -m "F-001B: parametro de altura por regime (cultivar x metodo_pastejo) em models.py"
git log --oneline -3
```

**Critério de aceite:** um commit novo contendo só esses três arquivos. `git status --short`
volta vazio para `src/` e `tests/`.

## Passo 4 — push

```bash
cd /mnt/c/code/seugado
git push
```

**Critério de aceite:** push aceito, sem divergência com o remoto.

---

## Relatório

`revisoes/RELATORIO-FATIA-001B-commit.md`, formato do `CLAUDE.md`. Registre no mínimo:
- confirmação da pré-condição do passo 1;
- saída resumida das quatro ferramentas;
- a lista de arquivos commitados e o hash do commit.

## Depois deste runbook

A fatia F-001B está fechada. O Arquiteto atualiza `docs/11-ESTADO-ATUAL.md` (F-001B → ✅
concluída, F-002 e F-003 seguem como já registrado) e emite o handoff. Nenhuma ação sua além
de rodar este runbook e colar o relatório de volta.
