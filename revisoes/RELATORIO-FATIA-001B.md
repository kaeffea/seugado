# RELATÓRIO-FATIA-001B — SPEC-002 (parâmetro por regime em `models.py`)
**Data:** 17/09/2026 · **Veredicto:** aprovada com ressalva

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | `MetodoPastejo` existe como `StrEnum` com exatamente dois membros: `CONTINUO = "continuo"`, `ROTACIONADO = "rotacionado"` | ✅ | `test_ac3_enum_is_strenum_with_exact_members[MetodoPastejo]`, `test_metodo_pastejo_has_two_members` |
| 2 | `ParametrosRegime` é `@dataclass(frozen=True, slots=True)` com exatamente os sete campos do R2, nessa ordem, nenhum com default | ✅ | `test_r3_r8_fields_match_spec_exactly[ParametrosRegime]`, `test_ac5_dataclass_is_frozen_and_slotted_at_runtime[ParametrosRegime]` |
| 3 | `Cultivar` não tem mais `altura_entrada_cm` nem `altura_saida_cm` | ✅ | leitura de `models.py:111-122`; `test_r3_r8_fields_match_spec_exactly[Cultivar]` |
| 4 | `Cultivar` tem `parametros_por_regime: tuple[ParametrosRegime, ...]` na posição do R3, sem default | ✅ | idem; `test_r4_cultivar_has_no_defaults` |
| 5 | `Cultivar` continua com zero defaults em qualquer campo | ✅ | `test_r4_cultivar_has_no_defaults`, `test_r4_cultivar_requires_every_parameter` |
| 6 | `Piquete` tem `metodo_pastejo: MetodoPastejo` na posição do R4, sem default | ✅ | `models.py:125-137`; `test_r3_r8_fields_match_spec_exactly[Piquete]` |
| 7 | `Fazenda`, `ComposicaoLote`, `Lote`, `Manejo`, `Evento` inalterados | ✅ | `test_r3_r8_fields_match_spec_exactly` (as cinco), byte-a-byte contra o dicionário `DATACLASSES` pré-existente |
| 8 | Os cinco enums pré-existentes (fora o novo) inalterados | ✅ | `test_ac3_enum_is_strenum_with_exact_members` (parametrizado) |
| 9 | Ordem de declaração das classes no arquivo bate com R5 | ✅ | `test_r9_declaration_order` |
| 10 | `models.py` continua com zero literais numéricos e zero dígitos em qualquer string | ✅ | `test_ac8_no_numeric_literal_in_module`, `test_ac8_no_digits_in_string_constants`; `grep` manual confirmatório |
| 11 | `models.py` continua abaixo de 300 linhas | ✅ | `test_style_file_under_300_lines` (191 linhas) |
| 12 | `tests/core/test_models.py` atualizado por R6; `pytest tests/core/test_models.py` passa com zero falhas | ✅ | 10 passed, isolado (`uv run pytest tests/core/test_models.py`) |
| 13 | Nenhuma dependência nova em `pyproject.toml` | ✅ | `git diff --stat -- pyproject.toml` vazio |
| 14 | Nenhum import novo em `models.py` além do que já importava | ✅ | `test_ac1_imports_only_stdlib_whitelist` — conjunto permanece `{dataclasses, datetime, enum, typing, uuid}` |

## Caso oculto (ADR-011)
- `Cultivar` com `parametros_por_regime=()` constrói sem exceção, `len(...) == 0`, e continua `frozen` — `test_ac2_cultivar_accepts_zero_regime_blocks` (adicionado nesta verificação).
- Lista em vez de tupla não é rejeitada em runtime — `test_finding_cultivar_accepts_list_instead_of_tuple_for_regimes` (achado, registrado, não motivo de reprovação).

