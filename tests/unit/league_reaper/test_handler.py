from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

OLD = "2020-01-01T00:00:00+00:00"


def _league(canonical_id="abc", **overrides):
    return {
        "PK": f"LEAGUE#{canonical_id}",
        "SK": "METADATA",
        "onboarded_at": OLD,
        "platform": "SLEEPER",
        "league_name": "Old League",
        **overrides,
    }


def _wire(table, leagues, current=None, jobs=None):
    """GSI3 returns ``leagues``; consistent reads return ``current`` (default: same)."""
    table.query.return_value = {"Items": leagues}
    stored = {item["PK"]: item for item in (leagues if current is None else current)}

    def get_item(Key, ConsistentRead):
        assert ConsistentRead is True
        if Key["SK"] == "JOB_STATUS":
            item = (jobs or {}).get(Key["PK"])
        else:
            item = stored.get(Key["PK"])
        return {"Item": item} if item else {}

    table.get_item.side_effect = get_item


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("LEAGUE_REAPER_DRY_RUN", "false")


def _embed(mock_post):
    return mock_post.call_args.kwargs["json"]["embeds"][0]


def _fields(embed):
    return {f["name"]: f["value"] for f in embed["fields"]}


class TestDryRun:
    @pytest.mark.parametrize("value", [None, "", "true", "no", "0", "flase"])
    def test_anything_but_false_writes_nothing(
        self,
        handler,
        mock_table,
        mock_post,
        mock_deletion,
        context,
        monkeypatch,
        value,
    ):
        if value is None:
            monkeypatch.delenv("LEAGUE_REAPER_DRY_RUN", raising=False)
        else:
            monkeypatch.setenv("LEAGUE_REAPER_DRY_RUN", value)
        _wire(mock_table, [_league(platform="YAHOO", owner_user_id="u1")])

        handler.lambda_handler({}, context)

        mock_deletion.delete_league_raw_data.assert_not_called()
        mock_deletion.delete_all_league_items.assert_not_called()
        mock_table.delete_item.assert_not_called()
        embed = _embed(mock_post)
        assert "DRY RUN" in embed["title"]
        assert _fields(embed)["Would remove"] == "1"
        assert "Old League (YAHOO) `abc` last active 2020-01-01" in embed["description"]

    def test_false_is_case_insensitive(
        self, handler, mock_table, mock_post, mock_deletion, context, monkeypatch
    ):
        monkeypatch.setenv("LEAGUE_REAPER_DRY_RUN", "False")
        _wire(mock_table, [_league()])
        handler.lambda_handler({}, context)
        mock_deletion.delete_all_league_items.assert_called_once()


