# Glossário — SeuGado

Vocabulário canônico do projeto. **Use exatamente estes termos** em código, specs, banco e UI.
Sinônimos listados existem na literatura mas são proibidos internamente, para evitar que o
mesmo conceito ganhe três nomes no código.

---

## Domínio agropecuário

### Piquete
Subdivisão cercada da pastagem, onde um lote pasteja por um período. É a **unidade espacial**
do sistema. Tem geometria (polígono georreferenciado), área em hectares e uma cultivar plantada.
- Proibido internamente: *talhão* (termo de lavoura), *pasto* (ambíguo), *paddock*.

### Módulo
Conjunto de piquetes que um mesmo lote rotaciona. Um módulo tem N piquetes: enquanto o lote
está em 1, os outros N−1 descansam.
- No MVP não modelamos módulo explicitamente — o otimizador trabalha sobre o conjunto todo
  de piquetes. Módulo é conceito de roadmap.

### Lote
Grupo de animais manejado como uma unidade. **Nunca movemos animais individuais, só lotes.**
Um lote tem composição por categoria (ex.: 3 bezerros, 10 novilhos, 20 adultos).
- Proibido: *rebanho* (é o conjunto de todos os lotes), *mob*, *grupo*.

### Categoria animal
Faixa que determina peso vivo médio e consumo. No MVP: `bezerro`, `novilho`, `adulto`.
Simplificação deliberada — o que importa para o cálculo é o **peso vivo total do lote**,
não a identidade dos animais.
As categorias são **ordenadas** pela escala de UA do `05` (bezerro 0,25 · novilho 0,50–0,75 ·
adulto 1,00 · touro 1,25). Essa ordem é o que define compatibilidade de fusão: duas categorias
são compatíveis quando estão a no máximo um degrau de distância (ADR-014, DT11).

### Cultivar
Variedade específica de capim. Ex.: Mombaça, Marandu, Tanzânia, Xaraés, Massai, Zuri, Tamani.
Cada cultivar tem seus próprios parâmetros de manejo (alturas, densidade, descanso).
- Atenção: "espécie" é o nível acima (*Panicum maximum*, *Brachiaria brizantha*).
  Usamos **cultivar** porque os parâmetros de manejo variam dentro da mesma espécie.

### Matéria seca (MS)
O que sobra do capim depois de remover toda a água. É **a moeda universal** do manejo de pasto.
Capim verde é majoritariamente água, e o teor de água varia com chuva, hora do dia, estação
e espécie — então peso verde não serve para comparar nada. Todos os cálculos de
disponibilidade e lotação são feitos em base de MS.
- Unidade padrão do projeto: **kg MS/ha**.

### Massa de forragem
Quantidade de MS disponível por área num dado momento. **É o estoque.** Unidade: `kg MS/ha`.
- Proibido: *biomassa* (reservado para a saída bruta do modelo SAFER), *disponibilidade*.

### Taxa de acúmulo
Velocidade de crescimento do capim. **É o fluxo.** Unidade: `kg MS/ha/dia`.
É isto que o SAFER produz diretamente; a massa de forragem é a integral disso no tempo.

### Altura de entrada
Altura do dossel em que o lote deve **entrar** no piquete. Corresponde ao ponto em que a
planta intercepta ~95% da luz incidente (ver *Interceptação luminosa*).
- Sinônimo aceito em UI: *ponto de entrada*. Em código: `altura_entrada_cm`.

### Altura de saída (resíduo)
Altura em que o lote deve **sair**, deixando folha suficiente para rebrota rápida.
Sair abaixo disso obriga a planta a usar reserva de raiz e degrada o pasto no longo prazo.
- Em código: `altura_saida_cm`. **`residuo_cm` é proibido** — nome canônico é único.

### Interceptação luminosa (IL)
Percentual da luz incidente capturado pelo dossel. A **IL de 95%** é o critério fisiológico
de entrada: passado esse ponto, a planta muda do estágio vegetativo para o reprodutivo,
alonga hastes e perde valor nutritivo. Medir IL exige fotômetro caro, por isso a literatura
usa **altura como substituto consistente da IL**.

### Período de descanso
Dias entre a saída de um lote e a entrada do próximo no mesmo piquete. Faixa prática usual:
21 a 45 dias. **No SeuGado o descanso é variável, governado pelo crescimento observado**,
não por calendário fixo — é um dos diferenciais do produto.

### Período de ocupação
Dias que um lote permanece num piquete. Faixa usual em rotacionado: 1 a 3 dias.
Calculado pelo sistema, não configurado pelo usuário.

### Eficiência de pastejo
Fração da massa de forragem **acima da altura de saída** que o animal efetivamente ingere.
O restante desaparece sem virar alimento: pisoteio, sujidade por fezes, rejeição seletiva e
senescência durante a ocupação. **É entrada de cálculo.**
Ignorar esse fator superestima a capacidade do piquete em mais que o dobro.
- Em código: `eficiencia_pastejo` (decimal). Valor: `TODO-PARAM` (ver ADR-010).
- ⚠️ Em boa parte da literatura "eficiência de pastejo" designa a **taxa de utilização**
  (base diferente). No SeuGado os dois termos são distintos e não se substituem.

