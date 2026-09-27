# Spec Delta

## MODIFIED Requirements

### Requirement: Nightly onboarding-health digest
The job SHALL run on a nightly schedule, query the GSI3 all-leagues index for every METADATA item
(paginating until exhausted), and post exactly one Discord message reporting the total leagues
onboarded, the number of active leagues (accessed within the last 14 days), the number of stale
leagues (not refreshed within the last 365 days), the ESPN / SLEEPER / YAHOO platform split, and
the count of new leagues onboarded within the last 24 hours, 7 days, and 30 days.

#### Scenario: Nightly run posts the digest
- **WHEN** the scheduled run executes and the query returns onboarded leagues
- **THEN** it posts a single Discord message containing the total onboarded count, the active-leagues (14d) count, the stale-leagues (1y) count, the ESPN, SLEEPER, and YAHOO counts, and the 24h/7d/30d new-onboard counts

#### Scenario: Yahoo leagues appear in the platform split
- **WHEN** the query returns onboarded leagues on ESPN, SLEEPER, and YAHOO
- **THEN** the digest reports each platform's count in a single `ESPN / SLEEPER / YAHOO` field, and the three counts sum to the total onboarded count

#### Scenario: Unrecognized platform is excluded from the split
- **WHEN** a league's effective platform is missing or is not ESPN, SLEEPER, or YAHOO
- **THEN** it is not counted under any platform in the split

#### Scenario: All METADATA items are counted across pages
- **WHEN** the GSI3 query returns results across multiple pages (a `LastEvaluatedKey` is present)
- **THEN** the run continues paginating and aggregates every METADATA item into the reported counts

#### Scenario: No onboarded leagues
- **WHEN** the query returns no METADATA items
- **THEN** the run still posts a digest with all counts equal to zero (including a `0 / 0 / 0` platform split) rather than raising
