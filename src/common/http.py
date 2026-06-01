"""Shared HTTP helpers for LeagueQL Lambda functions.

Vendored into every function's deployment zip via the build script.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_retry_session() -> requests.Session:
    """
    Build a ``requests`` session that retries transient failures on GET.

    Retries up to 3 times with exponential backoff on connection errors and the
    retryable status codes 429/500/502/503/504, for both http and https.

    Returns:
        A configured ``requests.Session``.
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
