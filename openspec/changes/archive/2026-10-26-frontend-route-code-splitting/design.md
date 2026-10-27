# Design

## Context

All pages are default-exported components imported statically in `app.tsx`; `APP_LAYOUT_ROUTES`
builds elements for the in-app routes inside `AppLayout`, which already wraps children in an
`ErrorBoundary` (reset on `location.pathname`) and `MembershipGuard`. A reusable `Spinner` exists.
`demo-data.json` is already dynamically imported (`lib/demo-api.ts`) and is its own 2 MB chunk, so
it needs no work. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Landing and public pages download no league-analytics code.
- Heavy vendor libraries land in separate, stable chunks.

**Non-Goals:**
- Prefetching on hover/idle, per-component (below page level) splitting, or restructuring the large
  page files.
- Changing the bundle's public paths or the CSP.

## Decisions

- **`React.lazy` per page in `app.tsx`.** Every page is a default export, so each import becomes
  `lazy(() => import('@/features/...'))` with no change to the page modules. Alternative: the React
  Router `lazy` route property; rejected because the app uses declarative `<Routes>`/`<Route>` and
  this avoids migrating to a data router.
- **Suspense placement.** One `<Suspense fallback={<Spinner/>}>` inside `AppLayout`, directly around
  `MembershipGuard`/children and inside the `ErrorBoundary`, so the sidebar/header stay mounted and
  a rejected lazy import is caught by the boundary and reset on navigation. A second `Suspense`
  wraps `<Routes>` for the public and standalone pages. Alternative: a single top-level boundary;
  rejected because it would blank the sidebar on every in-app navigation.
- **Which components stay eager.** Shell pieces rendered on every page (`Header`, `AppSidebar`,
  banners, `ProtectedRoute`, `MembershipGuard`) remain static imports. The landing page and the
  small public pages (changelog, privacy) also load lazily; the landing page is the largest single
  public file (~1,000 lines) and nothing else shares it.
- **Vendor chunking via `build.rollupOptions.output.manualChunks`.** Group `recharts`,
  `@clerk/*`, and `@opentelemetry/*` into named chunks. Because they change far less often than app
  code, they stay cached across deploys. Alternative: leave chunking to Rollup's defaults; rejected
  because shared vendor code would otherwise be duplicated or pulled into whichever page chunk
  imports it first. Exact groupings are confirmed against the build output (see tasks).
- **Chunk-load errors.** Rely on the existing `ErrorBoundary` rather than adding a bespoke
  reload-on-stale-chunk handler; its retry control and reset-on-navigation cover the case.

## Risks / Trade-offs

- [Stale chunk after a deploy: hashed filenames from the old build 404 for a user with an open tab]
  → surfaced by the `ErrorBoundary`; a reload fixes it. Cloudflare Pages serves the new build
  atomically.
- [Navigation latency: first visit to a page now incurs a chunk fetch] → small, cached afterward,
  and masked by the spinner; prefetching is a possible follow-up.
- [Too-fine vendor chunks add requests] → only three named groups, and everything else stays in
  Rollup's default split.
