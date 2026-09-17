# RUNBOOK-REV-008 — commit dos documentos da ADR-014

**Data:** 17/09/2026 · **Origem:** `[ARQUITETURA] Método de pastejo — ADR-014`
**Modelo recomendado:** Sonnet, esforço médio.

Este runbook **só commita documentação**. Nenhum arquivo de `src/` ou `tests/` deve aparecer
no diff. Se aparecer, pare e relate — é trabalho do Muse Code ainda não verificado.

---

## Passo 0 — árvore de trabalho

```bash
cd /mnt/c/code/seugado
git status --short
git diff --stat
```

**Critério de aceite:** os arquivos modificados são **exatamente** estes nove, todos em `docs/`:

```
docs/01-VISAO-E-ESCOPO.md
docs/02-GLOSSARIO.md
docs/03-DOMINIO-AGRONOMICO.md
docs/05-PARAMETROS-CULTIVARES.md
docs/06-ARQUITETURA-E-STACK.md
docs/07-MOTOR-DE-OTIMIZACAO.md
docs/10-ROTEIRO-DE-FATIAS.md
docs/11-ESTADO-ATUAL.md
docs/12-REGISTRO-DE-DECISOES-ADR.md
```

Arquivo de `docs/` **a mais** no diff não é motivo para parar: commite junto e registre no
relatório. Arquivo em `src/` ou `tests/` **é** motivo para parar.

---

## Passo 1 — conferir conteúdo, não só presença

A gravação já truncou em silêncio duas vezes neste projeto. Antes de commitar, confirme que a
ADR-014 chegou inteira ao disco:

```bash
cd /mnt/c/code/seugado
grep -c "ADR-014" docs/12-REGISTRO-DE-DECISOES-ADR.md
grep -n "parametros_por_regime" docs/12-REGISTRO-DE-DECISOES-ADR.md docs/05-PARAMETROS-CULTIVARES.md docs/06-ARQUITETURA-E-STACK.md
grep -n "resolver_parametros" docs/06-ARQUITETURA-E-STACK.md docs/10-ROTEIRO-DE-FATIAS.md
grep -n "aguardando_parametro" docs/02-GLOSSARIO.md docs/07-MOTOR-DE-OTIMIZACAO.md
grep -n "F-009B" docs/10-ROTEIRO-DE-FATIAS.md docs/01-VISAO-E-ESCOPO.md
wc -c docs/*.md
```

**Critério de aceite:**
- `parametros_por_regime` aparece nos três arquivos.
- `resolver_parametros` aparece nos dois.
- `aguardando_parametro` aparece nos dois.
- `F-009B` aparece nos dois.
- Tamanhos esperados em bytes: `01` 9980 · `02` 13368 · `03` 14386 · `05` 29431 ·
  `06` 13849 · `07` 8788 · `10` 8558 · `11` ver passo 2 · `12` 25864.

**Qualquer `grep` sem resultado ou tamanho diferente: pare e relate**, nomeando o arquivo.
Não commite — a escrita não sobreviveu e o Arquiteto precisa regravar.

> `11-ESTADO-ATUAL.md` é gravado de novo depois da emissão deste runbook (fecha DT7 e corrige
> o status do F-002), então o tamanho dele não é verificável aqui. Confira só que ele contém
> a linha `### O que a ADR-014 decidiu`.

---

## Passo 2 — commit

```bash
cd /mnt/c/code/seugado
git add docs/
git status --short
git commit -m "docs: ADR-014 metodo de pastejo — parametro por regime, celula vazia, continuo em laco proprio"
git log --oneline -3
```

**Critério de aceite:** um commit novo, contendo **só** arquivos de `docs/`.
`git status --short` volta vazio para `docs/`.

---

## Passo 3 — as quatro ferramentas

Nenhum arquivo de código mudou, então isto é só confirmação de que a árvore segue limpa.

```bash
cd /mnt/c/code/seugado
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

**Critério de aceite:** quatro limpas, 157 testes passando. Qualquer regressão aqui é achado
fora da implementação — relate, não conserte.

---

## Passo 4 — push

```bash
cd /mnt/c/code/seugado
git push
```

**Critério de aceite:** push aceito, sem divergência com o remoto.

---

## Relatório

`revisoes/RELATORIO-REV-008.md`, formato do `CLAUDE.md`. Registre no mínimo:
- a lista final de arquivos commitados;
- o resultado de cada `grep` do passo 1;
- o hash do commit.
