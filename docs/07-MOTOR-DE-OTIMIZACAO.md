# Motor de Otimização — SeuGado

O núcleo de Computação do projeto. É aqui que um time de Computação entrega algo que
agrônomos e agtechs de ERP não entregam.

---

## 1. Por que é genuinamente difícil

Não é "escolher o melhor piquete". É **atribuição com recursos limitados, restrições
temporais e efeitos futuros** — classe NP-difícil.

Três coisas o tornam não-trivial:

1. **Acoplamento temporal.** Mandar o lote para o piquete A hoje muda quais piquetes estarão
   disponíveis daqui a 3 semanas. Guloso míope degrada o sistema ao longo do ciclo.
2. **Recurso compartilhado escasso.** Mão de obra limita quantas movimentações cabem no dia.
3. **Variável de decisão dupla.** A altura de saída não é só restrição: sair mais alto
   consome menos agora mas devolve o piquete mais cedo (evidência em
   `03-DOMINIO-AGRONOMICO.md` §4 — resíduo de 50 cm rendeu mais ciclos que 30 cm).

Concorrentes entregam mapa NDVI porque não têm quem formule isto.

---

## 2. Formulação

### Escopo do problema diário (ADR-014)

A formulação abaixo é do **pastejo rotacionado**. Piquete com `metodo_pastejo = continuo` fica
**fora da variável de atribuição** `x[l,p,d]` — seu lote está fixado, e não existe variável
inteira de número de animais no problema diário. Ele **continua** na projeção de estado e
**continua** candidato na hierarquia do §4, porque é válvula de escape acima da fusão de lotes.

O contínuo tem laço próprio, **semanal**, disparado por gatilho de altura
(`altura_maxima_cm` / `altura_minima_cm` do bloco de regime da cultivar), que produz
recomendação de **ajuste de lotação** em vez de movimentação. É a fatia **F-009B**, pós-MVP;
até ela existir, piquete contínuo gera estado e alerta, não prescrição quantificada.

### Índices
- `l ∈ L` — lotes
- `p ∈ P` — piquetes **em pastejo rotacionado**
- `d ∈ D` — dias do horizonte (14 a 30)

### Variável principal
```
x[l,p,d] ∈ {0,1}   # lote l ocupa piquete p no dia d
```

### Variáveis derivadas
```
move[l,d]  ∈ {0,1}   # houve movimentação do lote l no dia d
massa[p,d] ∈ ℝ⁺      # massa de forragem projetada do piquete p no dia d
y[l_org,l_dst] ∈ {0,1}  # fusão de lote (só quando acionada)
```

### Restrições duras

| # | Restrição | Formulação |
|---|---|---|
| R1 | Um lote está em exatamente um piquete por dia | `Σ_p x[l,p,d] = 1  ∀l,d` |
| R2 | Um piquete recebe no máximo um lote | `Σ_l x[l,p,d] ≤ 1  ∀p,d` |
| R3 | Só entra em piquete apto | `x[l,p,d] ≤ apto[p,d]` |
| R4 | Nunca abaixo do resíduo mínimo | `massa[p,d] ≥ residuo_min[p]` |
| R5 | Descanso mínimo respeitado | ver §3 |
| R6 | Ocupação dentro da faixa da cultivar | `1 ≤ ocupação ≤ 3 dias` (configurável) — ver nota de assimetria abaixo |
| R7 | **Mão de obra** | `Σ_l move[l,d] ≤ capacidade_manejo[d]  ∀d` |
| R8 | **Rotina** | `move[l,d] = 0` se `d ∉ dias_preferenciais` |
| R9 | Lotes indissolúveis | `y[l,·] = 0  ∀l ∈ indissolúveis` |
| R10 | Fusão só entre categorias compatíveis | `y[a,b] ≤ compatível[a,b]` — ver abaixo |
| R11 | Piquete sem parâmetro não recebe lote | `x[l,p,d] = 0` se `resolver_parametros` devolve `faltantes` |

**R7 e R8 são o diferencial.** Nenhum concorrente pesquisado modela mão de obra ou rotina.

