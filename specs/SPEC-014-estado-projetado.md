# SPEC-014 — Projected farm state: forage mass today and growth for the next 14 days

## Context
The weekly planner needs, for every paddock, how much grass it has today and how fast it will
grow each day of the next two weeks, plus each cattle group's daily intake. The starting point
of a paddock's stock is the last canopy height the farmer measured with a ruler; from that day
on, the stock goes up by the SAFER growth rate (satellite + weather) and down by what the cattle
group occupying it eats. This spec creates the pure computation (`planner/estado.py`) and the
function that loads everything it needs from the database and the weather API
(`planner/carga.py`).

## Domain vocabulary
- `piquete` — paddock. `lote` — cattle group. `cultivar` — grass variety.
- `massa` — forage dry-matter stock, kg per ha. `altura` — canopy height, cm.
- `densidade_kg_ha_por_cm` — kg of dry matter per ha per cm of height (mass = height × density).
- `eficiencia_pastejo` — fraction of the forage removed from the paddock that the animals
  actually eat (the rest is trampled or lost). Removal per day = intake ÷ efficiency ÷ area.
- `taxa_acumulo` — growth rate, kg DM/ha/day.
- `faltantes` — names of what is missing to estimate or to plan a paddock.
- `confianca` / `motivo_confianca` — reliability tier and the Portuguese sentence naming its
  weakest factor.
- `omissao` — a move the system assumed happened because the farmer did not answer.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

You may read (not modify), to import from them: `src/seugado/core/models.py`,
`src/seugado/core/forragem.py`, `src/seugado/core/regras.py`, `src/seugado/core/projecao.py`,
`src/seugado/contratos.py`, `src/seugado/persistencia/catalogo.py`,
`src/seugado/persistencia/projecao_db.py`, `src/seugado/sensing/clima.py`,
`src/seugado/sensing/safer.py`.

## Files to create or modify
- CREATE `src/seugado/planner/estado.py`
- CREATE `src/seugado/planner/carga.py`
- CREATE `tests/planner/test_estado.py`

## Requirements

### R1 — Constants and small pure helpers (`estado.py`)
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
`avancar_massa_um_dia`: if `consumo_lote_kg_ms_dia == 0` → `massa + taxa`; otherwise
`eficiencia_pastejo` must be in `(0, 1]` (else `ValueError`) and the result is
`max(0.0, massa + taxa − consumo / (eficiencia · area_ha))`. `area_ha <= 0` → `ValueError`.

### R2 — Estimate confidence (`estado.py`)
```python
def confianca_estimativa(
    dias_desde_imagem: int | None,
    pixels_validos: int | None,
    dias_desde_altura: int,
    posicao_por_omissao: bool,
) -> tuple[Confianca, str]:
```
Four factors, each with a level and a Portuguese sentence; the result is
`core.regras.combinar_confianca` of the four levels, and the sentence is the one of the
**first** factor, in the order below, whose level equals the result.
| # | Factor | ALTA | MEDIA | BAIXA | Sentence |
|---|---|---|---|---|---|
| 1 | image age (days) | ≤ 5 | 6–15 | > 15 or `None` | `"última imagem de satélite sem nuvem há {n} dias"`; `None` → `"nenhuma imagem de satélite sem nuvem nos últimos 30 dias"` |
| 2 | ruler age (days) | ≤ 14 | 15–42 | > 42 | `"última medição de altura há {n} dias"` |
| 3 | clear pixels | ≥ 9 | 3–8 | `None` | `"piquete pequeno para a resolução do satélite ({n} pixels úteis)"`; `None` → same as factor 1's `None` sentence |
| 4 | position by omission | `False` | `True` | — | `"a última movimentação foi assumida sem confirmação sua"` |
Use `"há 1 dia"` for n = 1 and `"de hoje"` instead of `"há 0 dias"`. All thresholds are
`HIPOTESE-CALIBRAR` (ADR-023).

### R3 — `projetar_estado` (`estado.py`, pure)
```python
def projetar_estado(
    estado: EstadoFazenda,
    eventos: Sequence[Evento],
    catalogo: Mapping[UUID, CultivarCatalogo],
    centroides: Mapping[UUID, tuple[float, float]],     # piquete_id -> (lat, lon)
    clima: Sequence[ClimaDia],
    et0_media_anual_mm_dia: float,
    lat_fazenda: float,
    data_base: date,
    horizonte_previsao_dias: int = 14,
) -> EstadoProjetado:
```
For each **active** piquete of `estado.piquetes`, sorted by `nome`:
1. `c = catalogo[cultivar_id]`. `faltantes` = `resolver_alturas(c, metodo).faltantes` followed
   by `faltantes_calibracao(c, metodo)`.