### Taxa de utilização
Massa removida do piquete ÷ massa total pré-pastejo. **É saída descritiva**, usada em
relatório e no caso de regressão; nunca entra no cálculo de dias de ocupação.
Faixa observada em fazenda: 40% a 50%. Caso canônico: 1.760 ÷ 4.000 = 44%.
- Em código: `taxa_utilizacao` (decimal).

### Unidade Animal (UA)
Padronização para comparar categorias diferentes. **1 UA = 450 kg de peso vivo.**
Permite dizer "3 UA/ha" independentemente de serem bezerros ou adultos.
Dois usos e um não-uso, fixados pela ADR-014:
- **Exibição** da taxa de lotação (`UA/ha`).
- **Preenchimento**: quando o produtor não sabe o peso médio de uma categoria, o sistema deriva
  `peso_medio_kg = coeficiente_UA × 450`, com `origem: 'ua_tabela'` e `confianca: media`.
- **Nunca** como fórmula paralela de consumo — o cálculo canônico usa `peso_medio_kg`
  (`03` §6.1).

### Taxa de lotação
Quantidade de animais (ou UA) por área. Unidade: `UA/ha`.

### Capacidade de suporte
A taxa de lotação sustentável para um dado nível de desempenho animal.
Diferença importante: taxa de lotação é o que **está**; capacidade de suporte é o que **cabe**.

### Consumo diário
MS ingerida por animal por dia, expressa como % do peso vivo. Faixa: **2% a 3% do PV**.
Ex.: novilho de 300 kg a 2,2% consome 6,6 kg MS/dia.

### Manejo
No SeuGado, **um evento de movimentação de lote** (tirar de um piquete, colocar em outro).
É a unidade de trabalho que consome mão de obra.
- Cuidado: na literatura "manejo" é termo guarda-chuva. Internamente, é sempre o evento.

### Dissolução de lote
Distribuir os animais de um lote entre outros lotes existentes, quando não há piquete apto
para recebê-lo. Operação de último recurso, sempre com confirmação humana.

### Método de pastejo
Qual dos dois regimes governa um piquete: `rotacionado` ou `continuo`. **É propriedade do
piquete, não da fazenda** — fazendas mistas existem (ADR-014). Em código: `metodo_pastejo`,
enum `MetodoPastejo`. Determina qual bloco de parâmetro da cultivar vale ali.
- Proibido: *sistema de pastejo* (na literatura inclui também espécie e lotação), *regime*
  sozinho como nome de campo.

### Parâmetros por regime
Bloco de alturas que uma cultivar tem **para um método de pastejo específico**. A mesma
cultivar tem valores diferentes em contínuo e em rotacionado, e pode ter fonte para um e não
para o outro — o `05` é uma matriz esparsa cultivar × regime (ADR-014).
Em código: `ParametrosRegime`, acessado por `resolver_parametros(cultivar, metodo)`, que é a
porta única e devolve junto a lista de parâmetros `faltantes`.

### Pastejo rotacionado / lotação rotacionada
Método em que o lote alterna entre piquetes, com períodos de ocupação e descanso.
É o método que o SeuGado prescreve no MVP.

### Pastejo contínuo / lotação contínua
Lote permanece na mesma área o tempo todo, ajustando-se a carga animal.
**Está no escopo** como regime desde a ADR-014: tem campo no piquete, bloco de parâmetro
próprio, entra na projeção de estado e gera alerta de altura. O que fica para depois do MVP é a
**prescrição quantificada** de ajuste de lotação (fatia F-009B), que roda em laço **semanal**
por gatilho de altura, separado do laço diário do rotacionado.

### Aguardando parâmetro
Estado de um piquete cuja combinação cultivar × método de pastejo não tem altura conhecida.
Ele entra na projeção de estado, **não** entra em prescrição, e vira pendência de cadastro: o
sistema pergunta ao produtor a altura que ele usa. A resposta é parâmetro **daquela fazenda**,
com `confianca: baixa` — nunca default de catálogo (ADR-014).

### ILPF / ILP
Integração Lavoura-Pecuária(-Floresta). Sistemas com árvores ou rotação com lavoura.
Complica o sensoriamento óptico (sombra, bordas). Fora do escopo do MVP, mas registrado
porque afeta a validade das estimativas se um usuário tentar usar nesse contexto.

---

## Sensoriamento remoto

### NDVI
*Normalized Difference Vegetation Index*. `(NIR − Vermelho) / (NIR + Vermelho)`.
Varia de −1 a 1. Indica vigor da vegetação. É **insumo**, nunca saída para o usuário.

