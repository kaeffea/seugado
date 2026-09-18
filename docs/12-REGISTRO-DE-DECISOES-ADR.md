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

## ADR-016 — Custo espacial no otimizador: distância entra no MVP, grafo de porteiras fica para depois
**Data:** 18/09/2026 · **Status:** aceita

**Contexto.** Toda a formulação do `07` era **espacialmente cega**: `x[l,p,d]` trata os piquetes
como intercambiáveis e nenhuma restrição ou termo de objetivo olha onde eles ficam. O resultado
é o plano que o produtor rejeita antes de ler o motivo — dois lotes atravessando a fazenda em
sentidos opostos quando bastava cada um andar até o vizinho. O dado para evitar isso já existe e
nunca foi usado: `piquete.geometria GEOMETRY(Polygon,4326)` no `06` §5.

**Decisão.** Três partes, uma por estágio do otimizador (ADR-008):

1. **Matriz de distância por centroide.** `dist[p_origem, p_destino]`, em metros, derivada da
   geometria via PostGIS (`ST_Distance` sobre centroides reprojetados para CRS métrico),
   calculada uma vez por fazenda e invalidada quando a geometria de um piquete muda. É **dado
   derivado, não cadastro novo**: fricção adicional para o produtor é zero.
2. **No F-009 (guloso), a distância é critério de desempate, não termo de objetivo.** O guloso
   não tem função objetivo para ponderar. A ordem de escolha do destino passa a ser:
   (a) piquetes aptos (R3, R11), (b) melhor encaixe agronômico — o mais próximo do alvo de
   entrada, (c) **menor `dist` a partir do piquete atual do lote**. O item (c) é o que esta ADR
   acrescenta e custa uma ordenação.
3. **No F-021 (CP-SAT), a distância vira termo da função objetivo:** `− w6 · custo_espacial`,
   com `custo_espacial = Σ_l Σ_d dist[origem(l,d), destino(l,d)] · peso_vivo_total[l]`. A
   multiplicação pelo peso vivo é deliberada: caminhar 3 km com 200 bois não custa o mesmo que
   com 20 bezerros. `w6` é **`HIPOTESE-CALIBRAR`**, a fixar na ADR de pesos da função objetivo
   prevista antes do F-009.

**Por que o centroide já resolve a queixa que originou esta ADR.** A reclamação é sobre rotas
que se cruzam. Num problema de atribuição bipartida com custo euclidiano, **a solução de custo
mínimo nunca tem rotas cruzadas**: se duas atribuições se cruzam, trocar os destinos entre elas
reduz a soma das distâncias pela desigualdade triangular, logo a solução cruzada não era mínima.
A garantia sobrevive à troca de distância euclidiana por distância de caminho mínimo num grafo,
porque a desigualdade triangular vale em ambas. Isto é resultado, não heurística: **minimizar a
distância total elimina o cruzamento absurdo por construção.**

**Alternativas.**

(a) **Grafo de porteiras com caminho mínimo.** Tecnicamente superior e agronomicamente mais
honesto: gado anda por porteira e corredor, não em linha reta, e um trajeto pode atravessar um
piquete em descanso — pisoteio que o centroide não enxerga. **Rejeitada para o MVP** porque
exige cadastrar as conexões entre piquetes, que é fricção de configuração real e não trivial de
desenhar num mapa. Fica registrada como candidata pós-MVP; **condição de entrada:** validação em
fazenda real mostrar que a distância de centroide gera rota inaceitável. Enquanto isso, a
premissa é explícita — ver Consequências.

(b) **Substituir `w3 · numero_de_movimentacoes` por `w_dist · distância`.** Rejeitada: são custos
diferentes e ambos reais. O número de movimentações consome mão de obra (já limitada por R7); a
distância consome tempo de caminhamento e desgasta o animal. Os dois termos coexistem.

(c) **Restrição dura de não-cruzamento.** Desnecessária — o resultado acima mostra que o termo
de distância já a entrega.

