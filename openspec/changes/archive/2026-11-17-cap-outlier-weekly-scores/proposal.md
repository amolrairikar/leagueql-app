## Why

A single freak high-scoring week can swing a team's power score: it feeds both the season points total (30%) and the three-week recent-form mean (20%), and the min–max scaling then stretches the whole league around it. A last-place team has ranked 5th on the strength of one huge week.

## What Changes

- Before computing the points-scored and recent-form components, each team-week score is capped at the league's median + 2 robust standard deviations (1.4826 × the median absolute deviation) of all played team-weeks through the cut week. Scores below the cap are unchanged.
- The cap affects only those two components. Record, lineup efficiency, displayed records, points-for tiebreaks and record rank are unchanged.
- Weights and min–max scaling are unchanged.

## Capabilities

### Modified Capabilities
- `frontend/power-rankings`: points scored and recent form use outlier-capped weekly scores.

## Impact

Frontend only: `frontend/src/features/power_rankings/compute-power-rankings.ts`, its unit tests, and the component description text.
