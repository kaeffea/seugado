# RELATÓRIO-FATIA-002 — SPEC-003 (cálculos de forragem em `core/forragem.py`)
**Data:** 17/09/2026 · **Veredicto:** aprovada sem ressalvas

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | `massa_para_altura`, `altura_para_massa`, `consumo_lote_kg_ms_dia`, `dias_ocupacao`, `taxa_utilizacao`, `consumo_individual_kg_ms_dia` e `consumo_pct_pv` existem com as assinaturas exatas da spec | ✅ | `test_public_api_exact_match` |
| 2 | `massa_para_altura` e `altura_para_massa` são inversas exatas para qualquer densidade positiva | ✅ | `test_mass_height_are_exact_inverses`, `test_hidden_case_2_exact_inverses_differing_densities` |
| 3 | Caso de regressão canônico (`05`) reproduz `consumo_individual_kg_ms_dia ≈ 11.62` (±0.05), `consumo_pct_pv ≈ 2.42` (±0.02) e `taxa_utilizacao ≈ 0.44` (±0.01) | ✅ | `test_canonical_case_reproduces_expected_values`, `test_canonical_regression_case` |
| 4 | `dias_ocupacao` reproduz ≈ 4.0 dias (±0.05) a partir dos dados do caso canônico | ✅ | `test_canonical_case_reproduces_expected_values`, `test_canonical_regression_case` |
| 5 | `consumo_lote_kg_ms_dia` reproduz 6.6 para o exemplo da literatura (`[(1, 300.0, 0.022)]`) | ✅ | `test_consumo_lote_literature_example`, `test_consumo_lote_literature_and_multi_category` |
| 6 | `dias_ocupacao` retorna `float("inf")` quando o denominador com crescimento é `<= 0` | ✅ | `test_dias_ocupacao_returns_inf_when_growth_covers_intake`, `test_hidden_case_1_denominador_non_positive_returns_inf` |
| 7 | `consumo_lote_kg_ms_dia` retorna 0.0 para composição vazia sem levantar exceção | ✅ | `test_consumo_lote_empty_returns_zero`, `test_consumo_lote_literature_and_multi_category` |
| 8 | Todas as regras de validação levantam `ValueError` sob condição informada | ✅ | `test_validation_errors`, `test_hidden_case_3_and_validation_rules` |
| 9 | Todas as funções públicas possuem type hints completos em argumentos e retorno | ✅ | `test_all_functions_have_type_annotations`, `mypy --strict` limpo |
| 10 | Módulo não importa nada de `sensing/`, `planner/`, `api/`, `core.models` ou bibliotecas de banco | ✅ | `test_imports_whitelist` (único import: `collections.abc.Sequence`) |
| 11 | `pytest tests/core/test_forragem.py` passa com zero falhas | ✅ | 7 passed isolado |
| 12 | Nenhuma dependência nova em `pyproject.toml` | ✅ | `git diff --stat -- pyproject.toml` vazio |

## Casos ocultos (KIT-ACEITE-003)
- **Caso oculto 1 (Crescimento na taxa de acúmulo):** `massa_atual=3000.0`, `massa_residuo=2000.0`, `taxa_acumulo=50.0`, `area=10.0`, `eficiencia=0.8`, `consumo=4000.0` resultou em `2.2222` dias (±0.01), distinguindo da fórmula ingênua sem crescimento (`2.0`). Testado também denom <= 0 retornando `float("inf")` e massa <= resíduo retornando `0.0` (`test_hidden_case_1_*`).
- **Caso oculto 2 (Inversão exata em densidades variadas):** validado com densidades 250.0, 180.0 e 320.0 com precisão de máquina (`1e-9`) (`test_hidden_case_2_exact_inverses_differing_densities`).
- **Caso oculto 3 (Validação e distinção de fronteiras):** `consumo_lote_kg_ms_dia <= 0` levanta `ValueError` (distinto de 0.0 e de inf) (`test_hidden_case_3_and_validation_rules`).

## Checagens estruturais
- `forragem.py` tem 117 linhas (limite: 300) — ✅.
- Nenhuma das 7 funções possui valor default em parâmetros (Regra 1 / ADR-010: zero defaults para `densidade_kg_ha_por_cm` e `eficiencia_pastejo`) — ✅ (`test_no_default_arguments_on_any_function`).
- Funções puras: sem I/O, sem estado global, sem efeitos colaterais — ✅.
- `__init__.py` continuam vazios — ✅.

## Checagem de escopo
O Muse Code criou exclusivamente `src/seugado/core/forragem.py` e `tests/core/test_forragem.py`. Não tocou em `models.py`, `tests/conformance/`, `docs/`, `revisoes/` ou `specs/`.

## Ajustes pontuais do testador
- Adicionado `# noqa: PLR0913, PLR0917` na assinatura de `dias_ocupacao` (6 argumentos posicionais são contrato inalterável de `06` §3).
- Formatado o código com `uv run ruff format .` (sem alterações semânticas).

## Execução
- `ruff check .` → All checks passed!
- `ruff format --check .` → 11 files already formatted
- `mypy` → Success: no issues found in 11 source files
- `pytest` (suíte completa) → 196 passed in 2.49s
- `pytest tests/core/test_forragem.py` (isolado) → 7 passed
- `pytest tests/conformance/test_spec_003_forragem.py` (isolado) → 12 passed

## Defeitos na implementação
Nenhum defeito encontrado.
