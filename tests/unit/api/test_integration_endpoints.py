"""Tests for GET/POST /integrations (backend/integrations)."""

from unittest.mock import patch

import pytest

VALID_SUBMISSION = {
    "name": "Trade Grader",
    "category": "bot",
    "link": "https://github.com/example/trade-grader",
    "views": ["transactions"],
    "description": "Grades every trade.",
    "setup_steps": ["Fork the repo."],
}


@pytest.fixture
def github_error():
    # Imported lazily: a module-level import would load ``common.secrets`` during
    # collection, before ``conftest`` patches boto3, and build a real SSM client.
    from integrations import GitHubError

    return GitHubError


@pytest.fixture
def unauthenticated():
    import main
    import routes

    main.app.dependency_overrides.pop(routes.get_authenticated_user, None)


class TestListIntegrations:
    def test_returns_items(self, client):
        items = [{"issue_number": 7, "name": "Tool", "featured": True}]
        with patch("integrations.list_approved", return_value=items):
            response = client.get("/integrations")
        assert response.status_code == 200
        assert response.json() == {"detail": "Integrations", "data": {"items": items}}
        assert response.headers["cache-control"] == "no-store"

    def test_github_failure_returns_502(self, client, github_error):
        with patch("integrations.list_approved", side_effect=github_error("down")):
            response = client.get("/integrations")
        assert response.status_code == 502
        assert "Couldn't load integrations" in response.json()["detail"]

    @pytest.mark.usefixtures("unauthenticated")
    def test_requires_authentication(self, client):
        with patch("integrations.list_approved") as list_approved:
            response = client.get("/integrations")
        assert response.status_code == 401
        list_approved.assert_not_called()


class TestSubmitIntegration:
    def test_creates_issue_and_records_submission(self, client, mock_table):
        mock_table.get_item.return_value = {}
        with (
            patch("integrations.create_issue", return_value=42) as create_issue,
            patch("routes.time.time", return_value=1_800_000_000),
        ):
            response = client.post("/integrations", json=VALID_SUBMISSION)
        assert response.status_code == 201
        assert response.json() == {
            "detail": "Integration submitted for review",
            "data": {"issue_number": 42},
        }
        submission = create_issue.call_args.args[0]
        assert submission.name == "Trade Grader"
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "USER#user_1"
        assert item["submitted_at"] == [1_800_000_000]

    def test_validation_failure_returns_422_and_does_not_count(
        self, client, mock_table
    ):
        with patch("integrations.create_issue") as create_issue:
            response = client.post(
                "/integrations", json={**VALID_SUBMISSION, "link": "http://x.com"}
            )
        assert response.status_code == 422
        create_issue.assert_not_called()
        mock_table.put_item.assert_not_called()

    def test_limit_reached_returns_429(self, client, mock_table):
        now = 1_800_000_000
        mock_table.get_item.return_value = {
            "Item": {"submitted_at": [now - 30, now - 20, now - 10]}
        }
        with (
            patch("integrations.create_issue") as create_issue,
            patch("routes.time.time", return_value=now),
        ):
            response = client.post("/integrations", json=VALID_SUBMISSION)
        assert response.status_code == 429
        assert "limit of 3" in response.json()["detail"]
        create_issue.assert_not_called()

    def test_github_failure_returns_502_alerts_and_does_not_count(
        self, client, mock_table, github_error
    ):
        mock_table.get_item.return_value = {}
        with (
            patch(
                "integrations.create_issue", side_effect=github_error("500 boom")
            ) as create_issue,
            patch("routes.publish_failure") as alert,
        ):
            response = client.post("/integrations", json=VALID_SUBMISSION)
        assert response.status_code == 502
        assert response.json()["detail"] == (
            "Couldn't submit right now. Try again in a few minutes."
        )
        assert create_issue.call_count == 1
        alert.assert_called_once()
        mock_table.put_item.assert_not_called()

    def test_clerk_id_never_sent_to_github(self, client, mock_table):
        from integrations import build_issue_body

        mock_table.get_item.return_value = {}
        with patch("integrations.create_issue", return_value=1) as create_issue:
            client.post("/integrations", json=VALID_SUBMISSION)
        submission = create_issue.call_args.args[0]
        assert "user_1" not in build_issue_body(submission)
        assert "user_1" not in submission.model_dump_json()

    @pytest.mark.usefixtures("unauthenticated")
    def test_requires_authentication(self, client):
        with patch("integrations.create_issue") as create_issue:
            response = client.post("/integrations", json=VALID_SUBMISSION)
        assert response.status_code == 401
        create_issue.assert_not_called()
