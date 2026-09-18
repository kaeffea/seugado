# RELATÓRIO-SPEC-006 — Projeção pura de eventos (`core/projecao.py`)
**Data:** 18/09/2026 · **Veredicto:** aprovada sem ressalvas

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | `Evento` em `core/models.py` estendido exclusivamente com `sequencia: int` e `corrige_evento_id: UUID | None = None` | ✅ | `test_r3_r8_fields_match_spec_exactly[Evento]` em `test_spec_001_models.py` |
| 2 | `SituacaoPiquete` existe como `StrEnum` com membros `OCUPADO` e `DESCANSANDO` | ✅ | `test_situacao_piquete_enum` |
| 3 | `EstadoPiquete`, `EstadoLote`, `Leitura`, `EstadoFazenda` são `@dataclass(frozen=True, slots=True)` | ✅ | `test_dataclasses_frozen_and_slotted` |
| 4 | `EstadoPiquete` tem exatamente os 11 campos da spec (sem `massa_kg_ms_ha` nem `aguardando_parametro`) | ✅ | `test_estado_piquete_fields_exact` |
| 5 | `projetar` assina exatamente `projetar(eventos: Sequence[Evento]) -> EstadoFazenda` | ✅ | `test_projetar_signature` |
| 6 | Nenhuma função pública além de `projetar` em `core/projecao.py` | ✅ | `test_public_api_exact_match` |
| 7 | Módulo importa apenas stdlib e `seugado.core.models` | ✅ | `test_imports_whitelist` |
| 8 | Arquivo `core/projecao.py` possui no máximo 300 linhas | ✅ | `test_file_length_under_300_lines` (273 linhas) |
| 9 | Caso canônico de projeção com 3 eventos reproduz o estado esperado | ✅ | `test_canonical_case`, `test_canonical_three_event_fold` |
| 10 | Correção com `corrige_evento_id` aplica na posição temporal do evento original | ✅ | `test_correction_case_applies_at_original_position`, `test_correction_at_original_position_wins` |
| 11 | `pytest tests/core/test_projecao.py` passa com zero falhas | ✅ | 5 passed isolado |

## Casos ocultos (KIT-ACEITE-006)
- **Caso oculto 1 (Dissolução durante ocupação):** `lote_dissolvido` remove o lote e faz o piquete transicionar para `DESCANSANDO` com data e descanso zerado na referência (`test_hidden_case_1_dissolucao_durante_ocupacao`, `test_dissolution_frees_piquete_with_rest_days`).
- **Caso oculto 2 (Duas correções independentes):** Dois eventos de correção para dois piquetes distintos aplicam nas posições corretas sem interferência mútua (`test_hidden_case_2_two_independent_corrections`).
- **Caso oculto 3 (Entidade inexistente):** Referência a lote ou piquete desconhecido em eventos posteriores levanta `ValueError` (`test_hidden_case_3_reference_to_unknown_entity_raises`, `test_validation_errors`).
- **Caso oculto 4 (Eventos sem efeito de projeção):** Eventos como `parametro_alterado` e `foto_validacao` são consumidos sem quebrar e sem poluir o estado derivado (`test_hidden_case_4_events_without_effect_pass_through`, `test_latest_reading_wins_and_r7_skipped`).

## Ajustes pontuais do testador
- Adicionado `# noqa: PLR0912, PLR0913, PLR0917` no helper interno `_aplicar` de `core/projecao.py` (função de dispatch com `match/case` por tipo de evento).
- Atualizado o fixture do `Evento` em `tests/core/test_models.py` e os esquemas em `tests/conformance/test_spec_001_models.py` para incluir o campo obrigatório `sequencia=1`.
- Formatado o código com `uv run ruff format .`.

## Execução
- `ruff check .` → All checks passed!
- `ruff format --check .` → 17 files already formatted
- `mypy` → Success: no issues found in 17 source files
- `pytest` (suíte completa) → 235 passed in 2.55s
- `pytest tests/core/test_projecao.py` (isolado) → 5 passed
- `pytest tests/conformance/test_spec_006_projecao.py` (isolado) → 7 passed

## Defeitos na implementação
Nenhum defeito encontrado.
