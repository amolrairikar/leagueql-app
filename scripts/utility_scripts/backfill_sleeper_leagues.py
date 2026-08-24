"""
backfill_sleeper_leagues.py

Re-onboards every onboarded Sleeper league so the processor rebuilds **all** of its
precomputed views for **all** historical seasons. Use this after a processing change that
adds or alters a view for already-onboarded leagues (e.g. the backend/sleeper-transactions TRANSACTIONS view).

How it works
------------
For each Sleeper league (enumerated via the GSI2 ``platform=SLEEPER`` index, grouped by
canonical league id), the script asynchronously invokes the onboarder Lambda with:

  * ``requestType=REFRESH`` — reuses the existing ``canonical_league_id`` and preserves the
    league's METADATA (owner / members). A full ONBOARD would Put-overwrite
    METADATA, so REFRESH is used deliberately.
  * ``reprocess_all=True`` — stamps the manifest so the processor rebuilds every season's
    views from the raw season files already in S3, not just the latest season the normal
    refresh diff would pick.

The historical raw transaction data is already in S3 from the original onboards, so this is
a reprocess of existing raw data (the current season is also re-fetched as part of the
refresh). Idempotent — re-running simply rewrites the same items.

Environment & names
-------------------
Pass ``--environment dev|prod`` (default ``dev``); the script derives the names from the
Terraform convention in ``infrastructure/regional/main.tf``:

  * table   -> ``leagueql-table-{env}``
  * lambda  -> ``leagueql-onboarder-{env}``

``--table`` / ``--onboarder-lambda`` override the derivation.

Usage
-----
    # Dry-run against dev (default) — lists the leagues that would be re-onboarded
    pipenv run python scripts/utility_scripts/backfill_sleeper_leagues.py

    # Re-onboard every Sleeper league in prod
    pipenv run python scripts/utility_scripts/backfill_sleeper_leagues.py \
        --environment prod --execute

    # Target a single league (dry-run on dev). --league-id may be any league ID in a
    # renewed league's previous_league_id chain; it resolves to the canonical league.
    pipenv run python scripts/utility_scripts/backfill_sleeper_leagues.py --league-id 123456789

    # Re-onboard just that league in prod
    pipenv run python scripts/utility_scripts/backfill_sleeper_leagues.py \
        --environment prod --league-id 123456789 --execute
"""

import argparse
import logging
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

import boto3

# Make the shared ``common`` package importable so we reuse the exact onboarder-invoke
# payload contract the API and Sleeper auto-refresh use, rather than duplicating it.
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))
from common.onboarder_invoke import invoke_onboarder  # noqa: E402

TABLE_NAME_FMT = "leagueql-table-{env}"
ONBOARDER_LAMBDA_FMT = "leagueql-onboarder-{env}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def resolve_table(args) -> str:
    """The DynamoDB table name: explicit --table, else derived from --environment."""
    return args.table or TABLE_NAME_FMT.format(env=args.environment)


def resolve_onboarder_lambda(args) -> str:
    """The onboarder Lambda name: explicit --onboarder-lambda, else from --environment."""
    return args.onboarder_lambda or ONBOARDER_LAMBDA_FMT.format(env=args.environment)


def get_sleeper_leagues(ddb_client, table_name: str) -> list[dict]:
    """
    Enumerate every Sleeper league via GSI2, one entry per canonical league.

    Mirrors ``src/sleeper_refresh/utils.get_sleeper_leagues``: groups the per-season
    LEAGUE_LOOKUP rows by canonical_league_id and keeps the league_id of the most recent
    season (the one whose previous_league_id chain resolves the whole history).

    Returns:
        List of {"league_id", "canonical_league_id"} dicts.
    """
    items = []
    kwargs: dict = {
        "TableName": table_name,
        "IndexName": "GSI2",
        "KeyConditionExpression": "#p = :platform",
        "ExpressionAttributeNames": {"#p": "platform"},
        "ExpressionAttributeValues": {":platform": {"S": "SLEEPER"}},
    }
    while True:
        response = ddb_client.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    leagues_by_canonical = defaultdict(list)
    for item in items:
        canonical_league_id = item.get("canonical_league_id", {}).get("S")
        league_id = item.get("league_id", {}).get("S")
        seasons = item.get("seasons", {}).get("SS", [])
        if canonical_league_id and league_id and seasons:
            most_recent_season = max(seasons, key=int)
            leagues_by_canonical[canonical_league_id].append(
                {"league_id": league_id, "season": most_recent_season}
            )

    result = []
    for canonical_id, league_data in leagues_by_canonical.items():
        league_data.sort(key=lambda x: int(x["season"]), reverse=True)
        best = league_data[0]
        result.append(
            {"league_id": best["league_id"], "canonical_league_id": canonical_id}
        )
    return result


