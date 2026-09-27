## 1. Season utilities

- [x] 1.1 In `frontend/src/lib/season.ts`, add and export `currentFantasySeason(now: Date): number` (Sept flip → prior calendar year before September); verify a small unit assertion or reuse via typecheck.
- [x] 1.2 Update `frontend/src/features/sidebar/use-season-staleness.ts` to import `currentFantasySeason` from `@/lib/season` and delete its local copy; verify `npx vitest run src/features/sidebar` (staleness tests) still passes.
- [x] 1.3 In `frontend/src/lib/season.ts`, add `getCurrentNflSeason(): Promise<string>` — raw `fetch` of `https://api.sleeper.app/v1/state/nfl` returning `String(json.season)`, falling back to `String(currentFantasySeason(new Date()))` on any failure (never throws); verify via the tests added in section 5.

## 2. Shared ESPN credential fields component

- [x] 2.1 Create `frontend/src/features/connect_league/espn-credential-fields.tsx`: controlled SWID/espn_s2 `Input`s with the existing `HelpCircle`/`Tooltip` labels, the `useEspnExtensionReady` autofill button (`requestEspnCookies`/`EspnExtensionError`) or the `ESPN_EXTENSION_URL` install promo, and the manual DevTools cookie instructions as visible helper text below the inputs. Props: `swid`, `espnS2`, `onSwidChange`, `onEspnS2Change`, `swidError?`, `espnS2Error?`, `onAutofill(swid, espnS2)`. Verify it compiles (`npm run build:ci`) and renders in the landing-page tests (section 5).

## 3. Landing page inline ESPN onboarding

- [x] 3.1 In `frontend/src/features/landing_page/landing-page.tsx`, add `swid`/`espnS2` (and ESPN `autoRefresh`) state and render `<EspnCredentialFields>` + the ESPN auto-refresh opt-in checkbox only when `platform === 'ESPN'`, placed after the League ID input, staying responsive within `max-w-lg` (no horizontal page scroll). Verify visually and via section 5 tests.
- [x] 3.2 Rework the ESPN branch of `handleConnectSubmit`: on `getLeague` `404`, require SWID/espn_s2 (else set the inline `error` and return with no request); otherwise onboard in place — build the `OnboardRequest` `{ leagueId, platform: 'ESPN', season: await getCurrentNflSeason(), s2, swid, autoRefresh }`, call `onboardLeague('ONBOARD', body)`, `pollForCompletion`, `clearEspnCookies()`, and on success `setLeagueCookies` + navigate `/home`. Leave the `200` and `403` branches unchanged. Verify via section 5 tests.

## 4. `/connect_league` refresh form — remove manual season, auto-derive

- [x] 4.1 In `frontend/src/features/connect_league/league-connect-schema.ts`, remove `latestSeason` from the ESPN branch of the discriminated union; verify `npm run build:ci` typechecks.
- [x] 4.2 In `frontend/src/features/connect_league/league-connect.tsx`, delete the "Latest Season" `<Input>` block and the `trigger('latestSeason')` wiring, and set `season: data.platform === 'espn' ? await getCurrentNflSeason() : undefined` in `onSubmit`. Optionally reuse `<EspnCredentialFields>` for the SWID/espn_s2 markup. Verify via section 5 tests.

## 5. Tests

- [x] 5.1 Add a shared `sleeperNflState` MSW helper in `frontend/src/test/msw/server.ts` for `https://api.sleeper.app/v1/state/nfl`.
- [x] 5.2 Update `frontend/src/features/landing_page/__tests__/landing-connect.{feature,steps.test.tsx}`: ESPN `404` shows inline SWID/espn_s2, onboards in place (polls to COMPLETED, routes `/home`, never navigates to `/connect_league`); captured `POST /leagues` body carries the Sleeper-fetched `season`; Sleeper-fetch failure still sends the clock-fallback season; onboard attempted with empty credentials → inline error and no mutation. Verify `npx vitest run src/features/landing_page/__tests__`.
- [x] 5.3 Update `frontend/src/features/connect_league/__tests__/connect-league.{feature,steps.test.tsx}`: remove the manual-season scenarios ("non-4-digit season", live >4-digit typing), update the `connectEspnFlow` helper to stop filling the removed season input, and register the `sleeperNflState` handler for the refresh-onboard paths. Verify `npx vitest run src/features/connect_league/__tests__`.

## 5b. In-dashboard ESPN refresh dialog

- [x] 5b.1 Create `frontend/src/features/sidebar/refresh-league-dialog.tsx`: a dialog reusing `<EspnCredentialFields showManualInstructions={false}>` that, on submit, derives the season via `getCurrentNflSeason`, calls `onboardLeague('REFRESH', …)` (with retry), polls to completion, clears the ESPN cookies, and reloads the dashboard in place; surfaces `429`/`409` as a benign notice and other failures as an inline error. Verify via section 5b tests.
- [x] 5b.2 Wire it into `frontend/src/features/sidebar/app-sidebar.tsx`: replace the "Refresh League" `<Link to={refreshLeagueUrl}>` with a button that opens the dialog, drop the now-unused `refreshLeagueUrl`, and render `<RefreshLeagueDialog>`. Verify `npm run build:ci` + ownership-gating tests still pass.
- [x] 5b.3 Add `frontend/src/features/sidebar/__tests__/refresh-league.{feature,steps.test.tsx}`: successful refresh sends the auto-derived season + cookies and reloads; `429` cooldown shows the benign notice without reloading; empty cookies show an inline error with no request. Verify `npx vitest run src/features/sidebar/__tests__/refresh-league.steps.test.tsx`.

## 6. Spec sync, lint, and verification

- [x] 6.1 Update the `frontend/connect-league` main spec `## Purpose` wording so it no longer says the user enters a "latest season" (Purpose changes cannot ride in a delta); done as part of `/opsx:archive`.
- [x] 6.2 From `frontend/`, run `npm run format:fix`, `npm run lint`, and `npm run test`; confirm all pass.
- [x] 6.3 Run `openspec validate --all` and confirm it passes; then manual end-to-end check on `/` (ESPN in place onboard, no `/connect_league` redirect, no season field, extension helper + manual instructions visible).
