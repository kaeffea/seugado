# Estado Atual — SeuGado

**Atualizado em:** 17/09/2026
**Fase:** Fundação — configuração inicial concluída, nenhum código escrito ainda

> Este é o único arquivo do Knowledge que muda com frequência.
> Atualize ao fim de cada fatia. O Claude sempre entrega o bloco pronto para colar.

---

## Situação

Planejamento e base de conhecimento completos. Stack definida. Roteiro de fatias definido.
Nada implementado. Próximo passo é desbloquear os `TODO-PARAM` críticos antes de codar,
porque três fatias da Fase 0/1 estão bloqueadas por falta de parâmetro com fonte.

---

## Progresso das fatias

| Fatia | Status |
|---|---|
| F-001 Modelo de domínio | ⬜ não iniciada |
| F-002 Cálculos de forragem | 🔒 bloqueada (`densidade_kg_ha_por_cm`) |
| F-003 Regras de manejo | 🔒 bloqueada (alturas canônicas) |
| F-004 Persistência e eventos | ⬜ não iniciada |
| F-005 Ingestão de satélite | ⬜ não iniciada |
| F-006 Modelo SAFER | 🔒 bloqueada (`rue_max_g_por_mj` C4) |
| F-007 Clima e graus-dia | 🔒 bloqueada (`temperatura_base_c`) |
| F-008 ⭐ Projeção de estado | ⬜ não iniciada |
| F-009 a F-022 | ⬜ não iniciadas |

Legenda: ⬜ não iniciada · 🟨 em andamento · 🔒 bloqueada · ✅ concluída

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

---

## Decisões tomadas

Ver `12-REGISTRO-DE-DECISOES-ADR.md`. Resumo: ADR-001 a ADR-008 registradas na
configuração inicial.

---

## Ordem sugerida dos próximos chats

1. `[PESQUISA] Régua de Manejo Embrapa e alturas canônicas` → resolve B3
2. `[PESQUISA] Densidade do dossel: kg MS/ha por cm` → resolve B1
3. `[PESQUISA] RUE de gramíneas C4 tropicais` → resolve B2
4. `[FATIA-001] Modelo de domínio` → primeira spec para o Muse Code
5. `[APRENDER] Manejo de pastagens` → pode rodar em paralelo, quando quiser

---

## Perguntas em aberto

- Earth Engine permite uso não-comercial/acadêmico nos termos atuais? Se não, qual alternativa?
- Fonte climática: INMET (estações, densidade irregular) ou reanálise (grade, menor resolução)?
- Existe fazenda-piloto acessível para validação futura? (não bloqueia MVP)
- Pesos da função objetivo: começar com os defaults sugeridos ou derivar de entrevista?

---

## Log de handoffs

_(Cole aqui o handoff de cada chat encerrado, mais recente no topo.)_

**17/09/2026 — Configuração inicial**
Feito: base de conhecimento completa (13 arquivos), stack definida, roteiro de 22 fatias,
método de trabalho com 3 papéis estabelecido.
Pendente: 6 bloqueios de parâmetro; nenhuma linha de código.
Próximo: `[PESQUISA] Régua de Manejo Embrapa e alturas canônicas`.
