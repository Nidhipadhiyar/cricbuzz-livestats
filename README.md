# Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics

Cricbuzz LiveStats is a Python-based cricket analytics application built with Streamlit, SQLite, Pandas, and Plotly. It provides cricket match information, player statistics, database management, and SQL-driven insights through an interactive dashboard.

## Features

- **Live Matches:** View available match information from the cricket API.
- **Top Player Stats:** Explore player statistics presented through the application.
- **SQL Analytics:** Run and explore 25 SQL-based analytical questions, with CSV export for query results.
- **CRUD Management:** Manage supported cricket database records through the interface.
- **SQLite Database:** Store and query cricket data locally.
- **Interactive Visualizations:** Present analytical results using Streamlit and Plotly.

## Technology Stack

- Python
- Streamlit
- SQLite
- Pandas
- Plotly
- Requests
- python-dotenv
- SQLAlchemy
- Pytest

## Project Structure

```text
cricbuzz-livestats/
|-- app.py
|-- api/
|-- database/
|   |-- analytics.py
|   |-- db_connection.py
|   |-- match_repository.py
|   |-- schema.sql
|   `-- scorecard_repository.py
|-- pages/
|   |-- Top Player Stats page
|   |-- Live Matches page
|   |-- SQL Analytics page
|   `-- CRUD Management page
|-- services/
|   `-- cricket_api.py
|-- sql/
|-- tests/
|-- utils/
|-- requirements.txt
|-- .gitignore
`-- README.md
Additional database utilities and development scripts may be present in the working directory.

## Prerequisites

- Python 3.10 or a compatible Python version
- pip
- A Cricbuzz Cricket API subscription and API key for API-dependent features

## Installation and Setup

1. Clone the repository and enter the project directory.

   ```bash
   git clone <your-github-repository-url>
   cd cricbuzz-livestats
   ```

2. Create and activate a virtual environment.

   **Windows PowerShell:**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your own API credentials.

   ```text
   CRICKET_API_KEY=your_rapidapi_key
   CRICKET_API_HOST=cricbuzz-cricket.p.rapidapi.com
   ```

   Never commit your real `.env` file or expose your API key.

5. Ensure the SQLite database is available at the path expected by the application. If setting up from scratch, review `database/schema.sql` and the database connection code before initializing the database.

6. Start the application from the project root.

   ```bash
   streamlit run app.py
   ```

## Using the Dashboard

Open the local URL displayed by Streamlit, usually `http://localhost:8501`.

Use the homepage navigation to access Live Matches, Top Player Stats, SQL Analytics, and CRUD Management. In SQL Analytics, select an available analysis and export supported results as CSV.

## Database and Data Limitations

- The application relies on the configured SQLite database for stored cricket records.
- API-dependent features require valid credentials and are subject to the provider's usage limits.
- Some match toss details and venue metadata may be unavailable. Missing values should not be interpreted as verified facts.
- Data availability depends on the records stored in the database and the responses returned by the API.

## Security

- Keep API credentials in `.env`.
- Do not upload virtual environments, API secrets, or local database backups to GitHub.
- Review files before committing or publishing the repository.

## Project Goal

The goal of Cricbuzz LiveStats is to combine cricket data retrieval, local data storage, SQL analytics, and interactive visualization in one application.
