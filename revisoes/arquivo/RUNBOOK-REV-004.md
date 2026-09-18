# RUNBOOK-REV-004 — Reorganizar o layout do repositório (substitui o REV-003)

**Origem:** chat `[ARQUITETURA] Revisão pós-F-001` · **Autoriza:** ADR-013
**Substitui:** RUNBOOK-REV-003, reprovado corretamente no passo 1 — ele exigia árvore limpa
sem antes commitar as alterações que o próprio Arquiteto havia escrito.
**Modelo recomendado:** Sonnet, esforço médio.

Dois commits: um com as edições de documento que o Arquiteto deixou pendentes, outro **só de
renomeação**. Separar os dois é o que mantém o `git log --follow` legível.

**Invariante:** ao final, `uv run pytest` em **157 passando, 0 falhando, 0 pulados**, e
`ruff check .`, `ruff format --check .` e `mypy` limpos. Se quebrar e os passos abaixo não
resolverem, `git reset --hard HEAD` e relate.

Use `git mv`, não `mv`.

## 1 · Commitar o que o Arquiteto escreveu

Alteração não commitada em documento, `README.md`, `CLAUDE.md`, `pyproject.toml` ou
`revisoes/` é trabalho do Arquiteto: commite, não investigue.

- [ ] `cd /mnt/c/code/seugado && git status --porcelain`
- [ ] Se aparecer qualquer coisa em `seugado/`, `src/` ou `tests/`, **pare e relate** —
      isso não é do Arquiteto e este runbook embaralharia.
- [ ] `git add -A && git commit -m "docs: ADR-013, README, CLAUDE.md e runbooks"`
- [ ] `git status --porcelain` → agora vazio.
- [ ] `uv run pytest` → registre o número antes de mover nada.

## 2 · Documentos para `docs/`

- [ ] `mkdir -p docs`
- [ ] `git mv 00-INSTRUCOES-CUSTOM-INSTRUCTIONS.md 01-VISAO-E-ESCOPO.md 02-GLOSSARIO.md 03-DOMINIO-AGRONOMICO.md 04-SENSORIAMENTO-REMOTO-E-SAFER.md 05-PARAMETROS-CULTIVARES.md 06-ARQUITETURA-E-STACK.md 07-MOTOR-DE-OTIMIZACAO.md 08-METODO-DE-TRABALHO-LLM.md 09-TEMPLATE-SPEC-MUSE-CODE.md 10-ROTEIRO-DE-FATIAS.md 11-ESTADO-ATUAL.md 12-REGISTRO-DE-DECISOES-ADR.md docs/`
- [ ] `README.md` e `CLAUDE.md` **ficam na raiz**: são os dois pontos de entrada, um para
      humano e um para agente.

## 3 · Código para `src/` (src-layout)

- [ ] `mkdir -p src`
- [ ] `git mv seugado src/seugado`
- [ ] Conferir a árvore: `src/seugado/__init__.py`, `src/seugado/core/__init__.py`,
      `src/seugado/core/models.py`. Os três `__init__.py` continuam vazios.
- [ ] `rm -rf src/seugado/__pycache__ src/seugado/core/__pycache__` se sobraram.

## 4 · Conferir a configuração (não editar)

- [ ] `grep -n 'pythonpath\|mypy_path\|^files' pyproject.toml` → tudo apontando para `src`.
      Se apontar para `.` ou `seugado`, pare e relate: o arquivo não chegou atualizado.

## 5 · Verificar

- [ ] `uv run pytest` → **157/157**, igual ao passo 1. Erro de import ⇒ problema em
      `pythonpath`: confira o passo 4 e relate em vez de improvisar.
- [ ] `uv run mypy` → limpo. Se não encontrar `seugado`, falta `mypy_path`.
- [ ] `uv run ruff check .` e `uv run ruff format --check .` → limpos.

## 6 · Commitar a renomeação

- [ ] `git add -A && git commit -m "ADR-013: docs/ e src-layout"`
- [ ] `git push`
- [ ] `git log --stat -1` → confirmar que o commit é **só de renomeação** (`R` no status),
      sem alteração de conteúdo em `models.py` nem nos testes.

## 7 · Critério de aceite

- [ ] Raiz contém apenas `README.md`, `CLAUDE.md`, `pyproject.toml`, `uv.lock`,
      `.gitignore` e as pastas `docs/`, `src/`, `tests/`, `specs/`, `revisoes/`
      (mais os ignorados: `.git`, `.venv`, `.*_cache`).
- [ ] Quatro ferramentas limpas, 157/157.
- [ ] `git log --follow --oneline -- src/seugado/core/models.py` mostra o histórico completo,
      inclusive os commits anteriores à mudança de pasta.
- [ ] Dois commits novos: um `docs:` e um `ADR-013:`.

## 8 · Relatório

- [ ] Escrever `revisoes/RELATORIO-REV-004.md` no formato do `CLAUDE.md`.
- [ ] Caminho quebrado em documento ou script: **liste** em "Achados fora da implementação".
      Não corrija documento — isso é do Arquiteto.
