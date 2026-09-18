# Estado Atual — SeuGado

**Atualizado em:** 17/09/2026
**Fase:** Fundação — F-000, F-001 e **F-001B concluídas**. F-002 e F-003 são as próximas
fatias de código, sem bloqueio de decisão nem de parâmetro.

> Este é o único arquivo do Knowledge que muda com frequência, e é por onde se começa.
> O Arquiteto escreve este arquivo direto, no repositório e no Knowledge — você não cola nada.

---

## Situação

O modelo de domínio existe, foi verificado por suíte independente e passa **177/177 testes**.
O repositório tem fundação (git, `pyproject.toml`, ambiente declarado), está publicado no GitHub,
e `ruff`, `mypy` e `pytest` estão todos limpos.

**F-001B concluída (17/09/2026).** A ADR-014 foi aplicada com sucesso em `models.py` (SPEC-002,
commit `5a600c8`): `MetodoPastejo`, `ParametrosRegime`, `Cultivar.parametros_por_regime` e
`Piquete.metodo_pastejo`.

**Transição para o Fluxo Ágil:** A partir de 17/09/2026, o fluxo foi desburocratizado: Claude Code,
runbooks manuais e manifestos SHA-256 foram aposentados. O **Antigravity (Gemini)** assumiu a
execução de terminal, verificação no WSL, faxina de lints em testes e commits diretos no Git,
entregando um relatório final conciso para fechamento no Claude Projects. F-002 e F-003 estão
100% destravadas para implementação.

O chat `[ARQUITETURA] Método de pastejo` não fechou ADR — e isso foi o resultado certo.
Ele descobriu que a decisão depende de três perguntas empíricas (P1, P2, P3), criou o
bloqueio B8, e fechou dois pontos que entram na ADR-014 já acordados. O chat
`[PESQUISA] Regime de pastejo na prática brasileira` **respondeu as três perguntas com
fonte** (ver "Perguntas em aberto → Resolvidas", abaixo): a ambiguidade de regime por
cultivar é a norma (não a exceção), o ajuste de lotação em contínuo é guiado por
monitoramento (altura/resíduo) e não por taxa fixa por estação, e a separação de lote por
categoria é prática documentada, com bezerro no lote da mãe até a desmama e uma tabela de
Unidade Animal (UA) disponível. **B8 está fechado**: a pesquisa entregou o dado e a ADR-014 tomou a decisão.
O que trava o avanço agora é só **parâmetro** — `densidade_kg_ha_por_cm`, `eficiencia_pastejo`,
RUE de C4 e temperatura base (ver `05`). As faixas de altura por regime que faltam **deixaram
de travar**: a ADR-014 as transformou em pergunta ao produtor, com confiança baixa.

---

## Correção de 17/09/2026 — o F-002 nunca esteve bloqueado

O usuário reclamou, com razão, que o projeto acumula decisão e pesquisa sem produzir código.
Fui conferir a acusação contra os documentos e **ela procede em parte, por um erro meu de
bookkeeping**, não por natureza do método.

O `05` ("Escopo do bloqueio") e a ADR-010 dizem a mesma coisa, com todas as letras:

> `TODO-PARAM` bloqueia **default de produção** e operação com a cultivar afetada. Função pura
> que recebe o parâmetro como argumento pode ser implementada e testada com valor neutro
> declarado. **F-002 é implementável**; o que não é permitido é constante default inventada.

Mesmo assim o F-002 esteve marcado 🔒 neste arquivo desde a ADR-010. Isso é divergência entre
documentos, do tipo que o `CLAUDE.md` manda relatar — e ninguém relatou porque quem mantém
este arquivo sou eu.

**Três fatos que saem disso:**

1. O caso de regressão canônico do `05` fixa `eficiencia_pastejo = 1.0` e
   `taxa_acumulo = 0.0` de propósito. Ele **roda sem os parâmetros que faltam** e valida
   consumo individual, % PV e taxa de utilização. O F-002 tem critério de aceite executável hoje.
2. O contrato de `dias_ocupacao` no `06` §3 recebe **só floats** — nenhum `Cultivar`. Portanto
   o F-002 **não depende do F-001B** nem do schema da ADR-014. As duas fatias são paralelas.
3. A ponte massa↔altura precisa de `densidade_kg_ha_por_cm`, que segue `TODO-PARAM`. Ela é
   função pura que recebe a densidade por argumento: escreve-se e testa-se com valor neutro
   declarado; o que não pode é entrar em produção com número inventado.

**O que muda na prática:** a fila deixa de ser "quatro pesquisas e depois código". F-001B e
F-002 podem ser escritas agora, em qualquer ordem, e o F-003 destravou pela ADR-014. São três
fatias de código seguidas sem depender de nenhuma pesquisa.

---

## Progresso das fatias

| Fatia | Status |
|---|---|
| F-000 Fundação do repositório | ✅ concluída (ADR-012) |
| F-001 Modelo de domínio | ✅ concluída — 13/13 critérios, 157 testes |
| **F-001B Modelo de domínio: parâmetro por regime** | ✅ **concluída** — 14/14 critérios (RELATORIO-FATIA-001B), correção de anotação mypy aplicada (SPEC-002-CORRECAO-A), commit `5a600c8`, 177/177 testes |
| F-002 Cálculos de forragem | ⬜ **implementável — não estava bloqueada.** Ver "Correção de 17/09/2026", abaixo. O que está bloqueado é **operar em produção** com cultivar real, não escrever e testar as funções |
| F-003 Regras de manejo | ✅ **destravada pela ADR-014** — depende de F-001B, não mais de decisão |
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

Layout da ADR-013, aplicado e verificado (RELATORIO-REV-004):