class TestRemoval:
    def test_deletes_raw_data_before_items(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(mock_table, [_league()])

        handler.lambda_handler({}, context)

        calls = [c[0] for c in mock_deletion.method_calls]
        assert calls == ["delete_league_raw_data", "delete_all_league_items"]
        assert mock_deletion.delete_league_raw_data.call_args.args[1:] == (
            "leagueql-bucket-test",
            "abc",
        )
        assert _fields(_embed(mock_post))["Removed"] == "1"

    def test_s3_failure_keeps_items_and_other_leagues_still_run(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(mock_table, [_league("bad"), _league("good")])
        mock_deletion.delete_league_raw_data.side_effect = [RuntimeError("s3"), 1]

        with pytest.raises(RuntimeError, match="Failed to remove 1"):
            handler.lambda_handler({}, context)

        mock_deletion.delete_all_league_items.assert_called_once_with(
            mock_table, "good"
        )
        embed = _embed(mock_post)
        assert _fields(embed)["Failed"] == "1"
        assert "Failed: `bad`" in embed["description"]

    def test_paginates_the_index(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(mock_table, [_league("a"), _league("b")])
        mock_table.query.side_effect = [
            {"Items": [_league("a")], "LastEvaluatedKey": {"PK": "LEAGUE#a"}},
            {"Items": [_league("b")]},
        ]
        handler.lambda_handler({}, context)
        assert mock_deletion.delete_all_league_items.call_count == 2

    def test_posts_nothing_when_nothing_is_eligible(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(mock_table, [_league(onboarded_at=datetime.now(UTC).isoformat())])
        handler.lambda_handler({}, context)
        mock_post.assert_not_called()
        mock_table.get_item.assert_not_called()

    def test_stops_before_the_time_floor(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(mock_table, [_league("a"), _league("b"), _league("c")])
        context.get_remaining_time_in_millis.side_effect = [900_000, 59_999]

        handler.lambda_handler({}, context)

        mock_deletion.delete_all_league_items.assert_called_once()
        assert _fields(_embed(mock_post))["Deferred"] == "2"

    def test_missing_webhook_raises_before_removing(
        self, handler, mock_table, mock_deletion, context, live
    ):
        with (
            patch.object(handler, "_WEBHOOK_URL", ""),
            pytest.raises(RuntimeError, match="webhook"),
        ):
            handler.lambda_handler({}, context)
        mock_table.query.assert_not_called()


class TestSafetyChecks:
    @pytest.mark.parametrize(
        "current",
        [[], [_league(last_accessed_at=datetime.now(UTC).isoformat())]],
        ids=["gone", "recently opened"],
    )
    def test_no_longer_eligible_on_consistent_read(
        self, handler, mock_table, mock_post, mock_deletion, context, live, current
    ):
        _wire(mock_table, [_league()], current=current)
        handler.lambda_handler({}, context)
        assert mock_deletion.method_calls == []
        mock_post.assert_not_called()

    @pytest.mark.parametrize(
        ("overrides", "jobs"),
        [
            (
                {"active_job_id": "j1"},
                {"JOB#j1": {"status": "IN_PROGRESS"}},
            ),
            (
                {
                    "lineup_backfill_lease_until": Decimal(
                        int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
                    )
                },
                None,
            ),
        ],
        ids=["job", "backfill lease"],
    )
    def test_busy_league_is_skipped(
        self,
        handler,
        mock_table,
        mock_post,
        mock_deletion,
        context,
        live,
        overrides,
        jobs,
    ):
        _wire(mock_table, [_league(**overrides)], jobs=jobs)
        handler.lambda_handler({}, context)
        assert mock_deletion.method_calls == []
        assert _fields(_embed(mock_post))["Skipped (busy)"] == "1"

    @pytest.mark.parametrize(
        "jobs", [None, {"JOB#j1": {"status": "COMPLETED"}}], ids=["expired", "done"]
    )
    def test_finished_job_and_expired_lease_do_not_block(
        self, handler, mock_table, mock_post, mock_deletion, context, live, jobs
    ):
        _wire(
            mock_table,
            [_league(active_job_id="j1", lineup_backfill_lease_until=Decimal(1))],
            jobs=jobs,
        )
        handler.lambda_handler({}, context)
        mock_deletion.delete_all_league_items.assert_called_once()


class TestCredentialCleanup:
    @pytest.mark.parametrize(
        ("overrides", "sk"),
        [
            ({"platform": "YAHOO"}, "YAHOO_OAUTH"),
            ({"platform": "ESPN"}, "ESPN_CREDENTIALS"),
            ({"platform": "ESPN", "active_platform": "YAHOO"}, "YAHOO_OAUTH"),
        ],
    )
    def test_removes_orphaned_credentials(
        self,
        handler,
        mock_table,
        mock_post,
        mock_deletion,
        context,
        live,
        overrides,
        sk,
    ):
        _wire(mock_table, [_league(owner_user_id="u1", **overrides)])
        handler.lambda_handler({}, context)
        mock_table.delete_item.assert_called_once_with(Key={"PK": "USER#u1", "SK": sk})

    @pytest.mark.parametrize(
        "overrides",
        [{"platform": "SLEEPER", "owner_user_id": "u1"}, {"platform": "YAHOO"}],
        ids=["sleeper", "no owner"],
    )
    def test_nothing_to_clean_up(
        self,
        handler,
        mock_table,
        mock_post,
        mock_deletion,
        context,
        live,
        overrides,
    ):
        _wire(mock_table, [_league(**overrides)])
        handler.lambda_handler({}, context)
        mock_table.delete_item.assert_not_called()

    def test_keeps_credentials_still_needed(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(mock_table, [_league(platform="ESPN", owner_user_id="u1")])
        mock_deletion.owner_has_other_optedin_espn_leagues.return_value = True
        handler.lambda_handler({}, context)
        mock_table.delete_item.assert_not_called()

    def test_excludes_every_league_removed_this_run(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(
            mock_table,
            [
                _league("a", platform="YAHOO", owner_user_id="u1"),
                _league("b", platform="YAHOO", owner_user_id="u1"),
            ],
        )
        excluded = []
        mock_deletion.owner_has_other_yahoo_leagues.side_effect = (
            lambda table, owner, ids: excluded.append(set(ids)) or "b" not in ids
        )

        handler.lambda_handler({}, context)

        assert excluded == [{"a"}, {"a", "b"}]
        mock_table.delete_item.assert_called_once()

    def test_cleanup_failure_does_not_fail_the_removal(
        self, handler, mock_table, mock_post, mock_deletion, context, live
    ):
        _wire(mock_table, [_league(platform="YAHOO", owner_user_id="u1")])
        mock_table.delete_item.side_effect = RuntimeError("boom")

        handler.lambda_handler({}, context)

        embed = _embed(mock_post)
        assert _fields(embed)["Removed"] == "1"
        assert "Credential cleanup failed: `abc`" in embed["description"]


class TestSummaryTruncation:
    def test_long_list_is_cut_off_with_a_count(self, handler):
        lines = [f"line {i:03d} " + "x" * 90 for i in range(100)]
        description = handler._build_description(lines)
        shown = description.split("\n")
        assert len(description) <= 4096
        assert shown[-1] == f"+{100 - (len(shown) - 1)} more"

    def test_problem_lines_survive_truncation(self, handler):
        leagues = [
            {
                "canonical_league_id": f"league-{i}",
                "league_name": "x" * 80,
                "platform": "SLEEPER",
                "last_activity": "2020-01-01",
            }
            for i in range(100)
        ]
        result = handler.RunResult(
            removed=leagues, failed=["bad"], cleanup_failed=["league-99"]
        )

        description = handler._build_embed(result, False, datetime.now(UTC))[
            "description"
        ]

        shown = description.split("\n")
        assert shown[:2] == [
            "❌ Failed: `bad`",
            "⚠️ Credential cleanup failed: `league-99`",
        ]
        assert shown[-1].endswith(" more")
        assert len(description) <= 4096
