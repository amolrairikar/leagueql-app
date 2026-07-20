# FE-035: Weekly Matchup Recap

## Description
A premium section on the `/matchups` page that shows an **AI-written weekly recap column** for the
selected week — a medium-long, lighthearted-but-journalistic write-up of that week's matchups, with
a headline and body paragraphs. The prose is **precomputed asynchronously** by the scheduled
recap-generator Fargate task (Anthropic Claude Haiku 4.5,
[BE-021](../backend/BE-021-ai-weekly-matchup-recap.md)) and cached in DynamoDB; this feature only
**reads** the cached text through the existing query API
([BE-005](../backend/BE-005-query-precomputed-views-api.md)). There is no client-side generation and
no request-path LLM call. Behavior here is unchanged — weeks without a cached recap still show the
"generating" empty state — only the end-to-end latency differs: a recap now appears within roughly the
generator's cron interval plus a few seconds of generation, rather than a batch turnaround.

The section lives on `/matchups`, below the Weekly Awards section
([FE-032](FE-032-weekly-awards-superlatives.md)), and tracks the page's existing season + week
navigation — there is no separate selector. It renders the recap for the **selected week**.

## Scope
- Lives on the `/matchups` page ([FE-006](FE-006-matchups.md)), after the Weekly Awards block, scoped
  to the page's season + week navigation.
- New feature folder `src/features/weekly_recap/`:
  - `api-calls.ts` — `getWeekRecap(leagueId, platform, season, week)` wrapping
    `queryLeague<RecapItem>(leagueId, platform, \`MATCHUP_RECAP#${season}#WEEK#${week2}\`)` (week
    zero-padded to two digits); exports
    `RecapItem = { headline: string; body: string; generated_at: string }`.
  - `weekly-recap.tsx` — default-export component taking `{leagueId, platform, season, selectedWeek}`,
    using the canonical `useMemo → toResult → <Suspense>/use(promise)` pattern. Renders a styled
    headline plus body paragraphs (split `body` on `\n\n`), with skeleton, empty, and inline-error
    states. A fully-generated recap shows a **copy button** in the card's top-right corner that copies
    the recap (headline + body) to the clipboard so it can be pasted into a group chat; the button
    shows a copy icon by default and swaps to a check mark for ~2s after a successful copy.
- **Premium-gated:** wrapped in `SubscriptionGuard` with the shared `premium_feature` flag
  ([FE-021](FE-021-subscription-access-control.md) / [FE-026](FE-026-feature-flags.md)). This is the
  **only** remaining premium section (Weekly Awards and the other former premium features are now
  free). While `billing` is off the whole section (header + gated content) is **hidden**;
  with `billing` on but `premium_feature` off the guard is a pass-through and the section renders for
  everyone. When gated and the subscription is expired/absent, the guard renders a blurred lock
  overlay and the `WeeklyRecap` component is **not mounted**, so its recap data is never fetched while
  locked. The section header is gated on `isBillingEnabled` so it disappears with the section.

## Edge Cases
- **No recap for the selected week** (no item yet — generation pending, or a non-premium league that
  never generated): show an empty-state message ("Weekly recap generating! Check back soon.") rather
  than an error.
- **Copy a recap:** clicking the copy button writes the recap's headline + body to the clipboard and
  the icon swaps to a check mark for ~2s, then reverts to the copy icon.
- **Load failure (5xx) / network error:** surface an inline message; never throw.
- **Week with no selection:** falls back to the page's active week, consistent with Weekly Awards.
- **Locked (expired subscription):** the gated component is not mounted and never fetches.
- **Loading:** show a skeleton while the cached recap is fetched.

## Acceptance Criteria
- [ ] On `/matchups`, a Weekly Matchup Recap section renders below Weekly Awards for the selected
      season, showing the cached recap (headline + body paragraphs) for the **selected week**.
- [ ] Navigating to a different week fetches and renders that week's recap.
- [ ] A week with no cached recap shows the empty-state message ("Weekly recap generating! Check back
      soon."); a load failure shows an inline message — neither crashes.
- [ ] A fully-generated recap shows a copy button in the top-right; clicking it copies the recap
      (headline + body) to the clipboard and the icon changes to a check mark, then reverts.
- [ ] When `premium_feature` (and `billing`) is enabled and the league subscription is
      expired/absent, the section shows a blurred lock overlay instead of the recap and **does not
      fetch** the recap data. With `billing` off the section and its header are hidden; with `billing`
      on but `premium_feature` off it renders for everyone.

## Sources
`src/features/weekly_recap/`, `src/features/matchups/matchups.tsx`,
`src/features/weekly_awards/weekly-awards.tsx` (component pattern),
`src/features/instructions/instructions-page.tsx` (prose styling),
`src/features/subscription/subscription-guard.tsx`.
