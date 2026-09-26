# KIT-ACEITE-012 — SAFER

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- Só importa `math` e `dataclasses`; `SaferForaDaFaixa` herda de `ValueError`.
- ETf usa `t0_c` (°C).

## Caso canônico
Exemplo resolvido da spec (taxa 107,6 ± 1,0).

## Casos que a spec não mostra
1. `ndvi=0.62, red=0.06, nir=0.28, rg=17.5, t=24.0, ra=33.4, et0=4.2, rue=2.31` → albedo 0,1438 ± 0,0005; t0_c 29,66 ± 0,1; etf 0,355 ± 0,005; taxa 39,0 ± 0,5.
2. `ndvi=0.10` (f_rfa ≤ 0) → taxa 0,0, sem exceção.
3. `rg=40, ra=35` (tau ≥ 1) → `ValueError`.
