# Arquitetura e Stack — SeuGado

Restrição mestre: **custo R$ 0,00 até o fim do MVP.** Toda escolha cabe em camada gratuita
ou licença aberta.

Segunda restrição, igualmente importante: **o código é escrito por um agente de modelo
barato e contexto curto (Muse Code / Muse Spark 1.3).** Isso favorece stacks maduras,
com muita documentação pública e padrões previsíveis, sobre stacks elegantes mas raras.
Tecnologia obscura custa mais em retrabalho do agente do que economiza em elegância.

---

## 1. Stack escolhida

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem backend | **Python 3.12** | Único ecossistema geoespacial + científico + otimização maduro |
| API | **FastAPI** | Tipagem via Pydantic dá contrato explícito — agente barato erra menos |
| Dados geoespaciais | **Google Earth Engine** (Python API) | Processa na nuvem deles. Gratuito para uso acadêmico/não-comercial |
| Geometria local | **shapely**, **geopandas** | Padrão de facto |
| Otimização | **OR-Tools CP-SAT** (Google) | Gratuito, robusto, feito para scheduling com restrições |
| Banco | **PostgreSQL + PostGIS** via **Supabase** | Camada gratuita; PostGIS resolve geometria no banco |
| Auth | **Supabase Auth** | Já vem junto, zero código |
| Frontend | **React + Vite + TypeScript** | Máxima densidade de exemplos públicos |
| Mapa | **Leaflet + react-leaflet** | Mais simples que Mapbox e sem chave paga |
| Hospedagem front | **Vercel** (free) | Deploy por git push |
| Hospedagem API | **Fly.io** ou **Render** (free tier) | Avaliar em ADR na fatia de deploy |
| Jobs agendados | **GitHub Actions** (cron) | Gratuito, sem servidor, versionado |
| Mensageria MVP | **Telegram Bot API** | 100% gratuito, sem template aprovado, sem CNPJ |
| Mensageria futura | WhatsApp Cloud API | Atrás de uma interface abstrata desde o dia 1 |
| ML (gap-filling) | **scikit-learn** / **XGBoost** | Literatura de referência usa exatamente estes |
| Testes | **pytest** | Padrão |

### Decisões que exigem destaque

**Earth Engine em vez de baixar imagens.** Baixar e processar HLS localmente exigiria
storage e CPU que não cabem em camada gratuita. O Earth Engine processa do lado deles e
devolve só os números agregados por piquete — que é tudo o que precisamos. Reduz o
problema de "big data geoespacial" a "algumas centenas de floats por dia".
⚠️ Verificar em `[PESQUISA]` os termos atuais de uso não-comercial/acadêmico.

**Telegram antes de WhatsApp.** WhatsApp Cloud API exige CNPJ, Business Manager verificado,
templates aprovados, e a partir de 01/10/2026 passa a cobrar mensagens de serviço.
Telegram é gratuito e sem burocracia. A lógica de decisão não muda — só o adaptador de canal.
Para a demo, Telegram é canal técnico real; WhatsApp entra quando houver orçamento.

**OR-Tools CP-SAT.** É a escolha mais forte do projeto do ponto de vista de Computação.
Resolve exatamente a classe do problema (atribuição com restrições temporais e de recurso),
é gratuito, e tem bom desempenho sem exigir doutorado em pesquisa operacional.

---

## 2. Módulos e fronteiras

Regra: **cada módulo é trabalhável isoladamente.** Uma fatia deve tocar 1–2 módulos,
nunca todos. Isso é o que impede o contexto de crescer sem controle.

```
src/seugado/
├── core/           # entidades e regras puras. SEM I/O, SEM rede, SEM banco.
│   ├── models.py         # Piquete, Lote, Cultivar, Manejo, Evento
│   ├── forragem.py       # massa↔altura, consumo, dias de ocupação
│   └── regras.py         # apto para entrada? precisa sair? urgência?
├── sensing/        # sensoriamento remoto
│   ├── earth_engine.py   # cliente GEE, amostragem por geometria
│   ├── safer.py          # as 11 equações, funções puras
│   ├── clima.py          # ingestão climática, graus-dia, ET₀
│   └── gapfill.py        # modelo SAR→NDVI
├── planner/        # decisão
│   ├── estado.py         # projeção diária do estado dos piquetes
│   ├── otimizador.py     # CP-SAT
│   └── confianca.py      # cálculo de confiança
├── delivery/       # saída
│   ├── mensagem.py       # gera o texto em PT-BR
│   └── canais/           # telegram.py, whatsapp.py (interface comum)
├── api/            # FastAPI: rotas finas, só orquestram
├── jobs/           # pipeline diário
└── tests/
```

