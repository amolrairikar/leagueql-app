ESPN_QUERIES = {
    "TEAMS": """
    SELECT
        m.displayName AS display_name,
        CAST(t.id AS STRING) AS team_id,
        t.name AS team_name,
        t.logo AS team_logo,
        t.season,
        t.owners[1] AS primary_owner_id,
        t.owners[2] AS secondary_owner_id
    FROM teams t
    INNER JOIN members m
    ON t.primaryOwner = m.id
    AND m.season = t.season
    """,
    "MATCHUPS": """
    SELECT
        m.*,
        t1.primary_owner_id AS team_a_primary_owner_id,
        t1.secondary_owner_id AS team_a_secondary_owner_id,
        t2.primary_owner_id AS team_b_primary_owner_id,
        t2.secondary_owner_id AS team_b_secondary_owner_id
    FROM matchups m
    INNER JOIN teams t1
    ON (m.team_a_id = t1.team_id AND m.season = t1.season)
    INNER JOIN teams t2
    ON (m.team_b_id = t2.team_id AND m.season = t2.season)
    """,
    "SEASON_STANDINGS": """
    SELECT 
        season,
        team_id,
        primary_owner_id,
        secondary_owner_id,
        COUNT(*) AS games_played,
        SUM(is_win) AS wins,
        SUM(is_loss) AS losses,
        SUM(is_tie) AS ties,
        SUM(points_for) AS total_points_for,
        SUM(points_against) AS total_points_against,
        ROUND(CAST(SUM(is_win) AS FLOAT) / COUNT(*), 3) AS win_pct
    FROM (
        SELECT 
            season,
            team_a_id AS team_id,
            team_a_primary_owner_id AS primary_owner_id,
            team_a_secondary_owner_id AS secondary_owner_id,
            team_a_score AS points_for,
            team_b_score AS points_against,
            CASE WHEN team_a_score > team_b_score THEN 1 ELSE 0 END AS is_win,
            CASE WHEN team_a_score < team_b_score THEN 1 ELSE 0 END AS is_loss,
            CASE WHEN team_a_score = team_b_score THEN 1 ELSE 0 END AS is_tie
        FROM matchups m1
        UNION ALL
        SELECT 
            season,
            team_b_id AS team_id,
            team_b_primary_owner_id AS primary_owner_id,
            team_b_secondary_owner_id AS secondary_owner_id,
            team_b_score AS points_for,
            team_a_score AS points_against,
            CASE WHEN team_b_score > team_a_score THEN 1 ELSE 0 END AS is_win,
            CASE WHEN team_b_score < team_a_score THEN 1 ELSE 0 END AS is_loss,
            CASE WHEN team_b_score = team_a_score THEN 1 ELSE 0 END AS is_tie
        FROM matchups m2
    ) combined_stats
    GROUP BY season, team_id, primary_owner_id, secondary_owner_id
    ORDER BY season DESC, wins DESC, total_points_for DESC
    """,
}

SLEEPER_QUERIES = {
    "TEAMS": """
    SELECT
        display_name,
        NULL AS team_id,
        "metadata.team_name" AS team_name,
        avatar AS team_logo,
        season,
        user_id AS primary_owner_id,
        NULL AS secondary_owner_id
    FROM teams
    """
}
