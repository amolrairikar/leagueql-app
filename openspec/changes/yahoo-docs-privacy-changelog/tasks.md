# Tasks

## 1. Landing page — Yahoo "Beta" badge
- [x] 1.1 Add an optional `beta` field to the `Platform` type (`frontend/src/features/landing_page/types.ts`).
- [x] 1.2 Set `beta: true` on the Yahoo entry in `PLATFORMS` (`frontend/src/features/landing_page/constants.ts`).
- [x] 1.3 Render a "Beta" badge on the Yahoo chip in the "Works with" strip (`frontend/src/features/landing_page/landing-page.tsx`).
- [x] 1.4 Add a landing-page component-test assertion that Yahoo shows a "Beta" badge.

## 2. Privacy policy — Yahoo OAuth token disclosure
- [x] 2.1 Add Yahoo to the platforms named in the Overview and Third-Party Services sections.
- [x] 2.2 Add a "Yahoo OAuth Tokens" disclosure under "Data We Collect & Store" stating tokens are stored encrypted at rest to refresh league data, contrasted with never-stored ESPN cookies.
- [x] 2.3 Bump the "Last updated" date.

## 3. Docs — Yahoo connect subsection
- [x] 3.1 Add a `yahoo-leagues` (and `yahoo-form-fields`) TOC entry.
- [x] 3.2 Add the Yahoo subsection under "Connecting a League" documenting the OAuth flow and league-ID field.

## 4. Changelog
- [x] 4.1 Add a new release entry announcing Yahoo Fantasy support.

## 5. Verify
- [x] 5.1 `openspec validate --all` passes.
- [x] 5.2 Frontend lint + format pass, affected component tests pass.
