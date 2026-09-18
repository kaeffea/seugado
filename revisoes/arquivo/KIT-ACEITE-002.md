# KIT-ACEITE-002 — SPEC-002 (parâmetro por regime em `models.py`)

**Nunca colar no Muse Code.** Este arquivo é só para o Claude Code (testador). Se houver
qualquer sinal de que o Muse viu este arquivo, relate como violação (`CLAUDE.md`, regras de
verificação).

## O que esta fatia mudou

`Cultivar` perdeu `altura_entrada_cm`/`altura_saida_cm` e ganhou
`parametros_por_regime: tuple[ParametrosRegime, ...]`. `Piquete` ganhou `metodo_pastejo`.
Dois nomes novos entraram no módulo: o enum `MetodoPastejo` e o dataclass `ParametrosRegime`.
Nada mais em `models.py` deveria ter mudado.

## Suíte independente existente precisa ser atualizada, não substituída

`tests/conformance/test_spec_001_models.py` é a suíte estrutural do módulo inteiro, escrita
via AST — ela não foi escrita só para a SPEC-001, ela testa `models.py` como um todo, e
`models.py` como um todo é o que está mudando. Ela **vai falhar** contra o código novo do Muse
se ficar como está, porque os dicionários `ENUMS` e `DATACLASSES` nela ainda descrevem o
schema antigo. **Atualize esse arquivo no lugar** — não crie um `test_spec_002_*.py` paralelo
que duplicaria toda a checagem estrutural que já existe para as sete entidades que não
mudaram. Mantenha o nome do arquivo (preserva histórico de diff); ajuste só a primeira linha
do docstring do módulo para não dizer que é só da SPEC-001 — pode dizer algo como "covers the
schema as of SPEC-001 and SPEC-002".

### Mudanças exatas em `tests/conformance/test_spec_001_models.py`

**`ENUMS`** — adicionar a entrada nova, na posição correta (a ordem do dicionário Python é a
ordem de iteração, e `EXPECTED_ORDER` depende dela):

```python
ENUMS = {
    "CategoriaAnimal": {"BEZERRO": "bezerro", "NOVILHO": "novilho", "ADULTO": "adulto"},
    "QualidadeBase": {"ALTA": "alta", "MEDIA": "media", "BAIXA": "baixa"},
    "MetodoPastejo": {"CONTINUO": "continuo", "ROTACIONADO": "rotacionado"},
    "Confianca": {"ALTA": "alta", "MEDIA": "media", "BAIXA": "baixa"},
    "StatusManejo": { ... },   # inalterado
    "OrigemEvento": { ... },   # inalterado
    "TipoEvento": { ... },     # inalterado
}
```

**`DATACLASSES`** — `Cultivar` e `Piquete` mudam de forma; `ParametrosRegime` entra como
entrada nova logo após `Fazenda`. Os demais (`ComposicaoLote`, `Lote`, `Manejo`, `Evento`)
ficam exatamente como estão hoje.

```python
DATACLASSES = {
    "Fazenda": [ ... ],  # inalterado
    "ParametrosRegime": [
        ("metodo", "MetodoPastejo", NO_DEFAULT),
        ("altura_entrada_cm", "float | None", NO_DEFAULT),
        ("altura_saida_cm", "float | None", NO_DEFAULT),
        ("altura_maxima_cm", "float | None", NO_DEFAULT),
        ("altura_minima_cm", "float | None", NO_DEFAULT),
        ("confianca", "Confianca", NO_DEFAULT),
        ("fonte", "str", NO_DEFAULT),
    ],
    "Cultivar": [
        ("id", "UUID", NO_DEFAULT),
        ("slug", "str", NO_DEFAULT),
        ("nome", "str", NO_DEFAULT),
        ("parametros_por_regime", "tuple[ParametrosRegime, ...]", NO_DEFAULT),
        ("densidade_kg_ha_por_cm", "float", NO_DEFAULT),
        ("temperatura_base_c", "float", NO_DEFAULT),
        ("rue_max_g_por_mj", "float", NO_DEFAULT),
        ("qualidade_base", "QualidadeBase", NO_DEFAULT),
    ],
    "Piquete": [
        ("id", "UUID", NO_DEFAULT),
        ("fazenda_id", "UUID", NO_DEFAULT),
        ("nome", "str", NO_DEFAULT),
        ("area_ha", "float", NO_DEFAULT),
        ("cultivar_id", "UUID", NO_DEFAULT),
        ("metodo_pastejo", "MetodoPastejo", NO_DEFAULT),
        ("geometria_geojson", "dict[str, Any] | None", None),
        ("ativo", "bool", True),
    ],
    "ComposicaoLote": [ ... ],  # inalterado
    "Lote": [ ... ],            # inalterado
    "Manejo": [ ... ],          # inalterado
    "Evento": [ ... ],          # inalterado
}
```

