# SPEC-006 — Pure fold from event log to current farm state

## Context
This system is event-sourced: everything that happens is an immutable event, and the current
state is always derived, never edited in place. This spec implements that derivation — a pure
function that takes the full list of events for one farm and returns the state they add up to
today. Nothing here touches a database; the caller is responsible for fetching the events and
storing the result.

## Domain vocabulary
- `piquete` — a fenced paddock subdivision; the spatial unit cattle graze.
- `lote` — a group of cattle managed as one unit.
- `evento` — an immutable fact: something that happened, stored append-only.
- `dobra` (fold) — replaying the event log to compute current state, the way a bank statement is
  the fold of its transactions.
- `descanso` — the rest period a paddock needs between grazing cycles.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- MODIFY `src/seugado/core/models.py` (only the `Evento` class — see R0)
- CREATE `src/seugado/core/projecao.py`
- CREATE `tests/core/test_projecao.py`

## Requirements

### R0 — Extend `Evento` with the two fields the fold needs
`Evento` currently has no way to express write order or corrections. Add exactly two fields,
after `origem`, both required (no default) except `corrige_evento_id`:

```python
@dataclass(frozen=True, slots=True)
class Evento:
    id: UUID
    fazenda_id: UUID
    tipo: TipoEvento
    ocorrido_em: datetime
    registrado_em: datetime
    payload: dict[str, Any]
    origem: OrigemEvento
    sequencia: int                              # NEW — write order, assigned by the database
    corrige_evento_id: UUID | None = None        # NEW — set when this event corrects another
```
Do not add, rename or remove any other field. Do not add `ator`, `chave_idempotencia`,
`versao_payload` or `entidade_id` — those are persistence-layer concerns handled by a different
spec, not needed by this fold.

### R1 — State containers
Create these frozen, slotted dataclasses in `core/projecao.py`:

```python
class SituacaoPiquete(StrEnum):
    OCUPADO = "ocupado"
    DESCANSANDO = "descansando"

@dataclass(frozen=True, slots=True)
class EstadoPiquete:
    piquete_id: UUID
    fazenda_id: UUID
    nome: str
    area_ha: float
    cultivar_id: UUID
    metodo_pastejo: MetodoPastejo
    ativo: bool
    situacao: SituacaoPiquete
    lote_atual_id: UUID | None      # None when situacao is DESCANSANDO
    desde: date                     # date the current situacao began
    dias_descanso: int              # 0 when OCUPADO

@dataclass(frozen=True, slots=True)
class EstadoLote:
    lote_id: UUID
    fazenda_id: UUID
    nome: str
    composicao: tuple[ComposicaoLote, ...]
    indissoluvel: bool
    piquete_atual_id: UUID | None
    desde: date | None               # None when never assigned to a piquete
    peso_vivo_total_kg: float        # sum(n_animais * peso_medio_kg) over composicao

@dataclass(frozen=True, slots=True)
class Leitura:
    id: UUID
    piquete_id: UUID
    data: date
    ndvi: float
    origem_ndvi: str
    pct_nuvem: float
    pixels_validos: int
    massa_kg_ms_ha: float
    taxa_acumulo_kg_ms_ha_dia: float
    confianca: Confianca

@dataclass(frozen=True, slots=True)
class EstadoFazenda:
    fazenda_id: UUID
    piquetes: dict[UUID, EstadoPiquete]   # key: piquete_id
    lotes: dict[UUID, EstadoLote]         # key: lote_id
    leituras: dict[UUID, Leitura]         # key: piquete_id — only the MOST RECENT reading
```
Import `ComposicaoLote`, `MetodoPastejo`, `Confianca` from `seugado.core.models`. `dict` values
here are the projection's own containers, never used as dict *keys* by entity (rule `06` §7.12
is about entity objects as keys, not this).

### R2 — Ordering and corrections

```python
def projetar(eventos: Sequence[Evento]) -> EstadoFazenda:
    """Fold a farm's full event history into its current state."""
```

1. If `eventos` is empty, raise `ValueError`.
2. All events must share one `fazenda_id`; raise `ValueError` if they don't — this function
   projects one farm at a time, never several.
3. Build `corrigidos: dict[UUID, Evento]` mapping `corrige_evento_id -> corrective event`, for
   every event where `corrige_evento_id is not None`. If two events correct the same id, raise
   `ValueError` — one correction per event is all this fold supports.
4. For every `corrige_evento_id` found, its target id must exist among `eventos`; raise
   `ValueError` if not (a dangling correction).
5. Compute each event's **effective position**: for an event that is itself a target of a
   correction (its id is a key in `corrigidos`), the effective position is still its own
   `(ocorrido_em, sequencia)`, but its **effective content is the corrective event's**, not its
   own. A corrective event is itself skipped from direct iteration (it never appears at its own
   position — only at the position of what it corrects).
