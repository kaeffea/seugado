# Sensoriamento Remoto e Modelo SAFER — SeuGado

Como o sistema enxerga o pasto do céu. Base científica, equações, limitações e decisões.

---

## 1. Descoberta que define a arquitetura: o SAFER não precisa de banda termal

Intuição comum e **errada**: "preciso de Landsat 8 porque ele tem sensor térmico".

No SAFER, a temperatura de superfície (T₀) é obtida pelo **método residual**, via lei de
Stefan-Boltzmann, a partir do balanço de radiação — **não de um sensor térmico**.

Confirmação independente: a Embrapa aplicou a metodologia em pastagem usando o produto
**HLS (Harmonized Landsat Sentinel-2)**, que é um produto de **refletância de superfície
apenas**, sem banda termal. Se fosse necessário termal, não poderiam ter usado HLS.

> **Consequência:** Sentinel-2 pode ser usado normalmente, mesmo sem banda termal.
> Isso libera a fonte de maior revisita e maior resolução espacial.

---

## 2. Cadeia completa de equações

Fonte: Teixeira et al., *Geotecnologias para estimativas da produção de biomassa nos biomas
do Brasil* (Embrapa). Coeficientes obtidos originalmente no Nordeste com medições
simultâneas de campo e satélite.

| # | Grandeza | Formulação | Coeficientes |
|---|---|---|---|
| 1 | NDVI | `(ρ_NIR − ρ_red) / (ρ_NIR + ρ_red)` | — |
| 2 | Albedo de superfície `α₀` | função do albedo no topo da atmosfera | `a=0,08`, `b=0,41`, `c=0,14` |
| 3 | Saldo de radiação `Rn` | equação de Slob, com `τ_sw = RG / R_topo` | `a_L` = f(Ta) |
| 4 | Emissividade atmosférica `ε_A` | função de `−ln τ_sw` | `a_A=0,94`, `b_A=0,11` |
| 5 | Emissividade da superfície `ε₀` | função de `ln(NDVI)` | `a₀=0,06`, `b₀=1,00` |
| 6 | Temperatura de superfície `T₀` | **residual**, Stefan-Boltzmann | `σ = 5,67×10⁻⁸ W m⁻² K⁻⁴` |
| 7 | Fração evapotranspirativa `ETf` | `exp[ a_sf + b_sf · ( T₀ / (α₀ · NDVI) ) ] × (ET₀_ano / 5)` | `a_sf=1,80`, `b_sf=−0,008` |
| 8 | RFA incidente | `RFA_inc = a_R × RG` | `a_R = 0,44` |
| 9 | Fração de RFA absorvida | `f_RFA = a_F · NDVI + b_F` | `a_F=1,257`, `b_F=−0,161` |
| 10 | RFA absorvida | `RFA_abs = f_RFA × RFA_inc` | — |
| 11 | **Biomassa** | `BIO = ε_max × ETf × RFA_abs × 0,864` | `ε_max` ver §3 |

**Saída:** `BIO` em `kg/ha/dia` — é **taxa de acúmulo**, não estoque.

O termo `(ET₀_ano / 5)` na eq. 7 é um fator de correção para demandas atmosféricas
diferentes da região onde o SAFER foi calibrado; `5 mm/dia` é a média diária anual de ET₀
do Nordeste brasileiro, região original de calibração.

### Faixas de sanidade (para testes)

Valores de referência da literatura, por bioma, para validar que a implementação não
está produzindo absurdo:

| Bioma | ETf médio anual | BIO anual |
|---|---|---|
| Caatinga | 0,29 | 15,0 t/ha/ano |
| Cerrado | — | 26,5 t/ha/ano |
| Pantanal | — | 28,9 t/ha/ano |
| Amazônia | — | 32,6 t/ha/ano |
| Mata Atlântica | — | 38,2 t/ha/ano |
| Pampa | 0,94 | 39,2 t/ha/ano |

