[ARQUITETURA] Revisão pós-F-001: correções de método, contratos e documentos

> Colar este arquivo inteiro como primeira mensagem de um chat novo no Project.
> Modelo sugerido: Opus, esforço alto.

## Contexto

O Claude Code (testador) verificou a SPEC-001 (`seugado/core/models.py`).

- **Resultado:** aprovada. Os 13 critérios de aceite passam, com 156 testes passando e 1 pulado.
  - Uma suíte de conformidade independente foi criada em `tests/conformance/test_spec_001_models.py`.
  - O critério 12 (`pyproject.toml`) não pôde ser verificado, porque o arquivo não existe.
- **Implementação:** nenhum defeito.
- **Achados:** a revisão encontrou problemas de **método**, **contratos** e **documentos do Knowledge**. Eles estão listados abaixo.

## O que eu preciso de você

1. **Valide cada item.** Para cada ID, diga se concorda ou discorda e dê o porquê técnico. Se um item estiver errado, diga isso; não o aceite só porque veio do testador.
2. **Classifique cada item aceito** em uma destas categorias:
   - **DOC:** correção factual. Entregue o bloco pronto, informando o arquivo e se é substituição ou acréscimo.
   - **ADR:** decisão estrutural. Entregue a ADR pronta para colar no `12`.
   - **PESQ:** exige pesquisa. Não resolva aqui; encaminhe para um chat `[PESQUISA]`.
   - **SPEC:** vira trabalho para o Muse Code. Entregue a spec ou o esboço dela.
   - **ADIAR:** vale, mas pertence a outro chat já previsto. Informe qual.
3. **Priorize.** Primeiro o que bloqueia o F-002, depois o resto. Se não couber num chat só (regra 3 e ciclo de vida), resolva os itens 🔴 e emita o HANDOFF com a lista do que ficou pendente.
4. **Não reimprima documentos inteiros.** Entregue só os trechos que mudam.

---

## 🔴 Urgentes (bloqueiam ou contaminam a próxima fatia)

### U1 — Duas definições de "eficiência de pastejo" (bloqueia F-002) → provável PESQ + ADR

- **Onde:** `03` §6.2 e §6.4; `05` (`eficiencia_pastejo_default`); `02` (verbete "Eficiência de pastejo").
- **O que acontece:**
  - O `05` define `eficiencia_pastejo_default = 0,44` a partir de `1.760 ÷ 4.000`, ou seja, massa removida sobre a **massa total pré-pastejo**.
  - A fórmula do `03` §6.2 aplica a eficiência sobre **(massa_atual − massa_residuo)**.
  - Com 0,44 nessa fórmula, o caso canônico dá (4.000 − 2.240) × 5,81 × 0,44 ÷ (11,62 × 220) ≈ **1,8 dia, não 4**.
  - O próprio caso atribui todos os 1.760 kg ao consumo (11,62 kg/animal/dia = 2,42% do PV). Isso equivale a eficiência **1,0** sobre essa base, e o template do `09` já usa 1,0 por esse motivo.
  - O glossário define eficiência como a fração consumida da forragem disponível (40–50%, o resto é perdido por pisoteio).
- **O que decidir:**
  - Qual é a definição canônica e sobre qual base ela se aplica.
  - O nome de cada grandeza. Sugestão: separar `eficiencia_pastejo` de `taxa_utilizacao`.
  - Se o caso canônico serve para validar a eficiência ou só o consumo.
  - Corrigir `02`, `03` e `05` de forma coerente.

### U2 — O template `09` contradiz a SPEC-001 e a si mesmo → DOC

- A lista de arquivos do exemplo diz `MODIFY seugado/core/__init__.py (export new functions only)`. A SPEC-001 proíbe re-exports e o teste exige `__init__.py` vazio, então a próxima spec copiada do template quebra a regra. É preciso definir uma política única de `__init__.py`.
- O `INPUT` do teste de exemplo não tem `taxa_acumulo_kg_ms_ha_dia`, que é um parâmetro obrigatório da própria assinatura. Copiado assim, o teste dá `TypeError`.
- O exemplo exige considerar o crescimento durante a ocupação, mas `EXPECTED_DAYS = 4.0` só vale com crescimento zero. É preciso explicitar `taxa_acumulo = 0` no caso canônico.

### U3 — O programador recebe os testes prontos, e o testador duplica o trabalho → ADR + DOC (`08`, `09`)

- **Hoje:** a spec traz o arquivo de teste completo e o Muse o copia literalmente. O testador então precisa escrever outra suíte.
- **Evidência:** foram plantados defeitos, um por vez, em cópias do `models.py` (import proibido, `__post_init__`, `__hash__` próprio, enum com membro extra ou valor errado, classe não congelada, `__all__`, função extra). A suíte copiada pelo Muse **deixou passar quase todos**; a suíte independente pegou todos.
- **Risco no F-002:** se o Muse vê o número esperado, ele pode forçar o código a devolvê-lo.
- **Proposta:** dividir o que o planejador produz em dois artefatos.
  - **Spec para o Muse:** requisitos, exemplos ilustrativos e critérios. O Muse pode escrever testes próprios.
  - **Kit de aceite para o Claude Code:** casos com valores esperados e checagens estáticas. O Muse nunca vê o kit.
  - Atualizar `08` §1 e §7 (tabela de papéis e ciclo) e acrescentar ao `09` uma seção "Acceptance kit (tester only)".
- **Também:** criar no `08` um **template de relatório de conformidade**. Hoje ele é só citado, sem formato.

### U4 — Não há git nem `pyproject.toml`; o ambiente não está documentado → SPEC (F-000) + ADR de ferramentas

