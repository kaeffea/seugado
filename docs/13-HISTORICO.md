# Histórico do Projeto — SeuGado

> Arquivo de memória, contexto prévio e decisões fechadas.
> **Não deve ser lido na abertura de chats rotineiros**, preservando a economia de contexto e o cache de prompt.
> Consulte este documento apenas para arqueologia técnica ("por que decidimos X").
> O estado operacional ativo e a fila de trabalho vivem em `11-ESTADO-ATUAL.md`.

---

## 1. Correção histórica de 17/09/2026 — o F-002 nunca esteve bloqueado

O usuário reclamou, com razão, que o projeto acumulava decisão e pesquisa sem produzir código.
Conferida a acusação contra os documentos, ela procedeu em parte por um erro de bookkeeping do Arquiteto, não por natureza do método.

O `05` ("Escopo do bloqueio") e a ADR-010 dizem a mesma coisa, com todas as letras:

> `TODO-PARAM` bloqueia **default de produção** e operação com a cultivar afetada. Função pura
> que recebe o parâmetro como argumento pode ser implementada e testada com valor neutro
> declarado. **F-002 é implementável**; o que não é permitido é constante default inventada.

Mesmo assim o F-002 esteve marcado 🔒 no `11` desde a ADR-010.

**Três fatos estabelecidos:**

1. O caso de regressão canônico do `05` fixa `eficiencia_pastejo = 1.0` e `taxa_acumulo = 0.0` de propósito. Ele roda sem os parâmetros que faltam e valida consumo individual, % PV e taxa de utilização. O F-002 tinha critério de aceite executável.
2. O contrato de `dias_ocupacao` no `06` §3 recebe **só floats** — nenhum `Cultivar`. Portanto o F-002 **não dependia do F-001B** nem do schema da ADR-014. As duas fatias eram paralelas.
3. A ponte massa↔altura precisa de `densidade_kg_ha_por_cm`, que segue `TODO-PARAM`. Ela é função pura que recebe a densidade por argumento: escreve-se e testa-se com valor neutro declarado; o que não pode é entrar em produção com número inventado.

**O que mudou na prática:** a fila deixou de ser "quatro pesquisas e depois código". F-001B e F-002 foram implementadas, e o F-003 destravou pela ADR-014. Três fatias de código seguidas sem depender de nenhuma pesquisa.

---

## 2. Bloqueios e dívidas técnicas resolvidas

### Bloqueios superados
- **~~B3~~ Alturas canônicas — obter Comunicado Técnico 125 da Embrapa:** ✅ Resolvido em `[PESQUISA] Régua de Manejo Embrapa` (17/09/2026) — CT-135 cobre entrada+saída de Mombaça, Zuri, Tanzânia, Massai, Tamani, e máxima/mínima contínua de Xaraés, Piatã, Marandu, *B. decumbens*. Resíduo: entrada rotacional de Marandu/Xaraés virou B8.
- **~~B5~~ Peso médio de bezerro ausente:** ✅ **Rebaixado de bloqueio a refinamento pela ADR-014** (17/09/2026). A tabela de UA preenche o peso ausente (`coeficiente × 450`, confiança média). Buscar o peso real segue valendo como precisão. Parcialmente informado em `[PESQUISA] Regime de pastejo`: peso de desmama 180–210 kg (fonte baixa confiança, blog comercial) não é o mesmo que peso médio da fase de cria inteira. A tabela de UA por categoria (ver `05`) permite calcular consumo de lote misto sem esse número.
- **~~B8~~ Decisão de regime não tomada:** ✅ **RESOLVIDO 17/09/2026 — ADR-014 escrita e aceita.** Pesquisa (P1–P3) entregou o dado; a ADR decidiu schema por regime, comportamento na célula vazia, cadência do contínuo, fonte canônica de consumo e DT11. Ver `12`.

