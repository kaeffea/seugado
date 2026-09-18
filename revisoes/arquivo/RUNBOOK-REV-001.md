# RUNBOOK-REV-001 — Fundação do repositório

**Origem:** chat `[ARQUITETURA] Revisão pós-F-001` · **Autoriza:** ADR-012
**Modelo recomendado:** Sonnet, esforço médio.

Execute na ordem. Marque cada item. Pare e relate no primeiro erro não previsto.
Não edite os documentos `00`–`12` da raiz — eles são escritos pelo Arquiteto.
Não altere `seugado/core/models.py` neste runbook, mesmo que o linter reclame.

## 1 · Verificar o ponto de partida

- [ ] `cd /mnt/c/code/seugado && ls -a`
- [ ] Confirmar que `pyproject.toml` e `.gitignore` existem (foram criados pelo Arquiteto).
- [ ] Confirmar que **não** existe `.git`. Se existir, pare e relate — o histórico é de outra origem.

## 2 · Iniciar o versionamento

- [ ] `git init -b main`
- [ ] `git add -A`
- [ ] Verificar com `git status` que `.venv/`, `__pycache__/` e `.pytest_cache/` **não** entraram.
      Se entraram, o `.gitignore` não pegou: pare e relate.
- [ ] `git commit -m "F-001: modelo de domínio + fundação do repositório"`
- [ ] `git log --stat -1` e inclua a lista de arquivos no relatório.

## 3 · Instalar o ambiente declarado

- [ ] `uv sync --group dev`
- [ ] `uv run python -V` → esperado 3.12.x
- [ ] Registrar no relatório as versões instaladas de pytest, ruff e mypy.

## 4 · Rodar as verificações — **sem corrigir nada**

- [ ] `uv run ruff check .` — registre a contagem por regra.
- [ ] `uv run ruff format --check .` — registre quantos arquivos seriam reformatados.
- [ ] `uv run mypy` — registre os erros com arquivo e linha.
- [ ] `uv run pytest` — esperado: a suíte de `tests/core/` e a de `tests/conformance/` passando.

**Esperado:** `ruff` e `mypy` vão apontar coisas em `seugado/core/models.py` e nos testes.
Isso é a primeira medição, não uma falha da fatia F-001, que já foi aprovada.
Nenhuma correção neste runbook. A lista de apontamentos é o produto deste item.

## 5 · Critério de aceite deste runbook

- [ ] `.git` existe, com exatamente um commit, e o commit não contém `.venv` nem cache.
- [ ] `uv sync --group dev` completou sem erro.
- [ ] As quatro saídas do item 4 estão registradas no relatório.
- [ ] Nenhum arquivo `00`–`12`, nem `models.py`, nem `specs/`, foi modificado:
      comprovar com `git status --porcelain` limpo ao final.

## 6 · Relatório

- [ ] Escrever `revisoes/RELATORIO-REV-001.md` no formato do `CLAUDE.md`.
- [ ] No campo **Achados fora da implementação**, liste os apontamentos de `ruff` e `mypy`
      agrupados por regra, com a contagem. Não proponha conserto: o Arquiteto decide se
      vira spec para o Muse ou se a regra do linter é que está errada para este projeto.

## 7 · Opcional — só se o usuário pedir explicitamente

Publicar no GitHub, que é o que permitirá o Project Knowledge sincronizar do repositório
em vez de re-upload manual:

- [ ] `gh auth status` (se não estiver autenticado, pare e relate)
- [ ] `gh repo create seugado --private --source=. --push`
- [ ] Relatar a URL do repositório.