ETf observado varia de **0,14** (Caatinga, seca) a **1,15** (Pampa, úmido).
BIO diária típica: **20 a 115 kg/ha/dia** conforme bioma e trimestre.

> **Teste de sanidade obrigatório:** se a implementação produzir ETf fora de `[0,05; 1,3]`
> ou BIO fora de `[0; 150] kg/ha/dia`, há bug. Falhar alto e logar.

---

## 3. ⚠️ O ajuste C3/C4 — erro sistemático se ignorado

No paper, `ε_max = 2,45 g/MJ`, explicitamente assumido **"para a maioria das plantas C3 no Brasil"**.

Capins tropicais — Mombaça, Marandu, Tanzânia, Zuri, Massai (todos *Panicum* e *Brachiaria*) —
são plantas **C4**. Plantas C4 têm fotossíntese mais eficiente e portanto **RUE maior** que C3.

**Usar 2,45 g/MJ para capim tropical subestima sistematicamente a biomassa.**

Ações:
1. `ε_max` é **parâmetro por cultivar**, configurável, nunca constante no código.
2. Valor para gramíneas C4 tropicais é `TODO-PARAM` — resolver em chat `[PESQUISA]`.
3. Documentar a via fotossintética de cada cultivar em `05-PARAMETROS-CULTIVARES.md`.

Isto também é argumento técnico de diferenciação:
*"calibramos o RUE por via fotossintética da cultivar, não usamos o default genérico."*

---

## 4. Escolha de satélites

| Fonte | Resolução espacial | Revisita | Banda termal | Papel |
|---|---|---|---|---|
| **HLS** (Landsat 8/9 + Sentinel-2 harmonizados) | 30 m | ~2–3 dias | não | **Fonte óptica primária** |
| Sentinel-2 puro | 10 m (red/NIR) | ~5 dias | não | Refinamento para piquetes pequenos (fase 2) |
| Landsat 8/9 puro | 30 m | 16 dias (8 com os dois) | sim (não usada) | Já embutido no HLS |
| Sentinel-1 (SAR) | ~10 m | ~6–12 dias | — | Gap-filling, umidade, detecção de evento |

**Decisão (ADR-002):** usar **HLS** como fonte primária. Motivos: já harmoniza
radiometricamente as duas constelações (elimina o problema de calibrações diferentes),
maximiza revisita, e é exatamente o produto que a Embrapa usou na validação em pastagem.

Sentinel-2 puro a 10 m entra como fase 2, para piquetes de rotacionado intensivo
(0,5 a 3 ha), onde 30 m gera poucos pixels úteis por piquete.

### Regra de amostragem por piquete

⚠️ Pixels de borda misturam cerca, estrada e piquete vizinho. Aplicar **buffer negativo**
na geometria do piquete antes de amostrar (ex.: −15 m para HLS). Piquetes pequenos demais
para sobrar pixel após o buffer devem ser sinalizados com confiança reduzida.

---

## 5. Alerta crítico: o erro de 50%

Um estudo aplicou a mesma cadeia (Monteith + sensoriamento) em algodão e **superestimou a
produtividade em 50%**, com erro absoluto médio de 2 t/ha.

A causa declarada pelos autores: como o Landsat 8 tem revisita de 16 dias, em meses com
apenas uma imagem livre de nuvens foi necessário **multiplicar o valor diário de biomassa
por 30 dias**, e mudanças no ciclo da cultura não puderam ser identificadas.

O mesmo estudo relatou outro problema: o mascaramento de nuvens foi eficiente para eliminar
pixels nublados, **mas não excluiu os pixels com projeção de sombra de nuvem**, que
apresentaram NDVI abaixo do real e geraram diferenças bruscas de produtividade estimada.

> **Duas exigências de implementação que saem daí:**
> 1. **Nunca extrapolar linearmente** um valor diário de BIO por muitos dias.
>    A interpolação entre passagens é por clima (§6), não por repetição.
> 2. **Mascarar sombra de nuvem**, não só nuvem. É uma fonte de erro silenciosa e grande.

