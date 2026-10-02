"""
backfill_leagues.py

Re-onboards onboarded leagues so the processor rebuilds **all** of their precomputed views
for **all** historical seasons. Use this after a processing change that adds or alters a
view for already-onboarded leagues (e.g. the backend/sleeper-transactions TRANSACTIONS view).

Supported platforms
-------------------
  * **SLEEPER** — public API; every onboarded league is eligible.
  * **YAHOO** — credentialed; the onboarder obtains the owner's linked OAuth token from the
    ``owner_user_id`` on the league's METADATA. Leagues with no owner are skipped.
  * **ESPN** — credentialed; only leagues with ``auto_refresh_enabled=true`` on METADATA are
    eligible, because opting in is what stores the owner's (encrypted) cookies. The onboarder
    resolves those cookies from ``owner_user_id``. Leagues without an owner are skipped. The
    ESPN client needs a latest season, so the league's most recent onboarded season is sent.

Selection mirrors the scheduled refresh (``src/league_refresh/utils.get_leagues_to_refresh``)
except that leagues are **not** skipped for being behind the current NFL season — a backfill
rebuilds completed leagues too.

How it works
------------
For each selected league (enumerated via the GSI2 ``platform=<PLATFORM>`` index, grouped by
canonical league id), the script asynchronously invokes the onboarder Lambda with:

  * ``requestType=REFRESH`` — reuses the existing ``canonical_league_id`` and preserves the
    league's METADATA (owner / members / auto-refresh opt-in). A full ONBOARD would
    Put-overwrite METADATA, so REFRESH is used deliberately.
  * ``reprocess_all=True`` — stamps the manifest so the processor rebuilds every season's
    views from the raw season files already in S3, not just the latest season the normal
    refresh diff would pick.

The historical raw data is already in S3 from the original onboards, so this is a reprocess
of existing raw data (the most recent season is also re-fetched as part of the refresh).
Idempotent — re-running simply rewrites the same items.

Environment & names
-------------------
Pass ``--environment dev|prod`` (default ``dev``); the script derives the names from the
Terraform convention in ``infrastructure/regional/main.tf``:

  * table   -> ``leagueql-table-{env}``
  * lambda  -> ``leagueql-onboarder-{env}``

``--table`` / ``--onboarder-lambda`` override the derivation.

Usage
-----
    # Dry-run against dev (default) — lists every eligible league on every platform
    pipenv run python scripts/utility_scripts/backfill_leagues.py

    # Re-onboard only Yahoo and ESPN leagues in prod
    pipenv run python scripts/utility_scripts/backfill_leagues.py \
        --environment prod --platform YAHOO --platform ESPN --execute

    # Target a single league (dry-run on dev). --league-id needs exactly one --platform and
    # may be any league ID in a renewed league's chain; it resolves to the canonical league.
    pipenv run python scripts/utility_scripts/backfill_leagues.py \
        --platform SLEEPER --league-id 123456789

    # Target a single league by canonical ID (searches the selected platforms)
    pipenv run python scripts/utility_scripts/backfill_leagues.py \
        --environment prod --canonical-league-id <uuid> --execute
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
# payload contract the API and league auto-refresh use, rather than duplicating it.
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))
from common.onboarder_invoke import invoke_onboarder

TABLE_NAME_FMT = "leagueql-table-{env}"
ONBOARDER_LAMBDA_FMT = "leagueql-onboarder-{env}"

SLEEPER = "SLEEPER"
YAHOO = "YAHOO"
ESPN = "ESPN"
PLATFORMS = (SLEEPER, YAHOO, ESPN)

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


def _query_platform_lookups(ddb_client, table_name: str, platform: str) -> list[dict]:
    """Query GSI2 for every LEAGUE_LOOKUP item of ``platform`` (paginated)."""
    items: list[dict] = []
    kwargs: dict = {
        "TableName": table_name,
        "IndexName": "GSI2",
        "KeyConditionExpression": "#p = :platform",
        "ExpressionAttributeNames": {"#p": "platform"},
        "ExpressionAttributeValues": {":platform": {"S": platform}},
    }
    while True:
        response = ddb_client.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


def _most_recent_leagues(items: list[dict]) -> list[dict]:
    """
    Group LEAGUE_LOOKUP ``items`` by canonical league and keep the league_id of the most
    recent season (the chain head whose previous_league_id chain resolves the whole history).

    Returns:
        List of {"league_id", "canonical_league_id", "season"} dicts, where ``season`` is
        the chain head's most recent onboarded season.
    """
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
        best = max(league_data, key=lambda x: int(x["season"]))
        result.append(
            {
                "league_id": best["league_id"],
                "canonical_league_id": canonical_id,
                "season": best["season"],
            }
        )
    return result


def _get_refresh_metadata(
    ddb_client, table_name: str, canonical_league_id: str
) -> tuple[str | None, bool]:
    """
    Read ``owner_user_id`` and ``auto_refresh_enabled`` from a canonical league's METADATA.

    Returns:
        ``(owner_user_id_or_None, auto_refresh_enabled)``.
    """
    response = ddb_client.get_item(
        TableName=table_name,
        Key={
            "PK": {"S": f"LEAGUE#{canonical_league_id}"},
            "SK": {"S": "METADATA"},
        },
        ProjectionExpression="owner_user_id, auto_refresh_enabled",
    )
    item = response.get("Item", {})
    owner_user_id = item.get("owner_user_id", {}).get("S")
    auto_refresh_enabled = item.get("auto_refresh_enabled", {}).get("BOOL", False)
    return owner_user_id, auto_refresh_enabled


def _to_target(ddb_client, table_name: str, platform: str, league: dict) -> dict | None:
    """
    Build the backfill target for one chain-head ``league`` of ``platform``, or ``None``
    (with the reason logged) when a credentialed league can't be refreshed.

    Returns:
        A {"platform", "league_id", "canonical_league_id", "owner_user_id", "season"} dict.
        ``owner_user_id`` is None for Sleeper; ``season`` is set only for ESPN.
    """
    target = {
        "platform": platform,
        "league_id": league["league_id"],
        "canonical_league_id": league["canonical_league_id"],
        "owner_user_id": None,
        "season": None,
    }
    if platform == SLEEPER:
        return target

    owner_user_id, auto_refresh_enabled = _get_refresh_metadata(
        ddb_client, table_name, league["canonical_league_id"]
    )
    if platform == ESPN and not auto_refresh_enabled:
        logger.info(
            "Skipping ESPN league %s: auto-refresh not enabled (no stored cookies)",
            league["league_id"],
        )
        return None
    if not owner_user_id:
        logger.info(
            "Skipping %s league %s: no owner_user_id on METADATA",
            platform,
            league["league_id"],
        )
        return None

    target["owner_user_id"] = owner_user_id
    if platform == ESPN:
        # The ESPN client requires a latest season; re-fetch the newest onboarded one.
        target["season"] = league["season"]
    return target


def get_leagues(ddb_client, table_name: str, platforms: tuple[str, ...]) -> list[dict]:
    """
    Enumerate every backfill-eligible league on ``platforms``, one per canonical league.

    Returns:
        List of target dicts (see ``_to_target``).
    """
    result = []
    for platform in platforms:
        items = _query_platform_lookups(ddb_client, table_name, platform)
        for league in _most_recent_leagues(items):
            target = _to_target(ddb_client, table_name, platform, league)
            if target is not None:
                result.append(target)
    return result


def resolve_single_league(
    ddb_client,
    table_name: str,
    platforms: tuple[str, ...],
    *,
    league_id: str | None = None,
    canonical_league_id: str | None = None,
) -> list[dict]:
    """
    Resolve a single league to the shape ``get_leagues`` returns.

    Given a ``league_id`` (any ID in a renewed league's chain; requires exactly one
    platform) or a ``canonical_league_id`` directly (searched across ``platforms``),
    returns a one-element list whose ``league_id`` is the most-recent season's ID (the
    chain head) — the correct ID to pass to a REFRESH — so it drops straight into the
    same invoke loop the full backfill uses.

    Args:
        ddb_client: A low-level boto3 DynamoDB client.
        table_name: The DynamoDB table name.
        platforms: The platforms to search. Must be a single platform when resolving by
            ``league_id``.
        league_id: The platform league ID to target. Ignored when
            ``canonical_league_id`` is provided.
        canonical_league_id: The canonical league ID to target directly, skipping the
            LEAGUE_LOOKUP resolution.

    Returns:
        A one-element list on success, or an empty list (with an error logged) when the
        league can't be resolved, isn't onboarded on the searched platforms, or is a
        credentialed league that can't be refreshed.
    """
    if canonical_league_id is None:
        if len(platforms) != 1:
            logger.error("--league-id requires exactly one --platform")
            return []
        (platform,) = platforms
        # Resolve canonical from the LEAGUE_LOOKUP item, matching the key contract in
        # src/api/helpers.py::lookup_league.
        response = ddb_client.get_item(
            TableName=table_name,
            Key={
                "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                "SK": {"S": "LEAGUE_LOOKUP"},
            },
        )
        item = response.get("Item")
        resolved = item.get("canonical_league_id", {}).get("S") if item else None
        if not resolved:
            logger.error(
                "No LEAGUE_LOOKUP / canonical_league_id found for %s league %s",
                platform,
                league_id,
            )
            return []
        canonical_league_id = resolved

    # Reuse the same chain-head selection as the fleet-wide backfill, then filter down to
    # the requested canonical before the (per-league) METADATA eligibility check.
    for platform in platforms:
        items = _query_platform_lookups(ddb_client, table_name, platform)
        for league in _most_recent_leagues(items):
            if league["canonical_league_id"] == canonical_league_id:
                target = _to_target(ddb_client, table_name, platform, league)
                return [target] if target is not None else []

    logger.error(
        "Canonical league %s not found among onboarded %s leagues",
        canonical_league_id,
        "/".join(platforms),
    )
    return []


def build_body(league: dict) -> dict:
    """The onboarder request body for a backfill target (``season`` only for ESPN)."""
    body = {"leagueId": league["league_id"], "platform": league["platform"]}
    if league["season"] is not None:
        body["season"] = league["season"]
    return body


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Re-onboard Sleeper, Yahoo, and auto-refresh-enabled ESPN leagues so the "
            "processor rebuilds all views for all seasons. Dry-run unless --execute is passed."
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
        "--platform",
        dest="platforms",
        action="append",
        type=str.upper,
        choices=PLATFORMS,
        default=None,
        help=(
            "Platform to backfill; repeat for several (default: all of "
            f"{', '.join(PLATFORMS)})."
        ),
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
            "Target a single league instead of all of them (requires exactly one "
            "--platform). May be any league ID in a renewed league's chain; it resolves "
            "to the canonical league (and its most-recent-season ID)."
        ),
    )
    p.add_argument(
        "--canonical-league-id",
        default=None,
        help=(
            "Target a single league by canonical ID directly, skipping the league-ID "
            "lookup (searches the selected platforms). Takes precedence over --league-id."
        ),
    )
    p.add_argument("--region", default=None, help="AWS region (optional).")
    p.add_argument(
        "--throttle-seconds",
        type=float,
        default=0.0,
        help=(
            "Sleep between invocations to avoid a processor-Lambda thundering herd and "
            "bursting the platform APIs."
        ),
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
    args = p.parse_args(argv)
    # De-duplicate while keeping PLATFORMS order; default to every platform.
    selected = set(args.platforms or PLATFORMS)
    args.platforms = tuple(pl for pl in PLATFORMS if pl in selected)
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    table_name = resolve_table(args)
    onboarder_lambda = resolve_onboarder_lambda(args)
    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    ddb_client = session.client("dynamodb")
    lambda_client = session.client("lambda")
    platforms_label = "/".join(args.platforms)

    single_league = bool(args.league_id or args.canonical_league_id)
    if single_league:
        if args.league_id and args.canonical_league_id:
            logger.info(
                "Both --league-id and --canonical-league-id given; using canonical %s",
                args.canonical_league_id,
            )
        logger.info(
            "Resolving single league: env=%s table=%s onboarder=%s platforms=%s "
            "league_id=%s canonical_league_id=%s",
            args.environment,
            table_name,
            onboarder_lambda,
            platforms_label,
            args.league_id,
            args.canonical_league_id,
        )
        leagues = resolve_single_league(
            ddb_client,
            table_name,
            args.platforms,
            league_id=args.league_id,
            canonical_league_id=args.canonical_league_id,
        )
    else:
        logger.info(
            "Enumerating leagues: env=%s table=%s onboarder=%s platforms=%s",
            args.environment,
            table_name,
            onboarder_lambda,
            platforms_label,
        )
        leagues = get_leagues(ddb_client, table_name, args.platforms)

    logger.info("Found %d league(s) to re-onboard", len(leagues))
    for league in leagues:
        logger.info(
            "  platform=%s league_id=%s canonical_league_id=%s%s",
            league["platform"],
            league["league_id"],
            league["canonical_league_id"],
            f" season={league['season']}" if league["season"] else "",
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
            f"Re-onboard {len(leagues)} {platforms_label} league(s) in "
            f"'{args.environment}'? [y/N] "
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
                body=build_body(league),
                request_type="REFRESH",
                canonical_league_id=league["canonical_league_id"],
                correlation_id=correlation_id,
                owner_user_id=league["owner_user_id"],
                reprocess_all=True,
            )
            status_code = response.get("StatusCode")
            if status_code != 202:
                logger.error(
                    "Invocation for %s league %s returned status %s",
                    league["platform"],
                    league["league_id"],
                    status_code,
                )
                continue
            invoked += 1
            logger.info(
                "Re-onboarded platform=%s league_id=%s canonical_league_id=%s "
                "correlation_id=%s",
                league["platform"],
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
