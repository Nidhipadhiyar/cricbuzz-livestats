
import streamlit as st
import pandas as pd

from database.db_connection import get_connection, initialize_database

st.set_page_config(
    page_title="CRUD Management | Cricbuzz LiveStats",
    page_icon="🛠️",
    layout="wide",
)

initialize_database()

st.title("🛠️ Cricket Database Management")
st.caption("Create, view, update, and delete player and match-statistics records.")

st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #10251f;
    border: 1px solid #285344;
    padding: 14px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


def load_players():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT p.player_id, p.full_name, t.team_name,
                   p.playing_role, p.batting_style, p.bowling_style
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.team_id
            ORDER BY p.full_name
            """,
            conn,
        )


def load_teams():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT team_id, team_name FROM teams ORDER BY team_name",
            conn,
        )


def load_matches():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT match_id, match_description, match_type, status
            FROM matches
            ORDER BY match_id DESC
            """,
            conn,
        )


def load_stats():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT ps.stat_id, p.full_name AS player, t.team_name AS team,
                   m.match_description AS match_name,
                   ps.innings_number, ps.runs_scored, ps.balls_faced,
                   ps.fours, ps.sixes, ps.wickets_taken,
                   ps.runs_conceded, ps.overs_bowled,
                   ps.catches, ps.stumpings
            FROM player_match_stats ps
            JOIN players p ON p.player_id = ps.player_id
            LEFT JOIN teams t ON t.team_id = ps.team_id
            JOIN matches m ON m.match_id = ps.match_id
            ORDER BY ps.stat_id DESC
            """,
            conn,
        )


players_df = load_players()
teams_df = load_teams()
matches_df = load_matches()
stats_df = load_stats()

c1, c2, c3 = st.columns(3)
c1.metric("Players", len(players_df))
c2.metric("Matches", len(matches_df))
c3.metric("Player Stat Records", len(stats_df))

st.divider()

player_tab, stats_tab = st.tabs(
    ["👤 Manage Players", "📈 Manage Match Statistics"]
)

# ---------------- PLAYER CRUD ----------------
with player_tab:
    st.subheader("Player Records")

    view_tab, add_tab, edit_tab, delete_tab = st.tabs(
        ["View", "Add Player", "Edit Player", "Delete Player"]
    )

    with view_tab:
        st.dataframe(
            players_df,
            use_container_width=True,
            hide_index=True,
        )

    with add_tab:
        st.markdown("#### Add a new player")

        with st.form("add_player_form", clear_on_submit=True):
            name = st.text_input("Full name")
            role = st.selectbox(
                "Playing role",
                ["Batsman", "Bowler", "All-rounder", "Wicket-keeper"],
            )
            batting = st.selectbox(
                "Batting style",
                ["Right-hand", "Left-hand", "Unknown"],
            )
            bowling = st.text_input("Bowling style", value="Unknown")

            team_options = {"No team assigned": None}
            team_options.update({
                row["team_name"]: int(row["team_id"])
                for _, row in teams_df.iterrows()
            })
            selected_team = st.selectbox(
                "Team",
                list(team_options.keys()),
            )

            new_team = st.text_input(
                "Or enter a new team/country name (optional)"
            )

            submitted = st.form_submit_button(
                "➕ Add Player",
                use_container_width=True,
            )

            if submitted:
                if not name.strip():
                    st.error("Please enter the player's name.")
                else:
                    try:
                        with get_connection() as conn:
                            team_id = team_options[selected_team]

                            if new_team.strip():
                                conn.execute(
                                    """
                                    INSERT OR IGNORE INTO teams
                                        (team_name, country)
                                    VALUES (?, ?)
                                    """,
                                    (new_team.strip(), new_team.strip()),
                                )
                                row = conn.execute(
                                    "SELECT team_id FROM teams WHERE team_name = ?",
                                    (new_team.strip(),),
                                ).fetchone()
                                team_id = row["team_id"]

                            conn.execute(
                                """
                                INSERT INTO players
                                    (full_name, team_id, playing_role,
                                     batting_style, bowling_style)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    name.strip(), team_id, role,
                                    batting, bowling.strip(),
                                ),
                            )

                        st.success(f"Added {name.strip()} successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add player: {e}")

    with edit_tab:
        if players_df.empty:
            st.info("No players available to edit.")
        else:
            player_map = {
                f'{row["full_name"]} (ID {row["player_id"]})':
                int(row["player_id"])
                for _, row in players_df.iterrows()
            }

            selected_label = st.selectbox(
                "Choose player to edit",
                list(player_map.keys()),
                key="edit_player_select",
            )
            player_id = player_map[selected_label]
            current = players_df[
                players_df["player_id"] == player_id
            ].iloc[0]

            team_options = {"No team assigned": None}
            team_options.update({
                row["team_name"]: int(row["team_id"])
                for _, row in teams_df.iterrows()
            })

            current_team = current["team_name"]
            team_names = list(team_options.keys())
            default_team_index = (
                team_names.index(current_team)
                if pd.notna(current_team) and current_team in team_names
                else 0
            )

            with st.form("edit_player_form"):
                edited_name = st.text_input(
                    "Full name", value=current["full_name"]
                )
                role_options = [
                    "Batsman", "Bowler", "All-rounder", "Wicket-keeper"
                ]
                current_role = current["playing_role"]
                role_index = (
                    role_options.index(current_role)
                    if current_role in role_options else 0
                )
                edited_role = st.selectbox(
                    "Playing role", role_options, index=role_index
                )

                batting_options = ["Right-hand", "Left-hand", "Unknown"]
                current_batting = current["batting_style"]
                batting_index = (
                    batting_options.index(current_batting)
                    if current_batting in batting_options else 2
                )
                edited_batting = st.selectbox(
                    "Batting style", batting_options,
                    index=batting_index,
                )
                edited_bowling = st.text_input(
                    "Bowling style",
                    value=(
                        current["bowling_style"]
                        if pd.notna(current["bowling_style"]) else ""
                    ),
                )
                edited_team = st.selectbox(
                    "Team",
                    team_names,
                    index=default_team_index,
                )

                save_changes = st.form_submit_button(
                    "💾 Save Changes",
                    use_container_width=True,
                )

                if save_changes:
                    if not edited_name.strip():
                        st.error("Player name cannot be empty.")
                    else:
                        try:
                            with get_connection() as conn:
                                conn.execute(
                                    """
                                    UPDATE players
                                    SET full_name = ?, team_id = ?,
                                        playing_role = ?, batting_style = ?,
                                        bowling_style = ?
                                    WHERE player_id = ?
                                    """,
                                    (
                                        edited_name.strip(),
                                        team_options[edited_team],
                                        edited_role,
                                        edited_batting,
                                        edited_bowling.strip(),
                                        player_id,
                                    ),
                                )
                            st.success("Player updated successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not update player: {e}")

    with delete_tab:
        if players_df.empty:
            st.info("No players available to delete.")
        else:
            delete_label = st.selectbox(
                "Choose player to delete",
                list(player_map.keys()),
                key="delete_player_select",
            )
            delete_id = player_map[delete_label]

            linked_stats = int(
                stats_df[
                    stats_df["player"] ==
                    players_df.loc[
                        players_df["player_id"] == delete_id,
                        "full_name"
                    ].iloc[0]
                ].shape[0]
            )

            if linked_stats:
                st.warning(
                    f"This player has {linked_stats} statistics record(s). "
                    "Delete those records first in the Match Statistics tab."
                )

            confirm_delete = st.checkbox(
                "I confirm I want to delete this player.",
                key="confirm_delete_player",
            )

            if st.button(
                "🗑️ Delete Player",
                disabled=not confirm_delete or linked_stats > 0,
            ):
                try:
                    with get_connection() as conn:
                        conn.execute(
                            "DELETE FROM players WHERE player_id = ?",
                            (delete_id,),
                        )
                    st.success("Player deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete player: {e}")


