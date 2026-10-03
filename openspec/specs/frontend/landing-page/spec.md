# landing-page Specification

## Purpose
The public marketing/home page at `/`. It introduces LeagueQL, showcases the product with real screenshots, highlights features, explains onboarding, displays the live count of onboarded leagues as social proof, and routes visitors to sign in / connect a league or enter demo mode. Rendered with the marketing header (not the app sidebar layout).

## Requirements

### Requirement: Render the marketing sections
`/` SHALL render the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer with the marketing header, responsively on mobile and desktop. The FAQ accordion SHALL appear between the "How it works" steps and the final CTA band. The "Works with" strip SHALL list ESPN, Sleeper, and Yahoo, and SHALL mark Yahoo with a "Beta" badge indicating its support is newly released.

#### Scenario: Full page render
- **WHEN** a visitor loads `/`
- **THEN** the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer render with the marketing header, laid out responsively

#### Scenario: Yahoo marked Beta in the Works with strip
- **WHEN** a visitor loads `/` and the "Works with" strip renders
- **THEN** the Yahoo platform chip carries a "Beta" badge, while ESPN and Sleeper do not

### Requirement: FAQ accordion
The landing page SHALL present the frequently asked questions as a collapsible accordion in which every question renders collapsed by default (only the question and an expand indicator visible), a visitor can expand a question to reveal its answer, and the indicator reflects the open/closed state.

#### Scenario: Collapsed by default
- **WHEN** a visitor loads `/`
- **THEN** every FAQ question is visible and no FAQ answer is visible

#### Scenario: Expand a question
- **WHEN** a visitor activates a collapsed FAQ question
- **THEN** that question's answer becomes visible and the expand indicator reflects the open state

#### Scenario: Answers preserve their content
- **WHEN** a visitor expands each FAQ question
- **THEN** the answers present the same FAQ content previously shown on the docs page, including any step lists, keyboard-key references, and the support contact link

### Requirement: Product showcase carousel
The showcase SHALL render product screenshots in a swipeable scroll-snap carousel with dot indicators that auto-advances (pausing on pointer interaction, disabled under `prefers-reduced-motion`) and wraps at both edges.

#### Scenario: Auto-advance and pause
- **WHEN** the carousel is visible and the user is not interacting
- **THEN** it auto-advances, pauses on pointer interaction, and does not auto-advance under `prefers-reduced-motion`

#### Scenario: Wrap-around
- **WHEN** the user swipes past the last slide or back from the first
- **THEN** it loops seamlessly to the first or last slide respectively

### Requirement: Show the live league count
The page SHALL show the live onboarded-league count when the counts endpoint responds, and still render (count pill hidden) if it fails.

#### Scenario: Counts available
- **WHEN** the counts endpoint responds
- **THEN** the live onboarded-league count is shown

#### Scenario: Counts unavailable
- **WHEN** the counts endpoint fails or is slow
- **THEN** the page still renders with the count pill hidden/placeholder, never blocking

### Requirement: Route the CTAs
CTAs SHALL route to sign in / connect league (or into the app for signed-in users) and to demo mode, and the nav links SHALL resolve to `/docs` and the in-app `/changelog`.

#### Scenario: Signed-in user CTA
- **WHEN** a signed-in user activates the primary CTA
- **THEN** it routes into the app rather than re-prompting sign in

#### Scenario: Demo entry
- **WHEN** a visitor chooses "View Demo"
- **THEN** they enter demo mode with sample data without connecting a league

#### Scenario: Nav links
- **WHEN** the Docs and Changelog nav links are used
- **THEN** Docs resolves to `/docs` and Changelog to the in-app `/changelog` page

### Requirement: Inline connect routing by existence check
The inline connect form SHALL resolve the league via `getLeague` and route by outcome. ESPN credential inputs (SWID and espn_s2, each with a per-field tooltip explaining how to retrieve the cookie, plus the Chrome-extension autofill helper or install promo below the inputs) and the "enable automatic weekly refresh" opt-in checkbox SHALL NOT be shown merely because ESPN is selected; they SHALL be revealed only after a Connect submit whose existence check returns `404` (not onboarded). When these fields are revealed, an explanatory message "League not added to LeagueQL yet. Enter your ESPN cookies below to connect." SHALL be shown above them. The first `404` SHALL reveal these fields and send no `POST /leagues` onboard request; a subsequent Connect with SWID/espn_s2 provided SHALL onboard the not-yet-onboarded ESPN league in place — the same way Sleeper onboards in place — rather than routing to `/connect_league`. An ESPN `403` (onboarded, caller not a member) SHALL surface invite-link guidance, and a `200` (caller is a member/owner) SHALL route into the existing dashboard. For Yahoo, the form SHALL attempt an in-place onboard (`POST /leagues` with `platform=YAHOO`) before any OAuth redirect, so that an already-linked caller never re-visits Yahoo's consent screen; the consent redirect is used only when the caller has no stored Yahoo link.

