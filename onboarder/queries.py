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
    """
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