### SAFER
*Simple Algorithm for Evapotranspiration Retrieving*. Modelo que estima evapotranspiração
a partir de imagens ópticas + dados climáticos. Aplicado junto com o modelo de Eficiência
de Uso da Radiação (Monteith), produz taxa de acúmulo de biomassa em kg/ha/dia.
Ver `04-SENSORIAMENTO-REMOTO-E-SAFER.md`.

### ETf — Fração evapotranspirativa
Razão entre evapotranspiração atual e de referência (`ET/ET₀`). Representa o efeito da
umidade na zona das raízes. É a variável do SAFER que carrega "quanta água a planta tem".

### ET₀ — Evapotranspiração de referência
Demanda atmosférica por água, calculada a partir de dados climáticos (Penman-Monteith FAO-56).
O denominador do ETf.

### RFA / RFAabs
Radiação Fotossinteticamente Ativa (incidente / absorvida). A energia que a planta converte
em massa. `RFAinc = 0,44 × RG`.

### RUE / ε_max
*Radiation Use Efficiency* — eficiência máxima de conversão de luz em massa seca, em `g/MJ`.
⚠️ **Varia por via fotossintética.** O valor de 2,45 g/MJ do paper original é para plantas **C3**.
Capins tropicais são **C4** e têm RUE maior. Ver `05-PARAMETROS-CULTIVARES.md`.

### SAR
*Synthetic Aperture Radar*. Sensoriamento por micro-ondas. **Atravessa nuvem.**
No SeuGado, o Sentinel-1 (SAR) serve para preencher lacunas de NDVI em dias nublados,
não para alimentar o SAFER diretamente.

### Backscatter (VV, VH)
Sinal de radar retroespalhado, em duas polarizações. Sensível a umidade do solo e à
estrutura do dossel. Insumo do modelo de gap-filling.

### HLS
*Harmonized Landsat Sentinel-2*. Produto da NASA que harmoniza radiometricamente Landsat 8/9
e Sentinel-2 numa grade única de 30 m. **Fonte óptica primária do projeto.**

### Gap-filling
Reconstrução de valores de NDVI em datas sem imagem óptica limpa, usando SAR + clima
como preditores num modelo de ML treinado nas datas em que existem ambos.

### Graus-dia (soma térmica)
Energia térmica acumulada acima de uma temperatura base. O capim não cresce por calendário,
cresce por energia acumulada. É o motor de interpolação diária entre passagens de satélite.

### Densidade volumétrica do dossel
Quantos `kg MS/ha` existem por centímetro de altura, por cultivar.
**É a ponte entre o que o satélite mede (kg MS/ha) e o que a regra agronômica usa (cm).**
Parâmetro crítico e frequentemente esquecido.

---

## Método de trabalho

### Fatia (vertical slice)
Pedaço fino que atravessa todas as camadas e produz algo demonstrável.
Unidade de planejamento do projeto. **Não usamos sprint nem estimativa de tempo.**

### Spec
Documento autocontido, em inglês, que descreve uma tarefa para o Muse Code.
Segue `09-TEMPLATE-SPEC-MUSE-CODE.md`.

### ADR
*Architecture Decision Record*. Registro de decisão: contexto, decisão, alternativas, consequências.
Vive em `12-REGISTRO-DE-DECISOES-ADR.md`.

### Handoff
Bloco de fechamento de chat, com o que foi feito, o que ficou pendente e o prompt do próximo chat.

### TODO-PARAM
Marcação obrigatória quando uma spec precisa de um parâmetro agronômico que ainda não tem
fonte registrada. Bloqueia **default de produção** e operação com a cultivar afetada, até ser
resolvido num chat `[PESQUISA]`. Não bloqueia função pura que recebe o parâmetro por argumento.

### HIPOTESE-CALIBRAR
Marcação para número que **nós escolhemos** — peso de função objetivo, limiar de alerta,
tolerância de teste. Não é dado empírico, então não cai na regra de fonte rastreável; em
troca, precisa nomear a ADR que vai calibrá-lo. Ex.: pesos `w1..w5` em `07` §2.

### Kit de aceite
Arquivo em `revisoes/KIT-ACEITE-<NNN>.md` com as checagens que comprovam que o código
cumpre a spec: verificações estruturais, o caso canônico e ao menos um caso que a spec não
mostra. **O Muse Code nunca o vê** — se visse, escreveria código para a checagem em vez de
para o requisito (ADR-011).

### Runbook
Arquivo em `revisoes/RUNBOOK-<ID>.md` com a lista ordenada de comandos e verificações que o
Claude Code executa. É o formato de toda ação que exige terminal: git, instalação de
dependência, lint, tipos, testes.

### Relatório de conformidade
Saída do Claude Code em `revisoes/RELATORIO-<ID>.md`: veredicto, tabela de critérios com
evidência, defeitos, e achados fora da implementação. Formato definido em `CLAUDE.md`.
