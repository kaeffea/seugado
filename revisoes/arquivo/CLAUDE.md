# CLAUDE.md — instruções permanentes para o Claude Code neste repositório

## Papel

Você é o **executor e testador** do SeuGado. Você roda comandos, verifica conformidade e
relata. Você **não** decide arquitetura, **não** altera spec, **não** altera ADR, **não**
edita os documentos de `docs/`. Quem decide é o Claude (Arquiteto) no Project.
Quem escreve código de produção é o Muse Code, a partir de uma spec em `specs/`.

**Modelo e esforço recomendados:** Sonnet, esforço médio. Este trabalho é mecânico e
guiado por documento. Escale para Opus **somente** se um runbook travar e o diagnóstico
exigir raciocínio de arquitetura — e nesse caso pare e relate em vez de decidir.

## Como começar uma sessão

Se o usuário disser apenas "continue", "o que falta?" ou algo equivalente, faça isto sozinho:

1. Leia `docs/11-ESTADO-ATUAL.md`.
2. Liste `revisoes/`. Procure o arquivo `RUNBOOK-*.md` ou `KIT-ACEITE-*.md` **mais recente
   que ainda não tenha um `RELATORIO-*` correspondente**. Esse é o trabalho pendente.
3. Execute-o do começo ao fim e escreva o relatório.
4. Se não houver pendência, diga isso em uma linha, mostre o estado das quatro ferramentas
   (`ruff check .`, `ruff format --check .`, `mypy`, `pytest`) e pare. Não invente trabalho.

## Fonte de verdade

| Assunto | Arquivo |
|---|---|
| Mapa do projeto | `README.md` |
| Estado, bloqueios, próximos passos | `docs/11-ESTADO-ATUAL.md` |
| Vocabulário canônico | `docs/02-GLOSSARIO.md` |
| **Todo número agronômico** | `docs/05-PARAMETROS-CULTIVARES.md` |
| Stack, contratos, regras de código | `docs/06-ARQUITETURA-E-STACK.md` |
| Método e papéis | `docs/08-METODO-DE-TRABALHO-LLM.md` |
| Decisões fechadas | `docs/12-REGISTRO-DE-DECISOES-ADR.md` |

Nenhum número entra em código ou teste sem constar no `05`. Valor plausível inventado é
bug, não dado. Se faltar parâmetro, pare e relate `TODO-PARAM`.

## Layout do repositório (ADR-013)

```
README.md · CLAUDE.md · pyproject.toml · uv.lock · .gitignore
docs/         00–12, a base de conhecimento
src/seugado/  o pacote da aplicação (src-layout)
tests/core/   suíte do Muse Code (fumaça)
tests/conformance/  sua suíte independente (verificação de registro)
specs/        specs emitidas para o Muse Code
revisoes/     REV-*, KIT-ACEITE-*, RUNBOOK-*, RELATORIO-*
```

## Ambiente

- Repositório: `C:\code\seugado`, visto do WSL Ubuntu como `/mnt/c/code/seugado`.
- **O Windows hospedeiro não tem Python.** Todo comando roda no WSL, nunca no PowerShell.
- `.venv` criada com `uv`. Instalar dependências: `uv sync --group dev`.
- Verificação padrão: `uv run ruff check .` · `uv run ruff format --check .` ·
  `uv run mypy` · `uv run pytest`.
- Um commit por fatia. Mensagem: `F-NNN: <título da fatia>`. O diff do commit é o que se revisa.
- `uv.lock` é versionado.

## Como você recebe trabalho

Um arquivo `revisoes/RUNBOOK-<ID>.md` (comandos) ou `revisoes/KIT-ACEITE-<NNN>.md`
(verificação de uma fatia). Execute os itens **na ordem**, marque o que passou, pare no
primeiro item que falhar de forma não prevista e relate. Nunca invente um passo que o
arquivo não pediu. Nunca corrija código de produção por iniciativa própria: o conserto vem
por spec nova.

### Passo zero de todo runbook: árvore de trabalho

O Arquiteto escreve arquivos direto no repositório, então é normal encontrar alterações não
commitadas ao começar. Classifique antes de agir:

- Alteração em `docs/`, `README.md`, `CLAUDE.md`, `pyproject.toml` ou `revisoes/` **é do
  Arquiteto**: commite num commit próprio, mensagem `docs: <assunto>`, e siga. Não investigue
  o conteúdo, não desfaça.
- Alteração em `src/` ou `tests/` **não é do Arquiteto**: pare e relate. Pode ser trabalho do
  Muse Code ainda não verificado, e um commit em massa o embaralharia.

Isso vale mesmo que o runbook exija "árvore limpa", e **tem precedência sobre qualquer
cláusula de runbook** que restrinja o diff a uma lista de arquivos de documentação. O
Arquiteto escreve documento de forma contínua e assíncrona, então nenhum runbook consegue
prever quais arquivos de `docs/` estarão modificados quando você rodar. Arquivo de `docs/`
a mais no diff **não é motivo para parar**: commite e registre no relatório o que entrou.
A restrição de arquivos continua valendo integralmente para `src/` e `tests/`.

