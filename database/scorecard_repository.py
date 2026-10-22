
from database.db_connection import get_connection
from services.cricket_api import get_match_scorecard


def _safe_int(value, default=0):
    """Convert a value to an integer safely."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    """Convert a value to a float safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _cricket_overs_to_decimal(value, balls=None):
    """
    Convert cricket overs notation to decimal overs.

    Example:
        24.1 means 24 overs and 1 ball = 24 + 1/6 overs.
        42.3 means 42 overs and 3 balls = 42.5 overs.

    When the API provides the total number of balls, use it
    because it is more reliable than parsing the overs string.
    """
    if balls is not None:
        try:
            return int(balls) / 6
        except (TypeError, ValueError):
            pass

    if value is None:
        return 0.0

    try:
        overs_text = str(value).strip()
        whole_overs, separator, remaining_balls = (
            overs_text.partition(".")
        )

        completed_overs = int(whole_overs)
        balls_in_over = int(remaining_balls) if separator else 0

        if not 0 <= balls_in_over <= 5:
            raise ValueError(
                f"Invalid cricket overs value: {value}"
            )

        return completed_overs + balls_in_over / 6

    except (TypeError, ValueError):
        raise ValueError(
            f"Cannot convert cricket overs value: {value}"
        )


def _get_or_create_player(connection, player_data):
    """Find or create a player using their Cricbuzz player ID."""
    external_id = str(player_data["id"])
    name = (
        player_data.get("name")
        or player_data.get("batsmanname")
        or player_data.get("bat1name")
        or player_data.get("bat2name")
        or "Unknown player"
    )

    connection.execute(
        """
        INSERT INTO players (full_name, external_player_id)
        VALUES (?, ?)
        ON CONFLICT(external_player_id) DO UPDATE SET
            full_name = excluded.full_name
        """,
        (name, external_id),
    )

    row = connection.execute(
        """
        SELECT player_id
        FROM players
        WHERE external_player_id = ?
        """,
        (external_id,),
    ).fetchone()

    return row["player_id"]


def _get_or_create_team(connection, team_name):
    """Find or create a team by name."""
    if not team_name:
        return None

    connection.execute(
        """
        INSERT INTO teams (team_name)
        VALUES (?)
        ON CONFLICT(team_name) DO NOTHING
        """,
        (team_name,),
    )

    row = connection.execute(
        """
        SELECT team_id
        FROM teams
        WHERE team_name = ?
        """,
        (team_name,),
    ).fetchone()

    return row["team_id"] if row else None


def _merge_player_stats(innings):
    """
    Combine batting and bowling figures into player records.

    Batters belong to the innings' batting team.
    Bowlers belong to the opposing team.
    """
    players = {}

    # Batting statistics
    for position, batter in enumerate(
        innings.get("batsman", []),
        start=1,
    ):
        external_id = str(batter.get("id"))

        player = players.setdefault(
            external_id,
            {
                "id": external_id,
                "name": batter.get("name", "Unknown player"),
                "team_side": "batting",
                "runs_scored": 0,
                "balls_faced": 0,
                "fours": 0,
                "sixes": 0,
                "wickets_taken": 0,
                "runs_conceded": 0,
                "overs_bowled": 0.0,
                "batting_position": position,
                "is_out": 0,
                "economy_rate": None,
            },
        )

        player.update(
            {
                "name": batter.get("name", "Unknown player"),
                "team_side": "batting",
                "runs_scored": _safe_int(batter.get("runs")),
                "balls_faced": _safe_int(batter.get("balls")),
                "fours": _safe_int(batter.get("fours")),
                "sixes": _safe_int(batter.get("sixes")),
                "is_out": int(bool(batter.get("outdec"))),
                "batting_position": position,
            }
        )

    # Bowling statistics
    for bowler in innings.get("bowler", []):
        external_id = str(bowler.get("id"))

        player = players.setdefault(
            external_id,
            {
                "id": external_id,
                "name": bowler.get("name", "Unknown player"),
                "team_side": "bowling",
                "runs_scored": 0,
                "balls_faced": 0,
                "fours": 0,
                "sixes": 0,
                "wickets_taken": 0,
                "runs_conceded": 0,
                "overs_bowled": 0.0,
                "batting_position": None,
                "is_out": 0,
                "economy_rate": None,
            },
        )

        player.update(
            {
                "name": bowler.get("name", "Unknown player"),
                "team_side": "bowling",
                "wickets_taken": _safe_int(bowler.get("wickets")),
                "runs_conceded": _safe_int(bowler.get("runs")),
                "overs_bowled": _cricket_overs_to_decimal(
                    bowler.get("overs"),
                    balls=bowler.get("balls"),
                ),
                "economy_rate": _safe_float(
                    bowler.get("economy"),
                    default=None,
                ),
            }
        )

    # Calculate batting strike rate.
    for player in players.values():
        runs = player["runs_scored"]
        balls = player["balls_faced"]

        player["strike_rate"] = (
            runs * 100 / balls if balls > 0 else None
        )

    return players


