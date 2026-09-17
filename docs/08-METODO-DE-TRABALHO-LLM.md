# Método de Trabalho com LLM — SeuGado

Como três modelos com papéis distintos constroem um sistema sem se perder e sem queimar cota.

---

## 1. Os três papéis

| Papel | Ferramenta | Recebe | Produz | Nunca faz |
|---|---|---|---|---|
| **Planejador / Arquiteto** | Claude (Opus/Sonnet) no Project | Knowledge + pedido do usuário | Specs, **kits de aceite**, **runbooks**, ADRs, análises, handoffs, e os próprios arquivos `00`–`12` | Escrever código de produção |
| **Programador** | Muse Code (Muse Spark 1.3) | **Só a spec**, autocontida, em inglês | Código + testes próprios | Tomar decisão de arquitetura. Ver o kit de aceite |
| **Testador / Executor** | Claude Code (Sonnet, esforço médio) | `CLAUDE.md` + kit de aceite ou runbook + código | Suíte independente, relatório de conformidade, execução de comando | Alterar spec, ADR ou documento `00`–`12` |

O Claude Code lê `CLAUDE.md`, na raiz do repositório, antes de agir: papel, ambiente WSL,
checagens estruturais obrigatórias e formato do relatório de conformidade vivem lá.

### A regra de ouro

> **O programador nunca recebe o histórico de planejamento.**
> Ele recebe a spec, que é autocontida.
> **E nunca recebe o kit de aceite** (ADR-011): se ele vê a checagem, ele escreve o código
> para a checagem em vez de para o requisito.

É isto que impede o crescimento de contexto de virar exponencial. Se a spec precisa do
histórico para ser compreendida, **a spec está errada** — não o programador.

### Por que o programador é o elo frágil

Muse Spark 1.3 é mais barato e de contexto mais curto. Consequências que moldam as specs:

- Escopo precisa ser **estreito e literal**. "Implemente o módulo de sensoriamento" falha.
  "Implemente `calcular_ndvi(red, nir) -> float` com validação de faixa" funciona.
- **Critérios de aceitação verificáveis**, não descrições de intenção.
- **Arquivos a tocar listados explicitamente.** Sem isso ele reorganiza o projeto sozinho.
- **Seção "Out of scope" obrigatória.** É a que mais economiza retrabalho: impede que ele
  "ajude" fazendo coisas não pedidas.
- Uma spec = **um arquivo ou um punhado pequeno**. Se precisa tocar 5 arquivos, é duas specs.

---

## 2. Fatias verticais (não sprints)

A unidade de planejamento é a **fatia**: um pedaço fino que atravessa todas as camadas e
produz algo demonstrável. Sem estimativa de tempo, sem prazo, sem sprint.

❌ "fazer todo o backend" → "fazer todo o frontend"
✅ "um piquete, uma cultivar, uma imagem, uma recomendação, na tela"

Depois engrossa: múltiplos piquetes → múltiplos lotes → otimização → clima → SAR → foto.

Roteiro completo em `10-ROTEIRO-DE-FATIAS.md`.

**Critério de fatia bem dimensionada:** executável lendo **no máximo 3–4 arquivos**.
Se precisa de mais, é fatia larga demais — quebre.

---

## 3. Tipos de chat

Toda primeira mensagem de um chat começa com uma etiqueta. O Claude infere e declara
se você esquecer.

| Etiqueta | Para quê | Produz |
|---|---|---|
| `[APRENDER]` | Você entender domínio ou método. Sem pressão de produzir nada | Entendimento |
| `[ARQUITETURA]` | Decisão estrutural, escolha entre abordagens | ADR pronto para colar |
| `[FATIA-NNN]` | Trabalhar uma fatia específica | Spec em inglês para o Muse Code |
| `[PESQUISA]` | Caçar parâmetro agronômico, avaliar biblioteca, ler paper | Bloco para `05-PARAMETROS` com fonte |
| `[REVISAO]` | Conferir o que o Muse Code produziu contra a spec | Relatório de conformidade |
| `[TRIAGEM]` | Algo quebrou ou o resultado saiu estranho | Diagnóstico + spec de correção |

### Sobre o chat `[APRENDER]`

Você disse que precisa aprender muita coisa. **Separe isso dos chats de produção**, por
dois motivos: (a) chat de aprendizado é longo e conversacional, e poluiria um chat de
decisão; (b) você vai querer voltar nele, e misturado fica impossível de achar.

