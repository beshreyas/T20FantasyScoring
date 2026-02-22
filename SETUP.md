# Cricket-API / WT20 Setup

## What this project does

Flask app that provides:

- **API**
  - `GET /players/<player_name>` – Player stats (from Cricbuzz profiles, via Google search).
  - `GET /schedule` – Upcoming international matches (Cricbuzz schedule).
  - `GET /live` – Live match scores (Cricbuzz live scores).
  - `GET /match/<match_id>?cricinfo_url=<url>` – Completed match data: batting, bowling, fielding, **dots** (from ESPN Cricinfo), and **man_of_the_match** (from ESPN Cricinfo MVP page). Match data is taken from the Cricbuzz scorecard; dots and MoM require an ESPN Cricinfo full-scorecard URL.
- **Website** – `GET /` serves a Bootstrap UI for live scores, schedule, player search, and player comparison.

Data is scraped from **Cricbuzz** (scorecard, schedule, live, player profiles) and **ESPN Cricinfo** (dots and Player Of The Match). For educational use only; not for production.

---

## Prerequisites

- **Python 3.9+** (tested on 3.13)
- `python3` and `pip` on your PATH
- **Chrome + ChromeDriver** (and Selenium) if you want dots and man_of_the_match from Cricinfo (see below).

---

## Setup

1. **Virtual environment** (recommended):
   ```bash
   cd WT20
   python3 -m venv cric_venv
   ```

2. **Install dependencies**:
   ```bash
   ./cric_venv/bin/pip install -r requirements.txt
   ```
   On Windows: `cric_venv\Scripts\pip install -r requirements.txt`

3. **Run the app**:
   ```bash
   ./cric_venv/bin/python main.py
   ```
   On Windows: `cric_venv\Scripts\python main.py`  
   Then open **http://127.0.0.1:5000** (Flask runs with `debug=True`).

---

## Match endpoint and Cricinfo (`/match/<match_id>`)

- **Batting, bowling, fielding** come from the **Cricbuzz** scorecard (using `match_id` in the path).
- **Dots** (bowling dot-ball counts) and **man_of_the_match** come **only from ESPN Cricinfo**. You must pass the ESPN full-scorecard URL as the query parameter **`cricinfo_url`**.

**Example**
```bash
curl "http://127.0.0.1:5000/match/139373?cricinfo_url=https://www.espncricinfo.com/series/icc-men-s-t20-world-cup-2025-26-1502138/sri-lanka-vs-england-42nd-match-super-eights-group-2-1512760/full-scorecard"
```

- **Dots**: The app opens the Cricinfo full-scorecard (JS-rendered), finds the two bowling tables by the **0s** column header, and reads the 0s value per bowler. Implemented in `cricinfo_dots.py`. Requires **Chrome and ChromeDriver** (Selenium); otherwise dots in the response are 0.
- **Man of the match**: The app opens the Cricinfo **match-impact-player** (MVP) page, finds the “Player Of The Match” block, and extracts the player name. Implemented in `cricinfo_mom.py`. Also uses Selenium; if it fails or the parser doesn’t find the block, `man_of_the_match` in the JSON will be `null`.

Without `cricinfo_url`, or if Selenium is unavailable, the response still includes `batting`, `bowling`, `fielding`, and `scorecard_url`; `dots` will be 0 for all bowlers and `man_of_the_match` will be `null`.

---

## Scripts and modules (current)

| File | Purpose |
|------|--------|
| `main.py` | Flask app; match route, player/schedule/live routes, save to `match_results/`. |
| `batting.py` | Parse batting from Cricbuzz scorecard. |
| `bowling.py` | Parse bowling from Cricbuzz scorecard. |
| `fielding.py` | Build fielding (catches, run-outs, stumpings) from batting dismissals. |
| `cricinfo_dots.py` | Fetch Cricinfo full-scorecard (Selenium), parse bowling tables for **0s** column, return dots per bowler. |
| `cricinfo_mom.py` | Fetch Cricinfo match-impact-player page (Selenium), parse “Player Of The Match” and return the player name. Can be run as a script (see below). |

---

## Removed / no longer used

- **`dots.py`** – **Removed.** Previously fetched Cricbuzz over-by-over page and counted dot balls per bowler. That page lazy-loads overs and often only a subset of overs were loaded, so dot counts were incomplete and unreliable. Dot-ball counts are now taken **only from ESPN Cricinfo** (0s column on the full-scorecard) via `cricinfo_dots.py`. There is no Cricbuzz fallback for dots.

---

## Standalone script: Man of the match

You can run the MoM fetcher from the command line and optionally open the browser or save the page HTML for debugging:

```bash
cd WT20
./cric_venv/bin/python cricinfo_mom.py "https://www.espncricinfo.com/series/.../...-1512760/full-scorecard" [--visible] [--save-html]
```

- **`--visible`** – Open Chrome in a visible window so you can confirm the Cricinfo MVP page loads; window stays open for a few seconds.
- **`--save-html`** – Save the MVP page HTML to `mvp_page_debug.html` in the project folder (useful if MoM is not found and you need to inspect the page structure).

---

## Dependencies (`requirements.txt`)

- **Flask** – Web app and API
- **requests** – HTTP requests (Cricbuzz, Cricinfo fallback)
- **beautifulsoup4** – HTML parsing
- **lxml** – Parser for BeautifulSoup
- **googlesearch-python** – Resolve player profile URLs from Cricbuzz
- **selenium** – Headless Chrome for Cricinfo (dots and MoM) when the page is JS-rendered

Chrome and ChromeDriver must be installed and on your PATH (or otherwise available to Selenium) for Cricinfo dots and MoM to work.

---

## For the next maintainer

1. **Dots** – Sourced only from Cricinfo full-scorecard (0s column). If Cricinfo changes the table structure (e.g. class names or “0s” header), update `cricinfo_dots.py` (parsing and/or Selenium selectors).
2. **Man of the match** – Sourced only from Cricinfo match-impact-player page. If the “Player Of The Match” block or link structure changes, update `cricinfo_mom.py`. Use `--visible` and `--save-html` to debug.
3. **Match ID** – The number in `/match/<match_id>` is the **Cricbuzz** scorecard match ID. The `cricinfo_url` is a separate ESPN URL; there is no automatic mapping from Cricbuzz ID to Cricinfo URL, so callers must provide it.
4. **Saved results** – The match endpoint writes JSON to `match_results/<vs_portion>_<match_id>.json` (e.g. `England vs Sri Lanka_139373.json`). This folder is in `.gitignore`.

---

## Notes

- **`/live`** may return 500 if Cricbuzz’s live-scores HTML structure changes; the scraper would need an update.
- The template may reference `/static/images/bg.jpg`; if missing, the background image won’t load (app still runs).
- Player search uses Google; rate limits or blocking are possible with heavy use.
