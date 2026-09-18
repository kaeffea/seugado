# RELATÓRIO-FATIA-003 — SPEC-004 (regras de manejo em `core/regras.py`)
**Data:** 18/09/2026 · **Veredicto:** aprovada sem ressalvas

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | `ResolucaoParametros` existe como `@dataclass(frozen=True, slots=True)` com exatamente os dois campos do R1 | ✅ | `test_resolucao_parametros_dataclass_contract` |
| 2 | `resolver_parametros`, `apto_para_entrada`, `precisa_sair`, `urgencia`, `descanso_cumprido` existem com as assinaturas exatas | ✅ | `test_public_api_exact_match` |
| 3 | Caso canônico do worked-example reproduz os resultados esperados | ✅ | `test_canonical_worked_example`, `test_entry_exit_urgency_at_two_heights`, `test_descanso_uses_threshold` |
| 4 | Todas as funções públicas e o dataclass têm type hints completos | ✅ | `test_all_functions_and_dataclass_have_type_annotations`, `mypy --strict` limpo |
| 5 | Módulo importa exclusivamente de `seugado.core.models` e stdlib (`dataclasses`) | ✅ | `test_imports_whitelist` |
| 6 | `apto_para_entrada`, `precisa_sair`, `urgencia` levantam `ValueError` quando recebem bloco contínuo | ✅ | `test_hidden_case_3_continuo_block_raises_value_error`, `test_continuo_block_rejected_by_rotational_rules` |
| 7 | `resolver_parametros` nunca levanta exceção para blocos ausentes ou parciais | ✅ | `test_resolver_names_all_fields_when_entry_absent`, `test_hidden_case_1_partial_block_piata` |
| 8 | `pytest tests/core/test_regras.py` passa com zero falhas | ✅ | 7 passed isolado |
| 9 | Nenhuma dependência nova em `pyproject.toml` | ✅ | `git diff --stat -- pyproject.toml` vazio |
| 10 | Arquivo `regras.py` tem no máximo 300 linhas | ✅ | `test_file_length_under_300_lines` (96 linhas) |

## Casos ocultos (KIT-ACEITE-004)
- **Caso oculto 1 (Bloco parcial tipo Piatã):** Cultivar com entrada definida mas saída ausente devolve `parametros=None` e `faltantes=("altura_saida_cm",)` sem repassar bloco inutilizável (`test_hidden_case_1_partial_block_piata`).
- **Caso oculto 2 (Fronteira exata de descanso):** Validado com 21 dias da literatura (`descanso_cumprido(21, 21.0) == True`, `descanso_cumprido(0, 21.0) == False`) (`test_hidden_case_2_descanso_boundaries`).
- **Caso oculto 3 (Uso indevido de bloco contínuo):** As 3 funções rotacionais levantam `ValueError` sob método `CONTINUO` (`test_hidden_case_3_continuo_block_raises_value_error`).
- **Caso oculto 4 (Independência de ordem com múltiplos blocos):** Cultivar contendo blocos contínuo e rotacionado simultaneamente resolve o bloco correto em qualquer ordem de inserção (`test_hidden_case_4_multiple_blocks_order_independence`).

## Checagens estruturais
- `regras.py` tem 96 linhas (limite: 300) — ✅.
- Sem `__post_init__`, sem `__hash__` customizado, sem `__all__` — ✅ (`test_no_forbidden_class_features_in_regras`).
- Funções puras: sem I/O, sem estado global, sem acesso a banco ou data atual — ✅.
- `__init__.py` continuam vazios — ✅.

## Checagem de escopo
O Muse Code criou exclusivamente `src/seugado/core/regras.py` e `tests/core/test_regras.py`. Não tocou em `models.py`, `forragem.py`, `tests/conformance/`, `docs/`, `revisoes/` ou `specs/`.

## Ajustes pontuais do testador
- Ordenação de imports em `test_spec_004_regras.py` formatada pelo ruff (`uv run ruff check --fix . && uv run ruff format .`). Zero modificações na lógica de produção.

## Execução
- `ruff check .` → All checks passed!
- `ruff format --check .` → 14 files already formatted
- `mypy` → Success: no issues found in 14 source files
- `pytest` (suíte completa) → 215 passed in 3.43s
- `pytest tests/core/test_regras.py` (isolado) → 7 passed
- `pytest tests/conformance/test_spec_004_regras.py` (isolado) → 12 passed

## Defeitos na implementação
Nenhum defeito encontrado.