```
C:\code\seugado                git, main, publicado no GitHub (privado)
├── README.md                  mapa simples do projeto — ler primeiro
├── CLAUDE.md                  instruções permanentes do Claude Code
├── pyproject.toml             Python 3.12; dev: pytest, ruff, mypy strict; md fora do ruff
├── uv.lock                    versionado (ADR-012)
├── docs/                      00–12, a base de conhecimento (fonte de verdade)
├── src/seugado/core/models.py 7 enums, 8 dataclasses frozen/slots — F-001B, parâmetro por regime
├── tests/core/                suíte do Muse Code (fumaça)
├── tests/conformance/         suíte independente do Claude Code (verificação de registro)
├── specs/                     SPEC-001-domain-model.md · SPEC-002-domain-model-regime.md ·
│                              SPEC-002-CORRECAO-A-mypy-annotation.md
└── revisoes/                  REV-*, KIT-ACEITE-*, RUNBOOK-*, RELATORIO-*
```

Commits: `73ff3af` fundação + F-001 · `d06880b` ADRs 010–012 · `354382b` uv.lock ·
`3877064` dívida de lint zerada · `91d115c` ADR-013 (16 arquivos renomeados, 0 alterações) ·
`a1ef54e` caminhos hardcoded de `tests/conformance` para o src-layout ·
`e82f0b4` ADR-014, correção do status do F-002 e verificação por manifesto (RELATORIO-REV-009,
aprovada 5/5) · `94429cd` spec/runbook da F-001B (SPEC-002-CORRECAO-A,
RUNBOOK-FATIA-001B-commit) · `5a600c8` F-001B — parâmetro de altura por regime em `models.py`
(RELATORIO-FATIA-001B-commit, aprovada).
Ambiente: `.venv` por `uv` no WSL Ubuntu. O Windows hospedeiro não tem Python.
Versões medidas: Python 3.12.3, pytest 9.1.1, ruff 0.16.8, mypy 2.3.1.
Estado das ferramentas: `ruff check`, `ruff format --check`, `mypy` e `pytest` limpos, 177/177.

---

## Bloqueios ativos

| # | Bloqueio | Bloqueia | Resolver em |
|---|---|---|---|
| B1 | `densidade_kg_ha_por_cm` ausente para todas as cultivares | **produção** do F-002, não a implementação | `[PESQUISA]` |
| B2 | RUE para gramínea C4 tropical ausente (paper usa 2,45 g/MJ de C3) | F-006 | `[PESQUISA]` |
| ~~B3~~ | ~~Alturas canônicas — obter Comunicado Técnico 125 da Embrapa~~ | — | ✅ resolvido em `[PESQUISA] Régua de Manejo Embrapa` (17/09/2026) — CT-135 cobre entrada+saída de Mombaça, Zuri, Tanzânia, Massai, Tamani, e máxima/mínima contínua de Xaraés, Piatã, Marandu, *B. decumbens*. Resíduo: entrada rotacional de Marandu/Xaraés virou B8 |
| B4 | `temperatura_base_c` ausente | F-007 | `[PESQUISA]` |
| ~~B5~~ | ~~Peso médio de bezerro ausente~~ **Rebaixado de bloqueio a refinamento pela ADR-014** (17/09/2026): a tabela de UA preenche o peso ausente (`coeficiente × 450`, confiança média). Buscar o peso real segue valendo, como precisão | ~~F-002~~ | `[PESQUISA]` — parcialmente informado em `[PESQUISA] Regime de pastejo` (17/09/2026): peso de desmama 180–210 kg (fonte baixa confiança, blog comercial) não é o mesmo que peso médio da fase de cria inteira. A tabela de UA por categoria (ver `05`) permite calcular consumo de lote misto sem esse número — pode absorver o bloqueio na prática, decisão cabe à ADR-014 |
| B6 | Termos de uso atuais do Earth Engine não verificados | F-005 | `[PESQUISA]` |
| B7 | `eficiencia_pastejo` sem fonte — a faixa 0,40–0,50 mede outra grandeza (ADR-010) | **produção** do F-002, não a implementação | `[PESQUISA]` |
| ~~B8~~ | ~~Decisão de regime não tomada~~ ✅ **RESOLVIDO 17/09/2026 — ADR-014 escrita e aceita.** Pesquisa (P1–P3) entregou o dado; a ADR decidiu schema por regime, comportamento na célula vazia, cadência do contínuo, fonte canônica de consumo e DT11. Ver `12` | — | ✅ |

---

## Dívida técnica conhecida (não bloqueia)

| # | Item | Onde | Destino |
|---|---|---|---|
| ~~DT1~~ | ~~apontamentos de `ruff` e `mypy` em `tests/`~~ | — | ✅ resolvido em RELATORIO-REV-002 |
| DT8 | `SPEC-001` contém arquivo de teste pronto, o que a ADR-011 passou a proibir | `specs/` | histórico; não reescrever |
| DT10 | Caminhos `seugado/...` sem `src/` em `SPEC-001`, no texto da ADR-013 e no log de handoffs | `specs/`, `docs/12`, `docs/11` | **decidido: não corrigir.** São registros datados — a spec como foi emitida, a ADR descrevendo o estado anterior à própria decisão, e o log do dia. Corrigi apenas onde o caminho descreve o estado atual (`README`, árvore do `11`) |
| DT2 | Contratos de `06` §3 divergem do modelo implementado (`Literal` vs enum, `list` vs `tuple`, frozen não declarado, `Movimentacao` ≡ `Manejo`?) | `06` §3 | ADR-015 |
| ~~DT3~~ | ~~`Cultivar` exige todos os parâmetros; a recusa por `TODO-PARAM` precisa de dono~~ | — | ✅ **resolvido pela ADR-014** (17/09/2026). A recusa não vai para `__post_init__`: vira `resolver_parametros(cultivar, metodo)` em `core/regras.py`, porta única que devolve o bloco ou a lista de `faltantes`. Quem barra é o `planner/`. ADR-016 fica livre |
| DT4 | Convenções de enum e de entidade como chave de dict | `06` §7 (regras 11–12 já escritas) | ADR-017 confirma |
| DT9 | O Muse Code lê os arquivos do repositório direto, então o kit de aceite **não está fisicamente escondido** dele. Mitigação atual: proibição explícita na spec (`09`, "Reading scope") + conferência de escopo por `git diff` no `CLAUDE.md` | método | avaliar no `[ARQUITETURA] REV-001 parte 2` se vale commitar o kit só depois do commit do Muse |
| DT5 | Comentário `Monday first` ambíguo em `models.py` | `models.py` | próxima spec que tocar o arquivo |
| ~~DT11~~ | ~~O `07` §2 R10 diz "fusão só entre categorias compatíveis" e nunca define compatível~~ | — | ✅ **resolvido pela ADR-014** (17/09/2026). `compativel[a,b] = 1 ⟺ \|ordem(a) − ordem(b)\| ≤ 1` na escala de UA do `05`. Escrito em `07` §2 e `03` §9.4. O limiar `≤ 1` é `HIPOTESE-CALIBRAR` — ADR de fusão de lotes, antes do F-022 |
| ~~DT6~~ | ~~Tabela de alturas do `05` sem coluna de fonte~~ | — | ✅ resolvido em `[PESQUISA] Régua de Manejo Embrapa` (17/09/2026) — coluna de fonte e confiança adicionada, CT-135 citado |

