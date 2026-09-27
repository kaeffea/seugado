# KIT-ACEITE-015 — Admin, agenda e categorias

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `CategoriaAnimal`: 7 membros na ordem da spec; `ADULTO` não existe.
- `Fazenda`: ordem exata dos campos; `manejos_por_funcionario_dia` não existe em lugar nenhum de `src/`.
- `0003` aplicado: `cliente` existe com RLS; `fazenda` tem `cliente_id`, `animais_por_funcionario_dia`, `envio_plano_dia`, `envio_plano_hora`, `ultimo_envio_semanal`; `plano.status` com CHECK.
- `TipoAlerta` com 9 membros; `PassoPlano`, `DiferencaLote` frozen/slots.
- Conformance antiga (001, 004, 005, 006, 007, 008, 009, 010, 014A): atualizar para `vaca`/`boi`… e `animais_por_funcionario_dia` — mudança intencional (ADR-025).

## Caso canônico
30 touros sem peso → 562,5 kg e 405,0 kg MS/dia.

## Casos que a spec não mostra
1. `ComposicaoPayload(categoria="adulto", …)` → `ValidationError`.
2. `exigir_fazenda` com UUID inexistente → 404 "Fazenda não encontrada"; com fazenda existente de qualquer usuário → devolve o id.
3. Dois `UPDATE fazenda SET telegram_chat_id = 123` em fazendas diferentes → o segundo viola o índice único.
4. `consumo_lote` com 10 `novilha` de 337,5 kg → 74,25.
