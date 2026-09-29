# RELATÓRIO-BASELINE-MACOS — verificação da base antes de qualquer fatia
**Data:** 27/09/2026 · **Veredicto:** reprovada (base divergente; nenhuma fatia verificada)

Este relatório não verifica uma fatia. É a parada prevista em `papeis/TESTADOR.md` §Bootstrap:
o ambiente foi montado nesta máquina e a contagem de testes divergiu do painel, então a
verificação de fatia foi interrompida antes de começar.

## Bootstrap executado
- `uv` ausente na máquina → `brew install uv` (0.12.19), `uv sync --group dev`.
- `.venv` criado do zero a partir de `uv.lock`. Interpretador resolvido: **Python 3.14.7**
  (`requires-python = ">=3.12"`, sem `.python-version` no repositório).

## Execução
- `ruff check .` → `All checks passed!`
- `ruff format --check .` → **9 arquivos seriam reformatados**, 52 já formatados
- `mypy` → `Success: no issues found in 60 source files`
- `pytest` → **457 passaram, 2 falharam, 13 pulados**

## Escopo
Árvore de trabalho sem alteração em `src/` ou `tests/` — nada de implementação pendente para
verificar. Não rastreado ao iniciar: `CLAUDE.md`, `papeis/` (do Arquiteto, commitados em
`docs:` próprio), `frontend-design/` (5 PNG de mockup, aguardando decisão do usuário) e
`.DS_Store` (lixo de macOS, não commitado).

## Defeitos na implementação
Nenhum defeito de lógica de produção identificado. As duas falhas são de ambiente, ambas em
arquivos de teste:

1. `tests/conformance/test_spec_001_models.py:423`
   (`test_r6_lote_has_no_derived_values`) — a allowlist de atributos gerados pelo dataclass não
   prevê `__annotate_func__` e `__annotations_cache__`, introduzidos pelas anotações preguiçosas
   do **Python 3.14** (PEP 649). Falha do teste, não do `Lote`.
2. `tests/conformance/test_spec_013_satelite_sentinel2.py:354`
   (`test_inicializar_earth_engine_missing_env_raises_runtime_error`) — o teste apaga só
   `SEUGADO_GEE_PROJECT` e espera a mensagem citando essa variável, mas
   `src/seugado/sensing/earth_engine.py:40-42` checa `SEUGADO_GEE_SERVICE_ACCOUNT_JSON`
   primeiro. O teste só passa numa máquina onde a credencial esteja exportada — **defeito de
   isolamento do teste**, dependente de ambiente.

## Achados fora da implementação
1. **[TRIAGEM] Versão de Python não fixada.** `uv` escolheu 3.14.7; `[tool.ruff] target-version`
   diz `py312`. A base histórica foi construída em outro interpretador. Fixar via
   `.python-version` (ou `requires-python` mais estreito) é decisão do terminal 1 — e determina
   se o achado nº 1 acima se resolve editando o teste ou voltando para 3.12.
2. **[TRIAGEM] Cinco fatias commitadas com o portão das quatro ferramentas aberto.** Os
   9 arquivos que `ruff format --check` recusa já estão em `HEAD`:
   `src/seugado/sensing/clima.py`, `earth_engine.py`, `ingestao.py`,
   `tests/conformance/test_spec_011_clima.py`, `test_spec_013_satelite_sentinel2.py`,
   `test_spec_015_admin_agenda.py`, `test_spec_016_web_admin.py`,
   `tests/core/test_contratos.py`, `tests/sensing/test_ingestao.py`. O `ruff` do `uv.lock` é
   0.16.8, o mesmo que rodei — não é divergência de versão de ferramenta.
3. **[ARQUITETURA] O muro do ADR-011 não vigorou em F-MVP-011, 012, 013 e 015.** Cada um desses
   commits traz `src/` e `tests/conformance/` juntos, e a mensagem cita o kit de aceite
   (`c0cb2e3`, `1265d25`, `943c41c`, `1977987`). Pelo critério de `papeis/TESTADOR.md`
   §Checagem de escopo isso é violação grave: quem implementou tinha o kit à vista. Registro
   nominalmente; a suíte de conformidade dessas quatro fatias não vale como verificação
   independente.
4. **[TRIAGEM] `docs/11-ESTADO-ATUAL.md` está três fatias atrasado.** O painel diz
   "352 testes passando, 0 falhas, próxima F-MVP-011"; `HEAD` tem F-MVP-011, 012, 013, 015 e
   016 commitados e a suíte tem 457/2/13. O painel também declara ser mantido pelo
   "Antigravity", enquanto `CLAUDE.md` e `papeis/TESTADOR.md` o dão como exclusivo do Testador.
5. **[TRIAGEM] Faltam relatórios de cinco fatias já commitadas:** KIT-ACEITE-011, 012, 013, 015
   e 016 não têm `RELATORIO-*` correspondente. KIT-ACEITE-014 existe sem fatia iniciada.
6. **[TRIAGEM] Contagem esperada divergente entre documentos.** `papeis/TESTADOR.md` §Bootstrap
   espera "254 testes + 2 skipped"; `docs/11` espera 352 e 0 skipped; o real é 457 + 13 skipped
   (todos por ausência de `SEUGADO_TEST_DATABASE_URL` ou credencial GEE, comportamento correto
   pelo ADR-020). Nenhum dos dois números de referência serve mais como piso.
7. `.DS_Store` não está no `.gitignore`.

## Critérios não verificáveis
Nenhuma fatia foi verificada nesta sessão — a parada é deliberada. Os 13 testes pulados exigem
Postgres e credencial do Earth Engine, ausentes nesta máquina.