> **Renumeração de ADR (17/09/2026).** DT2, DT3 e DT4 apontavam para ADR-014/015/016.
> O número 014 passou a ser da ADR de método de pastejo, que é a primeira a fechar. As três
> dívidas andaram um número para a frente: DT2 → ADR-015, DT3 → ADR-016, DT4 → ADR-017.
> **Atualização:** DT3 foi absorvido pela própria ADR-014, então o número 016 fica livre.
> Restam DT2 → ADR-015 e DT4 → ADR-017 (ou 016, quando alguém for escrever).

---

## Decisões tomadas

Ver `12-REGISTRO-DE-DECISOES-ADR.md`. ADR-001 a ADR-009 na configuração inicial;
ADR-010 (eficiência de pastejo × taxa de utilização), ADR-011 (spec e kit de aceite
separados), ADR-012 (fundação do repositório) e ADR-013 (layout do repositório) depois.
**ADR-014 escrita e aceita em 17/09/2026** — método de pastejo: parâmetro por regime, célula
vazia perguntada ao produtor, contínuo em laço próprio, `peso_medio_kg` canônico, e a definição
de categoria compatível. Absorveu DT3 e DT11. Texto completo no `12`.

---

## Ordem sugerida dos próximos chats

Regra geral: pesquisa antes de arquitetura, porque as fatias estão travadas por parâmetro e
porque pesquisa roda em Sonnet enquanto arquitetura queima cota de Opus.

O chat 2 tentou furar essa fila e **provou a regra**: uma decisão de escopo que depende de
como a pecuária brasileira funciona de fato não pode ser tomada antes de alguém ir olhar.

| # | Chat | Modelo | Resolve | Por que agora |
|---|---|---|---|---|
| ~~1~~ | ~~`[PESQUISA] Régua de Manejo Embrapa (CT 135)`~~ | Sonnet | B3, DT6 | ✅ concluído 17/09/2026 |
| ~~2~~ | ~~`[ARQUITETURA] Método de pastejo: contínuo entra no escopo?`~~ | Opus | — | ✅ encerrado 17/09/2026 **sem ADR**. Produziu B8, P1–P3 e duas ideias registradas no `01`. Ver handoff |
| ~~3~~ | ~~`[PESQUISA] Regime de pastejo na prática brasileira`~~ | Sonnet | **B8** (via P1, P2, P3) | ✅ concluído 17/09/2026. Ver handoff |
| ~~4~~ | ~~`[ARQUITETURA] Método de pastejo — ADR-014`~~ | Opus | B8, ADR-014, DT3, DT11 | ✅ concluído 17/09/2026. Ver handoff |
| ~~4B~~ | ~~`[FATIA-001B] Modelo de domínio: parâmetro por regime`~~ | Sonnet, médio | aplica a ADR-014 em `models.py` | ✅ concluído 17/09/2026 — commit `5a600c8`, 177/177 testes |
| 5 | `[PESQUISA] Mercado e pecuária de Alagoas` | Sonnet | poda a fila de parâmetro | Desceu de #4. Decide **quais** cultivares valem pesquisa; roda depois da ADR-014, que já decidiu **quantas células** cada uma precisa |
| **4C** | **`[FATIA-002] Cálculos de forragem`** | Sonnet, médio | — | **Adiantado em 17/09/2026.** Não depende do F-001B nem de pesquisa nenhuma: o contrato recebe floats e o caso canônico roda com os parâmetros neutralizados. Ver "Correção de 17/09/2026" |
| 6 | `[PESQUISA] Densidade do dossel e eficiência de pastejo` | Sonnet | B1, B7 | Sem a densidade não existe ponte kg MS/ha ↔ cm. Continua necessária **para produção**, não para implementar o F-002 |
| 7 | `[PESQUISA] Peso por categoria animal e temperatura base` | Sonnet | B5 (resíduo), B4 | Encolheu: a tabela de UA absorveu a maior parte de B5. Sobra o peso médio da fase de cria e a temperatura base |
| 8 | `[PESQUISA] RUE de gramíneas C4 tropicais` | Sonnet | B2 | O mais difícil e o mais consequente: errar aqui enviesa toda estimativa de crescimento |
| 9 | `[ARQUITETURA] REV-001 parte 2` | Opus | DT2, DT4, DT9 | Encolheu de vez: DT3 e DT11 foram fechados **dentro** da ADR-014. Sobra higiene de contrato |

### Por que a ordem mudou (17/09/2026)

A justificativa original para antecipar Alagoas (ver `01`) era **podar a fila de parâmetro**:
saber quais cultivares dominam a região transformaria dez pesquisas em quatro. P1 mudou a
forma do problema e, com ela, a ordem.

