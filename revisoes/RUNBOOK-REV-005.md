# RUNBOOK-REV-005 — Commitar achados do CT-125 em `docs/05` e `docs/11`

**Origem:** chat `[PESQUISA] Régua de Manejo Embrapa (CT-125)`
**Autoriza:** nenhuma ADR nova — só atualização de dado, sem mudança de arquitetura.
**Modelo recomendado:** Sonnet, esforço baixo.

O Arquiteto já escreveu `docs/05-PARAMETROS-CULTIVARES.md` e `docs/11-ESTADO-ATUAL.md`
direto no repositório e no Project Knowledge. Não há código tocado — só documentação.
Este runbook apenas confere e commita.

**Invariante:** nenhum arquivo fora de `docs/05-PARAMETROS-CULTIVARES.md` e
`docs/11-ESTADO-ATUAL.md` deve aparecer no diff. Se aparecer, **pare e relate** — não é
deste runbook.

## 1 · Conferir o que mudou

- [ ] `cd /mnt/c/code/seugado && git status --porcelain`
- [ ] Confirmar que só aparecem `docs/05-PARAMETROS-CULTIVARES.md` e
      `docs/11-ESTADO-ATUAL.md`. Qualquer coisa em `src/`, `tests/` ou outro arquivo de
      `docs/` → pare e relate.
- [ ] `git diff docs/05-PARAMETROS-CULTIVARES.md docs/11-ESTADO-ATUAL.md` → ler por cima,
      só para confirmar que é a reescrita da tabela de alturas e do estado, não um acidente.

## 2 · Verificar que nada de código quebrou

- [ ] `uv run pytest` → **157/157**, igual ao estado anterior (nenhum teste deveria ter
      mudado, já que nenhum arquivo de código foi tocado).

## 3 · Commitar

- [ ] `git add docs/05-PARAMETROS-CULTIVARES.md docs/11-ESTADO-ATUAL.md`
- [ ] `git commit -m "docs: alturas canônicas do CT-125 (Régua de Manejo Embrapa) em 05; atualiza 11 (B3, DT6)"`
- [ ] `git push`

## 4 · Critério de aceite

- [ ] `git status --porcelain` vazio.
- [ ] `uv run pytest` continua 157/157.
- [ ] Um commit novo, só com os dois arquivos de `docs/`.

## 5 · Relatório

- [ ] Não precisa de `RELATORIO-REV-*` dedicado — é atualização de documento, não fatia.
      Se algo divergir do esperado (diff maior que o previsto, testes quebrando), registrar
      em `revisoes/RELATORIO-REV-005.md` no formato do `CLAUDE.md` e parar.
