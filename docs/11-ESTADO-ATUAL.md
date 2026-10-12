# Estado Atual — SeuGado

**Atualizado em:** 12/10/2026
**Fase:** MVP — fatias **F-MVP-007 a F-MVP-016 concluídas** e **ADR-026 (módulo, praça e motor diário) em andamento**: SPEC-017 e SPEC-018 entregues.
**Próxima:** otimizador real do João (J3) sobre o contrato da ADR-026, e as telas/bot que consomem módulo e praça.

> **Painel Operacional Conciso.** Este documento é mantido exclusivamente pelo **Antigravity** após a conclusão e commit de cada fatia. Modelos no Claude Projects apenas o consultam como ponteiro rápido.
> Arquivo de memória, pesquisas detalhadas e handoffs passados vivem em `13-HISTORICO.md`. Decisões fechadas vivem em `12-REGISTRO-DE-DECISOES-ADR.md`.

---

## Situação do Repositório

- **Fundação & MVP:** F-000 até F-004 e F-MVP-007 até F-MVP-016 concluídas e integradas, mais SPEC-017 e SPEC-018.
- **Suíte de Testes:** **697 testes passando** (0 skipped, 0 falhas), `ruff` e `mypy` limpos.
- **Backend:** FastAPI com rotas de fazendas, clientes, piquetes, lotes, cultivares, plano/ciclo, Telegram e **estrutura (módulo e praça)**. Rotina em `jobs/ciclo.py`, disparada de hora em hora pelo GitHub Actions (`.github/workflows/rotina.yml`); deploy no Render, com webhook do Telegram registrado.
- **Frontend Web:** Vite React + TypeScript com login, tema, clientes, fazenda, lotes, plano, configurações e mapa (desenho e renderização de piquetes).
- **Banco de Dados (Supabase):** migrações `0001` a `0004` aplicadas, 9 cultivares, 13 tipos de evento, RLS em todas as 17 tabelas, 5 fazendas cadastradas.
- **Últimos commits:**
  - `0fc9f67` — SPEC-018: módulo e praça no estado projetado, distância via praça
  - `4b8211e` — clima: retry em 429/5xx, `Retry-After` e cache de 6 h
  - `8a9362d` — SPEC-017: módulo e praça de alimentação, cadastro e API (migração `0004`)
  - `32e5ca6` — ADR-026 e SPEC-017/018
  - `13f2f88` — páginas de lotes e plano (L4–L5)

---

## Progresso das Fatias do MVP

| Fatia | Status | Resumo / Commit |
|---|---|---|
| F-000 a F-004 | ✅ concluídas | Fundação, domínio, regras e persistência inicial |
| F-MVP-007 Eventos do MVP | ✅ concluída | SPEC-007: OrigemPeso, AlturaMedida, Leitura raw, GeoJSON |
| F-MVP-008 Banco do MVP | ✅ concluída | SPEC-008: migração `0002_mvp.sql`, projeção DB, catálogo |
| F-MVP-009 Contratos do MVP | ✅ concluída | SPEC-009: `contratos.py`, serialização JSON |
| F-MVP-010 Esqueleto API & Web | ✅ concluída | SPEC-010: FastAPI, auth, frontend shell |
| F-MVP-011 Clima e graus-dia | ✅ concluída | SPEC-011: Open-Meteo, radiação extraterrestre, graus-dia (`943c41c`) |
| F-MVP-012 Modelo SAFER | ✅ concluída | SPEC-012: taxa de acúmulo (`1265d25`) |
| F-MVP-013 Satélite | ✅ concluída | SPEC-013: Sentinel-2 a 10 m, ingestão (`c0cb2e3`) |
| F-MVP-014 / 014A Estado projetado | ✅ concluídas | SPEC-014/014A: estoque forrageiro, projeção e carga (`f80203f`, `1b3edd3`) |
| F-MVP-015 Admin, agenda, categorias | ✅ concluída | SPEC-015: migração `0003` aplicada (`1977987`) |
| F-MVP-016 Web admin | ✅ concluída | SPEC-016: shell, seleção de fazenda (`08b7e85`) |
| Operação (ADR-025) | ✅ entregue | Bot Telegram (envio, respostas, lembrete, webhook), rotina autônoma, rotas de plano/ciclo/telegram, persistência e comparação de planos |
| **SPEC-017 Módulo e praça: cadastro** | ✅ **concluída** | Migração `0004`, `cadastro/estrutura.py`, 11 rotas (`8a9362d`) |
| **SPEC-018 Módulo e praça: planner** | ✅ **concluída** | Campos de estrutura no `EstadoProjetado`, `planner/estrutura.py`, carga (`0fc9f67`) |
| Motor diário e alertas (ADR-026 §5–6) | ⬜ **próxima** | Otimizador real, entrega diária, catálogo de alertas com ação; spec ainda não escrita |

---

## Pendências Conhecidas

1. **Otimizador ainda é MOCK.** `planner/otimizador.py` manda cada lote ao piquete com o capim mais alto e não usa `piquetes_candidatos` nem `distancia_manejo_m`. O motor real (J3) deve respeitar o módulo do lote e a distância via praça (ADR-026 §1 e §3), rodar todo dia e emitir o catálogo de alertas com ação (§6).
2. **Bot ainda no fluxo semanal.** A ADR-026 §5 elimina o plano `candidato` e passa a entregar a ordem do dia; o código do bot ainda produz o candidato. Depende da spec da ordem do dia.
3. **Telas de módulo e praça.** A API de estrutura existe (SPEC-017); falta a tela no mapa, a cargo do Ezequiel.
4. **SPEC-011 desatualizada.** A spec diz `timeout=30.0` e "no retry"; `sensing/clima.py` agora usa timeout de 20 s, retry com espera e cache de 6 h.
5. **Limiares `HIPOTESE-CALIBRAR`** do catálogo de alertas (1,2 / 1,2 / 0,8): fixar na ADR de calibração com os dados da fazenda do Philipe.
6. **Aceite independente.** Os kits `KIT-ACEITE-017` e `018` foram exercitados pelo próprio implementador (18/18 no 017; casos do 018 cobertos por testes); falta a rodada do testador (Antigravity), conforme ADR-011.

## Observações

- O conformance da SPEC-009 foi ajustado ao contrato atualizado (campos de estrutura no fim da ordem; roundtrip da fixture antiga ignora os campos novos). A fixture `estado_projetado_exemplo.json` não foi regenerada, de propósito: prova que JSON anterior à SPEC-018 ainda carrega.
- Os pushes diretos na `main` passam por bypass da regra "Changes must be made through a pull request" do GitHub.
- Branches remotos abertos: `feat/ezequiel-piquetes`, `feat/leandro-identidade-visual`.

---

## Próximo Passo Imediato

- **Ação:** escrever a spec do motor diário (otimizador J3 sobre `piquetes_candidatos` e `distancia_manejo_m`, entrega todo dia, catálogo de alertas da ADR-026 §6).
- **Em paralelo:** specs da tela de módulo/praça no mapa (Ezequiel) e da ordem do dia no bot (Leo).
- **Antes de fechar o ciclo:** rodada de aceite do testador nos kits 017 e 018, e atualização do texto da SPEC-011.
