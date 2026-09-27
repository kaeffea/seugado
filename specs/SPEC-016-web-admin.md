# SPEC-016 — Web shell for admins: farm selector, clients page, updated contract types

## Context
The web app is used only by the team (admins), never by farmers. An admin logs in, picks one
of the registered farms in a selector, and every page (map, cattle groups, weekly plan, farm
settings) works on that selected farm. There is no farmer onboarding. This spec adapts the
shared front-end shell: contract types, the selected-farm context, route protection, the top
bar with the selector, and the routes.

## Domain vocabulary
- `cliente` — the farmer. `fazenda` — farm. `lote` — cattle group. `plano` — weekly plan.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation.

## Files to create or modify (all under `frontend/src/`)
- MODIFY `lib/tipos.ts`, `lib/fazenda.tsx`, `componentes/RotaProtegida.tsx`,
  `componentes/Layout.tsx`, `App.tsx`
- CREATE `paginas/Clientes.tsx` (placeholder)
- DELETE `paginas/Onboarding.tsx`

## Requirements

### R1 — `lib/tipos.ts`
Replace these declarations (everything else in the file stays exactly as it is):
```ts
export type Categoria = "bezerro" | "bezerra" | "novilho" | "novilha" | "vaca" | "boi" | "touro";

export interface Cliente { id: string; nome: string; telefone: string | null; observacoes: string | null; }

export interface Fazenda {
  id: string; cliente_id: string | null; cliente_nome: string | null;
  nome: string; timezone: string;
  funcionarios_disponiveis: number; animais_por_funcionario_dia: number;
  dias_preferenciais_manejo: number[];            // 0 = segunda … 6 = domingo
  envio_plano_dia: number;                        // 0 = segunda … 6 = domingo
  envio_plano_hora: number;                       // 0 … 23, hora local da fazenda
}
export interface Me { usuario_id: string; email: string | null; }
```

### R2 — `lib/fazenda.tsx`
`FazendaProvider` exposes, through `useFazenda()`:
```ts
{ carregando: boolean; usuario: Me | null; fazendas: Fazenda[]; fazenda: Fazenda | null;
  selecionar: (id: string) => void; recarregar: () => Promise<void> }
```
- `recarregar`: without a Supabase session → `usuario = null`, `fazendas = []`. With a session:
  `api<Me>("/me")` then `api<Fazenda[]>("/fazendas")`.
- The selected farm id is kept in `localStorage` under `"seugado.fazenda_id"` (wrap every
  access in `try/catch`). After loading, `fazenda` = the stored id if it is in the list, else
  the first farm, else `null`.
- `selecionar(id)` stores the id and updates `fazenda`.
- Reload on Supabase auth state change (as today).

### R3 — `componentes/RotaProtegida.tsx`
While `carregando` → "Carregando…"; `usuario === null` → `<Navigate to="/login" replace />`;
otherwise `<Outlet />`. (No onboarding redirect.)

### R4 — `componentes/Layout.tsx`
Top bar: text "SeuGado · Admin"; a `<select>` listing `fazendas` as
`"{cliente_nome ?? "sem cliente"} — {nome}"`, value = selected id, `onChange` → `selecionar`;
links "Clientes e fazendas" (`/clientes`), "Mapa" (`/mapa`), "Lotes" (`/lotes`),
"Plano da semana" (`/plano`), "Fazenda" (`/configuracoes`); "Sair" button. Below it: if
`fazenda === null` and the current path is not `/clientes`, render
"Nenhuma fazenda selecionada. Cadastre uma em Clientes e fazendas." with a link to `/clientes`
instead of the `<Outlet />`; otherwise render `<Outlet />`.

### R5 — `App.tsx`
Routes: `/login` → `Login`; inside `RotaProtegida` and `Layout`: `/clientes` → `Clientes`,
`/mapa`, `/lotes`, `/plano`, `/configuracoes`; `/` and unknown → `<Navigate to="/mapa" />`.

### R6 — `paginas/Clientes.tsx`
Placeholder like the other pages: `<h1>Clientes e fazendas</h1>` and
"Em construção — responsável: Leandro".

## Constants and parameters
None.

## Testing — who does what
`npm run build` must pass. Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `npm run build` with zero TypeScript errors
- [ ] `tipos.ts` contains the R1 declarations verbatim and no `Onboarding` import remains
- [ ] Logged out → `/login`; logged in with no farm → message with link to `/clientes`
- [ ] The selected farm survives a page reload (localStorage)

## Worked example
An admin logs in; `/me` returns `{usuario_id, email}`; `/fazendas` returns two farms. The
selector shows "João da Silva — Fazenda Boa Vista" and "Maria Souza — Sítio Alegre"; choosing
the second stores its id, and the Mapa page (owned by another person) reads it from
`useFazenda().fazenda`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-016.md`.

## Out of scope
- Do NOT implement the Clientes page, the login form or any page content
- Do NOT call endpoints other than `/me` and `/fazendas`
- Do NOT add dependencies or a state-management library
