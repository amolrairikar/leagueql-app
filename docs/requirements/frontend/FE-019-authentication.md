# FE-019: Authentication & Protected Routes

## Description
Authentication is handled by Clerk. In-app analytics routes are wrapped in `ProtectedRoute`,
which requires a signed-in user (unless demo mode is active). Clerk JWTs authorize backend
API calls (the API Gateway uses a Clerk JWT authorizer). The Clerk provider is themed to
match the app's light/dark mode. Beyond authentication, the analytics routes are additionally
gated on an active subscription ([FE-021](FE-021-subscription-access-control.md)).

## Scope
- Provider: `src/app/clerk-with-theme.tsx`; `useUser` gate in `ProtectedRoute`
  (`src/app/app.tsx`).
- API auth: bearer JWT attached in `src/lib/api-client.ts`; backend authorizer in
  `docs/api/openapi_spec.yaml` (`ClerkJWT`).

## Edge Cases
- **Loading state:** while Clerk is loading (`!isLoaded`), show a spinner rather than
  redirecting.
- **Not signed in:** redirect to `/` (landing).
- **Demo mode:** `ProtectedRoute` bypasses auth entirely ([FE-015](FE-015-demo-mode.md)).
- **Expired/invalid JWT:** backend returns 401/403 via the authorizer; the client must
  handle re-auth.
- **Theme sync:** Clerk UI follows the active light/dark theme ([FE-020](FE-020-theme-toggle.md)).

## Acceptance Criteria
- [ ] Unauthenticated users hitting a protected route are redirected to `/` (except in demo
      mode).
- [ ] A spinner is shown while Clerk auth state is loading.
- [ ] Authenticated API requests attach the Clerk JWT and are authorized by the API Gateway.
- [ ] Demo mode bypasses the auth requirement.
- [ ] Clerk UI matches the active theme.

## Sources
`src/app/clerk-with-theme.tsx`, `src/app/app.tsx`, `src/lib/api-client.ts`,
`docs/api/openapi_spec.yaml`.
