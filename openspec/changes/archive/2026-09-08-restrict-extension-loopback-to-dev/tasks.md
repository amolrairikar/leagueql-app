## 1. Manifest — gate loopback matches on the build

- [x] 1.1 In `extension/manifest.config.ts`, move `http://localhost/*` and `http://127.0.0.1/*` out
      of the always-on `content_scripts.matches` and include them only when building for local
      development (`defineManifest((env) => ...)`, gated on `env.mode !== 'production'`).
- [x] 1.2 Kept the production matches limited to `https://leagueql.com/*` and `https://*.leagueql.com/*`.
- [x] 1.3 Scoped the dev matches to the dev-server port (`http://localhost:5173/*`,
      `http://127.0.0.1:5173/*`) instead of an any-port/any-path loopback wildcard.

## 2. Build wiring

- [x] 2.1 `extension/vite.config.ts` needs no change — `npm run build` runs `vite build` (mode
      `production`) and `npm run dev` runs `vite` (mode `development`), so `env.mode` resolves
      correctly.

## 3. Verification

- [x] 3.1 Production build (`npm run build`): `dist/manifest.json` `content_scripts[0].matches` =
      `['https://leagueql.com/*', 'https://*.leagueql.com/*']` — no loopback entries.
- [x] 3.2 Dev build (`vite build --mode development`): matches include
      `http://localhost:5173/*` and `http://127.0.0.1:5173/*`; production artifact rebuilt afterward.

## 4. Quality gates

- [x] 4.1 `tsc --noEmit` (run as part of `npm run build`) passes.
- [x] 4.2 `openspec validate --all` passes.
