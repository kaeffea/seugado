# Registro de Decisões — ADR

Uma decisão fechada **não se reabre sem declarar que está reabrindo e por quê.**
Formato: contexto, decisão, alternativas, consequências. Curto de propósito.

Status: `aceita` · `substituída por ADR-NNN` · `revogada`

---

## ADR-001 — Escopo: especialista em manejo de pasto, não ERP pecuário
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** Pastu e iRancho são ERPs pecuários completos com módulo de pasto. Tentar
competir em amplitude com empresas que têm anos de mercado e capital é perder por definição.

**Decisão.** O SeuGado resolve **um** problema: a decisão diária de rotação de pastagem.
Nada de cadastro individual de animal, pesagem, vacinação, financeiro, rastreabilidade.

**Alternativas.** (a) ERP completo — perde-se em amplitude contra quem tem 10 anos de
mercado. (b) Só visualização de satélite — é o que a Pastu já faz, sem diferencial.

**Consequências.** Escopo pequeno e defensável. Risco: o mercado pode preferir
"tudo-em-um". Mitigação: integrar com ERPs existentes no futuro, em vez de substituí-los.

---

## ADR-002 — HLS como fonte óptica primária
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** Landsat 8 tem 16 dias de revisita; Sentinel-2 tem ~5 dias e 10 m, mas nenhum
tem banda termal (que se descobriu não ser necessária: o SAFER deriva T₀ pelo método
residual). Misturar as duas fontes na mão exige harmonização radiométrica.

**Decisão.** Usar **HLS (Harmonized Landsat Sentinel-2)** como fonte primária.

**Alternativas.** (a) Landsat puro — revisita insuficiente, risco do erro de 50%
documentado. (b) Sentinel-2 puro — 10 m é melhor, mas menos revisita e sem harmonização
com Landsat. (c) Fusão manual — trabalho já resolvido pela NASA.

**Consequências.** Resolução de 30 m limita piquetes pequenos (rotacionado intensivo de
0,5–3 ha). Mitigado por F-019 (Sentinel-2 a 10 m como refinamento) e pelo buffer negativo
com contagem de pixels válidos alimentando a camada de confiança.

---

## ADR-003 — SAR para gap-filling, não como estimador primário
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** Sentinel-1 atravessa nuvem, mas não produz refletância óptica e portanto não
alimenta o SAFER. Como estimador direto de biomassa é mediano (R² = 0,71 em VH, e só com
MDE de 1 m; degrada com MDE de 30/90 m).

**Decisão.** SAR serve para: (1) prever NDVI em dias nublados via ML; (2) umidade do solo
como auxiliar; (3) corroboração para a camada de confiança; (4) detecção de evento de pastejo.
**Nunca** como fonte primária de massa.

**Alternativas.** (a) SAR como segundo estimador independente e média dos dois — combina
um modelo bom com um mediano, piorando o resultado. (b) Ignorar SAR — deixa a cegueira
das águas sem solução, que é o principal gap dos concorrentes.

**Consequências.** Arquitetura mais limpa: um modelo, duas fontes de NDVI. O gap-filling
exige treino com dados locais (a relação NDVI–SAR não é genérica).

---

## ADR-004 — Fricção assimétrica, não fricção zero
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** "Fricção zero" era a bandeira original, mas é insustentável: o sistema precisa
saber piquetes, lotes e confirmações. Além disso, a iRancho já resolveu a fricção de
registro por voz (−85% no tempo), melhor do que "eliminar o formulário".

**Decisão.** **Configuração pesada uma vez, confirmações triviais para sempre.**
Nada de dado por animal; nada de evento digitado no dia a dia.

**Alternativas.** (a) Fricção zero real — impossível. (b) Aceitar fricção de ERP — perde
o diferencial inteiro.

**Consequências.** Posicionamento honesto e defensável. Exige investimento em UX de
onboarding (desenho de piquetes é a única tarefa chata) e em reduzir confirmações
(confirmação por omissão, detecção por SAR, batch semanal).

