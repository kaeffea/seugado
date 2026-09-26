# KIT-ACEITE-007 — Eventos MVP

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `OrigemPeso` tem exatamente `PRODUTOR="produtor"`, `UA_TABELA="ua_tabela"`.
- `ComposicaoLote`: último campo `origem_peso`, default `OrigemPeso.PRODUTOR`; continua `frozen=True, slots=True`.
- `TipoEvento` tem 13 membros; `ALTURA_MEDIDA` é o último.
- `PAYLOAD_POR_TIPO` tem 13 entradas; todos os modelos com `extra="forbid"`.
- `PayloadLeituraSatelite` tem exatamente 9 campos (lista do R3.4); não tem `massa_kg_ms_ha`.
- `_ORDEM_CONFIANCA` existe e `combinar_confianca` não compara membros de enum entre si.
- `core/` não importa nada de `persistencia/`, `sensing/`, `planner/`, `api/`.

## Caso canônico
O exemplo resolvido da spec (P2 ocupado por L1 desde 24/09; P1 descansando; altura 28,0).

## Casos que a spec não mostra
1. `combinar_confianca(Confianca.BAIXA, Confianca.ALTA)` → `BAIXA`.
2. Duas `altura_medida` do mesmo piquete, datas 20/09 (30 cm) e 18/09 (25 cm) gravadas nessa ordem → fica 30 cm (a mais antiga não substitui).
3. `piquete_alterado` com geometria nova → `EstadoPiquete.geometria_geojson` é a nova.
4. Payload de piquete com `{"type": "Point", ...}` → `ValidationError`.
5. Conformance antiga: atualizar `tests/conformance/test_spec_005_persistencia.py` e `test_spec_006_projecao.py` para o novo formato de `leitura_satelite` (mudança intencional desta spec, ADR-023).
