# SPEC-010 — API and web front-end skeleton shared by the whole team

## Context
Four more people start coding tomorrow, each in their own files. To avoid merge conflicts and
guesswork, this spec creates the shared skeleton: the FastAPI application with one empty router
file per owner, the database-connection and authentication dependencies, and the React
front-end shell with routing, the Supabase login client, an authenticated `fetch` wrapper, the
TypeScript mirror of the API contracts and one placeholder page per owner.

## Domain vocabulary
- `fazenda` — farm. `piquete` — paddock. `lote` — cattle group. `plano` — weekly plan.
- `usuario` — a person logged in through Supabase Auth; owns exactly one fazenda in the MVP.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

**Precondition (already done before you start):** `frontend/` contains the default Vite
"react-ts" template with these packages installed: `react-router`, `@supabase/supabase-js`,
`leaflet`, `react-leaflet`, `@geoman-io/leaflet-geoman-free`, and dev `@types/leaflet`.
`pyproject.toml` already lists `fastapi`, `uvicorn[standard]`, `httpx` and `earthengine-api`.

## Files to create or modify
Python:
- CREATE `src/seugado/api/main.py`
- CREATE `src/seugado/api/deps.py`
- CREATE `src/seugado/api/auth.py`
- CREATE `src/seugado/api/rotas_fazenda.py`, `rotas_lotes.py`, `rotas_piquetes.py`,
  `rotas_plano.py`, `rotas_telegram.py` (stubs)
- CREATE `tests/api/test_main.py`
- CREATE `.env.example` (repository root)

Front-end (under `frontend/`):
- MODIFY `src/main.tsx`, `src/App.tsx`, `index.html` (title only)
- DELETE `src/App.css`, `src/index.css` and `src/assets/react.svg` if present
- CREATE `src/lib/supabase.ts`, `src/lib/api.ts`, `src/lib/tipos.ts`, `src/lib/fazenda.tsx`
- CREATE `src/componentes/Layout.tsx`, `src/componentes/RotaProtegida.tsx`
- CREATE `src/paginas/Login.tsx`, `Onboarding.tsx`, `Configuracoes.tsx`, `Lotes.tsx`,
  `Plano.tsx`, `Mapa.tsx` (placeholders)
- CREATE `src/estilo/tema.css`
- CREATE `vercel.json`, `.env.example`

## Requirements

### R1 — `api/main.py`
- `app = FastAPI(title="SeuGado API", version="0.1.0")`.
- CORS middleware: `allow_origins` = `os.environ.get("SEUGADO_CORS_ORIGINS",
  "http://localhost:5173").split(",")`, `allow_methods=["*"]`, `allow_headers=["*"]`.
- `GET /saude` returns `{"ok": true}` with no auth and no database access.
- `app.include_router(...)` for the five router modules, in this order: fazenda, lotes,
  piquetes, plano, telegram. No prefix is added here; each router declares full paths.
- Run command (document it in the module docstring):
  `uv run uvicorn seugado.api.main:app --app-dir src --reload`.

### R2 — `api/deps.py`
```python
def obter_conexao() -> Iterator[psycopg.Connection[Any]]:
    """Open one connection per request from DATABASE_URL and always close it."""

Conexao = Annotated[psycopg.Connection[Any], Depends(obter_conexao)]
```
- `psycopg.connect(os.environ["DATABASE_URL"])` with default (tuple) rows and
  `autocommit=False`. The dependency **never commits**: it yields the connection and closes it in
  `finally`. Uncommitted work is discarded on close. Callers commit explicitly.

### R3 — `api/auth.py`
```python
@dataclass(frozen=True, slots=True)
class UsuarioAtual:
    id: UUID
    email: str | None

def usuario_atual(authorization: Annotated[str | None, Header()] = None) -> UsuarioAtual: ...
Usuario = Annotated[UsuarioAtual, Depends(usuario_atual)]

def fazenda_do_usuario(conn: psycopg.Connection[Any], usuario_id: UUID) -> UUID | None: ...

def exigir_fazenda(fazenda_id: UUID, usuario: Usuario, conn: Conexao) -> UUID: ...
FazendaAutorizada = Annotated[UUID, Depends(exigir_fazenda)]
```
- `usuario_atual`: missing header or not starting with `"Bearer "` → `HTTPException(401)`.
  Otherwise `httpx.get(f"{SUPABASE_URL}/auth/v1/user", headers={"apikey": SUPABASE_ANON_KEY,
  "Authorization": authorization}, timeout=10.0)`; any status other than 200 → 401; on 200
  return `UsuarioAtual(id=UUID(body["id"]), email=body.get("email"))`. `SUPABASE_URL` and
  `SUPABASE_ANON_KEY` are read from the environment at call time.