Sugestão: um chat `[APRENDER]` por tema grande, não um só gigante.
`[APRENDER] Manejo de pastagens`, `[APRENDER] Sensoriamento remoto`,
`[APRENDER] Desenvolvimento orquestrado por LLM`, `[APRENDER] Otimização com CP-SAT`.

---

## 4. Ciclo de vida do chat

Não há número oficial de mensagens. Mas o comprimento da conversa **conta contra o limite
de uso** — cada turno reprocessa o histórico. Chat longo fica progressivamente mais caro
e de qualidade pior.

### Sinais de fim de vida útil

1. ~25 trocas
2. O assunto mudou para outra etiqueta
3. O Claude começou a repetir contexto já estabelecido
4. A fatia foi concluída
5. Você precisou reexplicar algo que já tinha explicado no mesmo chat ← **sinal mais forte**

O Claude monitora isso sozinho e emite o handoff. Você não precisa vigiar.

### Formato do handoff

```
🔄 FIM DE CICLO — abrir chat novo
Feito: <3 linhas>
Pendente: <3 linhas>
Próximo chat: [ETIQUETA] <título>
Primeira mensagem sugerida: "<prompt pronto para colar>"
Atualizar no Knowledge: <arquivos que mudaram>
```

O handoff escrito **substitui 50 mensagens de histórico**. É a técnica de maior retorno
de todo este documento.

### Continuidade entre chats de mesmo tipo

Quando um `[FATIA-007]` esgota e a fatia não acabou, abra `[FATIA-007] parte 2` e cole o
handoff como primeira mensagem. O Knowledge carrega o resto.

---

## 5. Economia de tokens — o que realmente funciona

### A inversão que muda tudo

> Conteúdo estável do Project é cacheado entre mensagens; reutilizá-lo é **mais barato** que
> reenviar texto novo. Não é grátis — o cache reduz o custo da releitura, não o elimina, e o
> detalhe da contabilidade nos planos de consumo não é público. Trate como desconto, não isenção.

**Consequência prática, que não depende do detalhe acima:** documento no Knowledge é lido uma
vez e reaproveitado; chat longo reprocessa o histórico **a cada turno**, e o histórico só cresce.
A estratégia correta é **base de conhecimento densa + chats magros**, não o contrário.

Por isso os documentos deste projeto são densos de propósito. Eles se pagam na primeira
reutilização.

### Regras operacionais

| Regra | Por quê |
|---|---|
| Nunca reimprimir o que está no Knowledge; citar pelo nome do arquivo | O Knowledge já está cacheado |
| Agrupar perguntas relacionadas numa mensagem | Cada mensagem reprocessa o histórico |
| Pedir e produzir **diffs**, não arquivos inteiros | Reescrever arquivo é o maior desperdício isolado |
| Nunca pedir "confira o que você escreveu" | Custo alto, retorno baixo. Verificação é papel do `[REVISAO]` |
| Revisar o prompt antes de enviar | Prompt vago gera rodada de esclarecimento |
| Referenciar documentos pelo nome ao perguntar | Ajuda o RAG a focar a busca |

### Esforço (effort level)

O nível de esforço conta contra o limite de uso. Use esforço alto só onde compra qualidade:
`[ARQUITETURA]`, otimizador, SAFER, triagem travada. Para pesquisa, aprendizado e revisão,
esforço médio basta.

### Escolha de modelo no plano Pro

Opus tem cota **semanal separada e restrita**. Trate como recurso escasso:

| Use Opus em | Use Sonnet em |
|---|---|
| Decisões de arquitetura irreversíveis | Pesquisa de parâmetros |
| Formulação do otimizador | Chats de aprendizado |
| Implementação do SAFER | Specs de CRUD, UI, integração |
| Triagem que o Sonnet não resolveu | Revisão contra critérios de aceitação |
| Specs de lógica de negócio densa | Redação de mensagens ao produtor |

Acompanhe em **Settings → Usage**: há barras de progresso da sessão de 5 horas e dos
limites semanais, com reset separado para Opus.

---

## 6. Combate à alucinação

O risco maior neste projeto não é código errado — é **parâmetro agronômico inventado**.
Um número plausível e falso passa despercebido e contamina tudo a jusante.