2. Anchor = the `altura_medida` event of this piquete with the greatest `data <= data_base`.
   None → append `"altura_inicial"`.
3. Readings = `leitura_satelite` events of this piquete with `data <= data_base`. None with
   `data >= data_base − 30 days` → append `"imagem_satelite"`. For a given day `d`, the reading
   used is the latest one with `data <= d`; if none, the earliest reading available.
4. Occupation: from `manejo_confirmado` (`lote_id`, `piquete_destino_id`, `data_execucao`) and
   `manejo_divergente` (`lote_id`, `piquete_real_id`, `data_execucao`) events, in
   `(ocorrido_em, sequencia)` order, a lote occupies a piquete from its `data_execucao`
   (inclusive) until its next move. Only lotes present in `estado.lotes` count, with their
   **current** composition (intake from `consumo_lote`).
5. Can estimate only if none of `"altura_inicial"`, `"imagem_satelite"`,
   `"densidade_kg_ha_por_cm"`, `"rue_max_g_por_mj"` is in `faltantes`. Then:
   - `massa = altura_cm × densidade` of the anchor; for each day `d` from anchor `data` to
     `data_base − 1` (inclusive): `taxa = taxa_acumulo_safer(reading(d), clima(d), Ra(lat_fazenda, d),
     et0_media_anual_mm_dia, rue)`; `massa = avancar_massa_um_dia(massa, taxa, intake of the lote
     occupying the piquete on d (0 if none), area, eficiencia_pastejo(c, metodo))`.
     If a day is occupied and the efficiency is `None` → append `"eficiencia_pastejo"` and stop.
   - `massa_hoje` = the result; `altura_hoje = core.forragem.massa_para_altura(massa, densidade)`.
   - `taxa_acumulo_prevista` = SAFER for days `data_base … data_base + horizonte − 1`, with the
     latest reading `<= data_base` held constant and that day's weather (forecast or observed).
   - A missing `ClimaDia` for any needed day → append `"clima"`; a `SaferForaDaFaixa` →
     append `"estimativa_invalida"`. In both cases the estimate is abandoned (`massa_hoje`,
     `altura_hoje` = `None`, `taxa_acumulo_prevista` = `()`).
6. Confidence: if the estimate exists → `confianca_estimativa(image age, clear pixels of the latest
   reading, days since the anchor, whether the move that put the current lote here has
   `origem == SISTEMA`)`. Otherwise `Confianca.BAIXA` with the sentence of the **first**
   `faltantes` item, from this table:
   | item | sentence |
   |---|---|
   | `altura_entrada_cm` / `altura_saida_cm` / `altura_maxima_cm` / `altura_minima_cm` | `"falta a altura de {entrada|saída|máxima|mínima} do {cultivar} no pastejo {rotacionado|contínuo}"` |
   | `densidade_kg_ha_por_cm`, `rue_max_g_por_mj`, `eficiencia_pastejo` | `"a cultivar {cultivar} ainda não tem calibração no SeuGado"` |
   | `altura_inicial` | `"nenhuma medição de altura com régua registrada para este piquete"` |
   | `imagem_satelite` | `"nenhuma imagem de satélite sem nuvem nos últimos 30 dias"` |
   | `clima` | `"faltam dados de clima para o período"` |
   | `estimativa_invalida` | `"o cálculo por satélite saiu da faixa esperada"` |
7. `dias_descanso` = `(data_base − desde).days` when resting, else `0`.
   `dias_desde_imagem_limpa` = days since the latest reading `<= data_base`, or `None`.
8. Build `PiqueteProjetado` with `parametros = resolver_alturas(c, metodo).parametros`,
   `densidade`, `eficiencia_pastejo(c, metodo)`, `descanso_min_dias`, the centroid, and the
   fields above. `faltantes` keeps insertion order without duplicates.

Lotes: every lote of `estado.lotes`, sorted by `nome` → `LoteProjetado` with
`consumo_kg_ms_dia = consumo_lote(...)` and `confianca_peso(...)`.

