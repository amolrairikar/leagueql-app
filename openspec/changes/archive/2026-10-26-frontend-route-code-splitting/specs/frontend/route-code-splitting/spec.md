# Spec Delta

## Purpose

Keep the initial download small by loading each page's code only when its route is visited, while
making the loading and failure states of that on-demand load visible to the user.

## ADDED Requirements

### Requirement: Load route pages on demand
The app SHALL load the code for a route's page only when that route is first rendered, rather than
bundling every page into the initial download, and SHALL render the same page content and URLs as
before.

#### Scenario: Landing page does not load league pages
- **WHEN** a visitor opens `/`
- **THEN** the code for league-analytics pages (for example standings, matchups, and manager
  history) is not requested

#### Scenario: Page loads when its route is visited
- **WHEN** a signed-in user navigates to `/standings`
- **THEN** the standings page code is requested and the page renders its normal content

### Requirement: Show a loading indicator while a page loads
While a route's code is loading, the app SHALL show the spinner in place of the page. For in-app
pages the sidebar, header, and banners SHALL remain mounted and only the page area SHALL show the
spinner.

#### Scenario: In-app page loading keeps the app chrome
- **WHEN** a signed-in user navigates between two in-app pages and the target page's code is still
  loading
- **THEN** the sidebar and header stay visible and the page area shows the spinner until the page
  renders

#### Scenario: Public page loading
- **WHEN** a visitor opens a public page such as `/docs` whose code is still loading
- **THEN** the spinner is shown until the page renders

### Requirement: Surface a failed page load
If a route's code fails to load (for example offline, or a stale deployment's chunk no longer
exists), the app SHALL show the error boundary's fallback with its retry control rather than a
blank screen, and SHALL recover when the user navigates to another route.

#### Scenario: Chunk load fails
- **WHEN** the network request for a route's page code fails
- **THEN** the error fallback is shown instead of a blank screen

#### Scenario: Recover by navigating
- **WHEN** the error fallback is shown for a failed in-app page and the user navigates to a
  different in-app route
- **THEN** the error state clears and the new page loads