- **Sem git:** não há como verificar "o agente não tocou em arquivos fora da lista", e a revisão fica sem diff.
- **Sem `pyproject.toml`:** o critério "nenhuma dependência nova" não pode ser verificado, e o pytest não está declarado como dependência.
- **Ambiente:** a `.venv` foi criada pelo `uv` no WSL Ubuntu, e o Windows não tem Python. Isso não está escrito em lugar nenhum.
- **Proposta:** criar uma fatia **F-000 · Fundação do repositório**.
  - `git init` e um commit por fatia.
  - `pyproject.toml` com Python 3.12, pytest como dependência de desenvolvimento e configuração do pytest.
  - ruff e mypy/pyright em modo estrito.
  - Uma seção de ambiente no `06`.
  - ruff e mypy são dependências novas, então exigem ADR (`06` §7 regra 7).

---

## 🟠 Importantes (decidir antes das fatias indicadas)

### I1 — Os contratos do `06` §3 divergem do modelo implementado → ADR (antes do F-002/F-008)

- `EstimativaForragem.confianca` é `Literal["alta","media","baixa"]`, e `Movimentacao.confianca` é `str`. O modelo usa o enum `Confianca`.
- `PlanoManejo` usa `list[...]`, mas a SPEC-001 proíbe listas em entidades imutáveis e exige tuplas.
- Os contratos não dizem se são dataclasses congeladas.
- `Movimentacao` duplica quase todo o `Manejo`. É preciso decidir se é o mesmo conceito.
- O `06` §3 diz que contratos são imutáveis sem ADR, por isso isto precisa de ADR.

### I2 — `Cultivar` exige todos os parâmetros como `float`, mas o `05` exige recusar cultivar com `TODO-PARAM` → ADR (antes do F-002)

- Com os campos obrigatórios, uma cultivar incompleta nem chega a ser criada.
- **Decidir:** onde fica a recusa "com mensagem clara" (num carregador de cultivares? em qual fatia?) e se algum campo deve virar `float | None`.

### I3 — Lacunas no modelo de eventos → ADIAR para o `[ARQUITETURA] Schema de eventos` (antes do F-004)

Incluir na pauta daquele chat:

- **Status e eventos que faltam:**
  - Não há status nem evento para "confirmação por omissão em 24h com confiança reduzida" (F-013).
  - Não há eventos para: plano gerado, criação ou alteração de fazenda e de cultivar, e posição inicial do lote.
- **Estrutura do `Evento`:**
  - Não tem versão de schema do `payload`, número de sequência nem ID do agregado. Sem isso, a ordenação e a evolução dos eventos ficam frágeis.
  - O `payload` é um `dict` alterável dentro de uma classe congelada (a imutabilidade é rasa). Decidir se aceitamos por convenção ou usamos uma estrutura imutável.
  - Datas sem fuso horário são aceitas. Definir a política de timezone.

### I4 — Comportamentos das entidades que precisam de decisão explícita → ADR curta ou nota no `06`

- `Confianca.ALTA == QualidadeBase.ALTA` dá `True`, porque `StrEnum` compara como string. A separação de tipos só é garantida por um verificador de tipos (depende do U4).
- `Piquete` sem geometria pode ser chave de dicionário; com geometria, dá `TypeError`. Deixar registrado que entidades não são usadas como chave (usar o `id`).
- Como não há validação, uma `list` passada no lugar de `tuple` é aceita e fica alterável. Definir quem valida e em qual fatia.

### I5 — Números sem fonte nos próprios documentos → DOC

- **`07` §2:** os pesos `w1..w5` não têm fonte. Isso viola a regra 1, a menos que ela se aplique só a parâmetros agronômicos.
  - Deixar explícito o escopo da regra 1.
  - Criar uma categoria "hipótese de projeto, calibrar em ADR", já prevista antes do F-009.
- **`05`:** a tabela de alturas não tem coluna de fonte. Massai, Zuri e Tamani aparecem sem referência.

### I6 — O glossário permite dois nomes para a mesma coisa → DOC

- O `02` aceita `altura_saida_cm` **ou** `residuo_cm` em código, o que contraria o princípio de nome canônico único. Escolher um só.

---

## 🟡 Manutenção

- **M1 — O `11-ESTADO-ATUAL` está desatualizado.**
  - Marcar o F-001 como ✅ e atualizar a fase.
  - Corrigir "ADR-001 a ADR-008" (a ADR-009 já existe).
  - Registrar o handoff abaixo e a nova suíte de conformidade.
- **M2 — O `06` §7 item 9 tem redação confusa** ("inglês no código? Não — ..."). Reescrever de forma direta.
- **M3 — O Muse trocou o comentário `Monday=0 .. Sunday=6` por "Monday first", que ficou ambíguo.**
  - Esclarecer que a regra "nenhum literal numérico" vale para código, não para comentários.
  - Corrigir o comentário quando uma spec voltar a tocar o `models.py`, porque não vale uma spec só para isso.

## Handoff do F-001 (para o `11`)

```
**17/09/2026 — F-001 Modelo de domínio**
Feito: seugado/core/models.py (6 enums, 7 dataclasses frozen/slots) aprovado; 13/13 critérios.
Suíte independente em tests/conformance/ (149 testes). Ambiente: .venv (uv) no WSL Ubuntu.
Pendente: REV-001 (U1–U4 urgentes; U1 bloqueia F-002). pyproject.toml e git inexistentes.
Próximo: [ARQUITETURA] Revisão pós-F-001 → depois [PESQUISA] eficiência de pastejo.
```
