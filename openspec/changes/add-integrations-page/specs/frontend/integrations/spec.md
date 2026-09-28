# Spec Delta

## Purpose

Give signed-in league members a page to browse integrations built on LeagueQL's league export and to submit their
own for maintainer review.

## ADDED Requirements

### Requirement: Gate the Integrations page behind a feature flag
When the `integrations` flag is on, the sidebar SHALL show an "Integrations" item in a "Community" group linking to
`/integrations`, and the route SHALL render the Integrations page. When the flag is off, the item SHALL be hidden and
visiting `/integrations` SHALL redirect to `/home`.

#### Scenario: Flag on
- **WHEN** the `integrations` flag is on and a signed-in user views the sidebar
- **THEN** a "Community" group with an "Integrations" item is shown, and following it renders the Integrations page

#### Scenario: Flag off
- **WHEN** the `integrations` flag is off
- **THEN** no "Integrations" item is shown, and navigating to `/integrations` lands on `/home`

### Requirement: Explain how integrations work
The page SHALL show a heading "Integrations", a short description, a "Submit your integration" button, and a
three-step "How it works" strip: export your league, plug it into something ("Upload it to an AI assistant, import
it into a sheet, or point a script at it."), and share what you built.

#### Scenario: Page header and steps
- **WHEN** the Integrations page loads
- **THEN** the heading, description, submit button, and the three steps in order are visible

### Requirement: List approved integrations
The page SHALL load approved integrations from `GET /integrations`, show a loading state while the request is in
flight, render the `featured` item (if any) as a featured card above the grid, and render every item as a card
showing its name, author handle, category, description, and the views it reads.

#### Scenario: Integrations render
- **WHEN** `GET /integrations` returns three items, one with `featured: true`
- **THEN** the featured item is shown in the featured card and all three appear as cards in the grid

#### Scenario: No featured item
- **WHEN** no returned item is featured
- **THEN** no featured card is shown and the grid still renders

#### Scenario: No integrations yet
- **WHEN** `GET /integrations` returns an empty list
- **THEN** the page shows an empty state inviting the user to submit the first integration

#### Scenario: Listing fails
- **WHEN** `GET /integrations` returns `5xx`
- **THEN** the page shows an inline error alert in place of the grid, and the submit button remains usable

### Requirement: Filter and search integrations
The page SHALL provide category chips (All, AI prompts, Dashboards, Spreadsheets, Bots, Notebooks) with per-category
counts and a search box matching name, description, and view names, applied together on the client, with a result
count and a no-matches state.

#### Scenario: Filter by category
- **WHEN** the user selects the "Bots" chip
- **THEN** only integrations in the `bot` category are shown and the result count updates

#### Scenario: Search by view name
- **WHEN** the user types `transactions` in the search box
- **THEN** only integrations whose name, description, or views match are shown

#### Scenario: No matches
- **WHEN** the active filter and search match nothing
- **THEN** a no-matches message is shown

### Requirement: Show integration details
Selecting a card or the featured card's "View setup" SHALL open a dialog with the integration's name, author,
category, description, numbered setup steps, the export files it reads (as `<season>_<view>.json`), a link to open
the project in a new tab, and — only when the integration has a prompt — the prompt text with a "Copy prompt"
button that changes to "Copied" after copying.

#### Scenario: Open details
- **WHEN** the user clicks an integration card
- **THEN** the detail dialog shows its setup steps, files read, and an external project link

#### Scenario: Copy prompt
- **WHEN** the integration has a prompt and the user clicks "Copy prompt"
- **THEN** the prompt is written to the clipboard and the button reads "Copied"

#### Scenario: No prompt
- **WHEN** the integration has no prompt
- **THEN** the dialog shows no prompt section and no copy button

### Requirement: Submit an integration for review
The "Submit your integration" dialog SHALL collect name, author handle, category, link, views read (checkboxes of the
export's views), description, setup steps (one per line), and — only when the category is AI prompt — a prompt, SHALL
disable submission while a request is in flight, and SHALL send the submission to `POST /integrations`. On success it
SHALL show a "Submitted for review" confirmation. On failure it SHALL keep the dialog and entered values and show the
error inline: the backend's message for `4xx` (including the daily-limit `429`), and a generic retry message for
`5xx`.

#### Scenario: Successful submission
- **WHEN** the user completes the form and submits, and `POST /integrations` returns `201`
- **THEN** the dialog shows "Submitted for review"

#### Scenario: Daily limit reached
- **WHEN** `POST /integrations` returns `429` with a limit message
- **THEN** the dialog shows that message inline and keeps the entered values

#### Scenario: Server failure
- **WHEN** `POST /integrations` returns `502`
- **THEN** the dialog shows an inline retry message and keeps the entered values

#### Scenario: Prompt field only for AI prompts
- **WHEN** the selected category is not AI prompt
- **THEN** the prompt field is hidden and no prompt is sent
