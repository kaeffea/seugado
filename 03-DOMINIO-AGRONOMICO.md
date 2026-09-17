# Domínio Agronômico — SeuGado

Base conceitual e matemática do manejo de pastagens. Escrito para quem **não é da área**.
Termos definidos em `02-GLOSSARIO.md`. Valores numéricos em `05-PARAMETROS-CULTIVARES.md`.

---

## 1. Por que matéria seca

Capim é majoritariamente água, e o teor de água varia com chuva, hora do dia, estação e
espécie. Dois piquetes com o mesmo peso de capim verde podem conter quantidades de alimento
completamente diferentes.

Por isso a zootecnia padroniza tudo em **matéria seca**: corta-se uma amostra, pesa-se verde,
seca-se em estufa até peso constante, pesa-se de novo. O que sobrou é o alimento real.

A literatura é explícita: o teor de MS é bastante variável entre gramíneas, componentes
morfológicos e épocas do ano, e **todos os cálculos de disponibilidade de forragem e ajuste
de lotação devem ter como base o teor de MS**.

> **Consequência para o sistema:** `kg MS/ha` é a unidade de interoperação entre o módulo de
> sensoriamento e o módulo de decisão. Nenhum outro módulo deve inventar unidade própria.

---

## 2. Estoque vs. fluxo

Dois números diferentes que iniciantes confundem:

| Conceito | Unidade | O que é | De onde vem |
|---|---|---|---|
| **Massa de forragem** | `kg MS/ha` | Quanto capim **tem agora** | Integral da taxa de acúmulo |
| **Taxa de acúmulo** | `kg MS/ha/dia` | Quanto capim **cresce por dia** | Saída direta do SAFER |

O SAFER produz a **taxa**. O sistema integra no tempo para obter o **estoque**,
subtraindo o que foi consumido nos períodos de ocupação.

```
massa(t+1) = massa(t) + taxa_acumulo(t) − consumo(t) − senescencia(t)
```

A `senescencia` (morte natural de folha velha) é frequentemente ignorada em modelos simples.
No MVP tratamos como fração da massa proporcional à idade do rebrote; é uma aproximação
declarada, não uma omissão.

---

## 3. Altura de entrada — a fisiologia

Este é o conceito central do manejo rotacionado, e a razão é fisiológica, não arbitrária.

O capim cresce e vai fechando o dossel. Quando intercepta **95% da luz incidente** (só 5%
chega à base da planta), ele atinge o ponto de máxima produtividade: máxima quantidade de
folhas, poucos talos, pouco material morto.

Passado esse ponto, a planta **rapidamente passa do estágio vegetativo para o reprodutivo**,
alongando hastes, aumentando a distância entre folhas e dificultando a colheita pelos animais.

> **A contraintuição que vende o produto:** deixar passar do ponto não é "mais capim",
> é capim pior. Mais massa, menos alimento.

### A prova quantitativa

Em capim-elefante cv. Cameroon com vacas mestiças, comparando entrada a 100 cm (95% IL)
contra 130 cm (100% IL), a altura maior resultou em:

- **−16%** de leite por vaca/dia
- **−34%** de leite total por hectare
- **+911 kg/ha** de forragem perdida

Mais alto = menos produção **e** mais desperdício. Este é o dado mais persuasivo do domínio.

### Por que altura e não IL

Medir interceptação luminosa exige fotômetro, aparelho caro e específico. A literatura
estabeleceu que a **altura do dossel substitui a IL de forma consistente, independente da
época do ano, altura de resíduo e estádio fisiológico**. Por isso a Embrapa criou a
"régua de manejo de pastagens" — uma régua física que o trabalhador leva ao campo.

**Implicação de UX:** o produtor pensa em centímetros. Toda comunicação com ele deve ser
em cm, mesmo que internamente o sistema opere em kg MS/ha.

---

## 4. Altura de saída — por que o resíduo importa

É o ponto em que a parte boa (folhas) foi consumida, mas resta folha suficiente para rebrota
rápida. Sair baixo demais faz a planta perder área foliar e recorrer a reservas de raiz,
degradando o pasto ao longo das estações.

Isso tem efeito mensurável no ciclo. Em capim-tanzânia, pastos com resíduo de **50 cm**
tiveram **mais ciclos de pastejo** que os de 30 cm, porque a IL pós-pastejo era de **67%**
com 50 cm contra **40%** com 30 cm — mais folha remanescente, rebrota mais rápida.

