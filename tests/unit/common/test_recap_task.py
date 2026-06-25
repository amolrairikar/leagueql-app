"""Unit tests for the shared recap-generator task launcher (BE-022)."""

import json
from unittest.mock import MagicMock

import pytest

import common.recap_task as recap_task

_TASK_ENV = {
    "RECAP_TASK_CLUSTER": "leagueql-dev",
    "RECAP_TASK_DEFINITION": "arn:aws:ecs:us-east-1:1:task-definition/recap:3",
    "RECAP_TASK_SUBNETS": "subnet-a,subnet-b",
    "RECAP_TASK_SECURITY_GROUPS": "sg-1",
    "RECAP_TASK_CONTAINER": "recap-generator",
}


@pytest.fixture
def configured(monkeypatch):
    for k, v in _TASK_ENV.items():
        monkeypatch.setenv(k, v)


def _overrides_env(call):
    return {
        e["name"]: e["value"]
        for e in call.kwargs["overrides"]["containerOverrides"][0]["environment"]
    }


class TestRunRecapTask:
    def test_runs_task_with_network_and_env_overrides(self, configured):
        ecs = MagicMock()
        recap_task.run_recap_task(
            ecs, canonical_league_id="cid", platform="SLEEPER", correlation_id="corr-1"
        )
        ecs.run_task.assert_called_once()
        kwargs = ecs.run_task.call_args.kwargs
        assert kwargs["cluster"] == "leagueql-dev"
        assert kwargs["taskDefinition"] == _TASK_ENV["RECAP_TASK_DEFINITION"]
        assert kwargs["launchType"] == "FARGATE"
        net = kwargs["networkConfiguration"]["awsvpcConfiguration"]
        assert net["subnets"] == ["subnet-a", "subnet-b"]
        assert net["securityGroups"] == ["sg-1"]
        assert net["assignPublicIp"] == "ENABLED"
        env = _overrides_env(ecs.run_task.call_args)
        assert env["CANONICAL_LEAGUE_ID"] == "cid"
        assert env["PLATFORM"] == "SLEEPER"
        assert env["CORRELATION_ID"] == "corr-1"
        # Tracing disabled in tests → inject_context returns {} → "{}".
        assert json.loads(env["TRACE_CONTEXT"]) == {}
        # native_league_id omitted when not supplied.
        assert "NATIVE_LEAGUE_ID" not in env

    def test_includes_native_league_id_when_present(self, configured):
        ecs = MagicMock()
        recap_task.run_recap_task(
            ecs,
            canonical_league_id="cid",
            platform="ESPN",
            correlation_id="",
            native_league_id="999",
        )
        env = _overrides_env(ecs.run_task.call_args)
        assert env["NATIVE_LEAGUE_ID"] == "999"

    def test_noop_when_not_configured(self, monkeypatch):
        # No RECAP_TASK_* env (e.g. the non-east region) → never calls run_task.
        for k in _TASK_ENV:
            monkeypatch.delenv(k, raising=False)
        ecs = MagicMock()
        recap_task.run_recap_task(
            ecs, canonical_league_id="cid", platform="ESPN", correlation_id=""
        )
        ecs.run_task.assert_not_called()

    def test_failure_is_swallowed(self, configured):
        ecs = MagicMock()
        ecs.run_task.side_effect = RuntimeError("RunTask failed")
        # Must not raise — a failed launch never fails the caller.
        recap_task.run_recap_task(
            ecs, canonical_league_id="cid", platform="ESPN", correlation_id=""
        )
