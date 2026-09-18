# Estado Atual — SeuGado

**Atualizado em:** 18/09/2026
**Fase:** Fundação — F-000, F-001, **F-001B** e **F-002 concluídas**. F-003 tem
`specs/SPEC-004-regras.md` emitida, aguardando implementação do Muse Code.

> Este é o registro único do estado operacional ativo e da fila de trabalho.
> Mudanças históricas, handoffs antigos e discussões passadas foram arquivados em `13-HISTORICO.md`.
> **A base de contexto vive no disco** (`C:\code\seugado\docs\`), não no Project Knowledge —
> todo chat abre lendo os arquivos que o prompt indicar (protocolo no `00`).

---

## Situação

O modelo de domínio e os cálculos de forragem estão implementados e cobertos por suítes de teste (fumaça e conformidade independente), passando **196/196 testes**. Repositório com fundação Git, `pyproject.toml`, `ruff`, `mypy` strict e `pytest` 100% limpos.

- **F-001B concluída (17/09/2026):** ADR-014 aplicada em `models.py` (commit `5a600c8`).
- **F-002 concluída (17/09/2026):** Cálculos de forragem em `core/forragem.py` (commit `d76c7f6`, 196/196 testes).
- **Transição para o Fluxo Ágil:** Runbooks e manifestos SHA-256 foram aposentados. O **Antigravity (Gemini)** assume a execução de terminal, verificação no WSL, faxina de lints em testes e commits diretos no Git. O Arquiteto (Claude) cuida de specs, ADRs e pesquisas.
- **F-003 destravada:** `core/regras.py` não depende de pesquisa e será implementada a seguir.

---

## Progresso das fatias

| Fatia | Status |
|---|---|
| F-000 Fundação do repositório | ✅ concluída (ADR-012) |
| F-001 Modelo de domínio | ✅ concluída — 13/13 critérios, 157 testes |
| **F-001B Modelo de domínio: parâmetro por regime** | ✅ **concluída** — 14/14 critérios, commit `5a600c8`, 177/177 testes |
| **F-002 Cálculos de forragem** | ✅ **concluída** — `core/forragem.py`, commit `d76c7f6`, 196/196 testes |
| F-003 Regras de manejo | 🟨 **spec emitida** (`SPEC-004-regras.md`) — aguarda Muse Code |
| F-004 Persistência e eventos | ⬜ não iniciada — exige `[ARQUITETURA] Schema de eventos` antes |
| F-005 Ingestão de satélite | ⬜ não iniciada |
| F-006 Modelo SAFER | 🔒 bloqueada (`rue_max_g_por_mj` C4) |
| F-007 Clima e graus-dia | 🔒 bloqueada (`temperatura_base_c`) |
| F-008 ⭐ Projeção de estado | ⬜ não iniciada |
| F-009B Ajuste de lotação em contínuo | ⬜ **nova, criada pela ADR-014** — pós-MVP, entra depois do F-015 |
| F-009 a F-022 | ⬜ não iniciadas |

Legenda: ⬜ não iniciada · 🟨 em andamento · 🔒 bloqueada · ✅ concluída

---

## O que existe no repositório

Layout da ADR-013, aplicado e verificado:

```
C:\code\seugado                git, main, publicado no GitHub (privado)
├── README.md                  mapa simples do projeto — ler primeiro
├── pyproject.toml             Python 3.12; dev: pytest, ruff, mypy strict; md fora do ruff
├── uv.lock                    versionado (ADR-012)
├── docs/                      00–13, a base de conhecimento (fonte de verdade)
├── src/seugado/core/models.py   7 enums, 8 dataclasses frozen/slots — F-001B, parâmetro por regime
├── src/seugado/core/forragem.py 7 funções puras — F-002, cálculos de forragem
├── tests/core/                suíte do Muse Code (fumaça)
├── tests/conformance/         suíte de conformidade independente (Antigravity)
├── specs/                     SPEC-001, SPEC-002, SPEC-002-CORRECAO-A, SPEC-003-forragem.md
└── revisoes/                  relatórios finais de fatia (arquivo/ contém o legado)
```

Ambiente: `.venv` por `uv` no WSL Ubuntu.
Versões medidas: Python 3.12.3, pytest 9.1.1, ruff 0.16.8, mypy 2.3.1.
Estado das ferramentas: `ruff check`, `ruff format --check`, `mypy` e `pytest` limpos, 196/196.

---

## Bloqueios ativos

| # | Bloqueio | Bloqueia | Resolver em |
|---|---|---|---|
| B1 | `densidade_kg_ha_por_cm` ausente para todas as cultivares | **produção** com cultivar real (F-002 implementado) | `[PESQUISA]` Q2 |
| B2 | RUE para gramínea C4 tropical ausente (paper usa 2,45 g/MJ de C3) | F-006 | `[PESQUISA]` Q4 |
| B4 | `temperatura_base_c` ausente | F-007 | `[PESQUISA]` Q5 |
| B6 | Termos de uso atuais do Earth Engine não verificados | F-005 | `[PESQUISA]` Q1 |
| B7 | `eficiencia_pastejo` sem fonte (ADR-010) | **produção** com cultivar real (F-002 implementado) | `[PESQUISA]` Q2 |

> Bloqueios resolvidos (~~B3~~, ~~B5~~, ~~B8~~) arquivados em `13-HISTORICO.md`.

---

## Dívida técnica ativa (não bloqueia)

| # | Item | Onde | Destino |
|---|---|---|---|
| DT2 | Contratos de `06` §3 divergem do modelo implementado (`Literal` vs enum, `list` vs `tuple`, frozen não declarado) | `06` §3 | ADR-015 |
| DT4 | Convenções de enum e de entidade como chave de dict | `06` §7 | ADR-017 confirma |
| DT5 | Comentário `Monday first` ambíguo em `models.py` | `models.py` | próxima spec que tocar o arquivo |
| DT8 | `SPEC-001` contém arquivo de teste pronto, o que a ADR-011 passou a proibir | `specs/` | histórico; não reescrever |
| DT9 | Mitigação do kit de aceite não estar fisicamente escondido do Muse Code | método | avaliar se commita kit pós-Muse |
| DT10 | Caminhos legados sem `src/` em registros datados | specs/docs | decidido: não corrigir registros históricos |

> Dívidas resolvidas (~~DT1~~, ~~DT3~~, ~~DT6~~, ~~DT11~~) arquivadas em `13-HISTORICO.md`.

---

## Decisões tomadas

Ver `12-REGISTRO-DE-DECISOES-ADR.md`.
- ADR-001 a ADR-009: configuração inicial e escopo.
- ADR-010: eficiência de pastejo × taxa de utilização.
- ADR-011: separação entre spec e kit de aceite.
- ADR-012: fundação do repositório e ferramentas dev.
- ADR-013: reorganização de layout (`src/seugado/`).
- ADR-014: método de pastejo (parâmetro por regime, célula vazia com pergunta ao produtor, contínuo em laço próprio semanal, `peso_medio_kg` canônico e categoria compatível).

---

## Ordem sugerida dos próximos chats

| # | Chat | Modelo | Resolve | Por que agora |
|---|---|---|---|---|
| 1 | `[FATIA-003] Regras de manejo` | Sonnet, médio | F-003 | **Próximo passo.** Terceira fatia de código, entrega `regras.py` e `resolver_parametros` |
| 2 | `[ARQUITETURA] Schema de eventos` | Opus | antes de F-004 | Define schema Postgres/PostGIS e persistência |
| 3 | `[FATIA-004] Persistência e eventos` | Sonnet, médio | F-004 | Aplica schema e projeção de estado inicial |
| — | `[PESQUISA] Q1 a Q6` | Sonnet, médio | B1, B2, B4, B6, B7 | Em paralelo ou entre fatias (ver raias abaixo) |

---

## Registro de perguntas abertas (Q1–Q12)

> **Registro único da fila de pesquisa.** Quem quiser saber o estado de uma pergunta consulta esta tabela.

| # | Pergunta | Trava o quê | Posição na fila |
|---|---|---|---|
| Q1 | Termos de uso atuais do Earth Engine permitem uso não-comercial? (B6) | F-005, arquitetura de F-006 | **Pesquisa 1.** Aposta de arquitetura |
| Q2 | `densidade_kg_ha_por_cm` por cultivar (B1) e `eficiencia_pastejo` (B7) | **F-008, o marco ⭐** | **Pesquisa 2.** Parede real do produto |
| Q3 | Quais cultivares dominam a pecuária de Alagoas? | nada | **Pesquisa 3.** Poda a Q2 |
| Q4 | RUE de gramínea C4 tropical (B2) | F-006 | **Pesquisa 4.** Estimativa de crescimento |
| Q5 | `temperatura_base_c` de gramínea tropical (B4) | F-007 | **Pesquisa 5.** Barato e isolado |
| Q6 | Fonte climática: INMET ou reanálise? | F-007 | **Pesquisa 5, junto com Q5.** |
| Q7 | `descanso_min/max_dias` por cultivar e `taxa_senescencia` | nada | **Pesquisa 6**, opcional |
| Q8 | Faixa de entrada rotacional do Marandu (19–30 cm) pode estreitar? | nada | Fora da fila por decisão (ADR-014 aceita faixa) |
| Q9 | Pastejo líder-seguidor: ganho medido? | ideia futura no 01 | Fora da fila por decisão |
| Q10 | Diferencial medido contínuo × rotacionado | ideia futura no 01 | Fora da fila por decisão |
| Q11 | Fazenda-piloto acessível para validação? | nada no MVP | Fora da fila por decisão (contato humano) |
| Q12 | Conectar GitHub como fonte do Knowledge? | nada | **Respondida e encerrada (18/09/2026): a pergunta perdeu objeto.** O Knowledge foi esvaziado; a base é lida do disco em `docs/`. Não há duas cópias para sincronizar |

### Duas raias, não uma fila
- **Raia A (código, Sonnet):** F-001B ✅ → F-002 ✅ → **F-003 (próxima)** → `[ARQUITETURA] schema de eventos` → F-004. **Zero dependência de pesquisa.**
- **Raia B (pesquisa, Sonnet):** Q1 → Q2 (+Q3) → Q4 → Q5 (+Q6). Um chat entre fatias.
As duas raias só se encontram no **F-005**. Até lá, nenhuma pesquisa bloqueia código.

---

## Log de handoffs

> Handoffs anteriores estão arquivados em `13-HISTORICO.md`.

**18/09/2026 — [FATIA-003] Regras de manejo (spec emitida)**
- **Feito:** `specs/SPEC-004-regras.md` emitida para o Muse Code — `core/regras.py`,
  funções puras: `resolver_parametros` (porta única de parâmetro, ADR-014),
  `apto_para_entrada`, `precisa_sair`, `urgencia`, `descanso_cumprido`. Kit de aceite em
  `revisoes/KIT-ACEITE-004.md`, com 4 casos ocultos (bloco parcial, fronteira de descanso,
  `ValueError` em bloco contínuo, múltiplos blocos por cultivar).
- **Nota de escopo:** `urgencia` marcada `HIPOTESE-CALIBRAR` (escala em cm bruto, não
  normalizada pela faixa entrada–saída) — não bloqueia, revisitar se F-020/F-021 precisarem
  de urgência comparável entre piquetes.
- **Pendente:** implementação pelo Muse Code, teste e commit pelo Antigravity.
- **Próximo:** `[ARQUITETURA] Schema de eventos` antes de F-004.

**17/09/2026 — [FATIA-002] Cálculos de forragem (concluída)**
- **Feito:** F-002 implementada em `core/forragem.py` com 7 funções puras (`massa_para_altura`, `altura_para_massa`, `consumo_lote_kg_ms_dia`, `dias_ocupacao`, `taxa_utilizacao`, `consumo_individual_kg_ms_dia`, `consumo_pct_pv`). Testada com suíte do Muse e suíte de conformidade independente em `tests/conformance/test_forragem_conformance.py`. Commit `d76c7f6`. 196/196 testes passando. `mypy` strict e `ruff` 100% limpos.
- **Pendente:** F-003 (Regras de manejo) — destravada pela ADR-014.
- **Próximo:** `[FATIA-003] Regras de manejo` no Claude Sonnet.
