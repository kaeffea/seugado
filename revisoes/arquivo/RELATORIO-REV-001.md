# RELATÓRIO-REV-001 — RUNBOOK-REV-001 (Fundação do repositório)
**Data:** 17/09/2026 · **Veredicto:** aprovada com ressalva

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | `.git` existe, com exatamente um commit, e o commit não contém `.venv` nem cache | ✅ | `git log --oneline \| wc -l` → 1; `git show --stat HEAD` sem `.venv`/`__pycache__`/`.pytest_cache` |
| 2 | `uv sync --group dev` completou sem erro | ✅ | instalou 7 pacotes (`pytest 9.1.1`, `ruff 0.16.8`, `mypy 2.3.1`, deps transitivas); único aviso foi de hardlink (não é erro) |
| 3 | As quatro saídas do item 4 estão registradas no relatório | ✅ | ver seção "Execução" abaixo |
| 4 | Nenhum arquivo `00`–`12`, `models.py` ou `specs/` foi modificado; `git status --porcelain` limpo ao final | ⚠️ | nenhum arquivo rastreado foi modificado (confirmado), mas `git status --porcelain` **não** ficou limpo — `uv.lock` ficou untracked. Ver "Achados fora da implementação" |

## Execução
- `git init -b main` → repositório criado; `git add -A` seguido de `git status` confirmou que `.venv/`, `__pycache__/` e `.pytest_cache/` não entraram no stage; commit `73ff3af` "F-001: modelo de domínio + fundação do repositório" (27 arquivos, 3963 inserções).
- `uv sync --group dev` → `Python 3.12.3`; `pytest 9.1.1`, `ruff 0.16.8`, `mypy 2.3.1 (compiled: yes)`.
- `uv run ruff check .` → **5 erros** (`UP017` datetime-timezone-utc: 4; `I001` unsorted-imports: 1). Todos em `tests/conformance/test_spec_001_models.py` e `tests/core/test_models.py`. Nenhum em `seugado/core/models.py`.
- `uv run ruff format --check .` → **4 arquivos** seriam reformatados (`06-ARQUITETURA-E-STACK.md`, `specs/SPEC-001-domain-model.md`, `tests/conformance/test_spec_001_models.py`, `tests/core/test_models.py`); 21 já formatados.
- `uv run mypy` → **18 erros em 2 arquivos** (ambos em `tests/`, nenhum em `seugado/`): `union-attr` (8), `comparison-overlap` (4), `misc` (1), `index` (1), `no-untyped-def` (1), `no-untyped-call` (1), `unused-ignore` (1), `attr-defined` (1).
- `uv run pytest` → **157 passaram, 0 falharam, 0 pulados** (suíte de `tests/core/` + `tests/conformance/` combinadas).

## Defeitos na implementação
Nenhum. Este runbook não avalia código de produção — os apontamentos de `ruff`/`mypy` acima são a primeira medição pedida pelo item 4, não uma reprovação da fatia F-001 (já aprovada em RELATÓRIO anterior). Nenhum apontamento caiu em `seugado/core/models.py`.

## Achados fora da implementação

**A1 — Ordem do runbook deixa `git status --porcelain` sujo ao final (método).**
O item 2 manda commitar antes do item 3 rodar `uv sync`, mas `uv sync` gera `uv.lock` na raiz. Como o `.gitignore` (correto) não ignora `uv.lock` — é um lockfile, não um artefato descartável — ele fica **untracked** depois do item 3, e o critério de aceite do item 5 ("`git status --porcelain` limpo ao final") não fecha literalmente. Não commitei nem ignorei o arquivo por iniciativa própria: decisão de política de lockfile (comitar em novo commit? incluir no `.gitignore`? outro item no runbook?) cabe ao Arquiteto.

**A2 — `ruff format --check` reformataria dois documentos `00`–`12`-adjacentes (`06-ARQUITETURA-E-STACK.md` e `specs/SPEC-001-domain-model.md`).**
O ruff está formatando blocos de código Python dentro de cercas ```` ``` ```` em arquivos Markdown (comportamento do `ruff format` sobre Markdown, sem configuração explícita em `pyproject.toml` para isso). Como o runbook proíbe editar `00`–`12` e não pedi `--fix`, nada foi alterado — mas vale decidir se isso deve entrar no escopo do `ruff format --check` do CI, já que hoje ele aponta para arquivos que o Claude Code não tem permissão de tocar.

**A3 — Apontamentos de `ruff check .`, agrupados por regra:**
| Regra | Contagem | Arquivos |
|---|---|---|
| `UP017` (datetime-timezone-utc) | 4 | `tests/conformance/test_spec_001_models.py` (2), `tests/core/test_models.py` (2) |
| `I001` (unsorted-imports) | 1 | `tests/core/test_models.py` |

**A4 — Apontamentos de `mypy`, agrupados por regra:**
| Regra | Contagem | Arquivo |
|---|---|---|
| `union-attr` | 8 | `tests/conformance/test_spec_001_models.py` |
| `comparison-overlap` | 4 | `tests/conformance/test_spec_001_models.py` |
| `misc` | 1 | `tests/core/test_models.py` |
| `index` | 1 | `tests/core/test_models.py` |
| `no-untyped-def` | 1 | `tests/conformance/test_spec_001_models.py` |
| `no-untyped-call` | 1 | `tests/conformance/test_spec_001_models.py` |
| `unused-ignore` | 1 | `tests/conformance/test_spec_001_models.py` |
| `attr-defined` | 1 | `tests/conformance/test_spec_001_models.py` |

Os `comparison-overlap` em `Confianca` vs `QualidadeBase` (linhas 247, 467, 468) são o mesmo ponto já registrado como I4 em `revisoes/REV-001-pos-fatia-001.md` — o `mypy` confirma, em modo estrito, que a separação de tipos entre os dois `StrEnum` só existe em tempo de checagem estática, não em runtime.

**A5 — `pytest` passou 157/157, sem pulados.** O relatório anterior (`REV-001-pos-fatia-001.md`) registrava "156 passando e 1 pulado" por falta de `pyproject.toml`. Agora que o arquivo existe (item deste próprio runbook), o teste que dependia dele deixou de ser pulado e passou. Não é regressão — é o efeito esperado de F-000 ter sido concluído.

## Critérios não verificáveis
Nenhum. Todos os critérios do runbook puderam ser executados e verificados diretamente.

## Item 7 (opcional)
Não executado — não foi solicitado explicitamente pelo usuário nesta execução.
