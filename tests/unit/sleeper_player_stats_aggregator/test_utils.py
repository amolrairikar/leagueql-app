"""Tests for sleeper_player_stats_aggregator/utils.py."""

import json
import logging

import requests


class TestJsonFormatter:
    def test_format_returns_json_with_required_keys(self):
        import utils

        formatter = utils.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
            func="test_func",
        )
        result = json.loads(formatter.format(record))
        assert result["level"] == "INFO"
        assert result["message"] == "hello world"
        assert result["function"] == "test_func"
        assert "timestamp" in result


class TestBuildRetrySession:
    def test_returns_requests_session(self):
        import utils

        session = utils.build_retry_session()
        assert isinstance(session, requests.Session)

    def test_mounts_adapters_for_http_and_https(self):
        import utils

        session = utils.build_retry_session()
        assert "https://" in session.adapters
        assert "http://" in session.adapters
