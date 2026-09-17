# Parâmetros de Cultivares — SeuGado

**REGRA INVIOLÁVEL DO PROJETO: nenhum número entra em código sem constar aqui, com fonte.**

Se uma spec precisa de um parâmetro ausente, marcar `TODO-PARAM: <nome>` e resolver
em chat `[PESQUISA]` antes de implementar. Valor plausível inventado é bug, não dado.

Campo `confianca`:
- `alta` — fonte primária Embrapa/artigo revisado, valor consistente entre fontes
- `media` — fonte secundária confiável, ou divergência pequena entre fontes
- `baixa` — fonte única, ou extrapolado
- `ausente` — `TODO-PARAM`, bloqueia implementação

---

## Alturas de entrada e saída

Valores consolidados da literatura pública. **Divergências entre fontes são reais**
(variam por adubação, estação e condição experimental) — por isso tratamos como
**faixa com default configurável**, nunca constante rígida.

| Cultivar | Espécie | Entrada (cm) | Saída (cm) | Confiança |
|---|---|---|---|---|
| Mombaça | *Panicum maximum* | 90 | 40 | média |
| Tanzânia | *Panicum maximum* | 70 | 30 | média |
| Massai | *Panicum maximum* | 55 | TODO-PARAM | baixa |
| Zuri | *Panicum maximum* | 80 | TODO-PARAM | baixa |
| Tamani | *Panicum maximum* | 50 | TODO-PARAM | baixa |
| Marandu | *Brachiaria brizantha* | TODO-PARAM | 10–15 | média |
| Xaraés | *Brachiaria brizantha* | TODO-PARAM | 15 | média |
| Cameroon | *Pennisetum purpureum* | 100 | 45 | alta |

### Notas por cultivar

**Mombaça.** Fontes divergem: 90 cm citado tanto para 90% de IL quanto para 95% de IL;
outra fonte dá 90 cm para 95% IL e **115 cm para 100% IL**. Saída aparece como 30, 40 e 50 cm
em fontes diferentes. Estudos experimentais usaram combinações de 30 e 50 cm de resíduo.
→ Default: entrada 90, saída 40. Faixa aceitável: entrada 85–95, saída 30–50.

**Tanzânia.** Alturas pré-pastejo estáveis ao longo de um ano experimental:
**65 cm para meta de 90% IL** e **75 cm para 95% IL**. Outra fonte simplifica para ~70 cm.
Resíduos testados: 30 e 50 cm. Com resíduo de 50 cm a IL pós-pastejo foi **67%**,
contra **40%** com 30 cm — o resíduo mais alto gerou **mais ciclos de pastejo**.
→ Default: entrada 70, saída 30. Registrar que 50 cm pode render mais ciclos.

**Cameroon.** Entrada a 100 cm (95% IL) superou 130 cm (100% IL): **−16%** leite/vaca/dia,
**−34%** leite/ha, **+911 kg/ha** de forragem perdida. Descanso fixo recomendado: **27 dias**.
→ Melhor evidência quantitativa disponível. Usar como caso de validação do motor.

**Xaraés.** Descanso fixo recomendado: **28 dias**.

**Marandu.** Resíduos de **10 e 15 cm**. Altura de entrada não capturada numericamente nas
fontes consultadas (aparece só como "95% e 100% de IL"). `TODO-PARAM` prioritário —
Marandu é a braquiária mais plantada do Brasil.

### Fonte prioritária a obter
**Comunicado Técnico 125 — "Régua de Manejo de Pastagens", Embrapa Gado de Corte.**
Cobre oito forrageiras tropicais (Xaraés, Piatã, Marandu, *B. decumbens*, *B. humidicola*,
Mombaça, Tanzânia, Massai) com alturas de entrada e saída em rotacionado **e** faixas
máxima/mínima em contínuo. Publicação Embrapa é de acesso aberto.
→ Obter em `[PESQUISA]` e substituir a tabela acima pelos valores canônicos.

---

## Parâmetros ausentes — bloqueiam implementação

| Parâmetro | Onde é usado | Prioridade | Notas |
|---|---|---|---|
| `densidade_kg_ha_por_cm` (todas cultivares) | ponte massa↔altura | 🔴 crítica | Ver §"Como obter", abaixo |
| `rue_max_g_por_mj` para C4 tropical | eq. 11 do SAFER | 🔴 crítica | Paper usa 2,45 g/MJ **para C3**. C4 é maior |
| `temperatura_base_c` | graus-dia | 🟠 alta | Gramíneas tropicais param abaixo de ~15 °C |
| `altura_entrada_cm` Marandu, Xaraés | regra de entrada | 🟠 alta | Cultivares mais plantadas |
| `altura_saida_cm` Massai, Zuri, Tamani | regra de saída | 🟡 média | Cultivares menos frequentes |
| `descanso_min/max_dias` por cultivar | limites de segurança | 🟡 média | Faixa geral 21–45 conhecida |
| `taxa_senescencia` | balanço de massa | 🟡 média | Aproximação declarada aceita no MVP |

### Como obter `densidade_kg_ha_por_cm` sem ir a campo

Buscar trabalhos que reportem **simultaneamente altura e massa de forragem** da mesma
cultivar. Teses de zootecnia fazem isso rotineiramente (amostram massa, composição
morfológica e altura no pré e pós-pastejo). Cada par (altura, massa) é um ponto de regressão.
15–20 pontos por cultivar dão curva utilizável.

⚠️ A relação não é perfeitamente linear — a densidade aumenta com a altura (o dossel adensa
na base). MVP: linear com intercepto. Se o erro for alto, evoluir para curva.

**Ponto de partida conhecido:** exemplo de fazenda comercial com massa pré-pastejo de
**4.000 kg MS/ha** e pós-pastejo de **2.240 kg MS/ha**. Se a cultivar e as alturas desse
caso forem identificadas, já são dois pontos reais.

