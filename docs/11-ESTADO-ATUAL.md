# Estado Atual — SeuGado

**Atualizado em:** 26/09/2026
**Fase:** MVP — **F-MVP-008 concluída**.
**Próxima:** **F-MVP-009 (Contratos do MVP — SPEC-009)**.

> **Painel Operacional Conciso.** Este documento é mantido exclusivamente pelo **Antigravity** após a conclusão e commit de cada fatia. Modelos no Claude Projects apenas o consultam como ponteiro rápido.
> Arquivo de memória, pesquisas detalhadas e handoffs passados vivem em `13-HISTORICO.md`. Decisões fechadas vivem em `12-REGISTRO-DE-DECISOES-ADR.md`.

---

## Situação do Repositório

- **Fundação & MVP:** F-000 até F-004, F-MVP-007 e F-MVP-008 concluídas e integradas.
- **Suíte de Testes:** **304 testes passando** (0 skipped, 0 falhas), `ruff` e `mypy --strict` 100% limpos.
- **Banco de Dados (Supabase):** Migrações `0001` e `0002` aplicadas, 9 cultivares populados, RLS habilitado (12 tabelas).
- **Últimos commits:** 
  - `3d3cef0` (F-MVP-007: modelos, payloads e projecao estendidos para MVP)
  - F-MVP-008 (SPEC-008: banco do MVP, migracao 0002, projecao DB e catalogo)

---

## Progresso das Fatias do MVP

| Fatia | Status | Resumo / Commit |
|---|---|---|
| F-000 a F-004 | ✅ concluídas | Fundação, domínio, regras e persistência inicial |
| **F-MVP-007 Eventos do MVP** | ✅ concluída | SPEC-007: OrigemPeso, AlturaMedida, Leitura raw, GeoJSON (281 testes) |
| **F-MVP-008 Banco do MVP** | ✅ **concluída** | SPEC-008: migração `0002_mvp.sql`, projeção DB, catálogo (304 testes) |
| **F-MVP-009 Contratos do MVP** | ⬜ **próxima** | SPEC-009: `contratos.py` e fixtures |
| F-MVP-010 Ingestão de satélite | ⬜ não iniciada | SPEC-010: Earth Engine HLS S30 |
| F-MVP-011 Clima e graus-dia | ⬜ não iniciada | SPEC-011: Open-Meteo histórico e previsão |
| F-MVP-012 Modelo SAFER | ⬜ não iniciada | SPEC-012: biomassa e evapotranspiração |
| F-MVP-013 Estado projetado | ⬜ não iniciada | SPEC-013: união de sensoriamento, clima e SAFER |
| F-MVP-014 API do núcleo | ⬜ não iniciada | SPEC-014: FastAPI, rotas e autenticação |

---

## Próximo Passo Imediato

- **Ação:** Entregar `specs/SPEC-009-contratos-mvp.md` para implementação pelo Muse Code.
- **A seguir:** Testar com `revisoes/KIT-ACEITE-009.md` e commitar como `F-MVP-009: ...`.
