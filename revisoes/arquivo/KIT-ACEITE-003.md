# KIT-ACEITE-003 — SPEC-003 (`core/forragem.py`)

**Nunca colar no Muse Code.** Este arquivo é só para o Antigravity (testador). Se houver
qualquer sinal de que o Muse viu este arquivo, relate como violação (`CLAUDE.md`, regras de
verificação).

## O que esta fatia criou

`src/seugado/core/forragem.py`, novo, com sete funções puras: `massa_para_altura`,
`altura_para_massa`, `consumo_lote_kg_ms_dia`, `dias_ocupacao`, `taxa_utilizacao`,
`consumo_individual_kg_ms_dia`, `consumo_pct_pv`. Nenhum arquivo existente deveria ter sido
tocado.

## Checagens estruturais

- `git status` / `git diff --stat` mostram **só** `src/seugado/core/forragem.py` e
  `tests/core/test_forragem.py` no lado de produção. Qualquer toque em `tests/conformance/`,
  `docs/`, `revisoes/` ou `specs/` é violação de escopo.
- `forragem.py` não importa nada de `seugado.core.models`, `sensing`, `planner`, `api`, nem
  biblioteca de banco. Import esperado: no máximo `collections.abc.Sequence` (stdlib).
- As sete assinaturas batem exatamente com a spec, campo a campo e tipo a tipo — em especial
  `dias_ocupacao`, que é contrato existente do `06` §3 e não pode ter mudado de forma alguma
  (ordem dos parâmetros, nomes, tipos, tipo de retorno).
- Nenhuma das sete funções tem valor default em nenhum parâmetro — em particular,
  `densidade_kg_ha_por_cm` e `eficiencia_pastejo` nunca podem ter default, porque isso seria
  reintroduzir como "default de produção" um `TODO-PARAM` (`05`, B1 e B7; ADR-010). Isto é o
  ponto mais importante desta revisão — um default silencioso aqui é exatamente o bug que a
  regra 1 do projeto existe para prevenir.
- Nenhuma outra função pública além das sete listadas.
- `forragem.py` está abaixo de 300 linhas.
- `__init__.py` de `src/seugado/core/` e `tests/core/` continuam vazios.
- Todas as funções são puras: sem I/O, sem estado global, sem `print`, sem leitura de arquivo
  ou variável de ambiente.

## Caso oculto — não mostrado na spec (ADR-011)

A spec só exercita `dias_ocupacao` com `taxa_acumulo_kg_ms_ha_dia = 0.0` (o caso canônico
neutralizado). Isto não verifica a parte nova e não trivial da fórmula — o ajuste analítico
para crescimento durante a ocupação. Construa, na sua suíte independente, este caso:

```
massa_atual_kg_ms_ha      = 3000.0
massa_residuo_kg_ms_ha    = 2000.0
taxa_acumulo_kg_ms_ha_dia = 50.0
area_ha                   = 10.0
eficiencia_pastejo        = 0.8
consumo_lote_kg_ms_dia    = 4000.0
```

Cálculo de referência (não é fonte agronômica — é só a fórmula da spec aplicada):

```
numerador   = (3000 - 2000) * 10 * 0.8 = 8000
denominador = 4000 - (50 * 10 * 0.8)   = 4000 - 400 = 3600
dias_ocupacao esperado = 8000 / 3600 ≈ 2.2222
```

Tolerância: ±0.01 dia. Se o resultado bater com a fórmula ingênua sem ajuste de crescimento
(8000 / 4000 = 2.0), a implementação ignorou o crescimento durante a ocupação — reprove.

Confirme também o caso de fronteira do denominador não-positivo: com os mesmos números acima
mas `taxa_acumulo_kg_ms_ha_dia = 500.0` (denominador = 4000 − 4000 = 0), o retorno deve ser
exatamente `float("inf")`, não uma exceção de divisão por zero nem um número finito grande.

## Segundo caso oculto — `massa_para_altura` / `altura_para_massa`

Confirme que as duas funções são inversas exatas para pelo menos dois valores de densidade
diferentes dos usados no worked example da spec (que usa 100.0). Sugestão: densidade 250.0,
altura 12.0 → massa 3000.0, e o caminho de volta deve devolver 12.0 exatamente (dentro de
erro de ponto flutuante, tolerância 1e-9).

## Terceiro caso oculto — validação

Confirme que `dias_ocupacao` levanta `ValueError` (não retorna `0.0` nem `inf`) quando
`consumo_lote_kg_ms_dia <= 0` — este é um caso de entrada inválida, diferente do caso
`massa_atual <= massa_residuo` (que retorna `0.0`) e diferente do denominador de crescimento
não-positivo (que retorna `inf`). As três saídas são deliberadamente distintas; confundir
qualquer uma das três é reprovação.

## Caso canônico (visível na spec, confirme mesmo assim)

- `taxa_utilizacao(4000.0, 2240.0) == 0.44` (±0.01)
- `consumo_individual_kg_ms_dia(1760.0, 5.81, 4.0, 220) ≈ 11.62` (±0.05)
- `consumo_pct_pv(11.62, 479.0) ≈ 2.42` (±0.02)
- `dias_ocupacao(4000.0, 2240.0, 0.0, 5.81, 1.0, 2556.4) ≈ 4.0` (±0.05)
- `consumo_lote_kg_ms_dia([(1, 300.0, 0.022)]) == 6.6`
- `consumo_lote_kg_ms_dia([]) == 0.0`, sem levantar exceção

## Checagem de escopo

`git status` / `git diff --stat` — ver "Checagens estruturais", acima.

## Formato do relatório

`revisoes/RELATORIO-FATIA-002.md`, formato do `CLAUDE.md`. Cubra os critérios de aceite da
SPEC-003 (não copie os deste kit — os deste kit são as evidências, não os itens da tabela).