---

## ADR-005 — Qualidade nutricional por proxy de idade, não por química
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** PB, FDN e digestibilidade importam, mas dentro de uma mesma cultivar variam
mais com a idade do rebrote do que com a espécie — e a regra dos 95% de IL já protege isso.

**Decisão.** Usar idade do rebrote (dias ou graus-dia desde a saída) como proxy,
exposta como indicador qualitativo: `ótima` / `declinando` / `passado do ponto`.
Cada cultivar carrega `qualidade_base` (alta/média/baixa) sem modelar química.

**Alternativas.** (a) Modelar química completa — módulo inteiro, exige dados que não temos.
(b) Ignorar qualidade — perde a mensagem central de que "mais alto não é melhor".

**Consequências.** ~80% do valor com ~10% da complexidade. Balanço nutricional e
suplementação ficam como roadmap pós-MVP (e conectam com o ganho de 30% em suplementação
que a Pastu alega).

---

## ADR-006 — Telegram antes de WhatsApp
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** WhatsApp é onde o produtor está, mas a Cloud API exige CNPJ, Business Manager
verificado e templates aprovados; e a partir de 01/10/2026 mensagens de serviço passam a
ser cobradas. Restrição de custo zero.

**Decisão.** Telegram Bot API como canal do MVP, atrás de uma interface `Channel` abstrata
desde a primeira linha de código.

**Alternativas.** (a) WhatsApp direto — burocracia e custo antes de haver produto.
(b) E-mail — o produtor não lê. (c) Só web — perde o argumento de "chega no bolso dele".

**Consequências.** A demo roda em canal real e gratuito. Trocar para WhatsApp é implementar
um adaptador, sem tocar na lógica de decisão. Perde-se o apelo de marketing do WhatsApp
até haver orçamento.

---

## ADR-007 — Event sourcing
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** O usuário identificou que alterar lote força recálculo do manejo inteiro.
Estado mutável torna recálculo e auditoria frágeis.

**Decisão.** Todo acontecimento vira evento imutável; o estado atual é derivado.

**Alternativas.** (a) Estado mutável com histórico em log — mais simples, mas recálculo
vira gambiarra e a auditoria fica incompleta.

**Consequências.** Custo inicial maior de arquitetura. Ganhos: recálculo trivial, auditoria
completa ("por que recomendou isso em 12/03?"), debug reprodutível do otimizador, e o dado
mais valioso do sistema — `manejo_divergente`, onde o produtor discordou da máquina.

---

## ADR-008 — Otimizador em três estágios, guloso primeiro
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** CP-SAT é o alvo certo, mas implementá-lo antes de existir estado projetado
confiável é otimizar ruído — e trava o projeto num ponto sem produto.

**Decisão.** Guloso (F-009) → busca local (F-020) → CP-SAT com horizonte rolante (F-021).
Cada estágio é entregável e serve de baseline para o seguinte.

**Alternativas.** (a) CP-SAT direto — alto risco, sem baseline de comparação.
(b) Só guloso — desperdiça a vantagem competitiva do time de Computação.

**Consequências.** O produto funciona cedo. A sofisticação vira melhoria mensurável
contra baseline, o que também dá material para o relatório acadêmico.

---

## ADR-009 — Não modelar módulo de pastejo no MVP
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** Na prática, fazendas organizam piquetes em módulos, e cada lote rotaciona
dentro do seu módulo.

**Decisão.** O otimizador trabalha sobre o conjunto **todo** de piquetes, sem agrupar em módulos.

**Alternativas.** (a) Modelar módulos — mais fiel à prática, mas adiciona restrição e
cadastro sem ganho no MVP.

**Consequências.** O otimizador tem mais liberdade (pode achar soluções melhores que a
organização atual da fazenda). Risco: propor movimentações que o produtor considera
"fora do módulo dele". Mitigação: se aparecer em validação, vira restrição opcional.