> **Implicação para o otimizador:** a altura de saída **não é apenas uma restrição, é uma
> variável de decisão** que afeta o ciclo futuro. Sair mais alto reduz o consumo agora mas
> devolve o piquete mais cedo. O otimizador deve poder explorar esse trade-off dentro da
> faixa segura da cultivar.

---

## 5. Período de descanso — onde o SeuGado ganha

Faixa prática geral na literatura: **descanso de 21 a 45 dias, ocupação de 1 a 3 dias**.
Algumas cultivares têm descanso fixo recomendado (Xaraés: 28 dias; Cameroon: 27 dias).

Mas descanso fixo é uma **aproximação grosseira**. O correto é descanso variável governado
pelo crescimento real. Nas águas o descanso encurta; na seca, alonga. Tabelas fixas erram
exatamente nas transições de estação, que é quando o produtor mais perde.

> **Este é o diferencial agronômico defensável do projeto:**
> "não usamos calendário fixo, usamos o crescimento observado."

Mantemos `descanso_min_dias` e `descanso_max_dias` por cultivar como **limites de segurança**,
não como alvo. O alvo é a altura de entrada.

---

## 6. A cadeia de cálculo completa

### 6.1. Consumo do lote

O que consome pasto não é o número de cabeças, é o **peso vivo total**.

```
consumo_lote_dia (kg MS/dia) = Σ_categorias ( n_animais × peso_medio_kg × pct_consumo )
```

Faixa de `pct_consumo`: **2% a 3% do peso vivo**.
Exemplo da literatura: recria de 300 kg a 2,2% → 6,6 kg MS/dia.

### 6.2. Forragem efetivamente disponível

```
MS_disponivel (kg MS) = ( massa_atual − massa_residuo_alvo ) × area_ha × eficiencia_pastejo
```

`eficiencia_pastejo` entre **0,40 e 0,50**. Sem esse fator, o sistema superestima a
capacidade do piquete em mais que o dobro.

### 6.3. Dias de ocupação

```
dias_ocupacao = MS_disponivel ÷ consumo_lote_dia
```

**Refinamento obrigatório:** o capim continua crescendo enquanto o lote está lá.
A conta correta soma a massa acumulada durante a ocupação:

```
MS_total = MS_inicial + ( taxa_acumulo × dias_ocupacao )
```

Como a `taxa_acumulo` diária vem do SAFER, incluir isso é trivial e aumenta a precisão
sobre qualquer concorrente que use massa estática.
Resolver iterativamente (2-3 iterações convergem) ou analiticamente.

### 6.4. Exemplo validado (fazenda comercial real)

Área 46,5 ha, 8 piquetes de 5,81 ha, ciclo 32 dias (4 de ocupação + 28 de descanso),
220 machos de 479 kg:

| Item | Valor |
|---|---|
| Massa pré-pastejo | 4.000 kg MS/ha |
| Massa pós-pastejo | 2.240 kg MS/ha |
| Consumo total | 1.760 kg MS/ha |
| Consumo individual | 1.760 × 5,81 ÷ 4 ÷ 220 = **11,62 kg MS/animal/dia** |
| Consumo em % PV | 11,62 ÷ 479 × 100 = **2,42%** |
| Eficiência de utilização | 1.760 ÷ 4.000 = **44%** |

Use este caso como **teste de regressão** do motor de cálculo: dados os mesmos insumos,
o sistema deve reproduzir estes números.

### 6.5. Unidade Animal

**1 UA = 450 kg de peso vivo** (algumas fontes usam 454 kg, ou definem 1 UA como consumindo
12 kg MS/dia). Serve para normalizar lotes heterogêneos e para exibir taxa de lotação.
Não entra no cálculo de ocupação — lá usamos peso vivo direto, que é mais preciso.

---

## 7. A ponte crítica: kg MS/ha ↔ centímetros

**O ponto de integração mais importante e mais esquecido do projeto.**

O SAFER produz `kg MS/ha`. As regras agronômicas estão em `cm`. A ponte é a
**densidade volumétrica do dossel**, por cultivar:

```
altura_estimada_cm = massa_forragem_kg_ha ÷ densidade_kg_ha_por_cm
massa_alvo_kg_ha  = altura_alvo_cm × densidade_kg_ha_por_cm
```

### Como obter a densidade sem ir a campo

