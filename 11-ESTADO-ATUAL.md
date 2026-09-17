# Estado Atual — SeuGado

**Atualizado em:** 17/09/2026
**Fase:** Fundação — F-000 e F-001 concluídas; primeiro código de produção no repositório

> Este é o único arquivo do Knowledge que muda com frequência.
> Atualize ao fim de cada fatia. O Claude sempre entrega o bloco pronto para colar.

---

## Situação

O modelo de domínio existe, foi verificado por suíte independente e passa 157/157 testes.
O repositório tem fundação: git, `pyproject.toml`, `.gitignore`, `CLAUDE.md` e ambiente
declarado. Três ADRs novas (010, 011, 012) fecharam os quatro achados urgentes da revisão
pós-F-001. O que trava o avanço não é código — são parâmetros agronômicos sem fonte.

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

```
C:\code\seugado            git, main, commit inicial 73ff3af
├── 00–12 *.md             base de conhecimento (fonte de verdade)
├── CLAUDE.md              instruções permanentes do Claude Code (papel, ambiente, relatório)
├── pyproject.toml         Python 3.12; dev: pytest, ruff, mypy strict
├── seugado/core/models.py 6 enums, 7 dataclasses frozen/slots — F-001 aprovada
├── specs/                 SPEC-001-domain-model.md
├── tests/core/            suíte do Muse Code
├── tests/conformance/     suíte independente do Claude Code
└── revisoes/              REV-001, RUNBOOK-REV-001, RELATORIO-REV-001
```

Ambiente: `.venv` por `uv` no WSL Ubuntu. O Windows hospedeiro não tem Python.
Versões medidas: Python 3.12.3, pytest 9.1.1, ruff 0.16.8, mypy 2.3.1.

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
| DT1 | 5 apontamentos de `ruff` e 18 de `mypy`, todos em `tests/` | `tests/core/`, `tests/conformance/` | RUNBOOK-REV-002 |
| DT2 | Contratos de `06` §3 divergem do modelo implementado (`Literal` vs enum, `list` vs `tuple`, frozen não declarado, `Movimentacao` ≡ `Manejo`?) | `06` §3 | ADR-013 |
| DT3 | `Cultivar` exige todos os parâmetros; a recusa por `TODO-PARAM` precisa de dono | `core/` | ADR-014 |
| DT4 | Convenções de enum e de entidade como chave de dict | `06` §7 (regras 11–12 já escritas) | ADR-015 confirma |
| DT5 | Comentário `Monday first` ambíguo em `models.py` | `models.py` | próxima spec que tocar o arquivo |
| DT6 | Tabela de alturas do `05` sem coluna de fonte | `05` | junto do `[PESQUISA]` do CT-125 |

---

## Decisões tomadas

Ver `12-REGISTRO-DE-DECISOES-ADR.md`. ADR-001 a ADR-009 na configuração inicial;
ADR-010 (eficiência de pastejo × taxa de utilização), ADR-011 (spec e kit de aceite
separados) e ADR-012 (fundação do repositório) na revisão pós-F-001.

---

## Ordem sugerida dos próximos chats

1. `[ARQUITETURA] REV-001 parte 2` → ADR-013, 014, 015 (DT2, DT3, DT4)
2. `[PESQUISA] Régua de Manejo Embrapa e alturas canônicas` → resolve B3 e DT6
3. `[PESQUISA] Densidade do dossel e eficiência de pastejo` → resolve B1 e B7, desbloqueia F-002
4. `[PESQUISA] RUE de gramíneas C4 tropicais` → resolve B2
5. `[ARQUITETURA] Schema de eventos` → antes do F-004
6. `[FATIA-002] Cálculos de forragem` → quando B1, B5 e B7 estiverem fechados

---

## Perguntas em aberto

- Earth Engine permite uso não-comercial/acadêmico nos termos atuais? Se não, qual alternativa?
- Fonte climática: INMET (estações, densidade irregular) ou reanálise (grade, menor resolução)?
- Publicar o repositório no GitHub para o Project Knowledge sincronizar de lá em vez de
  re-upload manual? (a integração existe e tem botão de Sync; falta decidir e autenticar)
- Existe fazenda-piloto acessível para validação futura? (não bloqueia MVP)

---

## Log de handoffs

_(Cole aqui o handoff de cada chat encerrado, mais recente no topo.)_

**17/09/2026 — [ARQUITETURA] Revisão pós-F-001**
Feito: ADR-010, 011 e 012 aceitas e aplicadas. Correções em `02`, `03`, `05`, `06`, `08`,
`09`, `10`, `12`. F-000 executada via RUNBOOK-REV-001: git, pyproject, ambiente medido,
157/157 testes. `CLAUDE.md` criado como instrução permanente do Claude Code.
Pendente: DT2, DT3 e DT4 → `[ARQUITETURA] REV-001 parte 2`. B7 novo. DT1 → RUNBOOK-REV-002.
Próximo: `[ARQUITETURA] REV-001 parte 2 — contratos, carregador de cultivares e convenções`.

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