- `fazenda_do_usuario`: `SELECT fazenda_id FROM fazenda_usuario WHERE usuario_id = %s`.
- `exigir_fazenda`: `fazenda_id` comes from the path. If `fazenda_do_usuario(...) != fazenda_id`
  → `HTTPException(403, "Sem acesso a esta fazenda")`; else return `fazenda_id`.

### R4 — Router stubs
Each of the five files contains only a module docstring naming its owner and
`router = APIRouter(tags=["<name>"])`. Owners: `rotas_fazenda` and `rotas_lotes` and
`rotas_plano` → Leandro; `rotas_piquetes` → Ezequiel; `rotas_telegram` → Leo.

### R5 — `.env.example` (root)
One variable per line, empty values, with a one-line comment above each group:
`DATABASE_URL`, `SEUGADO_TEST_DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`SEUGADO_CORS_ORIGINS`, `SEUGADO_GEE_PROJECT`, `SEUGADO_GEE_SERVICE_ACCOUNT_JSON`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`.

### R6 — Front-end shell
- `src/lib/supabase.ts`: `export const supabase = createClient(import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY)`.
- `src/lib/api.ts`:
  ```ts
  export class ErroApi extends Error { constructor(public status: number, public corpo: string) }
  export async function api<T>(caminho: string, opcoes: RequestInit = {}): Promise<T>
  ```
  Reads the session with `supabase.auth.getSession()`, calls
  `fetch(import.meta.env.VITE_API_URL + caminho, …)` adding `Content-Type: application/json`
  and `Authorization: Bearer <access_token>`; non-2xx → `throw new ErroApi(status, text)`;
  204 → `undefined`; otherwise `response.json()`.
- `src/lib/tipos.ts`: copy the TypeScript block in the section **API contract types** verbatim.
- `src/lib/fazenda.tsx`: `FazendaProvider` + `useFazenda()` returning
  `{ carregando: boolean; usuario: Me | null; fazenda: Fazenda | null; recarregar: () => Promise<void> }`.
  It calls `api<Me>("/me")` when a Supabase session exists and again on auth state change.
- `src/componentes/RotaProtegida.tsx`: while `carregando`, render "Carregando…"; no session →
  `<Navigate to="/login" />`; session but `fazenda === null` and the current path is not
  `/onboarding` → `<Navigate to="/onboarding" />`; else render `<Outlet />`.
- `src/componentes/Layout.tsx`: top bar with the text "SeuGado" and links "Mapa" (`/mapa`),
  "Lotes" (`/lotes`), "Plano da semana" (`/plano`), "Configurações" (`/configuracoes`), and a
  "Sair" button calling `supabase.auth.signOut()`; renders `<Outlet />` below.
- `src/App.tsx`: `BrowserRouter` wrapping `FazendaProvider`; routes: `/login` → `Login`;
  inside `RotaProtegida`: `/onboarding` → `Onboarding`, and inside `Layout`: `/mapa`, `/lotes`,
  `/plano`, `/configuracoes`; `/` and unknown paths → `<Navigate to="/mapa" />`.
- `src/main.tsx`: imports `leaflet/dist/leaflet.css`,
  `@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css` and `./estilo/tema.css`, renders `<App />`.
- Each page in `src/paginas/` exports a default component rendering an `<h1>` with the page
  name and a paragraph "Em construção — responsável: <owner>". Owners: Login, Onboarding,
  Configuracoes, Lotes, Plano → Leandro; Mapa → Ezequiel.
- `src/estilo/tema.css`: CSS custom properties on `:root` — `--cor-primaria: #2f6b3a;`,
  `--cor-fundo: #f7f6f2;`, `--cor-texto: #1d1d1b;`, `--cor-alerta: #b54708;`,
  `--cor-erro: #b42318;`, `--raio: 8px;`, `--fonte: system-ui, sans-serif;` and a `body` rule
  using them. (Placeholder palette; Leandro replaces it.)
- `index.html` title: `SeuGado`.
- `frontend/.env.example`: `VITE_SUPABASE_URL=`, `VITE_SUPABASE_ANON_KEY=`,
  `VITE_API_URL=http://localhost:8000`.
- `frontend/vercel.json`: `{"rewrites": [{"source": "/(.*)", "destination": "/"}]}`.