**Consequências.**

- Vale para o F-009 em diante. **Não** muda F-001 a F-008; nenhuma fatia concluída é reaberta.
- O `[ARQUITETURA] Schema de eventos` (antes do F-004) passa a ter um item a mais: onde mora a
  matriz de distância — tabela materializada, view PostGIS ou cache em memória do job diário.
- **Premissa explicitada, e é risco.** O modelo de distância assume que um lote consegue ir de
  qualquer piquete a qualquer outro, e que **todo piquete tem água**. Fazenda com bebedouro
  central, corredor único ou piquete sem água quebra a premissa em silêncio. Não vira campo de
  cadastro no MVP; vira pergunta na primeira validação em campo, e é o gatilho da alternativa (a).
- O guloso continua sem *lookahead*. O cenário "vale a pena esperar dois dias pelo piquete
  vizinho?" **não é resolvido no MVP** — ver a nota de horizonte no `07` §5.

---

## ADR-018 — Schema de eventos: append-only no banco, projeção como dobra pura, matriz de distância é projeção
**Data:** 18/09/2026 · **Status:** aceita

**Contexto.** A ADR-007 decidiu event sourcing e o `06` §4 esboçou uma tabela `eventos` de sete
colunas. O esboço não responde o que o F-004 precisa: quem impede que alguém edite o passado, em
que ordem os eventos são relidos quando um fato chega atrasado, onde mora o estado derivado, como
se corrige um evento errado e o que acontece quando o pipeline diário roda duas vezes. A ADR-016
deixou um item explícito para cá: onde mora a matriz de distância.

**Decisão.** Cinco partes.

**1. Tabela `evento`, no singular, append-only garantido pelo banco.**

```sql
CREATE TABLE evento (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fazenda_id         UUID NOT NULL REFERENCES fazenda(id),
  sequencia          BIGINT GENERATED ALWAYS AS IDENTITY,
  tipo               TEXT NOT NULL REFERENCES tipo_evento(tipo),
  origem             TEXT NOT NULL REFERENCES origem_evento(origem),
  ocorrido_em        TIMESTAMPTZ NOT NULL,
  registrado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
  ator               TEXT,          -- id do produtor, ou nome do job que gerou
  corrige_evento_id  UUID REFERENCES evento(id),
  chave_idempotencia TEXT,
  versao_payload     SMALLINT NOT NULL DEFAULT 1,
  payload            JSONB NOT NULL,
  entidade_id        UUID GENERATED ALWAYS AS ((payload->>'entidade_id')::uuid) STORED,
  UNIQUE (fazenda_id, chave_idempotencia)
);

CREATE INDEX ON evento (fazenda_id, ocorrido_em, sequencia);   -- ordem de releitura
CREATE INDEX ON evento (fazenda_id, entidade_id);              -- "eventos do piquete X"
CREATE INDEX ON evento (fazenda_id, tipo, ocorrido_em);

REVOKE UPDATE, DELETE ON evento FROM PUBLIC;  -- e dos papéis da aplicação no Supabase
-- + trigger BEFORE UPDATE OR DELETE que levanta exceção, para fechar o caminho do dono
```

Duas colunas de tempo com papéis distintos: **`ocorrido_em` é a ordem do mundo**, `sequencia` é a
ordem de gravação. A releitura ordena por `(ocorrido_em, sequencia)` — determinística mesmo quando
o produtor confirma hoje um manejo de ontem. `sequencia` também é o marcador de até onde cada
projeção foi derivada.

`tipo` e `origem` são `TEXT` com FK para tabela de domínio, **não** `CREATE TYPE`: acrescentar um
tipo de evento vira `INSERT`, não migração de tipo, e não se cria no banco a comparação entre enums
que o `06` §7 regra 11 proíbe. O `StrEnum` Python continua sendo a fronteira, usando `.value`.