### A regra mais importante: `core/` é puro

`core/` não importa nada de `sensing/`, `planner/`, `api/` ou banco. Só recebe dados
e devolve dados. Consequências, todas desejáveis:

- Testável sem mock, sem rede, sem banco
- Uma spec sobre regra de forragem carrega **só** `core/` no contexto do agente
- O caso de regressão canônico (`05-PARAMETROS-CULTIVARES.md`) roda em milissegundos

---

## 3. Contratos entre módulos

Definir **antes** de implementar. São eles que permitem trabalhar módulos isoladamente.

```python
# sensing → planner
def estimar_massa_forragem(piquete_id: UUID, data: date) -> EstimativaForragem: ...

class EstimativaForragem:
    massa_kg_ms_ha: float
    taxa_acumulo_kg_ms_ha_dia: float
    altura_estimada_cm: float
    confianca: Literal["alta", "media", "baixa"]
    origem_ndvi: Literal["optico", "sintetico_sar", "interpolado"]
    dias_desde_imagem_limpa: int

# core → planner
def dias_ocupacao(
    massa_atual_kg_ms_ha: float,
    massa_residuo_kg_ms_ha: float,
    taxa_acumulo_kg_ms_ha_dia: float,
    area_ha: float,
    eficiencia_pastejo: float,
    consumo_lote_kg_ms_dia: float,
) -> float: ...

# planner → delivery
class PlanoManejo:
    data_geracao: date
    horizonte_dias: int
    movimentacoes: list[Movimentacao]
    alertas: list[Alerta]
    pedidos_validacao: list[PedidoFoto]

class Movimentacao:
    data: date
    lote_id: UUID
    piquete_origem_id: UUID | None
    piquete_destino_id: UUID
    dias_previstos: int
    motivo: str          # texto em PT-BR, legível pelo produtor
    confianca: str
```

**Regra para o Muse Code:** nunca alterar um contrato. Se uma spec parecer exigir mudança
de contrato, isso é sinal de spec errada — voltar ao chat de arquitetura.

---

## 4. Event sourcing

Tudo que acontece vira um evento imutável. O estado atual é **derivado**, nunca editado.

```sql
CREATE TABLE eventos (
  id            UUID PRIMARY KEY,
  fazenda_id    UUID NOT NULL,
  tipo          TEXT NOT NULL,
  ocorrido_em   TIMESTAMPTZ NOT NULL,
  registrado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload       JSONB NOT NULL,
  origem        TEXT NOT NULL   -- 'produtor' | 'sistema' | 'satelite' | 'sar_inferido'
);
```

Tipos de evento: `piquete_criado`, `piquete_alterado`, `lote_criado`, `lote_alterado`,
`lote_dissolvido`, `manejo_recomendado`, `manejo_confirmado`, `manejo_recusado`,
`manejo_divergente`, `leitura_satelite`, `foto_validacao`, `parametro_alterado`.

Por que vale o esforço arquitetural:
- **Recálculo é trivial** — reprocessa os eventos. O usuário mexeu num lote? Recalcula tudo.
- **Auditoria completa** — dá para responder "por que o sistema recomendou isso em 12/03?"
- **Debug do otimizador** — reproduz o estado exato de qualquer dia
- **Aprendizado** — `manejo_divergente` é o dado mais valioso do sistema:
  é onde o produtor discordou da máquina

---

## 5. Modelo de dados essencial

```
fazenda      (id, nome, timezone, funcionarios_disponiveis,
              manejos_por_funcionario_dia, dias_preferenciais_manejo[])
piquete      (id, fazenda_id, nome, geometria GEOMETRY(Polygon,4326),
              area_ha, cultivar_id, ativo)
cultivar     (id, slug, parametros JSONB)        -- espelha 05-PARAMETROS
lote         (id, fazenda_id, nome, indissoluvel BOOL, ativo)
lote_composicao (lote_id, categoria, n_animais, peso_medio_kg)
leitura      (id, piquete_id, data, ndvi, origem, pct_nuvem,
              pixels_validos, massa_kg_ms_ha, taxa_acumulo, confianca)
plano        (id, fazenda_id, gerado_em, horizonte_dias, payload JSONB)
eventos      (ver §4)
```