## Checagens estruturais (ADR-011)
- Imports de `models.py` seguem a lista branca (`dataclasses`, `datetime`, `enum`, `typing`, `uuid`); nada de `sensing/`, `planner/`, `api/` ou banco — ✅ (`test_ac1_imports_only_stdlib_whitelist`).
- `ParametrosRegime` segue o padrão exato das demais entidades: `@dataclass(frozen=True, slots=True)`, sem `__post_init__`, sem `__hash__` próprio, sem `__all__`, sem métodos — ✅ (`test_ac5_decorator_is_written_exactly_as_specified`, `test_ac7_no_methods_in_any_class`, `test_ac7_no_post_init_or_custom_hash_at_runtime`).
- `MetodoPastejo` tem exatamente dois membros com valores `"continuo"`/`"rotacionado"` (sem acento) — ✅.
- Nenhuma função pública nova em `models.py` além das sete entidades já existentes mais as duas novas — ✅ (`test_ac2_runtime_public_names_are_classes_or_imports_only`, `test_ac2_module_defines_exactly_the_thirteen_names` — agora quinze nomes).
- `__init__.py` de `src/seugado/`, `src/seugado/core/`, `tests/` e `tests/core/` continuam vazios — ✅ (`test_ac13_package_init_files_are_empty`).
- Zero literal numérico e zero dígito dentro de string (inclusive docstring) — ✅, confirmado por teste e por `grep -nE '"[^"]*[0-9][^"]*"' src/seugado/core/models.py` (sem ocorrências).
- `models.py` continua abaixo de trezentas linhas (191) — ✅.
- `tests/core/test_models.py` atualizado e `pytest tests/core/` passa sozinho (10 passed) — ✅.

## Checagem de escopo
`git diff --stat` (contra a árvore de trabalho, antes de qualquer commit) mostra **só**
`src/seugado/core/models.py` e `tests/core/test_models.py` no lado de produção. Nenhum arquivo
em `tests/conformance/`, `docs/`, `revisoes/` ou `specs/` foi tocado pelo Muse Code — sem sinal
de que ele viu o kit de aceite.

## Execução
- `ruff check .` → All checks passed!
- `ruff format --check .` → 8 files already formatted
- `mypy` → 2 erros, ambos em `tests/core/test_models.py` (ver Defeitos abaixo); zero erros em `src/`
- `pytest` (suíte completa) → 177 passed, 0 failed, 0 skipped
- `pytest tests/core/test_models.py` (isolado) → 10 passed
- `pytest tests/conformance/` (isolado) → 167 passed

## Defeitos na implementação
1. **`tests/core/test_models.py:160-161`** — `test_metodo_pastejo_has_two_members` compara
   `MetodoPastejo.CONTINUO == "continuo"` e `MetodoPastejo.ROTACIONADO == "rotacionado"` sem o
   comentário `# type: ignore[comparison-overlap]` exigido por `docs/06-ARQUITETURA-E-STACK.md`
   §7 regra 11 para esse padrão de comparação. `mypy` falha nessas duas linhas
   (`Non-overlapping equality check`). O padrão já existe corretamente em outros pontos do
   projeto (ex.: `tests/conformance/test_spec_001_models.py:262` e `:513-514`, que carregam o
   `type: ignore` com comentário explicativo). Correção não feita aqui — cabe a uma spec/patch
   sobre o teste, não a este relatório.

Nenhum defeito encontrado em `src/seugado/core/models.py`.

## Achados fora da implementação
Nenhum.

## Critérios não verificáveis
Nenhum. Todos os critérios da SPEC-002 puderam ser verificados diretamente.

## Suíte de conformidade
`tests/conformance/test_spec_001_models.py` foi atualizada no lugar, conforme instruído pelo
KIT-ACEITE-002: docstring do módulo ajustada para cobrir SPEC-001 e SPEC-002; `ENUMS` ganhou
`MetodoPastejo`; `DATACLASSES` ganhou `ParametrosRegime` e as novas formas de `Cultivar`/
`Piquete`; `_sample()` ganhou builder para `ParametrosRegime` e builders atualizados; contagem
de dataclasses passou de sete para oito; as duas chamadas posicionais de
`test_finding_piquete_hashability_depends_on_geometry` ganharam `MetodoPastejo.ROTACIONADO`.
Dois testes novos foram acrescentados para cobrir o caso oculto do tuple vazio e o achado de
lista aceita em runtime. `mypy` limpo em todo o arquivo após ajuste dos comentários
`type: ignore` nesses dois testes novos.
