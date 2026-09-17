# RELATÓRIO-REV-005 — RUNBOOK-REV-005 (commit dos achados do CT-125/CT-135 em `docs/05` e `docs/11`)
**Data:** 17/09/2026 · **Veredicto:** reprovada — execução interrompida na etapa 1 (invariante violado)

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | Só `docs/05-PARAMETROS-CULTIVARES.md` e `docs/11-ESTADO-ATUAL.md` aparecem no diff | ❌ | `git status --porcelain` mostra `docs/01-VISAO-E-ESCOPO.md` modificado; `docs/05-PARAMETROS-CULTIVARES.md` **não aparece** no diff |
| 2 | `uv run pytest` → 157/157 | ✅ | 157 pontos (72+72+13), 0 falhas, 100% — ver seção Execução |
| 3 | Commit criado só com os dois arquivos de `docs/` | ⚠️ não executado | Etapa 3 não foi alcançada — parada obrigatória na etapa 1, conforme invariante do runbook |

## Execução
- `git status --porcelain` → `M docs/01-VISAO-E-ESCOPO.md`, `M docs/11-ESTADO-ATUAL.md`, `?? revisoes/RUNBOOK-REV-005.md` (o próprio runbook, não entra no commit)
- `git diff --stat` → `docs/01-VISAO-E-ESCOPO.md | 33 +++++++++++++++++++++++++++++++++` e `docs/11-ESTADO-ATUAL.md | 38 ++++++++++++++++++++++++++++++--------`. `docs/05-PARAMETROS-CULTIVARES.md` não consta.
- `ruff check .` / `ruff format --check .` / `mypy` → não executados (não pedidos pelo runbook; nenhum arquivo de código foi tocado)
- `pytest` → 157 passaram, 0 falharam, 0 pulados (contagem por pontos no output `-q`; a linha de resumo final não foi impressa pelo runner nesta sessão, mas a ausência de `F`/`E` e a contagem de pontos confirmam 157/157, igual ao estado anterior)
- Nenhum `git add` / `git commit` / `git push` foi executado.

## Defeitos na implementação
Nenhum — não houve código de produção tocado nesta revisão.

## Achados fora da implementação
1. **Invariante do runbook violado:** o diff inclui `docs/01-VISAO-E-ESCOPO.md`, com uma seção nova inteira ("Ideias registradas — não são escopo, são candidatas", 33 linhas) sobre migração assistida de contínuo→rotacionado e pesquisa de mercado em Alagoas. Esse conteúdo não tem relação nenhuma com o CT-125/CT-135 nem com o escopo declarado do RUNBOOK-REV-005. Por instrução explícita do runbook ("Se aparecer, pare e relate — não é deste runbook"), a execução foi interrompida antes do commit.
2. **`docs/05-PARAMETROS-CULTIVARES.md` não foi alterado.** O runbook afirma que "o Arquiteto já escreveu `docs/05-PARAMETROS-CULTIVARES.md`... direto no repositório", mas o arquivo não aparece em `git status` nem em `git diff --stat`. Ou a escrita em `05` não foi de fato commitada/salva no working tree, ou ficou em outro branch/sessão. Sem a mudança em `05`, o commit proposto pelo runbook (que junta `05` e `11`) fica incompleto — `11` já fala em alturas resolvidas com fonte e confiança, mas a tabela real de `05` continua no estado anterior.
3. **Divergência de numeração da fonte:** o runbook e o título do chat de origem dizem "CT-125" (Comunicado Técnico 125), mas o próprio `docs/11-ESTADO-ATUAL.md` (na seção "Perguntas em aberto" que o próprio diff adiciona) registra que o número correto pode ser "CT-135" e que isso ainda não foi confirmado. O nome do arquivo deste relatório e o commit sugerido no runbook citam "125"; se a fonte for de fato 135, tanto o runbook quanto a futura citação em `05` precisam do número certo.

## Critérios não verificáveis
- Critério 3 (commit) não pôde ser verificado porque a execução parou na etapa 1, conforme a própria instrução do runbook. Não é seguro commitar `docs/11-ESTADO-ATUAL.md` sozinho (sem `05`) nem incluir `docs/01-VISAO-E-ESCOPO.md` sem confirmação do Arquiteto de que essa seção é intencional e pertence a este commit.

## Recomendação
Não commitar nada nesta sessão. Encaminhar para o Arquiteto (chat `[ARQUITETURA]` ou `[TRIAGEM]`):
- Confirmar se a edição em `docs/01-VISAO-E-ESCOPO.md` é intencional e, se sim, se deve ir num commit separado (ela não é "achado do CT-125/CT-135").
- Confirmar por que `docs/05-PARAMETROS-CULTIVARES.md` não recebeu a reescrita da tabela de alturas que o runbook pressupõe, e reenviar o arquivo ou reemitir o runbook depois disso.
- Resolver a pergunta em aberto sobre CT-125 vs. CT-135 antes da citação formal em `05`.
