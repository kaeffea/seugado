# KIT-ACEITE-013 — Satélite Sentinel-2 (10 m)

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- Coleções exatas: `COPERNICUS/S2_SR_HARMONIZED` e `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`; nenhuma referência a HLS.
- `buffer(-5)`, `scale=10`, `cs_cdf >= 0.60`.
- `extrair_observacoes` puro; `ingerir_leituras` não faz commit nem reconstrói projeção.
- Chave `leitura:<piquete_id>:<YYYY-MM-DD>`; `entidade_id = uuid5(NAMESPACE_URL, chave)`.

## Caso canônico
Exemplo resolvido da spec (P1, NDVI 0,75, 20 % de nuvem, refletâncias escaladas).

## Casos que a spec não mostra
1. Linha já em reflectância (`red=0.05, nir=0.30`) → sem escala → NDVI 0,7143.
2. Duas linhas do mesmo piquete/data com 20 pixels cada → fica a primeira.
3. Real (Supabase + GEE): fazenda de teste com um piquete de ~0,1 ha e um de ~0,4 ha em pasto real → cada um tem ≥ 1 leitura nos últimos 30 dias; segunda execução devolve 0.
