# KIT-ACEITE-009 — Contratos

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- 9 dataclasses `frozen=True, slots=True`, ordem de campos exata; nenhuma coleção `list`/`dict` nos campos.
- `TipoAlerta` com 8 membros e valores exatos.
- Módulo não importa `sensing`, `planner`, `api`, `delivery`, `psycopg`, `pydantic`.

## Caso canônico
As duas fixtures carregam e fazem ida e volta idênticas.

## Casos que a spec não mostra
1. `plano_de_dict` com `data_geracao="2026-09-28T08:00:00"` (sem fuso) → `ValueError`.
2. `plano_de_dict` com `"tipo": "inexistente"` num alerta → `ValueError`.
3. `estado_de_dict` sem a chave `lotes` → `ValueError` mencionando `lotes`.