### Defesa em três camadas

1. **`05-PARAMETROS-CULTIVARES.md` é a única fonte de verdade numérica.**
   Nenhum número entra em spec ou código sem constar lá, com fonte e nível de confiança.
2. **`TODO-PARAM` bloqueia.** Parâmetro ausente não vira default silencioso — o sistema
   se recusa a operar com aquela cultivar e exibe mensagem clara.
3. **Faixas de sanidade em runtime.** ETf fora de `[0,05; 1,3]`, BIO fora de
   `[0; 150] kg/ha/dia` → falha alto e loga. Erro silencioso é pior que crash.

### Para o método

- Antes de propor solução nova, consultar `12-REGISTRO-DE-DECISOES-ADR.md`.
  Reabrir decisão fechada exige declarar que está reabrindo e por quê.
- Contratos entre módulos (`06-ARQUITETURA-E-STACK.md` §3) são imutáveis sem ADR.
  Spec que exige mudar contrato é spec errada.

---

## 7. Ciclo completo de uma fatia

```
1. [FATIA-NNN] no Claude
   → lê Knowledge, produz DOIS artefatos:
     · specs/SPEC-NNN-*.md          (vai para o Muse)
     · revisoes/KIT-ACEITE-NNN.md   (só o Claude Code vê)
   → você copia APENAS a spec

2. Muse Code
   → recebe SÓ a spec
   → produz código + testes próprios

3. Claude Code
   → lê CLAUDE.md + o kit de aceite + o código
   → escreve suíte independente em tests/conformance/, roda, relata em revisoes/RELATORIO-*

4. Se falhou:
   [TRIAGEM] no Claude → diagnóstico → spec de correção → volta ao passo 2

5. Se passou:
   [FATIA-NNN] emite handoff e escreve ele mesmo os arquivos 00–12 alterados
   → ação que exige shell (git, uv, lint) vai num revisoes/RUNBOOK-*.md
   → você roda o runbook no Claude Code e abre a próxima fatia
```

**O que o usuário faz, e só ele:** colar a spec no Muse Code, aprovar ADR, rodar o runbook,
e sincronizar o Knowledge. O Arquiteto escreve os documentos; ninguém pede que você redija.

---

## 7.1. Como escrever runbook que não trava sozinho

Dois runbooks foram reprovados por pré-condição que o próprio Arquiteto quebrou, não por erro
do executor. A causa é a mesma nos dois: **o Arquiteto escreve documento entre a emissão do
runbook e a execução dele.** Regras que saem daí, para quem escreve runbook:

- **Nunca** restringir o diff a uma lista fechada de arquivos de `docs/`. O executor não tem
  como saber quais documentos foram escritos depois. Restrição de arquivo vale para `src/` e
  `tests/`, onde o autor é outro.
- Todo runbook começa commitando o que estiver pendente em documentação, num commit próprio.
- Nunca exigir "árvore limpa" sem antes dar ao executor o passo que a limpa.
- Afirmar que um arquivo "já foi escrito" é uma premissa, não um fato: peça conferência de
  **conteúdo** e trate a ausência como parada legítima. Escrita em disco pode não sobreviver;
  aconteceu com `docs/05` em 17/09/2026, e só o testador pegou.
- O Arquiteto confere as próprias escritas relistando o diretório depois de gravar. A
  confirmação da ferramenta de escrita não é prova de que o arquivo ficou no disco.
  **Mecanismo identificado em 17/09/2026:** reaproveitar o mesmo caminho de origem em
  escritas sucessivas fazia a gravação repetir o conteúdo da primeira vez — o arquivo era
  tocado, o tamanho ficava o antigo, e a ferramenta reportava sucesso. Foi o que apagou a
  tabela do CT-135 do `docs/05` e o que engoliu duas edições do `CLAUDE.md`. Contorno:
  **caminho de origem novo e único a cada gravação**, e conferir o tamanho no disco depois.
  Enquanto esse contorno estiver em uso, todo runbook que dependa de um arquivo escrito pelo
  Arquiteto deve checar tamanho ou conteúdo esperado antes de commitar.
- Quando o runbook **é** o commit da documentação pendente, dizer isso na abertura e colocar
  as checagens de conteúdo **antes** do passo de commit, não numa seção que o executor lê
  depois. O passo zero do `CLAUDE.md` commita; se a conferência vier depois, ela conferiu um
  commit em vez de evitá-lo.

