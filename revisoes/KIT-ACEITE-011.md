# KIT-ACEITE-011 — Clima

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `ClimaDia` frozen/slots com 8 campos; nenhum teste chama rede (rodar pytest com a rede bloqueada).
- Endpoints exatos: `archive-api.open-meteo.com/v1/archive` e `api.open-meteo.com/v1/forecast`.

## Caso canônico
FAO-56 exemplo 8: Ra(−20°, 03/09) = 32,2 ± 0,1.

## Casos que a spec não mostra
1. `radiacao_extraterrestre_mj_m2_dia(-9.78, date(2026, 9, 28))` = 37,47 ± 0,1.
2. `graus_dia(14, 10, 15)` = 0,0.
3. `buscar_clima` com `data_inicio = hoje − 120 dias` faz 2 requisições e não repete datas.
