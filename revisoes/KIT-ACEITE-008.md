# KIT-ACEITE-008 — Banco MVP

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `0002_mvp.sql` envolto em `BEGIN; … COMMIT;`; não altera `0001`.
- RLS habilitado nas 12 tabelas; `SELECT count(*) FROM pg_policies WHERE schemaname='public'` = 0.
- `SELECT count(*) FROM cultivar` = 9; slugs: marandu, mombaca, tanzania, zuri, massai, tamani, xaraes, piata, decumbens.
- `reconstruir_projecao` e `carregar_catalogo` não chamam `commit`/`rollback` (grep).
- Nenhuma f-string montando SQL com dado.

## Caso canônico
O exemplo resolvido da spec (Xaraés + dois overrides).

## Casos que a spec não mostra
1. `aplicar_overrides(marandu, [(ROTACIONADO, "altura_entrada_cm", 28.0)], faz)` → bloco rotacionado com entrada 28, saída 15 preservada, `confianca=BAIXA`, `fonte="produtor:<faz>"`; bloco contínuo intacto.
2. `faltantes_calibracao(marandu, CONTINUO) == ()` e `faltantes_calibracao(marandu, ROTACIONADO) == ()`.
3. `faltantes_calibracao(piata, CONTINUO) == ("densidade_kg_ha_por_cm",)`.
4. Com banco: criar fazenda + 1 piquete por `registrar_evento`, chamar `reconstruir_projecao` duas vezes → 1 linha em `estado_piquete`, `ST_IsValid(geometria)` verdadeiro.
