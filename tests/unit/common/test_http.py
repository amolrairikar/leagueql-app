"""Tests for the shared src/common/http.py module."""

import requests

from common.http import build_retry_session


def test_build_retry_session_returns_session():
    assert isinstance(build_retry_session(), requests.Session)


def test_build_retry_session_mounts_retry_adapters():
    session = build_retry_session()
    for prefix in ("https://", "http://"):
        adapter = session.get_adapter(prefix)
        retry = adapter.max_retries
        assert retry.total == 3
        assert retry.backoff_factor == 1
        assert set(retry.status_forcelist) == {429, 500, 502, 503, 504}
        assert list(retry.allowed_methods) == ["GET"]
