# Estado Atual — SeuGado

**Atualizado em:** 12/10/2026
**Fase:** MVP — fatias **F-MVP-007 a F-MVP-016 concluídas** e **ADR-026 (módulo, praça e motor diário)**: SPEC-017, SPEC-018 e SPEC-019 entregues. O otimizador deixou de ser MOCK.
**Próxima:** consumo do motor diário pelo bot (ordem do dia, fim do plano `candidato`) e telas de módulo e praça.

> **Painel Operacional Conciso.** Este documento é mantido exclusivamente pelo **Antigravity** após a conclusão e commit de cada fatia. Modelos no Claude Projects apenas o consultam como ponteiro rápido.
> Arquivo de memória, pesquisas detalhadas e handoffs passados vivem em `13-HISTORICO.md`. Decisões fechadas vivem em `12-REGISTRO-DE-DECISOES-ADR.md`.

---

## Situação do Repositório

- **Fundação & MVP:** F-000 até F-004 e F-MVP-007 até F-MVP-016 concluídas e integradas, mais SPEC-017, SPEC-018 e SPEC-019.
- **Suíte de Testes:** **737 testes passando** (0 skipped, 0 falhas), `ruff` e `mypy` limpos.
- **Backend:** FastAPI com rotas de fazendas, clientes, piquetes, lotes, cultivares, plano/ciclo, Telegram e estrutura (módulo e praça). Rotina em `jobs/ciclo.py`, disparada de hora em hora pelo GitHub Actions (`.github/workflows/rotina.yml`); deploy no Render, com webhook do Telegram registrado.
- **Motor de otimização:** `planner/otimizador.py` simula 7 dias, um de cada vez, com lote preso ao módulo, distância via praça, fila de saída dentro da capacidade da equipe e fallback de altura. O catálogo de alertas (cada um com ação recomendada) vive em `planner/alertas.py`.
- **Frontend Web:** Vite React + TypeScript com login, tema, clientes, fazenda, lotes, plano, configurações e mapa (desenho e renderização de piquetes).
- **Banco de Dados (Supabase):** migrações `0001` a `0004` aplicadas, 9 cultivares, 13 tipos de evento, RLS em todas as 17 tabelas, 5 fazendas cadastradas.
- **Últimos commits:**
  - `5e75496` — SPEC-019: lote maior que a equipe sem destino não trava a fila (R5 emendado)
  - `3199bbb` — SPEC-019: motor diário guloso e catálogo de alertas
  - `0fc9f67` — SPEC-018: módulo e praça no estado projetado, distância via praça
  - `4b8211e` — clima: retry em 429/5xx, `Retry-After` e cache de 6 h
  - `8a9362d` — SPEC-017: módulo e praça de alimentação, cadastro e API (migração `0004`)

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
| SPEC-017 Módulo e praça: cadastro | ✅ concluída | Migração `0004`, `cadastro/estrutura.py`, 11 rotas (`8a9362d`) |
| SPEC-018 Módulo e praça: planner | ✅ concluída | Campos de estrutura no `EstadoProjetado`, `planner/estrutura.py`, carga (`0fc9f67`) |
| **SPEC-019 Motor diário e alertas** | ✅ **concluída** | Otimizador guloso dia a dia, catálogo de alertas com ação, emenda do R5 (`3199bbb`, `5e75496`) |
| Ordem do dia no bot (ADR-026 §5) | ⬜ **próxima** | Entrega diária, fim do plano `candidato`; spec ainda não escrita |
| Tela de módulo e praça | ⬜ não iniciada | API pronta; falta a tela no mapa (Ezequiel) |

---

## Pendências Conhecidas

1. **Bot ainda no fluxo do plano `candidato`.** A ADR-026 §5 elimina o candidato e passa a entregar a ordem do dia; o código do bot ainda produz o candidato. Depende da spec da ordem do dia.
2. **Telas de módulo e praça.** A API de estrutura existe (SPEC-017); falta a tela no mapa, a cargo do Ezequiel.
3. **Aceite independente pendente nos kits 017, 018 e 019.** Os kits foram exercitados por quem implementou (017: 18/18; 018: casos cobertos por testes; 019: suíte em `tests/conformance/test_spec_019.py`). No 019 o implementador viu os casos 1 a 3 antes de programar; o caso 4 foi escrito depois e pegou um defeito real do R5. Falta a rodada do testador (Antigravity), conforme ADR-011.
4. **Dívida: densidade do motor.** `gerar_plano` guarda o estado da simulação em closures dentro de uma função só (`# noqa: PLR0915`) para caber no limite de 300 linhas por arquivo. Não será refatorado: o motor guloso será substituído pelo CP-SAT depois do MVP.
5. **SPEC-011 desatualizada.** A spec diz `timeout=30.0` e "no retry"; `sensing/clima.py` usa timeout de 20 s, retry com espera e cache de 6 h.
6. **Limiares `HIPOTESE-CALIBRAR`:** fallback 0,9 × entrada, passando do ponto 1,2, sobra 1,2 e falta 0,8. Fixar na ADR de calibração com os dados da fazenda do Philipe.

## Observações

- Os conformance das SPEC-009 e SPEC-015 foram ajustados ao contrato atual: campos de estrutura no fim da ordem de `PiqueteProjetado`/`LoteProjetado`, 13 membros em `TipoAlerta`, e roundtrip das fixtures antigas ignorando `acao`/`modulo_id` e os campos de estrutura. As fixtures não foram regeneradas, de propósito: provam que JSON anterior às SPEC-018 e 019 ainda carrega.
- Os pushes diretos na `main` passam por bypass da regra "Changes must be made through a pull request" do GitHub.
- Branches remotos abertos: `feat/ezequiel-piquetes`, `feat/leandro-identidade-visual`.

---

## Próximo Passo Imediato

- **Ação:** escrever a spec da ordem do dia no bot (entrega diária, fim do plano `candidato`, uso dos alertas com ação).
- **Em paralelo:** spec da tela de módulo e praça no mapa (Ezequiel).
- **Antes de fechar o ciclo:** rodada de aceite do testador nos kits 017, 018 e 019, e atualização do texto da SPEC-011.