#### Scenario: Sleeper not onboarded
- **WHEN** the inline form resolves a Sleeper league to `404`
- **THEN** it onboards in place

#### Scenario: ESPN credentials hidden until lookup
- **WHEN** ESPN is selected in the inline connect form and no Connect submit has resolved to `404` yet
- **THEN** no SWID or espn_s2 inputs, cookie helper, or ESPN auto-refresh checkbox are shown, and the "League not added to LeagueQL yet" message is not shown

#### Scenario: ESPN credentials entered inline
- **WHEN** a Connect submit resolves an ESPN league to `404` for the first time
- **THEN** the message "League not added to LeagueQL yet. Enter your ESPN cookies below to connect." is shown above the SWID and espn_s2 inputs, which are revealed (each with a per-field tooltip and the extension "Autofill cookies from ESPN" button when the extension is detected, an install promo otherwise, below the inputs) together with the ESPN auto-refresh opt-in checkbox, and no `POST /leagues` onboard request is sent

#### Scenario: ESPN not onboarded
- **WHEN** the credential fields have been revealed, SWID/espn_s2 have been provided, and Connect is submitted again for a league that still resolves to `404`
- **THEN** it onboards the ESPN league in place via `POST /leagues` (polling the job to completion with the same progress UI as Sleeper) and, on success, clears the ESPN cookies from the browser and navigates to `/home` — without routing to `/connect_league`

#### Scenario: ESPN onboard without credentials
- **WHEN** the credential fields are revealed but the user submits Connect with SWID and espn_s2 still empty
- **THEN** an inline error is shown and no `POST /leagues` onboard request is sent

#### Scenario: ESPN season derived automatically
- **WHEN** an ESPN league is onboarded in place
- **THEN** the `season` sent with `POST /leagues` is derived automatically (from the Sleeper NFL-state endpoint, falling back to a clock-derived current fantasy season) and the user is never asked to enter it

#### Scenario: ESPN already onboarded — member routes in
- **WHEN** the inline form resolves an ESPN league to `200` (onboarded and the caller is a member or owner)
- **THEN** it routes into the existing league dashboard (`/home`) without revealing the credential fields

#### Scenario: ESPN member gate
- **WHEN** the inline form resolves an ESPN league to `403` (onboarded but caller not a member)
- **THEN** it surfaces the message "League already onboarded. Please reach out to your leaguemate who onboarded the league to get your league-specific invite link.", without revealing or prompting for ESPN cookies

#### Scenario: Yahoo already linked — onboard in place
- **WHEN** a Yahoo league is connected and `POST /leagues` (`platform=YAHOO`) succeeds with a `correlation_id` (the caller has a stored Yahoo link)
- **THEN** the form polls the job to completion in place with the same progress UI as Sleeper and, on success, navigates to `/home` — without redirecting to Yahoo's consent screen

#### Scenario: Yahoo already onboarded
- **WHEN** a Yahoo league is connected and `POST /leagues` responds `200` with a null `data` (the league already exists)
- **THEN** the form skips polling and routes the caller into the existing league dashboard (`/home`), without redirecting to Yahoo's consent screen

#### Scenario: Yahoo not linked — begin consent
- **WHEN** a Yahoo league is connected and `POST /leagues` responds `403` ("Link your Yahoo account first")
- **THEN** the form calls `GET /leagues/yahoo/oauth/authorize?leagueId=<id>` and navigates the browser (full-page redirect) to the returned Yahoo consent URL

#### Scenario: Yahoo link revoked
- **WHEN** a Yahoo onboard job fails with the `YAHOO_AUTH` re-link signal (a stored link whose token was revoked)
- **THEN** the form restarts the Yahoo OAuth step rather than showing a generic failure

#### Scenario: Other failure
- **WHEN** the existence check fails for another reason
- **THEN** a generic inline message is shown

### Requirement: Resume the Yahoo OAuth return inline without an auto-refresh opt-in
On load, `/` SHALL detect the Yahoo OAuth return params (`platform=YAHOO`, `yahooLinked`, and an optional `leagueId`) and resolve the return inline in the connect form, without routing to a separate page. On `yahooLinked=1` with a `leagueId` it SHALL open the connect form with Yahoo selected and resume onboarding for that league id with the same hero progress UI (polling the job and navigating to `/home` on success). No automatic-refresh opt-in SHALL be carried across the consent redirect or applied on the return, since Yahoo leagues always auto-refresh (frontend/connect-yahoo-league). On `yahooLinked=0` it SHALL open the connect form with Yahoo selected and show an inline retry alert instead of onboarding. The return params SHALL be consumed so a reload does not re-trigger onboarding, and a revoked/expired link surfaced during the resume SHALL restart the Yahoo OAuth step rather than showing a generic failure.

