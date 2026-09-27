# KIT-ACEITE-014A — Auxiliares do estado

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `planner/estado.py` não importa `psycopg`, `httpx`, `ee`, `sensing`, `persistencia`, `api`.
- Existem `CONSUMO_FRACAO_PV`, `UA_POR_CATEGORIA`, `UNIDADE_ANIMAL_KG`, `peso_por_ua_kg`,
  `consumo_lote`, `confianca_peso`, `avancar_massa_um_dia`, `confianca_estimativa`.
- `planner/carga.py` **não** existe ainda.

## Caso canônico
Exemplos resolvidos da spec (2038,04; 1113,75; 337,5; média por altura de 20 dias).

## Casos que a spec não mostra
1. `avancar_massa_um_dia(2000, 50, 0, 4, None)` → 2050.
2. `avancar_massa_um_dia(100, 0, 1000, 1, 0.5)` → 0,0 (não fica negativo).
3. `confianca_estimativa(None, None, 50, True)` → `(BAIXA, "nenhuma imagem de satélite sem nuvem nos últimos 30 dias")`.
4. `confianca_estimativa(0, 12, 1, False)` → `(ALTA, "última imagem de satélite sem nuvem de hoje")`.
5. `confianca_peso` com um item `PRODUTOR` e um `UA_TABELA` → `(MEDIA, "peso médio estimado pela tabela de Unidade Animal")`.
