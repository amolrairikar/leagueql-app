# Architecture

Diagram-as-code for the LeagueQL system architecture.

- [`architecture_diagram.py`](architecture_diagram.py) — the diagram, written with the
  [`diagrams`](https://diagrams.mingrammer.com/) library.
- `leagueql_architecture.png` — the rendered output (regenerate; do not hand-edit).

## Regenerate

```bash
pipenv install --dev diagrams   # one-time (already in the Pipfile dev deps)
brew install graphviz           # system binary the renderer shells out to
pipenv run python docs/architecture/architecture_diagram.py
```

## What it shows

- **Cloudflare edge** — the React SPA (`leagueql-app` worker) plus the `get-counts` /
  `sync-counts` workers that read the league count straight from DynamoDB.
- **AWS backend** — API Gateway → FastAPI Lambda, which fire-and-forget invokes the
  **onboarder → (S3 manifest event) → processor** async chain that writes precomputed views
  to DynamoDB. A prod-only SQS DLQ catches poison onboarder events.
- **Scheduled jobs** (EventBridge) — Sleeper refresh, player-metadata refresher, and the
  Sleeper stats Fargate task.
- **Ops** — SNS alerts fan out to the Discord notifier Lambda; API, onboarder, and processor
  export one end-to-end OpenTelemetry trace to Better Stack.

Keep this in sync with [`../requirements/`](../requirements/README.md) when the architecture
changes.
