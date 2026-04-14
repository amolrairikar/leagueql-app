QUERIES = {
    "TEAMS": {
        "ESPN": """
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
        "SLEEPER": """
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
    },
    "MATCHUPS": {
        "ESPN": """
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
        INNER JOIN teams_output t1
            ON (CAST(m.team_a_id AS STRING) = t1.team_id AND m.season = t1.season)
        INNER JOIN teams_output t2
            ON (CAST(m.team_b_id AS STRING) = t2.team_id AND m.season = t2.season)
        """,
        "SLEEPER": """
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
        INNER JOIN teams_output t1
            ON (CAST(m.team_a_roster_id AS STRING) = t1.team_id AND m.team_a_season = t1.season)
        INNER JOIN teams_output t2
            ON (CAST(m.team_b_roster_id AS STRING) = t2.team_id AND m.team_a_season = t2.season)
        """,
    },
    "STANDINGS": """
    WITH weekly_stats AS (
        SELECT 
            season,
            week,
            playoff_tier_type,
            team_a_id AS team_id,
            team_a_primary_owner_id AS owner_id,
            team_a_score AS points_for,
            CAST(team_b_score AS DOUBLE) AS points_against
        FROM matchups_output
        WHERE playoff_tier_type = 'NONE'
        UNION ALL
        SELECT 
            season,
            week,
            playoff_tier_type,
            team_b_id AS team_id,
            team_b_primary_owner_id AS owner_id,
            CAST(team_b_score AS DOUBLE) AS points_for,
            team_a_score AS points_against
        FROM matchups_output
        WHERE playoff_tier_type = 'NONE'
    ),
    league_rankings AS (
        SELECT 
            *,
            RANK() OVER (PARTITION BY season, week ORDER BY points_for DESC) as weekly_rank,
            COUNT(*) OVER (PARTITION BY season, week) as total_teams_that_week
        FROM weekly_stats
    ),
    processed_performance AS (
        SELECT 
            season,
            team_id,
            owner_id,
            points_for,
            points_against,
            CASE WHEN points_for > points_against THEN 1 ELSE 0 END AS win,
            CASE WHEN points_for < points_against THEN 1 ELSE 0 END AS loss,
            CASE WHEN points_for = points_against THEN 1 ELSE 0 END AS tie,
            (total_teams_that_week - weekly_rank) AS vs_league_wins,
            (weekly_rank - 1) AS vs_league_losses
        FROM league_rankings
    )
    SELECT 
        p.season,
        p.team_id,
        p.owner_id,
        t.team_name,
        t.team_logo,
        t.display_name AS owner_username,
        COUNT(*) AS games_played,
        SUM(p.win) AS wins,
        SUM(p.loss) AS losses,
        SUM(p.tie) AS ties,
        CONCAT(
            CAST(SUM(p.win) AS STRING), '-', 
            CAST(SUM(p.loss) AS STRING), '-', 
            CAST(SUM(p.tie) AS STRING)
        ) AS record,
        ROUND(SUM(p.win) / COUNT(*)::DOUBLE, 3) AS win_pct,
        SUM(p.vs_league_wins) AS total_vs_league_wins,
        SUM(p.vs_league_losses) AS total_vs_league_losses,
        ROUND(SUM(p.vs_league_wins) / (SUM(p.vs_league_wins) + SUM(p.vs_league_losses))::DOUBLE, 3) AS win_pct_vs_league,
        SUM(p.points_for) AS total_pf,
        SUM(p.points_against) AS total_pa,
        ROUND(AVG(p.points_for), 2) AS avg_pf,
        ROUND(AVG(p.points_against), 2) AS avg_pa
    FROM processed_performance p
    INNER JOIN teams_output t
        ON (p.team_id = t.team_id AND p.season = t.season)
    GROUP BY p.season, p.team_id, p.owner_id
    ORDER BY season DESC, wins DESC, total_pf DESC;
    """,
}
