# SPEC-009 — Cross-module contracts and their JSON form

## Context
Five people build five modules in parallel: satellite/state estimation, weekly planner, web
registration, weekly job and Telegram bot. They meet only through a handful of immutable data
types. This spec creates the single module that defines those types and converts them to and
from plain JSON-compatible dicts, so that a plan can be stored in the database, sent over HTTP
and loaded back identically. Two example files already exist and must load without error.

## Domain vocabulary
- `piquete` — paddock. `lote` — cattle group. `plano` — the weekly plan.
- `movimentacao` — one recommended move of a lote to another piquete on a given day.
- `alerta` — a warning for the farmer. `pedido_validacao` — a request to measure a paddock's
  grass height with a ruler.
- `confianca` / `motivo_confianca` — reliability tier and the Portuguese sentence naming the
  weakest piece of data behind it.
- `faltantes` — names of the parameters missing for a piquete.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

You may read (not modify) `src/seugado/core/models.py`, `src/seugado/core/projecao.py`, and the
two fixture files `tests/fixtures/estado_projetado_exemplo.json` and
`tests/fixtures/plano_exemplo.json`.

## Files to create or modify
- CREATE `src/seugado/contratos.py`
- CREATE `tests/core/test_contratos.py`

## Requirements

### R1 — Types
All dataclasses are `@dataclass(frozen=True, slots=True)`. Collections are tuples, never lists
or dicts. Import `Confianca`, `MetodoPastejo`, `CategoriaAnimal`, `OrigemPeso`,
`ComposicaoLote`, `ParametrosRegime` from `seugado.core.models` and `SituacaoPiquete` from
`seugado.core.projecao`. Field order is exactly as written.

```python
class TipoAlerta(StrEnum):
    SEM_PIQUETE_APTO = "sem_piquete_apto"
    CAPACIDADE_EXCEDIDA = "capacidade_excedida"
    AGUARDANDO_PARAMETRO = "aguardando_parametro"
    ESTIMATIVA_INDISPONIVEL = "estimativa_indisponivel"
    CONTINUO_ACIMA_MAXIMA = "continuo_acima_maxima"
    CONTINUO_ABAIXO_MINIMA = "continuo_abaixo_minima"
    LOTE_SEM_PIQUETE = "lote_sem_piquete"
    SEM_DIA_DE_MANEJO = "sem_dia_de_manejo"

@dataclass(frozen=True, slots=True)
class PiqueteProjetado:
    piquete_id: UUID
    nome: str
    area_ha: float
    metodo_pastejo: MetodoPastejo
    cultivar_slug: str
    cultivar_nome: str
    centroide_lat: float
    centroide_lon: float
    situacao: SituacaoPiquete
    lote_atual_id: UUID | None
    dias_descanso: int
    parametros: ParametrosRegime | None
    faltantes: tuple[str, ...]
    descanso_min_dias: float
    densidade_kg_ha_por_cm: float | None
    eficiencia_pastejo: float | None
    massa_hoje_kg_ms_ha: float | None
    altura_hoje_cm: float | None
    taxa_acumulo_prevista_kg_ms_ha_dia: tuple[float, ...]
    confianca: Confianca
    motivo_confianca: str
    dias_desde_imagem_limpa: int | None

@dataclass(frozen=True, slots=True)
class LoteProjetado:
    lote_id: UUID
    nome: str
    composicao: tuple[ComposicaoLote, ...]
    indissoluvel: bool
    piquete_atual_id: UUID | None
    desde: date | None
    peso_vivo_total_kg: float
    consumo_kg_ms_dia: float
    confianca_peso: Confianca
    motivo_confianca_peso: str

@dataclass(frozen=True, slots=True)
class EstadoProjetado:
    fazenda_id: UUID
    data_base: date
    horizonte_previsao_dias: int
    piquetes: tuple[PiqueteProjetado, ...]
    lotes: tuple[LoteProjetado, ...]

@dataclass(frozen=True, slots=True)
class Movimentacao:
    id: UUID
    data: date
    lote_id: UUID
    lote_nome: str
    piquete_origem_id: UUID | None
    piquete_origem_nome: str | None
    piquete_destino_id: UUID
    piquete_destino_nome: str
    altura_destino_cm: float
    altura_entrada_alvo_cm: float
    altura_origem_cm: float | None
    altura_saida_alvo_cm: float | None
    dias_previstos: int
    motivo: str
    confianca: Confianca
    motivo_confianca: str

@dataclass(frozen=True, slots=True)
class Alerta:
    tipo: TipoAlerta
    data: date
    texto: str
    confianca: Confianca
    motivo_confianca: str
    piquete_id: UUID | None
    lote_id: UUID | None

@dataclass(frozen=True, slots=True)
class PedidoValidacao:
    piquete_id: UUID
    piquete_nome: str
    motivo: str

@dataclass(frozen=True, slots=True)
class ResumoPiquete:
    piquete_id: UUID
    nome: str
    situacao: SituacaoPiquete
    lote_atual_nome: str | None
    altura_hoje_cm: float | None
    altura_entrada_alvo_cm: float | None
    altura_saida_alvo_cm: float | None
    confianca: Confianca
    motivo_confianca: str
    faltantes: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class PlanoManejo:
    id: UUID
    fazenda_id: UUID
    data_geracao: datetime          # timezone-aware, UTC
    data_inicio: date
    horizonte_dias: int
    movimentacoes: tuple[Movimentacao, ...]
    alertas: tuple[Alerta, ...]
    pedidos_validacao: tuple[PedidoValidacao, ...]
    piquetes: tuple[ResumoPiquete, ...]
```

