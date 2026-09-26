# KIT-ACEITE-010 — Esqueleto API e frontend

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `api/deps.py` sem `commit(` (grep); conexão fechada em `finally`.
- Os 5 arquivos de rota só têm docstring + `router = APIRouter(...)`.
- `frontend/src/lib/tipos.ts` idêntico ao bloco da spec (diff).
- `npm run build` sem erros; nenhuma dependência além das da precondição em `package.json`.

## Casos que a spec não mostra
1. `exigir_fazenda` com `fazenda_do_usuario` monkeypatchado para outra UUID → 403 "Sem acesso a esta fazenda".
2. `usuario_atual` com `Authorization: Token abc` → 401 sem chamar `httpx.get`.
3. `GET /saude` com `DATABASE_URL` ausente do ambiente → 200.
