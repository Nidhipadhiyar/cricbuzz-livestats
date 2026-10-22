
import streamlit as st
import pandas as pd
import plotly.express as px

from database.db_connection import get_connection


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SQL Analytics | Cricbuzz LiveStats",
    page_icon="📊",
    layout="wide",
)

st.title("📊 SQL Analytics")
st.caption(
    "Explore cricket data using 25 SQL questions covering "
    "beginner, intermediate, and advanced analytics."
)

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background: #10251f;
        border: 1px solid #285344;
        padding: 14px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ORIGINAL 25 PROJECT QUESTIONS
# SQL uses the existing SQLite database schema.
# ============================================================

ANALYSES = {

    # --------------------------------------------------------
    # BEGINNER: QUESTIONS 1–8
    # --------------------------------------------------------

    "Q1. Indian players": {
        "level": "Beginner",
        "question": (
            "Find all players who represent India. Display their "
            "full name, playing role, batting style, and bowling style."
        ),
        "sql": """
            SELECT DISTINCT
                p.full_name,
                p.playing_role,
                p.batting_style,
                p.bowling_style
            FROM players p
            LEFT JOIN teams player_team
                ON player_team.team_id = p.team_id
            LEFT JOIN player_match_stats ps
                ON ps.player_id = p.player_id
            LEFT JOIN teams stats_team
                ON stats_team.team_id = ps.team_id
            WHERE LOWER(COALESCE(player_team.country, '')) = 'india'
               OR LOWER(COALESCE(player_team.team_name, '')) = 'india'
               OR LOWER(COALESCE(stats_team.country, '')) = 'india'
               OR LOWER(COALESCE(stats_team.team_name, '')) = 'india'
            ORDER BY p.full_name;
        """,
        "chart": None,
    },

    "Q2. Matches in the last 30 days": {
        "level": "Beginner",
        "question": (
            "Show all cricket matches played in the last 30 days. "
            "Include match description, both team names, venue name "
            "with city, and match date. Sort newest first."
        ),
        "sql": """
            SELECT
                m.match_description,
                t1.team_name AS team1,
                t2.team_name AS team2,
                v.venue_name,
                v.city,
                m.match_date
            FROM matches m
            LEFT JOIN teams t1 ON t1.team_id = m.team1_id
            LEFT JOIN teams t2 ON t2.team_id = m.team2_id
            LEFT JOIN venues v ON v.venue_id = m.venue_id
            WHERE date(m.match_date) >= date('now', '-30 days')
              AND date(m.match_date) <= date('now')
            ORDER BY date(m.match_date) DESC;
        """,
        "chart": None,
    },

    "Q3. Top 10 ODI run scorers": {
        "level": "Beginner",
        "question": (
            "Top 10 highest run scorers in ODI. Display player name, "
            "total runs, batting average, and centuries. Highest first."
        ),
        "sql": """
            SELECT
                p.full_name AS player,
                SUM(ps.runs_scored) AS total_runs,
                ROUND(
                    1.0 * SUM(ps.runs_scored) /
                    NULLIF(
                        SUM(CASE WHEN ps.is_out = 1 THEN 1 ELSE 0 END),
                        0
                    ),
                    2
                ) AS batting_average,
                SUM(CASE WHEN ps.runs_scored >= 100 THEN 1 ELSE 0 END)
                    AS centuries
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            WHERE UPPER(m.match_type) = 'ODI'
            GROUP BY p.player_id, p.full_name
            ORDER BY total_runs DESC
            LIMIT 10;
        """,
        "chart": "bar",
    },

    "Q4. Large-capacity venues": {
        "level": "Beginner",
        "question": (
            "Find venues with capacity greater than 50,000. "
            "Display venue name, city, country, and capacity. "
            "Largest first."
        ),
        "sql": """
            SELECT venue_name, city, country, capacity
            FROM venues
            WHERE capacity > 50000
            ORDER BY capacity DESC;
        """,
        "chart": "bar",
    },

    "Q5. Matches won by each team": {
        "level": "Beginner",
        "question": (
            "Count matches won by each team. Show team name and "
            "total wins, ordered by most wins first."
        ),
        "sql": """
            SELECT
                t.team_name,
                COUNT(m.match_id) AS total_wins
            FROM teams t
            LEFT JOIN matches m ON m.winner_team_id = t.team_id
            GROUP BY t.team_id, t.team_name
            ORDER BY total_wins DESC;
        """,
        "chart": "bar",
    },

    "Q6. Players by role": {
        "level": "Beginner",
        "question": (
            "Count players by role: Batsman, Bowler, All-rounder, "
            "and Wicket-keeper."
        ),
        "sql": """
            SELECT
                COALESCE(playing_role, 'Unknown') AS playing_role,
                COUNT(*) AS total_players
            FROM players
            GROUP BY playing_role
            ORDER BY total_players DESC;
        """,
        "chart": "bar",
    },

    "Q7. Highest individual score by format": {
        "level": "Beginner",
        "question": (
            "Find the highest individual batting score in each "
            "format: Test, ODI, and T20/T20I."
        ),
        "sql": """
            WITH PlayerScores AS (
                SELECT
                    m.match_type AS format,
                    p.full_name AS player,
                    ps.runs_scored AS highest_score,
                    m.match_description,
                    m.match_date,
                    ROW_NUMBER() OVER (
                        PARTITION BY m.match_type
                        ORDER BY ps.runs_scored DESC, m.match_date DESC
                    ) AS ranking
                FROM player_match_stats ps
                JOIN players p
                    ON p.player_id = ps.player_id
                JOIN matches m
                    ON m.match_id = ps.match_id
                WHERE UPPER(m.match_type) IN ('TEST', 'ODI', 'T20', 'T20I')
            )
            SELECT
                format,
                player,
                highest_score,
                match_description,
                match_date
            FROM PlayerScores
            WHERE ranking = 1
            ORDER BY format;
        """,
        "chart": None,
    },

    "Q8. Series started in 2024": {
        "level": "Beginner",
        "question": (
            "List series started in 2024 with series name, host "
            "country, match type, start date, and planned matches."
        ),
        "sql": """
            SELECT
                series_name,
                host_country,
                match_type,
                start_date,
                planned_matches
            FROM series
            WHERE strftime('%Y', start_date) = '2024'
            ORDER BY start_date;
        """,
        "chart": None,
    },

    # --------------------------------------------------------
    # INTERMEDIATE: QUESTIONS 9–16
    # --------------------------------------------------------

    "Q9. All-rounders with 1000 runs and 50 wickets": {
        "level": "Intermediate",
        "question": (
            "Find all-rounders with more than 1,000 career runs and "
            "more than 50 wickets. Display name, runs, wickets, "
            "and format."
        ),
        "sql": """
            SELECT
                p.full_name AS player,
                m.match_type AS format,
                SUM(ps.runs_scored) AS total_runs,
                SUM(ps.wickets_taken) AS total_wickets
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            WHERE LOWER(COALESCE(p.playing_role, '')) LIKE '%all%'
            GROUP BY p.player_id, p.full_name, m.match_type
            HAVING SUM(ps.runs_scored) > 1000
               AND SUM(ps.wickets_taken) > 50
            ORDER BY total_runs DESC;
        """,
        "chart": "bar",
    },

    "Q10. Last 20 completed matches": {
        "level": "Intermediate",
        "question": (
            "Show the last 20 completed matches: description, teams, "
            "winning team, victory margin, victory type, and venue. "
            "Most recent first."
        ),
        "sql": """
            SELECT
                m.match_description,
                t1.team_name AS team1,
                t2.team_name AS team2,
                winner.team_name AS winning_team,
                m.win_margin,
                m.win_type,
                v.venue_name,
                m.match_date
            FROM matches m
            LEFT JOIN teams t1 ON t1.team_id = m.team1_id
            LEFT JOIN teams t2 ON t2.team_id = m.team2_id
            LEFT JOIN teams winner
                ON winner.team_id = m.winner_team_id
            LEFT JOIN venues v ON v.venue_id = m.venue_id
            WHERE m.winner_team_id IS NOT NULL
            ORDER BY date(m.match_date) DESC
            LIMIT 20;
        """,
        "chart": None,
    },

    "Q11. Players across multiple formats": {
        "level": "Intermediate",
        "question": (
            "Find players with at least two different formats. "
            "Show Test, ODI, and T20I runs and overall batting average."
        ),
        "sql": """
            SELECT
                p.full_name AS player,
                SUM(CASE WHEN UPPER(m.match_type) = 'TEST'
                    THEN ps.runs_scored ELSE 0 END) AS test_runs,
                SUM(CASE WHEN UPPER(m.match_type) = 'ODI'
                    THEN ps.runs_scored ELSE 0 END) AS odi_runs,
                SUM(CASE WHEN UPPER(m.match_type) IN ('T20I', 'T20')
                    THEN ps.runs_scored ELSE 0 END) AS t20_runs,
                ROUND(
                    1.0 * SUM(ps.runs_scored) /
                    NULLIF(
                        SUM(CASE WHEN ps.is_out = 1 THEN 1 ELSE 0 END),
                        0
                    ),
                    2
                ) AS overall_batting_average,
                COUNT(DISTINCT m.match_type) AS formats_played
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            GROUP BY p.player_id, p.full_name
            HAVING COUNT(DISTINCT m.match_type) >= 2
            ORDER BY formats_played DESC, overall_batting_average DESC;
        """,
        "chart": None,
    },

    "Q12. Home versus away team performance": {
        "level": "Intermediate",
        "question": (
            "Compare international teams' home and away performance "
            "using whether the venue country matches the team's country."
        ),
        "sql": """
            SELECT
                t.team_name,
                CASE
                    WHEN LOWER(COALESCE(v.country, '')) =
                         LOWER(COALESCE(t.country, ''))
                    THEN 'Home'
                    ELSE 'Away'
                END AS venue_condition,
                COUNT(*) AS matches_won
            FROM matches m
            JOIN teams t ON t.team_id = m.winner_team_id
            JOIN venues v ON v.venue_id = m.venue_id
            WHERE t.country IS NOT NULL
              AND v.country IS NOT NULL
            GROUP BY t.team_id, t.team_name, venue_condition
            ORDER BY t.team_name, venue_condition;
        """,
        "chart": "bar",
    },

    "Q13. Partnerships of 100 or more": {
        "level": "Intermediate",
        "question": (
            "Find recorded batting partnerships where two batters "
            "combined for at least 100 runs in the same innings."
        ),
        "sql": """
            SELECT
                p1.batter1_name AS batter1,
                p1.batter2_name AS batter2,
                p1.runs AS partnership_runs,
                p1.innings_number,
                m.match_description,
                m.match_date
            FROM partnerships p1
            JOIN matches m ON m.match_id = p1.match_id
            WHERE p1.runs >= 100
            ORDER BY p1.runs DESC;
        """,
        "chart": "bar",
    },

    "Q14. Bowlers at the same venue": {
        "level": "Intermediate",
        "question": (
            "Find bowlers with at least three matches at the same venue. "
            "Show average economy, wickets, and match count. Include "
            "only matches in which they bowled at least four overs."
        ),
        "sql": """
            SELECT
                p.full_name AS bowler,
                v.venue_name,
                COUNT(DISTINCT m.match_id) AS match_count,
                SUM(ps.wickets_taken) AS total_wickets,
                ROUND(
                    1.0 * SUM(ps.runs_conceded) /
                    NULLIF(SUM(ps.overs_bowled), 0),
                    2
                ) AS average_economy
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            JOIN venues v ON v.venue_id = m.venue_id
            WHERE COALESCE(ps.overs_bowled, 0) >= 4
            GROUP BY p.player_id, p.full_name, v.venue_id, v.venue_name
            HAVING COUNT(DISTINCT m.match_id) >= 3
            ORDER BY average_economy ASC;
        """,
        "chart": "bar",
    },

    "Q15. Close-match player performance": {
        "level": "Intermediate",
        "question": (
            "Analyze player performances in close matches: under "
            "50 runs or under 5 wickets as the victory margin."
        ),
        "sql": """
            SELECT
                p.full_name AS player,
                COUNT(DISTINCT m.match_id) AS close_matches_played,
                ROUND(AVG(ps.runs_scored), 2) AS average_runs,
                SUM(
                    CASE
                        WHEN m.winner_team_id = ps.team_id
                        THEN 1 ELSE 0
                    END
                ) AS wins_for_player_team
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            WHERE
                (LOWER(COALESCE(m.win_type, '')) LIKE '%run%'
                 AND CAST(m.win_margin AS REAL) < 50)
                OR
                (LOWER(COALESCE(m.win_type, '')) LIKE '%wicket%'
                 AND CAST(m.win_margin AS REAL) < 5)
            GROUP BY p.player_id, p.full_name
            ORDER BY close_matches_played DESC, average_runs DESC;
        """,
        "chart": None,
    },

    "Q16. Yearly player performance since 2020": {
        "level": "Intermediate",
        "question": (
            "Since 2020, calculate yearly average runs per player "
            "per match and average strike rate. Include players with "
            "at least five matches in that year."
        ),
        "sql": """
            SELECT
                CAST(strftime('%Y', m.match_date) AS INTEGER) AS year,
                p.full_name AS player,
                COUNT(DISTINCT m.match_id) AS matches,
                ROUND(AVG(ps.runs_scored), 2) AS average_runs,
                ROUND(
                    100.0 * SUM(ps.runs_scored) /
                    NULLIF(SUM(ps.balls_faced), 0),
                    2
                ) AS strike_rate
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            WHERE date(m.match_date) >= date('2020-01-01')
            GROUP BY year, p.player_id, p.full_name
            HAVING COUNT(DISTINCT m.match_id) >= 5
            ORDER BY year, average_runs DESC;
        """,
        "chart": None,
    },

    # --------------------------------------------------------
    # ADVANCED: QUESTIONS 17–25
    # --------------------------------------------------------

    "Q17. Toss advantage": {
        "level": "Advanced",
        "question": (
            "Calculate the percentage of matches won by the toss-winning "
            "team, grouped by toss decision: bat or bowl."
        ),
        "sql": """
            SELECT
                LOWER(m.toss_decision) AS toss_decision,
                COUNT(*) AS matches_with_result,
                SUM(
                    CASE
                        WHEN m.winner_team_id = m.toss_winner_team_id
                        THEN 1 ELSE 0
                    END
                ) AS toss_winner_match_wins,
                ROUND(
                    100.0 * SUM(
                        CASE
                            WHEN m.winner_team_id = m.toss_winner_team_id
                            THEN 1 ELSE 0
                        END
                    ) / NULLIF(COUNT(*), 0),
                    2
                ) AS toss_winner_win_percentage
            FROM matches m
            WHERE m.winner_team_id IS NOT NULL
              AND m.toss_winner_team_id IS NOT NULL
              AND LOWER(m.toss_decision) IN ('bat', 'bowl')
            GROUP BY LOWER(m.toss_decision)
            ORDER BY toss_decision;
        """,
        "chart": "bar",
    },

    "Q18. Most economical limited-overs bowlers": {
        "level": "Advanced",
        "question": (
            "Rank economical ODI and T20 bowlers by overall economy "
            "and wickets. Include players with at least 10 matches "
            "and an average of at least two overs per match."
        ),
        "sql": """
            SELECT
                p.full_name AS bowler,
                m.match_type AS format,
                COUNT(DISTINCT m.match_id) AS matches,
                SUM(ps.wickets_taken) AS wickets,
                ROUND(
                    1.0 * SUM(ps.runs_conceded) /
                    NULLIF(SUM(ps.overs_bowled), 0),
                    2
                ) AS economy_rate,
                ROUND(
                    1.0 * SUM(ps.overs_bowled) /
                    NULLIF(COUNT(DISTINCT m.match_id), 0),
                    2
                ) AS average_overs_per_match
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            WHERE UPPER(m.match_type) IN ('ODI', 'T20', 'T20I')
            GROUP BY p.player_id, p.full_name, m.match_type
            HAVING COUNT(DISTINCT m.match_id) >= 10
               AND average_overs_per_match >= 2
            ORDER BY economy_rate ASC, wickets DESC;
        """,
        "chart": "bar",
    },

    "Q19. Batting consistency since 2022": {
        "level": "Advanced",
        "question": (
            "Measure batting consistency since 2022 for innings "
            "with at least 10 balls faced. Lower standard deviation "
            "means more consistent scoring."
        ),
        "sql": """
            WITH PlayerConsistency AS (
            SELECT
                p.player_id,
                p.full_name AS player,
                COUNT(*) AS innings,
                AVG(ps.runs_scored) AS average_runs,
                AVG(ps.runs_scored * ps.runs_scored)
                    - AVG(ps.runs_scored) * AVG(ps.runs_scored)
                    AS run_variance
            FROM player_match_stats ps
            JOIN players p
                ON p.player_id = ps.player_id
            JOIN matches m
                ON m.match_id = ps.match_id
            WHERE date(m.match_date) >= date('2022-01-01')
            AND ps.balls_faced >= 10
            GROUP BY p.player_id, p.full_name
        )
        SELECT
            player,
            innings,
            ROUND(average_runs, 2) AS average_runs,
            ROUND(
                SQRT(MAX(0, run_variance)),
                2
            ) AS run_standard_deviation
        FROM PlayerConsistency
        ORDER BY run_standard_deviation ASC;
        """,
        "chart": None,
    },

    "Q20. Player matches by format": {
        "level": "Advanced",
        "question": (
            "Show player match counts in Test, ODI, and T20 and "
            "batting average per format. Include players with at "
            "least 20 total matches."
        ),
        "sql": """
            SELECT
                p.full_name AS player,
                COUNT(DISTINCT CASE WHEN UPPER(m.match_type) = 'TEST'
                    THEN m.match_id END) AS test_matches,
                COUNT(DISTINCT CASE WHEN UPPER(m.match_type) = 'ODI'
                    THEN m.match_id END) AS odi_matches,
                COUNT(DISTINCT CASE WHEN UPPER(m.match_type) IN ('T20','T20I')
                    THEN m.match_id END) AS t20_matches,
                ROUND(
                    1.0 * SUM(CASE WHEN UPPER(m.match_type) = 'TEST'
                        THEN ps.runs_scored ELSE 0 END) /
                    NULLIF(SUM(CASE WHEN UPPER(m.match_type) = 'TEST'
                        AND ps.is_out = 1 THEN 1 ELSE 0 END), 0),
                    2
                ) AS test_average,
                ROUND(
                    1.0 * SUM(CASE WHEN UPPER(m.match_type) = 'ODI'
                        THEN ps.runs_scored ELSE 0 END) /
                    NULLIF(SUM(CASE WHEN UPPER(m.match_type) = 'ODI'
                        AND ps.is_out = 1 THEN 1 ELSE 0 END), 0),
                    2
                ) AS odi_average,
                ROUND(
                    1.0 * SUM(CASE WHEN UPPER(m.match_type) IN ('T20','T20I')
                        THEN ps.runs_scored ELSE 0 END) /
                    NULLIF(SUM(CASE WHEN UPPER(m.match_type) IN ('T20','T20I')
                        AND ps.is_out = 1 THEN 1 ELSE 0 END), 0),
                    2
                ) AS t20_average,
                COUNT(DISTINCT m.match_id) AS total_matches
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            JOIN matches m ON m.match_id = ps.match_id
            GROUP BY p.player_id, p.full_name
            HAVING total_matches >= 20
            ORDER BY total_matches DESC;
        """,
        "chart": None,
    },

    "Q21. Weighted performance ranking": {
        "level": "Advanced",
        "question": (
            "Rank players per format using weighted batting, bowling, "
            "and fielding points from the project specification."
        ),
        "sql": """
            WITH player_format AS (
                SELECT
                    p.player_id,
                    p.full_name AS player,
                    m.match_type AS format,
                    SUM(ps.runs_scored) AS runs,
                    SUM(ps.balls_faced) AS balls_faced,
                    SUM(CASE WHEN ps.is_out = 1 THEN 1 ELSE 0 END)
                        AS dismissals,
                    SUM(ps.wickets_taken) AS wickets,
                    SUM(ps.runs_conceded) AS runs_conceded,
                    SUM(ps.overs_bowled) AS overs_bowled,
                    SUM(ps.catches) AS catches,
                    SUM(ps.stumpings) AS stumpings
                FROM player_match_stats ps
                JOIN players p ON p.player_id = ps.player_id
                JOIN matches m ON m.match_id = ps.match_id
                GROUP BY p.player_id, p.full_name, m.match_type
            ),
            metrics AS (
                SELECT *,
                    1.0 * runs / NULLIF(dismissals, 0) AS batting_average,
                    100.0 * runs / NULLIF(balls_faced, 0) AS strike_rate,
                    1.0 * runs_conceded / NULLIF(wickets, 0)
                        AS bowling_average,
                    1.0 * runs_conceded / NULLIF(overs_bowled, 0)
                        AS economy_rate
                FROM player_format
            )
            SELECT
                player,
                format,
                runs,
                wickets,
                ROUND(
                    COALESCE(runs * 0.01, 0)
                    + COALESCE(batting_average * 0.5, 0)
                    + COALESCE(strike_rate * 0.3, 0)
                    + COALESCE(wickets * 2, 0)
                    + COALESCE((50 - bowling_average) * 0.5, 0)
                    + COALESCE((6 - economy_rate) * 2, 0)
                    + catches * 3
                    + stumpings * 5,
                    2
                ) AS performance_points
            FROM metrics
            ORDER BY format, performance_points DESC;
        """,
        "chart": "bar",
    },

    "Q22. Head-to-head team comparison": {
        "level": "Advanced",
        "question": (
            "Compare team pairs with at least five matches in the "
            "last three years. Show matches, wins, average victory "
            "margin, and overall win percentage."
        ),
        "sql": """
            WITH team_results AS (
                SELECT
                    m.match_id,
                    m.match_date,
                    m.team1_id,
                    m.team2_id,
                    m.winner_team_id,
                    m.win_margin,
                    CASE
                        WHEN m.team1_id < m.team2_id THEN m.team1_id
                        ELSE m.team2_id
                    END AS pair_team1_id,
                    CASE
                        WHEN m.team1_id < m.team2_id THEN m.team2_id
                        ELSE m.team1_id
                    END AS pair_team2_id
                FROM matches m
                WHERE date(m.match_date) >= date('now', '-3 years')
            ),
            pair_results AS (
                SELECT
                    a.team_name AS team1,
                    b.team_name AS team2,
                    COUNT(*) AS total_matches,
                    SUM(CASE WHEN r.winner_team_id = a.team_id
                        THEN 1 ELSE 0 END) AS team1_wins,
                    SUM(CASE WHEN r.winner_team_id = b.team_id
                        THEN 1 ELSE 0 END) AS team2_wins,
                    ROUND(AVG(
                        CASE WHEN r.winner_team_id = a.team_id
                        THEN CAST(r.win_margin AS REAL) END
                    ), 2) AS team1_average_margin,
                    ROUND(AVG(
                        CASE WHEN r.winner_team_id = b.team_id
                        THEN CAST(r.win_margin AS REAL) END
                    ), 2) AS team2_average_margin
                FROM team_results r
                JOIN teams a ON a.team_id = r.pair_team1_id
                JOIN teams b ON b.team_id = r.pair_team2_id
                GROUP BY a.team_id, b.team_id
            )
            SELECT *,
                ROUND(100.0 * team1_wins / NULLIF(total_matches, 0), 2)
                    AS team1_win_percentage,
                ROUND(100.0 * team2_wins / NULLIF(total_matches, 0), 2)
                    AS team2_win_percentage
            FROM pair_results
            WHERE total_matches >= 5
            ORDER BY total_matches DESC;
        """,
        "chart": None,
    },

    "Q23. Recent player form": {
        "level": "Advanced",
        "question": (
            "Analyze recent player form from the last 10 saved batting "
            "performances, comparing runs and strike rates over the last "
            "five and last ten performances, 50+ scores, consistency, "
            "and a simple recent-form category."
        ),
        "sql": """
            WITH ranked_innings AS (
                SELECT
                    p.player_id,
                    p.full_name AS player,
                    m.match_date,
                    ps.match_id,
                    ps.innings_number,
                    ps.runs_scored,
                    ps.balls_faced,
                    100.0 * ps.runs_scored /
                        NULLIF(ps.balls_faced, 0) AS innings_strike_rate,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.player_id
                        ORDER BY
                            date(m.match_date) DESC,
                            ps.match_id DESC,
                            ps.innings_number DESC
                    ) AS recent_rank
                FROM player_match_stats ps
                JOIN players p ON p.player_id = ps.player_id
                JOIN matches m ON m.match_id = ps.match_id
                WHERE COALESCE(ps.balls_faced, 0) > 0
            ),
            recent_form AS (
                SELECT
                    player_id,
                    player,
                    COUNT(*) AS innings_available,
                    AVG(CASE WHEN recent_rank <= 5
                        THEN runs_scored END) AS average_last_5,
                    AVG(runs_scored) AS average_last_10,
                    AVG(CASE WHEN recent_rank <= 5
                        THEN innings_strike_rate END) AS strike_rate_last_5,
                    AVG(innings_strike_rate) AS strike_rate_last_10,
                    SUM(CASE WHEN runs_scored >= 50
                        THEN 1 ELSE 0 END) AS scores_50_plus,
                    AVG(runs_scored * runs_scored)
                        - AVG(runs_scored) * AVG(runs_scored)
                        AS run_variance
                FROM ranked_innings
                WHERE recent_rank <= 10
                GROUP BY player_id, player
            ),
            scored AS (
                SELECT
                    *,
                    CASE
                        WHEN average_last_5 IS NULL THEN 'Insufficient data'
                        WHEN average_last_5 >= average_last_10 * 1.2
                            THEN 'Excellent Form'
                        WHEN average_last_5 >= average_last_10
                            THEN 'Good Form'
                        WHEN average_last_5 >= average_last_10 * 0.8
                            THEN 'Average Form'
                        ELSE 'Poor Form'
                    END AS form_category
                FROM recent_form
            )
            SELECT
                player,
                innings_available,
                ROUND(average_last_5, 2) AS average_runs_last_5,
                ROUND(average_last_10, 2) AS average_runs_last_10,
                ROUND(strike_rate_last_5, 2) AS strike_rate_last_5,
                ROUND(strike_rate_last_10, 2) AS strike_rate_last_10,
                scores_50_plus,
                ROUND(SQRT(MAX(0, run_variance)), 2)
                    AS run_standard_deviation,
                form_category
            FROM scored
            ORDER BY average_last_5 DESC;
        """,
        "chart": None,
    },

    "Q24. Best batting partnerships": {
        "level": "Advanced",
        "question": (
            "Rank batting pairs appearing in at least five recorded "
            "partnerships. Show average runs, partnerships over 50, "
            "highest partnership, and success rate."
        ),
        "sql": """
            WITH pair_stats AS (
                SELECT
                    CASE WHEN batter1_name <= batter2_name
                        THEN batter1_name ELSE batter2_name END AS batter1,
                    CASE WHEN batter1_name <= batter2_name
                        THEN batter2_name ELSE batter1_name END AS batter2,
                    COUNT(*) AS partnership_count,
                    ROUND(AVG(runs), 2) AS average_partnership_runs,
                    SUM(CASE WHEN runs > 50 THEN 1 ELSE 0 END)
                        AS partnerships_over_50,
                    MAX(runs) AS highest_partnership
                FROM partnerships
                GROUP BY
                    CASE WHEN batter1_name <= batter2_name
                        THEN batter1_name ELSE batter2_name END,
                    CASE WHEN batter1_name <= batter2_name
                        THEN batter2_name ELSE batter1_name END
                HAVING COUNT(*) >= 5
            )
            SELECT *,
                ROUND(
                    100.0 * partnerships_over_50 /
                    NULLIF(partnership_count, 0),
                    2
                ) AS success_rate_percentage
            FROM pair_stats
            ORDER BY average_partnership_runs DESC;
        """,
        "chart": "bar",
    },

    "Q25. Quarterly player performance evolution": {
        "level": "Advanced",
        "question": (
            "Track quarterly average runs and strike rate. Compare "
            "quarters and label the observed career trajectory. Include "
            "players with at least six qualifying quarters and at least "
            "three matches in each quarter."
        ),
        "sql": """
            WITH quarterly AS (
                SELECT
                    p.player_id,
                    p.full_name AS player,
                    strftime('%Y', m.match_date) AS year,
                    CAST(
                        (CAST(strftime('%m', m.match_date) AS INTEGER) - 1)
                        / 3 + 1 AS INTEGER
                    ) AS quarter,
                    COUNT(DISTINCT m.match_id) AS matches,
                    AVG(ps.runs_scored) AS average_runs,
                    100.0 * SUM(ps.runs_scored) /
                        NULLIF(SUM(ps.balls_faced), 0) AS strike_rate
                FROM player_match_stats ps
                JOIN players p ON p.player_id = ps.player_id
                JOIN matches m ON m.match_id = ps.match_id
                WHERE ps.balls_faced > 0
                  AND m.match_date IS NOT NULL
                GROUP BY p.player_id, p.full_name, year, quarter
                HAVING COUNT(DISTINCT m.match_id) >= 3
            ),
            eligible AS (
                SELECT player_id
                FROM quarterly
                GROUP BY player_id
                HAVING COUNT(*) >= 6
            ),
            trend AS (
                SELECT
                    q.*,
                    LAG(q.average_runs) OVER (
                        PARTITION BY q.player_id
                        ORDER BY q.year, q.quarter
                    ) AS previous_quarter_average,
                    FIRST_VALUE(q.average_runs) OVER (
                        PARTITION BY q.player_id
                        ORDER BY q.year, q.quarter
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) AS first_quarter_average,
                    LAST_VALUE(q.average_runs) OVER (
                        PARTITION BY q.player_id
                        ORDER BY q.year, q.quarter
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) AS latest_quarter_average
                FROM quarterly q
                JOIN eligible e ON e.player_id = q.player_id
            )
            SELECT
                player,
                year,
                quarter,
                matches,
                ROUND(average_runs, 2) AS average_runs,
                ROUND(strike_rate, 2) AS strike_rate,
                ROUND(
                    average_runs - previous_quarter_average,
                    2
                ) AS change_in_average_runs,
                CASE
                    WHEN latest_quarter_average > first_quarter_average * 1.1
                        THEN 'Career Ascending'
                    WHEN latest_quarter_average < first_quarter_average * 0.9
                        THEN 'Career Declining'
                    ELSE 'Career Stable'
                END AS career_trajectory
            FROM trend
            ORDER BY player, year, quarter;
        """,
        "chart": None,
    },
}


