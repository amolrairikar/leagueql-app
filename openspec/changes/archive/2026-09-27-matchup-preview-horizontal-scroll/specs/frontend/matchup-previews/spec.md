## ADDED Requirements

### Requirement: Horizontally scroll overflowing preview content
Each matchup preview card SHALL scroll horizontally on its own when its content (for example a
long team or owner name on a narrow mobile viewport) is wider than the available width, rather
than clipping the content off-screen. A card whose content fits SHALL stay at the available width,
so one overflowing card never widens the others. The Recent Form card's usernames SHALL wrap so
that card always fits the viewport. The preview's close button SHALL remain visible and fixed to
the preview's corner, outside every scrolling card.

#### Scenario: Long names scroll instead of clipping
- **WHEN** the preview is shown on a viewport too narrow to fit a team's long owner or team name
- **THEN** the card containing that name can be scrolled horizontally to reveal the full name, and
  no text is clipped

#### Scenario: Cards that fit do not scroll or widen
- **WHEN** one preview card overflows the available width but another card's content fits
- **THEN** only the overflowing card scrolls; the fitting card stays at the available width with no
  horizontal scrollbar or extra whitespace

#### Scenario: Recent form fits on mobile
- **WHEN** the preview is shown on a narrow viewport for a team with a long username
- **THEN** the Recent Form card wraps the username and fits the viewport without scrolling

#### Scenario: Close button stays reachable
- **WHEN** a preview card is horizontally scrollable
- **THEN** the close button remains visible at the preview's corner and is not scrolled or clipped
