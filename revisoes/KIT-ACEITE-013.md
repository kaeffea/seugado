# KIT-ACEITE-013 — Satélite HLS

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `extrair_observacoes` puro; `ingerir_leituras` não faz commit nem reconstrói projeção.
- Chave de idempotência `leitura:<piquete_id>:<YYYY-MM-DD>`; `entidade_id = uuid5(NAMESPACE_URL, chave)`.

## Caso canônico
Exemplo resolvido da spec (P1, NDVI 0,75, 20 % de nuvem).

## Casos que a spec não mostra
1. Linha com `red=500, nir=3000` (int16) → escala 0,0001 → NDVI 0,7143 ± 0,0001.
2. Duas linhas do mesmo piquete/data com 20 pixels cada → fica a primeira.
3. Com banco e GEE reais (fazenda de teste): rodar duas vezes o mesmo período → número de eventos `leitura_satelite` não muda na segunda.
