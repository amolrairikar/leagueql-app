# landing-page Specification

## Purpose
The public marketing/home page at `/`. It introduces LeagueQL, showcases the product with real screenshots, highlights features, explains onboarding, displays the live count of onboarded leagues as social proof, and routes visitors to sign in / connect a league or enter demo mode. Rendered with the marketing header (not the app sidebar layout).

## Requirements

### Requirement: Render the marketing sections
`/` SHALL render the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, final CTA band, and footer with the marketing header, responsively on mobile and desktop.

#### Scenario: Full page render
- **WHEN** a visitor loads `/`
- **THEN** the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, final CTA band, and footer render with the marketing header, laid out responsively

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
The inline connect form SHALL resolve the league via `getLeague` and route by outcome, opening the Join League dialog on an ESPN `403`.

#### Scenario: Sleeper not onboarded
- **WHEN** the inline form resolves a Sleeper league to `404`
- **THEN** it onboards in place

#### Scenario: ESPN not onboarded
- **WHEN** the inline form resolves an ESPN league to `404`
- **THEN** it routes to `/connect_league` to onboard

#### Scenario: ESPN member gate
- **WHEN** the inline form resolves an ESPN league to `403` (onboarded but caller not a member)
- **THEN** it opens the Join League (membership verification) dialog in place

#### Scenario: Other failure
- **WHEN** the existence check fails for another reason
- **THEN** a generic inline message is shown
