# Design

## Context

The `integrations` flag was read in four places: the backend route dependency
`require_integrations_enabled`, the `GET /feature-flags` payload, the sidebar's "Community" group,
and the `IntegrationsRoute` wrapper that redirected `/integrations` to `/home`.

## Decisions

- **Remove the flag entirely rather than defaulting it on.** The feature is launched; keeping a
  kill switch is not wanted. The generic flag machinery (OpenFeature, SSM, `GET /feature-flags`)
  stays for `banner`.
- **Drop `IntegrationsRoute`.** With no gate it would be a pass-through, so the route table renders
  `IntegrationsPage` directly.
- **Drop the key from `GET /feature-flags`.** The SPA no longer reads it; an unknown flag already
  fails safe, so an old cached SPA simply hides the page until reload.

## Deploy order

Backend first is safest (an old SPA against the new backend hides the nav item until reload; a new
SPA against the old backend would hit `404`s if the SSM flag were off). Since the flag is on in prod,
either order works.