---

## ADR-010 — Eficiência de pastejo e taxa de utilização são grandezas distintas
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** `05` registrava `eficiencia_pastejo_default = 0,44` derivado de 1.760 ÷ 4.000
(massa removida sobre massa total pré-pastejo), enquanto `03` §6.2 aplica o fator sobre
(massa_atual − massa_residuo). São bases diferentes. Aplicar 0,44 na fórmula do §6.2 faz o
caso canônico render 1,76 dia em vez de 4 — o fator é contado duas vezes.

**Decisão.** Duas grandezas, dois nomes, uma base cada:
- `eficiencia_pastejo` — **entrada**, física. Fração da massa **acima do resíduo** que vira
  ingestão. O complemento desaparece sem ser ingerido (pisoteio, fezes, rejeição,
  senescência durante a ocupação). Valor: **TODO-PARAM**. A faixa 0,40–0,50 da literatura
  mede taxa de utilização, não isto, e portanto não serve como default.
- `taxa_utilizacao` — **saída**, descritiva. massa_removida ÷ massa_pré_pastejo. Caso
  canônico: 0,44. Nunca entra em cálculo, só em relatório.

A fórmula do `03` §6.2 mantém a forma atual. Leitura equivalente e mais clara:
`taxa_desaparecimento_dia = consumo_lote_dia ÷ eficiencia_pastejo`.

O caso canônico valida `consumo_individual` (11,62), `consumo_pct_pv` (2,42%) e
`taxa_utilizacao` (0,44). **Não valida `eficiencia_pastejo`**: a fonte atribui todo o
desaparecimento à ingestão. No teste de regressão, `eficiencia_pastejo = 1.0` e
`taxa_acumulo = 0.0` são fixados explicitamente para neutralizar os dois fatores.

**Escopo do bloqueio por TODO-PARAM.** `TODO-PARAM` bloqueia **default de produção** e
operação com a cultivar afetada. Não bloqueia função pura que recebe o parâmetro como
argumento. F-002 é implementável; o que não é permitido é constante default inventada.

**Alternativas.** (a) Usar 0,44 como entrada — caso canônico falha por fator 0,44.
(b) Remover o fator — reintroduz a superestimativa de >2x que `03` §11 item 2 proíbe.
(c) Renomear para `eficiencia_colheita` — mais claro contra a literatura, mas altera nome
no contrato `06` §3; rejeitado por churn, mitigado por nota no `02`.

**Consequências.** F-002 ganha um TODO-PARAM novo, sem ficar mais bloqueado do que já
estava (B1). Novo item de `[PESQUISA]`. `taxa_utilizacao` fica disponível desde o dia 1
porque é derivada. Risco: alguém ler um paper onde "eficiência de pastejo" significa taxa
de utilização e reimportar a confusão — daí a nota no `02`.

---

## ADR-011 — Spec e kit de aceite são artefatos separados
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** A spec entregava o arquivo de teste completo, o Muse o copiava literalmente e
o testador precisava escrever outra suíte. Prova empírica: 7 defeitos plantados um a um em
cópias de `models.py` (import proibido, `__post_init__`, `__hash__` próprio, enum com membro
extra, enum com valor errado, classe não congelada, `__all__`, função extra). A suíte copiada
deixou passar quase todos; a suíte independente pegou todos. **Todos os defeitos eram
estruturais** — nenhum era de valor numérico.

**Decisão.** O planejador produz dois artefatos por fatia:
- **Spec (Muse Code).** Requisitos, assinaturas exatas, exemplos resolvidos **com números**,
  regras de validação, critérios de aceite, `Out of scope`, estilo.
  **Nunca um arquivo de teste pronto.** O Muse escreve os próprios testes.
- **Kit de aceite (Claude Code).** Vive em `revisoes/KIT-ACEITE-<NNN>.md` e **nunca** é
  colado no Muse. Contém: (a) todas as checagens estruturais; (b) o caso canônico com
  tolerância; (c) **no mínimo um caso que a spec não mostra**.

