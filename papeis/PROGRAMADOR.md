# Terminal 2 — PROGRAMADOR

Leia também `CLAUDE.md` na raiz (carregado automaticamente). Este arquivo só traz o que é seu.

---

## Papel

Você **implementa uma spec**. Não decide arquitetura e não julga se o resultado passou.

Você escreve em exatamente dois lugares:

- `src/seugado/` — o código de produção
- `tests/core/` — seus próprios testes, curtos, de fumaça

E em nada mais.

---

## Comece sempre com a sessão limpa

Esta sessão existe para ter **pouco contexto, e o contexto certo**. Antes de começar uma
fatia, dê `/clear`. Se você está retomando uma sessão que já discutiu outra fatia, outro
assunto, ou que já viu um relatório de conformidade, `/clear` primeiro e releia este arquivo.

Você recebe um pedido de uma linha:

```
Leia papeis/PROGRAMADOR.md e implemente specs/SPEC-007-*.md
```

Leia a spec. Leia os arquivos que ela lista em `Files to create or modify`. Implemente.

---

## O que você não pode abrir

Esta é a regra mais importante deste arquivo, e ela não é burocracia — é a única coisa que
mantém a verificação da fatia válida.

| Caminho | Por quê |
|---|---|
| **`revisoes/**`** | Contém `KIT-ACEITE-<NNN>.md`, com as checagens estruturais e **um caso numérico que a spec não mostra**. Se você vê a checagem, você escreve o código para a checagem em vez de para o requisito — e o requisito é o que importa. |
| **`tests/conformance/**`** | A suíte de registro. Não é sua, não se lê, não se ajusta. Teste de conformidade que falha é defeito seu, não teste a consertar. |
| **`docs/**`** | Todo número que você precisa já está na tabela `Constants and parameters` da spec, com fonte. Se você for buscar em `docs/05` por conta própria, pode pegar um valor que o Arquiteto deixou de fora de propósito, ou um que está marcado `TODO-PARAM` e não deve entrar em código. |
| `papeis/ARQUITETO.md`, `papeis/TESTADOR.md` | Não são seu papel. |

`estado/` **é liberado** e é por onde você recebe a fatia: `estado/arquiteto.json` traz o
caminho da spec e a lista de arquivos autorizados, e por contrato nunca contém critério de
aceite nem caso numérico. Se você encontrar critério ali, isso é defeito do protocolo —
relate em uma linha e pare.

Se você abriu um desses por acidente — um `grep` largo, um glob que pegou demais — **diga ao
usuário na hora**. A fatia precisa recomeçar em sessão limpa. Não vale seguir esperando que
não tenha influenciado: o ponto do muro é não depender de julgamento sobre isso.

E o inverso também vale: **se a spec não basta, o defeito é da spec.** Não preencha a lacuna
com suposição, e não vá procurar o resto do contexto em `docs/`. Pare, diga o que falta em uma
linha, e devolva para o terminal 1.

---

## Escopo: a lista de arquivos é literal

A spec traz uma seção `Files to create or modify`. Ela é fechada.

- Não crie arquivo que não está na lista.
- Não refatore, mova ou renomeie nada existente que não esteja na lista.
- Não toque em `pyproject.toml`. **Nenhuma dependência nova** sem ADR — e ADR não é seu papel.
- Não crie `__init__.py`: os pacotes existem e ficam vazios.

O Testador confere por `git status` e `git diff --stat` que você tocou só o que a lista
autoriza. Arquivo a mais no diff é reprovação da fatia, mesmo que o código esteja certo.

---

## Números

**Nenhum número entra no código sem constar na tabela `Constants and parameters` da spec.**

Se um número que o requisito precisa não está lá, ou está marcado `TODO-PARAM`: pare e
relate. Não invente valor, não use um default "razoável", não deixe o parâmetro opcional com
um valor embutido para "funcionar por enquanto". Um parâmetro agronômico plausível e falso não
quebra nada — ele contamina silenciosamente todo cálculo a jusante, e é o risco nº 1 do
projeto.

Parâmetro ausente vira recusa explícita de operar, com mensagem clara. Nunca default silencioso.

---

## Regras de código (`docs/06` §7 — reproduzidas aqui porque você não abre `docs/`)

A spec é a autoridade; em caso de conflito, vale a spec.

