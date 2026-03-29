# Cricket-API / WT20 Setup

## What this project does

Flask app that provides:

- **API**
  - `GET /players/<player_name>` – Player stats (from Cricbuzz profiles, via Google search).
  - `GET /schedule` – Upcoming international matches (Cricbuzz schedule).
  - `GET /live` – Live match scores (Cricbuzz live scores).
  - `GET /t/<slug>/match/<match_id>?series_id=<id>` – Completed match data: batting, bowling (with dots), fielding, and man_of_the_match. All data comes from **ESPN Cricinfo API** in a single call.
- **Website** – `GET /` serves a Bootstrap UI for live scores, schedule, player search, and player comparison.
- **Fantasy Scoring** – Tracks player/team leaderboards per tournament. Player-team mapping via CSV upload.

---

## Prerequisites

- **Python 3.9+** (tested on 3.13)
- `python3` and `pip` on your PATH

> **Note:** Selenium and Chrome are **no longer needed**. All match data comes from the Cricinfo JSON API.

---

## Setup

1. **Virtual environment** (recommended):
   ```bash
   cd WT20
   python3 -m venv .venv
   ```

2. **Install dependencies**:
   ```bash
   ./.venv/bin/pip install -r requirements.txt
   ```
   On Windows: `.venv\Scripts\pip install -r requirements.txt`

3. **Configure `.env`**:
   ```bash
   # MongoDB Atlas connection string
   MONGODB_URI=mongodb+srv://...
   MONGODB_DB_NAME=wt20

   # ESPN Cricinfo API config
   CRICINFO_SERIES_ID=<your_series_id>
   CRICINFO_MATCH_URL=https://hs-consumer-api.espncricinfo.com/v1/pages/match/scorecard
   ```

4. **Run the app**:
   ```bash
   ./.venv/bin/python main.py
   ```
   Then open **http://127.0.0.1:5000** (Flask runs with `debug=True`).

---

## Match endpoint (`/t/<slug>/match/<match_id>`)

All match data (batting, bowling with dots, fielding, MoM) comes from a **single ESPN Cricinfo API call**. No HTML scraping, no Selenium.

**Requirements:**
- A Cricinfo **match ID** (numeric, from the Cricinfo URL)
- A Cricinfo **series ID** (from `.env` via `CRICINFO_SERIES_ID`, or pass `?series_id=...`)

**Example:**
```bash
curl "http://127.0.0.1:5000/t/wt20_2026/match/1512760?series_id=1502138"
```

**CLI scraper:**
```bash
python scrape_match.py 1512760 --tournament wt20_2026 --series-id 1502138
```

---

## Scripts and modules

| File | Purpose |
|------|---------|
| `main.py` | Flask app; tournament, match, player, and fantasy scoring endpoints. |
| `scrape_match.py` | Fetches match data from ESPN Cricinfo API (batting, bowling+dots, fielding, MoM). |
| `scoring.py` | Fantasy point calculation functions (batting, bowling, fielding, MoM). |
| `calculate_points.py` | Aggregates fantasy points across matches for a tournament. |
| `db.py` | MongoDB persistence layer (tournaments, matches, leaderboards). |
| `update_ui.py` | UI template update utilities. |

---

## Dependencies (`requirements.txt`)

- **Flask** – Web app and API
- **requests** – HTTP requests to Cricinfo API
- **pymongo** – MongoDB Atlas
- **python-dotenv** – `.env` file loading
- **gunicorn** – Production WSGI server

---

## For the next maintainer

1. **Cricinfo API** – The project uses `hs-consumer-api.espncricinfo.com` which is undocumented. If this API changes, update `scrape_match.py`.
2. **Match & Series IDs** – Found in Cricinfo URLs: `espncricinfo.com/series/<slug>-<SERIES_ID>/...-<MATCH_ID>/...`
3. **Saved results** – Match JSON saved to `match_results/<vs_portion>_<match_id>.json`. This folder is in `.gitignore`.
4. **Player CSV** – Upload `PlayersWithTeam.csv` via the UI or `POST /t/<slug>/players` to set up fantasy team rosters.

---

## Notes

- **`/live`** may return 500 if Cricbuzz's live-scores HTML structure changes.
- The template may reference `/static/images/bg.jpg`; if missing, the background image won't load.
- Player search uses Google; rate limits or blocking are possible with heavy use.