A fila de parâmetro deixou de ser uma lista de cultivares e virou uma **matriz esparsa
(cultivar × regime)**, com a maioria das células vazia. Alagoas poda o eixo *cultivar*; a
ADR-014 define o eixo *regime* — quantas faixas cada cultivar precisa ter, e o que o sistema
faz quando a célula está vazia. Rodar Alagoas primeiro entrega uma lista de cultivares sem
saber quantas faixas buscar para cada uma, e arrisca uma segunda passada de pesquisa nas
mesmas cultivares. Rodar a ADR-014 primeiro fixa a forma da célula; aí uma passada só preenche
exatamente o que falta. **Alagoas passou a ser downstream da ADR-014, não upstream.**

Três razões somam:
1. **A ADR-014 ficou barata.** Os chats 2 e 3 fizeram o trabalho caro. Dois pontos já estão
   acordados (`metodo_pastejo` no piquete; alterar composição de lote é cadastro), as opções
   estão montadas e o dado está no `05`. É chat de escrever, não de descobrir.
2. **É o único bloqueio esperando por nós.** B1, B2, B4, B7 esperam o mundo (pesquisa). B8
   espera uma decisão nossa, e o contexto que a torna barata é recente — ele decai.
3. **É o único que muda a contagem de fatias bloqueadas.** F-003 destrava; F-002, F-006 e
   F-007 seguem bloqueadas por parâmetro em qualquer ordem.

**A única razão real para manter a fila antiga** é cota de Opus apertada na semana. Se estiver,
rodar 5→8 em Sonnet primeiro é defensável e não quebra nada.

**A ADR-014 cresceu e deve absorver DT3 e DT11.** DT3 ("`Cultivar` exige todos os parâmetros;
a recusa por `TODO-PARAM` precisa de dono") deixou de ser higiene de contrato: com a matriz
esparsa confirmada, decidir o schema de parâmetro por regime **é** decidir DT3, e separá-los
faria mexer no mesmo arquivo duas vezes. DT11 ("categoria compatível") tem a tabela de UA
disponível e decide-se de graça no mesmo chat. Isso encolhe a REV-001 parte 2 para DT2, DT4
e DT9.

### O que a ADR-014 decidiu

Fechada em 17/09/2026. O texto está no `12`; aqui fica só o índice do que ela resolveu, porque
outros documentos apontam para esta lista:

1. **Schema de parâmetro por regime** — `Cultivar.parametros_por_regime`, tupla de blocos, um
   por método de pastejo com fonte. Célula vazia = bloco ausente. **Absorve DT3**: a recusa
   vira `resolver_parametros(cultivar, metodo)`, porta única em `core/regras.py`.
2. **Célula vazia** — piquete em `aguardando_parametro`: entra no estado, não entra em
   prescrição, e o **produtor informa a altura dele**, como parâmetro da fazenda
   (`origem: 'produtor'`, `confianca: baixa`), nunca do catálogo do `05`.
3. **Cadência do contínuo** — laço próprio e **semanal**, fora de `x[l,p,d]`, dentro da
   projeção de estado e da hierarquia do `07` §4. Fatia **F-009B**, pós-MVP.
4. **Consumo** — `peso_medio_kg` canônico; UA é preenchimento e exibição. **Rebaixa B5.**
5. **DT11** — `compativel[a,b] ⟺ |ordem(a) − ordem(b)| ≤ 1` na escala de UA.

Consequência que dói e ficou registrada: **F-001 reabre** (fatia F-001B).

Depois: `[FATIA-001B]`, e então `[FATIA-002] Cálculos de forragem`, com todos os parâmetros e
contratos fechados.

Em paralelo, quando quiser: `[PESQUISA] Termos de uso do Earth Engine` (B6). Não bloqueia
F-002 nem F-003, mas é a maior aposta não verificada do projeto — se o uso gratuito não valer
para este caso, F-005 e F-006 mudam de rota. Fazer antes do F-005, não depois.
E `[APRENDER] Manejo de pastagens` a qualquer momento: é didático, não produz artefato.

---

## Perguntas em aberto

### As que travavam a ADR-014 (B8) — resolvidas em `[PESQUISA] Regime de pastejo na prática brasileira` (17/09/2026)

- **P1 — ambiguidade de regime por cultivar.** ✅ **Resolvida: a ambiguidade é a norma, não
  a exceção.** Fontes técnicas mostram braquiárias (Marandu, Piatã) manejadas em
  **rotacionado** e panicuns (Tanzânia, Mombaça) manejados em **contínuo**, cada grupo com
  altura própria e documentada — nenhuma fonte trata o regime "fora" do CT-135 como raro ou
  desaconselhado (só a faixa de Marandu vinda de uma dissertação de intensificação é fronteira
  de pesquisa, não prática consolidada). Consequência direta, como a pergunta antecipava: **o
  `05` precisa de duas faixas de altura por cultivar**, e ganhou Tabela A2 (panicum contínuo:
  Tanzânia 40–60 cm, Mombaça 50–75 cm) e Tabela B2 (braquiária rotacionado: Marandu 19–30 cm
  entrada / 15 cm saída, confiança média; Piatã ≈33 cm entrada, confiança baixa, contexto
  ILPF). Xaraés, *B. decumbens*, Massai, Zuri e Tamani continuam `TODO-PARAM` no regime que
  falta — nenhuma fonte foi localizada especificamente para eles. Fontes completas com DOI e
  link estão no `05` (Tabelas A2 e B2, e notas por cultivar). Isto **não fecha a ADR-014** —
  decide o tamanho do problema, não a arquitetura da solução (schema de `regime`/altura por
  cultivar segue em aberto, marcado no `05`).

- **P2 — frequência do ajuste de lotação em contínuo.** ✅ **Resolvida, sem número único de
  frequência.** A prática documentada é **monitoramento e gatilho** (altura de dossel ou
  resíduo), não taxa fixa por estação nem calendário fixo:
  - EMBRAPA. *Ajuste de Lotação no Manejo de Pastagens* (Infoteca-e, doc/249938): "acrescenta-se
    ou retira-se animais cada vez que houver alterações [expressivas] na pastagem" — sem
    intervalo fixo, mas reconhece diferença de planejamento águas/seca no nível anual.
  - SENAR, *Ajuste de lotação e métodos de pastejo* (Curso 1 — Pastagens, Aula 17): nos
    exemplos práticos de lotação contínua usa "estimativa a cada mês" como cadência de
    reavaliação, quando o produtor não monitora altura continuamente.
  Leitura honesta: existe um piso sazonal (planejamento águas/seca) com ajuste fino disparado
  por observação de altura/resíduo — mais próximo de "sob demanda, monitorado" do que de
  "taxa fixa por estação". **Implicação para a ADR-014 (achado, não decisão):** isso pesa a
  favor de a prescrição de contínuo entrar como caminho **de ciclo curto** (semanal/quando
  monitorado) em vez de laço diário rígido ou puramente sazonal — mas a escolha entre laço
  diário, semanal ou sob demanda continua sendo decisão de arquitetura.

- **P3 — separação de lotes por categoria, e a unidade de conversão.** ✅ **Resolvida em
  três partes:**
  1. *Separação por categoria é prática comum, não depende do produtor ao ponto de ser
     imprevisível.* SILVA, M. V. P. *Apartação de bovinos de corte*. Pasto com Ciência
     (Exagro Consultoria), 2019: lista critérios usuais — "agrupar em lotes separados os
     bezerros(as), garrotes, bois erados, novilhas, primíparas e multíparas" (sexo, idade,
     peso, condição corporal). Confirma o que já havia sido verificado em 17/09/2026 (ver
     "Resolvidas", abaixo) sobre apartação ser prática documentada.
  2. *Bezerro fica com a mãe até a desmama — confirmado.* iRancho, *Desmama de bezerros de
     corte: idade, peso ideal e estratégias de manejo* (blog, 2026): desmama tipicamente aos
     6–8 meses, 180–210 kg, e é justamente o momento em que se formam "lotes padronizados de
     machos e fêmeas" — ou seja, antes da desmama o bezerro não tem lote próprio. A
     observação original do usuário estava certa.
  3. *Existe tabela de UA aceita — encontrada.* EMBRAPA GADO DE CORTE, SAC (14/09/2012):
     bezerro (0–1 ano) = 0,25 UA; novilho (1–2 anos) = 0,50 UA; novilho (2–3 anos) = 0,75 UA;
     vaca/boi = 1,00 UA; touro = 1,25 UA (base: 1 UA = vaca seca de 450 kg). Confiança
     **média** — é FAQ institucional Embrapa, mas não cita paper de origem. Tabela completa e
     nota de consistência cruzada com a fórmula linear (peso ÷ 450) estão no `05`.
  **Consequência:** isto **resolve DT11** na parte de dado (a tabela dá uma base numérica
  para "categoria compatível" — mesma UA ou adjacente), embora a regra em si ainda precise
  ser escrita numa ADR. **Absorve boa parte de B5**: o consumo de lote misto pode ser
  calculado via soma de UA × 450 kg × `consumo_pct_pv`, sem depender do peso médio exato do
  bezerro — mas o `05` também registra um achado de confiança baixa (peso de desmama,
  180–210 kg) que não é a mesma coisa que "peso médio da fase de cria inteira", então B5 não
  fecha 100%.

