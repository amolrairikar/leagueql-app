# Tasks

## 1. Onboarder

- [x] 1.1 In `src/onboarder/espn_client.py`, add `ESPN_BOXSCORE_SEASONS_ENDPOINT_FROM = 2018` and route `matchups` requests for seasons at or after it to the `seasons/{season}/segments/0/leagues/{id}` endpoint, keeping `leagueHistory` for every other `season <= V2_CUTOFF` request; verify with unit tests in `tests/unit/onboarder/test_espn_client.py` that 2018 matchup URLs use the seasons endpoint with `mBoxscore` and `scoringPeriodId`, 2018 non-matchup URLs use `leagueHistory`, and 2017 matchup URLs use `leagueHistory`

## 2. Processor coverage

- [x] 2.1 Add a processor unit test with a 2018-shaped matchup (matchup-period roster entries with `lineupSlotId` 0 and season-split stats); verify starters and bench are populated with the right fantasy positions and starter points sum to the team score

## 3. Checks

- [x] 3.1 Run `pipenv run ruff check --fix .`, `pipenv run ruff format .`, `pipenv run pytest tests/unit`, and `pipenv run behave tests/component`; verify everything passes
- [x] 3.2 Run `npx @fission-ai/openspec@latest validate fix-espn-2018-boxscores --strict`; verify it passes
