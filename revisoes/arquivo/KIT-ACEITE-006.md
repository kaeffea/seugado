# Kit de Aceite — SPEC-006 (projeção pura de eventos)

> Uso interno do testador (Antigravity). **Nunca colar no Muse Code** — o exemplo oculto perde
> valor se o agente que escreve o código o vir antes.

## Checks estruturais
- [ ] `core/projecao.py` não importa `sensing`, `planner`, `api`, `persistencia`, `psycopg` nem `pydantic`
- [ ] `SituacaoPiquete`, `EstadoPiquete`, `EstadoLote`, `Leitura`, `EstadoFazenda` — todas as
      dataclasses com `frozen=True, slots=True`; `SituacaoPiquete` é `StrEnum` com exatamente
      `OCUPADO` e `DESCANSANDO`
- [ ] `EstadoPiquete` tem exatamente: `piquete_id, fazenda_id, nome, area_ha, cultivar_id,
      metodo_pastejo, ativo, situacao, lote_atual_id, desde, dias_descanso` — nenhum campo a mais
      (em particular, **sem** `massa_kg_ms_ha` nem `aguardando_parametro`)
- [ ] `Evento` em `core/models.py` ganhou só `sequencia: int` e `corrige_evento_id: UUID | None = None`,
      nessa ordem, depois de `origem` — nenhum outro campo novo
- [ ] `projetar` assina exatamente `projetar(eventos: Sequence[Evento]) -> EstadoFazenda`
- [ ] Nenhuma função pública além de `projetar` (dataclasses e enum não contam)
- [ ] Arquivo `core/projecao.py` ≤ 300 linhas
- [ ] `mypy --strict` e `ruff check` limpos

## Caso canônico (dado na spec)
Três eventos (`piquete_criado` P1, `lote_criado` L1, `manejo_confirmado` L1→P1 em 2026-09-10):
- `piquetes[P1].situacao == OCUPADO`, `lote_atual_id == L1`, `desde == date(2026,9,10)`, `dias_descanso == 0`
- `lotes[L1].piquete_atual_id == P1`, `peso_vivo_total_kg == 9000.0`

## Caso de correção (dado na spec)
Mesmos três eventos + `piquete_alterado` corrigindo o evento 1, com `ocorrido_em` posterior aos
outros três, `area_ha=6.02`. Esperado: `piquetes[P1].area_ha == 6.02` — a correção precisa aplicar
**na posição do evento 1**, antes do `lote_criado` e do `manejo_confirmado`. Testar explicitamente
que a ordem de aplicação (não só o valor final de `area_ha`) respeita R2: construir um evento
`piquete_alterado` intermediário sem `corrige_evento_id` entre os eventos 1 e 3, com um `nome`
diferente, e confirmar que ele *não* é sobrescrito pela correção tardia (a correção mexe só em
`area_ha`, os outros campos do payload da correção substituem o piquete inteiro conforme R3 — então
o teste precisa fixar o `nome` do payload da correção igual ao que deveria valer ao final, e checar
que o `piquete_alterado` intermediário teve efeito antes da correção ser aplicada). Se a
implementação aplicar tudo por `ocorrido_em` da própria linha (ignorando a posição do corrigido),
este caso falha.

## Caso oculto 1 — dissolução durante ocupação (não mostrado na spec)
`piquete_criado` P1 (01/09), `lote_criado` L1 (02/09), `manejo_confirmado` L1→P1 em 03/09,
`lote_dissolvido` L1 em 08/09. Esperado: `L1` não existe mais em `lotes`; `piquetes[P1].situacao
== DESCANSANDO`, `lote_atual_id is None`, `desde == date(2026,9,8)`, `dias_descanso == 0` (porque
`data_referencia` é o próprio 08/09, o `ocorrido_em` mais recente do lote de eventos).

## Caso oculto 2 — duas correções independentes
Quatro eventos-base (dois piquetes, dois `piquete_alterado` diferentes, cada um corrigindo um dos
dois `piquete_criado`). Ambas as correções devem aplicar, cada uma na posição do seu próprio alvo,
sem uma interferir na outra.

## Caso oculto 3 — referência a entidade inexistente
`lote_alterado` referenciando um `entidade_id` que nunca apareceu num `lote_criado` anterior deve
levantar `ValueError`. Mesmo teste para `manejo_confirmado` com `piquete_destino_id` desconhecido.

## Caso oculto 4 — eventos sem efeito de projeção
Uma lista contendo só `piquete_criado` + `parametro_alterado` (payload qualquer, com
`entidade_id` válido) não deve levantar exceção, e o `parametro_alterado` não deve aparecer em
nenhum lugar do `EstadoFazenda` resultante.

## Fora do escopo do teste (não cobrar do Muse Code)
`combinar_confianca`, `aguardando_parametro`, `piquete_distancia`, qualquer efeito de
`manejo_recomendado`/`recusado`/`divergente`/`foto_validacao` além de "não quebra".