### Registro de perguntas abertas — dono e posição na fila

> **Por que esta tabela existe (17/09/2026).** O usuário perguntou se as perguntas levantadas
> em chats anteriores chegaram a virar pesquisa. Auditoria feita: **nenhuma se perdeu — todas
> estavam escritas** — mas estavam espalhadas por quatro lugares (`11` perguntas, `05`
> parâmetros ausentes, `01` ideias registradas, `10` tabela de pesquisa), sem nada que
> reconciliasse os quatro. Pergunta sem posição na fila parece que se multiplica sozinha.
> **Esta tabela passa a ser o registro único.** Os outros quatro lugares continuam existindo,
> mas quem quiser saber o estado de uma pergunta olha aqui.
>
> Regra: **toda pergunta tem uma linha, e toda linha tem uma posição ou uma recusa explícita.**
> "Sem dono" não é estado permitido. Se a resposta for "não vamos investigar", isso é uma
> decisão e fica escrito como tal.

| # | Pergunta | Trava o quê | Posição na fila |
|---|---|---|---|
| Q1 | Termos de uso atuais do Earth Engine permitem uso não-comercial/acadêmico? Se não, qual alternativa? (B6) | F-005, e a arquitetura de F-006 | **Pesquisa 1.** É aposta, não parâmetro: resposta ruim muda a rota, não só um número |
| Q2 | `densidade_kg_ha_por_cm` por cultivar (B1) e `eficiencia_pastejo` (B7) | **F-008, o marco ⭐** | **Pesquisa 2.** A parede real do produto. Cara: 15–20 pares (altura, massa) por cultivar |
| Q3 | Quais cultivares dominam a pecuária de Alagoas? | nada | **Pesquisa 3.** Poda a Q2 — decide para quais cultivares vale caçar densidade. Pode rodar junto com a 2 |
| Q4 | RUE de gramínea C4 tropical (B2) | F-006 | **Pesquisa 4.** Errar enviesa toda estimativa de crescimento |
| Q5 | `temperatura_base_c` de gramínea tropical (B4) | F-007 | **Pesquisa 5.** Barato e isolado |
| Q6 | Fonte climática: INMET (estações, densidade irregular) ou reanálise (grade, menor resolução)? | F-007 | **Pesquisa 5, junto com Q5.** Estava só no `10` e não tinha posição — corrigido aqui |
| Q7 | `descanso_min/max_dias` por cultivar e `taxa_senescencia` | nada — há faixa geral (21–45) e aproximação declarada | **Pesquisa 6**, opcional. Só vira prioridade se o erro medido do motor for alto |
| Q8 | A faixa de entrada rotacional do Marandu (19–30 cm) pode ser estreitada? | nada — a ADR-014 aceita faixa | **Fora da fila por decisão.** Reabre só se a validação em fazenda mostrar que a faixa larga custa caro |
| Q9 | Pastejo líder-seguidor: existe, com que ganho medido? | a ideia "Lote prioritário" do `01`, não o MVP | **Fora da fila por decisão.** É condição de entrada daquela ideia; a pesquisa roda quando a ideia for promovida, não antes |
| Q10 | Diferencial de desempenho medido contínuo × rotacionado | a ideia "Migração assistida" do `01` | **Fora da fila por decisão.** Mesmo motivo do Q9. Atenção: se o diferencial for pequeno, aquela ideia perde a razão de existir — verificar **antes** de promovê-la, nunca depois |
| Q11 | Existe fazenda-piloto acessível para validação? | nada no MVP | **Fora da fila por decisão.** Não é pesquisa web; é contato humano. Vira relevante perto do F-015 |
| Q12 | Conectar o repositório do GitHub como fonte do Project Knowledge? | nada | **Respondida: não, ainda não.** O Arquiteto escreve as duas cópias sozinho e a verificação por manifesto (`08` §7.3) cobre o risco que a conexão resolveria |

