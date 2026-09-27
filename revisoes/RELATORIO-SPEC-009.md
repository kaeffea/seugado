# Relatório de Conformidade — SPEC-009 (Contratos do MVP)

**Data:** 26/09/2026  
**Fatia:** F-MVP-009 (Contratos do MVP)  
**Status:** ✅ APROVADA (8/8 critérios, 13/13 casos de conformidade)

---

## 1. Critérios de Aceite (SPEC-009)

| # | Critério | Status | Verificação |
|---|---|---|---|
| 1 | Todas as 9 dataclasses existem, frozen e slotted, na ordem exata de campos especificada | ✅ | `test_all_dataclasses_frozen_slotted_no_methods`, `test_piquete_projetado_field_order`, `test_lote_projetado_field_order`, `test_plano_manejo_field_order` |
| 2 | `TipoAlerta` possui exatamente os 8 membros e valores especificados | ✅ | `test_tipo_alerta_members` |
| 3 | `estado_de_dict(json.load(estado_projetado_exemplo.json))` retorna 8 piquetes e 2 lotes | ✅ | `test_canonical_estado_projetado_fixture_roundtrip` |
| 4 | `plano_de_dict(json.load(plano_exemplo.json))` retorna 3 movimentações, 3 alertas, 1 pedido e 8 resumos | ✅ | `test_canonical_plano_exemplo_fixture_roundtrip` |
| 5 | Ambas as fixtures fazem round-trip bidirecional idêntico ao JSON de origem | ✅ | `test_canonical_estado_projetado_fixture_roundtrip` e `test_canonical_plano_exemplo_fixture_roundtrip` |
| 6 | Módulo não importa nada de `sensing/`, `planner/`, `api/`, `delivery/` ou bibliotecas de banco/serialização externa | ✅ | `test_forbidden_imports` |
| 7 | `ruff check .`, `ruff format --check .`, `mypy` e `pytest` 100% limpos e verdes | ✅ | 321 testes passando, 0 falhas, 0 skipped |
| 8 | Nenhuma nova dependência adicionada ao `pyproject.toml` | ✅ | Confirmado via `git status` |

---

## 2. Cenários do Kit de Aceite (KIT-ACEITE-009)

- **Checagens Estruturais:**
  - 9 dataclasses com `@dataclass(frozen=True, slots=True)`, sem métodos e sem coleções mutáveis (`list`/`dict`) nos atributos tipados (`test_all_dataclasses_frozen_slotted_no_methods`).
  - Ordem exata de campos para `PiqueteProjetado`, `LoteProjetado` e `PlanoManejo` (`test_piquete_projetado_field_order`, `test_lote_projetado_field_order`, `test_plano_manejo_field_order`).
  - `TipoAlerta` com 8 membros e valores string exatos (`test_tipo_alerta_members`).
  - Arquivo dentro do limite de 300 linhas (267 linhas) (`test_file_under_300_lines`).
  - Nenhuma dependência externa ou proibida (`test_forbidden_imports`).
- **Caso Canônico:** Ambas as fixtures (`estado_projetado_exemplo.json` e `plano_exemplo.json`) carregam e fazem round-trip exato (dict → dataclass → dict == original), e `json.dumps` é executado com sucesso (`test_canonical_estado_projetado_fixture_roundtrip`, `test_canonical_plano_exemplo_fixture_roundtrip`).
- **Caso Oculto 1 (Datetime ingênuo sem fuso):** `plano_de_dict` com `data_geracao="2026-09-28T08:00:00"` levanta `ValueError` mencionando naive (`test_hidden_case_1_plano_de_dict_naive_datetime`).
- **Caso Oculto 2 (Enum desconhecido em alerta):** `plano_de_dict` com `"tipo": "inexistente"` em alerta levanta `ValueError` (`test_hidden_case_2_plano_de_dict_unknown_enum_in_alerta`).
- **Caso Oculto 3 (Chave faltante em estado):** `estado_de_dict` sem a chave `lotes` levanta `ValueError` mencionando `lotes` (`test_hidden_case_3_estado_de_dict_missing_lotes_key`).
- **Caso Oculto 4 & 5 (UUID e Data malformados):** Strings inválidas de UUID e data levantam `ValueError` (`test_malformed_uuid_and_date`).

---

## 3. Ajustes do Testador (Antigravity)

1. **Refatoração Concisa em `contratos.py`:**
   - Implementado deserializador genérico e serializador funcional, eliminando duplicações de construtores manuais repetitivos e garantindo que o arquivo permaneça estritamente formatado pelo `ruff format` em 267 linhas (abaixo do limite de 300 linhas).
   - Suporte estrito para validação de UTC timezone-aware em `datetime`, rejeição de campos faltantes com nomes de chaves e tratamento de enums desconhecidos.
2. **Suíte de Conformidade Independente:**
   - Criada `tests/conformance/test_spec_009_contratos.py` (13 testes cobrindo todas as cláusulas do KIT-ACEITE-009).

---

## 4. Execução da Suíte

- `ruff check .` → All checks passed!
- `ruff format --check .` → 33 files already formatted
- `mypy` → Success: no issues found in 32 source files
- `pytest` → **321 passed** em 18.91s (0 failed, 0 skipped)
