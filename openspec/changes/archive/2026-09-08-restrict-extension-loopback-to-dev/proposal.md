## Why

The Chrome extension's content script is injected on `http://localhost/*` and `http://127.0.0.1/*`
(any port, any path) per `extension/manifest.config.ts`, and these loopback match patterns ship in
the **published** extension. The content script's only gate on releasing the user's ESPN `SWID` /
`espn_s2` cookies is that the page origin appears in `content_scripts.matches` — there is no nonce,
handshake, or user gesture (security finding **SEC-03**).

Loopback is not a trust boundary: any web app served from `localhost`/`127.0.0.1` on the victim's
machine (a co-running local service, a malicious local dev dependency, or adware serving a local
page) can post the request message and receive the user's live ESPN session cookies — full ESPN
account session credentials. The production origins (`https://leagueql.com`, `https://*.leagueql.com`)
are correctly restricted; the loopback wildcard is the exposure, and it only exists to support the
local Vite dev server.

## What Changes

- **Remove `http://localhost/*` and `http://127.0.0.1/*` from the published (production) manifest.**
  The shipped extension's `content_scripts.matches` contains only LeagueQL production origins.
- **Add loopback matches only in a dev build**, via a build-time flag / separate dev manifest, so
  local development against the Vite dev server keeps working while the published artifact carries no
  loopback exposure. Scope the dev matches as narrowly as practical (prefer the specific dev port
  over an any-port/any-path wildcard).

## Impact

- Specs: `extension/espn-cookie-autofill` (ADDED "Production manifest excludes loopback origins").
- Code/config: `extension/manifest.config.ts` (gate loopback matches on a dev build flag),
  `extension/vite.config.ts` / build scripts as needed to distinguish dev vs. publish builds.
- Tests/verification: assert the production-built manifest's `content_scripts.matches` contains only
  LeagueQL origins and no `localhost`/`127.0.0.1` entries; confirm a dev build still injects on the
  dev origin. No runtime behavior change on production LeagueQL pages.
