# Relatório de Conformidade — SPEC-010 (Esqueleto API e Frontend)

**Data:** 26/09/2026  
**Fatia:** F-MVP-010 (Esqueleto API e Frontend)  
**Status:** ✅ APROVADA (8/8 critérios, 7/7 casos de conformidade)

---

## 1. Critérios de Aceite (SPEC-010)

| # | Critério | Status | Verificação |
|---|---|---|---|
| 1 | `api/deps.py` sem chamadas a `commit()` e fecha conexão no bloco `finally` | ✅ | `test_deps_py_no_commit_and_closed_in_finally` |
| 2 | Os 5 módulos de rota são stubs vazios contendo apenas docstring e instância de `APIRouter` | ✅ | `test_five_router_modules_are_empty_stubs` |
| 3 | `frontend/src/lib/tipos.ts` é idêntico byte-a-byte ao bloco de tipos da especificação | ✅ | `test_frontend_tipos_ts_matches_spec` |
| 4 | `npm run build` compila sem erros no frontend e sem dependências extras em `package.json` | ✅ | `test_frontend_package_json_dependencies` e build Vite/TypeScript validado |
| 5 | `exigir_fazenda` com fazenda divergente da do usuário retorna 403 ("Sem acesso a esta fazenda") | ✅ | `test_hidden_case_1_exigir_fazenda_403` |
| 6 | `usuario_atual` com header sem prefixo "Bearer " retorna 401 sem invocar `httpx.get` | ✅ | `test_hidden_case_2_usuario_atual_token_sem_bearer` |
| 7 | `GET /saude` funciona com código 200 mesmo quando `DATABASE_URL` está ausente do ambiente | ✅ | `test_hidden_case_3_saude_sem_database_url` |
| 8 | `ruff check .`, `ruff format --check .`, `mypy` e `pytest` 100% limpos e verdes | ✅ | 333 testes passando, 0 falhas, 0 skipped |

---

## 2. Cenários do Kit de Aceite (KIT-ACEITE-010)

- **Checagens Estruturais:**
  - `deps.py` gerencia conexão com `autocommit=False`, nunca chama `commit` e fecha a conexão em `finally` (`test_deps_py_no_commit_and_closed_in_finally`).
  - Stubs das 5 rotas (`rotas_fazenda.py`, `rotas_lotes.py`, `rotas_piquetes.py`, `rotas_plano.py`, `rotas_telegram.py`) sem endpoints reais de negócio (`test_five_router_modules_are_empty_stubs`).
  - `tipos.ts` no frontend validado com o bloco TypeScript da especificação (`test_frontend_tipos_ts_matches_spec`).
  - `package.json` estritamente limitado às dependências de precondição autorizadas (`test_frontend_package_json_dependencies`).
- **Casos Ocultos:**
  - **Caso Oculto 1:** `exigir_fazenda` com UUID não pertencente ao usuário levanta `HTTPException(403, detail="Sem acesso a esta fazenda")` (`test_hidden_case_1_exigir_fazenda_403`).
  - **Caso Oculto 2:** Header `Authorization` inválido ("Token abc") rejeita imediatamente com 401 sem disparar requisição HTTP (`test_hidden_case_2_usuario_atual_token_sem_bearer`).
  - **Caso Oculto 3:** Endpoint de liveness `/saude` não toca no banco e responde `{"ok": true}` (200) sem `DATABASE_URL` (`test_hidden_case_3_saude_sem_database_url`).

---

## 3. Ajustes do Testador (Antigravity)

1. **Precondição do Repositório:**
   - Scaffold do Vite `react-ts` em `frontend/` com pacotes necessários instalados e validados.
   - Adicionadas dependências no backend (`fastapi`, `uvicorn[standard]`, `httpx`, `earthengine-api`) e override no `pyproject.toml` para `ee`.
2. **Suíte de Conformidade Independente:**
   - Criada `tests/conformance/test_spec_010_api_frontend.py` (7 testes cobrindo todas as cláusulas do KIT-ACEITE-010).

---

## 4. Execução da Suíte

- `ruff check .` → All checks passed!
- `ruff format --check .` → 43 files already formatted
- `mypy` → Success: no issues found in 42 source files
- `pytest` → **333 passed** em 22.04s (0 failed, 0 skipped)
- `frontend build` → `tsc -b && vite build` concluído com sucesso em 3.58s
