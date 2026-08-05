"""LeagueQL architecture diagram — as code.

Renders the LeagueQL system architecture to ``leagueql_architecture.png`` using the
`diagrams` library (https://diagrams.mingrammer.com/). It is a documentation artifact,
not application code: it captures how the frontend, AWS backend, async processing chain,
scheduled jobs, and external SaaS integrations fit together.

Usage (from repo root)::

    pipenv install --dev diagrams      # one-time; also needs the graphviz binary
    brew install graphviz              # system dependency for rendering
    pipenv run python docs/architecture/architecture_diagram.py

Keep this in sync with docs/requirements/ when the architecture changes.
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Fargate, Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import (
    Eventbridge,
    SimpleNotificationServiceSns,
    SimpleQueueServiceSqs,
)
from diagrams.aws.management import SystemsManagerParameterStore
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import S3
from diagrams.generic.blank import Blank
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Client, User
from diagrams.programming.framework import React
from diagrams.saas.cdn import Cloudflare
from diagrams.saas.chat import Discord
from diagrams.saas.identity import Auth0

GRAPH_ATTR = {
    "fontsize": "22",
    "labelloc": "t",
    "pad": "0.6",
    "nodesep": "0.6",
    "ranksep": "1.0",
    "splines": "spline",
}

# Edge styles
ASYNC = Edge(color="darkorange", style="dashed", label="async")
SCHED = Edge(color="purple", style="dotted", label="cron")
DATA = Edge(color="black")
TRACE = Edge(color="firebrick", style="dashed")

with Diagram(
    "LeagueQL — Application Architecture",
    filename="docs/architecture/leagueql_architecture",
    show=False,
    direction="LR",
    graph_attr=GRAPH_ATTR,
    outformat="png",
):
    user = User("Fantasy manager")

    with Cluster("External SaaS"):
        clerk = Auth0("Clerk\n(auth)")
        espn = Client("ESPN API")
        sleeper = Client("Sleeper API")
        # Text-only node (no vendor icon) for the OTEL / Better Stack observability backend.
        betterstack = Blank("OTEL\nBetter Stack (traces + RUM)")

    # ── Edge / Cloudflare tier ────────────────────────────────────────────────
    with Cluster("Cloudflare (edge)"):
        spa = React("React SPA\n(leagueql-app worker)")
        get_counts = Cloudflare("get-counts\nworker")
        sync_counts = Cloudflare("sync-counts\nworker (hourly cron)")
        counts_kv = Storage("Counts KV")

    ext = User("Chrome extension\n(ESPN cookie autofill)")

    # ── AWS backend ───────────────────────────────────────────────────────────
    with Cluster("AWS"):
        apigw = APIGateway("API Gateway")
        api = Lambda("API Lambda\n(FastAPI)")

        with Cluster("Async onboarding / processing chain"):
            onboarder = Lambda("Onboarder\nLambda")
            dlq = SimpleQueueServiceSqs("Onboarder DLQ\n(prod)")
            processor = Lambda("Processor Lambda\n(DuckDB transforms)")

        with Cluster("Scheduled jobs (EventBridge)"):
            evb = Eventbridge("EventBridge\nrules")
            sleeper_refresh = Lambda("Sleeper refresh\n(weekly)")
            player_meta = Lambda("Player metadata\nrefresher")
            stats_task = Fargate("Sleeper stats\nrefresher (Fargate)")

        discord_fn = Lambda("Discord notifier\nLambda")
        sns = SimpleNotificationServiceSns("SNS\n(alerts)")

        with Cluster("Data stores"):
            ddb = Dynamodb("DynamoDB\n(views, job status,\ncounts)")
            s3 = S3("S3\n(raw API payloads)")
            ssm = SystemsManagerParameterStore("SSM\n(flags + secrets)")

    discord = Discord("Discord\n(ops alerts)")

    # ── Request path ──────────────────────────────────────────────────────────
    user >> Edge(label="uses") >> spa
    ext >> Edge(label="autofills cookies") >> spa
    spa >> Edge(label="auth") >> clerk
    spa >> Edge(label="REST /leagues, /jobs") >> apigw >> api
    spa >> Edge(label="/counts") >> get_counts >> Edge(label="read") >> counts_kv
    # sync-counts refreshes the KV cache from DynamoDB on an hourly Cloudflare cron.
    sync_counts >> SCHED >> counts_kv
    sync_counts >> Edge(label="read counts") >> ddb
    spa >> TRACE >> betterstack  # RUM + OTLP via same-origin worker proxy

    # ── API → async chain ─────────────────────────────────────────────────────
    api >> ASYNC >> onboarder
    api >> DATA >> ddb  # job status, metadata reads/writes
    onboarder >> Edge(label="poison") >> dlq
    onboarder >> Edge(label="fetch seasons") >> [espn, sleeper]
    onboarder >> Edge(label="raw payloads +\nmanifest.json") >> s3
    (
        s3
        >> Edge(color="darkorange", style="dashed", label="S3 event\n(manifest)")
        >> processor
    )
    processor >> Edge(label="precomputed views") >> ddb

    # ── Scheduled jobs ────────────────────────────────────────────────────────
    evb >> SCHED >> [sleeper_refresh, player_meta, stats_task]
    sleeper_refresh >> ASYNC >> onboarder
    # Player metadata + Sleeper stats land in S3; the processor reads both prefixes
    # (alongside the raw payloads) when building precomputed views.
    player_meta >> Edge(label="player metadata\nJSON") >> s3
    stats_task >> Edge(label="player stats\nJSON") >> s3

    # ── Alerting & config ─────────────────────────────────────────────────────
    sns >> discord_fn >> Edge(label="webhook URL from SSM") >> discord
    [onboarder, processor, api] >> Edge(color="gray", style="dotted") >> sns
    [api, onboarder, processor] >> Edge(color="gray", style="dotted") >> ssm

    # ── Distributed tracing (one end-to-end trace → Better Stack) ─────────────
    [api, onboarder, processor] >> TRACE >> betterstack
