# authentication Specification

## Purpose
Authentication is handled by Clerk. In-app analytics routes are wrapped in `ProtectedRoute`, which requires a signed-in user unless demo mode is active. Clerk JWTs authorize backend API calls (the API Gateway uses a Clerk JWT authorizer). The Clerk provider is themed to match the app's light/dark mode.

## Requirements

### Requirement: Protect in-app routes
Unauthenticated users hitting a protected route SHALL be redirected to `/` (except in demo mode), with a spinner shown while Clerk auth state loads.

#### Scenario: Not signed in
- **WHEN** an unauthenticated user hits a protected route outside demo mode
- **THEN** they are redirected to `/` (landing)

#### Scenario: Auth loading
- **WHEN** Clerk auth state is still loading (`!isLoaded`)
- **THEN** a spinner is shown rather than redirecting

#### Scenario: Demo mode bypass
- **WHEN** demo mode is active
- **THEN** `ProtectedRoute` renders children without requiring sign-in

### Requirement: Attach a fresh Clerk JWT per request
Authenticated API requests SHALL attach a Clerk JWT obtained via `getToken()` (registered through `AuthTokenBridge`), not by reading the `__session` cookie, and send unauthenticated when no token can be minted.

#### Scenario: Token attached
- **WHEN** the API client makes an authenticated request
- **THEN** it attaches a fresh, short-lived session JWT from Clerk's `getToken()` (via `AuthTokenBridge`) rather than parsing the `__session` cookie, and the API Gateway authorizes it

#### Scenario: No token available
- **WHEN** no token can be minted (signed out / Clerk not yet loaded)
- **THEN** the request is sent unauthenticated and the backend returns `401`

#### Scenario: Expired/invalid JWT
- **WHEN** the backend returns `401`/`403` via the authorizer
- **THEN** the client handles re-auth

### Requirement: Theme the Clerk UI
The Clerk UI SHALL follow the active light/dark theme.

#### Scenario: Theme sync
- **WHEN** the active theme changes
- **THEN** the Clerk UI matches the active light/dark theme