def save_match_scorecard(external_match_id):
    """
    Fetch and save a real Cricbuzz scorecard to SQLite.

    Re-importing a match replaces its previously imported
    innings, player statistics, and partnerships.
    """
    external_match_id = str(external_match_id)
    data = get_match_scorecard(external_match_id)
    innings_list = data.get("scorecard", [])

    if not innings_list:
        raise ValueError(
            f"No innings found in the scorecard for "
            f"{external_match_id}."
        )

    with get_connection() as connection:
        match = connection.execute(
            """
            SELECT
                m.match_id,
                m.team1_id,
                m.team2_id,
                t1.team_name AS team1_name,
                t2.team_name AS team2_name
            FROM matches m
            LEFT JOIN teams t1 ON t1.team_id = m.team1_id
            LEFT JOIN teams t2 ON t2.team_id = m.team2_id
            WHERE m.external_match_id = ?
            """,
            (external_match_id,),
        ).fetchone()

        if not match:
            raise ValueError(
                f"Match {external_match_id} is not saved in "
                "the database. Sync its match metadata first."
            )

        local_match_id = match["match_id"]

        # Match the saved teams by their names.
        match_teams = {
            (match["team1_name"] or "").strip().casefold():
                match["team1_id"],
            (match["team2_name"] or "").strip().casefold():
                match["team2_id"],
        }

        # Validate team names before deleting previous scorecard data.
        for innings in innings_list:
            batting_team_name = (
                innings.get("batteamname") or ""
            ).strip()

            if batting_team_name.casefold() not in match_teams:
                raise ValueError(
                    f"Batting team '{batting_team_name}' does not "
                    f"match the saved match teams: "
                    f"{list(match_teams.keys())}. "
                    "Check the match metadata before importing."
                )

        # Remove only this match's previous scorecard data.
        connection.execute(
            """
            DELETE FROM player_match_stats
            WHERE match_id = ?
            """,
            (local_match_id,),
        )

        connection.execute(
            """
            DELETE FROM partnerships
            WHERE match_id = ?
            """,
            (local_match_id,),
        )

        connection.execute(
            """
            DELETE FROM match_innings
            WHERE match_id = ?
            """,
            (local_match_id,),
        )

        for innings_number, innings in enumerate(
            innings_list,
            start=1,
        ):
            batting_team_name = (
                innings.get("batteamname") or ""
            ).strip()

            batting_team_id = match_teams[
                batting_team_name.casefold()
            ]

            opponent_team_id = next(
                (
                    saved_team_id
                    for saved_name, saved_team_id
                    in match_teams.items()
                    if saved_name != batting_team_name.casefold()
                ),
                None,
            )

            if opponent_team_id is None:
                raise ValueError(
                    "Could not identify the opposing team."
                )

            extras_data = innings.get("extras") or {}
            extras_total = _safe_int(
                extras_data.get("total")
            )

            # Save innings summary.
            connection.execute(
                """
                INSERT INTO match_innings (
                    match_id,
                    external_innings_id,
                    innings_number,
                    team_id,
                    total_runs,
                    wickets_lost,
                    overs,
                    run_rate,
                    extras
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    local_match_id,
                    str(
                        innings.get(
                            "inningsid",
                            innings_number,
                        )
                    ),
                    innings_number,
                    batting_team_id,
                    _safe_int(innings.get("score")),
                    _safe_int(innings.get("wickets")),
                    _cricket_overs_to_decimal(
                        innings.get("overs")
                    ),
                    _safe_float(innings.get("runrate")),
                    extras_total,
                ),
            )

            # Merge batting and bowling figures.
            player_stats = _merge_player_stats(innings)

            for player in player_stats.values():
                local_player_id = _get_or_create_player(
                    connection,
                    {
                        "id": player["id"],
                        "name": player["name"],
                    },
                )

                # Assign batters and bowlers to their correct teams.
                player_team_id = (
                    batting_team_id
                    if player["team_side"] == "batting"
                    else opponent_team_id
                )

                economy = player.get("economy_rate")

                connection.execute(
                    """
                    INSERT INTO player_match_stats (
                        match_id,
                        player_id,
                        team_id,
                        runs_scored,
                        balls_faced,
                        fours,
                        sixes,
                        wickets_taken,
                        runs_conceded,
                        overs_bowled,
                        batting_position,
                        innings_number,
                        strike_rate,
                        economy_rate,
                        is_out
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        local_match_id,
                        local_player_id,
                        player_team_id,
                        player["runs_scored"],
                        player["balls_faced"],
                        player["fours"],
                        player["sixes"],
                        player["wickets_taken"],
                        player["runs_conceded"],
                        player["overs_bowled"],
                        player["batting_position"],
                        innings_number,
                        player["strike_rate"],
                        economy,
                        player["is_out"],
                    ),
                )

            # Save the partnerships returned by the API.
            partnership_data = innings.get("partnership") or {}
            partnerships = partnership_data.get("partnership", [])

            for partnership_number, partnership in enumerate(
                partnerships,
                start=1,
            ):
                connection.execute(
                    """
                    INSERT INTO partnerships (
                        match_id,
                        innings_number,
                        partnership_number,
                        batter1_external_id,
                        batter1_name,
                        batter2_external_id,
                        batter2_name,
                        runs,
                        balls
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        local_match_id,
                        innings_number,
                        partnership_number,
                        str(partnership.get("bat1id", "")),
                        partnership.get("bat1name", ""),
                        str(partnership.get("bat2id", "")),
                        partnership.get("bat2name", ""),
                        _safe_int(partnership.get("totalruns")),
                        _safe_int(partnership.get("totalballs")),
                    ),
                )

    return {
        "external_match_id": external_match_id,
        "innings_saved": len(innings_list),
    }