**Perguntas que a ADR-014 tirou desta tabela:** altura por regime nas células vazias (Xaraés,
*B. decumbens*, Massai, Zuri, Tamani) deixou de ser pesquisa e virou pergunta ao produtor, com
confiança baixa. Peso médio de bezerro (B5) deixou de bloquear — a tabela de UA preenche.

### Duas raias, não uma fila

Pesquisa espera o mundo; código não espera nada. Enquanto as duas dividiram a mesma fila,
pareceu que nada andava.

- **Raia A (código, Sonnet):** F-001B → F-002 → F-003 → `[ARQUITETURA] schema de eventos` →
  F-004. **Zero dependência de pesquisa.**
- **Raia B (pesquisa, Sonnet):** Q1 → Q2 (+Q3) → Q4 → Q5 (+Q6). Um chat entre fatias.

As duas raias só se encontram no **F-005**. Até lá, nenhuma pesquisa bloqueia nenhum código —
e a primeira parede de verdade é o **F-008**, que precisa do Q2.

### Resolvidas

- ~~Confirmar se a régua de manejo é o Comunicado Técnico 125 ou 135~~ → **resolvido
  17/09/2026.** CT **125** é a original (2013); a edição revisada de 2017 é o **CT 135**, e é
  dela que vêm as tabelas do `05`. Registro Infoteca-e `doc/1077406`.
- ~~`metodo_pastejo` é do piquete ou da fazenda?~~ → **do piquete.** Fazendas mistas existem, e
  o campo no piquete custa zero enquanto na fazenda custaria migração depois. Entra na ADR-014
  como ponto já acordado, não como opção.
- ~~O produtor alterar o número de animais de um lote é escopo de ERP?~~ → **não.** Foi um erro
  do Arquiteto em 17/09/2026. Cadastro de composição é `lote_alterado`, evento já previsto no
  `06` §4, e a ADR-007 existe para tornar o recálculo barato. Só o **sistema decidir comprar ou
  vender** fica fora — registrado explicitamente no "Fora de escopo" do `01`.
- ~~P1, P2, P3 (regime de pastejo na prática brasileira)~~ → **resolvidas 17/09/2026, com
  fonte.** Ver seção acima ("As que travavam a ADR-014"). B8 passa de "bloqueado por falta de
  dado" para "bloqueado por falta de decisão de arquitetura" (ADR-014).

---

## Log de handoffs

_(Cole aqui o handoff de cada chat encerrado, mais recente no topo.)_

**17/09/2026 — [FATIA-001B] Modelo de domínio: parâmetro por regime (encerrado)**
Feito: **F-001B concluída.** SPEC-002 aplicou a ADR-014 em `models.py` — `MetodoPastejo`
(3º enum), `ParametrosRegime` (2º dataclass, sem defaults), `Cultivar.parametros_por_regime`
substituindo os campos planos de altura, `Piquete.metodo_pastejo`. RELATORIO-FATIA-001B:
14/14 critérios, ✅ com uma ressalva de mypy (duas linhas de teste sem
`# type: ignore[comparison-overlap]`, rule 11 do `06` §7). Ressalva **não** foi remendada
direto: fui por spec de correção (SPEC-002-CORRECAO-A), como o método exige — conserto de
código sempre por spec nova, nunca por mim nem pelo Claude Code editando por iniciativa
própria. Reaplicada, reverificada, `mypy` limpo. Commit de código `5a600c8`
(RELATORIO-FATIA-001B-commit, aprovada, 177/177 testes), commit auxiliar de documentação
`94429cd`, push aceito.
Erro de método capturado no caminho: ao regravar `RUNBOOK-FATIA-001B-commit.md` corrigido,
reaproveitei o mesmo caminho de origem local e o disco ficou com a versão antiga — o próprio
bug que o `08` §7.1 documenta. Peguei pelo hash (não bati com o que eu pretendia gravar),
regravei com caminho novo, confirmei byte a byte antes de seguir.
Pendente: nada bloqueando F-002 nem F-003 — as duas destravadas, sem dependência de pesquisa.
Próximo: `[FATIA-002] Cálculos de forragem` ou `[FATIA-003] Regras de manejo`, as duas em
Sonnet, esforço médio; ver "Ordem sugerida dos próximos chats".

