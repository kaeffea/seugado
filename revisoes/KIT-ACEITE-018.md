# KIT-ACEITE-018 — Módulo e praça no planner

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `PiqueteProjetado` termina em `modulo_id, praca_id, praca_lat, praca_lon`; `LoteProjetado`
  termina em `modulo_id`; todos com default `None`; ordem dos campos antigos intacta.
- `planner/estrutura.py`: só `RAIO_TERRA_M`, `haversine_m`, `ponto_acesso`, `distancia_manejo_m`,
  `piquetes_candidatos` públicos; imports só `math`, `uuid`, `seugado.contratos`.
- `planner/estado.py`, `estado_util.py`, `otimizador.py` sem diff.
- Fixtures antigas de `tests/fixtures/` carregam sem regeneração.

## Caso canônico
Praça (−9,6000, −36,0000); A (−9,6010, −36,0000) e B (−9,6000, −36,0010) na mesma praça
→ 220,83 m; sem praça → 156,16 m (tolerância 0,5 m).

## Casos que a spec não mostra
1. Duas praças: A na praça P (−9,6000, −36,0000); C com centroide (−9,6060, −36,0040) na praça
   P2 (−9,6050, −36,0040) → `distancia_manejo_m(A, C) ≈ 930,51 m`.
2. Origem A sem praça, destino B na praça P → ≈ 220,83 m (acesso de A é o próprio centroide).
3. `distancia_manejo_m(A, A)` → `0.0`, mesmo com praça.
4. Simetria: `dist(A, C) == dist(C, A)` (tolerância 1e-6).
5. `PiqueteProjetado` com `praca_lat` preenchido e `praca_lon = None` → `ponto_acesso` levanta `ValueError`.
6. `_deserialize` com chave ausente de campo **sem** default (ex.: `nome`) → `ValueError("missing key: 'nome'")`.
7. Lote com módulo M1 numa fazenda com piquetes em M1, M2 e sem módulo → só os de M1, na ordem original.
