from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from database.analytics import get_dashboard_summary
from database.db_connection import get_connection, initialize_database
from services.cricket_api import extract_matches, get_live_matches


st.set_page_config(
    page_title="Cricbuzz LiveStats | Home",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()


def find_page_path(pattern):
    """Find a multipage app file without hardcoding its emoji prefix."""
    matches = list(Path("pages").glob(pattern))
    return str(matches[0]) if len(matches) == 1 else None


# ---------- Styling ----------
st.markdown(
    """
    <style>
    .hero {
        padding: 28px;
        border-radius: 16px;
        background: linear-gradient(120deg, #10251f, #1b4938);
        border: 1px solid #285344;
        margin-bottom: 20px;
    }
    .hero h1 { margin-bottom: 8px; }
    .hero p { color: #d4e8dc; font-size: 17px; }
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

# ---------- Header ----------
st.markdown(
    """
    <div class="hero">
        <h1>Cricbuzz LiveStats</h1>
        <p>Real-Time Cricket Insights &amp; SQL-Based Analytics</p>
        Explore live cricket, career statistics, and data-driven insights
        in one interactive dashboard.
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Database summary ----------
try:
    summary = get_dashboard_summary()

    with get_connection() as conn:
        total_players = conn.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0]
        total_player_stats = conn.execute(
            "SELECT COUNT(*) FROM player_match_stats"
        ).fetchone()[0]

    st.subheader("Project Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Saved Matches", f'{summary["total_matches"]:,}')
    c2.metric("Saved Players", f"{total_players:,}")
    c3.metric("Player Stat Records", f"{total_player_stats:,}")
    c4.metric("Match Formats", len(summary["format_counts"]))

    left, right = st.columns(2)

    with left:
        st.markdown("#### Matches by Format")
        format_df = pd.DataFrame(summary["format_counts"])
        if not format_df.empty:
            fig = px.bar(
                format_df,
                x="format",
                y="total",
                color="format",
                title="Saved Matches by Format",
            )
            fig.update_layout(
                template="plotly_dark",
                showlegend=False,
                xaxis_title="Format",
                yaxis_title="Matches",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No match-format data is saved yet.")

    with right:
        st.markdown("#### Matches by Status")
        status_df = pd.DataFrame(summary["status_counts"])
        if not status_df.empty:
            fig = px.pie(
                status_df,
                names="status",
                values="total",
                title="Saved Match Status",
                hole=0.45,
            )
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No match-status data is saved yet.")

except Exception as error:
    st.warning("Database summary is temporarily unavailable.")
    with st.expander("Technical details"):
        st.code(str(error))

st.divider()

# ---------- Live match highlights ----------
st.subheader("Live Cricket Highlights")
st.caption("Match information fetched from the Cricbuzz API.")

if st.button("Refresh Live Matches"):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("Fetching live matches..."):
        live_data = get_live_matches()
        live_matches = extract_matches(live_data)

    if live_matches:
        match_df = pd.DataFrame(live_matches)
        display_columns = [
            column
            for column in [
                "team1", "team2", "format", "match",
                "series", "venue", "status",
            ]
            if column in match_df.columns
        ]
        st.dataframe(
            match_df[display_columns],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "Cricbuzz returned no matches in the live endpoint. "
            "Check the Live Matches page for more match categories."
        )
except Exception as error:
    st.info(
        "Live match data could not be fetched right now. "
        "Your saved database analytics are still available above. "
        "Please try refreshing or visit the Live Matches page."
    )
    with st.expander("Technical details"):
        st.code(str(error))

st.divider()

# ---------- Navigation guide ----------
st.subheader("Explore the Platform")

navigation = [
    (
        "*Live_Matches.py",
        "Live Matches",
        "View live scores, match status, series, and venues.",
        "Explore Live Matches",
    ),
    (
        "*SQL_Analytics.py",
        "SQL Analytics",
        "Explore cricket data through SQL queries and analysis.",
        "Explore SQL Analytics",
    ),
    (
        "*Top_Player_Stats.py",
        "Top Player Stats",
        "Search real players and explore career batting and bowling statistics.",
        "Explore Player Stats",
    ),
    (
        "*CRUD_Management.py",
        "CRUD Management",
        "Create, view, update, and delete saved database records.",
        "Manage Records",
    ),
]

nav_left, nav_right = st.columns(2)

for index, (pattern, title, description, link_label) in enumerate(navigation):
    target_column = nav_left if index % 2 == 0 else nav_right
    with target_column:
        with st.container(border=True):
            st.markdown(f"### {title}")
            st.write(description)
            page_path = find_page_path(pattern)
            if page_path:
                st.page_link(page_path, label=link_label)
            else:
                st.warning(
                    f"Could not uniquely locate the page matching {pattern!r} "
                    "inside the pages folder."
                )

st.divider()

st.subheader("Technology Stack")
st.markdown(
    """
    - **Python and Streamlit:** application logic and interactive interface
    - **REST API and JSON:** retrieve cricket information from Cricbuzz
    - **SQLite and SQL:** store and analyze structured cricket records
    - **Pandas:** organize and process data
    - **Plotly:** interactive data visualizations
    """
)

st.caption("Cricbuzz LiveStats | Academic Sports Analytics Project")
