# Spec Delta

## ADDED Requirements

### Requirement: FAQ answers match actual behavior

The landing-page FAQ answers SHALL stay consistent with the app's real behavior and the other
public docs: ESPN cookies are needed for private ESPN leagues; stored ESPN cookies are removed once
none of the user's ESPN leagues has automatic refresh on; manual ESPN refresh is limited to once per
week per league during the season; and UI controls are named by their actual labels (for example
"Autofill cookies from ESPN").

#### Scenario: ESPN cookie answer is accurate

- **WHEN** a visitor expands "Why do I need to provide my ESPN cookies?"
- **THEN** the answer explains the cookies are required for private ESPN leagues, that they are
  stored only with automatic weekly refresh and removed once none of the user's ESPN leagues has it
  on, and the extension note refers to the "Autofill cookies from ESPN" button

#### Scenario: Refresh answer states the limits

- **WHEN** a visitor expands "My data looks outdated. How do I refresh it?"
- **THEN** the answer states that a manual ESPN refresh is available once per week per league
  during the season, rather than "anytime"