# ---------------- PLAYER MATCH STATISTICS ----------------
with stats_tab:
    st.subheader("Player Match Statistics")

    view_stats_tab, add_stats_tab, delete_stats_tab = st.tabs(
        ["View Records", "Add Statistics", "Delete Statistics"]
    )

    with view_stats_tab:
        st.dataframe(
            stats_df,
            use_container_width=True,
            hide_index=True,
        )

    with add_stats_tab:
        if players_df.empty or matches_df.empty:
            st.warning(
                "You need at least one player and one match in the database "
                "before adding player-match statistics. Add a player here "
                "and ensure match records exist from the Live Matches page."
            )
        else:
            player_options = {
                f'{row["full_name"]} (ID {row["player_id"]})':
                int(row["player_id"])
                for _, row in players_df.iterrows()
            }
            match_options = {
                f'{row["match_description"] or "Match"} '
                f'(ID {row["match_id"]})':
                int(row["match_id"])
                for _, row in matches_df.iterrows()
            }

            team_options = {"No team assigned": None}
            team_options.update({
                row["team_name"]: int(row["team_id"])
                for _, row in teams_df.iterrows()
            })

            with st.form("add_stats_form", clear_on_submit=True):
                chosen_player = st.selectbox(
                    "Player", list(player_options.keys())
                )
                chosen_match = st.selectbox(
                    "Match", list(match_options.keys())
                )
                chosen_team = st.selectbox(
                    "Team", list(team_options.keys())
                )
                innings = st.number_input(
                    "Innings number", min_value=1, max_value=4, value=1
                )
                runs = st.number_input(
                    "Runs scored", min_value=0, value=0
                )
                balls = st.number_input(
                    "Balls faced", min_value=0, value=0
                )
                fours = st.number_input(
                    "Fours", min_value=0, value=0
                )
                sixes = st.number_input(
                    "Sixes", min_value=0, value=0
                )
                wickets = st.number_input(
                    "Wickets taken", min_value=0, value=0
                )
                runs_conceded = st.number_input(
                    "Runs conceded", min_value=0, value=0
                )
                overs = st.number_input(
                    "Overs bowled", min_value=0.0, value=0.0, step=0.1
                )
                catches = st.number_input(
                    "Catches", min_value=0, value=0
                )
                stumpings = st.number_input(
                    "Stumpings", min_value=0, value=0
                )
                batting_position = st.number_input(
                    "Batting position (0 = unknown)",
                    min_value=0, max_value=11, value=0,
                )

                add_stats = st.form_submit_button(
                    "➕ Save Match Statistics",
                    use_container_width=True,
                )

                if add_stats:
                    try:
                        with get_connection() as conn:
                            conn.execute(
                                """
                                INSERT INTO player_match_stats (
                                    match_id, player_id, team_id,
                                    runs_scored, balls_faced, fours, sixes,
                                    wickets_taken, runs_conceded,
                                    overs_bowled, catches, stumpings,
                                    batting_position, innings_number
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    match_options[chosen_match],
                                    player_options[chosen_player],
                                    team_options[chosen_team],
                                    runs, balls, fours, sixes,
                                    wickets, runs_conceded, overs,
                                    catches, stumpings,
                                    batting_position or None, innings,
                                ),
                            )
                        st.success("Match statistics saved.")
                        st.rerun()
                    except Exception as e:
                        st.error(
                            "Could not save statistics. Check whether this "
                            "player already has a record for this match and "
                            "innings.\n\n"
                            f"Details: {e}"
                        )

    with delete_stats_tab:
        if stats_df.empty:
            st.info("There are no player statistics to delete.")
        else:
            stat_options = {
                f'ID {row["stat_id"]}: {row["player"]} — '
                f'{row["match_name"]} — Innings {row["innings_number"]}':
                int(row["stat_id"])
                for _, row in stats_df.iterrows()
            }

            selected_stat = st.selectbox(
                "Choose statistics record",
                list(stat_options.keys()),
            )
            confirm_stat_delete = st.checkbox(
                "I confirm deletion of this statistics record.",
                key="confirm_delete_stat",
            )

            if st.button(
                "🗑️ Delete Statistics",
                disabled=not confirm_stat_delete,
            ):
                try:
                    with get_connection() as conn:
                        conn.execute(
                            "DELETE FROM player_match_stats WHERE stat_id = ?",
                            (stat_options[selected_stat],),
                        )
                    st.success("Statistics record deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete statistics: {e}")
