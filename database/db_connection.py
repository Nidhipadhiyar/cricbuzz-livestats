
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "cricket.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def get_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _add_missing_columns(connection, table_name, columns):
    """Add columns that are missing from an existing table."""
    existing_columns = {
        row["name"]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }

    for column_name, column_definition in columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_definition}"
            )


def initialize_database():
    """Create tables and safely migrate an existing database."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.executescript(schema)

        _add_missing_columns(
            connection,
            "players",
            {
                "external_player_id": "TEXT",
            },
        )

        _add_missing_columns(
            connection,
            "player_match_stats",
            {
                "batting_average": "REAL",
                "strike_rate": "REAL",
                "economy_rate": "REAL",
                "is_out": "INTEGER DEFAULT 0",
            },
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_players_external_id
            ON players(external_player_id)
            """
        )


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")
    print(f"Database location: {DB_PATH}")