def resolve_single_league(
    ddb_client,
    table_name: str,
    *,
    league_id: str | None = None,
    canonical_league_id: str | None = None,
) -> list[dict]:
    """
    Resolve a single Sleeper league to the shape ``get_sleeper_leagues`` returns.

    Given a ``league_id`` (any ID in a renewed league's chain) or a
    ``canonical_league_id`` directly, returns a one-element list of
    ``{"league_id", "canonical_league_id"}`` — where ``league_id`` is the most-recent
    season's ID (the chain head), the correct ID to pass to a REFRESH — so it drops
    straight into the same invoke loop the full backfill uses.

    Args:
        ddb_client: A low-level boto3 DynamoDB client.
        table_name: The DynamoDB table name.
        league_id: The Sleeper league ID to target. Ignored when
            ``canonical_league_id`` is provided.
        canonical_league_id: The canonical league ID to target directly, skipping the
            LEAGUE_LOOKUP resolution.

    Returns:
        A one-element list on success, or an empty list (with an error logged) when the
        league can't be resolved or isn't among the onboarded Sleeper leagues.
    """
    if canonical_league_id is None:
        # Resolve canonical from the LEAGUE_LOOKUP item, matching the key contract in
        # src/api/helpers.py::lookup_league.
        pk = f"LEAGUE#{league_id}#PLATFORM#SLEEPER"
        response = ddb_client.get_item(
            TableName=table_name,
            Key={"PK": {"S": pk}, "SK": {"S": "LEAGUE_LOOKUP"}},
        )
        item = response.get("Item")
        resolved = item.get("canonical_league_id", {}).get("S") if item else None
        if not resolved:
            logger.error(
                "No LEAGUE_LOOKUP / canonical_league_id found for Sleeper league %s",
                league_id,
            )
            return []
        canonical_league_id = resolved

    # Reuse the full enumeration so the chain-head league_id selection is identical to
    # the fleet-wide backfill, then filter down to the requested canonical.
    for league in get_sleeper_leagues(ddb_client, table_name):
        if league["canonical_league_id"] == canonical_league_id:
            return [league]

    logger.error(
        "Canonical league %s not found among onboarded Sleeper leagues",
        canonical_league_id,
    )
    return []


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Re-onboard every Sleeper league so the processor rebuilds all views for all "
            "seasons. Dry-run unless --execute is passed."
        )
    )
    p.add_argument(
        "--environment",
        "--env",
        dest="environment",
        choices=("dev", "prod"),
        default="dev",
        help="Target environment; derives the table and lambda names (default: dev).",
    )
    p.add_argument(
        "--table",
        default=None,
        help="Override the DynamoDB table name (default: derived from --environment).",
    )
    p.add_argument(
        "--onboarder-lambda",
        default=None,
        help="Override the onboarder Lambda name (default: derived from --environment).",
    )
    p.add_argument(
        "--league-id",
        default=None,
        help=(
            "Target a single Sleeper league instead of all of them. May be any league "
            "ID in a renewed league's previous_league_id chain; it resolves to the "
            "canonical league (and its most-recent-season ID)."
        ),
    )
    p.add_argument(
        "--canonical-league-id",
        default=None,
        help=(
            "Target a single league by canonical ID directly, skipping the league-ID "
            "lookup. Takes precedence over --league-id."
        ),
    )
    p.add_argument("--region", default=None, help="AWS region (optional).")
    p.add_argument(
        "--throttle-seconds",
        type=float,
        default=0.0,
        help="Sleep between invocations to avoid a processor-Lambda thundering herd.",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Actually invoke the onboarder. Without this the script is dry-run.",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt before invoking.",
    )
    p.add_argument("--debug", action="store_true", help="Enable DEBUG logging.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    table_name = resolve_table(args)
    onboarder_lambda = resolve_onboarder_lambda(args)
    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    ddb_client = session.client("dynamodb")
    lambda_client = session.client("lambda")

    single_league = bool(args.league_id or args.canonical_league_id)
    if single_league:
        if args.league_id and args.canonical_league_id:
            logger.info(
                "Both --league-id and --canonical-league-id given; using canonical %s",
                args.canonical_league_id,
            )
        logger.info(
            "Resolving single Sleeper league: env=%s table=%s onboarder=%s league_id=%s "
            "canonical_league_id=%s",
            args.environment,
            table_name,
            onboarder_lambda,
            args.league_id,
            args.canonical_league_id,
        )
        leagues = resolve_single_league(
            ddb_client,
            table_name,
            league_id=args.league_id,
            canonical_league_id=args.canonical_league_id,
        )
    else:
        logger.info(
            "Enumerating Sleeper leagues: env=%s table=%s onboarder=%s",
            args.environment,
            table_name,
            onboarder_lambda,
        )
        leagues = get_sleeper_leagues(ddb_client, table_name)
    logger.info("Found %d Sleeper league(s) to re-onboard", len(leagues))
    for league in leagues:
        logger.info(
            "  league_id=%s canonical_league_id=%s",
            league["league_id"],
            league["canonical_league_id"],
        )

    if not leagues:
        logger.info("Nothing to do.")
        return

    if not args.execute:
        logger.info(
            "Dry-run complete. Re-run with --execute to re-onboard these %d league(s).",
            len(leagues),
        )
        return

    if not args.yes:
        confirm = input(
            f"Re-onboard {len(leagues)} Sleeper league(s) in '{args.environment}'? [y/N] "
        )
        if confirm.strip().lower() not in ("y", "yes"):
            logger.info("Aborted.")
            return

    invoked = 0
    for league in leagues:
        correlation_id = str(uuid.uuid4())
        try:
            response = invoke_onboarder(
                lambda_client=lambda_client,
                function_name=onboarder_lambda,
                body={"leagueId": league["league_id"], "platform": "SLEEPER"},
                request_type="REFRESH",
                canonical_league_id=league["canonical_league_id"],
                correlation_id=correlation_id,
                reprocess_all=True,
            )
            status_code = response.get("StatusCode")
            if status_code != 202:
                logger.error(
                    "Invocation for league %s returned status %s",
                    league["league_id"],
                    status_code,
                )
                continue
            invoked += 1
            logger.info(
                "Re-onboarded league_id=%s canonical_league_id=%s correlation_id=%s",
                league["league_id"],
                league["canonical_league_id"],
                correlation_id,
            )
        except Exception as exc:  # noqa: BLE001 - report and continue with the rest
            logger.error("Failed to invoke onboarder for league %s: %s", league, exc)
        if args.throttle_seconds:
            time.sleep(args.throttle_seconds)

    logger.info("Done. Invoked %d/%d league(s).", invoked, len(leagues))


if __name__ == "__main__":
    main()
