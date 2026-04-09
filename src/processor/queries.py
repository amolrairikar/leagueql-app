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
        CAST(m.team_a_id AS STRING) AS team_a_id,
        m.team_a_score AS team_a_score,
        CAST(m.team_b_id AS STRING) AS team_b_id,
        m.team_b_score AS team_b_score,
        m.playoff_tier_type AS playoff_tier_type,
        CAST(m.winner AS STRING) AS winner,
        CAST(m.loser AS STRING) AS loser,
        CAST(m.week AS STRING) AS week,
        CAST(m.season AS STRING) AS season,
        t1.primary_owner_id AS team_a_primary_owner_id,
        t1.secondary_owner_id AS team_a_secondary_owner_id,
        t2.primary_owner_id AS team_b_primary_owner_id,
        t2.secondary_owner_id AS team_b_secondary_owner_id
    FROM matchups m
    INNER JOIN teams_view t1
    ON (CAST(m.team_a_id AS STRING) = t1.team_id AND m.season = t1.season)
    INNER JOIN teams_view t2
    ON (CAST(m.team_b_id AS STRING) = t2.team_id AND m.season = t2.season)
    """,
}

SLEEPER_QUERIES = {
    "TEAMS": """
    SELECT
        u.display_name,
        CAST(r.roster_id AS STRING) AS team_id,
        "metadata.team_name" AS team_name,
        u.avatar AS team_logo,
        u.season,
        u.user_id AS primary_owner_id,
        NULL AS secondary_owner_id
    FROM users u
    INNER JOIN rosters r
    ON (u.user_id = r.owner_id AND u.league_id = r.league_id)
    """,
    "MATCHUPS": """
    SELECT
        CAST(m.team_a_roster_id AS STRING) AS team_a_id,
        m.team_a_points AS team_a_score,
        CAST(m.team_b_roster_id AS STRING) AS team_b_id,
        m.team_b_points AS team_b_score,
        NULL AS playoff_tier_type,
        CAST(m.winner AS STRING) AS winner,
        CAST(m.loser AS STRING) AS loser,
        CAST(m.team_a_week AS STRING) AS week,
        CAST(m.team_a_season AS STRING) AS season,
        t1.primary_owner_id AS team_a_primary_owner_id,
        t1.secondary_owner_id AS team_a_secondary_owner_id,
        t2.primary_owner_id AS team_b_primary_owner_id,
        t2.secondary_owner_id AS team_b_secondary_owner_id
    FROM matchups m
    INNER JOIN teams_view t1
    ON (CAST(m.team_a_roster_id AS STRING) = t1.team_id AND m.team_a_season = t1.season)
    INNER JOIN teams_view t2
    ON (CAST(m.team_b_roster_id AS STRING) = t2.team_id AND m.team_a_season = t2.season)
    """,
}
