"""Shared unit-test fixtures.

``common.job_status`` creates a module-level DynamoDB client at import time and is
imported by several Lambda handlers (onboarder, processor) as well as directly by
its own test module. Because Python caches the module, whichever test package
imports it first fixes which client instance every other package sees. This
session-autouse fixture forces that shared client to a mock so no test can make a
real AWS call regardless of collection/import order.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def _mock_common_job_status_client():
    # Import under a patched boto3 in case this is the first import (avoids
    # building a real client / needing a region); then pin the module global to a
    # mock for the whole session.
    with patch("boto3.client"):
        from common import job_status

    job_status._dynamodb = MagicMock()
    yield
