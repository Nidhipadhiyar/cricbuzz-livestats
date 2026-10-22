
import streamlit as st
import pandas as pd

from services.cricket_api import get_live_matches, extract_matches
from database.db_connection import get_connection
from database.match_repository import save_matches


st.set_page_config(
    page_title="Live Matches | Cricbuzz LiveStats",
    page_icon="🏏",
    layout="wide",
)

st.title("🏏 Live Cricket Matches")
st.caption("Live match information powered by the Cricbuzz API")


# ---------- Helpers ----------

def format_cricket_overs(value):
    """Convert decimal overs stored in SQLite back to cricket notation."""
    if value is None:
        return "—"

    try:
        total_balls = round(float(value) * 6)
        overs, balls = divmod(total_balls, 6)
        return f"{overs}.{balls}"
    except (TypeError, ValueError):
        return str(value)


@st.cache_data(ttl=60)
def load_matches():
    data = get_live_matches()
    return extract_matches(data)


def load_saved_scorecards():
    """Get matches that already have imported scorecard innings."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT
                m.external_match_id,
                m.match_description,
                m.match_type,
                t1.team_name AS team1,
                t2.team_name AS team2
            FROM matches m
            JOIN match_innings mi ON mi.match_id = m.match_id
            LEFT JOIN teams t1 ON t1.team_id = m.team1_id
            LEFT JOIN teams t2 ON t2.team_id = m.team2_id
            ORDER BY m.match_id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def load_scorecard(match_external_id):
    """Load innings, player statistics and partnerships from SQLite."""
    with get_connection() as connection:
        match = connection.execute(
            """
            SELECT match_id, match_description, match_type
            FROM matches
            WHERE external_match_id = ?
            """,
            (str(match_external_id),),
        ).fetchone()

        if not match:
            return None, [], [], []

        innings = connection.execute(
            """
            SELECT
                mi.innings_number,
                t.team_name,
                mi.total_runs,
                mi.wickets_lost,
                mi.overs,
                mi.run_rate,
                mi.extras
            FROM match_innings mi
            LEFT JOIN teams t ON t.team_id = mi.team_id
            WHERE mi.match_id = ?
            ORDER BY mi.innings_number
            """,
            (match["match_id"],),
        ).fetchall()

        batting = connection.execute(
            """
            SELECT
                s.innings_number,
                t.team_name,
                p.full_name AS player,
                s.runs_scored,
                s.balls_faced,
                s.fours,
                s.sixes,
                s.strike_rate,
                s.is_out,
                s.batting_position
            FROM player_match_stats s
            JOIN players p ON p.player_id = s.player_id
            LEFT JOIN teams t ON t.team_id = s.team_id
            WHERE s.match_id = ?
              AND s.batting_position IS NOT NULL
            ORDER BY s.innings_number, s.batting_position
            """,
            (match["match_id"],),
        ).fetchall()

        bowling = connection.execute(
            """
            SELECT
                s.innings_number,
                t.team_name,
                p.full_name AS bowler,
                s.overs_bowled,
                s.runs_conceded,
                s.wickets_taken,
                s.economy_rate
            FROM player_match_stats s
            JOIN players p ON p.player_id = s.player_id
            LEFT JOIN teams t ON t.team_id = s.team_id
            WHERE s.match_id = ?
              AND s.overs_bowled > 0
            ORDER BY s.innings_number, s.overs_bowled DESC
            """,
            (match["match_id"],),
        ).fetchall()

        partnerships = connection.execute(
            """
            SELECT
                innings_number,
                partnership_number,
                batter1_name,
                batter2_name,
                runs,
                balls
            FROM partnerships
            WHERE match_id = ?
            ORDER BY innings_number, partnership_number
            """,
            (match["match_id"],),
        ).fetchall()

    return (
        dict(match),
        [dict(row) for row in innings],
        [dict(row) for row in batting],
        [dict(row) for row in bowling],
        [dict(row) for row in partnerships],
    )


def display_scorecard(external_match_id):
    result = load_scorecard(external_match_id)

    if result[0] is None:
        st.warning("The selected match could not be found.")
        return

    match, innings, batting, bowling, partnerships = result

    st.subheader("Detailed Scorecard")
    st.caption(
        f"{match.get('match_description') or 'Match'}"
        f" · {match.get('match_type') or 'Format unavailable'}"
    )

    if not innings:
        st.info("No imported innings are available for this match.")
        return

    # Innings summary
    st.markdown("### Innings Summary")

    summary_rows = []
    for item in innings:
        summary_rows.append(
            {
                "Innings": item["innings_number"],
                "Batting Team": item["team_name"] or "Unknown",
                "Score": (
                    f'{item["total_runs"]}/{item["wickets_lost"]}'
                ),
                "Overs": format_cricket_overs(item["overs"]),
                "Run Rate": (
                    round(item["run_rate"], 2)
                    if item["run_rate"] is not None
                    else None
                ),
                "Extras": item["extras"],
            }
        )

    st.dataframe(
        pd.DataFrame(summary_rows),
        hide_index=True,
        use_container_width=True,
    )

    batting_df = pd.DataFrame(batting)
    bowling_df = pd.DataFrame(bowling)
    partnerships_df = pd.DataFrame(partnerships)

    # Batting scorecard
    st.markdown("### Batting")

    if not batting_df.empty:
        for innings_number in sorted(
            batting_df["innings_number"].unique()
        ):
            innings_batting = batting_df[
                batting_df["innings_number"] == innings_number
            ]

            team_name = innings_batting.iloc[0]["team_name"]

            with st.expander(
                f"Innings {innings_number} — {team_name}",
                expanded=True,
            ):
                display_df = innings_batting[
                    [
                        "player",
                        "runs_scored",
                        "balls_faced",
                        "fours",
                        "sixes",
                        "strike_rate",
                        "is_out",
                    ]
                ].copy()

                display_df.columns = [
                    "Batter",
                    "Runs",
                    "Balls",
                    "4s",
                    "6s",
                    "Strike Rate",
                    "Dismissed",
                ]

                display_df["Dismissed"] = display_df[
                    "Dismissed"
                ].map({1: "Yes", 0: "No"})

                st.dataframe(
                    display_df,
                    hide_index=True,
                    use_container_width=True,
                )
    else:
        st.info("No batting figures are available.")

    # Bowling scorecard
    st.markdown("### Bowling")

    if not bowling_df.empty:
        for innings_number in sorted(
            bowling_df["innings_number"].unique()
        ):
            innings_bowling = bowling_df[
                bowling_df["innings_number"] == innings_number
            ]

            with st.expander(
                f"Bowling figures — Innings {innings_number}",
                expanded=True,
            ):
                display_df = innings_bowling[
                    [
                        "team_name",
                        "bowler",
                        "overs_bowled",
                        "runs_conceded",
                        "wickets_taken",
                        "economy_rate",
                    ]
                ].copy()

                display_df["overs_bowled"] = display_df[
                    "overs_bowled"
                ].map(format_cricket_overs)

                display_df.columns = [
                    "Team",
                    "Bowler",
                    "Overs",
                    "Runs",
                    "Wickets",
                    "Economy",
                ]

                st.dataframe(
                    display_df,
                    hide_index=True,
                    use_container_width=True,
                )
    else:
        st.info("No bowling figures are available.")

    # Partnerships
    st.markdown("### Partnerships")

    if not partnerships_df.empty:
        partnerships_df["Batter Pair"] = (
            partnerships_df["batter1_name"].fillna("Unknown")
            + " & "
            + partnerships_df["batter2_name"].fillna("Unknown")
        )

        display_df = partnerships_df[
            [
                "innings_number",
                "partnership_number",
                "Batter Pair",
                "runs",
                "balls",
            ]
        ].copy()

        display_df.columns = [
            "Innings",
            "Partnership",
            "Batters",
            "Runs",
            "Balls",
        ]

        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No partnership data is available.")


# ---------- Refresh and live match list ----------

col1, col2 = st.columns([5, 1])

with col2:
    refresh = st.button("🔄 Refresh", use_container_width=True)

if refresh:
    st.cache_data.clear()
    st.rerun()


try:
    with st.spinner("Fetching cricket matches..."):
        matches = load_matches()

    if not matches:
        st.info(
            "No matches were returned by the API right now. "
            "Please refresh later."
        )
        matches = []

    if matches:
        # Save current API match metadata so newly selected matches
        # can later be imported into the database.
        try:
            save_matches(matches)
        except Exception as save_error:
            st.warning(
                "Live matches loaded, but match metadata could not "
                f"be saved: {save_error}"
            )

        search = st.text_input(
            "🔎 Search by team or series",
            placeholder="e.g. India",
        )

        all_formats = sorted(
            {
                str(m.get("format") or "Unknown")
                for m in matches
            }
        )

        selected_format = st.selectbox(
            "Filter by match format",
            ["All Formats"] + all_formats,
        )

        filtered_matches = matches

        if search:
            term = search.lower()
            filtered_matches = [
                m for m in filtered_matches
                if term in str(m.get("team1", "")).lower()
                or term in str(m.get("team2", "")).lower()
                or term in str(m.get("series", "")).lower()
            ]

        if selected_format != "All Formats":
            filtered_matches = [
                m for m in filtered_matches
                if str(m.get("format") or "Unknown")
                == selected_format
            ]

        live_matches = [
            m for m in filtered_matches
            if "progress" in str(m.get("state", "")).lower()
        ]

        completed_matches = [
            m for m in filtered_matches
            if str(m.get("state", "")).lower() == "complete"
        ]

        col1, col2, col3 = st.columns(3)
        col1.metric("Matches Found", len(filtered_matches))
        col2.metric("In Progress", len(live_matches))
        col3.metric("Completed", len(completed_matches))

        st.divider()

        def display_match(match):
            team1 = match.get("team1") or "Team 1"
            team2 = match.get("team2") or "Team 2"
            series = match.get("series") or "Cricket Series"
            description = match.get("match") or "Match"
            match_format = match.get("format") or "Unknown"
            status = (
                match.get("status")
                or match.get("state")
                or "Status unavailable"
            )
            venue = match.get("venue") or "Venue unavailable"
            city = match.get("city") or ""

            with st.container(border=True):
                st.markdown(f"**{series}**")
                st.caption(f"{description} · {match_format}")

                left, middle, right = st.columns([2, 1, 2])

                with left:
                    st.subheader(team1)
                    score1 = match.get("team1_score") or {}

                    if score1:
                        for score in score1.values():
                            if isinstance(score, dict):
                                runs = score.get("runs", 0)
                                wickets = score.get("wickets", 0)
                                overs = score.get("overs", "")
                                st.markdown(f"### {runs}/{wickets}")
                                if overs != "":
                                    st.caption(f"Overs: {overs}")
                    else:
                        st.caption("Score not available")

                with middle:
                    st.markdown(
                        "<div style='text-align:center; "
                        "padding-top:25px;'>VS</div>",
                        unsafe_allow_html=True,
                    )

                with right:
                    st.subheader(team2)
                    score2 = match.get("team2_score") or {}

                    if score2:
                        for score in score2.values():
                            if isinstance(score, dict):
                                runs = score.get("runs", 0)
                                wickets = score.get("wickets", 0)
                                overs = score.get("overs", "")
                                st.markdown(f"### {runs}/{wickets}")
                                if overs != "":
                                    st.caption(f"Overs: {overs}")
                    else:
                        st.caption("Score not available")

                st.info(f"📢 {status}")
                location = f"{venue}, {city}" if city else venue
                st.caption(f"📍 {location}")

        live_tab, all_tab = st.tabs(
            ["🔴 In Progress", "🏏 All Matches"]
        )

        with live_tab:
            if live_matches:
                for match in live_matches:
                    display_match(match)
            else:
                st.info("No matches are currently marked as in progress.")

        with all_tab:
            if filtered_matches:
                for match in filtered_matches:
                    display_match(match)
            else:
                st.warning("No matches match your selected filters.")

    # ---------- Saved detailed scorecards ----------

    st.divider()
    st.header("📋 Detailed Scorecards")
    st.caption(
        "Choose a match whose scorecard has already been imported "
        "into the local database."
    )

    saved_scorecards = load_saved_scorecards()

    if saved_scorecards:
        options = {
            (
                f'{item["team1"] or "Team 1"} vs '
                f'{item["team2"] or "Team 2"} — '
                f'{item["match_description"] or "Match"} '
                f'({item["external_match_id"]})'
            ): item["external_match_id"]
            for item in saved_scorecards
        }

        selected_label = st.selectbox(
            "Select a saved scorecard",
            list(options.keys()),
        )

        if selected_label:
            display_scorecard(options[selected_label])
    else:
        st.info(
            "No detailed scorecards have been imported yet. "
            "Import a scorecard first to view innings and player figures."
        )



except Exception as error:
    error_text = str(error)

    if "429" in error_text or "Too Many Requests" in error_text:
        st.warning("The Cricbuzz API rate limit has been reached.")
        st.info(
            "Live scores are temporarily unavailable. "
            "Showing scorecards already saved in the local database below."
        )
    else:
        st.error("Unable to load live matches from the Cricbuzz API.")
        st.caption(
            "The saved scorecards may still be available in your local database."
        )

    with st.expander("Technical details"):
        st.code(error_text)

    # Show locally saved scorecards even if the API request fails.
    st.divider()
    st.header("📋 Saved Scorecards")
    st.caption("These are previously saved records, not live scores.")

    try:
        saved_scorecards = load_saved_scorecards()

        if saved_scorecards:
            options = {
                (
                    f'{item["team1"] or "Team 1"} vs '
                    f'{item["team2"] or "Team 2"} — '
                    f'{item["match_description"] or "Match"} '
                    f'({item["external_match_id"]})'
                ): item["external_match_id"]
                for item in saved_scorecards
            }

            selected_label = st.selectbox(
                "Select a saved scorecard",
                list(options.keys()),
            )

            if selected_label:
                display_scorecard(options[selected_label])
        else:
            st.info("No saved scorecards are available yet.")

    except Exception as saved_error:
        st.error("Could not load saved scorecards from the database.")
        with st.expander("Database error details"):
            st.code(str(saved_error))
