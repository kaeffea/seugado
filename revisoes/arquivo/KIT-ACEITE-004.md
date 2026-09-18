# Kit de Aceite — SPEC-004 (Regras de manejo)

> Uso exclusivo do testador (Antigravity). Nunca colar no Muse Code.

## Checks estruturais

- [ ] `ResolucaoParametros` é `@dataclass(frozen=True, slots=True)` com exatamente os campos
      `parametros: ParametrosRegime | None` e `faltantes: tuple[str, ...]`
- [ ] Sem `__post_init__`, `__hash__` customizado ou `__all__` em `regras.py`
- [ ] Nenhuma função pública além de `resolver_parametros`, `apto_para_entrada`,
      `precisa_sair`, `urgencia`, `descanso_cumprido`
- [ ] `regras.py` importa só de `seugado.core.models` e da stdlib — nenhum import de
      `sensing`, `planner`, `delivery`, `api`, ou biblioteca de banco
- [ ] `regras.py` tem no máximo 300 linhas
- [ ] Nenhuma dependência nova em `pyproject.toml`
- [ ] Assinaturas exatas das 5 funções conforme SPEC-004 (nomes de parâmetro incluídos)

## Caso canônico (com tolerância)

Cultivar com um único bloco rotacionado: `altura_entrada_cm=90.0`, `altura_saida_cm=40.0`,
sem bloco contínuo.

| Chamada | Esperado |
|---|---|
| `resolver_parametros(cultivar, ROTACIONADO)` | `parametros` = o bloco acima, `faltantes == ()` |
| `resolver_parametros(cultivar, CONTINUO)` | `parametros is None`, `faltantes == ("altura_maxima_cm", "altura_minima_cm")` |
| `apto_para_entrada(88.0, bloco, descanso_cumprido=True)` | `False` |
| `apto_para_entrada(90.0, bloco, descanso_cumprido=True)` | `True` |
| `apto_para_entrada(90.0, bloco, descanso_cumprido=False)` | `False` |
| `precisa_sair(38.0, bloco)` | `True` |
| `precisa_sair(41.0, bloco)` | `False` |
| `urgencia(38.0, bloco)` | `2.0` (tolerância ±0.001) |
| `urgencia(88.0, bloco)` | `-48.0` (tolerância ±0.001) |
| `descanso_cumprido(21, 21)` | `True` |
| `descanso_cumprido(20, 21)` | `False` |

## Casos ocultos (o Muse Code não viu estes números)

1. **Bloco parcial (Piatã-like).** Cultivar com bloco rotacionado presente mas
   `altura_saida_cm=None` (entrada com fonte, saída sem fonte — caso real registrado em
   `05-PARAMETROS-CULTIVARES.md`, Piatã). Esperado:
   `resolver_parametros(cultivar, ROTACIONADO)` → `parametros is None`,
   `faltantes == ("altura_saida_cm",)`. **Não** deve devolver o bloco parcial como se fosse
   utilizável.

2. **Fronteira exata de descanso com valor geral da literatura.**
   `descanso_cumprido(dias_desde_ultima_saida=21, descanso_min_dias=21.0)` → `True`
   (usa o valor geral de `05`, 21 dias, confiança alta — o limite inclui a igualdade).
   `descanso_cumprido(dias_desde_ultima_saida=0, descanso_min_dias=21.0)` → `False`.

3. **`ValueError` em uso indevido de bloco contínuo.** Bloco com
   `metodo=MetodoPastejo.CONTINUO`, `altura_maxima_cm=120.0`, `altura_minima_cm=60.0`.
   Chamar `apto_para_entrada`, `precisa_sair` ou `urgencia` com esse bloco deve levantar
   `ValueError` nos três casos — nenhum deve silenciosamente devolver `True`/`False`.

4. **Múltiplos blocos, mesma cultivar.** Cultivar com um bloco `CONTINUO`
   (`altura_maxima_cm=120.0`, `altura_minima_cm=60.0`) **e** um bloco `ROTACIONADO`
   completo (`altura_entrada_cm=90.0`, `altura_saida_cm=40.0`) na mesma tupla
   `parametros_por_regime`. `resolver_parametros(cultivar, MetodoPastejo.ROTACIONADO)` deve
   devolver o bloco rotacionado (não o contínuo, não confundir por posição no índice da
   tupla).

## Critério de aceite final
Todos os checks estruturais e todas as linhas das tabelas acima batem, com zero falhas em
`pytest tests/core/test_regras.py` e no rerun independente do testador.
