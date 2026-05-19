"""Tests for FastAPI endpoint handlers in main.py."""

from unittest.mock import MagicMock

import botocore.exceptions
import pytest


class TestRootEndpoint:
    def test_health_check(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["detail"] == "Healthy!"


class TestGetLeagueEndpoint:
    def test_returns_league_data(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [
                {"seasons": {"2023", "2024"}, "canonical_league_id": "canonical-abc"}
            ]
        }
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["league_name"] == "Test League"
        assert "2023" in data["seasons"]
        assert "2024" in data["seasons"]

    def test_returns_404_for_unknown_league(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.get("/leagues/999?platform=SLEEPER")
        assert response.status_code == 404

    def test_invalid_league_id_format(self, client):
        response = client.get("/leagues/abc?platform=SLEEPER")
        assert response.status_code == 422

    def test_invalid_platform(self, client):
        response = client.get("/leagues/123?platform=YAHOO")
        assert response.status_code == 422

    def test_cache_control_header(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [{"seasons": {"2023"}, "canonical_league_id": "canonical-abc"}]
        }
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.headers["cache-control"] == "no-store"


class TestGetRefreshStatusEndpoint:
    def test_returns_onboard_status(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        response = client.get(
            "/leagues/123/refresh_status?platform=SLEEPER&refreshOperation=ONBOARD"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["refresh_operation"] == "ONBOARD"
        assert data["refresh_status"] == "COMPLETED"

    def test_returns_refresh_status(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        response = client.get(
            "/leagues/123/refresh_status?platform=SLEEPER&refreshOperation=REFRESH"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["refresh_operation"] == "REFRESH"
        assert data["refresh_status"] == "COMPLETED"

    def test_defaults_to_failed_when_status_missing(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}},
        ]
        response = client.get(
            "/leagues/123/refresh_status?platform=SLEEPER&refreshOperation=ONBOARD"
        )
        assert response.status_code == 200
        assert response.json()["data"]["refresh_status"] == "FAILED"

    def test_case_insensitive_refresh_operation(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        response = client.get(
            "/leagues/123/refresh_status?platform=sleeper&refreshOperation=onboard"
        )
        assert response.status_code == 200

    def test_returns_404_for_unknown_league(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.get(
            "/leagues/999/refresh_status?platform=SLEEPER&refreshOperation=ONBOARD"
        )
        assert response.status_code == 404


class TestOnboardLeagueEndpoint:
    def test_onboard_new_league(self, client, mock_table, mock_lambda_client):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER", "season": "2024"},
        )
        assert response.status_code == 201
        assert "onboarding" in response.json()["detail"].lower()
        mock_lambda_client.invoke.assert_called_once()

    def test_returns_200_when_already_onboarded(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 200
        assert "already onboarded" in response.json()["detail"].lower()

    def test_refresh_existing_league(
        self, client, mock_table, mock_lambda_client, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201
        assert "refresh" in response.json()["detail"].lower()

    def test_refresh_nonexistent_espn_league_returns_404(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "ESPN"},
        )
        assert response.status_code == 404

    def test_refresh_nonexistent_sleeper_league_triggers_lambda(
        self, client, mock_table, mock_lambda_client
    ):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201
        mock_lambda_client.invoke.assert_called_once()

    def test_returns_500_on_lambda_error(self, client, mock_table, mock_lambda_client):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ServiceError", "Message": "fail"}}, "Invoke"
        )
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 500

    def test_invalid_platform_returns_500(self, client, mock_table):
        # platform is a plain str in OnboardingPayload; Platform() conversion
        # happens in the handler body, so an invalid value raises ValueError -> 500
        mock_table.get_item.return_value = {}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "YAHOO"},
        )
        assert response.status_code == 500

    def test_payload_league_id_too_long_returns_422(self, client):
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER", "season": "x" * 101},
        )
        assert response.status_code == 422

    def test_non_404_lookup_error_is_reraised(self, client, mock_table):
        import botocore.exceptions

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "server error"}}, "GetItem"
        )
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 500


