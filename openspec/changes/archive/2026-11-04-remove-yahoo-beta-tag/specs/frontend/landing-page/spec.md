## ADDED Requirements

### Requirement: Render the marketing sections and supported platforms
`/` SHALL render the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer with the marketing header, responsively on mobile and desktop. The FAQ accordion SHALL appear between the "How it works" steps and the final CTA band. The "Works with" strip SHALL list ESPN, Sleeper, and Yahoo, without marking any platform with a "Beta" badge or tooltip.

#### Scenario: Full page render
- **WHEN** a visitor loads `/`
- **THEN** the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer render with the marketing header, laid out responsively

#### Scenario: No platform marked Beta
- **WHEN** a visitor loads `/` and the "Works with" strip renders
- **THEN** the ESPN, Sleeper, and Yahoo chips render with no "Beta" badge or tooltip

## REMOVED Requirements

### Requirement: Render the marketing sections
**Reason**: Yahoo is no longer in beta; the requirement is replaced by "Render the marketing sections and supported platforms", which drops the Beta badge.
**Migration**: None; the Beta badge and its tooltip are removed from the UI.
