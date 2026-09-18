# Kit de Aceite — SPEC-005 (migração e gateway de escrita de eventos)

> Uso interno do testador (Antigravity). **Nunca colar no Muse Code.**

## Checks estruturais
- [ ] Migração cria exatamente: `tipo_evento`, `origem_evento`, `fazenda` (`IF NOT EXISTS`),
      `evento`, `estado_piquete`, `estado_lote`, `leitura` — nada além disso, e nenhum `DROP`
- [ ] `evento` bate campo a campo com a ADR-018 (`docs/12`): mesmas colunas, mesmos tipos, os dois
      índices, `entidade_id` como coluna gerada, `UNIQUE (fazenda_id, chave_idempotencia)`,
      `REVOKE UPDATE, DELETE` e o trigger que impede `UPDATE`/`DELETE`
- [ ] 12 modelos Pydantic, um por valor de `TipoEvento`, com exatamente os campos da tabela do R2
      da spec — nem a mais nem a menos
- [ ] `registrar_evento` assina exatamente como o R3 da spec; não chama `conn.commit()`
- [ ] `pyproject.toml` ganhou só `psycopg[binary]` e `pydantic` — nenhuma outra dependência nova
- [ ] `mypy --strict` e `ruff check` limpos
- [ ] Nenhum import de `sensing`, `planner`, `api`, nem de `core.projecao`

## Caso dado na spec
`PayloadLeituraSatelite` com os valores do worked example valida. O mesmo payload com
`pixels_validos=0` levanta `pydantic.ValidationError`.

## Caso oculto 1 — composição inválida
`ComposicaoPayload(categoria="adulto", n_animais=0, peso_medio_kg=450)` levanta
`ValidationError` (viola `gt=0` em `n_animais`).

## Caso oculto 2 — payload de tipo errado
Validar `PayloadLoteDissolvido` contra um payload que só tem `entidade_id` (sem mais campos) —
deve passar, porque `lote_dissolvido` não tem campos além de `entidade_id`. Validar o mesmo
payload contra `PayloadLoteAlterado` (que exige `nome`, `composicao`, `indissoluvel`, `ativo`) —
deve falhar por campos ausentes.

## Caso oculto 3 — idempotência (requer banco; pular se `SEUGADO_TEST_DATABASE_URL` ausente)
Duas chamadas a `registrar_evento` com o mesmo `(fazenda_id, chave_idempotencia)` devem retornar o
mesmo `id`, e a tabela `evento` deve ter só uma linha para essa chave ao final. **Registrar
explicitamente no relatório se este caso rodou ou foi pulado** — não é aceitável reportar "passou"
quando na verdade pulou por falta da variável de ambiente.

## Fora do escopo do teste
Qualquer leitura de `evento` ou das tabelas derivadas (a spec é só de escrita); `piquete_distancia`;
qualquer comportamento de `core/projecao.py` (é de outra spec, testada por outro kit).
