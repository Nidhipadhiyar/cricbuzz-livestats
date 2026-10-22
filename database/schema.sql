
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL UNIQUE,
    country TEXT
);

CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    team_id INTEGER,
    playing_role TEXT,
    batting_style TEXT,
    bowling_style TEXT,
    external_player_id TEXT UNIQUE,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_name TEXT NOT NULL,
    city TEXT,
    country TEXT,
    capacity INTEGER
);

CREATE TABLE IF NOT EXISTS series (
    series_id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_name TEXT NOT NULL,
    host_country TEXT,
    match_type TEXT,
    start_date TEXT,
    planned_matches INTEGER
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_match_id TEXT UNIQUE,
    series_id INTEGER,
    match_description TEXT,
    match_type TEXT,
    team1_id INTEGER,
    team2_id INTEGER,
    venue_id INTEGER,
    match_date TEXT,
    status TEXT,
    winner_team_id INTEGER,
    win_margin INTEGER,
    win_type TEXT,
    toss_winner_team_id INTEGER,
    toss_decision TEXT,
    FOREIGN KEY (series_id) REFERENCES series(series_id),
    FOREIGN KEY (team1_id) REFERENCES teams(team_id),
    FOREIGN KEY (team2_id) REFERENCES teams(team_id),
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id),
    FOREIGN KEY (winner_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (toss_winner_team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS player_match_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER,
    runs_scored INTEGER DEFAULT 0,
    balls_faced INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    wickets_taken INTEGER DEFAULT 0,
    runs_conceded INTEGER DEFAULT 0,
    overs_bowled REAL DEFAULT 0,
    catches INTEGER DEFAULT 0,
    stumpings INTEGER DEFAULT 0,
    batting_position INTEGER,
    innings_number INTEGER DEFAULT 1,
    batting_average REAL,
    strike_rate REAL,
    economy_rate REAL,
    is_out INTEGER DEFAULT 0,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE (match_id, player_id, innings_number)
);

CREATE TABLE IF NOT EXISTS match_innings (
    innings_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    external_innings_id TEXT,
    innings_number INTEGER NOT NULL,
    team_id INTEGER,
    total_runs INTEGER DEFAULT 0,
    wickets_lost INTEGER DEFAULT 0,
    overs REAL DEFAULT 0,
    run_rate REAL,
    extras INTEGER DEFAULT 0,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE (match_id, innings_number)
);

CREATE TABLE IF NOT EXISTS partnerships (
    partnership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    innings_number INTEGER NOT NULL,
    partnership_number INTEGER NOT NULL,
    batter1_external_id TEXT,
    batter1_name TEXT,
    batter2_external_id TEXT,
    batter2_name TEXT,
    runs INTEGER DEFAULT 0,
    balls INTEGER DEFAULT 0,
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    UNIQUE (match_id, innings_number, partnership_number)
);

CREATE INDEX IF NOT EXISTS idx_matches_date
ON matches(match_date);

CREATE INDEX IF NOT EXISTS idx_matches_type
ON matches(match_type);

CREATE INDEX IF NOT EXISTS idx_player_stats_player
ON player_match_stats(player_id);

CREATE INDEX IF NOT EXISTS idx_player_stats_match
ON player_match_stats(match_id);

CREATE INDEX IF NOT EXISTS idx_innings_match
ON match_innings(match_id);

CREATE INDEX IF NOT EXISTS idx_partnerships_match
ON partnerships(match_id);
