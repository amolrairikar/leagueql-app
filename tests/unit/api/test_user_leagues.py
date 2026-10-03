"""Tests for GET /me/leagues and its listing helper (backend/user-leagues)."""

from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

TABLE = "test-table"


def _member(canonical):
    return {"PK": f"LEAGUE#{canonical}", "SK": "MEMBER#user_1"}


def _lookup(league_id, platform, seasons):
    item = {"PK": f"LEAGUE#{league_id}#PLATFORM#{platform}"}
    if seasons is not None:
        item["seasons"] = set(seasons)
    return item


def _metadata(canonical, **attrs):
    return {"PK": f"LEAGUE#{canonical}", "SK": "METADATA", **attrs}


class _Store:
    """Fakes the GSI4 / GSI1 queries and METADATA BatchGetItem behind main.table."""

    def __init__(self, mock_table, members, lookups, metadata):
        self.members = members  # list of pages (each a list of canonical ids)
        self.lookups = lookups  # canonical -> list of lookup items
        self.metadata = metadata  # canonical -> METADATA item
        mock_table.query.side_effect = self.query
        self.resource = MagicMock()
        self.resource.batch_get_item.side_effect = self.batch_get

    def query(self, **kwargs):
        if kwargs["IndexName"] == "GSI4":
            page = kwargs.get("ExclusiveStartKey", {}).get("page", 0)
            response = {"Items": [_member(c) for c in self.members[page]]}
            if page + 1 < len(self.members):
                response["LastEvaluatedKey"] = {"page": page + 1}
            return response
        canonical = kwargs["KeyConditionExpression"].get_expression()["values"][1]
        return {"Items": self.lookups.get(canonical, [])}

    def batch_get(self, RequestItems):
        keys = RequestItems[TABLE]["Keys"]
        items = [
            self.metadata[k["PK"].removeprefix("LEAGUE#")]
            for k in keys
            if k["PK"].removeprefix("LEAGUE#") in self.metadata
        ]
        return {"Responses": {TABLE: items}}


@pytest.fixture
def store(mock_table):
    def _make(members, lookups=None, metadata=None):
        s = _Store(mock_table, members, lookups or {}, metadata or {})
        p = patch("main.dynamodb_resource", s.resource)
        p.start()
        _make.patches.append(p)
        return s

    _make.patches = []
    with patch("main.DYNAMODB_TABLE_NAME", TABLE):
        yield _make
    for p in _make.patches:
        p.stop()


def _no_reauth(_uid):
    raise AssertionError("re-auth status must not be read")


