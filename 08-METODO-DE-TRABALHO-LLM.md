# Método de Trabalho com LLM — SeuGado

Como três modelos com papéis distintos constroem um sistema sem se perder e sem queimar cota.

---

## 1. Os três papéis

| Papel | Ferramenta | Recebe | Produz | Nunca faz |
|---|---|---|---|---|
| **Planejador / Arquiteto** | Claude (Opus/Sonnet) no Project | Knowledge + pedido do usuário | Specs, ADRs, análises, handoffs | Escrever código de produção |
| **Programador** | Muse Code (Muse Spark 1.3) | **Só a spec**, autocontida, em inglês | Código + testes | Tomar decisão de arquitetura |
| **Testador** | Claude Code | Spec + código produzido | Testes, relatório de conformidade | Alterar a spec |

### A regra de ouro

> **O programador nunca recebe o histórico de planejamento.**
> Ele recebe a spec, que é autocontida.

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

> Conteúdo em projects é cacheado e **não conta contra seus limites quando reutilizado**.
> Cada vez que você referencia aquele conteúdo, só as porções novas/não-cacheadas contam.

**Consequência:** Project Knowledge pesado é **barato**. Chat longo é **caro**.
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
   → lê Knowledge, produz spec em inglês
   → você copia a spec

2. Muse Code
   → recebe SÓ a spec
   → produz código + testes

3. Claude Code
   → recebe spec + código
   → roda testes, relata conformidade

4. Se falhou:
   [TRIAGEM] no Claude → diagnóstico → spec de correção → volta ao passo 2

5. Se passou:
   [FATIA-NNN] emite handoff
   → você atualiza 11-ESTADO-ATUAL.md no Knowledge
   → abre próxima fatia
```

**Atualizar o Knowledge não é opcional.** É o que mantém o sistema coerente entre chats.
O Claude sempre entrega o **bloco de texto pronto** para colar — você não precisa redigir.

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