# ============================================================
# QUERY EXECUTION
# ============================================================

def run_query(sql):
    """Execute a read-only SELECT query against the local database."""
    if not sql.strip().lower().startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed.")

    with get_connection() as conn:
        return pd.read_sql_query(sql, conn)


# ============================================================
# DATABASE SUMMARY
# ============================================================

try:
    with get_connection() as conn:
        total_matches = conn.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()[0]

        total_players = conn.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0]

        total_teams = conn.execute(
            "SELECT COUNT(*) FROM teams"
        ).fetchone()[0]

        total_stat_records = conn.execute(
            "SELECT COUNT(*) FROM player_match_stats"
        ).fetchone()[0]

        total_partnerships = conn.execute(
            "SELECT COUNT(*) FROM partnerships"
        ).fetchone()[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Saved Matches", total_matches)
    c2.metric("Saved Players", total_players)
    c3.metric("Saved Teams", total_teams)
    c4.metric("Player Stat Records", total_stat_records)
    c5.metric("Partnerships", total_partnerships)

except Exception as error:
    st.error(f"Could not load database summary: {error}")
    st.stop()

st.divider()


# ============================================================
# QUESTION SELECTOR
# ============================================================

st.subheader("🔍 Explore SQL Questions")

level_filter = st.selectbox(
    "Filter by difficulty",
    ["All levels", "Beginner", "Intermediate", "Advanced"],
)

available_questions = [
    name
    for name, item in ANALYSES.items()
    if level_filter == "All levels" or item["level"] == level_filter
]

selected_question = st.selectbox(
    "Select an analytical question",
    available_questions,
)

analysis = ANALYSES[selected_question]

st.caption(
    f"Difficulty: {analysis['level']} | "
    f"Question {list(ANALYSES).index(selected_question) + 1} of 25"
)

st.markdown(f"**Question:** {analysis['question']}")

with st.expander("View SQL query", expanded=True):
    st.code(analysis["sql"].strip(), language="sql")

run_clicked = st.button(
    "▶ Run SQL Query",
    type="primary",
    key="run_sql_query",
)

if run_clicked:
    try:
        result = run_query(analysis["sql"])
        st.session_state["sql_result"] = result
        st.session_state["sql_result_question"] = selected_question
        st.session_state.pop("sql_query_error", None)

    except Exception as error:
        st.session_state["sql_query_error"] = str(error)
        st.session_state.pop("sql_result", None)
        st.session_state.pop("sql_result_question", None)

if st.session_state.get("sql_query_error"):
    st.error("This query could not be executed against the current database.")
    st.code(st.session_state["sql_query_error"])

if (
    "sql_result" in st.session_state
    and st.session_state.get("sql_result_question") == selected_question
):
    result = st.session_state["sql_result"]

    st.subheader("📋 Query Results")
    st.caption(f"{len(result)} row(s) returned.")

    if result.empty:
        st.info(
            "The query ran successfully but returned no rows. "
            "This can happen when the database does not yet contain "
            "enough matching records."
        )

    else:
        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True,
        )

        chart_type = analysis["chart"]

        if chart_type == "bar" and len(result.columns) >= 2:
            numeric_columns = result.select_dtypes(
                include="number"
            ).columns.tolist()

            category_candidates = [
                column
                for column in result.columns
                if column not in numeric_columns
            ]

            if numeric_columns and category_candidates:
                category = category_candidates[0]

                # Prefer the first numeric column as the chart measure.
                metric = numeric_columns[0]

                chart_data = result.copy()

                # Avoid rendering excessively large charts.
                if len(chart_data) > 30:
                    chart_data = chart_data.head(30)

                fig = px.bar(
                    chart_data.sort_values(metric),
                    x=metric,
                    y=category,
                    orientation="h",
                    title=(
                        f"{metric.replace('_', ' ').title()} by "
                        f"{category.replace('_', ' ').title()}"
                    ),
                    color=metric,
                )

                fig.update_layout(
                    template="plotly_dark",
                    yaxis={"categoryorder": "total ascending"},
                )

                st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            "⬇ Download Results as CSV",
            data=result.to_csv(index=False).encode("utf-8"),
            file_name="cricbuzz_sql_results.csv",
            mime="text/csv",
            key=f"download_{list(ANALYSES).index(selected_question)}",
        )

st.divider()

st.info(
    "Data coverage note: these queries use only records saved in your local "
    "SQLite database. The current dataset has 25 matches but player statistics "
    "for only one Test match; toss details, venue countries/capacities, and "
    "most player metadata are not yet populated. Therefore, zero-row results "
    "may reflect missing coverage rather than a SQL error. Queries requiring "
    "historical thresholds (such as 5, 10, or 20 matches) need more imported "
    "history before they can produce representative results."
)
