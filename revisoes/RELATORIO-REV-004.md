# RELATÓRIO-REV-004 — RUNBOOK-REV-004 (reorganização do layout, ADR-013)
**Data:** 17/09/2026 · **Veredicto:** aprovada com ressalva

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | Raiz contém apenas `README.md`, `CLAUDE.md`, `pyproject.toml`, `uv.lock`, `.gitignore` e as pastas `docs/`, `src/`, `tests/`, `specs/`, `revisoes/` | ✅ | `ls -la` na raiz, passo 7 |
| 2 | Quatro ferramentas limpas, 157/157 | ✅ | ver seção Execução |
| 3 | `git log --follow --oneline -- src/seugado/core/models.py` mostra histórico completo | ✅ | mostra `91d115c ADR-013: docs/ e src-layout` e `73ff3af F-001: modelo de domínio + fundação do repositório` |
| 4 | Dois commits novos: um `docs:` e um `ADR-013:` | ⚠️ ressalva | três commits novos, não dois — ver "Defeitos na implementação" |
| 5 | Commit `ADR-013:` é só renomeação (`R` no status), sem alteração de conteúdo | ✅ | `git log --stat -1 91d115c` → `16 files changed, 0 insertions(+), 0 deletions(-)`, todas as linhas `R` |

## Execução
- Passo 1 (baseline antes de mover): `uv run pytest` → **157 passaram, 0 falharam, 0 pulados**.
- `ruff check .` → All checks passed!
- `ruff format --check .` → 8 files already formatted
- `mypy` → Success: no issues found in 8 source files
- `pytest` (final) → **157 passaram, 0 falharam, 0 pulados**

## Defeitos na implementação
Nenhum em `src/seugado/`.

## Achados fora da implementação

1. **Desvio do runbook: três commits em vez de dois.** Ao mover `seugado/` para `src/seugado/`
   (passo 3) e rodar `uv run pytest` (passo 5), a suíte quebrou: `tests/conformance/test_spec_001_models.py`
   tinha três caminhos absolutos hardcoded apontando para o layout antigo (`seugado/core/models.py`,
   `seugado/__init__.py`, `seugado/core/__init__.py`), usados para ler o código-fonte via AST e para
   checar que os `__init__.py` estão vazios. Esse arquivo é da minha própria suíte
   (`tests/conformance/`, não é código de produção nem documento de `docs/`), então corrigi os três
   caminhos para `src/seugado/...` e commitei em separado (`a1ef54e: tests: atualizar caminhos
   hardcoded de tests/conformance para src-layout (ADR-013)`) para manter o commit `ADR-013:` puro,
   como o runbook exige no passo 6. O runbook previa apenas dois commits (passo 6 e critério de
   aceite #4); reporto o desvio porque o arquivo não antecipava esse tipo de quebra — só cobria erro
   de import ligado a `pythonpath` (passo 5). Recomendo que o próximo runbook de reorganização de
   layout inclua explicitamente "atualizar caminhos hardcoded em `tests/conformance/`" como passo, já
   que é o ponto cego que este runbook teve.

2. **Referências de caminho desatualizadas em documentos** (não corrigidas, são do Arquiteto):
   - [README.md:31](README.md:31) — `` `seugado/core/models.py` `` sem prefixo `src/`.
   - [docs/11-ESTADO-ATUAL.md:156](docs/11-ESTADO-ATUAL.md:156) — `` `seugado/core/models.py` `` sem prefixo `src/`.
   - `specs/SPEC-001-domain-model.md` (linhas 47–49, 58, 264, 279, 295, 445, 456) — spec já
     encerrada, referencia `seugado/__init__.py`, `seugado/core/__init__.py` e
     `seugado/core/models.py` sem `src/`. Provavelmente correto deixar como registro histórico da
     spec tal como foi emitida ao Muse Code, mas sinalizo para o Arquiteto decidir.
   - `docs/12-REGISTRO-DE-DECISOES-ADR.md` (linhas 272, 283, 303) — menções a `seugado/` sem `src/`
     dentro do texto do próprio ADR-013 que decide a mudança para `src/seugado/`; parecem
     intencionais (descrevem o estado *antes* da decisão), mas vale conferência do Arquiteto.

## Critérios não verificáveis
Nenhum.