#### Scenario: Linked return resumes onboarding inline
- **WHEN** `/` loads with `platform=YAHOO&yahooLinked=1&leagueId=<id>` and the visitor is signed in
- **THEN** the connect form opens with Yahoo selected and onboarding resumes inline (`POST /leagues` with `platform=YAHOO`, polling with the hero progress bar), navigating to `/home` on success

#### Scenario: Linked return for an already-onboarded league
- **WHEN** the inline resume calls `POST /leagues` and it responds `200` with a null `data` (the league already exists)
- **THEN** polling is skipped and the visitor is routed into the existing league dashboard (`/home`)

#### Scenario: No auto-refresh opt-in on return
- **WHEN** the visitor returns from Yahoo consent with `yahooLinked=1`
- **THEN** the inline resume's `POST /leagues` carries no automatic-refresh opt-in choice

#### Scenario: Declined return
- **WHEN** `/` loads with `platform=YAHOO&yahooLinked=0`
- **THEN** the connect form opens with Yahoo selected and an inline retry alert ("Yahoo linking was cancelled or failed — try again") is shown, and no onboard request is sent

#### Scenario: Revoked link on return
- **WHEN** the inline resume fails with the `YAHOO_AUTH` re-link signal (or a `403` "link first")
- **THEN** the Yahoo OAuth step is restarted rather than a generic failure being shown

#### Scenario: Return params not re-triggered on reload
- **WHEN** the Yahoo return has been handled and the page is reloaded
- **THEN** the consumed `platform`/`yahooLinked`/`leagueId` params no longer re-trigger onboarding

### Requirement: View My Leagues button
For a signed-in user, the hero SHALL show a "View My Leagues" button beside "Connect Your League" and "View Demo". It SHALL toggle an expandable panel below the buttons and expose its state with `aria-expanded`. Signed-out visitors SHALL NOT see it. Opening the panel SHALL close the Connect form, and opening the Connect form SHALL close the panel.

#### Scenario: Signed out
- **WHEN** a signed-out visitor loads `/`
- **THEN** no "View My Leagues" button is shown

#### Scenario: Expand and collapse
- **WHEN** a signed-in user activates "View My Leagues", then activates it again
- **THEN** the panel expands below the buttons with `aria-expanded="true"`, then collapses with `aria-expanded="false"`

#### Scenario: Mutually exclusive with Connect
- **WHEN** the panel is open and the user activates "Connect Your League"
- **THEN** the Connect form opens and the panel collapses, and the reverse also holds

### Requirement: List the user's leagues
When expanded, the panel SHALL fetch the user's leagues and list them in the returned order (most recently updated first). Each row SHALL show the platform logo, league name, platform, season span with season count, and when it was last updated. A migrated league SHALL note its source platform, and an owner's ESPN league needing re-auth SHALL show a "Reconnect ESPN" flag. Rows SHALL NOT show owner/member badges or filters.

#### Scenario: Leagues listed
- **WHEN** the panel opens and the API returns leagues
- **THEN** each league renders as a row with its logo, name, "Platform • first–last · N seasons • Updated …", in API order

#### Scenario: Migrated league row
- **WHEN** a returned league has `migrated_from` set
- **THEN** its row notes "Moved from <platform>"

#### Scenario: Re-auth flag
- **WHEN** a returned league has `espn_reauth_required` true
- **THEN** its row shows a "Reconnect ESPN" flag

#### Scenario: Missing-league hint
- **WHEN** the list renders
- **THEN** a hint below it reads "Missing a league? For ESPN or Yahoo, ask the league owner for an invite link. For Sleeper, open your league once using "Connect Your League" and it shows up here afterwards."

### Requirement: League list states
The panel SHALL show a loading skeleton while fetching. With no leagues, it SHALL show an empty state that explains how leagues get added and offers "Connect Your League". When the request fails, it SHALL show the error inline with a retry action, not in a global banner.

#### Scenario: Loading
- **WHEN** the leagues request is in flight
- **THEN** skeleton rows are shown

#### Scenario: Empty
- **WHEN** the API returns an empty list
- **THEN** an empty state with a "Connect Your League" action is shown, and that action opens the Connect form

#### Scenario: Request fails
- **WHEN** the leagues request fails with a `4xx` or `5xx`
- **THEN** an inline error with "Try again" is shown, and retrying re-requests the list

### Requirement: Open a league from the list
Activating a row SHALL open that league the same way the Connect flow opens an already-onboarded league: it loads the league's metadata for the row's `league_id` and `platform`, stores the league selection, and navigates to `/home`. A failure SHALL be shown inline without leaving the page.

#### Scenario: Open succeeds
- **WHEN** the user activates a league row
- **THEN** the league's selection is stored and the app navigates to `/home`

#### Scenario: Open fails
- **WHEN** loading the selected league's metadata fails (for example `403` after access was revoked)
- **THEN** an inline error is shown and the user stays on `/`
