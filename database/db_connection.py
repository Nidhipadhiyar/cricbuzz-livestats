
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "cricket.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SAMPLE_DATA_PATH = BASE_DIR / "sample_data.sql"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _add_missing_columns(connection, table_name, columns):
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
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.executescript(schema)

        _add_missing_columns(
            connection,
            "players",
            {"external_player_id": "TEXT"},
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

        match_count = connection.execute(
            "SELECT COUNT(*) FROM matches"
        ).fetchone()[0]

        print(f"DEBUG: Database path: {DB_PATH}")
        print(f"DEBUG: Matches before sample import: {match_count}")
        print(f"DEBUG: Sample SQL exists: {SAMPLE_DATA_PATH.exists()}")

        if match_count == 0 and SAMPLE_DATA_PATH.exists():
            try:
                sample_sql = SAMPLE_DATA_PATH.read_text(encoding="utf-8")
                connection.executescript(sample_sql)
                imported_count = connection.execute(
                    "SELECT COUNT(*) FROM matches"
                ).fetchone()[0]
                print(f"DEBUG: Matches after sample import: {imported_count}")
            except Exception as error:
                print(f"DEBUG: Sample import failed: {type(error).__name__}: {error}")
                raise


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")
    print(f"Database location: {DB_PATH}")