### Dívidas técnicas liquidadas
- **~~DT1~~ Apontamentos de `ruff` e `mypy` em `tests/`:** ✅ Resolvido em `RELATORIO-REV-002`.
- **~~DT3~~ `Cultivar` exige todos os parâmetros; a recusa por `TODO-PARAM` precisa de dono:** ✅ **Resolvido pela ADR-014** (17/09/2026). A recusa não vai para `__post_init__`: vira `resolver_parametros(cultivar, metodo)` em `core/regras.py`, porta única que devolve o bloco ou a lista de `faltantes`. Quem barra é o `planner/`.
- **~~DT6~~ Tabela de alturas do `05` sem coluna de fonte:** ✅ Resolvido em `[PESQUISA] Régua de Manejo Embrapa` (17/09/2026) — coluna de fonte e confiança adicionada, CT-135 citado.
- **~~DT11~~ O `07` §2 R10 diz "fusão só entre categorias compatíveis" e nunca define compatível:** ✅ **Resolvido pela ADR-014** (17/09/2026). `compativel[a,b] = 1 ⟺ |ordem(a) − ordem(b)| ≤ 1` na escala de UA do `05`. Escrito em `07` §2 e `03` §9.4. O limiar `≤ 1` é `HIPOTESE-CALIBRAR` — ADR de fusão de lotes, antes do F-022.
- **~~DT12~~ Caminho espúrio de migração (`src/seugado/db/migracoes/`):** ✅ **Resolvido (18/09/2026).** Diretório espúrio criado pelo Muse Code foi removido. Migração SQL padronizada exclusivamente em `db/migrations/0001_evento_e_derivadas.sql` conforme ADR-020 §2 e SPEC-005. Commit `cfcac56`.

> **Renumeração de ADR (17/09/2026):** DT2, DT3 e DT4 apontavam para ADR-014/015/016.
> O número 014 passou a ser da ADR de método de pastejo, que foi a primeira a fechar. As dívidas andaram:
> DT2 → ADR-015, DT3 → absorvida na ADR-014 (número 016 livre), DT4 → ADR-017 (ou 016).

---

## 3. Justificativas e narrativas de fluxo (17/09/2026)

### Por que a ordem mudou (17/09/2026)
A justificativa original para antecipar Alagoas (ver `01`) era **podar a fila de parâmetro**: saber quais cultivares dominam a região transformaria dez pesquisas em quatro. P1 mudou a forma do problema e, com ela, a ordem.

A fila de parâmetro deixou de ser uma lista de cultivares e virou uma **matriz esparsa (cultivar × regime)**, com a maioria das células vazia. Alagoas poda o eixo *cultivar*; a ADR-014 define o eixo *regime* — quantas faixas cada cultivar precisa ter, e o que o sistema faz quando a célula está vazia. Rodar Alagoas primeiro entrega uma lista de cultivares sem saber quantas faixas buscar para cada uma, e arrisca uma segunda passada de pesquisa nas mesmas cultivares. Rodar a ADR-014 primeiro fixa a forma da célula; aí uma passada só preenche exatamente o que falta. **Alagoas passou a ser downstream da ADR-014, não upstream.**

Três razões somam:
1. **A ADR-014 ficou barata.** Os chats 2 e 3 fizeram o trabalho caro. Dois pontos já estavam acordados (`metodo_pastejo` no piquete; alterar composição de lote é cadastro), as opções estavam montadas e o dado no `05`.
2. **Era o único bloqueio esperando decisão interna.** B1, B2, B4, B7 esperam o mundo (pesquisa). B8 esperava decisão interna.
3. **Era o único que mudava a contagem de fatias bloqueadas.** F-003 destrava; F-002, F-006 e F-007 seguiam com parâmetros pendentes.

### O que a ADR-014 decidiu
Fechada em 17/09/2026. Texto completo no `12-REGISTRO-DE-DECISOES-ADR.md`.
1. **Schema de parâmetro por regime** — `Cultivar.parametros_por_regime`, tupla de blocos, um por método de pastejo com fonte. Célula vazia = bloco ausente. Absorve DT3: recusa vira `resolver_parametros(cultivar, metodo)` em `core/regras.py`.
2. **Célula vazia** — piquete em `aguardando_parametro`: entra no estado, não entra em prescrição, e o produtor informa a altura dele, como parâmetro da fazenda (`origem: 'produtor'`, `confianca: baixa`), nunca do catálogo do `05`.
3. **Cadência do contínuo** — laço próprio e semanal, fora de `x[l,p,d]`, dentro da projeção de estado e da hierarquia do `07` §4. Fatia F-009B, pós-MVP.
4. **Consumo** — `peso_medio_kg` canônico; UA é preenchimento e exibição. Rebaixa B5.
5. **DT11** — `compativel[a,b] ⟺ |ordem(a) − ordem(b)| ≤ 1` na escala de UA.

---

## 4. Perguntas empíricas resolvidas (P1, P2, P3 e outras)

