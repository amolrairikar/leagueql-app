# Tasks

## 1. Lazy-load route pages

- [x] 1.1 In `frontend/src/app/app.tsx`, replace the static page imports with `React.lazy` imports and wrap `AppLayout`'s page area and the top-level `<Routes>` in `Suspense` with the `Spinner` fallback; verify `npm run build:ci` succeeds and `dist/assets` contains separate per-page chunks
- [x] 1.2 Add the `frontend/route-code-splitting` scenarios under `frontend/src/app/__tests__/` (jest-cucumber feature + steps): spinner while loading with the sidebar still mounted, normal page after load, and error fallback when the import rejects then recovery on navigation; verify with `npx vitest run src/app`
- [x] 1.3 Run the existing component suite with `npm run test:run` and fix any test that assumed synchronous page rendering (use `findBy*`); verify the full suite is green

## 2. Vendor chunking

- [x] 2.1 Add `build.rollupOptions.output.manualChunks` to `frontend/vite.config.ts` for recharts, Clerk, and OpenTelemetry; verify with `npm run build:ci` that the entry chunk is substantially below the previous 1.58 MB and record before/after sizes in the PR description
- [x] 2.2 Confirm the landing page loads without requesting league-page or recharts chunks (check the network list in `npm run preview`, or the built `index.html` preload list); verify no recharts chunk is preloaded for `/`

## 3. Quality

- [x] 3.1 Run `npm run format:fix` and `npm run lint` from `frontend/` and verify both are clean
- [x] 3.2 Run `npx @fission-ai/openspec@latest validate --all` and verify no errors
