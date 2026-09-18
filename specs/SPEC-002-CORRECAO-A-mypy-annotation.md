# SPEC-002-CORRECAO-A — Add the required mypy annotation to two test assertions

## Context

This is a one-line-each correction to a test file you already wrote for SPEC-002,
`tests/core/test_models.py`. Everything else in that file and in `src/seugado/core/models.py`
is correct and unchanged by this correction. Only two lines need a comment added.

This codebase has a standing style rule: comparing a `StrEnum` member directly to a string
literal (for example `SomeEnum.MEMBER == "value"`) is intentional and correct at runtime, but
the project's `mypy --strict` configuration flags it as a `comparison-overlap` error. The
project's convention is not to avoid this comparison — it is meaningful and used throughout the
codebase — but to silence the specific mypy check with an explicit, commented `# type: ignore`,
so the reason is visible to anyone reading the test rather than an unexplained suppression.

Two assertions in `test_metodo_pastejo_has_two_members` compare an enum member directly to a
string literal and are missing this annotation, which makes `mypy` fail on those two lines.

## Reading scope — read this file only

This spec is self-contained. Read **only** this file and `tests/core/test_models.py`. Do not
open, read or modify anything under `revisoes/`, `docs/`, `specs/`, `src/` or
`tests/conformance/`.

## Files to create or modify

- MODIFY `tests/core/test_models.py`

## Requirements

### R1 — Add the mypy ignore comment to both enum-to-string comparisons

In `test_metodo_pastejo_has_two_members`, these two lines currently read:

```python
    assert MetodoPastejo.CONTINUO == "continuo"
    assert MetodoPastejo.ROTACIONADO == "rotacionado"
```

Change them to:

```python
    assert MetodoPastejo.CONTINUO == "continuo"  # type: ignore[comparison-overlap]  # runtime equality is the documented behaviour; see 06 §7 rule 11
    assert MetodoPastejo.ROTACIONADO == "rotacionado"  # type: ignore[comparison-overlap]  # runtime equality is the documented behaviour; see 06 §7 rule 11
```

Use this exact comment text — it matches the wording already used for the same pattern
elsewhere in this codebase. Do not change the assertions themselves, their order, or anything
else in the function. Do not touch the third line of that function
(`assert len(list(MetodoPastejo)) == 2`) — it does not compare an enum member to a string and
does not need this annotation.

### R2 — Nothing else in the file changes

Every other line of `tests/core/test_models.py` — including the rest of
`test_parametros_regime_continuo_uses_max_min_heights` and every other test function — is
already correct. Do not reformat, reorder, or edit anything you were not asked to change here.

## Constants and parameters

None.

## Validation rules

None — this is a comment-only change to a test file.

## Testing — who does what

This correction does not need new tests. Run the existing suite yourself
(`pytest tests/core/test_models.py`) as a smoke check that nothing broke; it should still show
the same passing tests as before, now with `mypy` clean on this file too.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria

- [ ] Both lines in `test_metodo_pastejo_has_two_members` carry
      `# type: ignore[comparison-overlap]` followed by the exact comment text given in R1
- [ ] No other line in `tests/core/test_models.py` changed
- [ ] `uv run mypy` reports zero errors in `tests/core/test_models.py`
- [ ] `pytest tests/core/test_models.py` still passes with zero failures
- [ ] No new dependency added to `pyproject.toml`

## Worked example

Not applicable — this is a two-line comment addition, shown verbatim in R1.

## Acceptance kit (tester only — NEVER paste into the coding agent)

None new. The tester re-runs `uv run mypy` and the existing `KIT-ACEITE-002` structural
checks, which are unaffected by this correction.

## Out of scope

- Do NOT touch `src/seugado/core/models.py` — it already has zero mypy errors
- Do NOT touch `tests/conformance/`
- Do NOT add `# type: ignore` anywhere else in the file "for safety" — only the two lines named
  in R1 have the error
- Do NOT change the ignore code (must be exactly `comparison-overlap`, not a bare `# type: ignore`)

## Style constraints

- Same as SPEC-002: Python 3.12, no logic changes, comment-only edit