`entidade_id` é coluna gerada a partir do payload e indexada, porque "todos os eventos do piquete X"
é a consulta que auditoria, tela de histórico e debug fazem. **Todo payload carrega `entidade_id`**;
quem valida é um modelo Pydantic por `tipo`, na porta única de escrita (`persistencia/eventos.py`,
função `registrar_evento`). Nenhum outro caminho escreve em `evento`.

**2. Correção é evento novo, nunca `UPDATE`.** `corrige_evento_id` aponta o evento errado. A dobra
faz uma pré-passagem montando o conjunto de ids corrigidos; o evento corrigido é ignorado e a
correção entra **na posição temporal do corrigido**, não na dela própria. Sem isso, corrigir a data
de um manejo reordenaria a história e mudaria estado que não deveria mudar.

**3. `chave_idempotencia` existe porque o pipeline é re-disparável.** O `06` §6 permite
`workflow_dispatch`, e GitHub Actions re-executa job falho. Sem chave, a releitura de satélite do
dia entra duas vezes e a massa é contada em dobro. A chave é determinística por natureza do fato —
para leitura de satélite, `leitura:<piquete_id>:<data>`.

**4. Projeção é dobra pura em `core/projecao.py`; o banco guarda só a entrada e a saída.**

```python
def projetar(eventos: Sequence[Evento]) -> EstadoFazenda: ...
```

Sem I/O, sem banco, testável com lista literal de eventos — a mesma disciplina do `06` §2. As
tabelas derivadas são `estado_piquete`, `estado_lote`, `leitura` e `piquete_distancia`; cada uma
carrega `derivado_ate_sequencia` e `derivado_em`, e a reconstrução é `DELETE` + `INSERT` da fazenda
inteira numa transação. **Tabela derivada nunca recebe escrita de outro lugar.**

Cuidado de nome, porque "projeção" passa a ter dois sentidos no projeto e confundi-los é bug:
`core/projecao.py` dobra **o passado até o presente** (F-004); `planner/estado.py` projeta **o
presente para a frente no tempo** (F-008, o marco ⭐). Módulos separados, propósitos separados.

**Sem snapshot no MVP.** Uma fazenda de 80 piquetes gera da ordem de 35 mil eventos por ano,
dominados por leitura de satélite; dobrar isso em Python leva menos de um segundo. Snapshot é
complexidade que só se paga depois. **Condição de entrada:** releitura completa passar de 2 s
medidos — aí entra tabela `snapshot(fazenda_id, ate_sequencia, estado JSONB)` e a dobra passa a
partir dela.

**5. A matriz de distância da ADR-016 é projeção, não cadastro.** Tabela materializada
`piquete_distancia (fazenda_id, piquete_origem_id, piquete_destino_id, distancia_m)`, preenchida por
`ST_Distance` sobre centroides reprojetados para CRS métrico, reconstruída pela mesma dobra quando
a releitura encontra `piquete_criado` ou `piquete_alterado` com mudança de geometria. 80 piquetes
dão 6.400 linhas — custo irrelevante.

**Alternativas.**
- *View PostGIS para a distância* — recalcula O(n²) a cada rodada do guloso, e o guloso consulta a
  matriz em todo passo de escolha de destino.
- *Cache em memória do job diário* — o job do GitHub Actions é sem estado e morre a cada execução;
  o cache nunca sobreviveria entre a rodada de ingestão e a de planejamento.
- *Tabelas de estado mutáveis, atualizadas a cada evento* — é o estado mutável que a ADR-007
  rejeitou, entrando pela porta dos fundos. Derivada reconstruída não pode divergir da fonte.
- *`CREATE TYPE` para `tipo` e `origem`* — cada tipo novo vira migração, e `ALTER TYPE ... ADD VALUE`
  não roda dentro de transação em todas as versões. FK resolve com `INSERT`.
- *Manter `leitura` como tabela-fonte, escrita direto pela ingestão* — cria um segundo caminho de
  escrita e duas verdades sobre o mesmo fato, já que `leitura_satelite` também é evento.