**R10, definido (ADR-014, fecha DT11).** `compatível[a,b] = 1 ⟺ |ordem(a) − ordem(b)| ≤ 1`,
com `ordem` sendo a posição da categoria na escala de UA do `05` (bezerro 0,25 · novilho
0,50–0,75 · adulto 1,00 · touro 1,25). Dois lotes são fundíveis só se **todo** par de
categorias entre eles for compatível. O limiar `≤ 1` é **`HIPOTESE-CALIBRAR`** — escolha
nossa, a calibrar na ADR de fusão de lotes prevista antes do F-022. Ver `03` §9.4.

**R6 precisa de assimetria, e ainda não tem.** A faixa 1–3 dias tem fonte (`03` §5), mas hoje é
dura nos dois lados, e os dois lados não têm o mesmo custo. Estourar **3 dias** faz o gado comer
a rebrota da própria planta — dano agronômico, que é o erro que o produto existe para evitar.
Ficar **abaixo de 1 dia** é só incômodo operacional: acontece sempre que o lote é grande demais
para o piquete, e numa fazenda com lotes grandes e piquetes pequenos torna **todo** par
`(lote, piquete)` inviável — o modelo volta sem solução em vez de voltar com um plano ruim.
Decisão pendente: limite superior duro, limite inferior *soft* com penalidade. Fica para a **ADR
de pesos da função objetivo**, prevista antes do F-009 (`10`), junto com `w6`. Registrada como
**Q13** no `11`.

**R11 é a contrapartida da matriz esparsa.** Piquete cuja combinação cultivar × método de
pastejo não tem altura conhecida fica `aguardando_parametro`: aparece no estado, não entra no
plano, e vira pergunta ao produtor no cadastro (ADR-014).

### Função objetivo

Ponderada, com pesos configuráveis por fazenda:

```
maximizar:
    w1 · consumo_dentro_da_janela_de_qualidade
  − w2 · forragem_perdida_por_passar_do_ponto
  − w3 · numero_de_movimentacoes
  − w4 · penalidade_violacao_residuo_soft
  − w5 · desvio_da_rotina_preferida
  − w6 · custo_espacial
```

`custo_espacial = Σ_l Σ_d dist[origem(l,d), destino(l,d)] · peso_vivo_total[l]` (ADR-016).
Multiplicar pelo peso vivo é deliberado: mover 200 bois por 3 km não custa o mesmo que mover 20
bezerros. `dist` é a matriz de distância entre centroides de piquete, derivada da geometria que o
`06` §5 já guarda. Este termo é o que impede o plano de rotas cruzadas — ver a prova na ADR-016.

Pesos iniciais: `w1=1.0, w2=0.8, w3=0.3, w4=5.0, w5=0.2, w6` a definir — **`HIPOTESE-CALIBRAR`**.
Não são dado empírico e não estão sujeitos à regra 1 (ver `05`, "Escopo desta regra"):
são escolha de projeto, a ser calibrada na ADR de pesos da função objetivo, prevista
antes do F-009. `w4` alto de propósito: violar resíduo degrada o pasto por temporadas,
é o erro mais caro.

---

## 3. Descanso mínimo — a restrição que confunde

Não é "espere N dias". É "o piquete só volta a ser apto quando a massa voltar ao alvo",
com um piso de segurança em dias.

```
apto[p,d] = 1  ⟺  massa[p,d] ≥ massa_entrada[p]
                  E  dias_desde_ultima_saida[p,d] ≥ descanso_min[cultivar]
```

`massa[p,d]` é **projetada** pelo módulo de sensoriamento (SAFER + graus-dia), não medida.
Por isso a confiança da estimativa entra no otimizador: horizonte longo tem massa mais
incerta, e o otimizador não deve tratar dia 28 com a mesma certeza do dia 2.

---

## 4. Fusão de lotes — último recurso

Acionada quando **nenhum** piquete está apto para um lote em urgência de saída.

Hierarquia de soluções, nesta ordem:

1. Estender ocupação atual (se ainda acima do resíduo)
2. Usar piquete marginalmente abaixo do alvo de entrada (aceitar sub-ótimo)
3. Aceitar violação temporária de resíduo, com alerta explícito
4. **Fusão de lotes**
5. Escalar ao produtor sem solução automática

Regras da fusão:
- Nunca automática. **Sempre com confirmação humana.**
- Só entre categorias compatíveis (não misturar bezerro com adulto)
- Após fusão, recalcular consumo do lote destino (soma dos pesos vivos) e seus dias de ocupação
- A mensagem **sempre** mostra as alternativas descartadas:
  *"alternativa: aceitar 3 dias de sobrepastejo no Piquete 4"*, *"alternativa: suplementar"*

