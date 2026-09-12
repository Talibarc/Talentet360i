# Talent360i frontend

React 19, TypeScript and Vite, using the existing Lucide icons and Recharts stack. The shared navy/indigo/teal component system supports desktop and mobile role workspaces.

## Run

From the repository root, start the seeded mock backend as described in the root README, then:

```powershell
npm.cmd --prefix frontend ci --cache .cache/npm --no-audit --no-fund
npm.cmd --prefix frontend run dev -- --strictPort
```

Open http://127.0.0.1:5173 and select a synthetic role/function. No frontend environment secrets are required. `/api` proxies to the local backend on port 8000. Production hosting must supply that proxy; the build does not embed backend credentials.

## Check

```powershell
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Vitest and Testing Library exercise role navigation, dynamic IDs, answer privacy, submission payloads, source-bound TNI, evidence, manager revisions/comments, notifications, audit filtering, leader filters, engagement claims and API error handling. Tests use synthetic fixtures and mocked fetch, with no backend or Luna connection. `npm run format` formats source with Prettier.

`api.ts` centralizes requests, errors and demo headers. `hooks.ts` manages cancellable reads and loading states. `ui.tsx` provides shared cards, forms, dialogs and status components. Role pages use backend-calculated results and never reproduce scoring formulas. API authorization remains authoritative; hiding a navigation item is not the security boundary.

Source documents, missing Finance references, real scoring-policy acceptance, production identity/SSO and binary evidence upload remain outside the completed synthetic demo. See the root README and NEXT_STEPS.md.
