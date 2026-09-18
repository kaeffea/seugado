# Estado Atual — SeuGado

**Atualizado em:** 18/09/2026
**Fase:** Fundação concluída (F-000, F-001, **F-001B**, **F-002**, **F-003** e **F-004 concluídas**).
Próxima: **F-005 (Ingestão de satélite)**, dando início à Fase 1 ("Enxergar o pasto").

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
| **F-003 Regras de manejo** | ✅ **concluída** — `core/regras.py`, commit `0248cad`, 215/215 testes |
| **F-004 Persistência e eventos** | ✅ **concluída** — `core/projecao.py`, `persistencia/eventos.py`, SQL migration, 254 testes (+2 skipped) |
| F-005 Ingestão de satélite | ⬜ não iniciada — próxima fatia (início da Fase 1) |
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
├── pyproject.toml             Python 3.12; dev: pytest, ruff, mypy strict; psycopg, pydantic
├── uv.lock                    versionado (ADR-012)
├── db/migrations/             0001_evento_e_derivadas.sql — migração SQL pura (ADR-020)
├── docs/                      00–13, a base de conhecimento (fonte de verdade)
├── src/seugado/core/models.py   7 enums, 8 dataclasses frozen/slots — F-001B/F-004
├── src/seugado/core/forragem.py 7 funções puras — F-002, cálculos de forragem
├── src/seugado/core/regras.py   5 funções puras — F-003, regras de manejo e resolução
├── src/seugado/core/projecao.py dobra pura de eventos — F-004 (SPEC-006)
├── src/seugado/persistencia/eventos.py gateway de escrita validado com Pydantic — F-004 (SPEC-005)
├── tests/core/                suíte do Muse Code (fumaça)
├── tests/persistencia/        suíte de persistência do Muse Code
├── tests/conformance/         suíte de conformidade independente (Antigravity)
├── specs/                     SPEC-001 a SPEC-006
└── revisoes/                  relatórios finais de fatia (arquivo/ contém o legado)
```

Ambiente: `.venv` por `uv` no WSL Ubuntu.
Versões medidas: Python 3.12.3, pytest 9.1.1, ruff 0.16.8, mypy 2.3.1.
Estado das ferramentas: `ruff check`, `ruff format --check`, `mypy` e `pytest` limpos, 254 passed (2 skipped).

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
- ADR-016: custo espacial no otimizador (distância de centroide no MVP, grafo de porteiras pós-MVP).
- ADR-014: método de pastejo (parâmetro por regime, célula vazia com pergunta ao produtor, contínuo em laço próprio semanal, `peso_medio_kg` canônico e categoria compatível).
- ADR-018: schema de eventos — tabela `evento` append-only, correção como evento novo, releitura por `(ocorrido_em, sequencia)`, projeção como dobra pura em `core/projecao.py`, matriz de distância da ADR-016 como projeção materializada.
- ADR-019: confiança composta pelo elo mais fraco (mínimo, não produto), `motivo_confianca` obrigatório. Fecha Q14.
- ADR-020: driver `psycopg` (v3, sem ORM) para a F-004, migração como SQL puro versionado, teste de I/O opcional via `SEUGADO_TEST_DATABASE_URL`.

---

## Ordem sugerida dos próximos chats

| # | Chat | Modelo | Resolve | Por que agora |
|---|---|---|---|---|
| 1 | `[FATIA-003] Regras de manejo` | Sonnet, médio | F-003 | **Próximo passo.** Terceira fatia de código, entrega `regras.py` e `resolver_parametros` |
| 2 | `[FATIA-004] Persistência e eventos` | Sonnet, médio | F-004 | Aplica a ADR-018: migração SQL, `registrar_evento` e a dobra |
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
| **Q13** | R6 deve ser assimétrica? Limite superior duro (3 dias, dano agronômico) e inferior *soft* (1 dia, incômodo operacional)? | risco de **inviabilidade** do modelo em fazenda de lotes grandes e piquetes pequenos | **Decidir na `[ARQUITETURA]` de pesos da função objetivo**, antes do F-009 |
| ~~Q14~~ | Parâmetro de cultivar precisa de `confianca` própria, e como compor com a da estimativa? | — | **Respondida e encerrada (18/09/2026) pela ADR-019:** o campo já existia (ADR-014); a composição é o **mínimo** numa escala ordenada, não produto, sobre três fatores, com `motivo_confianca` obrigatório |
| **Q15** | Lookahead de horizonte fixo (`k ≤ 2` dias) no guloso do F-009, aproveitando a projeção do F-008? | nada; é melhoria opcional do F-009 | Fora da fila até a validação mostrar que o guloso é curto demais. Exige ADR |
| Q12 | Conectar GitHub como fonte do Knowledge? | nada | **Respondida e encerrada (18/09/2026): a pergunta perdeu objeto.** O Knowledge foi esvaziado; a base é lida do disco em `docs/`. Não há duas cópias para sincronizar |

### Duas raias, não uma fila
- **Raia A (código, Sonnet):** F-001B ✅ → F-002 ✅ → **F-003 (próxima)** → `[ARQUITETURA] schema de eventos` → F-004. **Zero dependência de pesquisa.**
- **Raia B (pesquisa, Sonnet):** Q1 → Q2 (+Q3) → Q4 → Q5 (+Q6). Um chat entre fatias.
As duas raias só se encontram no **F-005**. Até lá, nenhuma pesquisa bloqueia código.

---

## Log de handoffs

> Handoffs anteriores estão arquivados em `13-HISTORICO.md`.

**18/09/2026 — [FATIA-004] Persistência e eventos (specs emitidas)**
- **Feito:** **ADR-020** aceita — a F-004 precisava de uma escolha que a ADR-018 não fez: como o
  Python fala com o Postgres. Driver `psycopg` v3 sem ORM, migração como SQL puro versionado, teste
  de I/O real opcional (`SEUGADO_TEST_DATABASE_URL`, pulado se ausente).
- **Fatia dividida em duas specs**, pela regra de dimensionamento do `10` (uma spec não toca 5+
  arquivos): `SPEC-005-persistencia-eventos.md` (I/O — migração SQL da tabela `evento`, das tabelas
  de domínio `tipo_evento`/`origem_evento` e das derivadas `estado_piquete`/`estado_lote`/`leitura`,
  e `persistencia/eventos.py` com `registrar_evento` e um modelo Pydantic por tipo) e
  `SPEC-006-projecao-eventos.md` (puro — `core/projecao.py` com a dobra `projetar`, e extensão
  mínima de `Evento` em `core/models.py` com `sequencia` e `corrige_evento_id`).
- **Escopo da dobra restrito a 7 dos 12 tipos de evento** nesta fatia: `piquete_criado`,
  `piquete_alterado`, `lote_criado`, `lote_alterado`, `lote_dissolvido`, `manejo_confirmado`,
  `leitura_satelite`. Os outros cinco (`manejo_recomendado`, `manejo_recusado`,
  `manejo_divergente`, `foto_validacao`, `parametro_alterado`) são validados e persistidos pelo
  `registrar_evento`, mas não mudam nenhuma das três tabelas derivadas ainda — ficam registrados,
  sem efeito de projeção, até a fatia que os consome (F-010, F-013, F-014) definir o contrato.
- **`piquete_distancia` adiada da F-004.** A ADR-018 já previa isso como possível
  ("ainda que só o F-009 a use"); calcular `ST_Distance` sobre centroides exige geometria (shapely)
  que nenhuma spec anterior trouxe como dependência. Fica para uma spec pequena e dedicada antes do
  F-009, sem reabrir a ADR-018.
- **`aguardando_parametro` fora de `EstadoPiquete` nesta fatia.** Depende de cruzar o evento com o
  catálogo de `Cultivar` (via `resolver_parametros`), que não é evento — é tabela de referência.
  Isso é trabalho do `planner/estado.py` (F-008), não da dobra pura sobre o log de eventos.
- **Pendente:** implementação pelo Muse Code (duas specs, ordem: `SPEC-006` antes de `SPEC-005`,
  já que `SPEC-005` referencia os payloads que `SPEC-006` também consome), teste e commit pelo
  Antigravity.
- **Observação para o próximo chat:** `src/seugado/core/regras.py` já existe no disco com
  `resolver_parametros`, `apto_para_entrada`, `precisa_sair`, `urgencia` e `descanso_cumprido` —
  o Muse Code parece já ter entregue a F-003, mas este `11` ainda a lista como "spec emitida,
  aguardando implementação". Confirmar com o Antigravity se os testes de `SPEC-004-regras.md`
  passaram e o commit foi feito; se sim, atualizar esta tabela antes de seguir.
- **Próximo:** Muse Code implementa `SPEC-006` e `SPEC-005`; depois, F-005 (Ingestão de satélite).

**18/09/2026 — [ARQUITETURA] Schema de eventos**
- **Feito:** **ADR-018** e **ADR-019** aceitas. Tabela `evento` (singular) append-only por
  `REVOKE` + trigger, com `sequencia`, `ator`, `corrige_evento_id`, `chave_idempotencia`,
  `versao_payload` e `entidade_id` gerada do payload. Releitura por `(ocorrido_em, sequencia)`;
  correção entra na posição temporal do evento corrigido. Projeção é **dobra pura** em
  `core/projecao.py`, distinta da projeção temporal do `planner/estado.py` (F-008). Quatro
  tabelas derivadas — `estado_piquete`, `estado_lote`, `leitura`, `piquete_distancia` — com
  `derivado_ate_sequencia`, reconstruídas por `DELETE`+`INSERT`. **A matriz de distância da
  ADR-016 mora numa tabela materializada**, não em view nem em cache do job.
- **Q14 fechada (ADR-019):** confiança combina pelo **mínimo** de três fatores (estimativa,
  parâmetro de regime, peso), nunca por produto — produto exigiria números sem fonte. Toda
  recomendação carrega `motivo_confianca`.
- **Editado:** `06` §2 (módulos novos), §3 (contratos `projetar`, `combinar_confianca`,
  `motivo_confianca` em `Movimentacao`), §4 (tabela completa), §5 (bloco de derivadas);
  `12` (ADR-018, ADR-019); `11`.
- **Mudança de fronteira:** `leitura` deixa de ser tabela-fonte e vira derivada — o F-005 grava
  evento, não linha. E `Cultivar` passa a ser sempre carregada no contexto de uma fazenda, com o
  override da ADR-014 aplicado na camada de carga; a assinatura de `resolver_parametros` da
  SPEC-004 não muda.
- **Adiado com condição:** snapshot de projeção só entra se a releitura passar de 2 s medidos.
- **Próximo:** `[FATIA-004] Persistência e eventos`.

**18/09/2026 — [ARQUITETURA] Custo espacial e triagem de brainstorming**
- **Feito:** **ADR-016** aceita — o otimizador deixa de ser espacialmente cego. Matriz de
  distância entre centroides derivada da geometria que o `06` §5 já guarda (fricção zero para o
  produtor); distância como **desempate** no guloso do F-009; termo `− w6 · custo_espacial`,
  ponderado por peso vivo, na função objetivo do F-021. Grafo de porteiras rejeitado para o MVP,
  registrado como candidato pós-MVP com condição de entrada. Premissa de "todo piquete tem água e
  alcança todo outro" explicitada como risco.
- **Editado:** `07` §2 (função objetivo, nota de assimetria de R6), `07` §5 (ordem de escolha do
  guloso e o que ele não faz), `01` (a ideia de migração de regime virou **planejador de
  capacidade bidirecional**), `12` (ADR-016).
- **Rejeitado do brainstorming, com motivo:** "rotacionado produz 3 a 4x mais carne/ha" — número
  sem fonte, exatamente o que a regra 1 proíbe; a premissa continua sendo **Q10**, não verificada.
  E "o CP-SAT resolve o trade-off de esperar sozinho" — resolve, mas é F-021, **pós-MVP**, e
  depende de pesos que ninguém calibrou ainda.
- **Confirmado sem mudança:** peso por categoria e não individual (ADR-014, `origem_peso`), e
  cultivar sem parâmetro não prescreve (R11). O brainstorming reconfirmou decisões já fechadas.
- **Novas perguntas:** Q13 (assimetria de R6), Q14 (confiança do parâmetro), Q15 (lookahead curto).
- **Próximo:** inalterado — F-003 aguarda o Muse Code, depois `[ARQUITETURA] Schema de eventos`.

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
