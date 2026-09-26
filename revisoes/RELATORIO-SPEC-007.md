# Relatório de Conformidade — SPEC-007 (Eventos MVP)

**Data:** 26/09/2026
**Fatia:** F-MVP-007 (Eventos MVP)
**Status:** ✅ APROVADA (10/10 critérios, 12/12 casos de conformidade)

---

## 1. Critérios de Aceite (SPEC-007)

| # | Critério | Status | Verificação |
|---|---|---|---|
| 1 | `OrigemPeso` existe com exatamente dois membros (`PRODUTOR`, `UA_TABELA`) | ✅ | `test_origem_peso_enum` |
| 2 | `ComposicaoLote` tem `origem_peso` como último campo, default `OrigemPeso.PRODUTOR` | ✅ | `test_composicao_lote_origem_peso_field` |
| 3 | `TipoEvento.ALTURA_MEDIDA.value == "altura_medida"` (13º membro) | ✅ | `test_tipo_evento_thirteen_members_altura_medida_last` |
| 4 | `combinar_confianca` retorna o mínimo na ordem baixa/média/alta e levanta `ValueError` sem argumentos | ✅ | `test_ordem_confianca_dict_and_combinar_confianca` |
| 5 | `PAYLOAD_POR_TIPO` possui 13 entradas, mapeia `ALTURA_MEDIDA` e todos modelos com `extra="forbid"` | ✅ | `test_payload_por_tipo_thirteen_entries_extra_forbid` |
| 6 | `PayloadLeituraSatelite` possui exatamente os 9 campos do R3.4 e sem `massa_kg_ms_ha` | ✅ | `test_payload_leitura_satelite_fields` |
| 7 | `projetar` expõe `alturas`, novo formato de `Leitura` e `geometria_geojson` em `EstadoPiquete` | ✅ | `test_canonical_worked_example` |
| 8 | `manejo_divergente` move o lote para `piquete_real_id` e descansa o piquete anterior | ✅ | `test_canonical_worked_example` |
| 9 | `ruff check`, `mypy` e `pytest` 100% limpos e verdes | ✅ | Verificação completa das suítes |
| 10 | Nenhuma dependência nova em `pyproject.toml` | ✅ | Verificado via Git |

---

## 2. Cenários do Kit de Aceite (KIT-ACEITE-007)

- **Caso Canônico:** P2 ocupado por L1 desde 24/09; P1 descansando; altura 28,0 cm; peso total derivado corretamente (`test_canonical_worked_example`).
- **Caso Oculto 1 (Combinação de confiança):** `combinar_confianca(BAIXA, ALTA)` → `BAIXA` (`test_hidden_case_1_combinar_confianca_baixa_alta`).
- **Caso Oculto 2 (Substituição temporal de altura):** Duas `altura_medida` no mesmo piquete, 20/09 (30 cm) e 18/09 (25 cm) gravadas nessa ordem → permanece a medição mais recente no tempo (30 cm) (`test_hidden_case_2_altura_medida_latest_date_wins`).
- **Caso Oculto 3 (Atualização de geometria):** `piquete_alterado` com nova geometria atualiza `geometria_geojson` em `EstadoPiquete` (`test_hidden_case_3_piquete_alterado_geometria_nova`).
- **Caso Oculto 4 (Validação GeoJSON):** Geometria com tipo inválido (`Point`) ou anel com menos de 4 coordenadas levanta `ValidationError` (`test_hidden_case_4_payload_point_geometry_validation_error`).
- **Caso Oculto 5 (Ajuste intencional de conformidade legada):** Suítes `test_spec_001_models.py`, `test_spec_004_regras.py`, `test_spec_005_persistencia.py` e `test_spec_006_projecao.py` atualizadas para refletir as decisões intencionais das ADRs 022–024.

---

## 3. Ajustes do Testador (Antigravity)

1. **Correções de Linter em scripts:**
   - Corrigidos imports e limite de linha em `scripts/testar_gee.py`.
2. **Atualização da Suíte de Conformidade:**
   - Criada a suíte independente `tests/conformance/test_spec_007_eventos_mvp.py` (12 testes).
   - Ajustados os contratos legados de teste que verificavam contagens antigas (12 membros de evento, 5 funções em regras, etc.).

---

## 4. Execução da Suíte

- `ruff check .` → All checks passed!
- `ruff format --check .` → 24 files already formatted
- `mypy` → Success: no issues found in 23 source files
- `pytest` → **281 passed, 2 skipped** (testes de banco real pulados sem `SEUGADO_TEST_DATABASE_URL`)
