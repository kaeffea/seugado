# Estado Atual — SeuGado

**Atualizado em:** 17/09/2026
**Fase:** Fundação — F-000 e F-001 concluídas; primeiro código de produção no repositório

> Este é o único arquivo do Knowledge que muda com frequência, e é por onde se começa.
> O Arquiteto escreve este arquivo direto, no repositório e no Knowledge — você não cola nada.

---

## Situação

O modelo de domínio existe, foi verificado por suíte independente e passa 157/157 testes.
O repositório tem fundação (git, `pyproject.toml`, `CLAUDE.md`, ambiente declarado), está
publicado no GitHub, e `ruff`, `mypy` e `pytest` estão todos limpos. Três ADRs novas
(010, 011, 012) fecharam os quatro achados urgentes da revisão pós-F-001.
**O que trava o avanço não é código — são parâmetros agronômicos sem fonte.**

---

## Progresso das fatias

| Fatia | Status |
|---|---|
| F-000 Fundação do repositório | ✅ concluída (ADR-012) |
| F-001 Modelo de domínio | ✅ concluída — 13/13 critérios, 157 testes |
| F-002 Cálculos de forragem | 🔒 bloqueada (`densidade_kg_ha_por_cm`, `eficiencia_pastejo`) |
| F-003 Regras de manejo | 🔒 bloqueada (alturas canônicas) |
| F-004 Persistência e eventos | ⬜ não iniciada — exige `[ARQUITETURA] Schema de eventos` antes |
| F-005 Ingestão de satélite | ⬜ não iniciada |
| F-006 Modelo SAFER | 🔒 bloqueada (`rue_max_g_por_mj` C4) |
| F-007 Clima e graus-dia | 🔒 bloqueada (`temperatura_base_c`) |
| F-008 ⭐ Projeção de estado | ⬜ não iniciada |
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
├── src/seugado/core/models.py 6 enums, 7 dataclasses frozen/slots — F-001, intocada
├── tests/core/                suíte do Muse Code (fumaça)
├── tests/conformance/         suíte independente do Claude Code (verificação de registro)
├── specs/                     SPEC-001-domain-model.md
└── revisoes/                  REV-*, KIT-ACEITE-*, RUNBOOK-*, RELATORIO-*
```

Commits: `73ff3af` fundação + F-001 · `d06880b` ADRs 010–012 · `354382b` uv.lock ·
`3877064` dívida de lint zerada · `91d115c` ADR-013 (16 arquivos renomeados, 0 alterações) ·
`a1ef54e` caminhos hardcoded de `tests/conformance` para o src-layout.
Ambiente: `.venv` por `uv` no WSL Ubuntu. O Windows hospedeiro não tem Python.
Versões medidas: Python 3.12.3, pytest 9.1.1, ruff 0.16.8, mypy 2.3.1.
Estado das ferramentas: `ruff check`, `ruff format --check`, `mypy` e `pytest` limpos, 157/157.

---

## Bloqueios ativos

| # | Bloqueio | Bloqueia | Resolver em |
|---|---|---|---|
| B1 | `densidade_kg_ha_por_cm` ausente para todas as cultivares | F-002 | `[PESQUISA]` |
| B2 | RUE para gramínea C4 tropical ausente (paper usa 2,45 g/MJ de C3) | F-006 | `[PESQUISA]` |
| B3 | Alturas canônicas — obter Comunicado Técnico 125 da Embrapa | F-003 | `[PESQUISA]` |
| B4 | `temperatura_base_c` ausente | F-007 | `[PESQUISA]` |
| B5 | Peso médio de bezerro ausente | F-002 | `[PESQUISA]` |
| B6 | Termos de uso atuais do Earth Engine não verificados | F-005 | `[PESQUISA]` |
| B7 | `eficiencia_pastejo` sem fonte — a faixa 0,40–0,50 mede outra grandeza (ADR-010) | F-002 | `[PESQUISA]` |

---

## Dívida técnica conhecida (não bloqueia)

| # | Item | Onde | Destino |
|---|---|---|---|
| ~~DT1~~ | ~~apontamentos de `ruff` e `mypy` em `tests/`~~ | — | ✅ resolvido em RELATORIO-REV-002 |
| DT7 | O campo de instruções do Project descreve o fluxo antigo (entregar blocos para colar, pedir re-upload) | instruções do Project | usuário cola o `00` novo |
| DT8 | `SPEC-001` contém arquivo de teste pronto, o que a ADR-011 passou a proibir | `specs/` | histórico; não reescrever |
| DT10 | Caminhos `seugado/...` sem `src/` em `SPEC-001`, no texto da ADR-013 e no log de handoffs | `specs/`, `docs/12`, `docs/11` | **decidido: não corrigir.** São registros datados — a spec como foi emitida, a ADR descrevendo o estado anterior à própria decisão, e o log do dia. Corrigi apenas onde o caminho descreve o estado atual (`README`, árvore do `11`) |
| DT2 | Contratos de `06` §3 divergem do modelo implementado (`Literal` vs enum, `list` vs `tuple`, frozen não declarado, `Movimentacao` ≡ `Manejo`?) | `06` §3 | ADR-014 |
| DT3 | `Cultivar` exige todos os parâmetros; a recusa por `TODO-PARAM` precisa de dono | `core/` | ADR-015 |
| DT4 | Convenções de enum e de entidade como chave de dict | `06` §7 (regras 11–12 já escritas) | ADR-016 confirma |
| DT9 | O Muse Code lê os arquivos do repositório direto, então o kit de aceite **não está fisicamente escondido** dele. Mitigação atual: proibição explícita na spec (`09`, "Reading scope") + conferência de escopo por `git diff` no `CLAUDE.md` | método | avaliar no `[ARQUITETURA] REV-001 parte 2` se vale commitar o kit só depois do commit do Muse |
| DT5 | Comentário `Monday first` ambíguo em `models.py` | `models.py` | próxima spec que tocar o arquivo |
| DT6 | Tabela de alturas do `05` sem coluna de fonte | `05` | junto do `[PESQUISA]` do CT-125 |

---

## Decisões tomadas

Ver `12-REGISTRO-DE-DECISOES-ADR.md`. ADR-001 a ADR-009 na configuração inicial;
ADR-010 (eficiência de pastejo × taxa de utilização), ADR-011 (spec e kit de aceite
separados) e ADR-012 (fundação do repositório) na revisão pós-F-001.

---

## Ordem sugerida dos próximos chats

Pesquisa vem antes de arquitetura por dois motivos: F-002 e F-003 estão travadas por
parâmetro, não por decisão; e pesquisa roda em Sonnet, enquanto arquitetura consome a cota
semanal de Opus — gasta-se o barato enquanto o caro espera.

| # | Chat | Modelo | Resolve | Por que agora |
|---|---|---|---|---|
| 1 | `[PESQUISA] Régua de Manejo Embrapa (CT 125)` | Sonnet | B3, DT6 | Um documento público cobre 8 cultivares de uma vez e substitui a tabela de alturas inteira. Maior retorno por esforço |
| 2 | `[PESQUISA] Densidade do dossel e eficiência de pastejo` | Sonnet | B1, B7 | Sem a densidade não existe ponte kg MS/ha ↔ cm, que é o cálculo central do F-002 |
| 3 | `[PESQUISA] Peso por categoria animal e temperatura base` | Sonnet | B5, B4 | Fecha o último bloqueio do F-002 e prepara o F-007 |
| 4 | `[PESQUISA] RUE de gramíneas C4 tropicais` | Sonnet | B2 | O mais difícil e o mais consequente: errar aqui enviesa toda estimativa de crescimento |
| 5 | `[ARQUITETURA] REV-001 parte 2` | Opus | DT2, DT3, DT4, DT9 | Os contratos precisam estar certos **antes** de escrever a spec do F-002, que os consome |

Depois: `[FATIA-002] Cálculos de forragem`, com todos os parâmetros e contratos fechados.

Em paralelo, quando quiser: `[PESQUISA] Termos de uso do Earth Engine` (B6). Não bloqueia
F-002 nem F-003, mas é a maior aposta não verificada do projeto — se o uso gratuito não valer
para este caso, F-005 e F-006 mudam de rota. Fazer antes do F-005, não depois.
E `[APRENDER] Manejo de pastagens` a qualquer momento: é didático, não produz artefato.

---

## Perguntas em aberto

- Earth Engine permite uso não-comercial/acadêmico nos termos atuais? Se não, qual alternativa?
- Fonte climática: INMET (estações, densidade irregular) ou reanálise (grade, menor resolução)?
- Conectar o repositório do GitHub como fonte do Project Knowledge? Já está publicado. O
  ganho é fonte única; o custo é apagar as 12 cópias do Knowledge para não duplicar contexto,
  e verificar a leitura antes. **Recomendação atual: não conectar ainda** — o Arquiteto já
  escreve as duas cópias sozinho, então a sincronização resolveria um problema que não existe
  mais.
- Existe fazenda-piloto acessível para validação futura? (não bloqueia MVP)

---

## Log de handoffs

_(Cole aqui o handoff de cada chat encerrado, mais recente no topo.)_

**17/09/2026 — [ARQUITETURA] Revisão pós-F-001 (encerrado)**
Feito: ADR-010 a ADR-013 aceitas e aplicadas. Layout reorganizado (`docs/`, `src/seugado/`)
com histórico preservado por `git mv`. Quatro runbooks executados; 001, 002 e 004 aprovados,
003 corretamente reprovado por pré-condição que eu mesmo havia quebrado — lição virou o
"passo zero" do `CLAUDE.md` e a §7.1 do `08`. Quatro ferramentas limpas, 157/157.
Pendente: B1–B7 (parâmetros), DT2, DT3, DT4 e DT9 → `[ARQUITETURA] REV-001 parte 2`,
depois das quatro pesquisas.
Próximo: `[PESQUISA] Régua de Manejo Embrapa (CT 125)`, em Sonnet, esforço médio.

**17/09/2026 — [ARQUITETURA] Revisão pós-F-001**
Feito: ADR-010, 011 e 012 aceitas e aplicadas em `02`, `03`, `05`, `06`, `07`, `08`, `09`,
`10`, `12`. F-000 e a dívida de lint executadas via RUNBOOK-REV-001 e 002: git, pyproject,
uv.lock versionado, quatro ferramentas limpas, 157/157. `CLAUDE.md` e `README.md` criados.
Repositório publicado no GitHub. Varredura de coerência feita: corrigidos `07` (fatias com
número errado, pesos sem marcação), `02` (vocabulário novo do método), `08` (afirmação forte
demais sobre cache de Knowledge), `09` (regra explícita de quem escreve teste).
Pendente: DT2, DT3, DT4 → `[ARQUITETURA] REV-001 parte 2`, **depois** das quatro pesquisas.
DT7: o usuário precisa colar o `00` novo no campo de instruções do Project.
Próximo: `[PESQUISA] Régua de Manejo Embrapa (CT 125)`.

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
