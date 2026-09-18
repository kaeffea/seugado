# SeuGado — leia isto primeiro

Mapa simples do projeto. Os outros arquivos são densos de propósito; este não é.
Se você se perder, volte aqui.

---

## 1. O que o sistema faz

Olha o pasto por satélite e manda uma mensagem ao pecuarista dizendo **qual lote de gado
mover para qual piquete, e por quantos dias**.

Três palavras que aparecem em tudo:

- **piquete** — um pedaço cercado do pasto. É onde o gado fica.
- **lote** — um grupo de bois manejado junto. Nunca se move um boi sozinho, só o lote.
- **massa de forragem** — quanto capim existe ali, medido em quilos de matéria seca por
  hectare (`kg MS/ha`). Mede-se seco porque capim verde é quase todo água, e água não alimenta.

O problema que ele resolve: se o gado entra tarde, o capim já virou talo e alimenta pouco.
Se o gado sai tarde, a planta gasta reserva de raiz e o pasto degrada. As duas perdas se
evitam com a mesma decisão — **quando mover, para onde, por quanto tempo** — e hoje essa
decisão é tomada no olho ou em calendário fixo.

## 2. O que já existe

| Coisa | Estado |
|---|---|
| Base de conhecimento (14 documentos) | pronta |
| Repositório com git, ambiente e ferramentas | pronto |
| Modelo de domínio (`src/seugado/core/models.py`) | pronto, com parâmetro por regime (ADR-014) |
| Cálculos de forragem (`src/seugado/core/forragem.py`) | pronto, 196 testes passando |
| Regras de manejo, satélite, otimizador, mensagem | **nada ainda** |

Estamos na fundação: quatro fatias concluídas de 22 (F-000, F-001, F-001B, F-002), e a
próxima — F-003, regras de manejo — está destravada. O que trava o avanço **não é código nem
decisão**: são números agronômicos sem fonte confiável, que barram o uso em produção com
cultivar real, não a implementação (ver `docs/11-ESTADO-ATUAL.md`).

## 3. Quem faz o quê

Três ferramentas com papéis claros, sem burocracia de terminal para o Arquiteto:

| Quem | Faz | Nunca faz |
|---|---|---|
| **Você** | decide, aprova, aponta o Muse para a spec, cola o relatório final no Claude | escrever código ou documento à mão |
| **Claude (Arquiteto)**, no Project | decide arquitetura, pesquisa agronomia, escreve as specs (`specs/`) e atualiza a documentação | escrever código de produção ou gerar runbooks de terminal |
| **Muse Code** | escreve o código de produção em `src/seugado/` a partir da spec, e testes próprios em `tests/core/` | decidir arquitetura |
| **Antigravity (Gemini)** | roda os testes no WSL, arruma lints/anotações de tipo simples, faz o commit/push no Git e entrega 1 relatório final | inventar parâmetros ou alterar regras de negócio |

Por que o Muse não decide arquitetura: ele é um modelo direto de contexto curto. Se puder escolher, escolhe diferente a cada chamada.
Por que o Antigravity cuida de terminal e testes: ele opera diretamente no ambiente, resolve atritos simples de tipagem sem criar novas specs e poupa a cota de tokens do Claude Projects.

## 4. O ciclo de uma fatia

```
1. No Claude Projects:       Gera a spec em specs/SPEC-NNN-*.md
2. No Muse Code:             "Leia specs/SPEC-NNN-*.md e implemente"
3. No Antigravity:           "Teste e commite a fatia" 
                             (Ele roda ruff/mypy/pytest, arruma lints, commita e entrega o relatório)
4. No Claude Projects:       Você cola o relatório final → Arquiteto fecha a fatia e abre a próxima!
```

Suas ações: **apontar o Muse para a spec, pedir para o Antigravity testar/commitar, e avisar o Claude Projects que terminou.** Zero runbooks manuais. Zero uploads de arquivos.

## 5. Onde fica cada coisa

Na raiz fica apenas o `README.md` como guia do projeto, mais as configurações (`pyproject.toml`, `uv.lock`, `.gitignore`). Todo o resto está organizado em pastas:

```
docs/
  00-INSTRUCOES    o texto que vai no campo de instruções do Project + o protocolo de leitura
  01-VISAO         o que o produto é e o que está fora de escopo
  02-GLOSSARIO     o nome certo de cada coisa. Em dúvida de vocabulário, é aqui
  03-DOMINIO       a agronomia, explicada para quem não é da área
  04-SENSORIAMENTO como o satélite vira número
  05-PARAMETROS    TODO número agronômico, com fonte. Nada entra em código sem estar aqui
  06-ARQUITETURA   stack, módulos, contratos, regras de código, ambiente
  07-MOTOR         o otimizador: formulação e restrições
  08-METODO        método de trabalho com LLMs (Claude Projects + Muse Code + Antigravity)
  09-TEMPLATE      o molde de toda spec para o Muse
  10-ROTEIRO       as 22 fatias, na ordem
  11-ESTADO        ⬅ o que está feito, o que está travado, qual o próximo chat
  12-ADR           toda decisão fechada, com o porquê
  13-HISTORICO     arqueologia: bloqueios fechados, handoffs antigos. NÃO se lê por padrão

src/seugado/       o código do app (src-layout)
tests/             core = testes do Muse · conformance = testes de conformidade
specs/             as specs emitidas para o Muse Code
revisoes/          relatórios finais de cada fatia (arquivo/ contém o legado)
```

`src/seugado/` em vez de `seugado/seugado/` é convenção de Python (*src-layout*): evita que
um comando rodado na raiz importe a pasta local em vez do pacote. O caminho de import não
muda — continua `from seugado.core...`.

**Comece sempre pelo `docs/11-ESTADO-ATUAL.md`.** É o único que muda toda semana.

**O Project Knowledge está vazio, de propósito.** Nada é enviado para lá. O Claude lê estes
arquivos direto do disco, e por isso todo prompt precisa dizer quais arquivos ler — a tabela
de leitura por etiqueta está em `docs/00-INSTRUCOES-CUSTOM-INSTRUCTIONS.md`.

## 6. Duas regras que explicam quase todas as decisões

1. **Nenhum número sem fonte.** Um parâmetro agronômico plausível e falso passa
   despercebido e contamina tudo depois dele. Se falta fonte, marca-se `TODO-PARAM` e a
   implementação espera. É por isso que o projeto parece travado: está travado de propósito.
2. **Custo R$ 0,00 até o MVP.** Toda escolha de stack cabe em camada gratuita.

## 7. Ambiente

O código roda no **WSL Ubuntu**, não no Windows — o Windows desta máquina não tem Python.
`.venv` criada com `uv`. Comandos: `uv sync --group dev`, `uv run pytest`, `uv run ruff check .`,
`uv run mypy`.
