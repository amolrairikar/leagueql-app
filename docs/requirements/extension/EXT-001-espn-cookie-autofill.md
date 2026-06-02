# EXT-001: ESPN Cookie Auto-Fill Chrome Extension

## Description
A Chrome extension that reads the user's ESPN `espn_s2` and `SWID` cookies and makes them
available to the LeagueQL onboarding form, so users with private ESPN leagues don't have to
manually copy cookie values from their browser. The extension only reads ESPN cookies and
passes them to the LeagueQL app for onboarding; it never stores or transmits them elsewhere.

## Scope
- Extension source: `extension/` (`src/`, `manifest.config.ts`).
- Frontend integration: `src/lib/espn-extension.ts`, `src/lib/cookie-handler.ts`,
  consumed by the connect/migrate flows ([FE-002](../frontend/FE-002-connect-league.md),
  [FE-003](../frontend/FE-003-migrate-league.md)).
- Privacy disclosure: [FE-018](../frontend/FE-018-privacy-pages.md) (`/extension-privacy`).

## Edge Cases
- **Extension not installed:** the connect/migrate forms must fall back to manual cookie
  entry.
- **User not logged into ESPN:** cookies absent — communicate that the user must log into
  ESPN first.
- **Cookie permissions scope:** the extension requests access only to ESPN domains.
- **Cookie lifecycle:** values are passed to LeagueQL once for onboarding and cleared after
  use; never persisted by the extension or app.
- **Message channel:** the page ↔ extension messaging must validate origin/messages.
- **Chrome Web Store policy:** a public privacy page and minimal permissions are required.

## Acceptance Criteria
- [ ] The extension can read `espn_s2` and `SWID` from the user's ESPN cookies and provide
      them to the LeagueQL onboarding/migration form.
- [ ] When the extension is absent, the form still supports manual cookie entry.
- [ ] When the user is not logged into ESPN, the UI explains how to proceed.
- [ ] The extension requests permissions scoped to ESPN domains only.
- [ ] Cookie values are not stored or logged; they are cleared after onboarding.
- [ ] Behavior matches the published `/extension-privacy` disclosure.

## Sources
`extension/`, `src/lib/espn-extension.ts`, `src/lib/cookie-handler.ts`, `extension/README.md`.
