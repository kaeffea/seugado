# SeuGado — Visão e Escopo

## Uma frase

Sistema que monitora pastagens por satélite e clima e entrega ao pecuarista a **ordem direta**
de qual lote de gado mover para qual piquete, por quantos dias — sem exigir que ele digite
dados de animais no dia a dia.

## O problema

O pecuarista brasileiro perde arrobas por duas falhas simétricas:

- **Sub-pastejo**: o capim passa do ponto ideal, lignifica, vira talo e material morto.
  Perde valor nutritivo e o animal ganha menos peso mesmo com pasto "sobrando".
- **Super-pastejo**: o lote fica além do resíduo mínimo, a planta perde área foliar,
  usa reserva de raiz para rebrotar, e o pasto degrada ao longo das estações.

A decisão que evita as duas é a mesma: **quando mover, para onde, e por quanto tempo.**
Hoje essa decisão é tomada no "olho do dono", ou com calendário fixo, que erra justamente
nas transições de estação — quando o crescimento do capim muda de ritmo.

## A tese

> Não disputamos o tempo administrativo do produtor.
> Transformamos dados aéreos complexos na decisão diária mais lucrativa da fazenda.

Três diferenciais que sustentam isso, nesta ordem de importância:

1. **Prescritivo, não descritivo.** A saída do sistema é uma frase em português com uma ordem
   de manejo, não um mapa de calor NDVI que o produtor precisa interpretar.
2. **Otimização real com restrições operacionais.** Alocação de lotes a piquetes respeitando
   mão de obra disponível, rotina de manejo do produtor e lotes indissolúveis. Nenhum
   concorrente pesquisado modela isso.
3. **Fricção assimétrica.** Configuração pesada uma vez; depois, só confirmações de um toque.

## Posicionamento contra os concorrentes

| Concorrente | O que faz bem | Onde o SeuGado ataca |
|---|---|---|
| **Pastu** | ERP pecuário completo + NDVI por satélite; ~420 clientes; parceria com frigoríficos | Entrega descritiva (mapas NDVI); só satélite óptico (cego em nuvem); foco em >800 cabeças |
| **iRancho** | BOS: registro por voz, offline, −85% no tempo de registro; 10 anos de mercado | Ela otimiza o *registro* de eventos de rebanho. Nós decidimos *manejo de pasto*. Camada diferente |
| **PastoAuto** | Monitoramento de pastagem por satélite, entrada sem hardware | Mesma limitação óptica; sem motor de otimização |
| **Halter / Nofence / Vence** | Cerca virtual por colar GPS, controle fino de pastejo | Hardware caro, não operam no Brasil. Nosso roadmap de longo prazo, não concorrência atual |

**Aviso de rota:** a Pastu recebeu aporte para expandir IA e sensoriamento remoto.
O gap "descritivo" dela é alvo móvel. Nosso fosso durável não é *ter* satélite — é o
**motor de otimização com restrições operacionais** e a **calibração local por fazenda**.

## Público

Do pequeno ao grande produtor. Porte **não é critério de escopo** — o sistema escala por
número de piquetes e lotes, não por tamanho de rebanho. Um sistema que funciona para 3
piquetes funciona para 80; o otimizador só fica mais valioso quando cresce.

## Fora de escopo (MVP)

Mudar qualquer item desta lista exige ADR. Não implemente, não planeje, não "deixe preparado".

- ❌ ERP zootécnico: cadastro individual de animal, brinco, pesagem, vacinação, genealogia
- ❌ Módulo financeiro, fluxo de caixa, custo de produção
- ❌ Rastreabilidade, integração com frigorífico, SISBOV
- ❌ Balanço nutricional completo (PB/FDN/digestibilidade) e recomendação de suplementação
- ❌ Hardware próprio: colar, sensor de campo, estação meteorológica, cerca virtual
- ❌ Drone proprietário (integração com drone comercial fica para pós-MVP)
- ❌ App nativo iOS/Android (web responsivo + bot de mensagem resolvem)
- ❌ Multi-fazenda / multi-tenant complexo (uma fazenda por conta no MVP)
- ❌ Previsão de preço de arroba, mercado, cotação

## Definição de pronto (MVP)

O MVP está pronto quando, para uma fazenda real com piquetes desenhados:

1. O sistema estima massa de forragem por piquete, semanalmente, sem intervenção humana.
2. O sistema emite um plano de manejo para os próximos 7 dias, respeitando mão de obra
   e dias preferenciais do produtor.
3. O produtor recebe o plano numa mensagem legível e confirma execução com um toque.
4. O sistema recalcula quando a confirmação chega (ou não chega).
5. Toda recomendação carrega um nível de confiança, e recomendações de baixa confiança
   pedem foto de validação opcional.

## Custo do desenvolvimento

**Meta: R$ 0,00 até o fim do MVP.** Toda escolha de stack, hospedagem, dado e serviço deve
caber em camada gratuita ou licença aberta. Investimento só após MVP validado.
Qualquer dependência paga proposta precisa de ADR justificando e uma alternativa gratuita avaliada.