- **P1 — Ambiguidade de regime por cultivar:** ✅ **Resolvida: a ambiguidade é a norma, não a exceção.** Fontes técnicas mostram braquiárias (Marandu, Piatã) manejadas em **rotacionado** e panicuns (Tanzânia, Mombaça) manejados em **contínuo**, cada grupo com altura própria e documentada. O `05` ganhou Tabela A2 (panicum contínuo: Tanzânia 40–60 cm, Mombaça 50–75 cm) e Tabela B2 (braquiária rotacionado: Marandu 19–30 cm entrada / 15 cm saída; Piatã ≈33 cm entrada). Xaraés, *B. decumbens*, Massai, Zuri e Tamani continuam `TODO-PARAM` no regime que falta.
- **P2 — Frequência do ajuste de lotação em contínuo:** ✅ **Resolvida, sem número único de frequência.** A prática documentada é **monitoramento e gatilho** (altura de dossel ou resíduo), não taxa fixa por estação nem calendário fixo (Embrapa Infoteca-e doc/249938 e SENAR Curso 1 Aula 17). Isso pesou a favor de prescrição de contínuo de ciclo curto (semanal/sob monitoramento), decidida na ADR-014 como laço semanal (F-009B pós-MVP).
- **P3 — Separação de lotes por categoria e unidade de conversão:** ✅ **Resolvida em três partes:**
  1. Separação por categoria é prática comum (Silva, Pasto com Ciência 2019: bezerros, garrotes, bois erados, novilhas, primíparas, multíparas).
  2. Bezerro fica com a mãe até a desmama (6–8 meses, 180–210 kg, iRancho 2026).
  3. Tabela de UA da Embrapa Gado de Corte (2012): bezerro 0,25 UA, novilho 1-2a 0,50 UA, novilho 2-3a 0,75 UA, vaca/boi 1,00 UA, touro 1,25 UA (1 UA = 450 kg).
- **Régua de Manejo — CT 125 vs 135:** ✅ CT 125 é a edição original (2013); CT 135 é a revisada de 2017 (Embrapa Infoteca-e doc/1077406), de onde vêm os dados do `05`.
- **`metodo_pastejo` é do piquete ou da fazenda?** ✅ Do piquete. Fazendas mistas existem e o custo no modelo de dados é zero.
- **Produtor alterar número de animais de lote:** ✅ Cadastro de composição é evento `lote_alterado` (`06` §4). Não é ERP. Apenas compra/venda fica fora de escopo.

---

## 5. Arquivo de handoffs anteriores

### 18/09/2026 — [FATIA-004] Persistência e eventos (concluída)
- **Feito:** F-004 concluída e dividida em duas specs: `SPEC-006` (projeção pura em `core/projecao.py`, dobra `projetar()`, commit `02afb79`) e `SPEC-005` (persistência em `persistencia/eventos.py` com Pydantic, migração SQL `0001_evento_e_derivadas.sql`, commit `32d06bf`). Suíte com 254 testes passando (+2 skipped de integração de banco). ADR-020 aceita.

### 18/09/2026 — [ARQUITETURA] Schema de eventos (ADR-018 e ADR-019)
- **Feito:** ADR-018 e ADR-019 aceitas. Tabela `evento` append-only por triggers e REVOKE. Releitura por `(ocorrido_em, sequencia)`. Tabelas derivadas materializadas. Confiança combinada pelo mínimo e obrigatória.

### 18/09/2026 — [ARQUITETURA] Custo espacial e triagem de brainstorming (ADR-016)
- **Feito:** ADR-016 aceita. Matriz de distância entre centroides no modelo e penalidade no otimizador.

### 18/09/2026 — [FATIA-003] Regras de manejo (concluída)
- **Feito:** SPEC-004 implementada em `core/regras.py` com 5 funções puras: `resolver_parametros`, `apto_para_entrada`, `precisa_sair`, `urgencia` e `descanso_cumprido`. 215 testes passando. Commit `0248cad`.

### 17/09/2026 — [FATIA-002] Cálculos de forragem (concluída)
- **Feito:** F-002 implementada em `core/forragem.py` com 7 funções puras (`massa_para_altura`, `altura_para_massa`, `consumo_lote_kg_ms_dia`, `dias_ocupacao`, `taxa_utilizacao`, `consumo_individual_kg_ms_dia`, `consumo_pct_pv`). 196 testes passando. Commit `d76c7f6`.

### 17/09/2026 — [FATIA-001B] Modelo de domínio: parâmetro por regime (encerrado)
- **Feito:** F-001B concluída. SPEC-002 aplicou a ADR-014 em `models.py` — `MetodoPastejo` (3º enum), `ParametrosRegime` (2º dataclass, sem defaults), `Cultivar.parametros_por_regime` substituindo os campos planos de altura, `Piquete.metodo_pastejo`. RELATORIO-FATIA-001B: 14/14 critérios, correção de anotação mypy (SPEC-002-CORRECAO-A). Commit de código `5a600c8`, commit de documentação `94429cd`. 177/177 testes.
- **Pendente:** Nada bloqueando F-002 nem F-003.