## API contract types
```ts
export type Confianca = "alta" | "media" | "baixa";
export type MetodoPastejo = "continuo" | "rotacionado";
export type Categoria = "bezerro" | "novilho" | "adulto";
export type SituacaoPiquete = "ocupado" | "descansando";

export interface Fazenda {
  id: string; nome: string; timezone: string;
  funcionarios_disponiveis: number; manejos_por_funcionario_dia: number;
  dias_preferenciais_manejo: number[];            // 0 = segunda … 6 = domingo
}
export interface Me { usuario_id: string; email: string | null; fazenda: Fazenda | null; }

export interface Cultivar {
  id: string; slug: string; nome: string;
  regimes_disponiveis: MetodoPastejo[]; calibrada: boolean; faltantes_calibracao: string[];
}
export interface GeoJsonPolygon { type: "Polygon"; coordinates: number[][][]; }
export interface Piquete {
  id: string; nome: string; geometria: GeoJsonPolygon; area_ha: number;
  cultivar_id: string; cultivar_nome: string; metodo_pastejo: MetodoPastejo;
  situacao: SituacaoPiquete; lote_atual_id: string | null; lote_atual_nome: string | null;
  ultima_altura_cm: number | null; ultima_altura_data: string | null;
}
export interface ParametroPendente {
  cultivar_id: string; cultivar_nome: string; metodo_pastejo: MetodoPastejo; faltantes: string[];
}
export interface ComposicaoItem {
  categoria: Categoria; n_animais: number; peso_medio_kg: number | null;
  origem_peso?: "produtor" | "ua_tabela";
}
export interface Lote {
  id: string; nome: string; indissoluvel: boolean; composicao: ComposicaoItem[];
  piquete_atual_id: string | null; piquete_atual_nome: string | null; desde: string | null;
  peso_vivo_total_kg: number; n_animais_total: number;
}
export interface Movimentacao {
  id: string; data: string; lote_id: string; lote_nome: string;
  piquete_origem_id: string | null; piquete_origem_nome: string | null;
  piquete_destino_id: string; piquete_destino_nome: string;
  altura_destino_cm: number; altura_entrada_alvo_cm: number;
  altura_origem_cm: number | null; altura_saida_alvo_cm: number | null;
  dias_previstos: number; motivo: string; confianca: Confianca; motivo_confianca: string;
}
export interface Alerta {
  tipo: string; data: string; texto: string; confianca: Confianca; motivo_confianca: string;
  piquete_id: string | null; lote_id: string | null;
}
export interface PedidoValidacao { piquete_id: string; piquete_nome: string; motivo: string; }
export interface ResumoPiquete {
  piquete_id: string; nome: string; situacao: SituacaoPiquete; lote_atual_nome: string | null;
  altura_hoje_cm: number | null; altura_entrada_alvo_cm: number | null;
  altura_saida_alvo_cm: number | null; confianca: Confianca; motivo_confianca: string;
  faltantes: string[];
}
export interface PlanoManejo {
  id: string; fazenda_id: string; data_geracao: string; data_inicio: string; horizonte_dias: number;
  movimentacoes: Movimentacao[]; alertas: Alerta[]; pedidos_validacao: PedidoValidacao[];
  piquetes: ResumoPiquete[];
}
```

## Constants and parameters
None (the palette is a placeholder, not a parameter).

## Validation rules
- `GET /saude` never touches the database.
- Any route using `Usuario` returns 401 without a valid Supabase token.
- Any route using `FazendaAutorizada` returns 403 for a farm the user does not own.

## Testing — who does what
Write your own tests in `tests/api/` with FastAPI's `TestClient`: `/saude` returns 200 and
`{"ok": true}`; `usuario_atual` returns 401 without a header (monkeypatch `httpx.get` for the
other cases). Keep them short. You will NOT be given a test file to copy, and you must not wait
for one.

Your tests are not the verification of record. A separate agent writes an independent
conformance suite in `tests/conformance/` and decides whether the work is accepted. Do not
create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `uv run uvicorn seugado.api.main:app --app-dir src` starts and `GET /saude` returns `{"ok": true}`
- [ ] `/docs` lists no routes other than `/saude` (the routers are empty)
- [ ] `api/deps.py` never calls `commit()`
- [ ] `npm run build` inside `frontend/` succeeds with zero TypeScript errors
- [ ] Opening `http://localhost:5173/mapa` without a session redirects to `/login`
- [ ] `src/lib/tipos.ts` matches the block above character for character
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run pytest` pass

## Worked example
A logged-in user without a farm opens `/lotes`: `FazendaProvider` calls `GET /me`, receives
`{"usuario_id": "…", "email": "a@b.c", "fazenda": null}`, and `RotaProtegida` redirects to
`/onboarding`. A request to `GET /fazendas/<other farm id>/lotes` (once Leandro implements it)
returns 403 because `exigir_fazenda` compares the path id with `fazenda_usuario`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-010.md`.

## Out of scope
- Do NOT implement any business endpoint (`/me`, piquetes, lotes, plano, telegram)
- Do NOT implement the login form, onboarding form, map or any real page content
- Do NOT add a CSS framework, UI kit, state-management or data-fetching library
- Do NOT add a connection pool or an ORM
- Do NOT verify JWTs locally (auth goes through Supabase's `/auth/v1/user`)
- Do NOT add dependencies beyond the ones listed in the precondition

## Style constraints
- Python 3.12, type hints on every public function; docstrings and comments in English
- TypeScript strict mode (the Vite template default); no `any`
- Domain nouns stay in Portuguese in both languages
- `__init__.py` files stay empty; maximum 300 lines per file
