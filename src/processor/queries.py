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
            t.owners[2] AS secondary_owner_id,
            t.rankCalculatedFinal AS final_rank
        FROM teams t
        INNER JOIN members m
            ON t.primaryOwner = m.id
            AND m.season = t.season
        """,
        "SLEEPER": """
        WITH playoff_team_counts AS (
            SELECT season, COUNT(DISTINCT team_id) AS num_playoff_teams
            FROM (
                SELECT season, CAST(team_1 AS STRING) AS team_id FROM brackets WHERE bracket_type = 'WINNERS_BRACKET'
                UNION
                SELECT season, CAST(team_2 AS STRING) AS team_id FROM brackets WHERE bracket_type = 'WINNERS_BRACKET'
            )
            GROUP BY season
        ),
        sleeper_ranks AS (
            SELECT b.season, CAST(b.winner AS STRING) AS team_id,
                CASE
                    WHEN b.bracket_type = 'LOSERS_BRACKET' THEN b.position + pt.num_playoff_teams
                    ELSE b.position
                END AS final_rank
            FROM brackets b
            JOIN playoff_team_counts pt ON b.season = pt.season
            WHERE b.position IS NOT NULL AND b.winner IS NOT NULL
            UNION ALL
            SELECT b.season, CAST(b.loser AS STRING) AS team_id,
                CASE
                    WHEN b.bracket_type = 'LOSERS_BRACKET' THEN b.position + 1 + pt.num_playoff_teams
                    ELSE b.position + 1
                END AS final_rank
            FROM brackets b
            JOIN playoff_team_counts pt ON b.season = pt.season
            WHERE b.position IS NOT NULL AND b.loser IS NOT NULL
        )
        SELECT
            u.display_name,
            CAST(r.roster_id AS STRING) AS team_id,
            u.metadata.team_name AS team_name,
            'https://sleepercdn.com/avatars/thumbs/' || u.avatar AS team_logo,
            u.season,
            u.user_id AS primary_owner_id,
            NULL AS secondary_owner_id,
            sr.final_rank
        FROM users u
        INNER JOIN rosters r
            ON (u.user_id = r.owner_id AND u.league_id = r.league_id)
        LEFT JOIN sleeper_ranks sr
            ON (CAST(r.roster_id AS STRING) = sr.team_id AND u.season = sr.season)
        """,
    },
    "MATCHUPS": {
        "ESPN": """
        SELECT
            CAST(m.team_a_id AS STRING) AS team_a_id,
            t1.display_name AS team_a_display_name,
            t1.team_name AS team_a_team_name,
            t1.team_logo AS team_a_team_logo,
            CAST(m.team_a_score AS DOUBLE) AS team_a_score,
            m.team_a_starters AS team_a_starters,
            m.team_a_bench AS team_a_bench,
            t1.primary_owner_id AS team_a_primary_owner_id,
            t1.secondary_owner_id AS team_a_secondary_owner_id,
            CAST(m.team_b_id AS STRING) AS team_b_id,
            t2.display_name AS team_b_display_name,
            t2.team_name AS team_b_team_name,
            t2.team_logo AS team_b_team_logo,
            CAST(m.team_b_score AS DOUBLE) AS team_b_score,
            m.team_b_starters AS team_b_starters,
            m.team_b_bench AS team_b_bench,
            t2.primary_owner_id AS team_b_primary_owner_id,
            t2.secondary_owner_id AS team_b_secondary_owner_id,
            m.playoff_tier_type AS playoff_tier_type,
            CASE
                WHEN m.playoff_tier_type = 'WINNERS_BRACKET' THEN
                    CASE
                        WHEN CAST(m.season AS INTEGER) < 2021 THEN
                            CASE
                                WHEN CAST(m.week AS INTEGER) = 14 THEN 'Quarterfinals'
                                WHEN CAST(m.week AS INTEGER) = 15 THEN 'Semifinals'
                                WHEN CAST(m.week AS INTEGER) = 16 THEN 'Finals'
                                ELSE NULL
                            END
                        ELSE
                            CASE
                                WHEN CAST(m.week AS INTEGER) = 15 THEN 'Quarterfinals'
                                WHEN CAST(m.week AS INTEGER) = 16 THEN 'Semifinals'
                                WHEN CAST(m.week AS INTEGER) = 17 THEN 'Finals'
                                ELSE NULL
                            END
                    END
                WHEN m.playoff_tier_type = 'NONE' THEN NULL
                ELSE 'Losers Bracket'
            END AS playoff_round,
            CAST(m.winner AS STRING) AS winner,
            CAST(m.loser AS STRING) AS loser,
            CAST(m.week AS STRING) AS week,
            CAST(m.season AS STRING) AS season
        FROM matchups m
        INNER JOIN teams_output t1
            ON (CAST(m.team_a_id AS STRING) = t1.team_id AND m.season = t1.season)
        INNER JOIN teams_output t2
            ON (CAST(m.team_b_id AS STRING) = t2.team_id AND m.season = t2.season)
        """,
        "SLEEPER": """
        SELECT
            CAST(m.team_a_roster_id AS STRING) AS team_a_id,
            t1.display_name AS team_a_display_name,
            t1.team_name AS team_a_team_name,
            t1.team_logo AS team_a_team_logo,
            m.team_a_points AS team_a_score,
            m.team_a_starters AS team_a_starters,
            m.team_a_bench AS team_a_bench,
            t1.primary_owner_id AS team_a_primary_owner_id,
            t1.secondary_owner_id AS team_a_secondary_owner_id,
            CAST(m.team_b_roster_id AS STRING) AS team_b_id,
            t2.display_name AS team_b_display_name,
            t2.team_name AS team_b_team_name,
            t2.team_logo AS team_b_team_logo,
            m.team_b_points AS team_b_score,
            m.team_b_starters AS team_b_starters,
            m.team_b_bench AS team_b_bench,
            t2.primary_owner_id AS team_b_primary_owner_id,
            t2.secondary_owner_id AS team_b_secondary_owner_id,
            m.playoff_tier_type AS playoff_tier_type,
            CASE
                WHEN m.playoff_tier_type = 'WINNERS_BRACKET' THEN
                    CASE
                        WHEN CAST(m.team_a_season AS INTEGER) < 2021 THEN
                            CASE
                                WHEN CAST(m.team_a_week AS INTEGER) = 14 THEN 'Quarterfinals'
                                WHEN CAST(m.team_a_week AS INTEGER) = 15 THEN 'Semifinals'
                                WHEN CAST(m.team_a_week AS INTEGER) = 16 THEN 'Finals'
                                ELSE NULL
                            END
                        ELSE
                            CASE
                                WHEN CAST(m.team_a_week AS INTEGER) = 15 THEN 'Quarterfinals'
                                WHEN CAST(m.team_a_week AS INTEGER) = 16 THEN 'Semifinals'
                                WHEN CAST(m.team_a_week AS INTEGER) = 17 THEN 'Finals'
                                ELSE NULL
                            END
                    END
                WHEN m.playoff_tier_type = 'NONE' THEN NULL
                ELSE 'Losers Bracket'
            END AS playoff_round,
            CAST(m.winner AS STRING) AS winner,
            CAST(m.loser AS STRING) AS loser,
            CAST(m.team_a_week AS STRING) AS week,
            CAST(m.team_a_season AS STRING) AS season
        FROM matchups m
        INNER JOIN teams_output t1
            ON (CAST(m.team_a_roster_id AS STRING) = t1.team_id AND m.team_a_season = t1.season)
        INNER JOIN teams_output t2
            ON (CAST(m.team_b_roster_id AS STRING) = t2.team_id AND m.team_a_season = t2.season)
        """,
    },
    "PLAYOFF_BRACKET": {
        "ESPN": """
        SELECT
            b.match_id,
            b.round,
            CAST(b.team_1 AS STRING) AS team_1_id,
            t1.display_name AS team_1_display_name,
            t1.team_name AS team_1_team_name,
            t1.team_logo AS team_1_team_logo,
            CAST(b.team_2 AS STRING) AS team_2_id,
            t2.display_name AS team_2_display_name,
            t2.team_name AS team_2_team_name,
            t2.team_logo AS team_2_team_logo,
            CAST(b.winner AS STRING) AS winner,
            CAST(b.loser AS STRING) AS loser,
            b.position,
            b.team_1_from,
            b.team_2_from,
            b.season
        FROM brackets b
        LEFT JOIN teams_output t1
            ON (CAST(b.team_1 AS STRING) = t1.team_id AND b.season = t1.season)
        LEFT JOIN teams_output t2
            ON (CAST(b.team_2 AS STRING) = t2.team_id AND b.season = t2.season)
        """,
        "SLEEPER": """
        SELECT
            b.match_id,
            b.round,
            CAST(b.team_1 AS STRING) AS team_1_id,
            t1.display_name AS team_1_display_name,
            t1.team_name AS team_1_team_name,
            t1.team_logo AS team_1_team_logo,
            CAST(b.team_2 AS STRING) AS team_2_id,
            t2.display_name AS team_2_display_name,
            t2.team_name AS team_2_team_name,
            t2.team_logo AS team_2_team_logo,
            CAST(b.winner AS STRING) AS winner,
            CAST(b.loser AS STRING) AS loser,
            b.position,
            b.team_1_from,
            b.team_2_from,
            b.season
        FROM brackets b
        LEFT JOIN teams_output t1
            ON (CAST(b.team_1 AS STRING) = t1.team_id AND b.season = t1.season)
        LEFT JOIN teams_output t2
            ON (CAST(b.team_2 AS STRING) = t2.team_id AND b.season = t2.season)
        """,
    },
    "WEEKLY_STANDINGS": """
    WITH weekly_stats AS (
        SELECT
            season,
            week,
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
            RANK() OVER (PARTITION BY season, week ORDER BY points_for DESC) AS weekly_rank,
            COUNT(*) OVER (PARTITION BY season, week) AS total_teams_that_week
        FROM weekly_stats
    ),
    processed_performance AS (
        SELECT
            season,
            week,
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
    ),
    cumulative_stats AS (
        SELECT
            season,
            week,
            team_id,
            owner_id,
            ROW_NUMBER() OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS games_played,
            SUM(win) OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS wins,
            SUM(loss) OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS losses,
            SUM(tie) OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS ties,
            SUM(points_for) OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS total_pf,
            SUM(points_against) OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS total_pa,
            SUM(vs_league_wins) OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS total_vs_league_wins,
            SUM(vs_league_losses) OVER (PARTITION BY season, team_id ORDER BY CAST(week AS INTEGER)) AS total_vs_league_losses
        FROM processed_performance
    )
    SELECT
        c.season,
        c.week AS snapshot_week,
        c.team_id,
        c.owner_id,
        t.display_name AS owner_username,
        c.games_played,
        c.wins,
        c.losses,
        c.ties,
        CONCAT(
            CAST(c.wins AS STRING), '-',
            CAST(c.losses AS STRING), '-',
            CAST(c.ties AS STRING)
        ) AS record
    FROM cumulative_stats c
    INNER JOIN teams_output t
        ON (c.team_id = t.team_id AND c.season = t.season)
    ORDER BY season DESC, CAST(snapshot_week AS INTEGER) DESC, wins DESC;
    """,
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
    ),
    champion AS (
        SELECT
            season,
            winner AS champion_team_id
        FROM matchups_output
        WHERE playoff_tier_type = 'WINNERS_BRACKET'
            AND (
                (CAST(season AS INTEGER) < 2021 AND CAST(week AS INTEGER) = 16)
                OR (CAST(season AS INTEGER) >= 2021 AND CAST(week AS INTEGER) = 17)
            )
    )
    SELECT
        p.season,
        p.team_id,
        p.owner_id,
        t.team_name,
        t.team_logo,
        t.display_name AS owner_username,
        t.final_rank,
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
        ROUND(AVG(p.points_against), 2) AS avg_pa,
        CASE WHEN c.champion_team_id IS NOT NULL THEN 'Yes' ELSE 'No' END AS champion
    FROM processed_performance p
    INNER JOIN teams_output t
        ON (p.team_id = t.team_id AND p.season = t.season)
    LEFT JOIN champion c
        ON (p.team_id = c.champion_team_id AND p.season = c.season)
    GROUP BY p.season, p.team_id, p.owner_id, t.team_name, t.team_logo, t.display_name, t.final_rank, c.champion_team_id
    ORDER BY season DESC, wins DESC, total_pf DESC;
    """,
    "DRAFT": {
        "ESPN": """
        WITH actual_position_ranks AS (
            SELECT
                player_id,
                season,
                player_name,
                position,
                total_points,
                RANK() OVER (
                    PARTITION BY season, position
                    ORDER BY total_points DESC
                ) AS actual_position_rank
            FROM player_scoring_totals
        ),
        draft_with_scoring AS (
            SELECT
                dp.*,
                apr.player_name,
                apr.position,
                apr.total_points,
                apr.actual_position_rank,
                RANK() OVER (
                    PARTITION BY dp.season, apr.position
                    ORDER BY dp.overallPickNumber ASC
                ) AS drafted_position_rank
            FROM draft_picks dp
            LEFT JOIN actual_position_ranks apr
                ON (dp.playerId = apr.player_id AND dp.season = apr.season)
        )
        SELECT
            CAST(ds.teamId AS STRING) AS team_id,
            t.display_name AS owner_username,
            t.team_name,
            t.team_logo,
            ds.id AS pick_id,
            ds.roundId AS round,
            ds.roundPickNumber AS round_pick_number,
            ds.overallPickNumber AS overall_pick_number,
            CAST(ds.playerId AS STRING) AS player_id,
            ds.player_name,
            ds.position,
            ds.total_points,
            ds.keeper,
            ds.reservedForKeeper AS reserved_for_keeper,
            ds.autoDraftTypeId AS auto_draft_type_id,
            ds.bidAmount AS bid_amount,
            ds.lineupSlotId AS lineup_slot_id,
            ds.memberId AS member_id,
            ds.nominatingTeamId AS nominating_team_id,
            ds.tradeLocked AS trade_locked,
            ds.season,
            ds.drafted_position_rank,
            ds.actual_position_rank,
            ds.drafted_position_rank - ds.actual_position_rank AS draft_rank_delta
        FROM draft_with_scoring ds
        INNER JOIN teams_output t
            ON (CAST(ds.teamId AS STRING) = t.team_id AND ds.season = t.season)
        ORDER BY ds.season, ds.overallPickNumber
        """,
        "SLEEPER": "",
    },
}