Números permanecem na spec porque modelo de contexto curto sem exemplo resolvido erra a
fórmula e gera rodada de TRIAGEM — mais caro que o risco de overfitting. O que sai da spec
é o *arquivo de teste* e as *checagens estruturais*, que é onde a falha foi medida.

**Alternativas.** (a) Manter como está — provado insuficiente. (b) Retirar todo número da
spec — maximiza independência e maximiza retrabalho com Muse Spark 1.3.

**Consequências.** O testador deixa de duplicar trabalho: ele executa o kit. O formato do
relatório de conformidade e as checagens estruturais vivem em `CLAUDE.md`, na raiz do
repositório, que é o que o Claude Code lê antes de agir. Risco: kit esquecido → fatia sem
verificação estrutural; mitigado pelo checklist de emissão de spec no `09`.

---

## ADR-012 — Fundação do repositório: git, pyproject, ruff, mypy
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** Sem git não há diff, e o critério "o agente não tocou em arquivos fora da
lista" é inverificável. Sem `pyproject.toml`, "nenhuma dependência nova" é inverificável e
o pytest não está declarado. O ambiente (`.venv` criada por `uv` no WSL Ubuntu; o Windows
não tem Python) não estava escrito em lugar nenhum.

**Decisão.** `git init`, um commit por fatia, mensagem `F-NNN: <título>`; o diff do commit é
o que o testador revisa. `pyproject.toml` com Python 3.12, grupo `dev` = pytest + ruff +
mypy, e configuração do pytest. ruff para lint e formatação, mypy em `strict = true`.
Markdown fora do escopo do ruff. `uv.lock` versionado: isto é aplicação, não biblioteca, e
o pipeline diário roda em CI — build reproduzível depende do lock no repositório.
**Isto não é fatia do Muse Code** — não há lógica de domínio; os arquivos são criados
direto no repositório pelo Arquiteto, e os comandos rodam via runbook no Claude Code.

ruff e mypy são dependências novas, o que exige esta ADR por `06` §7 regra 7. São
**exclusivamente de desenvolvimento**: a restrição sobre dependência de produção segue intacta.

**Alternativas.** (a) Fatia F-000 com spec para o Muse — custo de round-trip sem ganho.
(b) Seguir sem git — inverificabilidade permanente. (c) pyright em vez de mypy —
equivalente em rigor, mas exige Node; mypy é Python puro e casa com o critério de stack
madura do `06`.

**Consequências.** Os critérios de aceite sobre dependência e sobre arquivos tocados passam
a ser verificáveis. Primeira medição (RELATÓRIO-REV-001): 5 apontamentos de ruff e 18 de
mypy, **todos em `tests/`**, nenhum em `seugado/`. O `mypy` estrito **acusa**
`Confianca.ALTA == QualidadeBase.ALTA` como `comparison-overlap` — a defesa estática existe,
mas a igualdade continua verdadeira em runtime, então a convenção do `06` §7 regra 11
permanece necessária.

---

## ADR-013 — Layout do repositório: `docs/` e src-layout
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** A raiz acumulava 14 arquivos `.md` misturados com configuração e código, e o
usuário relatou que não conseguia se orientar. O pacote ficava em `seugado/seugado/` — que é
o padrão histórico do Python, não um erro, mas desconfortável de ler e sujeito a um bug
conhecido: um processo iniciado na raiz importa a pasta local em vez do pacote instalado,
e a diferença só aparece quando já há build ou empacotamento.

**Decisão.**
- Base de conhecimento (`00`–`12`) vai para `docs/`. Os nomes numerados não mudam, então
  continuar dizendo "o `05`" segue funcionando.
- Pacote vai para `src/seugado/` (**src-layout**). `pytest` resolve com `pythonpath = ["src"]`
  e `mypy` com `mypy_path = "src"`.