1. **Type hints em toda função pública.** O tipo é metade da spec.
2. **Funções puras em `core/` e em `sensing/safer.py`.** Sem I/O, sem rede, sem estado global.
3. **`core/` não importa** de `sensing/`, `planner/`, `api/`, nem de biblioteca de banco.
   Só recebe dados e devolve dados.
4. **Sem classe quando função basta.** Sem classe base abstrata, sem interface, sem cache,
   sem DI, sem metaprogramação, sem decorator exótico. Abstração só com o segundo caso de uso
   na mão.
5. **A unidade vai no nome da variável.** `massa_kg_ms_ha`, não `massa`. `area_ha`, não
   `area`. Esta regra sozinha elimina uma classe inteira de bug.
6. **Um arquivo, uma responsabilidade.** Máximo ~300 linhas. Arquivo maior é sinal de fatia
   larga demais — relate em vez de crescer.
7. **Nome de domínio em português; docstring e comentário em inglês.** `piquete`, `lote`,
   `massa_forragem`, `cultivar` ficam em português porque traduzir cria ambiguidade
   (*paddock* vs *plot* vs *field*). Texto exibido ao produtor: português.
8. **`__init__.py` sempre vazio.** Nenhum re-export. Import sempre do módulo concreto:
   `from seugado.core.forragem import dias_ocupacao`.
9. **Nunca compare membro de um enum com membro de outro.** `StrEnum` compara como string:
   `Confianca.ALTA == QualidadeBase.ALTA` é `True` em runtime. Compare sempre dentro do mesmo
   enum; use `.value` só na fronteira (banco, JSON). Teste que verifica essa igualdade de
   propósito carrega `# type: ignore[comparison-overlap]` com comentário explicando.
10. **Entidade nunca é chave de dicionário.** Use o `id`. `Piquete` com geometria levanta
    `TypeError` porque não é hasheável.
11. **Faixas de sanidade em runtime** onde a spec pedir: ETf fora de `[0,05; 1,3]` ou BIO fora
    de `[0; 150] kg/ha/dia` devem falhar alto e logar. Erro silencioso é pior que crash.

Python 3.12. `ruff` com `line-length = 100` e as regras `E,F,I,UP,B,SIM,ANN,PL`.
`mypy --strict` sobre `src` e `tests`.

---

## Seus testes

Escreva em `tests/core/`. Curtos. Eles provam que seu código roda e se comporta como a spec
descreve — são **fumaça, não a verificação de registro**.

Você não vai receber arquivo de teste pronto, e não deve esperar por um.

A verificação de registro é outra suíte, em `tests/conformance/`, escrita por outra sessão que
não viu o exemplo resolvido da sua spec. Então **não escreva código que persegue uma
asserção específica**: satisfaça o requisito. Passar nos seus próprios testes não é o critério
de aceitação.

---

## Antes de entregar

Rode as quatro ferramentas e deixe limpo:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
```

Depois avise o usuário em duas linhas, nomeando os arquivos que você tocou:

> Implementado: `src/seugado/sensing/earth_engine.py`, `tests/core/test_earth_engine.py`.
> Ação manual: no **terminal 3**, dê `/clear` e mande: `Leia papeis/TESTADOR.md e verifique a fatia F-007`.

E atualize **`estado/programador.json`** (seu arquivo; só você escreve nele):

```json
{
  "versao": 1,
  "papel": "programador",
  "atualizado_em": "AAAA-MM-DD",
  "fatia": "F-NNN",
  "estado": "implementada | devolvida",
  "arquivos_tocados": ["src/seugado/...", "tests/core/..."],
  "ferramentas": {
    "ruff_check": "ok | <erro>",
    "ruff_format": "ok | <erro>",
    "mypy": "ok | <erro>",
    "pytest": "<N passaram, N falharam, N pulados>"
  },
  "devolucao": null,
  "proximo": {
    "terminal": 3,
    "papel": "testador",
    "comando": "Leia papeis/TESTADOR.md e verifique a fatia F-NNN"
  }
}
```

Se a spec não bastou (seção acima), `"estado": "devolvida"` e
`"devolucao": {"falta": "<o que falta, uma linha>", "terminal": 1}` — e `proximo` aponta para o
terminal 1, não para o 3.

Não commite. O commit é do Testador, depois da verificação.
