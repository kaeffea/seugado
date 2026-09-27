# SPEC-014A — Forage-state helpers used by the planner and by lot registration

## Context
Two teammates start coding before the full projected-state module exists. The weekly planner
needs the one-day forage-stock step, and the herd-group registration needs the fallback live
weight per animal category. This spec creates `planner/estado.py` with only those small pure
helpers and the estimate-confidence function. A later spec adds the main projection function
to the same file without changing anything written here.

## Domain vocabulary
- `lote` — cattle group. `piquete` — paddock. `categoria` — `bezerro` (calf), `novilho`
  (young steer/heifer), `adulto` (adult).
- `massa` — forage dry-matter stock, kg per ha. `taxa_acumulo` — growth, kg DM/ha/day.
- `eficiencia_pastejo` — fraction of the forage removed from the paddock that the animals eat.
  Removal per day = intake ÷ efficiency ÷ area.
- `UA` (Unidade Animal) — 450 kg of live weight.
- `confianca` — `alta` / `media` / `baixa`.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

You may read (not modify), to import from them: `src/seugado/core/models.py`,
`src/seugado/core/forragem.py`, `src/seugado/core/regras.py`.

## Files to create or modify
- CREATE `src/seugado/planner/estado.py`
- CREATE `tests/planner/test_estado.py`

## Requirements

### R1 — Constants and helpers
```python
CONSUMO_FRACAO_PV: dict[CategoriaAnimal, float] = {
    CategoriaAnimal.BEZERRO: 0.024, CategoriaAnimal.NOVILHO: 0.022, CategoriaAnimal.ADULTO: 0.024,
}
UA_POR_CATEGORIA: dict[CategoriaAnimal, float] = {
    CategoriaAnimal.BEZERRO: 0.25, CategoriaAnimal.NOVILHO: 0.75, CategoriaAnimal.ADULTO: 1.00,
}
UNIDADE_ANIMAL_KG = 450.0

def peso_por_ua_kg(categoria: CategoriaAnimal) -> float:
    """Fallback mean live weight when the farmer does not know it: UA coefficient × 450 kg."""

def consumo_lote(composicao: Sequence[ComposicaoLote]) -> float:
    """Daily dry-matter intake of a lote, kg/day (uses core.forragem.consumo_lote_kg_ms_dia)."""

def confianca_peso(composicao: Sequence[ComposicaoLote]) -> tuple[Confianca, str]:
    """ALTA 'peso médio informado por você' unless any item came from the UA table:
    then MEDIA 'peso médio estimado pela tabela de Unidade Animal'."""

def avancar_massa_um_dia(
    massa_kg_ms_ha: float,
    taxa_acumulo_kg_ms_ha_dia: float,
    consumo_lote_kg_ms_dia: float,
    area_ha: float,
    eficiencia_pastejo: float | None,
) -> float:
    """Stock at the start of the next day."""
```
`consumo_lote` passes `(n_animais, peso_medio_kg, CONSUMO_FRACAO_PV[categoria])` for each item
to `core.forragem.consumo_lote_kg_ms_dia`.
`avancar_massa_um_dia`: `area_ha <= 0` → `ValueError`. If `consumo_lote_kg_ms_dia == 0` →
return `massa + taxa`. Otherwise `eficiencia_pastejo` must be in `(0, 1]` (else `ValueError`),
and the result is `max(0.0, massa + taxa − consumo / (eficiencia · area_ha))`.

### R2 — Estimate confidence
```python
def confianca_estimativa(
    dias_desde_imagem: int | None,
    pixels_validos: int | None,
    dias_desde_altura: int,
    posicao_por_omissao: bool,
) -> tuple[Confianca, str]:
```
Four factors, each with a level and a Portuguese sentence. The result level is
`core.regras.combinar_confianca` of the four levels. The sentence is the one of the **first**
factor, in the order below, whose level equals the result.

| # | Factor | ALTA | MEDIA | BAIXA | Sentence |
|---|---|---|---|---|---|
| 1 | image age (days) | ≤ 5 | 6–15 | > 15 or `None` | `"última imagem de satélite sem nuvem há {n} dias"`; `None` → `"nenhuma imagem de satélite sem nuvem nos últimos 30 dias"` |
| 2 | ruler age (days) | ≤ 14 | 15–42 | > 42 | `"última medição de altura há {n} dias"` |
| 3 | clear pixels | ≥ 9 | 3–8 | `None` | `"piquete pequeno para a resolução do satélite ({n} pixels úteis)"`; `None` → same as factor 1's `None` sentence |
| 4 | position by omission | `False` | `True` | — | `"a última movimentação foi assumida sem confirmação sua"` |

In the image and ruler sentences use `"há 1 dia"` for n = 1 and `"de hoje"` instead of
`"há 0 dias"`. All thresholds are `HIPOTESE-CALIBRAR` (ADR-023).

## Constants and parameters
| Name | Value | Source |
|---|---|---|
| Intake bezerro / novilho / adulto | 2.4 % / 2.2 % / 2.4 % of live weight | `05`: default 2.4 % (bezerro has no specific value); novilho 2.2 %; adulto 2.4 % |
| UA bezerro / novilho / adulto | 0.25 / 0.75 / 1.00 | `05`, UA table (Embrapa); novilho uses the 2–3-year row (ADR-024) |
| 1 UA | 450 kg | `05` |
| Confidence thresholds | see R2 | `HIPOTESE-CALIBRAR` (ADR-023) |

## Validation rules
- `avancar_massa_um_dia` with consumption > 0 and efficiency `None` or `0` → `ValueError`.
- `avancar_massa_um_dia` with `area_ha <= 0` → `ValueError`.

## Testing — who does what
Write your own tests in `tests/planner/`, as a smoke check. Keep them short. You will NOT be
given a test file to copy.

Your tests are not the verification of record. A separate agent writes an independent
conformance suite in `tests/conformance/` and decides whether the work is accepted. Do not
create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] All functions and constants exist with the exact names and signatures above
- [ ] Worked-example values reproduced
- [ ] Module imports nothing from `sensing/`, `persistencia/`, `api/` or any I/O library
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run --env-file .env pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
- `avancar_massa_um_dia(2420.0, 60.0, 1113.75, 3.5, 0.72)` → `2038.04` (±0.01).
- `consumo_lote((ComposicaoLote(NOVILHO, 150, 337.5, OrigemPeso.UA_TABELA),))` → `1113.75`.
- `peso_por_ua_kg(CategoriaAnimal.NOVILHO)` → `337.5`.
- `confianca_estimativa(3, 40, 20, False)` → `(MEDIA, "última medição de altura há 20 dias")`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-014A.md`.

## Out of scope
- Do NOT implement `projetar_estado` or `montar_estado_projetado` (a later spec adds them)
- Do NOT create `planner/carga.py`
- Do NOT import `sensing/`, weather, satellite or database code
- Do NOT add new dependencies

## Style constraints
- Python 3.12, type hints on every public function; pure functions only
- Variable names carry their unit; domain nouns stay in Portuguese; docstrings in English
- `__init__.py` files stay empty; maximum 300 lines per file
