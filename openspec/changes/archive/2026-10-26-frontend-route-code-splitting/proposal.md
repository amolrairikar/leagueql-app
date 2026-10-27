# Proposal

## Why

`frontend/src/app/app.tsx` statically imports every page (about 20), so the built entry chunk is
~1.58 MB. Every visitor, including someone who only opens the landing page, downloads and parses the
whole app (recharts, the OpenTelemetry stack, Clerk UI, and the large league-analytics pages) before
anything renders. This slows first load, most noticeably on mobile.

## What Changes

- Load each route's page component on demand (`React.lazy`) so a visit downloads only the code for
  the page being viewed.
- Show the existing spinner while a route's code is loading, keeping the app chrome (sidebar,
  header, banners) mounted for in-app pages.
- Surface a failed chunk load through the existing error boundary, which already resets on
  navigation.
- Split heavy vendor libraries (recharts, Clerk, OpenTelemetry) into their own long-cacheable
  chunks via the Vite build config so they are fetched only when needed and survive app deploys.
- No change to routes, URLs, or page content.

## Capabilities

### New Capabilities
- `frontend/route-code-splitting`: pages load on demand with a loading fallback, and a failed load
  is surfaced rather than leaving a blank screen.

### Modified Capabilities

## Impact

- `frontend/src/app/app.tsx` (lazy page imports, `Suspense` boundaries), `frontend/vite.config.ts`
  (`build.rollupOptions` chunking).
- Frontend component tests: add a route-loading scenario beside `frontend/src/app/__tests__/`.
- No backend, API, infrastructure, or dependency changes. The Cloudflare Pages `_headers` CSP is
  unaffected (same-origin scripts).