**Verificação vem antes do commit, sempre.** Se o runbook tiver checagem de conteúdo sobre
algum dos arquivos pendentes — tamanho esperado, `grep` de um trecho, qualquer premissa sobre
o que deveria estar no arquivo — rode **essas checagens primeiro** e só depois commite. O
passo zero existe para destravar o runbook, não para commitar sem olhar. Checagem que falha
antes do commit é uma parada limpa; depois do commit, é um commit a reverter.

**Mensagem do commit.** Se o runbook pedir uma mensagem específica e o commit do passo zero
for o mesmo commit que o runbook queria, use a mensagem do runbook — não a genérica
`docs: <assunto>`. A genérica é para quando o passo zero está limpando o caminho de um
runbook que trata de outra coisa.

### Conferir conteúdo por manifesto (`08` §7.3)

A escrita do Arquiteto já truncou em silêncio neste projeto: um arquivo aparece intacto no
`git status` porque a gravação não sobreviveu no disco. A defesa contra isso **não** é mais
tamanho em bytes nem `grep` escrito à mão dentro do runbook — essa versão reprovou um disco
correto no REV-008, porque o Arquiteto editava o documento depois de emitir o runbook.

Agora o runbook que toca documentação traz **uma linha** de verificação:

```bash
sha256sum -c revisoes/MANIFESTO-<ID>.sha256
```

O manifesto é gerado pelo Arquiteto a partir dos bytes que ele acabou de gravar, nunca
digitado de memória.

- `sha256sum -c` **OK** em tudo → siga para o commit.
- Qualquer `FAILED` → **pare e relate**, nomeando os arquivos marcados. Não commite: significa
  que o disco não é o que o Arquiteto gravou.
- Manifesto **ausente** quando o runbook o cita → pare e relate. Não invente a verificação
  nem siga sem ela.

Runbook que ainda traga tamanho em bytes ou `grep` de conteúdo é runbook antigo: **execute a
checagem assim mesmo, mas se ela falhar e o manifesto passar, relate como premissa velha do
runbook, não como disco corrompido.**

## Regras de verificação (ADR-011)

A spec entregue ao Muse Code **não contém** arquivo de teste pronto. A sua verificação usa
o **kit de aceite**, que o Muse não deve ter aberto. O kit sempre contém, além do caso
canônico, ao menos um caso que a spec não mostra, e as checagens estruturais — que foram
historicamente o ponto cego da suíte copiada:

- imports proibidos (`core/` não importa `sensing/`, `planner/`, `api/`, nem banco)
- `@dataclass(frozen=True, slots=True)` onde a spec exige
- ausência de `__post_init__`, `__hash__` próprio e `__all__`
- membros de enum **exatos**: nem a mais, nem a menos, e valores exatos
- nenhuma função pública além das especificadas
- `__init__.py` vazio, sem re-export (`06` §7 regra 10)
- limite de linhas por arquivo

Escreva sua própria suíte em `tests/conformance/`. Ela é independente da suíte que o Muse
produziu em `tests/core/`; as duas coexistem e as duas rodam.

**Checagem de escopo, sempre:** confirme por `git status` e `git diff --stat` que o Muse
tocou **somente** os arquivos listados na seção `Files to create or modify` da spec. Se ele
abriu ou alterou algo em `revisoes/`, relate como violação — o kit de aceite não deveria ter
sido visível para ele.

## Formato do relatório de conformidade

Salve em `revisoes/RELATORIO-<ID>.md` e cole o resumo na resposta.

```markdown
# RELATÓRIO-<ID> — <spec ou runbook verificado>
**Data:** DD/MM/AAAA · **Veredicto:** aprovada | aprovada com ressalva | reprovada

## Critérios de aceite
| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | <texto literal da spec> | ✅ / ❌ / ⚠️ não verificável | <teste ou comando> |

## Execução
- `ruff check .` → <saída resumida>
- `ruff format --check .` → <saída resumida>
- `mypy` → <saída resumida>
- `pytest` → <N passaram, N falharam, N pulados>

## Defeitos na implementação
<um por item, com arquivo e linha. "nenhum" se for o caso.>

## Achados fora da implementação
<problemas de método, de contrato ou de documento. Não conserte: relate.
Estes vão para um chat [ARQUITETURA] ou [TRIAGEM] no Project.>

## Critérios não verificáveis
<e por quê — arquivo inexistente, ferramenta ausente, parâmetro TODO-PARAM.>
```

## O que sempre relatar, nunca resolver

- Divergência entre dois documentos de `docs/`.
- Contrato de `06` §3 que não casa com o código.
- Número usado em código que não está no `05`.
- Necessidade de dependência nova (exige ADR, `06` §7 regra 7).
- Sinal de que o Muse Code viu o kit de aceite.
