# Tasks

## 1. Processor

- [x] 1.1 Classify Yahoo playoff tiers by bracket path (`_classify_yahoo_playoff_tiers`).
- [x] 1.2 Credit Yahoo trade items as adds/drops on the receiving/sending teams.
- [x] 1.3 Store Yahoo `created` as epoch ms and resolve `week` from the season's week calendar.
- [x] 1.4 STANDINGS `champion` = winner of each season's last winners-bracket week.

## 2. Onboarder

- [x] 2.1 Fetch and parse each Yahoo season's week calendar (`game_weeks`).

## 3. Tests & quality

- [x] 3.1 Processor unit tests (tiers, single champion, trades, created, week) and onboarder tests.
- [x] 3.2 Run ruff, pytest, behave, and `openspec validate --all`.
- [x] 3.3 Document `LOSERS_CONSOLATION_LADDER` in `docs/db/dynamodb_spec.md`.
