# RELATÓRIO-REV-002 — RUNBOOK-REV-002
**Data:** 17/09/2026 · **Veredicto:** aprovada

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | Commitar documentos `02,03,05,06,08,09,10,11,12`, `pyproject.toml` e `revisoes/`, sem tocar `seugado/` | ✅ | commit `d06880b` — `git status --porcelain` pré-commit confirmou só esses arquivos |
| 2 | `uv.lock` versionado, fora do `.gitignore` | ✅ | commit `354382b`; `.gitignore` não lista `uv.lock` |
| 3 | `ruff check --fix` resolve `UP017`/`I001` em `tests/` | ✅ | `Found 9 errors (9 fixed, 0 remaining)` |
| 4 | `ruff format tests/` | ✅ | `2 files reformatted, 3 files left unchanged` |
| 5 | 157/157 testes antes de mexer em mypy | ✅ | `157 passed in 0.94s` (antes e depois) |
| 6 | 18 erros de mypy resolvidos conforme regras do runbook | ✅ | ver seção "Execução"; `Success: no issues found in 8 source files` |
| 7 | `comparison-overlap` StrEnum: `# type: ignore[comparison-overlap]` com o comentário exigido, sem mudar asserção | ✅ | 3 ocorrências (linhas 261, 510, 511 do arquivo original) marcadas literalmente |
| 8 | `unused-ignore` removido | ✅ | `# type: ignore[attr-defined]` retirado de `test_ac10_new_attributes_cannot_be_added` |
| 9 | Quatro comandos limpos ao final | ✅ | `ruff check .`, `ruff format --check .`, `mypy`, `pytest` — todos limpos, 157/157 |
| 10 | Três commits novos nesta ordem, `git status --porcelain` vazio ao final | ✅ | `d06880b`, `354382b`, `3877064` |
| 11 | `seugado/core/models.py` inalterado | ✅ | `git log --oneline -- seugado/core/models.py` → só `73ff3af` |
| 12 | Nenhum doc `00`–`12` no commit do bloco 3 | ✅ | `git show --stat 3877064` não lista nenhum |

## Execução
- `ruff check .` → All checks passed!
- `ruff format --check .` → 8 files already formatted
- `mypy` → Success: no issues found in 8 source files
- `pytest` → 157 passaram, 0 falharam, 0 pulados

### Como os 18 erros de mypy foram resolvidos
| Arquivo:linha (original) | Código | Tratamento |
|---|---|---|
| `tests/core/test_models.py:54` | `misc` | `# type: ignore[misc]` com comentário — mutação em dataclass frozen; não há narrowing possível, o teste existe justamente para provar que a atribuição levanta em runtime |
| `tests/core/test_models.py:66` | `index` | `assert p.geometria_geojson is not None` antes de indexar |
| `test_spec_001_models.py:140` | `no-untyped-def` | `_sample(name: str) -> typing.Any` |
| `test_spec_001_models.py:173` | `no-untyped-call` | `builders: dict[str, typing.Callable[[], typing.Any]]` anotado |
| `test_spec_001_models.py:186` | `union-attr` | `assert node.module is not None` |
| `test_spec_001_models.py:261` | `comparison-overlap` | ignore exigido pelo runbook (identidade `Confianca is not QualidadeBase`) |
| `test_spec_001_models.py:273` (×2) | `union-attr` | `typing.cast(typing.Any, cls).__dataclass_params__` — `__dataclass_params__` existe em runtime mas não está no protocolo `DataclassInstance` do typeshed; narrowing não se aplica, cast é a correção padrão para essa lacuna conhecida do stub |
| `test_spec_001_models.py:309` | `union-attr` | `assert isinstance(s.target, ast.Name)` antes de `.id` |
| `test_spec_001_models.py:370` | `union-attr` | expressão condicional: nome só é lido para `FunctionDef`/`AsyncFunctionDef`; `Lambda` usa literal `"<lambda>"` — lista continua vazia hoje, comportamento do teste não muda |
| `test_spec_001_models.py:434` | `union-attr` | mesmo tratamento da linha 309 |
| `test_spec_001_models.py:462` | `unused-ignore` | comentário removido |
| `test_spec_001_models.py:510`, `511` | `comparison-overlap` | ignore exigido pelo runbook |
| `test_spec_001_models.py:536` | `attr-defined` | `assert isinstance(f.dias_preferenciais_manejo, list)` antes do `.append` — estreitamento verdadeiro em runtime (uma lista foi injetada de propósito) |
| `test_spec_001_models.py:537` | `comparison-overlap` | resolvido pelo mesmo `assert isinstance(..., list)` acima, sem precisar de ignore |

## Defeitos na implementação
Nenhum. `seugado/core/models.py` não foi tocado, conforme escopo do bloco 3.

## Achados fora da implementação
- **Contagem do runbook não bate com a natureza dos erros.** O bloco 3 descreve
  "`comparison-overlap` (4 ocorrências, `Confianca` vs `QualidadeBase`)". A contagem de 4
  está certa, mas só 3 ocorrências (linhas 261, 510, 511) são de fato `Confianca` vs
  `QualidadeBase`/string. A quarta (linha 537) é `tuple[int, ...]` vs `list[int]`, dentro de
  `test_finding_types_are_not_enforced_so_lists_slip_in` — não tem relação com `StrEnum`.
  Resolvi essa quarta ocorrência com `assert isinstance(..., list)` (estreitamento real,
  preferido pelo próprio runbook) em vez do comentário de ignore específico de `StrEnum`,
  já que aplicar o texto "`runtime equality is the documented behaviour`" a um caso de
  tupla/lista seria um comentário incorreto no código. Nenhuma asserção de teste mudou de
  valor esperado. Reportando por precaução, não é um bloqueio.
- **`__dataclass_params__` fora do protocolo `DataclassInstance` do typeshed.** Gap
  conhecido da stub padrão de `dataclasses` — o atributo existe em runtime mas não está
  tipado. Resolvido com `typing.cast`, ponto que pode valer uma nota na ADR-011 caso o Muse
  Code venha a testar `__dataclass_params__` em outra spec futuramente (mesmo padrão se
  repetirá).

## Critérios não verificáveis
Nenhum — todos os itens do runbook tinham arquivo, ferramenta e parâmetro disponíveis.
Bloco 6 (publicar no GitHub) não foi executado: é opcional e condicionado a pedido explícito
do usuário, que não ocorreu nesta execução.
