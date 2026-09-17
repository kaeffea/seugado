# Template de Spec para o Muse Code

O Claude (planejador) usa este template para toda spec. **Escrito em inglês** — o agente
programador tende a performar melhor e gastar menos tokens em inglês, e nomes de domínio
em português são preservados explicitamente na seção de vocabulário.

## Regras da spec

1. **Autocontida.** Nunca referencia o chat, outra spec ou "como discutido". Quem lê não viu nada.
2. **Um arquivo, ou poucos arquivos próximos.** Se toca 5+ arquivos, quebre em duas specs.
3. **Critérios verificáveis**, nunca intenções. "Should be robust" ❌ · "Raises ValueError when ndvi < -1" ✅
4. **`Out of scope` é obrigatória.** É a seção que mais economiza retrabalho.
5. **Todo número vem de `05-PARAMETROS-CULTIVARES.md`.** Se falta, marcar `TODO-PARAM` e
   **não emitir a spec** — resolver em `[PESQUISA]` primeiro.
6. **Nunca alterar contratos** de `06-ARQUITETURA-E-STACK.md` §3.

---

## TEMPLATE

````markdown
# SPEC-<NNN> — <short imperative title>

## Context
<2-4 sentences. What this code is for, in plain terms. No project history.
Enough for someone who has never seen this project to understand the purpose.>

## Domain vocabulary
<ONLY the Portuguese domain terms used in this spec. Omit the section if none.>
- `piquete` — a fenced paddock subdivision; the spatial unit. Keep this name in code.
- `lote` — a group of cattle managed as one unit. Keep this name in code.
- `massa_forragem` — available forage dry matter, in kg DM per hectare.

## Files to create or modify
<Explicit list. The agent must not touch anything else.>
- CREATE `seugado/core/forragem.py`
- CREATE `tests/core/test_forragem.py`
- (never list `__init__.py`: packages stay empty — see `06` §7 rule 10)

## Requirements

### R1 — <requirement name>
<Precise description. Include the exact signature when it is a function.>

```python
def dias_ocupacao(
    massa_atual_kg_ms_ha: float,
    massa_residuo_kg_ms_ha: float,
    taxa_acumulo_kg_ms_ha_dia: float,
    area_ha: float,
    eficiencia_pastejo: float,
    consumo_lote_kg_ms_dia: float,
) -> float:
    """Return the number of days a lote can graze a piquete."""
```

Formula:
```
available_kg = (massa_atual - massa_residuo) * area_ha * eficiencia_pastejo
days = available_kg / consumo_lote_dia
```
Growth during occupation must be accounted for: total available forage is the initial
mass plus accumulation over the occupation period. Solve iteratively (max 5 iterations,
convergence tolerance 0.01 days) or analytically.
`eficiencia_pastejo` is the ingested fraction of the mass ABOVE the residue height. It is
NOT the observed utilization rate (removed mass over pre-grazing mass). See ADR-010.

### R2 — <next requirement>
...

## Constants and parameters
<Every number used, with its source. Copied from 05-PARAMETROS-CULTIVARES.md.>

| Name | Value | Unit | Source |
|---|---|---|---|
| `UTILIZACAO_CASO_CANONICO` | 0.44 | — | Validated farm case; descriptive output only |
| `UNIDADE_ANIMAL_KG` | 450 | kg | Industry standard |

## Validation rules
<What must raise, and which exception.>
- Raise `ValueError` if `eficiencia_pastejo` is outside `[0.0, 1.0]`
- Raise `ValueError` if `area_ha <= 0`
- Return `0.0` (not negative) if `massa_atual <= massa_residuo`

## Testing — who does what
<Copy this section verbatim into every spec. It removes the ambiguity about test ownership.>

Write your own tests in `tests/core/`, as a smoke check that your code runs and behaves as
described. Keep them short. You will NOT be given a test file to copy, and you must not
wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
<Binary and verifiable. The tester checks exactly these.>
- [ ] `dias_ocupacao` exists with the exact signature above
- [ ] Canonical regression case passes (see Test data)
- [ ] All public functions have type hints
- [ ] Module imports nothing from `sensing/`, `planner/`, `api/` or any DB library
- [ ] `pytest tests/core/test_forragem.py` passes with zero failures
- [ ] No new dependency added to `pyproject.toml`

## Worked example
<One illustrative case with concrete numbers, in prose or as a docstring example.
NOT a test file: the agent writes its own tests. The tester's numbers live in the
acceptance kit, which the coding agent never sees.>

Canonical commercial-farm case: initial mass 4000 kg DM/ha, residue 2240 kg DM/ha,
area 5.81 ha, accumulation rate 0.0 kg DM/ha/day, grazing efficiency 1.0 (this source case
reports disappearance as intake), herd intake 11.62 * 220 kg DM/day → about 4.0 days.

## Acceptance kit (tester only — NEVER paste into the coding agent)
<Lives in `revisoes/KIT-ACEITE-<NNN>.md`, not in this spec. Must contain:>
- All structural checks: forbidden imports, `frozen=True, slots=True`, absence of
  `__post_init__` / custom `__hash__` / `__all__`, exact enum membership AND values,
  no extra public functions, file length limit.
- The canonical case with its tolerance.
- **At least one numeric case that the spec does not show.**

## Out of scope
<The most important section. Be explicit and generous here.>
- Do NOT add database access, ORM models or migrations
- Do NOT add HTTP endpoints
- Do NOT implement the optimizer or any scheduling logic
- Do NOT add logging frameworks, DI containers or decorators
- Do NOT refactor or reorganise existing files
- Do NOT create abstract base classes or interfaces
- Do NOT add caching

## Style constraints
- Python 3.12, type hints on every public function
- Pure functions only: no I/O, no global state, no side effects
- Variable names carry their unit: `massa_kg_ms_ha`, not `massa`
- Domain nouns stay in Portuguese: `piquete`, `lote`, `massa_forragem`, `cultivar`
- Docstrings and comments in English
- Prefer functions over classes; no abstraction without a second use case
- Maximum 300 lines per file
````

---

## Exemplo de spec bem dimensionada vs. mal dimensionada

| ❌ Mal dimensionada | ✅ Bem dimensionada |
|---|---|
| "Implement the sensing module" | "Implement `calcular_ndvi(red, nir) -> float` with range validation" |
| "Make the optimizer work" | "Implement greedy allocation: sort lotes by urgency, assign to best apt piquete" |
| "Add the Telegram integration" | "Implement `TelegramChannel.send(chat_id, text) -> bool` conforming to the `Channel` protocol" |
| "Build the farm setup screen" | "Implement paddock polygon drawing on a Leaflet map, emitting GeoJSON on save" |

## Checklist antes de emitir uma spec

- [ ] Nenhum `TODO-PARAM` pendente entre os números usados
- [ ] Todos os números têm fonte na tabela de constantes
- [ ] `Out of scope` tem pelo menos 5 itens
- [ ] Critérios de aceitação são todos binários
- [ ] Existe pelo menos um caso de teste com número esperado concreto
- [ ] Nenhum contrato de `06-ARQUITETURA-E-STACK.md` §3 foi alterado
- [ ] A spec faz sentido para quem nunca viu o projeto
- [ ] A spec **não** contém arquivo de teste pronto (ADR-011)
- [ ] O kit de aceite existe em `revisoes/KIT-ACEITE-<NNN>.md` e tem ≥1 caso oculto
- [ ] Nenhum `__init__.py` na lista de arquivos a tocar
