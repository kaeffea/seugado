# Método de Trabalho com LLM — SeuGado

Como três modelos com papéis distintos constroem um sistema sem se perder e sem queimar cota.

---

## 1. Os três papéis

| Papel | Ferramenta | Recebe | Produz | Nunca faz |
|---|---|---|---|---|
| **Planejador / Arquiteto** | Claude (Opus/Sonnet) no Project | `docs/` lido do disco + pedido do usuário | Specs, critérios de aceite, ADRs, pesquisas e atualizações de `docs/` | Escrever código de produção, gerar runbooks ou comandos de terminal |
| **Programador** | Muse Code (Muse Spark 1.3) | **Só a spec**, autocontida, em inglês | Código em `src/` + testes próprios em `tests/core/` | Tomar decisão de arquitetura |
| **Testador / Committer / Supervisor** | Antigravity (Gemini) | Código + spec + critérios | Execução de testes (WSL), correção direta de lints em testes, commits Git, relatório final e mentoria didática | Alterar regras de negócio ou inventar parâmetros |

O Antigravity opera diretamente no ambiente WSL, testa, formata, resolve pequenos apontamentos de linter/tipagem em testes e realiza os commits no repositório.

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

O encerramento é feito em **prosa limpa e humana** (conforme a regra 6 do `00`, sendo **proibido** o uso de blocos de código ou molduras com `🔄 FIM DE CICLO`).
O Arquiteto resume em poucas linhas o que foi feito, o que ficou pendente, indica o próximo chat (com modelo e esforço recomendados) e fornece o prompt exato pronto para colar.

Exemplo de formato:
> *Essa tarefa está concluída e documentada. Para poupar sua cota de contexto, abra um novo chat intitulado `[FATIA-003] Regras de manejo` no modelo Sonnet (esforço médio) e envie a mensagem abaixo para começarmos:*
> `<prompt pronto para colar>`

O handoff escrito **substitui 50 mensagens de histórico**. É a técnica de maior retorno
de todo este documento.

### Continuidade entre chats de mesmo tipo

Quando um `[FATIA-007]` esgota e a fatia não acabou, abra `[FATIA-007] parte 2` e cole o
handoff como primeira mensagem — **com a linha `Leia:`**, porque o chat novo abre sem nenhum
documento carregado.

---

## 5. Economia de tokens — o que realmente funciona

### A economia mudou em 18/09/2026

Até 17/09 a base vivia no **Project Knowledge**, e o raciocínio era: documento denso se paga
porque o Knowledge é cacheado entre mensagens. **Isso acabou.** O Knowledge foi esvaziado e a
base passou a ser lida do disco (`docs/`), a cada chat, por leitura explícita de arquivo.

O que isso muda:

- **Não existe mais amortização por cache.** Todo arquivo lido é custo cheio, toda vez.
- **Densidade deixou de ser virtude automática.** Um documento dá lucro se for *lido inteiro
  quando é lido*; se 80% dele é irrelevante para a tarefa, esses 80% são desperdício puro.
  Foi por isso que o `13-HISTORICO.md` nasceu: separar o que se lê sempre do que quase nunca.
- **A granularidade virou a alavanca principal.** O ganho não vem mais de escrever bem, vem
  de **ler pouco e certo**. Daí o protocolo de leitura por etiqueta no `00`.

O que **não** mudou: chat longo reprocessa o histórico a cada turno, e o histórico só cresce.
Chats magros continuam sendo a regra, e o handoff continua sendo a técnica de maior retorno
deste documento.

### Regras operacionais

| Regra | Por quê |
|---|---|
| Ler só os arquivos que a tabela do `00` manda | Sem cache, arquivo lido à toa é custo puro |
| Todo prompt e handoff carrega a linha `Leia:` | Chat novo abre com zero documento carregado |
| Nunca reimprimir o conteúdo de um arquivo já lido; citar pelo nome | Pagar duas vezes pelo mesmo texto |
| Agrupar perguntas relacionadas numa mensagem | Cada mensagem reprocessa o histórico |
| Pedir e produzir **diffs**, não arquivos inteiros | Reescrever arquivo é o maior desperdício isolado |
| Nunca pedir "confira o que você escreveu" | Custo alto, retorno baixo. Verificação é papel do `[REVISAO]` |
| Revisar o prompt antes de enviar | Prompt vago gera rodada de esclarecimento |

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
1. [FATIA-NNN] no Claude Projects
   → Lê do disco os arquivos da linha "Leia:" e emite a spec autocontida em specs/SPEC-NNN-*.md
   → Indica a ação manual em uma linha (pedir ao Muse Code para implementar)
   → Para e aguarda

2. Muse Code
   → Lê specs/SPEC-NNN-*.md no disco
   → Produz código em src/seugado/ e testes em tests/core/
   → Notifica o usuário

3. Antigravity (Gemini)
   → Roda as 4 ferramentas no WSL: ruff check, ruff format, mypy, pytest
   → Corrige diretamente qualquer apontamento cosmético (lint, formatação, # type: ignore em testes)
   → Executa/atualiza a suíte de conformidade em tests/conformance/
   → Realiza o commit e push direto no Git: git commit -m "F-NNN: <título>"
   → Gera UM único relatório final conciso de conformidade em revisoes/RELATORIO-<NNN>.md

4. Fechamento no Claude Projects
   → Lê o relatório final
   → Registra a conclusão em docs/11-ESTADO-ATUAL.md (via edição cirúrgica)
   → Se houver débitos técnicos secundários, anota para fatias futuras
   → Encerra o ciclo e indica o próximo chat em prosa limpa
```

### 7.1. Edição cirúrgica de documentos
Ao atualizar a base de conhecimento (`docs/`), modifique apenas as seções ou tabelas necessárias. Nunca reescreva arquivos inteiros de 500 linhas para alterar poucas linhas de texto — isso poupa tokens de saída e evita problemas de truncamento de disco.

### 7.2. Fim de burocracias descartadas
- **Runbooks e Manifestos SHA-256 estão abolidos:** Toda operação de terminal e integridade de arquivos é auditada pelo Antigravity diretamente via Git.
- **Zero micro-specs para correções de lint:** Apontamentos simples de linter ou tipagem estrita em arquivos de teste são resolvidos diretamente pelo testador (Antigravity), sem necessidade de rodadas extras de spec para o Muse.

---

## 8. Erros de método a evitar

1. **Chat gigante que faz tudo.** Cada turno reprocessa o histórico inteiro.
2. **Mandar histórico de conversa para o Muse Code.** Ele se perde e você paga por isso.
3. **Spec vaga.** "Implemente o otimizador" → falha garantida.
4. **Esquecer de atualizar o `docs/` no disco.** Duas semanas depois ninguém sabe o que foi decidido.
   Não há mais cópia no Knowledge para salvar o esquecimento: o disco é a única fonte.
5. **Deixar o programador decidir arquitetura.** Ele decide diferente a cada chamada.
6. **Reabrir decisão fechada sem ADR.** Consome cota e produz incoerência.
7. **Usar Opus para tudo.** A cota semanal acaba e você fica sem ele quando precisa.
8. **Pedir para o Claude "revisar o que ele mesmo escreveu".** Verificação é papel separado.