### 17/09/2026 — [ARQUITETURA] Método de pastejo — ADR-014 (encerrado)
- **Feito:** ADR-014 escrita e aceita, fechando B8, DT3 e DT11 e rebaixando B5. Documentos atualizados: `01`, `02`, `03`, `05`, `06`, `07`, `10`, `11`, `12`. Commit `e82f0b4` (RELATORIO-REV-009, 5/5 aprovado). Manifesto SHA-256 e runbook simplificado com `sha256sum -c`. Correção registrada: F-002 nunca esteve bloqueado para código.

### 17/09/2026 — [PESQUISA] Regime de pastejo na prática brasileira (encerrado)
- **Feito:** P1, P2 e P3 respondidas com fonte rastreável. Tabelas A2 e B2 criadas no `05`. B8 passou de bloqueio de pesquisa para bloqueio de decisão.

### 17/09/2026 — [ARQUITETURA] Método de pastejo: contínuo entra no escopo? (encerrado sem ADR)
- **Feito:** Decisão adiada corretamente para aguardar dados reais. Criados B8 e perguntas P1–P3. Estabelecido que `metodo_pastejo` é do piquete e alteração de lote é cadastro (`lote_alterado`). Regra 7 incluída no `00`.

### 17/09/2026 — [PESQUISA] Régua de Manejo Embrapa (CT-135) (encerrado)
- **Feito:** CT-135 obtido; tabela de alturas do `05` reescrita com fonte e confiança por cultivar. Resolvidos B3 e DT6.

### 17/09/2026 — [ARQUITETURA] Revisão pós-F-001 · parte final
- **Feito:** Runbooks 001–007 executados. Regras consolidadas no `08` §7.1.

### 17/09/2026 — [ARQUITETURA] Revisão pós-F-001 (encerrado)
- **Feito:** ADR-010 a ADR-013 aceitas e aplicadas. Layout reorganizado com src-layout (`src/seugado/`). 157/157 testes limpos.

### 17/09/2026 — [ARQUITETURA] Revisão pós-F-001
- **Feito:** ADR-010, 011 e 012 aceitas e aplicadas. `CLAUDE.md` e `README.md` criados. Repositório no GitHub.

### 17/09/2026 — F-001 Modelo de domínio
- **Feito:** `seugado/core/models.py` aprovado; 13/13 critérios. Suíte em `tests/conformance/`.

### 17/09/2026 — Configuração inicial
- **Feito:** Base de conhecimento completa (13 arquivos), stack definida, roteiro de 22 fatias, método de trabalho com 3 papéis estabelecido.

---

## 6. Fila de pesquisas agronômicas (Q1–Q15)

> Arquivo de consulta para chats com etiqueta `[PESQUISA]`. Não deve ser lido em chats de código ou arquitetura rotineira.

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
| ~~Q14~~ | Parâmetro de cultivar precisa de `confianca` própria, e como compor com a da estimativa? | — | **Respondida e encerrada (18/09/2026) pela ADR-019:** composição é o **mínimo** numa escala ordenada sobre três fatores, com `motivo_confianca` obrigatório |
| **Q15** | Lookahead de horizonte fixo (`k ≤ 2` dias) no guloso do F-009, aproveitando a projeção do F-008? | nada; melhoria opcional do F-009 | Fora da fila até a validação mostrar que o guloso é curto demais |
| ~~Q12~~ | Conectar GitHub como fonte do Knowledge? | nada | **Respondida e encerrada (18/09/2026):** Knowledge esvaziado; a base é lida do disco em `docs/` |

---

## 7. Registro de dívidas técnicas ativas (não bloqueiam)

| # | Item | Onde | Destino |
|---|---|---|---|
| DT2 | Contratos de `06` §3 divergem do modelo implementado (`Literal` vs enum, `list` vs `tuple`, frozen não declarado) | `06` §3 | ADR-015 |
| DT4 | Convenções de enum e de entidade como chave de dict | `06` §7 | ADR-017 confirma |
| DT5 | Comentário `Monday first` ambíguo em `models.py` | `models.py` | próxima spec que tocar o arquivo |
| DT8 | `SPEC-001` contém arquivo de teste pronto, o que a ADR-011 passou a proibir | `specs/` | histórico; não reescrever |
| DT9 | Mitigação do kit de aceite não estar fisicamente escondido do Muse Code | método | avaliar se commita kit pós-Muse |
| DT10 | Caminhos legados sem `src/` em registros datados | specs/docs | decidido: não corrigir registros históricos |

