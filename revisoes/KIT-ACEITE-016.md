# KIT-ACEITE-016 — Web admin

Uso exclusivo do testador (Antigravity). **Nunca** colar no Muse Code (ADR-011).

## Checagens estruturais
- `npm run build` sem erros; `paginas/Onboarding.tsx` não existe; nenhuma rota `/onboarding`.
- `tipos.ts`: blocos do R1 idênticos; demais tipos inalterados (diff com a versão anterior).
- Acesso ao `localStorage` dentro de `try/catch`.

## Casos que a spec não mostra
1. `localStorage` com id que não está mais na lista → seleciona a primeira fazenda.
2. `/fazendas` vazio → Layout mostra o aviso com link para `/clientes`, e `/clientes` abre normalmente.
3. Sem sessão → `/plano` redireciona para `/login`.