Buscar trabalhos que reportem **simultaneamente altura e massa de forragem** para a mesma
cultivar. Teses e artigos de zootecnia fazem isso rotineiramente (medem massa, composição
morfológica e altura no pré e pós-pastejo). Cada par (altura, massa) é um ponto de regressão.
Com 15–20 pontos por cultivar tem-se uma curva utilizável.

⚠️ A relação **não é perfeitamente linear** — a densidade tende a aumentar com a altura
(o dossel adensa na base). No MVP usamos linear com intercepto; se o erro for alto,
evoluir para curva.

### Decisão de arquitetura

Operar internamente em `kg MS/ha` e converter para `cm` **apenas na camada de apresentação**.
Motivo: a massa é a grandeza física conservada (dá para somar, subtrair, integrar);
altura não é aditiva.

---

## 8. Valor nutritivo — o que fazer e o que não fazer no MVP

Parâmetros clássicos: **PB** (proteína bruta; abaixo de ~7% a digestão trava e o animal
come menos), **FDN** (fibra em detergente neutro; quanto maior, menor o consumo possível)
e **digestibilidade**.

**Mas:** dentro de uma mesma cultivar, o valor nutritivo varia **mais com a idade do rebrote
do que com a espécie**. Capim passado do ponto tem mais talo e material morto, o que derruba
PB e sobe FDN — que é exatamente o que a regra dos 95% de IL já protege.

> **Decisão de escopo (ver ADR-005):** não modelar química no MVP.
> Usar **idade do rebrote** (dias ou graus-dia desde a saída) como proxy de qualidade,
> exposta como indicador qualitativo: `ótima` / `declinando` / `passado do ponto`.
> Ganha-se ~80% do valor com ~10% da complexidade.

Cada cultivar carrega um campo `qualidade_base` (`alta` / `média` / `baixa`) para diferenciar,
por exemplo, *Panicum* de *B. humidicola*, sem modelar química nenhuma.

---

## 9. Restrições operacionais — o que nenhum concorrente modela

Estas não são agronomia, são realidade de fazenda, e são o fosso competitivo do SeuGado.

### 9.1. Mão de obra
Cada manejo consome tempo de um funcionário. Não adianta o ótimo matemático pedir 15
movimentações num dia se a fazenda tem 2 pessoas.
Campos necessários: `funcionarios_disponiveis`, `manejos_por_funcionario_dia`.
Fricção: dois números, uma vez, no cadastro.

### 9.2. Rotina
Fazenda tem rotina. "Segunda e quinta é dia de mexer gado."
O produtor quer **previsibilidade**, não otimalidade dinâmica.
Modelar como restrição de janela: manejos só em dias configurados.
Isso **reduz** o ótimo matemático e **aumenta muito** a adoção real.

Argumento de venda: *"otimizamos dentro da rotina do produtor, não contra ela."*

### 9.3. Lotes indissolúveis
Lote separado para venda, lote em protocolo sanitário, lote de genética.
Flag booleana `indissoluvel`. O otimizador nunca propõe fusão desses.

### 9.4. Compatibilidade de fusão
Se houver fusão, só entre categorias compatíveis. Não misturar bezerros com adultos:
competição alimentar, risco de lesão, manejo sanitário diferente.

---

## 10. Sazonalidade brasileira

| Período | Nome popular | Comportamento |
|---|---|---|
| Out–Mar | **Águas** | Crescimento acelerado. Maior risco de sub-pastejo (capim passa do ponto). Maior cobertura de nuvem → pior sensoriamento óptico |
| Abr–Set | **Seca** | Crescimento lento. Maior risco de super-pastejo. Céu limpo → bom sensoriamento óptico |

**A ironia central do problema:** a época em que o sistema mais precisa acertar (águas) é
exatamente a época em que o satélite óptico menos enxerga. É isto que justifica o
gap-filling por SAR e a interpolação climática.

---

## 11. Erros comuns a evitar no código

1. Usar peso verde em vez de matéria seca em qualquer conta.
2. Esquecer a eficiência de pastejo (superestima capacidade em >2x).
3. Tratar massa de forragem como estática durante a ocupação.
4. Usar número de cabeças em vez de peso vivo total no consumo.
5. Aplicar período de descanso fixo em vez de crescimento observado.
6. Confundir `kg MS/ha` com `cm` sem passar pela densidade.
7. Usar RUE de planta C3 (2,45 g/MJ) para capim tropical, que é C4.
8. Deixar o lote sair abaixo do resíduo mínimo "porque o otimizador achou melhor".
