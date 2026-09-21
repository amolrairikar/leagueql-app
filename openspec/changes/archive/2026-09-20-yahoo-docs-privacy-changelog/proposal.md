# Proposal

## Why

Yahoo Fantasy is now a fully supported onboarding platform (OAuth account
linking plus real league-data onboarding), but the public-facing surfaces still
describe LeagueQL as an ESPN/Sleeper-only tool:

- The landing page "Works with" strip lists Yahoo with no signal that support is
  newly shipped and still stabilizing.
- The privacy policy says data comes only "from ESPN and Sleeper" and never
  discloses that, unlike ESPN cookies (which are never stored), LeagueQL **does**
  persist Yahoo OAuth tokens — encrypted at rest — to refresh league data.
- The `/docs` "Connecting a League" section documents only ESPN and Sleeper, so
  a Yahoo user has no instructions for the OAuth connect flow.
- The in-app changelog has no entry announcing Yahoo support.

## What Changes

- **Landing page:** mark Yahoo in the "Works with" strip with a "Beta" badge so
  visitors know Yahoo support is newly released.
- **Privacy policy (`/privacy`):** disclose Yahoo as a data source and add a
  clear statement that Yahoo OAuth access/refresh tokens are stored encrypted at
  rest so LeagueQL can refresh league data, never shared, and removed on
  request — contrasted with the never-stored ESPN cookies. (Kept plain: no
  internal encryption implementation details.)
- **Docs (`/docs`):** add a Yahoo subsection under "Connecting a League"
  documenting the OAuth link flow (select Yahoo, enter league ID, authorize with
  Yahoo, onboarding resumes automatically) and the Yahoo league-ID form field,
  and add it to the table of contents.
- **Changelog:** add a release entry announcing Yahoo Fantasy support.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `frontend/landing-page`: the "Works with" strip labels Yahoo with a "Beta"
  badge.
- `frontend/privacy-pages`: the general privacy page discloses Yahoo as a data
  source and that Yahoo OAuth tokens are stored encrypted at rest.
- `frontend/instructions-docs`: "Connecting a League" gains a Yahoo subsection
  (with its own TOC entry) documenting the OAuth connect flow.

## Impact

- Frontend only (content / UI):
  - `frontend/src/features/landing_page/constants.ts` — Yahoo `Platform` gains a
    `beta` flag.
  - `frontend/src/features/landing_page/types.ts` — `Platform` type gains an
    optional `beta` field.
  - `frontend/src/features/landing_page/landing-page.tsx` — render the "Beta"
    badge in the "Works with" strip.
  - `frontend/src/features/privacy/privacy-page.tsx` — Yahoo data source + OAuth
    token disclosure.
  - `frontend/src/features/instructions/instructions-page.tsx` — Yahoo connect
    subsection + TOC entry.
  - `frontend/src/features/changelog/constants.ts` — new release entry.
  - Landing-page component tests gain a "Beta" badge assertion.
- No backend, API-contract, DynamoDB, or infrastructure changes.
