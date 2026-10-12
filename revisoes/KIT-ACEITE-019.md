# KIT-ACEITE-019 — Motor diário guloso e catálogo de alertas

> Só para o testador. **Nunca** colar no Muse Code. Conformidade em `tests/conformance/test_spec_019.py`.

## Checagens estruturais
- `gerar_plano(estado, fazenda, agora, plano_id) -> PlanoManejo` — assinatura idêntica.
- `TipoAlerta`: os 9 membros antigos com os mesmos valores + `abaixo_da_saida`, `pronto_em`,
  `sobra_de_capim`, `falta_de_capim`. Nenhum outro.
- `Alerta`: últimos campos `acao: str = ""` e `modulo_id: UUID | None = None`. Nenhum outro campo novo.
- Plano JSON gravado antes (sem `acao`/`modulo_id` nos alertas) → `plano_de_dict` funciona; `acao == ""`.
- `DiaSimulado` em `planner/alertas.py`: `frozen=True, slots=True`, 5 campos com os nomes da spec.
- `alertas.py` não importa `otimizador.py`. Nenhum dos dois importa `api/`, `persistencia/`,
  `delivery/`, `jobs/`, `sensing/`, `psycopg`.
- Cada arquivo ≤ 300 linhas. `__init__.py` vazios. Sem `MOCK`/`demonstração` no código.
- Constantes `0.9`, `1.2`, `1.2`, `0.8` com comentário `HIPOTESE-CALIBRAR`.
- `test_otimizador_mock.py` removido. Suíte inteira, `ruff` e `mypy` limpos.

## Caso canônico (o da spec)
Reproduzir: 1 movimentação L1 P1→P3 em 12/10, `dias_previstos == 7`; alertas exatamente
{`pronto_em` P2, `pronto_em` P5, `passando_do_ponto` P4, `passando_do_ponto` P5, `falta_de_capim` M1}.
Texto do `falta_de_capim` contém `49%`.

## Caso oculto 1 — capacidade e abaixo da saída
Segunda 12/10/2026, todos os dias de manejo, 1 funcionário × 60 animais/dia, sem módulos.
Marandu 30/15 cm, 110 kg/ha/cm, ef. 0,72, descanso mínimo 21, taxa 40 kg/ha/dia (14 dias).
- A: 1,0 ha, 15 cm, com L1 (40 animais, consumo 400)
- B: 1,0 ha, 14 cm, com L2 (30 animais, consumo 300)
- C: 3,0 ha, 35 cm, descanso 30 · D: 2,0 ha, 32 cm, descanso 30

Esperado:
- Dia 12/10: L2 (urgência 1) B→C. L1: 30+40 > 60 e já houve movimento → `capacidade_excedida` L1 em 12/10.
- Dia 13/10: L1 A→D (`altura_origem_cm == 10.3`, `altura_destino_cm == 32.4`).
- `abaixo_da_saida` em 12/10 para A (acao "Retirar o lote L1 hoje. Nenhum pasto…") e para B
  (acao "Retirar o lote L2 hoje e levar para o C.").
- `falta_de_capim` grupo None: oferta 40×7×0,72 = 201,6; demanda 700 → texto contém `29%`; rótulo "pastos sem módulo".
- Nenhum `pronto_em`, `passando_do_ponto`, `sem_piquete_apto`.

## Caso oculto 2 — fallback e distância pela praça
Mesmos parâmetros, 2 funcionários × 100. L (20 animais, consumo 200) em P1 (1 ha, 15 cm).
P2 e P3: 1 ha, 28 cm, descanso 30 (nenhum apto; ambos ≥ 0,9 × 30 = 27).
Centroides: P1 (−9,6000; −36,6000), P2 (−9,6020; −36,6000), P3 (−9,6100; −36,6000).
P1 e P2 bebem na praça Q (−9,6010; −36,6000); P3 sem praça.
Esperado: L P1→P2 em 12/10 (≈222 m contra ≈1,1 km), `motivo` com "o mais perto da entrada".
Em 18/10 P2 projeta 12,9 cm para 19/10 → L P2→P3 (P3 com 30,2 cm, apto). Logo nenhum `pronto_em`.
`falta_de_capim` grupo None: 40×3×0,72 = 86,4 / 200 → `43%`.

## Caso oculto 3 — sem dia de manejo
Só quarta (2) é dia de manejo; data base segunda 12/10. L (consumo 400) em P (1 ha, 17 cm).
Terça 13/10 P fica ≤ 15 cm → `sem_dia_de_manejo` com `lote_id` de L, data 13/10, acao
"Antecipar a troca do lote L para 13/10.". Nenhuma movimentação em seg/ter.
Na quarta 14/10 não há outro pasto → `sem_piquete_apto` de L em 14/10. `falta_de_capim` com `7%`.
Com `dias_preferenciais_manejo == ()`: o `sem_dia_de_manejo` da fazenda (ids None) **e** o de L em 13/10; zero movimentações; nenhum `sem_piquete_apto`.

## Propriedades
- Lote com módulo nunca vai para fora dele (gerar fazenda com 2 módulos e lote preso em M1).
- Determinismo: duas chamadas → `plano_para_dict` iguais.
- `capacidade <= 0` → `ValueError`.
- Todo alerta com `acao != ""`.

## Caso oculto 4 — lote maior que a equipe sem destino (pós-implementação, emenda do R5)
Segunda 12/10/2026, todos os dias de manejo, 1 funcionário × 50 animais/dia. Mesmos parâmetros
do caso 1 (30/15 cm, 110 kg/ha/cm, ef. 0,72, descanso mínimo 21, taxa 40), todos com 1 ha.
- Módulo M1 = {A, C}: A 14 cm com L_big (80 animais, consumo 500, `modulo_id` M1); C 20 cm, descanso 30.
- Módulo M2 = {B, D}: B 15 cm com L_small (20 animais, consumo 200, `modulo_id` M2); D 33 cm, descanso 30.

Esperado:
- L_big vem primeiro (urgência 1), tenta sozinho (80 > 50), não acha destino (C abaixo de 27 cm)
  → `sem_piquete_apto` de L_big em 12/10, sem gastar capacidade.
- A fila continua: L_small B→D em 12/10. **Única** movimentação do plano.
- `abaixo_da_saida` em 12/10 para A e B; `falta_de_capim` M1 com `12%` e M2 com `29%`.
- Nenhum `capacidade_excedida`, `pronto_em` ou `passando_do_ponto`.
