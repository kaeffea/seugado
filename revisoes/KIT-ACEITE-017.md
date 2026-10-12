# KIT-ACEITE-017 — Módulo e praça: banco, cadastro e API

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `0004` aplicado depois do `0003`: `modulo`, `praca`, `piquete_estrutura`, `lote_modulo` com RLS;
  `praca.ponto` é `geometry(Point,4326)`; `UNIQUE (fazenda_id, nome)` em `modulo` e `praca`;
  `CHECK` de `piquete_estrutura` recusa linha com `modulo_id` e `praca_id` nulos.
- `cadastro/estrutura.py` importa `UNIDADE_ANIMAL_KG` de `seugado.planner.estado` (sem cópia de 450).
- Nenhuma função escreve em `evento`; `persistencia/eventos.py`, `core/`, `cadastro/piquetes.py`,
  `cadastro/lotes.py` e `contratos.py` sem diff.
- 11 rotas no `openapi.json`, com 201 nos POST e 204 nos DELETE.
- Arquivo ≤ 300 linhas; `__init__.py` vazios.

## Caso canônico
P1 10 ha + P2 5 ha, lote de 30 bois de 540 kg → `area_ha 15.0`, `ua_total 36.0`, `lotacao_ua_ha 2.4`.

## Casos que a spec não mostra
1. Caso do mentor num módulo só: lotes 100 × 210 kg, 60 × 360 kg, 40 × 540 kg, piquetes somando
   152 ha → `ua_total ≈ 142.67`, `lotacao_ua_ha ≈ 0.939` (tolerância 0,001).
2. Módulo sem piquetes ativos → `area_ha 0.0`, `lotacao_ua_ha None`.
3. Piquete desativado no módulo não entra em `piquete_ids` nem em `area_ha`.
4. `definir_estrutura_piquete` com módulo da fazenda B numa chamada da fazenda A → 400.
5. PUT estrutura com `{modulo_id: null, praca_id: null}` apaga a linha; GET `/estrutura` devolve
   o piquete com `None, None`.
6. `DELETE` de praça usada por um piquete → 409; depois de desvincular → 204.
7. Praça com `lat = 91` → 422.