- Na raiz ficam apenas dois pontos de entrada — `README.md` (humano) e `CLAUDE.md` (agente) —
  mais `pyproject.toml`, `uv.lock` e `.gitignore`.
- `revisoes/` **não** é renomeada nem subdividida, apesar de guardar quatro tipos de arquivo
  (`REV-`, `KIT-ACEITE-`, `RUNBOOK-`, `RELATORIO-`). O nome já está referenciado em
  `CLAUDE.md`, `08`, `09`, nas ADRs 011 e 012 e em dois relatórios; o prefixo já agrupa os
  arquivos na listagem alfabética. Renomear custaria uma varredura de referências para
  comprar estética.
- A pasta mãe **não** é renomeada: quebraria a pasta conectada e o remote do GitHub.

**Alternativas.** (a) Manter tudo na raiz — o usuário não se orienta. (b) Renomear a pasta
mãe para `seugado-app` — churn sem ganho. (c) Flat-layout mantendo `seugado/` na raiz —
elimina `docs/` como ganho mas preserva o problema de import.

**Consequências.** Movimentação feita com `git mv`, então `git log --follow` preserva o
histórico. Nenhuma linha de código muda. Caminho de import (`from seugado.core...`)
**não muda** — só a localização física. Risco: script ou documento com caminho absoluto
antigo; o RUNBOOK-REV-003 verifica as quatro ferramentas depois da mudança.

---

## ADR-014 — Método de pastejo: parâmetro por regime, célula vazia perguntada ao produtor, contínuo em laço próprio
**Data:** 17/09/2026 · **Status:** aceita

**Contexto.** O CT-135 documenta braquiária só em pastejo contínuo e colonião só em
rotacionado, mas a `[PESQUISA] Regime de pastejo na prática brasileira` (17/09/2026) mostrou
que a mesma cultivar roda nos dois regimes, com altura própria em cada um: **a ambiguidade é
a norma, não a exceção**. A altura deixou de ser propriedade da cultivar e passou a ser
propriedade do par **cultivar × regime** — uma matriz esparsa, com a maioria das células ainda
vazia (`05`, Tabelas A, A2, B e B2). Dois pontos já estavam acordados e entram aqui como
premissa, não como opção: `metodo_pastejo` é campo do **piquete** (fazendas mistas existem), e
o produtor alterar a composição de um lote é **cadastro** (`lote_alterado`), não ERP.

**Decisão.** Cinco partes.

**1. Schema: parâmetro por regime, e a recusa passa a ter dono explícito (absorve DT3).**
`Cultivar` perde os campos planos de altura e passa a carregar uma tupla de blocos, um por
regime em que a cultivar tem fonte:

```python
class MetodoPastejo(StrEnum):          # mesmo valor de piquete.metodo_pastejo
    CONTINUO = "continuo"
    ROTACIONADO = "rotacionado"

@dataclass(frozen=True, slots=True)
class ParametrosRegime:
    metodo: MetodoPastejo
    altura_entrada_cm: float | None    # rotacionado: entrada do giro
    altura_saida_cm: float | None      # rotacionado: resíduo de saída
    altura_maxima_cm: float | None     # contínuo: gatilho de aumentar lotação
    altura_minima_cm: float | None     # contínuo: gatilho de reduzir lotação
    confianca: Confianca
    fonte: str

@dataclass(frozen=True, slots=True)
class Cultivar:
    ...
    parametros_por_regime: tuple[ParametrosRegime, ...]
```

Tupla, e não `dict`, porque `Cultivar` é `frozen/slots`: `frozen` impede rebind, não mutação —
um `dict` dentro dela seria mutável na prática e tornaria a entidade não hasheável, contra a
regra 12 do `06` §7. **A célula vazia é a ausência da entrada**, não um bloco cheio de `None`.

