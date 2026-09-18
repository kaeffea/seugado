# Roteiro de Fatias — SeuGado

Sem prazo, sem sprint, sem estimativa de tempo. A ordem importa; a velocidade não.

**Marco crítico:** a partir da **Fatia 08** já existe produto entregando valor real.
Tudo depois é refinamento. Essa ordem garante que, se o projeto parar, ele para num
ponto que funciona — não num ponto quebrado.

---

## Fase 0 — Fundação (sem código de produto)

### F-000 · Fundação do repositório ✅
git, `pyproject.toml` (Python 3.12, pytest/ruff/mypy no grupo `dev`), `.gitignore`
e `uv.lock` versionado. Não é fatia do Muse Code — não há lógica de domínio.
(O `CLAUDE.md` também entregue nesta fatia foi removido com a aposentadoria do Claude Code;
as regras de método que ele carregava vivem no `08` §7.)
**Entrega:** diff verificável e critério "nenhuma dependência nova" auditável. Ver ADR-012.

### F-001 · Modelo de domínio
Entidades puras: `Piquete`, `Lote`, `Cultivar`, `Manejo`, `Evento`.
Dataclasses com type hints, sem persistência, sem I/O.
**Módulo:** `core/models.py` · **Entrega:** vocabulário do glossário virou código.
⚠️ **Reaberta pela ADR-014.** `Cultivar` perde os campos planos de altura e ganha
`parametros_por_regime: tuple[ParametrosRegime, ...]`; entram o enum `MetodoPastejo` e o campo
`metodo_pastejo` em `Piquete`. É o primeiro arquivo aprovado a ser reaberto — exige spec
própria (**F-001B**), antes do F-002.

### F-002 · Cálculos de forragem
`massa ↔ altura`, consumo do lote, dias de ocupação (com crescimento durante a ocupação).
**Módulo:** `core/forragem.py` · **Entrega:** caso de regressão canônico passa.
✅ **Não bloqueada.** `TODO-PARAM` barra **default de produção**, não implementação (`05`,
"Escopo do bloqueio"; ADR-010). As funções recebem `densidade_kg_ha_por_cm` e
`eficiencia_pastejo` por argumento, e o caso canônico do `05` roda com os dois neutralizados
(`eficiencia_pastejo = 1.0`, `taxa_acumulo = 0.0`). O contrato de `dias_ocupacao` (`06` §3)
recebe só floats, então esta fatia **também não depende do F-001B**. Ver `11`, "Correção de
17/09/2026".

### F-003 · Regras de manejo
`apto_para_entrada?`, `precisa_sair?`, `urgencia`, `descanso_cumprido?`, e
`resolver_parametros(cultivar, metodo)` — a porta única de acesso a parâmetro, que devolve o
bloco de regime ou a lista de `faltantes` (ADR-014).
**Módulo:** `core/regras.py` · **Entrega:** decisão binária por piquete, testada.

### F-004 · Persistência e eventos
Schema Postgres/PostGIS, tabela `eventos` append-only, projeção de estado.
**Módulo:** `db/` · **Entrega:** estado derivado de eventos, recálculo funciona.

---

## Fase 1 — Enxergar o pasto

### F-005 · Ingestão de satélite
Cliente Earth Engine, amostragem de NDVI por geometria de piquete.
Máscara de nuvem **e de sombra de nuvem**. Buffer negativo. Contagem de pixels válidos.
**Módulo:** `sensing/earth_engine.py` · **Entrega:** NDVI por piquete por data.

### F-006 · Modelo SAFER
As 11 equações como funções puras. Faixas de sanidade em runtime.
**Módulo:** `sensing/safer.py` · **Entrega:** `kg MS/ha/dia` a partir de NDVI + clima.
⚠️ Bloqueada por `TODO-PARAM: rue_max_g_por_mj` (C4). · **Modelo: Opus, esforço alto.**

### F-007 · Ingestão climática e graus-dia
Cliente de clima (reanálise + INMET), ET₀, soma térmica.
**Módulo:** `sensing/clima.py` · **Entrega:** motor de interpolação diária entre passagens.
⚠️ Bloqueada por `TODO-PARAM: temperatura_base_c`.

### F-008 · Projeção de estado ⭐ **MARCO — primeiro valor real**
Junta tudo: avança massa diariamente, corrige quando chega imagem limpa.
**Módulo:** `planner/estado.py`
**Entrega:** *"o Piquete 7 está em 88 cm hoje"* — resposta que nenhum concorrente dá
com este nível de rigor.

---

## Fase 2 — Decidir

### F-009 · Otimizador guloso
Ordena por urgência, aloca ao melhor piquete apto. Sem lookahead.
Respeita mão de obra e dias preferenciais desde já.
**Módulo:** `planner/otimizador.py` · **Entrega:** plano de 7 dias.

