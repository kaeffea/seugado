# RUNBOOK-REV-007 — Commitar as correções de ordem do passo zero

**Origem:** chat `[ARQUITETURA] Revisão pós-F-001`, em resposta ao RELATORIO-REV-006.
**Autoriza:** nenhuma ADR nova — só regra de método.
**Modelo recomendado:** Sonnet, esforço médio.

Este runbook **é** o commit da documentação pendente. Por isso as conferências de conteúdo
vêm antes do commit, e a mensagem do commit é a do passo 3 — não a genérica do passo zero.

Sem lista fechada de arquivos: qualquer coisa em `docs/`, `README.md`, `CLAUDE.md`,
`pyproject.toml` ou `revisoes/` entra. Arquivo em `src/` ou `tests/` → pare e relate.

## 1 · Conferir conteúdo (antes de commitar)

- [ ] `cd /mnt/c/code/seugado && git status --porcelain` → nada em `src/` nem `tests/`.
- [ ] `wc -c CLAUDE.md` → esperado **8415 bytes**.
- [ ] `grep -c "Verificação vem antes do commit" CLAUDE.md` → **1**.
- [ ] `grep -c "Mensagem do commit" CLAUDE.md` → **1**.
- [ ] `wc -c docs/08-METODO-DE-TRABALHO-LLM.md` → esperado **13060 bytes**, com tolerância:
      o que importa é o `grep` abaixo, não o número exato.
- [ ] `grep -c "Mecanismo identificado em 17/09/2026" docs/08-METODO-DE-TRABALHO-LLM.md` → **1**.
- [ ] Qualquer uma dessas checagens falhando significa que a escrita do Arquiteto não chegou
      ao disco: **pare e relate**, dizendo qual arquivo e qual checagem. Já aconteceu três
      vezes; é a defesa que funciona.

## 2 · Verificar que nada de código quebrou

- [ ] `uv run pytest | tail -3` → **157 passaram, 0 falharam, 0 pulados**.

## 3 · Commitar

- [ ] `git add -A`
- [ ] `git commit -m "docs: verificacao antes do commit no passo zero; mecanismo da escrita perdida"`
- [ ] `git push`

## 4 · Critério de aceite

- [ ] `git status --porcelain` vazio.
- [ ] Um commit novo, sem arquivo de `src/` ou `tests/`.
- [ ] As seis checagens do passo 1 passaram **antes** do commit.

## 5 · Relatório

- [ ] `revisoes/RELATORIO-REV-007.md` no formato do `CLAUDE.md`.
- [ ] Se este runbook tiver funcionado como esperado — checagens antes, commit depois,
      mensagem correta — diga isso em uma linha. Confirmação de que a correção pegou vale
      tanto quanto achado novo.