A recusa por `TODO-PARAM` (DT3) **não** vai para `__post_init__`. Carregar cultivar com buraco
tem de ser legal — senão o catálogo não pode nem ser lido, e a tela de cadastro não consegue
dizer ao produtor o que falta. A recusa vira função pura, **porta única de acesso ao
parâmetro**, em `core/regras.py`:

```python
@dataclass(frozen=True, slots=True)
class ResolucaoParametros:
    parametros: ParametrosRegime | None
    faltantes: tuple[str, ...]     # nomes do que falta; vazia quando resolveu

def resolver_parametros(cultivar: Cultivar, metodo: MetodoPastejo) -> ResolucaoParametros: ...
```

Ninguém obtém o parâmetro sem receber `faltantes` no mesmo retorno. Quem barra é o `planner/`:
piquete com `faltantes` não entra em prescrição. `core/forragem.py` continua recebendo número
por argumento, como o escopo de bloqueio da ADR-010 já permite.

**2. Célula vazia: perguntar ao produtor, com o piquete parado até a resposta.**
Cair numa célula vazia não é hipótese remota — Xaraés, *B. decumbens*, Massai, Zuri e Tamani
estão sem fonte no regime que falta. Enquanto não há resposta, o piquete fica em
`aguardando_parametro`: **entra** na projeção de estado, **não entra** em prescrição, e aparece
como pendência de cadastro. O cadastro pergunta ao produtor a altura que ele usa, em cm, e a
resposta vira evento `parametro_alterado` com `origem: 'produtor'` e `confianca: baixa`, que a
camada de confiança propaga até a mensagem.

**A guarda que faz isso caber na regra 1:** altura dada pelo produtor é parâmetro **daquela
fazenda**. Não entra no `05`, não vira default de catálogo, não se propaga para outra fazenda
com a mesma cultivar. A regra 1 proíbe número sem fonte rastreável; aqui a fonte é o produtor,
e fica registrada no evento junto com o número.

**3. Contínuo ganha laço próprio, mais lento — e continua visível ao otimizador.**
Piquete contínuo sai da variável de atribuição `x[l,p,d]` do `07` §2 (seu lote está fixado) e
**não** ganha variável inteira de número de animais no problema diário. Ele recebe avaliação
**semanal**, disparada por gatilho de altura (`altura_maxima_cm` / `altura_minima_cm` do bloco
de regime), produzindo recomendação de **ajuste de lotação**, não de movimentação.

Semanal, e não mensal: a P2 mostrou reavaliação da ordem de um mês **quando o produtor não
monitora altura** — e o SeuGado é exatamente o monitoramento que falta. O `01` já promete
plano de 7 dias; a cadência do contínuo se encaixa nessa mesma batida sem criar uma terceira.

O piquete contínuo **continua na projeção de estado** e continua candidato na hierarquia do
`07` §4. Isto corrige de propósito o erro (b) registrado no `11` — esconder o contínuo do
otimizador o piora, porque ele é válvula de escape acima da fusão de lotes. O que sai do
problema diário é só a variável de atribuição.

**4. `peso_medio_kg` é canônico; UA é preenchimento e exibição.**
A cadeia do `03` §6.1 não muda: consumo é Σ(`n_animais` × `peso_medio_kg` × `pct_consumo`).
Quando o produtor não sabe o peso médio de uma categoria, o sistema **deriva**
`peso_medio_kg = coeficiente_UA(categoria) × 450`, grava com `origem: 'ua_tabela'` e
`confianca: media`. UA nunca vira fórmula paralela de consumo — segue como unidade de exibição
(`UA/ha`) e de normalização de lote, como o `03` §6.5 já dizia.

Risco nomeado: o coeficiente de bezerro (0,25 UA → 112,5 kg) fica **abaixo** do peso de desmama
achado na pesquisa (180–210 kg, confiança baixa). Subestimar peso subestima consumo, o que
superestima `dias_ocupacao` — erro na direção do super-pastejo, que é o caro (`07` §2, `w4=5,0`).
Por isso o valor derivado carrega confiança média e não encerra o assunto: **B5 deixa de
bloquear F-002 e vira item de precisão**, não de fundação.

