# KIT-ACEITE-014 — Estado projetado

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `estado.py` sem import de `psycopg`, `httpx`, `ee`; `carga.py` sem commit.
- `faltantes` sem duplicatas e na ordem de inserção.

## Caso canônico
Exemplos resolvidos da spec (2038,04; 1113,75; confiança média por altura de 20 dias).

## Casos que a spec não mostra
1. `avancar_massa_um_dia(2000, 50, 0, 4, None)` → 2050.
2. `confianca_estimativa(None, None, 50, True)` → `(BAIXA, "nenhuma imagem de satélite sem nuvem nos últimos 30 dias")`.
3. Piquete Marandu medido a 25 cm dois dias antes de `data_base`, sem lote, com uma leitura e `ClimaDia` fixos → `massa_hoje = 2750 + taxa(d1) + taxa(d2)` (taxas calculadas pela própria `taxa_acumulo_safer`).
4. Mesmo piquete ocupado por lote de 1000 kg/dia, eficiência 0,72, área 2 ha → cada dia subtrai 694,44.