### R2 — JSON conversion
```python
def estado_para_dict(estado: EstadoProjetado) -> dict[str, Any]: ...
def estado_de_dict(dados: Mapping[str, Any]) -> EstadoProjetado: ...
def plano_para_dict(plano: PlanoManejo) -> dict[str, Any]: ...
def plano_de_dict(dados: Mapping[str, Any]) -> PlanoManejo: ...
```
Mapping rules (the fixture files follow them exactly):
- Keys are the field names. Every field is always present (`None` → `null`).
- `UUID` → `str(uuid)`; `date` → `date.isoformat()`; `datetime` → `datetime.isoformat()`
  (must be timezone-aware; `plano_de_dict` rejects a naive value with `ValueError`);
  `StrEnum` → `.value`; tuples → lists.
- `ParametrosRegime` → object with keys `metodo`, `altura_entrada_cm`, `altura_saida_cm`,
  `altura_maxima_cm`, `altura_minima_cm`, `confianca`, `fonte`.
- `ComposicaoLote` → object with keys `categoria`, `n_animais`, `peso_medio_kg`, `origem_peso`.
- Round trip: `plano_de_dict(plano_para_dict(p)) == p` and
  `estado_de_dict(estado_para_dict(e)) == e` for every valid value.
- `json.dumps(plano_para_dict(p), ensure_ascii=False)` must succeed (only JSON-native types).

## Constants and parameters
None.

## Validation rules
- `plano_de_dict` / `estado_de_dict` raise `ValueError` on an unknown enum value, a malformed
  UUID or date, a naive `data_geracao`, or a missing key (let the underlying `KeyError` be
  re-raised as `ValueError` with the key name).

## Testing — who does what
Write your own tests in `tests/core/`, as a smoke check that your code runs and behaves as
described. Load both fixture files with `json.load` and check that they convert and round-trip.
Keep the tests short. You will NOT be given a test file to copy, and you must not wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] All 9 dataclasses exist, frozen and slotted, with the exact fields and order above
- [ ] `TipoAlerta` has exactly the 8 members and values above
- [ ] `estado_de_dict(json.load(estado_projetado_exemplo.json))` returns 8 piquetes and 2 lotes
- [ ] `plano_de_dict(json.load(plano_exemplo.json))` returns 3 movimentações, 3 alertas,
      1 pedido and 8 resumos
- [ ] Both fixtures round-trip to a dict equal to the loaded JSON
- [ ] The module imports nothing from `sensing/`, `planner/`, `api/`, `delivery/` or any DB library
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
In `plano_exemplo.json`, the first `movimentacoes` item has `"data": "2026-09-28"`,
`"lote_nome": "Recria"`, `"piquete_destino_nome": "Piquete 1"`, `"dias_previstos": 3` and
`"confianca": "media"`. After `plano_de_dict`, that item is a `Movimentacao` whose `data` is
`date(2026, 9, 28)` and whose `confianca` is `Confianca.MEDIA`; converting back gives the same
dict.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-009.md`.

## Out of scope
- Do NOT compute anything (no forage, no planning, no text generation)
- Do NOT add database, HTTP or file I/O (tests may read the fixtures)
- Do NOT modify the fixture files
- Do NOT use Pydantic, dataclasses-json or any serialization library
- Do NOT add methods to the dataclasses
- Do NOT add new dependencies

## Style constraints
- Python 3.12, type hints on every public function
- Pure functions only: no I/O, no global state, no side effects
- Domain nouns stay in Portuguese; docstrings and comments in English
- `__init__.py` files stay empty
- Maximum 300 lines per file
