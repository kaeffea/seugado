# Relatório de Conformidade — SPEC-014A (Auxiliares do Estado)

**Data:** 27/09/2026  
**Fatia:** F-MVP-014A (Auxiliares do Estado)  
**Status:** ✅ APROVADA (8/8 critérios, 10/10 casos de conformidade)

---

## 1. Critérios de Aceite (SPEC-014A)

| # | Critério | Status | Verificação |
|---|---|---|---|
| 1 | `planner/estado.py` importa apenas stdlib e `seugado.core` (sem DB, sensing, persistencia, api) | ✅ | `test_estado_py_forbidden_imports` |
| 2 | `CONSUMO_FRACAO_PV`, `UA_POR_CATEGORIA`, `UNIDADE_ANIMAL_KG` definidos exatamente | ✅ | `test_constants_values` |
| 3 | `peso_por_ua_kg`, `consumo_lote`, `confianca_peso`, `avancar_massa_um_dia`, `confianca_estimativa` existem | ✅ | `test_expected_symbols_exist` |
| 4 | `planner/carga.py` não foi criado nesta etapa | ✅ | `test_carga_py_does_not_exist_yet` |
| 5 | Casos canônicos resolvidos da spec (337,5 kg; 1113,75 kg/dia; 2038,04 kg/ha; régua de 20 dias) | ✅ | `test_canonical_worked_examples` |
| 6 | Todos os casos ocultos do KIT-ACEITE-014A validados | ✅ | `test_hidden_case_1_*` até `test_hidden_case_5_*` |
| 7 | Validações de domínio (`area_ha <= 0`, `eficiencia_pastejo` fora de `(0, 1]`) levantam `ValueError` | ✅ | `test_avancar_massa_validations` |
| 8 | `ruff check .`, `ruff format --check .`, `mypy` e `pytest` 100% limpos e verdes | ✅ | 352 testes passando, 0 falhas, 0 skipped |

---

## 2. Cenários do Kit de Aceite (KIT-ACEITE-014A)

- **Checagens Estruturais:**
  - `planner/estado.py` livre de imports proibidos (`psycopg`, `httpx`, `ee`, `sensing`, `persistencia`, `api`) (`test_estado_py_forbidden_imports`).
  - Constantes com valores canônicos: `UNIDADE_ANIMAL_KG = 450.0`, `CONSUMO_FRACAO_PV` (0.024 / 0.022 / 0.024) e `UA_POR_CATEGORIA` (0.25 / 0.75 / 1.00) (`test_constants_values`).
  - `planner/carga.py` ausente (`test_carga_py_does_not_exist_yet`).
- **Casos Canônicos:**
  - Fallback novilho: 0.75 × 450 = 337,5 kg (`test_canonical_worked_examples`).
  - Consumo 150 novilhos: 150 × 337,5 × 0.022 = 1113,75 kg MS/dia (`test_canonical_worked_examples`).
  - Avanço de massa 1 dia: 2420 + 60 − 1113.75 / (0.72 × 3.5) = 2038,04 kg MS/ha (`test_canonical_worked_examples`).
  - Confiança da estimativa com imagem recente (3d), pixels suficientes (40), régua de 20 dias e posição confirmada → `Confianca.MEDIA`, frase "última medição de altura há 20 dias" (`test_canonical_worked_examples`).
- **Casos Ocultos:**
  - **Caso 1 (Sem consumo):** Piquete sem lote (`consumo == 0.0`, `eficiencia == None`) avança exatamente `massa + taxa` (2000 + 50 = 2050) (`test_hidden_case_1_avancar_massa_sem_consumo`).
  - **Caso 2 (Piso zero):** Desaparecimento maior que o estoque trunca em `0.0` kg MS/ha (`test_hidden_case_2_avancar_massa_floor_zero`).
  - **Caso 3 (Sem imagem de satélite):** Imagem e pixels `None` resultam em `Confianca.BAIXA` com frase "nenhuma imagem de satélite sem nuvem nos últimos 30 dias" (`test_hidden_case_3_confianca_sem_imagem_satelite`).
  - **Caso 4 (Imagem de hoje):** `dias_desde_imagem == 0` formata "última imagem de satélite sem nuvem de hoje" (`test_hidden_case_4_confianca_imagem_de_hoje`).
  - **Caso 5 (Confiança de peso mista):** Composição com pelo menos um item via `UA_TABELA` rebaixa para `Confianca.MEDIA` com frase da tabela de UA (`test_hidden_case_5_confianca_peso_mista`).

---

## 3. Execução da Suíte

- `ruff check .` → All checks passed!
- `ruff format --check .` → 46 files already formatted
- `mypy` → Success: no issues found in 45 source files
- `pytest` → **352 passed** em 32.69s (0 failed, 0 skipped)
