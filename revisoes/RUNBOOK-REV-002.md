# RUNBOOK-REV-002 — Aplicar REV-001, política de lockfile e dívida de lint

**Origem:** chat `[ARQUITETURA] Revisão pós-F-001` · **Autoriza:** ADR-010, ADR-011, ADR-012
**Responde a:** RELATORIO-REV-001, achados A1, A2, A3, A4
**Modelo recomendado:** Sonnet, esforço médio.

Execute na ordem, um commit por bloco. Pare e relate no primeiro erro não previsto.
Os documentos `00`–`12` já foram reescritos pelo Arquiteto e chegam **não commitados** —
seu trabalho com eles é commitar, não editar.

## 1 · Commitar as decisões (documentos)

- [ ] `cd /mnt/c/code/seugado && git status --porcelain`
- [ ] Confirmar que os arquivos modificados são: `02`, `03`, `05`, `06`, `08`, `09`, `10`,
      `11`, `12`, `pyproject.toml`, e novos em `revisoes/`. **Nada em `seugado/`.**
      Se `seugado/` aparecer, pare e relate.
- [ ] `git add -A && git commit -m "REV-001: ADR-010, ADR-011 e ADR-012 aplicadas"`

## 2 · Política de lockfile (achado A1)

Decisão do Arquiteto: **`uv.lock` é versionado.** Isto é aplicação, não biblioteca, e o
pipeline diário roda em GitHub Actions — build reproduzível depende do lock no repositório.
Já está registrado em `06` §8 e na ADR-012. Não incluir no `.gitignore`.

- [ ] `git add uv.lock && git commit -m "F-000: versionar uv.lock"`
- [ ] Confirmar `git status --porcelain` vazio.

## 3 · Dívida de lint e tipos (achados A3 e A4) — só em `tests/`

Escopo: **exclusivamente** `tests/core/` e `tests/conformance/`.
Não tocar `seugado/core/models.py`. Não alterar o comportamento de nenhum teste.
**Invariante:** `uv run pytest` continua em 157 passando, 0 falhando, 0 pulados. Se o número
de testes mudar, você alterou comportamento — desfaça e relate.

- [ ] `uv run ruff check --fix .` (resolve `UP017` e `I001`)
- [ ] `uv run ruff format tests/`
- [ ] `uv run pytest` → confirmar 157/157 antes de seguir.
- [ ] Resolver os 18 erros de `mypy`, com estas regras:
  - `no-untyped-def`, `no-untyped-call`, `union-attr`, `index`, `attr-defined`, `misc`:
    corrigir com anotação ou `assert` de estreitamento. Preferir `assert x is not None` a
    `# type: ignore` quando o teste já pressupõe o valor.
  - `comparison-overlap` (4 ocorrências, `Confianca` vs `QualidadeBase`): **são
    intencionais** — o teste documenta que `StrEnum` compara como string em runtime.
    Marcar cada uma com `# type: ignore[comparison-overlap]  # runtime equality is the
    documented behaviour; see 06 §7 rule 11` e **não** mudar a asserção.
  - `unused-ignore`: remover o `# type: ignore` que sobrou.
- [ ] `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy` · `uv run pytest`
      → esperado: zero erro nos quatro, 157/157.
- [ ] `git add -A && git commit -m "F-001: zerar divida de lint e tipos em tests/"`

## 4 · Critério de aceite deste runbook

- [ ] Três commits novos, nesta ordem, e `git status --porcelain` vazio ao final.
- [ ] `ruff check`, `ruff format --check`, `mypy` e `pytest` limpos.
- [ ] `seugado/core/models.py` **inalterado**: comprovar com
      `git log --oneline -- seugado/core/models.py` → apenas o commit `73ff3af`.
- [ ] Nenhum documento `00`–`12` editado por você: comprovar que os diffs desses arquivos
      estão todos no commit do bloco 1 e nenhum no commit do bloco 3.

## 5 · Relatório

- [ ] Escrever `revisoes/RELATORIO-REV-002.md` no formato do `CLAUDE.md`.
- [ ] Em **Achados fora da implementação**, registrar qualquer erro de `mypy` que você não
      conseguiu resolver sem mudar comportamento de teste. Não force: relate.

## 6 · Opcional — publicar no GitHub

Só se o usuário pedir. É o que permite o Project Knowledge sincronizar do repositório em
vez de re-upload manual.

- [ ] `gh auth status` (se não autenticado, pare e relate)
- [ ] `gh repo create seugado --private --source=. --push`
- [ ] Relatar a URL.