## 7.2. Runbook que move arquivo

Reorganizar layout parece trivial e tem um ponto cego provado: a suíte de
`tests/conformance/` lê o código-fonte por caminho literal (para checar estrutura via AST),
então mover o pacote quebra a suíte sem quebrar nenhum import. Todo runbook que move arquivo
inclui, obrigatoriamente:

- um passo explícito de **atualizar caminho hardcoded em `tests/conformance/`**;
- a exigência de que o commit de renomeação seja puro (`R` no status, zero inserções);
- a correção de caminho num commit **separado**, que é do testador e não do Arquiteto.

## 7.3. Verificação de escrita: manifesto, não número solto

**Regra, a partir de 17/09/2026:** runbook **nunca** carrega tamanho esperado em bytes nem
`grep` de conteúdo escrito à mão. Essas checagens existiam por causa da gravação que truncava
em silêncio (REV-006/REV-007), e elas **falharam como remédio** — no REV-008 reprovaram um
disco que estava correto, duas vezes, pelo mesmo motivo:

1. O Arquiteto escreveu o tamanho de `docs/10` no runbook e **depois editou `docs/10` de novo**.
   O número no runbook virou fóssil no instante da edição seguinte.
2. O Arquiteto pediu `grep aguardando_parametro` em `docs/02`, mas escreveu no glossário o
   verbete "Aguardando parâmetro", com acento e espaço. A premissa nunca existiu no arquivo.

Os dois erros têm a mesma raiz: **o runbook afirmava um fato sobre o disco que o Arquiteto
digitou de memória**, e o disco continua mudando depois que o runbook é emitido — o que o
próprio `CLAUDE.md` já diz ser normal e assíncrono.

### O que substitui

O Arquiteto verifica a própria escrita **no momento em que grava**: relê o arquivo de volta do
disco e compara byte a byte com o que pretendia escrever. Isso é estritamente mais forte que
um tamanho no runbook, e não pode envelhecer, porque acontece antes de o runbook existir.

Depois de gravar, o Arquiteto emite um **manifesto** — `revisoes/MANIFESTO-<ID>.sha256`,
gerado a partir dos bytes que estão no disco, nunca digitado à mão. O runbook então carrega
**uma linha**:

```bash
sha256sum -c revisoes/MANIFESTO-<ID>.sha256
```

Propriedades que isso compra:
- Nenhum número no runbook é escrito de memória, então não há premissa falsa a envelhecer.
- Detecta truncamento, edição parcial e corrupção — tudo que o tamanho detectava, e mais.
- Se o Arquiteto editar um documento depois de emitir o manifesto, ele emite manifesto novo.
  Falha de `sha256sum -c` passa a significar **uma coisa só**: o disco não é o que o Arquiteto
  gravou. É sinal verdadeiro, não ruído.

### O que o Claude Code faz quando falha

Igual a antes: **pare e relate**, nomeando os arquivos que o `sha256sum -c` marcou como
`FAILED`. Não commite. Mas agora a falha é informativa — ela aponta o arquivo, não uma
divergência de contagem que pode ser só o Arquiteto tendo editado de novo.

### O que continua valendo

Verificar **presença** de arquivo, classificar a árvore de trabalho (passo zero) e conferir
escopo de `src/`/`tests/` por `git diff --stat` seguem exatamente como estão. O que sai é só
a checagem de conteúdo escrita à mão dentro do runbook.

---

## 8. Erros de método a evitar

1. **Chat gigante que faz tudo.** Cada turno reprocessa o histórico inteiro.
2. **Mandar histórico de conversa para o Muse Code.** Ele se perde e você paga por isso.
3. **Spec vaga.** "Implemente o otimizador" → falha garantida.
4. **Esquecer de atualizar o Knowledge.** Duas semanas depois ninguém sabe o que foi decidido.
5. **Deixar o programador decidir arquitetura.** Ele decide diferente a cada chamada.
6. **Reabrir decisão fechada sem ADR.** Consome cota e produz incoerência.
7. **Usar Opus para tudo.** A cota semanal acaba e você fica sem ele quando precisa.
8. **Pedir para o Claude "revisar o que ele mesmo escreveu".** Verificação é papel separado.
