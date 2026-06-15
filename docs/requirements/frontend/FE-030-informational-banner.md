# FE-030: Informational Banner

## Description
A thin, generic informational banner rendered directly **below the in-app header**, used to
promote whatever the current campaign is (a "join the LeagueQL Discord community" invite
today). It is gated behind the `banner` global feature flag (FE-026 / BE-017) so it can be
turned on/off from the AWS AppConfig console with no redeploy, and it is dismissible — a
dismissal is remembered per-browser in `localStorage`. The banner's content (message + link)
is a single editable config block in the component, so refreshing the campaign is a content
change, not a structural one.

## Scope
- Component: `src/components/banner.tsx` — content-driven (the `BANNER_*` constants),
  self-gates on the flag and on the stored dismissal, returning `null` when off or dismissed.
- Flag helper: `isBannerEnabled()` in `src/lib/feature-flags.ts` (reads the `banner` flag
  resolved from `GET /feature-flags`).
- Placement: rendered in `AppLayout` (`src/app/app.tsx`) immediately below the in-app
  header. **Main app only** — it does not appear on the public/marketing routes that use the
  shared `<Header>` (landing, changelog, privacy, docs).
- Content: `BANNER_MESSAGE`, `BANNER_LINK_LABEL`, `BANNER_LINK_URL` constants. The current
  campaign is the Discord invite; `BANNER_LINK_URL` ships as a clearly-marked placeholder
  (`https://discord.gg/REPLACE_ME`) to be replaced before the flag is turned on. An empty
  `BANNER_LINK_URL` renders a message-only banner.
- Dismissal persistence: `localStorage` key `leagueql.bannerDismissed` (read/written
  defensively so storage failures never crash the app).

## Edge Cases
- **Flag off (default):** the banner renders nothing, regardless of dismissal state.
- **Flag on, not dismissed:** the banner shows on every main-app page with its message and,
  when configured, a link that opens in a new tab (`rel="noopener noreferrer"`).
- **Dismissed:** clicking the close (X) button hides the banner and writes the
  `localStorage` flag, so it stays hidden across reloads/navigations for that browser.
- **Main app only:** the banner never appears on landing/docs/privacy/changelog routes.
- **Placeholder/link-less content:** until the campaign link is real, the flag should stay
  OFF in production; a banner with no `BANNER_LINK_URL` shows just the message.
- **localStorage unavailable:** a storage read/write failure (private browsing, disabled
  storage) is swallowed — the banner still renders and dismisses for the session.

## Acceptance Criteria
- [ ] With `banner` OFF, the banner is not rendered anywhere.
- [ ] With `banner` ON, the banner appears below the header on every main-app page and, when
      configured, links to the campaign URL in a new tab.
- [ ] The banner does not render on the public marketing routes (landing/docs/privacy/changelog).
- [ ] Dismissing the banner hides it and keeps it hidden after a reload (localStorage).

## Sources
`src/components/banner.tsx`, `src/lib/feature-flags.ts`, `src/app/app.tsx`,
[FE-026](FE-026-feature-flags.md) (flag plumbing), [BE-017](../backend/BE-017-feature-flags.md)
(`banner` exposed via `GET /feature-flags`).
