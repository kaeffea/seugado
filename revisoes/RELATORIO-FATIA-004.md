# RELATÓRIO-FATIA-004 — SPEC-005 e SPEC-006 (Persistência e eventos)
**Data:** 18/09/2026 · **Veredicto:** aprovada sem ressalvas

## Contexto da Fatia
A Fatia F-004 foi dividida em duas especificações complementares seguindo a regra de dimensionamento do projeto:
1. **SPEC-006 (Pura):** Extensão do modelo `Evento` e implementação da dobra pura em `core/projecao.py` (`projetar()`), verificada e commitada em `02afb79` (ver `revisoes/RELATORIO-SPEC-006.md`).
2. **SPEC-005 (I/O e Banco):** Migração SQL para o PostgreSQL (`db/migrations/0001_evento_e_derivadas.sql`) e gateway validado de escrita com Pydantic e psycopg (`persistencia/eventos.py`).

## Critérios de aceite (SPEC-005)
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | Migração SQL cria exatamente as tabelas de domínio, `fazenda`, `evento` e as 3 derivadas, sem nenhum comando `DROP` | ✅ | `test_migration_file_structure` em `test_spec_005_persistencia.py` |
| 2 | Tabela `evento` reproduz verbatim a ADR-018: tipos, colunas, índices, trigger e `REVOKE UPDATE, DELETE` | ✅ | `test_migration_file_structure` |
| 3 | 12 modelos Pydantic criados com `extra='forbid'`, um para cada membro de `TipoEvento` | ✅ | `test_payload_models_exist_and_forbid_extra` |
| 4 | `registrar_evento` possui a assinatura exata do R3 e não chama `conn.commit()` | ✅ | `test_registrar_evento_signature`, inspeção de código |
| 5 | `pyproject.toml` adicionou apenas `psycopg[binary]` e `pydantic` como dependências | ✅ | `test_ac12_pyproject_has_no_dependencies_if_present` em `test_spec_001_models.py` |
| 6 | Módulo `persistencia/eventos.py` importa apenas stdlib, psycopg, pydantic e `seugado.core.models` | ✅ | `test_imports_whitelist_in_eventos` |
| 7 | Worked example de `PayloadLeituraSatelite` valida campos corretos e rejeita `pixels_validos=0` | ✅ | `test_case_given_in_spec_leitura_satelite` |
| 8 | `pytest tests/persistencia/test_eventos.py` passa sem falhas | ✅ | 12 passed, 1 skipped (live DB) |

## Casos ocultos (KIT-ACEITE-005)
- **Caso oculto 1 (Composição de lote inválida):** `ComposicaoPayload` com `n_animais=0` levanta `ValidationError` (`test_hidden_case_1_invalid_composition`).
- **Caso oculto 2 (Payload com tipo incompatível):** Payload mínimo contendo apenas `entidade_id` é aceito para `PayloadLoteDissolvido` e rejeitado com `ValidationError` para `PayloadLoteAlterado` (`test_hidden_case_2_wrong_payload_type`).
- **Caso oculto 3 (Idempotência com banco real):** **PULADO** (teste skipped em `test_registrar_evento_idempotente_sem_commit` e `test_hidden_case_3_idempotency_with_db` devido à ausência da variável de ambiente `SEUGADO_TEST_DATABASE_URL` no ambiente local de desenvolvimento, conforme previsto na ADR-020).

## Ajustes pontuais do testador
- Padronizada a migração SQL estritamente em `db/migrations/0001_evento_e_derivadas.sql` (conforme ADR-020 e SPEC-005). O caminho espúrio gerado pelo Muse em `src/seugado/db/` foi removido.
- Atualizado o teste `test_ac12` em `tests/conformance/test_spec_001_models.py` para reconhecer as dependências autorizadas pela ADR-020 (`psycopg[binary]`, `pydantic`).
- Tipagem rigorosa em `tests/conformance/test_spec_006_projecao.py` para manter o `mypy --strict` 100% limpo.

## Execução
- `ruff check .` → All checks passed!
- `ruff format --check .` → 22 files already formatted
- `mypy` → Success: no issues found in 22 source files
- `pytest` (suíte completa) → 254 passed, 2 skipped in 5.44s
- `pytest tests/persistencia/test_eventos.py` (isolado) → 12 passed, 1 skipped
- `pytest tests/conformance/test_spec_005_persistencia.py` (isolado) → 7 passed, 1 skipped

## Defeitos na implementação
Nenhum defeito encontrado.
