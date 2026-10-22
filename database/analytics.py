
from database.db_connection import get_connection


def get_dashboard_summary():
    with get_connection() as connection:
        total_matches = connection.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()[0]

        format_counts = connection.execute(
            """
            SELECT
                COALESCE(match_type, 'Unknown') AS format,
                COUNT(*) AS total
            FROM matches
            GROUP BY match_type
            ORDER BY total DESC
            """
        ).fetchall()

        status_counts = connection.execute(
            """
            SELECT
                COALESCE(status, 'Unknown') AS status,
                COUNT(*) AS total
            FROM matches
            GROUP BY status
            ORDER BY total DESC
            """
        ).fetchall()

        matches = connection.execute(
            """
            SELECT
                m.external_match_id,
                s.series_name,
                m.match_description,
                m.match_type,
                t1.team_name AS team1,
                t2.team_name AS team2,
                v.venue_name,
                v.city,
                m.status
            FROM matches m
            LEFT JOIN series s ON m.series_id = s.series_id
            LEFT JOIN teams t1 ON m.team1_id = t1.team_id
            LEFT JOIN teams t2 ON m.team2_id = t2.team_id
            LEFT JOIN venues v ON m.venue_id = v.venue_id
            ORDER BY m.match_id DESC
            """
        ).fetchall()

    return {
        "total_matches": total_matches,
        "format_counts": [dict(row) for row in format_counts],
        "status_counts": [dict(row) for row in status_counts],
        "matches": [dict(row) for row in matches],
    }
