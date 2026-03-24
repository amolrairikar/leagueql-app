from queries import ESPN_QUERIES, SLEEPER_QUERIES


class TestESPNQueries:
    def test_teams_query_exists(self):
        assert "TEAMS" in ESPN_QUERIES
        assert isinstance(ESPN_QUERIES["TEAMS"], str)
        assert len(ESPN_QUERIES["TEAMS"]) > 0


class TestSleeperQueries:
    def test_teams_query_exists(self):
        assert "TEAMS" in SLEEPER_QUERIES
        assert isinstance(SLEEPER_QUERIES["TEAMS"], str)
        assert len(SLEEPER_QUERIES["TEAMS"]) > 0
