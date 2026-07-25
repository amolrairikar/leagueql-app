"""Runtime secret retrieval from AWS SSM Parameter Store.

Vendored into every function's deployment zip. Sensitive credentials (e.g. the
Axiom ingest token) are stored as **SecureString** SSM parameters and fetched at
cold start by parameter *name* — the name is passed via a non-sensitive env var,
so the secret value never appears in Lambda environment variables, the Terraform
state, or CI.
"""

import os

import boto3
import botocore.config

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_ssm_client = boto3.client("ssm", config=_retry_config)


def get_ssm_parameter(name: str) -> str:
    """Return the decrypted value of a SecureString SSM parameter.

    Args:
        name: The full SSM parameter name (e.g. ``/leagueql/prod/axiom/api_token``).

    Returns:
        The decrypted parameter value.
    """
    response = _ssm_client.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]


def get_secret_from_env_param(env_var: str) -> str:
    """Resolve a secret from the SSM parameter whose name is in ``env_var``.

    Returns ``""`` when the env var is unset so a module still imports cleanly in
    contexts where the secret is not configured (e.g. unit tests and local dev).
    This mirrors the previous ``os.environ.get(..., "")`` behavior while keeping
    the secret value out of the environment.

    Args:
        env_var: Name of the env var holding the SSM parameter *name*.

    Returns:
        The decrypted secret value, or ``""`` when the env var is unset.
    """
    param_name = os.environ.get(env_var)
    if not param_name:
        return ""
    return get_ssm_parameter(param_name)
