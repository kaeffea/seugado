# Estado Atual — SeuGado

**Atualizado em:** 26/09/2026
**Fase:** MVP — **F-MVP-010 concluída**.
**Próxima:** **F-MVP-011 (Clima e Graus-Dia — SPEC-011)**.

> **Painel Operacional Conciso.** Este documento é mantido exclusivamente pelo **Antigravity** após a conclusão e commit de cada fatia. Modelos no Claude Projects apenas o consultam como ponteiro rápido.
> Arquivo de memória, pesquisas detalhadas e handoffs passados vivem em `13-HISTORICO.md`. Decisões fechadas vivem em `12-REGISTRO-DE-DECISOES-ADR.md`.

---

## Situação do Repositório

- **Fundação & MVP:** F-000 até F-004 e F-MVP-007 até F-MVP-010 concluídas e integradas.
- **Suíte de Testes:** **333 testes passando** (0 skipped, 0 falhas), `ruff` e `mypy --strict` 100% limpos.
- **Frontend Web:** Vite React + TypeScript compilando limpo (`npm run build`), autenticação Supabase, Leaflet e Geoman integrados.
- **Banco de Dados (Supabase):** Migrações `0001` e `0002` aplicadas, 9 cultivares populados, RLS habilitado (12 tabelas).
- **Últimos commits:** 
  - `f5403fd` (F-MVP-009: contratos entre modulos e conversao JSON)
  - `49e253d` (prep(SPEC-010): esqueleto vite react-ts no frontend e dependencias da API no pyproject)
  - F-MVP-010 (SPEC-010: esqueleto da API FastAPI e frontend web compartilhado)

---

## Progresso das Fatias do MVP

| Fatia | Status | Resumo / Commit |
|---|---|---|
| F-000 a F-004 | ✅ concluídas | Fundação, domínio, regras e persistência inicial |
| **F-MVP-007 Eventos do MVP** | ✅ concluída | SPEC-007: OrigemPeso, AlturaMedida, Leitura raw, GeoJSON (281 testes) |
| **F-MVP-008 Banco do MVP** | ✅ concluída | SPEC-008: migração `0002_mvp.sql`, projeção DB, catálogo (304 testes) |
| **F-MVP-009 Contratos do MVP** | ✅ concluída | SPEC-009: `contratos.py`, 9 dataclasses, serialização JSON (321 testes) |
| **F-MVP-010 Esqueleto API & Web** | ✅ **concluída** | SPEC-010: FastAPI, 5 rotas stubs, auth, frontend shell (333 testes) |
| **F-MVP-011 Clima e graus-dia** | ⬜ **próxima** | SPEC-011: Open-Meteo histórico e previsão |
| F-MVP-012 Modelo SAFER | ⬜ não iniciada | SPEC-012: biomassa e evapotranspiração |
| F-MVP-013 Ingestão de satélite HLS | ⬜ não iniciada | SPEC-013: Earth Engine HLS S30 |
| F-MVP-014 Estado projetado | ⬜ não iniciada | SPEC-014: união de sensoriamento, clima e SAFER |

---

## Próximo Passo Imediato

- **Ação:** Entregar `specs/SPEC-011-clima.md` para implementação pelo Muse Code.
- **A seguir:** Testar com `revisoes/KIT-ACEITE-011.md` e commitar como `F-MVP-011: ...`.