**17/09/2026 — [ARQUITETURA] Método de pastejo — ADR-014 (encerrado)**
Feito: **ADR-014 escrita e aceita**, fechando B8, DT3 e DT11 e rebaixando B5. Cinco decisões:
(1) altura passa a ser do par cultivar × regime, em `parametros_por_regime`, com
`resolver_parametros` como porta única — a recusa por `TODO-PARAM` ganhou dono e saiu do
`__post_init__`; (2) célula vazia vira `aguardando_parametro` + pergunta ao produtor, com a
guarda de que altura de produtor é parâmetro da fazenda e nunca sobe para o `05`; (3) contínuo
em laço semanal próprio, fora de `x[l,p,d]` mas dentro da projeção de estado e da hierarquia
do `07` §4 — corrige de propósito o erro (b) do chat 2; (4) `peso_medio_kg` canônico, UA como
preenchimento; (5) categoria compatível = distância ≤ 1 na escala de UA, limiar marcado
`HIPOTESE-CALIBRAR`. Documentos reescritos pelo Arquiteto nos dois lugares: `01` (fronteira do
contínuo no fora-de-escopo), `02` (verbetes de método de pastejo, parâmetros por regime,
aguardando parâmetro, UA e categoria), `03` (§3, §6.1, §6.5, §9.4), `05` (formato canônico
inteiro + uso da tabela de UA), `06` (§3 contrato, §5 modelo de dados), `07` (§2 escopo do
problema diário, R10 definido, R11 novo), `10` (F-001B, F-009B, tabelas de pesquisa e de ADR),
`11` e `12`.
Erros/limitações registrados de propósito: o `05` **não** estava na lista de impacto que o
usuário passou, mas o "Formato canônico no código" contradizia a decisão de frente — foi
reescrito e está sinalizado. O limiar `≤ 1` de categoria compatível é escolha nossa, não dado.
O fallback de UA para bezerro (112,5 kg) fica abaixo do peso de desmama conhecido (180–210 kg)
e erra na direção do super-pastejo — por isso confiança média obrigatória, e B5 continua
aberto como refinamento.
Pendente: **F-001B** (spec que aplica o schema em `models.py`) não foi escrita. Commit **feito**
(`e82f0b4`, RELATORIO-REV-009 aprovada 5/5).
Terceiro erro meu, e o que mais custou tempo: o `RUNBOOK-REV-008` reprovou por **duas premissas
minhas erradas**, não por disco ruim — pedi `grep aguardando_parametro` num arquivo onde escrevi
o verbete com acento e espaço, e fixei o tamanho de `docs/10` antes de editar `docs/10` de novo.
Conserto aplicado no método, não só neste runbook: **`08` §7.3 e `CLAUDE.md` agora proíbem
tamanho em bytes e `grep` escrito à mão dentro de runbook**. No lugar, o Arquiteto relê a
gravação do disco e compara byte a byte na hora, emite `revisoes/MANIFESTO-<ID>.sha256` gerado
dos bytes reais, e o runbook carrega uma linha só: `sha256sum -c`. Estreado no REV-009, 14/14 OK.
Dois erros meus, corrigidos no fim do chat: (a) mandei o usuário "pedir o runbook no próximo
chat" em vez de escrevê-lo, contra a regra de que toda ação de terminal vira runbook;
(b) repeti DT7 como pendente quando o usuário já havia colado o `00` novo há vários chats —
DT7 removido deste arquivo.
Achado maior, registrado em "Correção de 17/09/2026": **o F-002 nunca esteve bloqueado**.
O `05` e a ADR-010 sempre disseram que `TODO-PARAM` barra produção, não implementação, e este
arquivo o marcava 🔒 mesmo assim. F-001B e F-002 são paralelas; F-003 destravou pela ADR-014.
Próximo: `[FATIA-001B] Modelo de domínio: parâmetro por regime` **ou**
`[FATIA-002] Cálculos de forragem` — as duas independentes, ambas em Sonnet, esforço médio.

**17/09/2026 — [PESQUISA] Regime de pastejo na prática brasileira (encerrado)**
Feito: P1, P2 e P3 respondidas com fonte rastreável (ver "Perguntas em aberto → Resolvidas").
Resumo: (P1) ambiguidade de regime por cultivar é a norma — braquiária roda em rotacionado
(Marandu, Piatã) e panicum roda em contínuo (Tanzânia, Mombaça), cada um com altura própria;
`05` ganhou Tabela A2 (panicum contínuo) e Tabela B2 (braquiária rotacionado). (P2) ajuste de
lotação em contínuo é por monitoramento/gatilho (altura ou resíduo), não taxa fixa por
estação — achado favorece ciclo curto na prescrição, não decide o laço. (P3) separação por
categoria é prática comum, bezerro fica com a mãe até a desmama (confirma observação do
usuário), e existe tabela de UA por categoria etária (Embrapa CNPGC, 2012) — resolve DT11 na
parte de dado e absorve boa parte de B5. `05` e `11` reescritos com todas as fontes, DOIs e
links. B8 passa de "falta pesquisa" para "falta decisão de arquitetura".
Erros/limitações registrados de propósito: a faixa de Marandu rotacionado (19–30 cm) não tem
valor único nem régua oficial — são três fontes convergentes, uma delas (Andrade 2008) citada
apenas de forma indireta, via outro artigo, sem verificação no documento primário. A faixa de
Piatã rotacionado (≈33 cm) vem de estudo em sistema ILPF, não pasto aberto puro. Xaraés e
*B. decumbens* seguem sem fonte de rotacionado — não foram extrapolados de Marandu/Piatã.
Pendente: a ADR-014 em si (schema de `metodo_pastejo`/altura por regime, o que fazer com a
ambiguidade confirmada). B5 não fecha 100% (peso médio de bezerro segue TODO-PARAM, só o
peso de desmama foi encontrado, confiança baixa). DT11 tem dado mas não tem regra escrita.
Próximo: usuário decide entre `[PESQUISA] Mercado e pecuária de Alagoas` (seguir a fila,
Sonnet) ou `[ARQUITETURA] Método de pastejo — ADR-014` (adiantar a decisão agora que a
pesquisa está pronta, Opus, esforço alto) — ver trade-off registrado em "Ordem sugerida".

