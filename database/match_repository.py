
import re

from database.db_connection import get_connection


def _clean(value):
    """Convert empty strings and whitespace-only values to None."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _find_winner(status, team1, team2):
    """Identify a winner only when the status clearly names a team."""
    status = _clean(status)
    if not status:
        return None

    status_lower = status.lower()

    # Draws, abandoned games and no-results must not have a winner.
    if any(term in status_lower for term in (
        "draw", "no result", "abandon", "cancelled", "canceled", "tied"
    )):
        return None

    for team in (team1, team2):
        if team and re.search(
            rf"^{re.escape(team)}\s+won\b",
            status,
            flags=re.IGNORECASE,
        ):
            return team

    return None


def _team_id(connection, team_name, country=None):
    """Create or reuse a team without erasing existing country metadata."""
    team_name = _clean(team_name) or "Unknown team"
    country = _clean(country)

    connection.execute(
        """
        INSERT INTO teams (team_name, country)
        VALUES (?, ?)
        ON CONFLICT(team_name) DO UPDATE SET
            country = COALESCE(teams.country, excluded.country)
        """,
        (team_name, country),
    )

    row = connection.execute(
        "SELECT team_id FROM teams WHERE team_name = ?",
        (team_name,),
    ).fetchone()

    return row["team_id"]


def save_matches(matches):
    """Insert or update match listings without erasing known metadata."""
    saved = 0

    with get_connection() as connection:
        for match in matches:
            external_id = _clean(match.get("match_id"))
            if external_id is None:
                continue

            external_id = str(external_id)

            team1 = _clean(match.get("team1")) or "Team 1"
            team2 = _clean(match.get("team2")) or "Team 2"

            team1_id = _team_id(
                connection, team1, match.get("team1_country")
            )
            team2_id = _team_id(
                connection, team2, match.get("team2_country")
            )

            venue_name = _clean(match.get("venue")) or "Unknown venue"
            city = _clean(match.get("city"))
            venue_country = _clean(match.get("venue_country"))

            venue = connection.execute(
                """
                SELECT venue_id FROM venues
                WHERE venue_name = ? AND city IS ?
                LIMIT 1
                """,
                (venue_name, city),
            ).fetchone()

            if venue:
                venue_id = venue["venue_id"]
                connection.execute(
                    """
                    UPDATE venues
                    SET country = COALESCE(country, ?)
                    WHERE venue_id = ?
                    """,
                    (venue_country, venue_id),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO venues (venue_name, city, country)
                    VALUES (?, ?, ?)
                    """,
                    (venue_name, city, venue_country),
                )
                venue_id = cursor.lastrowid

            series_name = (
                _clean(match.get("series")) or "Unknown series"
            )
            match_type = _clean(match.get("format"))

            series = connection.execute(
                """
                SELECT series_id FROM series
                WHERE series_name = ?
                LIMIT 1
                """,
                (series_name,),
            ).fetchone()

            if series:
                series_id = series["series_id"]
                connection.execute(
                    """
                    UPDATE series
                    SET match_type = COALESCE(match_type, ?),
                        host_country = COALESCE(host_country, ?),
                        start_date = COALESCE(start_date, ?),
                        planned_matches = COALESCE(planned_matches, ?)
                    WHERE series_id = ?
                    """,
                    (
                        match_type,
                        _clean(match.get("host_country")),
                        _clean(match.get("series_start_date")),
                        match.get("planned_matches"),
                        series_id,
                    ),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO series (
                        series_name, host_country, match_type,
                        start_date, planned_matches
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        series_name,
                        _clean(match.get("host_country")),
                        match_type,
                        _clean(match.get("series_start_date")),
                        match.get("planned_matches"),
                    ),
                )
                series_id = cursor.lastrowid

            status = (
                _clean(match.get("status"))
                or _clean(match.get("state"))
            )

            winner_name = _clean(match.get("winner"))
            if not winner_name:
                winner_name = _find_winner(status, team1, team2)

            winner_id = (
                _team_id(connection, winner_name)
                if winner_name else None
            )

            toss_winner_name = _clean(match.get("toss_winner"))
            toss_winner_id = (
                _team_id(connection, toss_winner_name)
                if toss_winner_name else None
            )

            match_date = _clean(match.get("match_date"))
            description = _clean(match.get("match")) or "Match"

            connection.execute(
                """
                INSERT INTO matches (
                    external_match_id, series_id, match_description,
                    match_type, team1_id, team2_id, venue_id,
                    match_date, status, winner_team_id,
                    win_margin, win_type, toss_winner_team_id,
                    toss_decision
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_match_id) DO UPDATE SET
                    series_id = excluded.series_id,
                    match_description = excluded.match_description,
                    match_type = COALESCE(
                        excluded.match_type, matches.match_type
                    ),
                    team1_id = excluded.team1_id,
                    team2_id = excluded.team2_id,
                    venue_id = excluded.venue_id,
                    match_date = COALESCE(
                        excluded.match_date, matches.match_date
                    ),
                    status = COALESCE(excluded.status, matches.status),
                    winner_team_id = COALESCE(
                        excluded.winner_team_id, matches.winner_team_id
                    ),
                    win_margin = COALESCE(
                        excluded.win_margin, matches.win_margin
                    ),
                    win_type = COALESCE(
                        excluded.win_type, matches.win_type
                    ),
                    toss_winner_team_id = COALESCE(
                        excluded.toss_winner_team_id,
                        matches.toss_winner_team_id
                    ),
                    toss_decision = COALESCE(
                        excluded.toss_decision, matches.toss_decision
                    )
                """,
                (
                    external_id,
                    series_id,
                    description,
                    match_type,
                    team1_id,
                    team2_id,
                    venue_id,
                    match_date,
                    status,
                    winner_id,
                    match.get("win_margin"),
                    _clean(match.get("win_type")),
                    toss_winner_id,
                    _clean(match.get("toss_decision")),
                ),
            )

            saved += 1

    return saved


def get_saved_matches():
    """Retrieve saved matches with their related team, series and venue."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                m.external_match_id,
                s.series_name,
                m.match_description,
                m.match_type,
                m.match_date,
                t1.team_name AS team1,
                t2.team_name AS team2,
                v.venue_name,
                v.city,
                m.status,
                winner.team_name AS winner
            FROM matches m
            LEFT JOIN series s ON m.series_id = s.series_id
            LEFT JOIN teams t1 ON m.team1_id = t1.team_id
            LEFT JOIN teams t2 ON m.team2_id = t2.team_id
            LEFT JOIN venues v ON m.venue_id = v.venue_id
            LEFT JOIN teams winner
                ON m.winner_team_id = winner.team_id
            ORDER BY m.match_id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]