Confira: `EXPECTED_ORDER = list(ENUMS) + list(DATACLASSES)` passa a ter **quinze** nomes
(sete enums, oito dataclasses) — os testes que dependem dela (`test_ac2_module_defines_...`,
`test_r9_declaration_order`, `test_ac2_runtime_public_names_are_classes_or_imports_only`) não
precisam mudar de lógica, só herdam a lista nova.

**`_sample()`** — os builders de `Cultivar` e `Piquete` quebram porque a assinatura mudou.
Adicione também um builder para `ParametrosRegime` (ele agora é amostrado nos testes
genéricos de `DATACLASSES`, como frozen/slots e imutabilidade de campo):

```python
def _sample(name: str) -> typing.Any:
    comp = models.ComposicaoLote(models.CategoriaAnimal.ADULTO, 1, 1.0)
    regime = models.ParametrosRegime(
        models.MetodoPastejo.ROTACIONADO, 1.0, 1.0, None, None, models.Confianca.ALTA, "f"
    )
    builders: dict[str, typing.Callable[[], typing.Any]] = {
        "Fazenda": lambda: models.Fazenda(U, "f", "America/Fortaleza", 1, 1, (0,)),
        "ParametrosRegime": lambda: regime,
        "Cultivar": lambda: models.Cultivar(
            U, "s", "n", (regime,), 1.0, 1.0, 1.0, models.QualidadeBase.ALTA
        ),
        "Piquete": lambda: models.Piquete(U, U, "p", 1.0, U, models.MetodoPastejo.ROTACIONADO),
        "ComposicaoLote": lambda: comp,
        "Lote": lambda: models.Lote(U, U, "l", (comp,)),
        "Manejo": lambda: models.Manejo(...),   # inalterado
        "Evento": lambda: models.Evento(...),   # inalterado
    }
    return builders[name]()
```

**`test_ac5_exactly_seven_dataclasses`** — renomeie a asserção para **oito**
(`assert len(found) == 8`; renomear o nome do teste é opcional, o número interno não é).

**`test_ac4_tipo_evento_has_exactly_twelve_members`** — inalterado (não é sobre as entidades
que mudaram).

**Qualquer outro teste que itere `DATACLASSES` ou `ENUMS`** (`test_ac5_dataclass_is_frozen...`,
`test_ac6_...`, `test_ac10_...`, `test_r3_r8_fields_match_spec_exactly`, etc.) já é
parametrizado a partir desses dois dicionários — não precisa de mudança de lógica, só herda
as entradas novas automaticamente.

**Achado a preservar:** `test_finding_piquete_hashability_depends_on_geometry` constrói um
`Piquete` manualmente com posicionais (`models.Piquete(U, U, "p", 1.0, U, ...)`). A posição de
`geometria_geojson` mudou de sexto para sétimo argumento posicional porque `metodo_pastejo`
entrou antes dele — ajuste as duas chamadas posicionais desse teste
(`hash(_sample("Piquete"))` já usa `_sample`, então só a segunda chamada,
`models.Piquete(U, U, "p", 1.0, U, geometria_geojson=...)`, precisa ganhar
`models.MetodoPastejo.ROTACIONADO` como sexto posicional antes do kwarg de geometria).