---

## 6. Interpolação climática — o motor diário

Capim não cresce por calendário, cresce por energia acumulada. Arquitetura:

> **Satélite = âncora de calibração** (a cada 2–5 dias, quando há céu limpo)
> **Clima = motor de interpolação diária** entre âncoras

Todo dia o sistema avança o estado de cada piquete usando clima. Quando chega imagem limpa,
**corrige o desvio acumulado**. Conceitualmente é um filtro de Kalman; no MVP pode ser
uma correção proporcional simples.

### Variáveis climáticas necessárias

| Variável | Onde entra |
|---|---|
| Radiação solar global (RG) | `RFA_inc = 0,44·RG`; `Rn` via Slob |
| Temperatura do ar (média, máx, mín) | `Rn`, `ET₀`, graus-dia |
| Umidade relativa | `ET₀` |
| Velocidade do vento | `ET₀` |
| Precipitação | crescimento, balanço hídrico simplificado |

**Fontes candidatas (ambas gratuitas, avaliar em `[PESQUISA]`):**
- **INMET** — estações automáticas. A Embrapa usou 491 estações interpoladas pelo método
  de "movimento da média" até a resolução das imagens. Risco: densidade irregular de estações.
- **Reanálise (ERA5 / NASA POWER)** — grade contínua, sem dependência de estação próxima.
  Menor resolução espacial, maior consistência temporal.

Recomendação inicial: usar reanálise como base (cobertura garantida) e INMET como
correção local quando houver estação próxima.

### Graus-dia

```
GD_dia = max(0, (T_max + T_min)/2 − T_base)
GD_acumulado = Σ GD_dia desde a saída do último lote
```

`T_base` é parâmetro por cultivar (gramíneas tropicais têm base alta — praticamente param
abaixo de ~15 °C). Valor exato é `TODO-PARAM`.

---

## 7. Sentinel-1 (SAR) — quatro papéis, um deles essencial

**O SAR não alimenta o SAFER.** O SAFER depende de refletância óptica (NDVI, albedo) para
derivar T₀ e ETf. Radar mede retroespalhamento de micro-ondas — grandeza física diferente.

### 7.1. Gap-filling de NDVI ⭐ (papel principal)

Literatura consolidada: modelos de ML (Random Forest) reconstruíram NDVI afetado por nuvens
a partir de Sentinel-1 + Landsat 8 na bacia do Rio Doce, com **índice de concordância de
Willmott entre ~0,64 e 0,96**, permitindo monitoramento livre de lacunas por nuvens e sombras.

Mecânica:
1. Nos dias com **ambas** as fontes, treinar modelo `SAR + clima + contexto → NDVI`.
2. Nos dias nublados com **só SAR**, prever o NDVI que teria sido observado.
3. O NDVI sintético entra no SAFER normalmente, marcado com flag de origem.

> Arquiteturalmente elegante: não são dois modelos concorrentes. O SAR **mantém o SAFER
> rodando durante as nuvens**.

⚠️ Ressalva da literatura: a relação NDVI–SAR **não é genérica**; é afetada por estrutura
do dossel, fenologia, exposição e umidade do solo. Exige treino com dados da região/cultivar.

### 7.2. Umidade do solo
Backscatter VV e VH é **altamente sensível à umidade do solo devido ao gradiente dielétrico**.
Umidade governa o ETf. Uso: variável auxiliar de validação/correção do ETf.
⚠️ Em vegetação alta e densa a interação do sinal com a vegetação fica complexa e o NDVI
satura — funciona melhor em pasto baixo/rebrota do que em capim pronto para entrada.

### 7.3. Estimativa independente de biomassa
Em pastagem, relação quadrática significativa entre biomassa acima do solo e polarização
**VH**, com **R² = 0,71** — porém apenas com modelo de elevação de **1 m** para ortorretificar;
com MDEs usuais de 30 ou 90 m o desempenho caiu.

