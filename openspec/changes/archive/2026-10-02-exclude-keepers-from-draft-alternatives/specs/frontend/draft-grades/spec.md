## ADDED Requirements

### Requirement: Exclude keepers from suggested alternatives
The "Could have picked instead" alternatives for a bust SHALL exclude picks where `keeper` is true, because a keeper's draft slot was not open to other managers.

#### Scenario: Keeper not suggested as an alternative
- **WHEN** a better-scoring, same-position player drafted after a bust was a keeper
- **THEN** that player is not listed among the bust's alternatives, and if no non-keeper alternatives remain the bust shows no alternatives section

### Requirement: No alternatives for keeper busts
A bust pick where `keeper` is true SHALL show no "Could have picked instead" alternatives, while still counting as a bust.

#### Scenario: Keeper bust
- **WHEN** a pick flagged as a bust was a keeper
- **THEN** it is still marked and counted as a bust, but no alternatives section is shown for it
