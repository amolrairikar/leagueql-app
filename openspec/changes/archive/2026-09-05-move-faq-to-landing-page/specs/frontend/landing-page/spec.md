## MODIFIED Requirements

### Requirement: Render the marketing sections
`/` SHALL render the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer with the marketing header, responsively on mobile and desktop. The FAQ accordion SHALL appear between the "How it works" steps and the final CTA band.

#### Scenario: Full page render
- **WHEN** a visitor loads `/`
- **THEN** the hero, product showcase, "Works with" strip, feature highlights, "How it works" steps, FAQ accordion, final CTA band, and footer render with the marketing header, laid out responsively

## ADDED Requirements

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
