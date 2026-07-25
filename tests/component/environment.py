"""Behave environment for LeagueQL **component** tests.

Component tests exercise whole components (the onboarder->processor chain, the
FastAPI app, the Sleeper auto-refresh Lambda) with every *external* dependency
mocked:

* **AWS** (DynamoDB, S3) is backed by ``moto`` (``mock_aws``) — an in-memory
  AWS, so the pipeline really writes to and reads back from S3/DynamoDB without
  touching a cloud account. This is what makes a true round-trip chain test
  possible.
* **Platform HTTP** (ESPN/Sleeper) is patched per scenario in the step
  definitions (the platform API client is replaced with a fake that returns
  fixture payloads).

This mirrors the module-loading pattern in ``tests/integration/environment.py``
(loading Lambda handlers that share bare module names like ``utils``/``handler``
via ``importlib`` and stashing the handler references on ``context``), but swaps
the real dev AWS stack for moto. Unlike the unit tests, modules are imported
*after* moto starts, so every module-level ``boto3`` client is moto-backed with
no per-module patching.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import boto3
from moto import mock_aws

_ROOT = Path(__file__).parents[2]
_SRC = _ROOT / "src"
_API_SRC = _SRC / "api"

TABLE_NAME = "leagueql-table-test"
BUCKET_NAME = "leagueql-test-bucket"
REGION = "us-east-1"
# Default authenticated caller for API scenarios; the shared seeding step records
# this user as the league owner so owner-gated endpoints pass (LQL-01 / BE-016).
DEFAULT_USER = "owner_user"

# Environment the modules read at import time. Set before any handler import.
_ENV = {
    "DYNAMODB_TABLE_NAME": TABLE_NAME,
    "S3_BUCKET_NAME": BUCKET_NAME,
    # BE-010: player metadata refresher writes the Sleeper players cache here.
    "PLAYER_METADATA_S3_KEY": "player-metadata/sleeper_nfl_players.json",
    "ONBOARDER_LAMBDA_NAME": "onboarder-test",
    "AWS_DEFAULT_REGION": REGION,
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SECURITY_TOKEN": "testing",
    "AWS_SESSION_TOKEN": "testing",
}


def _load_module(unique_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _stub_newrelic() -> None:
    """The API and processor import ``newrelic``; stub it so it is a no-op."""
    nr = MagicMock()
    nr.agent.ASGIApplicationWrapper.side_effect = lambda app: app
    nr.agent.background_task.return_value = lambda f: f
    sys.modules.setdefault("newrelic", nr)
    sys.modules.setdefault("newrelic.agent", nr.agent)


def _create_table() -> None:
    client = boto3.client("dynamodb", region_name=REGION)
    client.create_table(
        TableName=TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "canonical_league_id", "AttributeType": "S"},
            {"AttributeName": "platform", "AttributeType": "S"},
            {"AttributeName": "league_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "canonical_league_id", "KeyType": "HASH"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["seasons", "PK"],
                },
            },
            {
                "IndexName": "GSI2",
                "KeySchema": [
                    {"AttributeName": "platform", "KeyType": "HASH"},
                    {"AttributeName": "league_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )


def _create_bucket() -> None:
    client = boto3.client("s3", region_name=REGION)
    client.create_bucket(Bucket=BUCKET_NAME)
    # The processor reads the previous manifest version via list_object_versions,
    # so the bucket must be versioned (matches the deployed bucket).
    client.put_bucket_versioning(
        Bucket=BUCKET_NAME,
        VersioningConfiguration={"Status": "Enabled"},
    )


def _load_handlers(context) -> None:
    """Load every Lambda handler + the API once, stashing refs on ``context``.

    Bare module names (``utils``, ``queries``, ``handler``) are shared across
    source dirs, so each component is loaded with its bare-name imports resolved,
    then the handler reference is captured on ``context`` — steps always reach
    handlers through ``context`` and never the (last-writer-wins) bare names.
    """
    # ``common`` (shared package) and the API top-level modules must be importable.
    for path in (_SRC, _API_SRC):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    # --- onboarder ---------------------------------------------------------
    onboarder_pkg = types.ModuleType("onboarder")
    onboarder_pkg.__path__ = [str(_SRC / "onboarder")]
    sys.modules["onboarder"] = onboarder_pkg
    onboarder_utils = _load_module("onboarder.utils", _SRC / "onboarder" / "utils.py")
    sys.modules["utils"] = onboarder_utils
    sys.modules["writer"] = _load_module(
        "onboarder.writer", _SRC / "onboarder" / "writer.py"
    )
    sys.modules["espn_client"] = _load_module(
        "onboarder.espn_client", _SRC / "onboarder" / "espn_client.py"
    )
    sys.modules["sleeper_client"] = _load_module(
        "onboarder.sleeper_client", _SRC / "onboarder" / "sleeper_client.py"
    )
    onboarding_service = _load_module(
        "onboarding_service", _SRC / "onboarder" / "onboarding_service.py"
    )
    context.onboarding_service_mod = onboarding_service
    context.sleeper_client_mod = sys.modules["sleeper_client"]
    context.onboarder_handler = _load_module(
        "onboarder.handler", _SRC / "onboarder" / "handler.py"
    )

    # --- processor (overwrites bare ``utils``/``queries`` for its own load) -
    processor_pkg = types.ModuleType("processor")
    processor_pkg.__path__ = [str(_SRC / "processor")]
    sys.modules["processor"] = processor_pkg
    sys.modules["utils"] = _load_module(
        "processor.utils", _SRC / "processor" / "utils.py"
    )
    sys.modules["queries"] = _load_module(
        "processor.queries", _SRC / "processor" / "queries.py"
    )
    context.processor_handler = _load_module(
        "processor.handler", _SRC / "processor" / "handler.py"
    )

    # --- sleeper_refresh (overwrites bare ``utils`` for its own load) -------
    refresh_pkg = types.ModuleType("sleeper_refresh")
    refresh_pkg.__path__ = [str(_SRC / "sleeper_refresh")]
    sys.modules["sleeper_refresh"] = refresh_pkg
    sys.modules["utils"] = _load_module(
        "sleeper_refresh.utils", _SRC / "sleeper_refresh" / "utils.py"
    )
    context.refresh_utils_mod = sys.modules["utils"]
    context.refresh_handler = _load_module(
        "sleeper_refresh.handler", _SRC / "sleeper_refresh" / "handler.py"
    )

    # --- API (main/helpers/routes are plain top-level modules) -------------
    import main  # noqa: F811  (resolved via _API_SRC on sys.path)

    # No real Lambda exists under moto[s3,dynamodb]; the API only needs to record
    # that it *would* invoke the onboarder, so stub the Lambda client.
    main.lambda_client = MagicMock()
    context.main = main
    context.lambda_client = main.lambda_client

    from fastapi.testclient import TestClient

    context.api = TestClient(main.app, raise_server_exceptions=False)

    # --- player metadata refresher (BE-010) --------------------------------
    pm_pkg = types.ModuleType("player_metadata")
    pm_pkg.__path__ = [str(_SRC / "player_metadata")]
    sys.modules["player_metadata"] = pm_pkg
    sys.modules["utils"] = _load_module(
        "player_metadata.utils", _SRC / "player_metadata" / "utils.py"
    )
    context.player_metadata_handler = _load_module(
        "player_metadata.handler", _SRC / "player_metadata" / "handler.py"
    )


def before_all(context):
    _stub_newrelic()
    for key, value in _ENV.items():
        # Always set (not setdefault) so a stray real value can't leak in.
        import os

        os.environ[key] = value

    context._moto = mock_aws()
    context._moto.start()
    _create_table()
    _create_bucket()

    context.region = REGION
    context.table_name = TABLE_NAME
    context.bucket_name = BUCKET_NAME
    context.ddb = boto3.client("dynamodb", region_name=REGION)
    context.ddb_resource = boto3.resource("dynamodb", region_name=REGION)
    context.s3 = boto3.client("s3", region_name=REGION)

    _load_handlers(context)


def _clear_table(context) -> None:
    table = context.ddb_resource.Table(TABLE_NAME)
    scan = table.scan(ProjectionExpression="PK, SK")
    with table.batch_writer() as writer:
        for item in scan.get("Items", []):
            writer.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})


def _clear_bucket(context) -> None:
    versions = context.s3.list_object_versions(Bucket=BUCKET_NAME)
    to_delete = [
        {"Key": v["Key"], "VersionId": v["VersionId"]}
        for v in versions.get("Versions", []) + versions.get("DeleteMarkers", [])
    ]
    if to_delete:
        context.s3.delete_objects(Bucket=BUCKET_NAME, Delete={"Objects": to_delete})


def before_scenario(context, scenario):
    # Reset the API's Lambda-invoke spy each scenario so payload assertions are
    # scoped to the scenario under test.
    context.main.lambda_client.reset_mock()
    # Reset feature flags to all-off (the app's fail-safe default) each scenario;
    # scenarios that need a flag ON opt in via ``feature_flags._override_for_testing``.
    from common import feature_flags

    feature_flags._override_for_testing({})
    # Per-scenario ``mock.patch`` handles (started in steps) to stop on teardown.
    context._patches = []
    # Every league route now sits behind the Clerk JWT dependency (LQL-01 /
    # BE-016). Authenticate as the default owner so owner-gated endpoints pass;
    # the shared seeding step records DEFAULT_USER as the league owner. Steps that
    # need a different caller layer their own ``patch.dict`` override on top.
    import routes

    context.default_user = DEFAULT_USER
    context.main.app.dependency_overrides[routes.get_authenticated_user] = lambda: (
        DEFAULT_USER
    )


def after_scenario(context, scenario):
    for patcher in getattr(context, "_patches", []):
        patcher.stop()
    context._patches = []
    import routes

    context.main.app.dependency_overrides.pop(routes.get_authenticated_user, None)
    _clear_table(context)
    _clear_bucket(context)


def after_all(context):
    context._moto.stop()