### R4 — `montar_estado_projetado` (`carga.py`, I/O)
```python
def montar_estado_projetado(
    conn: psycopg.Connection[Any], fazenda_id: UUID, data_base: date,
) -> EstadoProjetado:
```
1. `eventos = carregar_eventos(conn, fazenda_id)`; none → empty `EstadoProjetado`.
2. `estado = projetar(eventos)`; `catalogo = carregar_catalogo(conn, fazenda_id)`.
3. Centroids: `SELECT piquete_id, ST_Y(ST_Centroid(geometria)), ST_X(ST_Centroid(geometria))
   FROM estado_piquete WHERE fazenda_id = %s AND ativo`. None → empty `EstadoProjetado`.
   `lat_fazenda`, `lon_fazenda` = means of the centroids. `timezone` from `fazenda`.
4. `inicio` = earliest anchor date among active piquetes (default `data_base`);
   `clima = buscar_clima(lat, lon, inicio, data_base + 13 days, hoje=data_base, timezone)`;
   `et0 = et0_media_anual_mm_dia(lat, lon, data_base, timezone)`.
5. Return `projetar_estado(...)`. Never commit.

## Constants and parameters
| Name | Value | Source |
|---|---|---|
| Intake bezerro / novilho / adulto | 2.4 % / 2.2 % / 2.4 % of live weight | `05`: `consumo_pct_pv_default` 2.4 % (bezerro has no specific value); novilho 2.2 %; adulto 2.4 % |
| UA bezerro / novilho / adulto | 0.25 / 0.75 / 1.00 | `05`, UA table (Embrapa); novilho uses the 2–3-year row, ADR-024 |
| 1 UA | 450 kg | `05` |
| Satellite lookback | 30 days | `HIPOTESE-CALIBRAR` — ADR-023 |
| Confidence thresholds (R2) | see table | `HIPOTESE-CALIBRAR` — ADR-023 |
| Forecast horizon | 14 days | Open-Meteo forecast covers 16 days |

## Validation rules
- `avancar_massa_um_dia` with consumption and efficiency `None`/`0` → `ValueError`.
- `projetar_estado` never raises for a single paddock's data problem: it records it in
  `faltantes` and continues with the next paddock.

## Testing — who does what
Write your own tests in `tests/planner/`. Test `projetar_estado` with literal events, a literal
catalog entry, literal `ClimaDia` values and no network or database. Keep them short. You will
NOT be given a test file to copy, and you must not wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] All functions exist with the exact signatures above
- [ ] Worked-example values reproduced
- [ ] A piquete without ruler measurement gets `faltantes` containing `"altura_inicial"`,
      `massa_hoje_kg_ms_ha is None` and `confianca == BAIXA`
- [ ] A Mombaça piquete (no density) is present in the result with `massa_hoje_kg_ms_ha is None`
- [ ] `projetar_estado` is pure (no I/O imports in `estado.py`)
- [ ] `estado_para_dict(montar_estado_projetado(...))` works on a real Supabase farm (tester)
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
- `avancar_massa_um_dia(2420.0, 60.0, 1113.75, 3.5, 0.72)` → `2420 + 60 − 1113.75/(0.72·3.5)`
  = `2038.04` (±0.01).
- `consumo_lote((ComposicaoLote(NOVILHO, 150, 337.5, UA_TABELA),))` → `1113.75`.
- `confianca_estimativa(3, 40, 20, False)` → `(MEDIA, "última medição de altura há 20 dias")`.
- A Marandu rotational piquete measured at 30.0 cm on `data_base` itself (no simulated days):
  `massa_hoje = 3300.0`, `altura_hoje = 30.0`, and 14 forecast rates, each equal to
  `taxa_acumulo_safer(...)` for that day's weather.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-014.md`.

## Out of scope
- Do NOT decide movements, alerts or plans (that is the planner's job)
- Do NOT model senescence, water balance, NDVI change during grazing, or composition history
- Do NOT handle `corrige_evento_id` for movement events (the MVP produces no such corrections)
- Do NOT write to the database, commit, or rebuild projections
- Do NOT cache weather or satellite data
- Do NOT add new dependencies

## Style constraints
- Python 3.12, type hints on every public function
- `estado.py` pure; I/O only in `carga.py`
- Variable names carry their unit; domain nouns stay in Portuguese; docstrings in English
- `__init__.py` files stay empty; maximum 300 lines per file (split helpers into
  `planner/estado_util.py` only if `estado.py` would exceed it)