**17/09/2026 — [ARQUITETURA] Método de pastejo: contínuo entra no escopo? (encerrado sem ADR)**
Feito: a decisão foi **corretamente adiada**. O chat isolou as três perguntas empíricas que a
travam (P1, P2, P3), criou B8, e fechou dois pontos que entram na ADR-014 já acordados —
`metodo_pastejo` é do **piquete**, e alterar composição de lote é **cadastro, não ERP**.
Duas ideias foram registradas no `01`: lote prioritário na função objetivo, e a antecipação da
pesquisa de Alagoas (que deixou de ser marketing e virou poda da fila de parâmetro).
O `00` ganhou a regra 7: o que o usuário diz sobre a vida real da fazenda é brainstorming a
validar, nunca requisito aceito nem pedido recusado.
Erros do Arquiteto, registrados de propósito: (a) afirmou que contínuo não tem decisão de
manejo — falso; (b) propôs arquitetura que escondia o piquete contínuo do otimizador, o que o
piora, porque o contínuo é válvula de escape acima da fusão de lotes na hierarquia do `07` §4;
(c) classificou alteração de rebanho pelo produtor como fora de escopo; (d) leu a ADR-005 como
bloqueio para priorizar lote, quando ela só proíbe *quantificar* ganho, não *ordenar*.
Pendente: B8 e a ADR-014 inteira. DT11 (definir "categoria compatível"). DT7, versão `-b`.
Próximo: `[PESQUISA] Regime de pastejo na prática brasileira`, em Sonnet, esforço médio.

**17/09/2026 — [PESQUISA] Régua de Manejo Embrapa (CT-135) (encerrado)**
Feito: CT-135 obtido (Costa & Queiroz, Embrapa Gado de Corte) e tabela de alturas do `05`
reescrita com fonte e confiança por cultivar, separando pastejo contínuo (braquiárias) de
rotacionado (panicuns). Resolve B3 e DT6. Corrigida premissa inicial: Zuri e Tamani **são**
cobertos pelo CT-135 — só Cameroon e *B. humidicola* ficam de fora.
Pendente: achado novo — CT-135 só cobre Marandu/Xaraés em contínuo, não em rotacional; o
`TODO-PARAM` de entrada rotacional dessas duas cultivares agora depende de uma decisão de
regime, não de um dado ausente. Pendência secundária: confirmar número da série (125 vs. 135).
Próximo: `[PESQUISA] Densidade do dossel e eficiência de pastejo`, em Sonnet, esforço médio.

**17/09/2026 — [ARQUITETURA] Revisão pós-F-001 · parte final**
Feito: sete runbooks executados (001–007); 003 e 005 reprovados corretamente por
pré-condição que o próprio Arquiteto quebrava, e cada reprovação virou regra permanente no
`CLAUDE.md` e no `08` §7.1 — passo zero, precedência sobre cláusula de runbook, verificação
antes do commit, conferência de conteúdo e não de presença.
Achado de ferramenta: reaproveitar o mesmo caminho de origem nas gravações do Arquiteto
repetia conteúdo antigo silenciosamente. Apagou a tabela do CT-135 do `05` e duas edições do
`CLAUDE.md`. Contorno: caminho novo a cada gravação + conferência de tamanho no disco.
Só o executor independente pegou — é a melhor evidência a favor da ADR-011 até agora.
Pendente: commit desta última edição do `11` (o passo zero do próximo runbook recolhe).
Próximo: `[ARQUITETURA] Método de pastejo: contínuo entra no escopo?`, em Opus, esforço alto.

**17/09/2026 — [ARQUITETURA] Revisão pós-F-001 (encerrado)**
Feito: ADR-010 a ADR-013 aceitas e aplicadas. Layout reorganizado (`docs/`, `src/seugado/`)
com histórico preservado por `git mv`. Quatro runbooks executados; 001, 002 e 004 aprovados,
003 corretamente reprovado por pré-condição que eu mesmo havia quebrado — lição virou o
"passo zero" do `CLAUDE.md` e a §7.1 do `08`. Quatro ferramentas limpas, 157/157.
Pendente: B1–B7 (parâmetros), DT2, DT3, DT4 e DT9 → `[ARQUITETURA] REV-001 parte 2`,
depois das quatro pesquisas.
Próximo: `[PESQUISA] Régua de Manejo Embrapa (CT 135)`, em Sonnet, esforço médio.

**17/09/2026 — [ARQUITETURA] Revisão pós-F-001**
Feito: ADR-010, 011 e 012 aceitas e aplicadas em `02`, `03`, `05`, `06`, `07`, `08`, `09`,
`10`, `12`. F-000 e a dívida de lint executadas via RUNBOOK-REV-001 e 002: git, pyproject,
uv.lock versionado, quatro ferramentas limpas, 157/157. `CLAUDE.md` e `README.md` criados.
Repositório publicado no GitHub. Varredura de coerência feita: corrigidos `07` (fatias com
número errado, pesos sem marcação), `02` (vocabulário novo do método), `08` (afirmação forte
demais sobre cache de Knowledge), `09` (regra explícita de quem escreve teste).
Pendente: DT2, DT3, DT4 → `[ARQUITETURA] REV-001 parte 2`, **depois** das quatro pesquisas.
DT7: o usuário precisa colar o `00` novo no campo de instruções do Project.
Próximo: `[PESQUISA] Régua de Manejo Embrapa (CT 135)`.

**17/09/2026 — F-001 Modelo de domínio**
Feito: `seugado/core/models.py` (6 enums, 7 dataclasses frozen/slots) aprovado; 13/13
critérios. Suíte independente em `tests/conformance/`. Ambiente `.venv` (uv) no WSL Ubuntu.
Pendente: REV-001 (U1–U4). `pyproject.toml` e git inexistentes na época.
Próximo: `[ARQUITETURA] Revisão pós-F-001`.

**17/09/2026 — Configuração inicial**
Feito: base de conhecimento completa (13 arquivos), stack definida, roteiro de 22 fatias,
método de trabalho com 3 papéis estabelecido.
Pendente: 6 bloqueios de parâmetro; nenhuma linha de código.
Próximo: `[PESQUISA] Régua de Manejo Embrapa e alturas canônicas`.