6. Sort by effective `(ocorrido_em, sequencia)` ascending and apply each event's effective
   content in that order (R3–R6). An event that neither corrects anything nor is corrected
   applies its own content at its own position, unchanged.
7. `data_referencia` (used for R3's `dias_descanso`) is `max(e.ocorrido_em for e in eventos).date()`
   — the fold has no notion of "today" other than the latest fact it was given.

### R3 — `piquete_criado` / `piquete_alterado`
Payload keys (both types): `entidade_id` (UUID, the piquete), `nome` (str), `area_ha` (float),
`cultivar_id` (UUID), `metodo_pastejo` (str, one of `MetodoPastejo` values), `ativo` (bool).

- `piquete_criado`: insert a new `EstadoPiquete` — `situacao=DESCANSANDO`, `lote_atual_id=None`,
  `desde=evento.ocorrido_em.date()`, `dias_descanso = (data_referencia - desde).days`.
- `piquete_alterado`: update `nome`, `area_ha`, `cultivar_id`, `metodo_pastejo`, `ativo` on the
  existing entry with the same `entidade_id`. Raise `ValueError` if no such piquete exists yet
  (an alteration before a creation is a data-integrity bug, not a state to represent).
  `situacao`, `lote_atual_id`, `desde` are untouched by this event.

### R4 — `lote_criado` / `lote_alterado` / `lote_dissolvido`
Payload keys, `lote_criado`/`lote_alterado`: `entidade_id` (UUID, the lote), `nome` (str),
`composicao` (list of `{categoria, n_animais, peso_medio_kg}`), `indissoluvel` (bool).
Payload keys, `lote_dissolvido`: `entidade_id` only.

- `lote_criado`: insert `EstadoLote` — `piquete_atual_id=None`, `desde=None`,
  `peso_vivo_total_kg` computed from `composicao`.
- `lote_alterado`: update `nome`, `composicao`, `indissoluvel`, recompute `peso_vivo_total_kg`, on
  the existing entry. `piquete_atual_id`/`desde` untouched. Raise `ValueError` if the lote doesn't
  exist yet.
- `lote_dissolvido`: remove the lote from `lotes`. If it currently occupies a piquete
  (`piquete_atual_id is not None`), that piquete transitions to `DESCANSANDO`,
  `lote_atual_id=None`, `desde=evento.ocorrido_em.date()`, `dias_descanso` recomputed against
  `data_referencia`.

### R5 — `manejo_confirmado`
Payload keys: `entidade_id` (UUID, the manejo — not used by the fold), `lote_id` (UUID),
`piquete_destino_id` (UUID), `data_execucao` (date, ISO string in payload).

This is the one event that moves a lote. On `manejo_confirmado`:
1. If the lote currently occupies a piquete, that piquete transitions to `DESCANSANDO` per R4's
   dissolution logic (same `desde`/`dias_descanso` update, using `data_execucao` instead of
   `ocorrido_em`).
2. The destination piquete transitions to `OCUPADO`, `lote_atual_id = lote_id`,
   `desde = data_execucao`, `dias_descanso = 0`.
3. The lote's `EstadoLote.piquete_atual_id` and `desde` update to match.
4. Raise `ValueError` if `lote_id` or `piquete_destino_id` isn't a known entity at this point in
   the fold.

### R6 — `leitura_satelite`
Payload keys: `entidade_id` (UUID, the reading itself), `piquete_id` (UUID), `data` (date, ISO
string), `ndvi` (float), `origem_ndvi` (str), `pct_nuvem` (float), `pixels_validos` (int),
`massa_kg_ms_ha` (float), `taxa_acumulo_kg_ms_ha_dia` (float), `confianca` (str, one of
`Confianca` values).

Build a `Leitura` from the payload and store it in `leituras[piquete_id]` **only if** no reading
is stored yet for that piquete, or the new one's `data` is later (ties broken by the event's own
effective position, which is already chronological per R2 — so in practice, always overwrite,
since events are applied in order). Also set `EstadoPiquete.massa_kg_ms_ha`... — **do not** add
this field to `EstadoPiquete` (R1 already defines its exact fields); mass currently lives only on
`Leitura`. Any function needing "the piquete's current mass" reads
`estado.leituras[piquete_id].massa_kg_ms_ha`.

### R7 — Events with no projection effect in this fatia
`manejo_recomendado`, `manejo_recusado`, `manejo_divergente`, `foto_validacao`,
`parametro_alterado` are valid `TipoEvento` values that this function must accept without
raising — but they change nothing in the returned `EstadoFazenda`. Simply skip them in the fold.

## Constants and parameters
None. This module performs no agronomic calculation and introduces no numeric constant.

## Validation rules
- Raise `ValueError` if `eventos` is empty.
- Raise `ValueError` if events span more than one `fazenda_id`.
- Raise `ValueError` on a correction chain (two events correcting the same id) or a dangling
  `corrige_evento_id`.
