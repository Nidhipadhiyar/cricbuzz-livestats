
import streamlit as st
import pandas as pd
import plotly.express as px

from database.db_connection import get_connection
from services.cricket_api import (
    search_players,
    get_player_batting_stats,
    get_player_bowling_stats,
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Top Player Stats | Cricbuzz LiveStats",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 Top Player Statistics")
st.caption(
    "Explore live career statistics from Cricbuzz and "
    "analyze match performances saved in your local database."
)

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background: #10251f;
        border: 1px solid #285344;
        padding: 16px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# API DATA HELPERS
# --------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def find_players(query):
    return search_players(query)


@st.cache_data(ttl=300, show_spinner=False)
def load_batting(player_id):
    return get_player_batting_stats(player_id)


@st.cache_data(ttl=300, show_spinner=False)
def load_bowling(player_id):
    return get_player_bowling_stats(player_id)


def stats_to_dataframe(data):
    """Convert Cricbuzz career-statistics JSON into a readable table."""
    if not isinstance(data, dict):
        return pd.DataFrame()

    headers = data.get("headers", [])
    rows = []

    for item in data.get("values", []):
        values = item.get("values", [])

        if not values:
            continue

        row = {"Statistic": values[0]}

        for index, value in enumerate(values[1:], start=1):
            column = (
                headers[index]
                if index < len(headers)
                else f"Format {index}"
            )
            row[column] = value

        rows.append(row)

    return pd.DataFrame(rows)


def get_stat_value(df, statistic, format_name):
    """Return one statistic for the selected format."""
    if df.empty or "Statistic" not in df.columns:
        return "—"

    matching_rows = df.loc[df["Statistic"] == statistic]

    if matching_rows.empty or format_name not in matching_rows.columns:
        return "—"

    value = matching_rows.iloc[0][format_name]

    if pd.isna(value) or str(value).strip() == "":
        return "—"

    return str(value)


# --------------------------------------------------
# LIVE PLAYER SEARCH
# --------------------------------------------------

st.header("🔎 Search Real Players")
st.caption(
    "Search Cricbuzz to view career batting and bowling statistics "
    "across Test, ODI, T20, and IPL."
)

with st.form("player_search_form"):
    query = st.text_input(
        "Player name",
        placeholder="For example: Virat Kohli",
    )

    search_clicked = st.form_submit_button(
        "Search Players",
        type="primary",
    )

if search_clicked:
    if not query.strip():
        st.warning("Enter a player's name first.")
        st.session_state.pop("live_player_results", None)
    else:
        try:
            with st.spinner("Searching Cricbuzz..."):
                result = find_players(query.strip())

            players_found = result.get("player", [])
            st.session_state["live_player_results"] = players_found

            if not players_found:
                st.info("No players found. Try another name.")

        except Exception as error:
            st.error("Could not search Cricbuzz.")
            with st.expander("Technical details"):
                st.code(str(error))

players = st.session_state.get("live_player_results", [])

