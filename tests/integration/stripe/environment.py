import importlib.util
import os
import sys
from pathlib import Path

import boto3
import requests

_HERE = Path(__file__).parent
_SRC = Path(__file__).parents[3] / "src"

_REQUIRED_ENV_VARS = [
    "TEST_SLEEPER_LEAGUE_ID",
    "AWS_ACCOUNT_ID",
    "API_BASE_URL",
    "CLERK_SECRET_KEY_SSM_PARAM",
    "TEST_CLERK_USER_ID",
    # The subscription-lifecycle scenarios drive Stripe sandbox directly (create a
    # test-mode subscription, then cancel it) so the deployed webhook converges
    # subscription_end_time onto the league — they need the dev secret key + price.
    "STRIPE_SECRET_KEY_SSM_PARAM",
    "STRIPE_PRICE_ID",
]


def _load_module(unique_name, path):
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Loaded here (not as a bare import) so the helper resolves regardless of how
# behave sets up sys.path. It only imports ``requests``, so it is safe at import.
mint_jwt = _load_module(
    "stripe_integration.clerk_auth", _HERE / "clerk_auth.py"
).mint_jwt


def before_all(context):
    # _SRC makes the shared ``common`` package importable (feature flag + SSM lookups).
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

    # Stripe billing is feature-flagged (BE-017) and the flag now lives in AWS
    # AppConfig (runtime, no redeploy). This suite exercises the deployed billing
    # endpoints + webhook, which only behave as tested when billing is ON; with the
    # flag OFF they 404 / no-op, so the whole suite is not applicable. Ask the
    # deployment itself via the public ``GET /feature-flags`` endpoint (the same
    # resolved AppConfig state the Lambdas enforce) and, when billing is off, skip
    # every scenario (see ``before_scenario``) without resolving any SSM secrets.
    api_base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    context.billing_enabled = False
    if api_base_url:
        try:
            resp = requests.get(f"{api_base_url}/feature-flags", timeout=10)
            resp.raise_for_status()
            context.billing_enabled = bool(resp.json().get("data", {}).get("billing"))
        except requests.RequestException:
            context.billing_enabled = False
    if not context.billing_enabled:
        return

    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    os.environ.setdefault("DYNAMODB_TABLE_NAME", "leagueql-table-dev")

    # Resolve the Clerk auth config used to mint the bearer token the deployed
    # billing endpoints authenticate against (the secret is a SecureString SSM
    # parameter, never in CI).
    from common.secrets import get_ssm_parameter

    context.clerk_secret_key = get_ssm_parameter(
        os.environ["CLERK_SECRET_KEY_SSM_PARAM"]
    )
    context.clerk_user_id = os.environ["TEST_CLERK_USER_ID"]
    context.clerk_template = os.environ.get("CLERK_JWT_TEMPLATE", "integration-tests")
    context.api_base_url = os.environ["API_BASE_URL"].rstrip("/")
    context.mint_jwt = mint_jwt

    # Stripe sandbox (test mode) credentials for the lifecycle scenarios. The
    # secret key is a SecureString SSM parameter (never in CI); the price is the
    # non-sensitive dev recurring price the subscription is created against.
    context.stripe_secret_key = get_ssm_parameter(
        os.environ["STRIPE_SECRET_KEY_SSM_PARAM"]
    )
    context.stripe_price_id = os.environ["STRIPE_PRICE_ID"]

    # The Stripe suite reads the league the onboarding suites already wrote — it
    # runs after them (CI ``needs``) so the LEAGUE_LOOKUP / METADATA records exist.
    context.test_league_id = os.environ["TEST_SLEEPER_LEAGUE_ID"]
    context.platform = "SLEEPER"
    context.table_name = "leagueql-table-dev"
    context.dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")


def before_scenario(context, scenario):
    # Billing feature-flagged off (BE-017): the deployed endpoints don't do billing,
    # so skip the scenario rather than asserting billing behavior that can't happen.
    if not getattr(context, "billing_enabled", True):
        scenario.skip(
            "Billing disabled (BE-017); Stripe integration suite not applicable"
        )
        return

    # Stripe objects a scenario creates in sandbox, torn down in after_scenario so
    # a lifecycle run leaves no dangling test-mode subscriptions/customers.
    context.cleanup_subscription_ids = []
    context.cleanup_customer_ids = []


def after_scenario(context, scenario):
    """Best-effort teardown of Stripe objects and subscription state a scenario wrote.

    Cancels any test-mode subscription and deletes any test customer created via
    the Stripe API, then strips the subscription attributes the webhook wrote to
    the league METADATA (plus the durable TRIAL_USED marker) so the shared dev
    league is left pristine for the next run / the billing scenarios. Failures
    are swallowed — teardown must never fail the run.
    """
    sub_ids = getattr(context, "cleanup_subscription_ids", [])
    cus_ids = getattr(context, "cleanup_customer_ids", [])
    if not (sub_ids or cus_ids):
        return

    import stripe

    stripe.api_key = context.stripe_secret_key
    for sub_id in sub_ids:
        try:
            stripe.Subscription.cancel(sub_id)
        except Exception:
            pass
    for cus_id in cus_ids:
        try:
            stripe.Customer.delete(cus_id)
        except Exception:
            pass

    canonical = getattr(context, "test_canonical_id", None)
    if not canonical:
        return
    try:
        context.dynamodb_client.update_item(
            TableName=context.table_name,
            Key={"PK": {"S": f"LEAGUE#{canonical}"}, "SK": {"S": "METADATA"}},
            UpdateExpression=(
                "REMOVE stripe_subscription_id, subscription_end_time, "
                "pending_checkout, trial_used"
            ),
        )
        context.dynamodb_client.delete_item(
            TableName=context.table_name,
            Key={
                "PK": {
                    "S": f"LEAGUE#{context.test_league_id}#PLATFORM#{context.platform}"
                },
                "SK": {"S": "TRIAL_USED"},
            },
        )
    except Exception:
        pass
