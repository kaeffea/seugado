# RUNBOOK-REV-003 — Reorganizar o layout do repositório

**Origem:** chat `[ARQUITETURA] Revisão pós-F-001` · **Autoriza:** ADR-013
**Modelo recomendado:** Sonnet, esforço médio.

Mover arquivos, nada mais. Nenhuma linha de código muda de conteúdo.
**Invariante:** ao final, `uv run pytest` continua em **157 passando, 0 falhando, 0 pulados**,
e `ruff check .`, `ruff format --check .` e `mypy` continuam limpos. Se algum quebrar e não
for resolvido pelos passos abaixo, **desfaça com `git reset --hard HEAD` e relate**.

Use `git mv` (não `mv`), para o histórico seguir os arquivos.

## 1 · Ponto de partida

- [ ] `cd /mnt/c/code/seugado`
- [ ] `git status --porcelain` → deve estar **vazio**. Se não estiver, pare e relate:
      há trabalho não commitado que este runbook embaralharia.
- [ ] `uv run pytest` → registre o número antes de mexer.

## 2 · Documentos para `docs/`

- [ ] `mkdir -p docs`
- [ ] `git mv 00-INSTRUCOES-CUSTOM-INSTRUCTIONS.md 01-VISAO-E-ESCOPO.md 02-GLOSSARIO.md 03-DOMINIO-AGRONOMICO.md 04-SENSORIAMENTO-REMOTO-E-SAFER.md 05-PARAMETROS-CULTIVARES.md 06-ARQUITETURA-E-STACK.md 07-MOTOR-DE-OTIMIZACAO.md 08-METODO-DE-TRABALHO-LLM.md 09-TEMPLATE-SPEC-MUSE-CODE.md 10-ROTEIRO-DE-FATIAS.md 11-ESTADO-ATUAL.md 12-REGISTRO-DE-DECISOES-ADR.md docs/`
- [ ] Confirmar que `README.md` e `CLAUDE.md` **ficaram na raiz**: são os dois pontos de
      entrada, um para humano e um para agente.

## 3 · Código para `src/` (src-layout)

- [ ] `mkdir -p src`
- [ ] `git mv seugado src/seugado`
- [ ] Confirmar a árvore: `src/seugado/__init__.py`, `src/seugado/core/__init__.py`,
      `src/seugado/core/models.py`. Os três `__init__.py` continuam vazios.
- [ ] Remover caches que ficaram para trás, se existirem:
      `rm -rf src/seugado/__pycache__ src/seugado/core/__pycache__`

## 4 · `pyproject.toml`

O Arquiteto já ajustou o arquivo para o layout novo (`pythonpath = ["src"]`,
`mypy_path = "src"`, `files = ["src", "tests"]`). Você não edita; só confirma:

- [ ] `grep -n 'pythonpath\|mypy_path\|^files' pyproject.toml` → deve apontar para `src`.
      Se apontar para `.` ou para `seugado`, pare e relate: o arquivo não chegou atualizado.

## 5 · Verificar

- [ ] `uv run pytest` → **157/157**, igual ao passo 1. Se der erro de import, o problema é
      `pythonpath`; confira o passo 4 e relate em vez de improvisar.
- [ ] `uv run mypy` → limpo. Se reclamar que não encontra `seugado`, falta `mypy_path`.
- [ ] `uv run ruff check .` e `uv run ruff format --check .` → limpos.

## 6 · Commitar

- [ ] `git add -A`
- [ ] `git commit -m "ADR-013: docs/ e src-layout"`
- [ ] `git push`
- [ ] `git log --stat -1` → confirmar que o commit é **só de renomeação** (`R` no status dos
      arquivos), sem alteração de conteúdo em `models.py` nem nos testes.

## 7 · Critério de aceite

- [ ] Raiz contém apenas: `README.md`, `CLAUDE.md`, `pyproject.toml`, `uv.lock`,
      `.gitignore`, e as pastas `docs/`, `src/`, `tests/`, `specs/`, `revisoes/`
      (mais os diretórios ignorados: `.git`, `.venv`, `.*_cache`).
- [ ] As quatro ferramentas limpas, 157/157.
- [ ] `git log --follow --oneline -- src/seugado/core/models.py` mostra o histórico completo
      do arquivo, inclusive os commits anteriores à mudança de pasta.

## 8 · Relatório

- [ ] Escrever `revisoes/RELATORIO-REV-003.md` no formato do `CLAUDE.md`.
- [ ] Se algum caminho quebrado aparecer em qualquer documento ou script, **liste** em
      "Achados fora da implementação". Não corrija documento: isso é do Arquiteto.