Transparência aqui não é cortesia — é o que faz o produtor confiar no motor.

---

## 5. Progressão de implementação

**Não implementar CP-SAT direto.** Três estágios, cada um entregável:

### Estágio 1 — Heurística gulosa (F-009)
Ordena por urgência: quem precisa sair já > quem está no ponto > quem pode esperar.
Aloca ao melhor piquete apto disponível, escolhido nesta ordem: **(a)** apto por R3 e R11,
**(b)** melhor encaixe agronômico — o mais próximo do alvo de entrada, **(c)** menor `dist` a
partir do piquete atual do lote. O critério (c) é a distância entrando como **desempate**, não
como termo de objetivo: o guloso não tem função objetivo para ponderar (ADR-016).
Sem lookahead. **Já é infinitamente melhor que mapa NDVI.**

> **O que o guloso não faz, e é bom saber antes de prometer.** "Vale a pena esperar dois dias
> pelo piquete vizinho ficar pronto, em vez de mandar o lote para o piquete distante hoje?" é
> exatamente a pergunta que um algoritmo sem lookahead **não** responde. Ela só é resolvida de
> verdade no Estágio 3. Meio-termo barato, se o F-009 se mostrar curto demais na validação:
> como o F-008 já projeta massa para os próximos dias, o guloso pode considerar apto não só
> `apto[p,hoje]` mas `apto[p, hoje+k]` para `k ≤ 2`, e comparar "esperar k dias" com "ir agora
> para o mais distante". É um lookahead de horizonte fixo, não busca — não vira CP-SAT
> disfarçado. **Não** entra no F-009 sem ADR; registrado como **Q15** no `11`.
Serve de baseline para medir os estágios seguintes.

### Estágio 2 — Busca local (F-020, pós-MVP)
Parte da solução gulosa, aplica trocas (swap de destino, adiar/antecipar movimentação),
aceita se melhora o objetivo. Simulated annealing se necessário.

### Estágio 3 — CP-SAT com horizonte rolante (F-021, alvo final)
Otimiza 14–30 dias à frente, **executa só os primeiros dias, re-otimiza no dia seguinte**.

Por que horizonte rolante e não otimizar a temporada inteira: a incerteza da previsão de
crescimento cresce com o tempo. Otimizar 90 dias é otimizar ruído. Otimiza-se 3–4 semanas,
executa-se a primeira, e re-otimiza com dados novos.

---

## 6. Saída legível

O otimizador produz estrutura; o módulo `delivery` produz português. Formato-alvo:

```
🌱 SeuGado — plano de quinta, 18/09

▸ Mover Lote Recria → Piquete 7
  Piquete 7 está em 88 cm (ponto da Mombaça: 90 cm)
  Previsão: 3 dias de pastejo
  Confiança: alta

▸ Piquete 3 precisa ser desocupado
  Está em 38 cm, resíduo mínimo é 40 cm

⚠️ Piquete 5: última imagem limpa há 11 dias
  Pode mandar uma foto? Ajuda a corrigir a estimativa.
```

Regras de redação:
- **Sempre o motivo junto da ordem.** "Mova" sem "porque" não constrói confiança.
- **Números em cm**, não em kg MS/ha. O produtor pensa em centímetros e tem a régua.
- **Nunca mostrar NDVI, ETf, backscatter.** São insumos internos.
- Um plano por mensagem, não uma mensagem por movimentação.

---

## 7. Testes obrigatórios

| Teste | O que verifica |
|---|---|
| Caso de regressão canônico | Reproduz os números de `05-PARAMETROS-CULTIVARES.md` |
| Mão de obra saturada | Com 1 funcionário e 5 urgências, agenda ≤ capacidade e prioriza corretamente |
| Sem piquete apto | Aciona a hierarquia do §4 na ordem certa |
| Lote indissolúvel | Nunca aparece em proposta de fusão |
| Dia não preferencial | Nenhuma movimentação agendada fora da rotina |
| Resíduo | Nenhuma solução viável deixa `massa < residuo_min` |
| Determinismo | Mesma entrada → mesma saída (seed fixa no CP-SAT) |
| Degradação graciosa | Com confiança baixa em todos os piquetes, ainda produz plano + alertas |