**Consequências.**
- **F-004 ganha escopo fechado:** migração SQL, `registrar_evento` com validação Pydantic por tipo,
  `core/projecao.py` com a dobra, e as quatro tabelas derivadas. `piquete_distancia` entra aqui
  ainda que só o F-009 a use — é a dobra que a mantém coerente.
- **`leitura` deixa de ser tabela-fonte e vira derivada.** O F-005 passa a gravar evento
  `leitura_satelite`, não linha em `leitura`. Ajuste no `06` §5, sem fatia reaberta.
- `Cultivar` passa a ser **sempre carregada no contexto de uma fazenda**: o override de
  `parametro_fazenda` (ADR-014) é aplicado na camada de carga, que monta o bloco de regime com
  `fonte: 'produtor:<fazenda_id>'` e `confianca: baixa`. A assinatura pura de `resolver_parametros`
  da SPEC-004 fica **intacta** — `core/` continua sem saber o que é fazenda.
- Auditoria fica completa de verdade: `ator`, `origem`, `corrige_evento_id` e as duas colunas de
  tempo respondem "por que recomendou isso em 12/03, e com que dado, sabido quando".
- Custo honesto: toda escrita passa por uma função só, e toda leitura de estado depende de uma
  dobra ter rodado. Fazenda sem projeção derivada não tem estado — o pipeline precisa garantir a
  ordem ingestão → dobra → plano.

---

## ADR-019 — Confiança é o elo mais fraco, não um produto (fecha Q14)
**Data:** 18/09/2026 · **Status:** aceita

**Contexto.** Q14 perguntava duas coisas: se o parâmetro de cultivar precisa de `confianca` própria
além da `fonte`, e se a confiança final da recomendação é composição da confiança da estimativa com
a do parâmetro. A pergunta ficou marcada para cá porque o `01` exige, na definição de pronto, que
toda recomendação carregue confiança, e porque confiança `baixa` é o gatilho do pedido de foto.

**Decisão.** Cinco partes.

1. **O campo já existe.** `ParametrosRegime.confianca` entrou com a ADR-014. Q14 não pede campo
   novo; pede a regra de composição, que é o que falta.
2. **A composição é o mínimo numa escala ordenada, não um produto.** Função pura
   `combinar_confianca(*fatores: Confianca) -> Confianca` em `core/regras.py`, com a ordem
   declarada num `dict` explícito (`baixa` 0 · `media` 1 · `alta` 2). A ordem **nunca** vem de
   comparação de enum — `06` §7 regra 11.
3. **Três fatores no MVP**, e a lista é fechada: confiança da estimativa de forragem
   (`EstimativaForragem.confianca`), confiança do parâmetro de regime resolvido, e confiança do peso
   (`origem_peso: 'produtor'` → alta; `'ua_tabela'` → média, conforme ADR-014).
4. **Toda recomendação carrega `confianca` e `motivo_confianca`** — o nome do elo mais fraco, em
   PT-BR, pronto para a mensagem: *"confiança baixa porque a altura de entrada foi informada por
   você, não por fonte técnica"*. Empate entre fatores no mesmo grau: vence a ordem da lista acima.
5. **`baixa` dispara o pedido de foto de validação** do `01`. É a única consequência automática de
   grau de confiança no MVP.

**Por que não produto.** Multiplicar exige mapear três graus em números — 1,0 / 0,7 / 0,4, ou outra
escolha qualquer — que ninguém tem fonte para justificar. Seria `HIPOTESE-CALIBRAR` criada à toa,
contra a regra 1. O mínimo é monótono, não degrada por acumular fatores bons, e é explicável em uma
frase ao produtor: a recomendação vale o que vale o dado mais fraco que entrou nela.

**Alternativas.**
- *Produto de pesos numéricos* — ver acima; inventa número e ainda faz três fatores "alta" virarem
  confiança menor que um fator "alta", o que é falso.
- *Confiança só da estimativa de satélite* — esconde exatamente o caso que a ADR-014 criou: altura
  dada pelo produtor, em piquete com estimativa ótima. Seria mentir com número bom.
