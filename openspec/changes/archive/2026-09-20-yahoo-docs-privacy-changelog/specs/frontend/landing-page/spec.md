# Spec Delta

## MODIFIED Requirements

### Requirement: Render the marketing sections
`/` SHALL render the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer with the marketing header, responsively on mobile and desktop. The FAQ accordion SHALL appear between the "How it works" steps and the final CTA band. The "Works with" strip SHALL list ESPN, Sleeper, and Yahoo, and SHALL mark Yahoo with a "Beta" badge indicating its support is newly released.

#### Scenario: Full page render
- **WHEN** a visitor loads `/`
- **THEN** the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer render with the marketing header, laid out responsively

#### Scenario: Yahoo marked Beta in the Works with strip
- **WHEN** a visitor loads `/` and the "Works with" strip renders
- **THEN** the Yahoo platform chip carries a "Beta" badge, while ESPN and Sleeper do not
