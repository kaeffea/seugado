# RELATÓRIO-REV-003 — RUNBOOK-REV-003 (Reorganizar o layout do repositório)
**Data:** 17/09/2026 · **Veredicto:** reprovada

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | Passo 1: `git status --porcelain` deve estar vazio antes de iniciar | ❌ | ver saída abaixo |

Execução interrompida no primeiro item do runbook, conforme instruído: *"pare no primeiro
item que falhar de forma não prevista e relate"* (CLAUDE.md) e o próprio passo 1 do
RUNBOOK-REV-003: *"Se não estiver [vazio], pare e relate: há trabalho não commitado que
este runbook embaralharia."*

`git status --porcelain` (via WSL, `/mnt/c/code/seugado`):

```
 M 06-ARQUITETURA-E-STACK.md
 M 09-TEMPLATE-SPEC-MUSE-CODE.md
 M 11-ESTADO-ATUAL.md
 M 12-REGISTRO-DE-DECISOES-ADR.md
 M CLAUDE.md
 M README.md
 M pyproject.toml
?? revisoes/RUNBOOK-REV-003.md
```

`git diff --stat`:

```
 06-ARQUITETURA-E-STACK.md      |  5 +++-
 09-TEMPLATE-SPEC-MUSE-CODE.md  |  9 ++++++
 11-ESTADO-ATUAL.md             | 33 +++++++++++----------
 12-REGISTRO-DE-DECISOES-ADR.md | 34 +++++++++++++++++++++
 CLAUDE.md                      | 66 +++++++++++++++++++++++++++++++----------
 README.md                      | 67 ++++++++++++++++++++++++------------------
 pyproject.toml                 |  6 ++--
 7 files changed, 157 insertions(+), 63 deletions(-)
```

Nenhum passo além do 1 foi executado: nenhum `git mv`, nenhuma verificação das quatro
ferramentas, nenhum commit. A árvore de trabalho não foi tocada por esta sessão.

## Execução
- `ruff check .` → não executado (runbook interrompido no passo 1)
- `ruff format --check .` → não executado
- `mypy` → não executado
- `pytest` → não executado

## Defeitos na implementação
Nenhum — nenhuma implementação foi tentada.

## Achados fora da implementação
- Há seis documentos de `docs/` (na verdade ainda na raiz, pré-mudança de layout) e
  `pyproject.toml` com alterações não commitadas de uma sessão anterior, mais o próprio
  `RUNBOOK-REV-003.md` como arquivo novo não rastreado. O runbook pressupõe árvore limpa
  antes do `git mv` em massa; misturar essas edições com a reorganização impediria o commit
  do passo 6 de ser "só de renomeação" (critério do passo 6: `R` no status, sem alteração de
  conteúdo).
- Não investiguei o conteúdo dessas edições pendentes (é fora do escopo deste runbook e da
  minha função). Quem decide se elas devem ser commitadas antes, descartadas, ou se o
  runbook deve ser ajustado para tolerar isso é o Arquiteto.

## Critérios não verificáveis
- Passos 2 a 8 do runbook: não verificáveis nesta execução porque a pré-condição do passo 1
  falhou e a execução foi interrompida ali, conforme instruído.