if players:
    player_options = {
        (
            f"{player.get('name', 'Unknown player')} — "
            f"{player.get('teamName', 'Unknown team')} "
            f"(ID: {player.get('id', '')})"
        ): player
        for player in players
        if player.get("id")
    }

    if player_options:
        selected_label = st.selectbox(
            "Select a player",
            list(player_options.keys()),
            key="selected_live_player",
        )

        selected_player = player_options[selected_label]
        player_id = str(selected_player["id"])

        st.subheader(f"🏏 {selected_player.get('name', 'Player')}")
        st.caption(
            f"Team: {selected_player.get('teamName', 'Unknown')} "
            f"| Player ID: {player_id}"
        )

        batting_tab, bowling_tab = st.tabs(
            ["🏏 Career Batting", "🎯 Career Bowling"]
        )

        # ------------------------------------------
        # CAREER BATTING
        # ------------------------------------------

        with batting_tab:
            try:
                with st.spinner("Loading batting statistics..."):
                    batting_data = load_batting(player_id)

                batting_df = stats_to_dataframe(batting_data)

                formats = ["Test", "ODI", "T20", "IPL"]

                chosen_format = st.selectbox(
                    "Batting format",
                    formats,
                    key=f"batting_format_{player_id}",
                )

                m1, m2, m3, m4 = st.columns(4)

                m1.metric(
                    "Matches",
                    get_stat_value(
                        batting_df, "Matches", chosen_format
                    ),
                )

                m2.metric(
                    "Career Runs",
                    get_stat_value(
                        batting_df, "Runs", chosen_format
                    ),
                )

                m3.metric(
                    "Batting Average",
                    get_stat_value(
                        batting_df, "Average", chosen_format
                    ),
                )

                m4.metric(
                    "Strike Rate",
                    get_stat_value(
                        batting_df, "SR", chosen_format
                    ),
                )

                st.subheader(f"{chosen_format} Batting Record")

                if (
                    not batting_df.empty
                    and chosen_format in batting_df.columns
                ):
                    display_batting = batting_df[
                        ["Statistic", chosen_format]
                    ].rename(
                        columns={chosen_format: "Career Value"}
                    )

                    st.dataframe(
                        display_batting,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info(
                        "No batting statistics are available "
                        "for this format."
                    )

            except Exception as error:
                st.error("Could not load batting statistics.")
                with st.expander("Technical details"):
                    st.code(str(error))

        # ------------------------------------------
        # CAREER BOWLING
        # ------------------------------------------

        with bowling_tab:
            try:
                with st.spinner("Loading bowling statistics..."):
                    bowling_data = load_bowling(player_id)

                bowling_df = stats_to_dataframe(bowling_data)

                chosen_bowling_format = st.selectbox(
                    "Bowling format",
                    ["Test", "ODI", "T20", "IPL"],
                    key=f"bowling_format_{player_id}",
                )

                b1, b2, b3, b4 = st.columns(4)

                b1.metric(
                    "Matches",
                    get_stat_value(
                        bowling_df, "Matches", chosen_bowling_format
                    ),
                )

                b2.metric(
                    "Wickets",
                    get_stat_value(
                        bowling_df, "Wickets", chosen_bowling_format
                    ),
                )

                b3.metric(
                    "Economy",
                    get_stat_value(
                        bowling_df, "Eco", chosen_bowling_format
                    ),
                )

                b4.metric(
                    "Bowling Average",
                    get_stat_value(
                        bowling_df, "Avg", chosen_bowling_format
                    ),
                )

                st.subheader(
                    f"{chosen_bowling_format} Bowling Record"
                )

                if (
                    not bowling_df.empty
                    and chosen_bowling_format in bowling_df.columns
                ):
                    display_bowling = bowling_df[
                        ["Statistic", chosen_bowling_format]
                    ].rename(
                        columns={
                            chosen_bowling_format: "Career Value"
                        }
                    )

                    st.dataframe(
                        display_bowling,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info(
                        "No bowling statistics are available "
                        "for this format."
                    )

            except Exception as error:
                st.error("Could not load bowling statistics.")
                with st.expander("Technical details"):
                    st.code(str(error))

st.divider()


# --------------------------------------------------
# LOCAL DATABASE ANALYTICS
# --------------------------------------------------

st.header("📊 Saved Database Analytics")

st.caption(
    "The leaderboards below use match performances stored in your "
    "SQLite database. They are not complete career leaderboards "
    "unless all relevant match data has been imported."
)


@st.cache_data(ttl=30, show_spinner=False)
def load_player_stats():
    query = """
        SELECT
            p.player_id,
            p.full_name AS player,
            t.team_name AS team,
            p.playing_role AS role,

            COUNT(DISTINCT ps.match_id) AS matches,

            COALESCE(SUM(ps.runs_scored), 0) AS runs,
            COALESCE(MAX(ps.runs_scored), 0) AS highest_score,

            COALESCE(SUM(ps.balls_faced), 0) AS balls_faced,
            COALESCE(SUM(ps.fours), 0) AS fours,
            COALESCE(SUM(ps.sixes), 0) AS sixes,

            COALESCE(SUM(ps.wickets_taken), 0) AS wickets,
            COALESCE(SUM(ps.runs_conceded), 0) AS runs_conceded,

            COALESCE(SUM(ps.catches), 0) AS catches,
            COALESCE(SUM(ps.stumpings), 0) AS stumpings

        FROM players p

        LEFT JOIN teams t
            ON p.team_id = t.team_id

        LEFT JOIN player_match_stats ps
            ON p.player_id = ps.player_id

        GROUP BY
            p.player_id,
            p.full_name,
            t.team_name,
            p.playing_role

        ORDER BY runs DESC
    """

    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


try:
    df = load_player_stats()

    if df.empty:
        st.info(
            "No players are currently saved in the database. "
            "Use the live player search above to explore career "
            "statistics, or add records through CRUD Management."
        )

    else:
        # ------------------------------------------
        # DATABASE SUMMARY
        # ------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Saved Players", len(df))
        c2.metric("Saved Runs", f"{int(df['runs'].sum()):,}")
        c3.metric("Saved Wickets", f"{int(df['wickets'].sum()):,}")

        highest_score = int(df["highest_score"].max())

        c4.metric(
            "Highest Saved Individual Score",
            highest_score,
        )

        st.caption(
            "These summary figures represent records in the local "
            "database only. The highest score is the maximum "
            "runs_scored value recorded for one player in one "
            "saved innings."
        )

        st.divider()

        local_batting, local_highest, local_bowling, local_compare = (
            st.tabs(
                [
                    "🏏 Most Runs",
                    "⭐ Highest Individual Score",
                    "🎯 Most Wickets",
                    "📈 Compare Saved Players",
                ]
            )
        )

        # ------------------------------------------
        # MOST RUNS
        # ------------------------------------------

        with local_batting:
            batting = df[df["runs"] > 0].copy()

            if batting.empty:
                st.info(
                    "No batting performances have been saved yet."
                )

            else:
                batting["Strike Rate"] = (
                    batting["runs"]
                    / batting["balls_faced"].replace(0, float("nan"))
                ) * 100

                batting["Strike Rate"] = batting[
                    "Strike Rate"
                ].round(2)

                top_runs = batting.sort_values(
                    "runs",
                    ascending=False,
                ).head(10)

                st.subheader("Top 10 Saved Run Scorers")

                st.dataframe(
                    top_runs[
                        [
                            "player",
                            "team",
                            "role",
                            "matches",
                            "runs",
                            "highest_score",
                            "fours",
                            "sixes",
                            "Strike Rate",
                        ]
                    ].rename(
                        columns={
                            "player": "Player",
                            "team": "Team",
                            "role": "Role",
                            "matches": "Matches",
                            "runs": "Total Runs",
                            "highest_score": "Highest Individual Score",
                            "fours": "Fours",
                            "sixes": "Sixes",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                fig = px.bar(
                    top_runs.sort_values("runs"),
                    x="runs",
                    y="player",
                    orientation="h",
                    title="Top Saved Run Scorers",
                    labels={
                        "runs": "Total Runs",
                        "player": "Player",
                    },
                    color="runs",
                    color_continuous_scale=[
                        "#28745a",
                        "#7ee0a5",
                    ],
                )

                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

        # ------------------------------------------
        # HIGHEST INDIVIDUAL SCORE
        # ------------------------------------------

        with local_highest:
            score_data = df[df["highest_score"] > 0].copy()

            if score_data.empty:
                st.info(
                    "No individual batting scores have been saved yet."
                )

            else:
                top_scores = score_data.sort_values(
                    ["highest_score", "runs"],
                    ascending=[False, False],
                ).head(10)

                st.subheader(
                    "Top 10 Highest Individual Scores in Saved Data"
                )

                st.dataframe(
                    top_scores[
                        [
                            "player",
                            "team",
                            "role",
                            "matches",
                            "highest_score",
                            "runs",
                        ]
                    ].rename(
                        columns={
                            "player": "Player",
                            "team": "Team",
                            "role": "Role",
                            "matches": "Matches",
                            "highest_score": "Highest Individual Score",
                            "runs": "Total Runs",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                fig = px.bar(
                    top_scores.sort_values("highest_score"),
                    x="highest_score",
                    y="player",
                    orientation="h",
                    title="Highest Individual Scores in Saved Data",
                    labels={
                        "highest_score": "Runs in One Innings",
                        "player": "Player",
                    },
                    color="highest_score",
                    color_continuous_scale=[
                        "#7353ba",
                        "#c5a7ff",
                    ],
                )

                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

        # ------------------------------------------
        # MOST WICKETS
        # ------------------------------------------

        with local_bowling:
            bowlers = (
                df[df["wickets"] > 0]
                .sort_values("wickets", ascending=False)
                .head(10)
            )

            if bowlers.empty:
                st.info(
                    "No bowling performances have been saved yet."
                )

            else:
                st.subheader("Top 10 Saved Wicket Takers")

                st.dataframe(
                    bowlers[
                        [
                            "player",
                            "team",
                            "role",
                            "matches",
                            "wickets",
                            "runs_conceded",
                        ]
                    ].rename(
                        columns={
                            "player": "Player",
                            "team": "Team",
                            "role": "Role",
                            "matches": "Matches",
                            "wickets": "Wickets",
                            "runs_conceded": "Runs Conceded",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                fig = px.bar(
                    bowlers.sort_values("wickets"),
                    x="wickets",
                    y="player",
                    orientation="h",
                    title="Top Saved Wicket Takers",
                    labels={
                        "wickets": "Wickets",
                        "player": "Player",
                    },
                    color="wickets",
                    color_continuous_scale=[
                        "#28627a",
                        "#7bd9ee",
                    ],
                )

                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

        # ------------------------------------------
        # COMPARE PLAYERS
        # ------------------------------------------

        with local_compare:
            selected = st.multiselect(
                "Choose saved players to compare",
                sorted(df["player"].dropna().unique()),
                key="saved_player_comparison",
            )

            if selected:
                comparison = df[df["player"].isin(selected)]

                st.dataframe(
                    comparison[
                        [
                            "player",
                            "team",
                            "matches",
                            "runs",
                            "highest_score",
                            "wickets",
                            "fours",
                            "sixes",
                            "catches",
                        ]
                    ].rename(
                        columns={
                            "player": "Player",
                            "team": "Team",
                            "matches": "Matches",
                            "runs": "Total Runs",
                            "highest_score": "Highest Individual Score",
                            "wickets": "Wickets",
                            "fours": "Fours",
                            "sixes": "Sixes",
                            "catches": "Catches",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        # ------------------------------------------
        # ALL SAVED PLAYER RECORDS
        # ------------------------------------------

        with st.expander("View all saved player records"):
            st.dataframe(
                df.rename(
                    columns={
                        "player": "Player",
                        "team": "Team",
                        "role": "Role",
                        "matches": "Matches",
                        "runs": "Total Runs",
                        "highest_score": "Highest Individual Score",
                        "balls_faced": "Balls Faced",
                        "fours": "Fours",
                        "sixes": "Sixes",
                        "wickets": "Wickets",
                        "runs_conceded": "Runs Conceded",
                        "catches": "Catches",
                        "stumpings": "Stumpings",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

except Exception as error:
    st.error("Could not load saved database statistics.")

    with st.expander("Technical details"):
        st.code(str(error))