class TestDeleteLeagueEndpoint:
    def _setup_delete_mocks(self, mock_table, league_lookup_item, mock_s3_client):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.delete_item.return_value = {}
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.return_value = {"Items": []}
        mock_s3_client.list_objects_v2.return_value = {}
        return mock_writer

    def test_deletes_league_successfully(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        assert "deleted" in response.json()["detail"].lower()

    def test_deletes_s3_objects_when_present(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "raw-api-data/canonical-abc/file.json"}]
        }
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_s3_client.delete_objects.assert_called_once()

    def test_skips_s3_delete_when_no_objects(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_s3_client.delete_objects.assert_not_called()

    def test_returns_404_for_unknown_league(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.delete("/leagues/999?platform=SLEEPER")
        assert response.status_code == 404

    def test_deletes_gsi_lookup_items(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.delete_item.return_value = {}
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.side_effect = [
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
        ]
        mock_s3_client.list_objects_v2.return_value = {}
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_writer.delete_item.assert_any_call(
            Key={"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}
        )

    def test_paginated_gsi_query_during_delete(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.delete_item.return_value = {}
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.side_effect = [
            {
                "Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}],
                "LastEvaluatedKey": {
                    "PK": "LEAGUE#123#PLATFORM#SLEEPER",
                    "SK": "LEAGUE_LOOKUP",
                },
            },
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
        ]
        mock_s3_client.list_objects_v2.return_value = {}
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        assert mock_table.query.call_count == 8

    def test_decrements_league_count_on_successful_delete(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        from decimal import Decimal

        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": Decimal("-1")},
        )

    def test_client_error_during_delete_returns_500(
        self, client, mock_table, league_lookup_item
    ):
        import botocore.exceptions

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.delete_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "DeleteItem"
        )
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 500


class TestQueryLeagueEndpoint:
    def test_query_with_suffix_returns_item(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {
                "Item": {
                    "PK": "LEAGUE#canonical-abc",
                    "SK": "MATCHUPS#2024",
                    "data": [{"week": 1}],
                }
            },
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS%232024"
        )
        assert response.status_code == 200
        assert response.json()["data"] == [{"week": 1}]

    def test_query_without_suffix_returns_all_items(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {
            "Items": [
                {"data": [{"week": 1}]},
                {"data": [{"week": 2}]},
            ]
        }
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 200
        assert response.json()["data"] == [{"week": 1}, {"week": 2}]

    def test_query_handles_pagination(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.side_effect = [
            {
                "Items": [{"data": [{"week": 1}]}],
                "LastEvaluatedKey": {"PK": "x", "SK": "y"},
            },
            {"Items": [{"data": [{"week": 2}]}]},
        ]
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_query_converts_decimals(
        self, client, mock_table, league_lookup_item, sample_matchup_items
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": sample_matchup_items}
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 200
        row = response.json()["data"][0]
        assert isinstance(row["home_score"], float)
        assert row["home_score"] == 120.5

    def test_query_returns_404_when_no_data(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": []}
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 404

    def test_query_returns_404_when_item_missing(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {},
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS%232024"
        )
        assert response.status_code == 404

    def test_invalid_query_type_returns_400(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=INVALID_TYPE"
        )
        assert response.status_code == 400

    def test_cache_control_header_set(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": [{"data": [{"week": 1}]}]}
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.headers["cache-control"] == "private, max-age=300"

    def test_boto_error_returns_500(self, client, mock_table, league_lookup_item):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            botocore.exceptions.ClientError(
                {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
            ),
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS%232024"
        )
        assert response.status_code == 500

    @pytest.mark.parametrize(
        "query_type,sk_base",
        [
            ("TEAMS", "TEAMS"),
            ("MATCHUPS", "MATCHUPS"),
            ("SEASON_STANDINGS", "STANDINGS"),
            ("WEEKLY_STANDINGS", "WEEKLY_STANDINGS"),
            ("PLAYOFF_BRACKET", "PLAYOFF_BRACKET"),
            ("DRAFT", "DRAFT"),
        ],
    )
    def test_query_type_to_sk_base_mapping(
        self, client, mock_table, league_lookup_item, query_type, sk_base
    ):
        from boto3.dynamodb.conditions import ConditionExpressionBuilder

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": [{"data": []}]}
        client.get(f"/leagues/123/query?platform=SLEEPER&queryType={query_type}")
        call_kwargs = mock_table.query.call_args[1]
        condition = call_kwargs["KeyConditionExpression"]
        rendered = ConditionExpressionBuilder().build_expression(condition)
        sk_values = list(rendered.attribute_value_placeholders.values())
        assert any(str(v).startswith(sk_base) for v in sk_values)
