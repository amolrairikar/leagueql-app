## Why

When a first ESPN Connect lookup on the landing page returns `404`, the SWID/espn_s2
credential fields appear with no explanation of why they suddenly showed up. Users don't
know the league isn't in LeagueQL yet or that entering cookies is the next step, which
makes the reveal feel abrupt and unclear.

## What Changes

- On the landing-page inline connect form, when a first ESPN Connect lookup resolves to
  `404` and reveals the SWID/espn_s2 credential fields, show the explanatory text
  "League not added to LeagueQL yet. Enter your ESPN cookies below to connect." above
  those fields.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `frontend/landing-page`: the "Inline connect routing by existence check" requirement
  gains an explanatory message shown together with the revealed ESPN credential fields.

## Impact

- `frontend/src/features/landing_page/landing-page.tsx` — render the message inside the
  `needsEspnCredentials` block.
- Frontend component tests under
  `frontend/src/features/landing_page/__tests__/` — assert the message appears on the
  first-404 reveal.
