## Context

The beta treatment is driven by a `beta` flag on `Platform` and a shared `YAHOO_BETA_SUPPORT_NOTE` constant used in two places.

## Decisions

- Delete the flag, the constant and the now-unused `SUPPORT_EMAIL` outright instead of hiding them, since nothing else uses them.
- Keep the changelog entry, minus "(Beta)".