Geometria em **EPSG:4326** (lat/lon) para armazenamento; reprojetar para métrico
ao calcular área e buffer.

---

## 6. Pipeline diário (GitHub Actions)

```yaml
# .github/workflows/pipeline-diario.yml
on:
  schedule:
    - cron: '0 9 * * *'   # 06:00 America/Fortaleza (UTC-3)
  workflow_dispatch:       # permite rodar manualmente
```

Passos: ingestão satélite → ingestão clima → SAFER → projeção de estado →
(se dia de planejamento) otimizador → envio de mensagem.

Segredos (chaves GEE, Supabase, Telegram) em GitHub Secrets. **Nunca no repositório.**

---

## 7. Restrições de codificação para o agente

Estas regras existem porque o agente programador é barato e de contexto curto.
Elas entram em toda spec.

1. **Type hints obrigatórios** em toda função pública. O tipo é metade da spec.
2. **Funções puras em `core/` e `sensing/safer.py`.** Sem I/O, sem estado global.
3. **Sem classe quando função basta.** Abstração prematura confunde agente barato.
4. **Sem framework de DI, sem metaprogramação, sem decorators exóticos.**
5. **Unidade no nome da variável.** `massa_kg_ms_ha`, não `massa`. `area_ha`, não `area`.
   Esta regra sozinha elimina uma classe inteira de bug.
6. **Um arquivo, uma responsabilidade.** Arquivo acima de ~300 linhas é sinal de fatia larga demais.
7. **Sem novas dependências** fora das listadas em §1 sem ADR.
8. **Toda função de cálculo agronômico tem teste** com valor esperado vindo de
   `05-PARAMETROS-CULTIVARES.md`.
9. **Nomes de domínio em português; comentários e docstrings em inglês.** `massa_forragem`,
   `piquete`, `lote` ficam em português porque traduzir cria ambiguidade (*paddock* vs
   *plot* vs *field*). Texto exibido ao produtor: português. Docstring e comentário: inglês.
10. **`__init__.py` sempre vazio.** Nenhum re-export. Importação sempre do módulo concreto
    (`from seugado.core.forragem import dias_ocupacao`). Dois caminhos de import para o
    mesmo símbolo contradizem o princípio de nome canônico único e convidam import circular.
11. **Nunca comparar membro de enum com outro tipo de enum.** `StrEnum` compara como string:
    `Confianca.ALTA == QualidadeBase.ALTA` é `True` **em runtime**. O `mypy` em modo estrito
    acusa (`comparison-overlap`), então a defesa estática existe — mas ela desaparece em
    qualquer caminho não tipado. Comparar sempre dentro do mesmo enum; usar `.value` apenas
    na fronteira (banco, JSON). Teste que verifica essa igualdade de propósito deve carregar
    `# type: ignore[comparison-overlap]` com comentário explicando.
12. **Entidade nunca é chave de dicionário.** Usar o `id`. `Piquete` com geometria levanta
    `TypeError` porque `dict` não é hasheável.

---

## 8. Ambiente de desenvolvimento

- Repositório: `C:\code\seugado`, visto do WSL Ubuntu como `/mnt/c/code/seugado`.
  Versionado com git desde a fundação (commit `73ff3af`). Um commit por fatia,
  mensagem `F-NNN: <título>`. O diff do commit é o que o testador revisa.
- Layout (ADR-013): `docs/` para a base de conhecimento, `src/seugado/` para o pacote
  (src-layout), `tests/core/` e `tests/conformance/`, `specs/`, `revisoes/`.
  Na raiz ficam só `README.md`, `CLAUDE.md` e os arquivos de configuração.
- **O Windows hospedeiro não tem Python.** Todo comando roda no WSL, nunca no PowerShell.
- `.venv` criada com `uv`. Instalar: `uv sync --group dev`.
- `pyproject.toml` declara Python >= 3.12 e o grupo `dev`: pytest, ruff, mypy (`strict`).
  Markdown está fora do escopo do ruff (`extend-exclude`), porque ele reformatava blocos
  de código dentro dos documentos `00`–`12`.
- `uv.lock` **é versionado**: isto é aplicação, não biblioteca, e o pipeline diário roda em
  GitHub Actions — build reproduzível depende do lock estar no repositório.
- Verificação padrão antes de entregar ao testador:
  `uv run ruff check .` · `uv run mypy` · `uv run pytest`.