**5. DT11 — "categoria compatível", definida pela escala de UA.**
`compativel[a,b] = 1 ⟺ |ordem(a) − ordem(b)| ≤ 1`, onde `ordem` é a posição da categoria na
escala de UA do `05` (bezerro 0,25 · novilho 0,50–0,75 · adulto 1,00 · touro 1,25). Dois lotes
só são fundíveis se **todo** par de categorias entre eles for compatível. Com as três
categorias do MVP isso produz exatamente a regra que o `03` §9.4 já enunciava em prosa:
bezerro com novilho pode, novilho com adulto pode, **bezerro com adulto não**.

O limiar `≤ 1` é escolha nossa, não dado empírico: **`HIPOTESE-CALIBRAR`**, a calibrar na ADR
de fusão de lotes prevista antes do F-022.

**Alternativas.**
- *Campos planos com sufixo de regime* (`altura_entrada_rotacionado_cm`, …) — dobra o número de
  campos, metade sempre `None`, e acrescentar um regime vira alteração de dataclass.
- *Recusa em `__post_init__` da `Cultivar`* — torna ilegal carregar o catálogo incompleto, que
  é o estado real do projeto hoje, e esconde de quem monta a tela exatamente o que falta.
- *Default conservador na célula vazia* — é valor plausível inventado, proibido pela regra 1.
  *Recusar o piquete e parar ali*, sem perguntar, é honesto mas trava o produto numa cultivar
  comum; virou o estado intermediário (`aguardando_parametro`), não o destino.
- *Contínuo no mesmo laço diário* — exige a variável inteira `n[l,p,d]` no problema diário, o
  que muda a classe do modelo do `07` §2 para comprar uma cadência que a prática não usa.
- *UA como fonte canônica de consumo* — mais grossa que o peso real e obrigaria a reescrever a
  `03` §6.1 para ganhar robustez que o fallback já entrega.

**Consequências.**
- **F-003 destrava.** Em troca, **F-001 é reaberta**: `models.py`, intocada desde a aprovação,
  ganha `MetodoPastejo`, `ParametrosRegime` e o campo novo em `Cultivar`. É o primeiro arquivo
  aprovado a ser reaberto, e exige spec própria antes do F-002.
- Pastejo contínuo **deixa de ser "fora do escopo do MVP"** como conceito: entra no modelo de
  dados, na projeção de estado e no alerta. A **prescrição** de lotação contínua é a fatia nova
  **F-009B**, posicionada depois do F-015 — ou seja, pós-MVP. Consequência honesta e registrada
  como risco de produto: uma fazenda 100% contínua, no MVP, recebe estado e alerta ("acima da
  altura máxima, considere aumentar a lotação"), mas **não** recebe número de animais.
- A fila de parâmetro do `05` ganha forma definida — célula por cultivar × regime. A
  `[PESQUISA] Mercado e pecuária de Alagoas` passa a podar o eixo *cultivar* sabendo quantas
  células buscar para cada uma.
- **DT3 e DT11 fechados. B5 rebaixado** de bloqueio a refinamento. A
  `[ARQUITETURA] REV-001 parte 2` encolhe para DT2, DT4 e DT9.
- Aparece uma classe nova de parâmetro — **override por fazenda** — que F-004 (evento) e F-014
  (cadastro) têm de carregar, e que não existia antes desta ADR. É o preço da parte 2.

---

## Template para novas ADRs

```markdown
## ADR-NNN — <título curto e decisivo>
**Data:** DD/MM/AAAA · **Status:** aceita

**Contexto.** <o problema, em 2-3 frases>
**Decisão.** <o que foi decidido, imperativo>
**Alternativas.** <o que foi descartado e por quê>
**Consequências.** <o que melhora, o que piora, o que fica pendente>
```