---

## Parâmetros zootécnicos (independentes de cultivar)

| Parâmetro | Valor | Confiança | Fonte |
|---|---|---|---|
| `unidade_animal_kg` | 450 | alta | Padrão consolidado. Algumas fontes usam 454 |
| `consumo_pct_pv_min` | 2,0 % | alta | Faixa clássica |
| `consumo_pct_pv_max` | 3,0 % | alta | Faixa clássica |
| `consumo_pct_pv_default` | 2,4 % | média | Exemplo real: 11,62 kg MS/dia ÷ 479 kg = 2,42% |
| `eficiencia_pastejo_min` | 0,40 | alta | Faixa real em fazenda |
| `eficiencia_pastejo_max` | 0,50 | alta | Faixa real em fazenda |
| `eficiencia_pastejo_default` | 0,44 | alta | Caso validado: 1.760 ÷ 4.000 = 44% |
| `ocupacao_min_dias` | 1 | alta | Faixa usual rotacionado |
| `ocupacao_max_dias` | 3 | média | Faixa usual; casos reais usam até 4 |
| `descanso_min_dias` (geral) | 21 | alta | Faixa geral da literatura |
| `descanso_max_dias` (geral) | 45 | alta | Faixa geral da literatura |

### Pesos médios por categoria — TODO-PARAM

| Categoria | Peso médio (kg) | Consumo (% PV) | Confiança |
|---|---|---|---|
| bezerro | TODO-PARAM | TODO-PARAM | ausente |
| novilho | ~300 | 2,2 % | média |
| adulto | ~450–480 | 2,4 % | média |

Referências ancoradas: recria de **300 kg a 2,2%** → 6,6 kg MS/dia.
Machos inteiros de **479 kg** consumindo **11,62 kg MS/dia** (2,42% PV).
→ Bezerro é lacuna real. Resolver em `[PESQUISA]`.

---

## Constantes do SAFER (fixas, não configuráveis)

| Símbolo | Valor | Equação |
|---|---|---|
| `a`, `b`, `c` (albedo) | 0,08 / 0,41 / 0,14 | 2 |
| `a_A`, `b_A` (emiss. atm.) | 0,94 / 0,11 | 4 |
| `a₀`, `b₀` (emiss. sup.) | 0,06 / 1,00 | 5 |
| `σ` (Stefan-Boltzmann) | 5,67×10⁻⁸ W m⁻² K⁻⁴ | 6 |
| `a_sf`, `b_sf` (ETf) | 1,80 / −0,008 | 7 |
| `a_R` (RFA) | 0,44 | 8 |
| `a_F`, `b_F` (fRFA) | 1,257 / −0,161 | 9 |
| fator de conversão | 0,864 | 11 |
| `ET₀` de referência (denominador) | 5 mm/dia | 7 |

---

## Faixas de sanidade (validação de implementação)

| Grandeza | Faixa aceitável | Ação se fora |
|---|---|---|
| NDVI | −1 a 1; pasto vivo: 0,2 a 0,9 | Investigar máscara de nuvem |
| ETf | 0,05 a 1,3 | Falhar alto e logar |
| BIO | 0 a 150 kg/ha/dia | Falhar alto e logar |
| Massa de forragem | 500 a 12.000 kg MS/ha | Alerta, não falha |
| Consumo individual | 1 a 20 kg MS/animal/dia | Falhar alto |

Referências de BIO anual por bioma: Caatinga 15,0 · Cerrado 26,5 · Pantanal 28,9 ·
Amazônia 32,6 · Mata Atlântica 38,2 · Pampa 39,2 (t/ha/ano).
ETf observado: 0,14 (Caatinga seca) a 1,15 (Pampa úmido).

---

## Caso de regressão canônico

Este caso **deve** ser reproduzido pelo motor de cálculo. Se não reproduzir, há bug.

```yaml
entrada:
  area_total_ha: 46.5
  n_piquetes: 8
  area_piquete_ha: 5.81
  massa_pre_pastejo_kg_ms_ha: 4000
  massa_pos_pastejo_kg_ms_ha: 2240
  n_animais: 220
  peso_medio_kg: 479
  dias_ocupacao: 4
  dias_descanso: 28

saida_esperada:
  consumo_total_kg_ms_ha: 1760
  consumo_individual_kg_ms_dia: 11.62   # tolerância ±0.05
  consumo_pct_pv: 2.42                  # tolerância ±0.02
  eficiencia_utilizacao: 0.44           # tolerância ±0.01
```

---

## Formato canônico no código

```yaml
mombaca:
  nome_exibicao: "Mombaça"
  especie: "Panicum maximum"
  via_fotossintetica: C4
  altura_entrada_cm: 90
  altura_entrada_faixa: [85, 95]
  altura_saida_cm: 40
  altura_saida_faixa: [30, 50]
  densidade_kg_ha_por_cm: null      # TODO-PARAM
  rue_max_g_por_mj: null            # TODO-PARAM (C4)
  temperatura_base_c: null          # TODO-PARAM
  descanso_min_dias: 21
  descanso_max_dias: 45
  qualidade_base: alta
  fontes:
    altura_entrada: "Embrapa, Podcast Primeiro Pastejo (90% IL ~90cm)"
    altura_saida: "Embrapa, idem (~40cm)"
  observacoes: >
    Fontes divergem: outra referência dá 90cm para 95% IL e 115cm para 100% IL.
    Resíduos experimentais de 30 e 50 cm também documentados.
  confianca: media
```

Todo parâmetro `null` com comentário `TODO-PARAM` faz o sistema **recusar-se a operar**
com aquela cultivar, exibindo mensagem clara — em vez de usar default silencioso.
