# Relatório de Conformidade — SPEC-008 (Banco MVP)

**Data:** 26/09/2026  
**Fatia:** F-MVP-008 (Banco do MVP)  
**Status:** ✅ APROVADA (8/8 critérios, 10/10 casos de conformidade)

---

## 1. Critérios de Aceite (SPEC-008)

| # | Critério | Status | Verificação |
|---|---|---|---|
| 1 | `0002_mvp.sql` aplica limpo após `0001` no Supabase em transação única (`BEGIN; … COMMIT;`) | ✅ | Aplicado e validado ao vivo |
| 2 | Após migração, `SELECT count(*) FROM cultivar` retorna exatamente 9 | ✅ | `test_cultivar_table_count_and_slugs` |
| 3 | RLS habilitado nas 12 tabelas públicas e nenhuma política criada (`count(*) == 0`) | ✅ | `test_rls_enabled_and_zero_policies` |
| 4 | `reconstruir_projecao` grava exatamente 1 linha em `estado_piquete` por piquete projetado com geometria PostGIS válida (`ST_IsValid`) e sem `commit` | ✅ | `test_canonical_reconstruir_projecao_persists_expected_state` & `test_hidden_case_4_reconstruir_idempotente_postgis_geometria` |
| 5 | `carregar_catalogo(conn, None)["<marandu id>"].densidade_kg_ha_por_cm == 110` | ✅ | `test_marandu_densidade_catalog` |
| 6 | `faltantes_calibracao(mombaca, ROTACIONADO) == ("densidade_kg_ha_por_cm", "rue_max_g_por_mj", "eficiencia_pastejo")` | ✅ | `test_mombaca_faltantes_rotacionado` |
| 7 | `ruff check .`, `ruff format --check .`, `mypy` e `pytest` 100% limpos e verdes | ✅ | 304 testes passando, 0 skipped, 0 falhas |
| 8 | Nenhuma nova dependência adicionada ao `pyproject.toml` | ✅ | Confirmado via `git status` |

---

## 2. Cenários do Kit de Aceite (KIT-ACEITE-008)

- **Checagens Estruturais:**
  - `0002_mvp.sql` envolto em `BEGIN; … COMMIT;`; não altera `0001` (`test_migration_0002_wrapped_in_transaction`).
  - 12 tabelas com RLS habilitado e 0 policies em `public` (`test_rls_enabled_and_zero_policies`).
  - 9 cultivares com slugs exatos: marandu, mombaca, tanzania, zuri, massai, tamani, xaraes, piata, decumbens (`test_cultivar_table_count_and_slugs`).
  - `reconstruir_projecao` e `carregar_catalogo` não invocam `commit` nem `rollback` via AST (`test_no_commit_or_rollback_in_projecao_db_and_catalogo`).
  - Nenhuma interpolação f-string de SQL com dados (`test_no_fstring_sql_execution`).
- **Caso Canônico:** Xaraés com overrides de entrada (35 cm) e saída (18 cm), resultando em bloco rotacionado calibrado (`confianca=BAIXA`, `fonte="produtor:<fazenda_id>"`) e zero faltantes (`test_canonical_xaraes_overrides_worked_example`).
- **Caso Oculto 1 (Override parcial Marandu):** Override de entrada 28 cm em pastejo rotacionado preserva saída 15 cm da literatura, atribuindo `confianca=BAIXA` e fonte do produtor, mantendo bloco contínuo intacto (`test_hidden_case_1_marandu_partial_override`).
- **Caso Oculto 2 (Faltantes Marandu):** `faltantes_calibracao(marandu, CONTINUO) == ()` e `faltantes_calibracao(marandu, ROTACIONADO) == ()` (`test_hidden_case_2_marandu_faltantes_empty`).
- **Caso Oculto 3 (Faltantes Piatã contínuo):** `faltantes_calibracao(piata, CONTINUO) == ("densidade_kg_ha_por_cm",)` (`test_hidden_case_3_piata_faltantes_continuo`).
- **Caso Oculto 4 (Idempotência e Geometria PostGIS):** Criação de fazenda + piquete via `registrar_evento`, duas chamadas a `reconstruir_projecao` resultam em exatamente 1 linha em `estado_piquete` com `ST_IsValid(geometria)` verdadeiro (`test_hidden_case_4_reconstruir_idempotente_postgis_geometria`).

---

## 3. Ajustes do Testador (Antigravity)

1. **Execução de Migrações no Banco Supabase:**
   - As migrações `0001_evento_e_derivadas.sql` e `0002_mvp.sql` foram aplicadas com sucesso no banco remoto do Supabase.
   - Estado de cultivares (9 registros) e integridade do PostGIS foram validados diretamente na base.
2. **Correção em Teste Unitário:**
   - Em `tests/persistencia/test_projecao_db.py`, corrigida tentativa de exclusão direta de evento em `test_reconstruir_fazenda_vazia_limpa_derivadas`, respeitando o trigger `trg_impedir_alteracao_evento` (append-only).
3. **Carregamento Automático do Ambiente em Testes:**
   - Adicionado `tests/conftest.py` para carregar `SEUGADO_TEST_DATABASE_URL` automaticamente a partir do `.env` local, eliminando testes pulados (`0 skipped`).
4. **Suíte de Conformidade Independente:**
   - Criada `tests/conformance/test_spec_008_banco_mvp.py` (10 testes cobrindo todas as cláusulas do KIT-ACEITE-008).

---

## 4. Execução da Suíte

- `ruff check .` → All checks passed!
- `ruff format --check .` → 30 files already formatted
- `mypy` → Success: no issues found in 29 source files
- `pytest` → **304 passed** em 18.90s (0 failed, 0 skipped)