- *Escala numérica contínua (0 a 1) em vez de três graus* — dá falsa precisão e não tem como ser
  calibrada sem dado de campo que o projeto não tem.

**Consequências.**
- `planner/confianca.py` fica reduzido a montar a lista de fatores e chamar o primitivo puro; a
  regra de combinação mora em `core/`, onde é testável sem banco.
- A fatia F-010 (camada de confiança) encolhe e deixa de depender de pesquisa.
- `motivo_confianca` vira campo obrigatório de `Movimentacao` e `Alerta`, tocando o contrato do
  `06` §3 — alteração feita agora, antes de existir implementação que dependa dele.
- Q14 fecha. Nenhuma fatia concluída é reaberta.

---

## ADR-020 — Driver de banco, migrações como SQL puro, e teste de I/O opcional (F-004)
**Data:** 18/09/2026 · **Status:** aceita

**Contexto.** A ADR-018 fechou o schema da tabela `evento` e das derivadas, mas não escolheu como o
Python fala com o Postgres. O `06` §1 lista "PostgreSQL + PostGIS via Supabase" como banco, sem
biblioteca cliente. `pyproject.toml` hoje tem `dependencies = []` — a F-004 é a primeira fatia a
tocar I/O de verdade, e sem decisão aqui o Muse Code escolhe sozinho, o que a regra 7 do `06` §7
proíbe. Falta também dizer como o `pytest` do Antigravity, rodando no WSL sem Postgres à mão, lida
com um teste que precisa de banco de verdade.

**Decisão.** Três partes.

1. **Driver: `psycopg` (v3, síncrono, extra `binary`).** Sem ORM. SQL puro nas funções de
   persistência, coerente com "stack madura, muita documentação" do `06` (topo do arquivo) e com o
   projeto não ter modelado nenhuma camada de ORM em nenhuma ADR anterior. `pydantic` entra junto,
   como dependência própria (já implícita no `06` §1 via FastAPI, agora explícita porque é usada
   antes de existir API).
2. **Migração é arquivo SQL versionado, sem framework.** `db/migrations/0001_evento_e_derivadas.sql`,
   numerado, aplicado manualmente pelo Antigravity (`psql` ou SQL Editor do Supabase). Alembic ou
   equivalente adicionaria ORM implícito e uma segunda fonte de verdade sobre o schema; o projeto
   já tem uma — o próprio SQL.
3. **Teste de I/O é opcional, não bloqueante.** Testes que abrem conexão real leem
   `SEUGADO_TEST_DATABASE_URL` do ambiente; ausente, o teste é pulado (`pytest.mark.skipif`), nunca
   falha. A validação Pydantic por tipo — a parte que a regra 1 do `06` §7 e a regra de pureza mais
   se importam em cobrir sem banco — é testada sempre, sem depender de conexão.

**Alternativas.**
- *`asyncpg` / stack assíncrona* — FastAPI se beneficiaria, mas o pipeline diário (`06` §6) é um
  job síncrono do GitHub Actions; async sem servidor rodando o event loop é complexidade sem uso.
- *SQLAlchemy Core ou ORM* — mais familiar, mas é a stack "elegante mas rara" que o topo do `06`
  pede para evitar num agente de contexto curto; SQL puro com `psycopg` é mais previsível para ele.
- *Exigir Postgres local (Docker) para rodar a suíte* — contradiz "custo R$ 0,00" e "sem servidor";
  o ambiente de teste do Antigravity é o WSL, sem Docker garantido.

**Consequências.**
- `pyproject.toml` ganha duas dependências novas: `psycopg[binary]`, `pydantic`.
- Toda spec de persistência a partir daqui referencia esta ADR em vez de reabrir a escolha.
- O teste de conformidade de I/O real fica pendente até existir um projeto Supabase configurado —
  registrado como item de dívida técnica, não como bloqueio da F-004.

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
