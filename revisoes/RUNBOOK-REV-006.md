# RUNBOOK-REV-006 — Commitar a documentação pendente (substitui o REV-005)

**Origem:** chat `[ARQUITETURA] Revisão pós-F-001`
**Substitui:** RUNBOOK-REV-005, reprovado corretamente. Ele restringia o diff a dois arquivos
de `docs/`, e o Arquiteto havia escrito outros depois de emitir o runbook.
**Autoriza:** nenhuma ADR nova — atualização de documento e de dado, sem mudança de arquitetura.
**Modelo recomendado:** Sonnet, esforço médio.

**Sem lista fechada de arquivos.** Qualquer arquivo de `docs/`, `README.md`, `CLAUDE.md`,
`pyproject.toml` ou `revisoes/` que apareça modificado é trabalho do Arquiteto: entra no
commit. Arquivo em `src/` ou `tests/` **não** é — se aparecer, pare e relate.

## 1 · Conferir conteúdo, não só presença

Duas premissas deste runbook precisam de confirmação antes do commit. Se alguma falhar,
**pare e relate** — foi exatamente essa conferência que salvou o ciclo anterior.

- [ ] `cd /mnt/c/code/seugado && git status --porcelain`
- [ ] Nada em `src/` nem em `tests/`. Se houver, pare.
- [ ] `wc -c docs/05-PARAMETROS-CULTIVARES.md` → esperado **15331 bytes**. Se vier ~10108, a
      tabela do CT-135 não está no disco: pare e relate.
- [ ] `grep -c "Comunicado técnico, 135" docs/05-PARAMETROS-CULTIVARES.md` → **1 ou mais**.
      Zero significa que a citação corrigida não chegou: pare e relate.
- [ ] `grep -c "Tabela A — Pastejo rotacionado" docs/05-PARAMETROS-CULTIVARES.md` → **1**.
- [ ] `grep -c "Ideias registradas" docs/01-VISAO-E-ESCOPO.md` → **1**. Essa seção é
      intencional: registra duas ideias pós-MVP a pedido do usuário.

## 2 · Verificar que nada de código quebrou

- [ ] `uv run pytest` → **157 passaram, 0 falharam, 0 pulados**. Nenhum arquivo de código foi
      tocado, então qualquer outro número é sinal de que algo mais aconteceu: relate.
- [ ] Se o resumo final do `pytest` não for impresso, rode `uv run pytest -q --no-header -p
      no:cacheprovider` ou `uv run pytest | tail -5` para obter a linha de contagem. Contar
      pontos no output é aproximação; o relatório merece o número literal.

## 3 · Commitar

- [ ] `git add -A`
- [ ] `git commit -m "docs: alturas do CT-135, ideias pós-MVP, fila de chats e regras de runbook"`
- [ ] `git push`

## 4 · Critério de aceite

- [ ] `git status --porcelain` vazio.
- [ ] Um commit novo, sem nenhum arquivo de `src/` ou `tests/`.
- [ ] `uv run pytest` em 157/157.
- [ ] `docs/05-PARAMETROS-CULTIVARES.md` no commit, com a tabela do CT-135 presente.

## 5 · Relatório

- [ ] `revisoes/RELATORIO-REV-006.md` no formato do `CLAUDE.md`.
- [ ] Listar em "Achados fora da implementação" **quais** arquivos de documentação entraram
      no commit. É o registro de que o commit foi maior que o assunto do runbook — o que
      agora é esperado, não é desvio.
