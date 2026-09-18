# Estado Atual — SeuGado

**Atualizado em:** 18/09/2026
**Fase:** Fase 0 (Fundação) 100% concluída.
**Próxima:** Fase 1 ("Enxergar o pasto") — **F-005 (Ingestão de satélite)**.

> **Painel Operacional Conciso.** Este documento é mantido exclusivamente pelo **Antigravity** após a conclusão e commit de cada fatia. Modelos no Claude Projects apenas o consultam como ponteiro rápido.
> Arquivo de memória, pesquisas detalhadas e handoffs passados vivem em `13-HISTORICO.md`. Decisões fechadas vivem em `12-REGISTRO-DE-DECISOES-ADR.md`.

---

## Situação do Repositório

- **Fase 0 (Fundação):** F-000, F-001, F-001B, F-002, F-003 e F-004 concluídas e integradas.
- **Suíte de Testes:** **254 testes passando** (+2 skipped de integração de banco), `ruff` e `mypy --strict` 100% limpos.
- **Últimos commits:** 
  - `0248cad` (F-003: regras de manejo em `core/regras.py`)
  - `02afb79` (F-004a: projeção pura de eventos em `core/projecao.py` - SPEC-006)
  - `32d06bf` (F-004b: persistência e migração SQL em `persistencia/eventos.py` - SPEC-005)

---

## Progresso das Fatias

| Fatia | Status | Resumo / Commit |
|---|---|---|
| F-000 Fundação do repositório | ✅ concluída | ADR-012 |
| F-001 Modelo de domínio | ✅ concluída | 13/13 critérios, 157 testes |
| F-001B Parâmetro por regime | ✅ concluída | commit `5a600c8`, 177 testes |
| F-002 Cálculos de forragem | ✅ concluída | commit `d76c7f6`, 196 testes |
| F-003 Regras de manejo | ✅ concluída | commit `0248cad`, 215 testes |
| F-004 Persistência e eventos | ✅ concluída | commits `02afb79` / `32d06bf`, 254 testes |
| **F-005 Ingestão de satélite** | ⬜ **próxima** | Início da Fase 1 (Earth Engine / Sentinel-2) |
| F-006 Modelo SAFER | 🔒 bloqueada | Aguarda B2 (`rue_max_g_por_mj`) |
| F-007 Clima e graus-dia | 🔒 bloqueada | Aguarda B4 (`temperatura_base_c`) |
| F-008 ⭐ Projeção de estado | ⬜ não iniciada | Marco da Fase 1 |
| F-009 a F-022 | ⬜ não iniciadas | Fase 2 em diante |

---

## Bloqueios Ativos

| # | Bloqueio | Bloqueia | Resolver em |
|---|---|---|---|
| B1 | `densidade_kg_ha_por_cm` ausente para todas as cultivares | Produção real (F-002 implementado) | `[PESQUISA]` Q2 (`13` §6) |
| B2 | RUE para gramínea C4 tropical ausente | F-006 | `[PESQUISA]` Q4 (`13` §6) |
| B4 | `temperatura_base_c` ausente | F-007 | `[PESQUISA]` Q5 (`13` §6) |
| B7 | `eficiencia_pastejo` sem fonte (ADR-010) | Produção real (F-002 implementado) | `[PESQUISA]` Q2 (`13` §6) |

---

## Próximo Passo Imediato

- **Chat:** `[FATIA-005] Ingestão de satélite (Earth Engine)`
- **Modelo:** Claude Sonnet (esforço médio)
- **Prompt:**
  ```text
  [FATIA-005] Ingestão de satélite
  Leia: docs/11, docs/09, docs/06 §3, docs/10 (entrada F-005), docs/12 (ADR-018 e ADR-020).
  ```