### F-009B · Ajuste de lotação em pastejo contínuo — **pós-MVP**
Laço **semanal**, separado do diário, disparado por gatilho de altura
(`altura_maxima_cm` / `altura_minima_cm`). Produz recomendação de **quantos animais entram ou
saem** do piquete contínuo, não de movimentação.
**Módulo:** `planner/` · **Entrega:** prescrição para fazenda que não rotaciona.
⚠️ **Entra depois do F-015**, não aqui. Fica listada nesta posição porque é onde ela pertence
conceitualmente (é a irmã do F-009), mas a ordem de execução é pós-MVP — ver ADR-014. Até ela
existir, piquete contínuo recebe estado e alerta de altura, **não** número de animais.

### F-010 · Camada de confiança
Cálculo de confiança por estimativa; faixas alta/média/baixa.
**Módulo:** `planner/confianca.py` · **Entrega:** toda recomendação carrega confiança.

### F-011 · Geração de mensagem
Estrutura → português legível. Ordem + motivo + confiança.
**Módulo:** `delivery/mensagem.py` · **Entrega:** o texto que o produtor lê.

---

## Fase 3 — Falar com o produtor

### F-012 · Canal Telegram
Interface `Channel` abstrata + implementação Telegram. Envio e recebimento de confirmação.
**Módulo:** `delivery/canais/` · **Entrega:** mensagem chega no celular.

### F-013 · Loop de confirmação
Confirmado / não feito / fiz diferente. Confirmação por omissão em 24h com confiança reduzida.
Gera eventos. **Módulo:** `delivery/` + `db/` · **Entrega:** ciclo fechado.

### F-014 · Cadastro da fazenda (web)
Desenho de piquetes no mapa (Leaflet → GeoJSON), cultivar por piquete, lotes por categoria,
funcionários, dias preferenciais.
**Módulo:** `frontend/` + `api/` · **Entrega:** fricção de configuração resolvida.

### F-015 · Pipeline diário automatizado
GitHub Actions cron, orquestração ponta a ponta, tratamento de falha.
**Módulo:** `jobs/` · **Entrega:** ⭐ **MVP COMPLETO** — roda sozinho todo dia.

---

## Fase 4 — Precisão

### F-016 · Gap-filling por SAR
Ingestão Sentinel-1, treino `SAR + clima → NDVI`, predição em dias nublados.
**Módulo:** `sensing/gapfill.py` · **Entrega:** resolve a cegueira das águas.
**Modelo: Opus, esforço alto.**

### F-017 · Validação por foto
Upload pelo canal, referência de escala por dois pontos na tela, correção da estimativa.
**Módulo:** `sensing/` + `delivery/` · **Entrega:** calibração local que melhora com o uso.

### F-018 · Detecção de manejo por SAR
Inferir execução pelo backscatter, reduzindo pedidos de confirmação.
**Módulo:** `sensing/gapfill.py` · **Entrega:** menos fricção recorrente.

### F-019 · Sentinel-2 a 10 m
Fonte de refinamento para piquetes pequenos de rotacionado intensivo.
**Módulo:** `sensing/earth_engine.py` · **Entrega:** viabiliza piquetes de 0,5–3 ha.

---

## Fase 5 — Otimização avançada

### F-020 · Busca local
Trocas sobre a solução gulosa. Baseline de comparação: F-009.
**Módulo:** `planner/otimizador.py`

### F-021 · CP-SAT com horizonte rolante
Otimização 14–30 dias, execução dos primeiros dias, re-otimização diária.
**Módulo:** `planner/otimizador.py` · **Modelo: Opus, esforço alto.**

### F-022 · Fusão de lotes
Hierarquia de soluções, compatibilidade de categoria, confirmação humana obrigatória,
exibição das alternativas descartadas.
**Módulo:** `planner/otimizador.py`

---

## Chats `[PESQUISA]` que desbloqueiam fatias

A fila canônica e o status de cada pesquisa vivem exclusivamente no **`11-ESTADO-ATUAL.md` (tabela Q1–Q12)**, que é o registro único de perguntas e bloqueios de pesquisa do projeto.

Conforme a **ADR-014** e a divisão em **Duas Raias**:
- **Raia A (código):** F-001B ✅ → F-002 ✅ → **F-003 (próxima)** → `[ARQUITETURA] schema de eventos` → F-004. Zero dependência de pesquisa.
- **Raia B (pesquisa):** Q1 → Q2 (+Q3) → Q4 → Q5 (+Q6). Rodam em chats dedicados no Sonnet entre as fatias de código. As duas raias só se encontram a partir de F-005 e no marco F-008.


---

## Chats `[ARQUITETURA]` previstos

| Tema | Quando | Produz |
|---|---|---|
| Schema de eventos e projeção de estado | antes de F-004 | ADR |
| Estratégia de correção da âncora de satélite | antes de F-008 | ADR |
| Pesos da função objetivo | antes de F-009 | ADR |
| Fusão de lotes: calibrar o limiar de categoria compatível | antes de F-022 | ADR |
| Hospedagem da API (Fly.io vs Render) | antes de F-015 | ADR |
| Features do modelo de gap-filling | antes de F-016 | ADR |

---

## Regra de dimensionamento

Se uma fatia não cabe em **3–4 arquivos lidos**, ela é larga demais. Quebre.
Se uma spec toca **5+ arquivos**, são duas specs.
