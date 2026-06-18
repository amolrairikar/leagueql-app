# FE-030: Informational Banner

## Description
A thin, generic informational banner rendered directly **below the in-app header**, used to
promote whatever the current campaign is (a "join the LeagueQL Discord community" invite
today). It is gated behind the `banner` global feature flag (FE-026 / BE-017) so it can be
turned on/off from the AWS SSM Parameter Store console with no redeploy, and it is dismissible — a
dismissal is remembered per-browser in `localStorage`. The banner's content (message + link)
is a single editable config block in the component, so refreshing the campaign is a content
change, not a structural one.

## Scope
- Component: `src/components/banner.tsx` — content-driven (the `BANNER_*` constants),
  self-gates on the flag, on demo mode, and on the stored dismissal, returning `null` when off,
  in demo mode, or dismissed.
- Flag helper: `isBannerEnabled()` in `src/lib/feature-flags.ts` (reads the `banner` flag
  resolved from `GET /feature-flags`).
- Placement: rendered in `AppLayout` (`src/app/app.tsx`) immediately below the in-app
  header. **Main app only** — it does not appear on the public/marketing routes that use the
  shared `<Header>` (landing, changelog, privacy, docs).
- Content: `BANNER_MESSAGE_PREFIX`, `BANNER_LINK_LABEL`, `BANNER_MESSAGE_SUFFIX`, and
  `BANNER_LINK_URL` constants. The message reads PREFIX + LINK_LABEL + SUFFIX, with the link
  rendered inline on `BANNER_LINK_LABEL`, so the link lives within the sentence rather than as
  a trailing call-to-action. The current campaign is the Discord invite — "Join the LeagueQL
  Discord community" with the word "community" linking to the invite
  (`https://discord.gg/jE2dm89GWh`). An empty `BANNER_LINK_URL` renders the label as plain text
  (a message-only banner).
- Dismissal persistence: `localStorage` key `leagueql.bannerDismissed` (read/written
  defensively so storage failures never crash the app).

## Edge Cases
- **Flag off (default):** the banner renders nothing, regardless of dismissal state.
- **Flag on, not dismissed:** the banner shows on every main-app page with its message and,
  when configured, a link that opens in a new tab (`rel="noopener noreferrer"`).
- **Dismissed:** clicking the close (X) button hides the banner and writes the
  `localStorage` flag, so it stays hidden across reloads/navigations for that browser.
- **Main app only:** the banner never appears on landing/docs/privacy/changelog routes.
- **Demo mode:** the banner is suppressed (renders nothing) while exploring the demo, so the
  promotional invite doesn't clutter the sample-data experience — even with the flag on.
- **Link-less content:** a banner with no `BANNER_LINK_URL` shows just the message (the label
  renders as plain text).
- **localStorage unavailable:** a storage read/write failure (private browsing, disabled
  storage) is swallowed — the banner still renders and dismisses for the session.

## Acceptance Criteria
- [ ] With `banner` OFF, the banner is not rendered anywhere.
- [ ] With `banner` ON, the banner appears below the header on every main-app page and, when
      configured, links to the campaign URL in a new tab.
- [ ] The banner does not render on the public marketing routes (landing/docs/privacy/changelog).
- [ ] The banner does not render in demo mode, even with `banner` ON.
- [ ] Dismissing the banner hides it and keeps it hidden after a reload (localStorage).

## Sources
`src/components/banner.tsx`, `src/lib/feature-flags.ts`, `src/app/app.tsx`,
[FE-026](FE-026-feature-flags.md) (flag plumbing), [BE-017](../backend/BE-017-feature-flags.md)
(`banner` exposed via `GET /feature-flags`).