class TestListUserLeagues:
    def _list(self, reauth=_no_reauth):
        from main import list_user_leagues

        return list_user_leagues("user_1", reauth)

    def test_no_leagues_returns_empty_without_batch_get(self, store):
        s = store([[]])
        assert self._list() == []
        s.resource.batch_get_item.assert_not_called()

    def test_sorted_newest_first_and_paginates_index(self, store):
        store(
            [["a"], ["b"]],
            lookups={
                "a": [_lookup("1", "SLEEPER", ["2024"])],
                "b": [_lookup("2", "ESPN", ["2023", "2024"])],
            },
            metadata={
                "a": _metadata(
                    "a",
                    platform="SLEEPER",
                    league_name="A",
                    onboarded_at="2024-01-01T00:00:00Z",
                ),
                "b": _metadata(
                    "b",
                    platform="ESPN",
                    league_name="B",
                    onboarded_at="2023-01-01T00:00:00Z",
                    last_refresh_at="2025-01-01T00:00:00Z",
                ),
            },
        )
        leagues = self._list()
        assert [lg["league_name"] for lg in leagues] == ["B", "A"]
        assert leagues[0] == {
            "league_id": "2",
            "platform": "ESPN",
            "league_name": "B",
            "seasons": ["2023", "2024"],
            "updated_at": "2025-01-01T00:00:00Z",
            "migrated_from": None,
            "espn_reauth_required": False,
        }
        # Never refreshed → updated_at falls back to onboarded_at.
        assert leagues[1]["updated_at"] == "2024-01-01T00:00:00Z"

    def test_migrated_league_uses_latest_destination_lookup(self, store):
        store(
            [["m"]],
            lookups={
                "m": [
                    _lookup("900", "ESPN", ["2021", "2022"]),
                    _lookup("111", "SLEEPER", ["2023"]),
                    _lookup("222", "SLEEPER", ["2024"]),
                    # A pending renewal (no seasons) is ignored.
                    _lookup("333", "SLEEPER", None),
                ]
            },
            metadata={
                "m": _metadata(
                    "m",
                    platform="ESPN",
                    active_platform="SLEEPER",
                    migrated_from="ESPN",
                    onboarded_at="2021-01-01T00:00:00Z",
                )
            },
        )
        [league] = self._list()
        assert league["league_id"] == "222"
        assert league["platform"] == "SLEEPER"
        assert league["migrated_from"] == "ESPN"
        assert league["seasons"] == ["2021", "2022", "2023", "2024"]
        assert league["league_name"] is None

    def test_skips_missing_metadata_and_unusable_lookups(self, store):
        store(
            [["gone", "nolookup", "ok"]],
            lookups={
                "nolookup": [_lookup("5", "SLEEPER", None)],
                "ok": [_lookup("6", "SLEEPER", ["2024"])],
            },
            metadata={
                "nolookup": _metadata("nolookup", platform="SLEEPER"),
                "ok": _metadata("ok", platform="SLEEPER", onboarded_at="x"),
            },
        )
        assert [lg["league_id"] for lg in self._list()] == ["6"]

    def test_reauth_flag_only_for_owned_auto_refreshed_espn(self, store):
        store(
            [["own1", "own2", "member", "manual"]],
            lookups={
                c: [_lookup(c, "ESPN", ["2024"])]
                for c in ["own1", "own2", "member", "manual"]
            },
            metadata={
                "own1": _metadata(
                    "own1",
                    platform="ESPN",
                    owner_user_id="user_1",
                    auto_refresh_enabled=True,
                    onboarded_at="4",
                ),
                "own2": _metadata(
                    "own2",
                    platform="ESPN",
                    owner_user_id="user_1",
                    auto_refresh_enabled=True,
                    onboarded_at="3",
                ),
                "member": _metadata(
                    "member",
                    platform="ESPN",
                    owner_user_id="other",
                    auto_refresh_enabled=True,
                    onboarded_at="2",
                ),
                "manual": _metadata(
                    "manual",
                    platform="ESPN",
                    owner_user_id="user_1",
                    auto_refresh_enabled=False,
                    onboarded_at="1",
                ),
            },
        )
        reauth = MagicMock(return_value=(True, "2026-01-01T00:00:00Z"))
        flags = {
            lg["league_id"]: lg["espn_reauth_required"] for lg in self._list(reauth)
        }
        assert flags == {"own1": True, "own2": True, "member": False, "manual": False}
        reauth.assert_called_once_with("user_1")

    def test_chunks_batch_get_to_100_keys(self, store):
        ids = [f"c{i}" for i in range(150)]
        s = store([ids])
        assert self._list() == []
        sizes = [
            len(c.kwargs["RequestItems"][TABLE]["Keys"])
            for c in s.resource.batch_get_item.call_args_list
        ]
        assert sizes == [100, 50]

    def test_retries_unprocessed_keys(self, store):
        s = store(
            [["a"]],
            lookups={"a": [_lookup("1", "SLEEPER", ["2024"])]},
            metadata={"a": _metadata("a", platform="SLEEPER", onboarded_at="x")},
        )
        unprocessed = {TABLE: {"Keys": [{"PK": "LEAGUE#a", "SK": "METADATA"}]}}
        s.resource.batch_get_item.side_effect = [
            {"Responses": {TABLE: []}, "UnprocessedKeys": unprocessed},
            {"Responses": {TABLE: [s.metadata["a"]]}},
        ]
        with patch("helpers.time.sleep"):
            assert [lg["league_id"] for lg in self._list()] == ["1"]

    def test_unprocessed_keys_exhausted_raises_500(self, store):
        from fastapi import HTTPException

        s = store([["a"]])
        unprocessed = {TABLE: {"Keys": [{"PK": "LEAGUE#a", "SK": "METADATA"}]}}
        s.resource.batch_get_item.side_effect = None
        s.resource.batch_get_item.return_value = {
            "Responses": {TABLE: []},
            "UnprocessedKeys": unprocessed,
        }
        with patch("helpers.time.sleep"), pytest.raises(HTTPException) as exc:
            self._list()
        assert exc.value.status_code == 500

    def test_dynamodb_error_raises_500(self, store, mock_table):
        from fastapi import HTTPException

        store([["a"]])
        mock_table.query.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "x"}}, "Query"
        )
        with pytest.raises(HTTPException) as exc:
            self._list()
        assert exc.value.status_code == 500


class TestGetMyLeaguesEndpoint:
    def test_returns_leagues_with_no_store(self, client, store):
        store(
            [["a"]],
            lookups={"a": [_lookup("1", "SLEEPER", ["2024"])]},
            metadata={"a": _metadata("a", platform="SLEEPER", onboarded_at="x")},
        )
        response = client.get("/me/leagues")
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert [lg["league_id"] for lg in response.json()["data"]] == ["1"]

    def test_empty_list(self, client, store):
        store([[]])
        response = client.get("/me/leagues")
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_unauthenticated_returns_401(self, client):
        import main
        import routes

        main.app.dependency_overrides.pop(routes.get_authenticated_user, None)
        response = client.get("/me/leagues")
        assert response.status_code == 401

    def test_passes_espn_reauth_lookup(self, client, store):
        store(
            [["a"]],
            lookups={"a": [_lookup("1", "ESPN", ["2024"])]},
            metadata={
                "a": _metadata(
                    "a",
                    platform="ESPN",
                    owner_user_id="user_1",
                    auto_refresh_enabled=True,
                    onboarded_at="x",
                )
            },
        )
        with patch(
            "espn_credentials.get_reauth_status", return_value=(True, "t")
        ) as reauth:
            response = client.get("/me/leagues")
        assert response.json()["data"][0]["espn_reauth_required"] is True
        reauth.assert_called_once_with("user_1")
