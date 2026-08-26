# LeagueQL admin dashboard

A simple, read-only Streamlit dashboard for onboarding health, built from the
`METADATA` items in DynamoDB via **GSI3** (single `SK = "METADATA"` query — no
full-table scan).

It shows:

- **Total leagues onboarded**
- **Active leagues (14d)** — leagues whose `last_accessed_at` is within the last 14
  days (a missing `last_accessed_at` counts as inactive)
- **Leagues by platform** — ESPN vs SLEEPER horizontal bar
- **Cumulative leagues onboarded** — a line chart over `onboarded_at` with
  1M / 3M / 6M / YTD / 1Y / All range buttons embedded in the chart

## Running it

Point your terminal's AWS credentials at the **prod** account (the dashboard queries
`leagueql-table-prod`), then:

```bash
pipenv run streamlit run scripts/admin_dashboard/dashboard.py
```

Use the sidebar **Refresh data** button to re-query DynamoDB (results are otherwise
cached for 5 minutes).

## Layout

- `dashboard.py` — the Streamlit app (data access + charts).
- `aggregations.py` — pure aggregation helpers (no AWS/Streamlit), unit-tested in
  `tests/unit/scripts/test_admin_dashboard_aggregations.py`.