**`test_finding_replace_creates_modified_copy`** usa `_sample("Piquete")` — nenhuma mudança
de código necessária, só passa a exercitar o `Piquete` novo automaticamente.

## Checagens estruturais (o ponto cego histórico — ADR-011)

Confirme, além da suíte parametrizada acima:

- `models.py` não importa nada de `sensing/`, `planner/`, `api/`, nem biblioteca de banco —
  a lista de imports permitidos não muda (`dataclasses`, `datetime`, `enum`, `typing`, `uuid`)
- `MetodoPastejo` e `ParametrosRegime` seguem exatamente o mesmo padrão das entidades
  existentes: `ParametrosRegime` é `@dataclass(frozen=True, slots=True)`, sem
  `__post_init__`, sem `__hash__` próprio, sem `__all__`, sem métodos
- `MetodoPastejo` tem exatamente dois membros, nem a mais nem a menos, com os valores exatos
  `"continuo"` e `"rotacionado"` — não `"contínuo"` (sem acento: o valor da string é uma chave
  técnica, o glossário em `docs/02` é que carrega a grafia acentuada para exibição)
- Nenhuma função pública nova em `models.py` além das sete entidades já existentes mais as
  duas novas
- `__init__.py` de `src/seugado/`, `src/seugado/core/`, `tests/` e `tests/core/` continuam
  vazios
- **Zero literal numérico e zero dígito dentro de qualquer string (inclusive docstring) em
  `models.py`.** Rode: nenhum caractere `0-9` deve aparecer dentro de aspas no arquivo.
  Comentário `#` pode ter dígito sem violar a regra (não é string literal), mas não deveria
  ter sido necessário nesta fatia.
- `models.py` continua abaixo de trezentas linhas
- `tests/core/test_models.py` foi atualizado (não deletado) e `pytest tests/core/` passa
  sozinho, isolado do resto da suíte

## Caso oculto — não mostrado na spec (ADR-011)

A spec mostra um `Cultivar` com uma tupla de **dois** blocos (`rotacionado`, `continuo`).
Construa, na sua suíte independente, um `Cultivar` cujo `parametros_por_regime` é uma tupla de
**zero** blocos (`parametros_por_regime=()`), e confirme:

- a construção **não levanta exceção** — célula vazia é estado representável, não é erro deste
  módulo (a recusa por `TODO-PARAM` é responsabilidade do F-003, não deste)
- `len(cultivar.parametros_por_regime) == 0`
- o `Cultivar` resultante continua `frozen` (tentar reatribuir `parametros_por_regime` levanta
  `FrozenInstanceError`, igual a qualquer outro campo)

Confirme também que passar uma **lista** em vez de tupla para `parametros_por_regime` não é
rejeitado em runtime (achado, não critério de aceite — este módulo não valida tipos, igual ao
`test_finding_types_are_not_enforced_so_lists_slip_in` já existente para `Fazenda`). Registre
como achado se quiser, mas não é motivo de reprovação.

## Caso canônico

Não há caso numérico de regressão nesta fatia — `models.py` é schema puro, sem cálculo. O
"caso canônico" aqui é estrutural: o exemplo de dois blocos do worked example da spec deve
funcionar exatamente como mostrado, e a checagem de campo-a-campo (`test_r3_r8_fields_match_spec_exactly`,
parametrizada) é o que cobre isso.

## Checagem de escopo

`git status` / `git diff --stat` devem mostrar **só** `src/seugado/core/models.py` e
`tests/core/test_models.py` no lado de produção. Se o Muse tiver tocado
`tests/conformance/`, `docs/`, `revisoes/` ou `specs/`, relate como violação — ele não deveria
ter tido acesso a esses caminhos pela spec, e a spec explicitamente proíbe.

## Formato do relatório

`revisoes/RELATORIO-FATIA-001B.md`, formato do `CLAUDE.md`. Cubra os critérios de aceite da
SPEC-002 (não copie os deste kit — os deste kit são as evidências, não os itens da tabela).
