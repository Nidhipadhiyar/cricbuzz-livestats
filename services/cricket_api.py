
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv(
    "CRICKET_API_HOST",
    "cricbuzz-cricket.p.rapidapi.com",
)
API_KEY = os.getenv("CRICKET_API_KEY")
BASE_URL = f"https://{API_HOST}"


def _headers():
    """Build authenticated RapidAPI request headers."""
    if not API_KEY:
        raise RuntimeError(
            "CRICKET_API_KEY is missing. Add it to your .env file."
        )

    return {
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": API_KEY,
    }


def _get_json(url, params=None):
    """Make an API request and return its JSON response."""
    response = requests.get(
        url,
        headers=_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def _timestamp_to_date(value):
    """Convert Cricbuzz millisecond timestamps to YYYY-MM-DD."""
    if value in (None, ""):
        return None

    try:
        # Cricbuzz commonly provides timestamps in milliseconds.
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000

        return datetime.fromtimestamp(
            timestamp, tz=timezone.utc
        ).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        # Preserve a date string if the API already supplied one.
        if isinstance(value, str) and "-" in value:
            return value[:10]
        return None


def get_live_matches():
    """Fetch match listings from the Cricbuzz live endpoint."""
    return _get_json(f"{BASE_URL}/matches/v1/live")


def _team_name(team):
    """Extract a team name from a Cricbuzz team object."""
    if not isinstance(team, dict):
        return None

    return (
        team.get("teamName")
        or team.get("teamSName")
        or team.get("name")
    )


def _venue_value(venue_info, *keys):
    """Return the first available venue field."""
    if not isinstance(venue_info, dict):
        return None

    for key in keys:
        value = venue_info.get(key)
        if value not in (None, ""):
            return value

    return None


def extract_matches(data):
    """Flatten Cricbuzz's nested match response into a list."""
    matches = []

    for match_type in data.get("typeMatches", []):
        for series_item in match_type.get("seriesMatches", []):
            series_wrapper = series_item.get("seriesAdWrapper", {})

            if not isinstance(series_wrapper, dict):
                continue

            series_id = series_wrapper.get("seriesId")
            wrapper_series_name = series_wrapper.get("seriesName")

            for match_item in series_wrapper.get("matches", []):
                info = match_item.get("matchInfo", {})
                score = match_item.get("matchScore", {})

                if not isinstance(info, dict):
                    continue

                if not isinstance(score, dict):
                    score = {}

                team1 = info.get("team1", {})
                team2 = info.get("team2", {})
                venue_info = info.get("venueInfo", {})

                if not isinstance(team1, dict):
                    team1 = {}
                if not isinstance(team2, dict):
                    team2 = {}
                if not isinstance(venue_info, dict):
                    venue_info = {}

                team1_score = score.get("team1Score", {})
                team2_score = score.get("team2Score", {})

                if not isinstance(team1_score, dict):
                    team1_score = {}
                if not isinstance(team2_score, dict):
                    team2_score = {}

                start_date = _timestamp_to_date(
                    info.get("startDate")
                    or info.get("startTime")
                    or info.get("matchStartTimestamp")
                )

                series_start_date = _timestamp_to_date(
                    info.get("seriesStartDt")
                )

                series_end_date = _timestamp_to_date(
                    info.get("seriesEndDt")
                )

                winner = (
                    info.get("winner")
                    or info.get("winnerName")
                    or info.get("winningTeam")
                )
                if isinstance(winner, dict):
                    winner = _team_name(winner)

                toss_winner = (
                    info.get("tossWinnerName")
                    or info.get("tossWinner")
                )
                if isinstance(toss_winner, dict):
                    toss_winner = _team_name(toss_winner)

                matches.append({
                    "match_id": info.get("matchId"),
                    "series_id": info.get("seriesId") or series_id,
                    "series": (
                        info.get("seriesName")
                        or wrapper_series_name
                    ),
                    "match": info.get("matchDesc"),
                    "format": info.get("matchFormat"),
                    "team1": _team_name(team1) or "Team 1",
                    "team2": _team_name(team2) or "Team 2",
                    "status": info.get("status", ""),
                    "state": info.get("state", ""),
                    "match_date": start_date,
                    "match_end_date": _timestamp_to_date(
                        info.get("endDate")
                    ),
                    "series_start_date": series_start_date,
                    "series_end_date": series_end_date,
                    "winner": winner,
                    "win_margin": (
                        info.get("winByRuns")
                        or info.get("winByInnings")
                        or info.get("winByWickets")
                    ),
                    "win_type": (
                        "runs" if info.get("winByRuns") else
                        "wickets" if info.get("winByWickets") else
                        "innings" if info.get("winByInnings") else
                        None
                    ),
                    "toss_winner": toss_winner,
                    "toss_decision": (
                        info.get("tossDecision")
                        or info.get("tossDecisionName")
                    ),
                    "venue": _venue_value(
                        venue_info, "ground", "name"
                    ),
                    "city": _venue_value(venue_info, "city"),
                    "venue_country": _venue_value(
                        venue_info, "country"
                    ),
                    "team1_country": team1.get("country"),
                    "team2_country": team2.get("country"),
                    "team1_score": team1_score,
                    "team2_score": team2_score,
                })

    return matches


def search_players(query):
    """Search real players using the Cricbuzz API."""
    return _get_json(
        f"{BASE_URL}/stats/v1/player/search",
        params={"plrN": query},
    )


def get_player_batting_stats(player_id):
    """Fetch batting statistics for a Cricbuzz player ID."""
    return _get_json(
        f"{BASE_URL}/stats/v1/player/{player_id}/batting"
    )


def get_player_bowling_stats(player_id):
    """Fetch bowling statistics for a Cricbuzz player ID."""
    return _get_json(
        f"{BASE_URL}/stats/v1/player/{player_id}/bowling"
    )


def get_match_scorecard(match_id):
    """Fetch a detailed scorecard for a Cricbuzz match ID."""
    return _get_json(
        f"{BASE_URL}/mcenter/v1/{match_id}/scard"
    )