- Raise `ValueError` when an alteration, dissolution or confirmation event references an entity
  id that no prior event created.

## Testing — who does what
Write your own tests in `tests/core/`, as a smoke check that your code runs and behaves as
described. Keep them short. You will NOT be given a test file to copy, and you must not
wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `Evento` has exactly the two new fields, in the position and with the defaults specified
- [ ] `projetar` exists with the exact signature `projetar(eventos: Sequence[Evento]) -> EstadoFazenda`
- [ ] `EstadoPiquete`, `EstadoLote`, `Leitura`, `EstadoFazenda`, `SituacaoPiquete` exist with
      exactly the fields specified, `frozen=True, slots=True` on the dataclasses
- [ ] Canonical worked example (below) passes
- [ ] Correction example (below) passes
- [ ] All public functions have type hints
- [ ] Module imports nothing from `sensing/`, `planner/`, `api/`, `persistencia/` or any DB library
- [ ] `pytest tests/core/test_projecao.py` passes with zero failures
- [ ] Only `psycopg`, `pydantic` are absent from this module's imports — it adds no new dependency

## Worked example
Farm with one piquete and one lote, three events, `ocorrido_em` on 2026-09-01, 09-05 and 09-10,
`sequencia` 1, 2, 3:

1. `piquete_criado` — `entidade_id=P1`, `nome="Piquete 7"`, `area_ha=5.81`, `cultivar_id=C1`,
   `metodo_pastejo="rotacionado"`, `ativo=True`.
2. `lote_criado` — `entidade_id=L1`, `nome="Lote A"`, `composicao=[{categoria: "adulto",
   n_animais: 20, peso_medio_kg: 450}]`, `indissoluvel=False`.
3. `manejo_confirmado` — `entidade_id=M1`, `lote_id=L1`, `piquete_destino_id=P1`,
   `data_execucao="2026-09-10"`.

Result: `piquetes[P1].situacao == OCUPADO`, `lote_atual_id == L1`, `desde == date(2026,9,10)`,
`dias_descanso == 0`. `lotes[L1].piquete_atual_id == P1`, `peso_vivo_total_kg == 9000.0`.

**Correction example.** Same three events, plus a fourth: `piquete_alterado` correcting event 1
(`corrige_evento_id = <id of event 1>`), `ocorrido_em` 2026-09-15 (when the mistake was noticed),
payload identical except `area_ha=6.02`. Expected: `piquetes[P1].area_ha == 6.02` — the correction
applies at event 1's position (before the `lote_criado` and `manejo_confirmado` that follow it),
not at its own late `ocorrido_em`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-006.md`. Must contain:
- Structural checks: forbidden imports (`sensing`, `planner`, `api`, `persistencia`, `psycopg`,
  `pydantic`), `frozen=True, slots=True` on every new dataclass, exact field sets, no extra
  public functions, file length limit (300 lines).
- Both worked examples above, with their exact expected values.
- At least one hidden numeric case not shown in this spec (e.g., a `lote_dissolvido` while
  occupying a piquete, checking the piquete returns to `DESCANSANDO` with the right `dias_descanso`).
- A case with two independent corrections on two different original events, verifying both apply
  correctly.
- A case where an event referencing an unknown id raises `ValueError`.

## Out of scope
- Do NOT implement `combinar_confianca` — that belongs to F-010 (ADR-019), a different module.
- Do NOT compute `aguardando_parametro` on `EstadoPiquete` — it depends on the `Cultivar` catalog,
  which is reference data, not an event; that join happens in `planner/estado.py` (F-008).
- Do NOT compute or store `piquete_distancia` — deferred to a dedicated spec before F-009 (needs
  geometry math not yet decided).
- Do NOT give `manejo_recomendado`, `manejo_recusado`, `manejo_divergente`, `foto_validacao` or
  `parametro_alterado` any projection effect — R7 covers them.
- Do NOT add database access, an ORM, or any I/O of any kind.
- Do NOT implement `registrar_evento` or any Pydantic model — that is `SPEC-005`.
- Do NOT add HTTP endpoints, logging, caching, or dependency injection.
- Do NOT refactor `core/forragem.py` or `core/regras.py`.
- Do NOT create abstract base classes or interfaces.

## Style constraints
- Python 3.12, type hints on every public function
- Pure functions and frozen/slots dataclasses only: no I/O, no global state, no side effects
- Variable and field names carry their unit: `massa_kg_ms_ha`, not `massa`
- Domain nouns stay in Portuguese: `piquete`, `lote`, `evento`, `descanso`
- Docstrings and comments in English
- Prefer functions over classes; dataclasses here are data, not behavior
- Maximum 300 lines per file — split into a private helper module if it doesn't fit