> Uso: **sinal de corroboração** para a camada de confiança ("os dois modelos concordam?"),
> nunca como fonte primária. Mediano e sensível a topografia.

### 7.4. Detecção de evento de pastejo
Existe literatura sobre observação de práticas de corte em pastagem via SAR polarimétrico.
Quando um lote rebaixa o capim, a estrutura do dossel muda e isso aparece no backscatter.
Uso: **inferir automaticamente que um manejo ocorreu**, reduzindo a fricção de confirmação.

---

## 8. Validação por foto — sensoriamento proximal barato

Literatura de apoio: integrando sensoriamento proximal (altura por sensor ultrassônico) com
índices de vegetação de Landsat 7 e Sentinel-2, o **XGBoost atingiu R² = 0,86, MAE de
414 kg/ha e RMSE de 538 kg/ha**. Isso é substancialmente melhor que satélite puro.

A foto do celular com referência de escala é o substituto barato do ultrassônico.

**Achado útil para escopo:** no mesmo estudo, os índices de **red-edge do Sentinel-2 não
melhoraram substancialmente** as predições em pastagem homogênea. Não gastar esforço com
bandas exóticas no MVP — NDVI e derivados simples bastam.

### Implementação, do simples ao complexo
1. **Objeto de escala conhecida** na foto (régua de manejo, cabo de enxada marcado, bota),
   usuário arrasta dois pontos na tela marcando base e topo do dossel. Quase sem CV. ← **MVP**
2. **Marcador ArUco** impresso — detecção robusta e gratuita via OpenCV, escala automática.
3. Segmentação + estimativa de altura por visão computacional. Pós-MVP.

**Quando pedir:** só quando a confiança estiver baixa. Isso transforma a foto de "tarefa
chata" em "o sistema está sendo honesto comigo e pedindo ajuda".

**Efeito composto:** cada foto vira dado de treino. O modelo fica calibrado para aquela
fazenda específica. É um fosso competitivo que **cresce com o uso** e que nenhum
concorrente satélite-puro tem.

---

## 9. Camada de confiança

```
confianca = f(
  dias_desde_ultima_imagem_optica_limpa,
  pct_nuvem_na_ultima_leitura,
  concordancia_SAFER_vs_SAR,
  erro_historico_do_modelo_neste_piquete,
  houve_foto_de_validacao_recente,
  pixels_validos_apos_buffer
)
```

| Faixa | Comportamento |
|---|---|
| **Alta** | Executa recomendação normalmente |
| **Média** | Recomenda, mas sinaliza a incerteza na mensagem |
| **Baixa** | Recomenda + pede foto de validação (opcional) |

Não é enfeite. É o antídoto para a maior objeção do pecuarista a sistemas de IA:
*"como é que eu sei que isso tá certo?"*. E é diferencial: nenhum concorrente pesquisado
expõe confiança da própria estimativa.

---

## 10. Pipeline diário

```
1. Buscar imagens novas (HLS, Sentinel-1) para as geometrias da fazenda
2. Mascarar nuvem E sombra de nuvem
3. Aplicar buffer negativo; se pixels válidos < limiar → marcar confiança baixa
4. Calcular NDVI por piquete (média dos pixels válidos)
5. Se não houver óptico limpo → prever NDVI via modelo SAR (flag: sintético)
6. Buscar clima do dia (RG, Ta, UR, vento, chuva)
7. Rodar SAFER → taxa de acúmulo (kg MS/ha/dia)
8. Avançar estado: massa(t+1) = massa(t) + acúmulo − consumo − senescência
9. Se houve imagem óptica limpa → corrigir desvio acumulado (âncora)
10. Converter massa → altura (densidade da cultivar) para apresentação
11. Recalcular confiança
12. Disparar otimizador se for dia de planejamento
```

Frequência: diária. Custo computacional baixo o suficiente para caber em agendador gratuito.
