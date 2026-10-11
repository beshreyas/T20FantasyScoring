# T20FantasyScoring: project context handoff

Written 2026-10-11 for sharing with another Claude session. Nothing here is a secret. No credentials were found or used.

## Project basics
- Owner: Shreyas (GitHub `beshreyas`). Private project.
- Repo: https://github.com/beshreyas/T20FantasyScoring
- Goal: build and maintain a fantasy points scoring system for T20 cricket matches.
- No project instructions are set.
- Live site: https://t20-fantasy-hub.onrender.com/ (hosted on Render, database on MongoDB Atlas). The real `MONGODB_URI` lives only in Render's Environment settings, not in the repo.

## What the app is (from the repo exploration, 2026-10-04)
A Flask app for running fantasy leagues on T20 tournaments.
- You create a tournament and upload a player-to-fantasy-team CSV (`PlayersWithTeam.csv`, teams like PPT, RamSurya, GKKani).
- It pulls finished scorecards from ESPN Cricinfo's undocumented `hs-consumer-api`.
- It scores every player using the rules in `SCORING.md` (`scoring.py`) and shows player and team leaderboards in a single-page UI (`templates/index.html`).
- Data is stored in MongoDB (`db.py`). Deployed with gunicorn via the Dockerfile (listens on port 10000). New matches are picked up through `/auto-scrape/trigger`, which accepts GET so an external cron can call it (last commit, Mar 29).
- State: no open PRs or issues. The only PR (scoring + UI) was merged in February; the `t20_scoring_with_ui` branch was never deleted. No TODOs and no tests. Scoring functions were smoke-tested directly and work (e.g. a duck off 3 balls scores -13).

## Issues noticed in the code
- The daily auto-scrape scheduler (00:15 IST) only starts under `python main.py`, never under gunicorn, and `APScheduler`/`pytz` are not in `requirements.txt`. In Docker, the external cron is the only thing scraping.
- No endpoint requires auth. Anyone with the URL can delete a tournament, overwrite the roster or trigger a scrape. Because the trigger accepts GET, a crawler could set it off.
- The README still documents `/players`, `/schedule` and `/live`, but those routes are no longer in `main.py`.
- Players are matched to teams by substring (`calculate_points.py:41`), so a short name can land on the wrong team. Bowling points come out as decimals for part-overs (`scoring.py:64`).

Suggested next work, not yet started: (1) add a pytest suite for `scoring.py` and team matching using the saved scorecards in `match_results/`; (2) add a shared-secret check on write and trigger endpoints, and either remove the dead scheduler code from the gunicorn path or add its dependencies.

## Incident: "select tournament shows nothing" (2026-10-04)
- Symptom: on the live site the tournament selector was empty and the page said "No tournaments yet", although a tournament had been run before. The user had not visited for a long time.
- Cause (from reading the code, not from the live site, which the sandbox could not open): the free MongoDB Atlas cluster auto-pauses after about 60 days of inactivity. When the app can't reach the database, `GET /tournaments` fails, and the error handler in `templates/index.html:1074` (`.catch(() => { hideEl(loading); showEl(empty); })`) shows the empty state with no error message. The dropdown is filled only on success (`templates/index.html:1091`).
- Resolution: the user resumed the Atlas cluster. Nothing in the repo was changed.
- Checklist if it recurs: Atlas cluster paused? Atlas Network Access has `0.0.0.0/0`? Database user and password still valid? Render `MONGODB_URI` set, and `MONGODB_DB_NAME` (defaults to `wt20` in code) matches? Render logs show `ServerSelectionTimeoutError` or `authentication failed`?
- Offered but not done: change the page to show the real error instead of "No tournaments yet".

## Hosting discussion (2026-10-04)
The user asked how to stop Atlas pausing and whether the app can be hosted free without Render's keep-alive pings. All of this was written from memory without checking pricing pages, so verify current terms before acting.
- Keep Atlas and Render awake: a free scheduled ping (cron-job.org) calling `https://t20-fantasy-hub.onrender.com/tournaments` every 14 minutes. That route reads the database, so Atlas stays active. A ping to `/` or `/auto-scrape/status` would keep Render awake but not touch the database.
- Alternatives discussed:
  - Google Cloud Run (recommended if moving): the existing Dockerfile should deploy as is; wakes in seconds when idle; large free allowance; needs a billing card.
  - Oracle Cloud Always Free VM: always on, but self-managed.
  - Hugging Face Spaces (Docker): free, but sleeps after a couple of days without visitors.
  - Koyeb: has a free web service; limits unverified.
  - Fly.io and Railway: mostly trial credit or pay-as-you-go now.
  - Vercel: Flask as serverless functions, but the daily scrape would not run.
  - Heroku: no free tier since 2022; about $5 a month.
  - GitHub Pages: static only, cannot run Flask. GitHub Actions: can act as the pinger, but scheduled runs are best-effort and a 14-minute ping would likely use up free minutes on a private repo.
  - PythonAnywhere free: avoid; it blocks most outside internet access, which would break Cricinfo scraping and Atlas.
- Current recommendation: stay on Render with the free cron-job.org ping, or move to Cloud Run to stop pinging.

### Cloud Run steps (as given, unrun)
1. Create a Google Cloud project, attach billing, install `gcloud`, run `gcloud auth login` and `gcloud config set project YOUR_PROJECT_ID`.
2. `gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com`
3. From the repo folder: `gcloud run deploy t20-fantasy-hub --source . --region asia-south1 --allow-unauthenticated --port 10000 --min-instances 0 --max-instances 1 --timeout 120 --set-env-vars MONGODB_URI='YOUR_ATLAS_URI',MONGODB_DB_NAME=wt20`. Prefer Secret Manager with `--set-secrets` for the URI. Never commit it.
4. Atlas Network Access needs `0.0.0.0/0`, since Cloud Run has no fixed IP.
5. Open the printed URL and confirm the old tournaments appear.
6. Create a Cloud Scheduler job that sends a GET to `https://YOUR-URL/auto-scrape/trigger` at `15 0 * * *` in timezone `Asia/Kolkata`, since the in-app scheduler does not run under gunicorn.
7. After it works, update bookmarks and delete or suspend the Render service.

## Open decisions
- The user has not yet chosen between staying on Render with a ping or moving to Cloud Run.
- The user has not chosen between the two suggested code tasks (tests, or auth plus scheduler cleanup), or the error-message fix.
- No code changes, deploys or PRs have been made. Do not deploy or change hosting without the user's OK.

## Working notes for the next session
- Project chat messages should be posted top level, not as replies under a user's message, or the user won't see them (this happened once on 2026-10-11).
- The coordinator session ID given to the user was `session_01S82KB3dtWx2TpPEW2wfzTi` (https://claude.ai/code/session_01S82KB3dtWx2TpPEW2wfzTi), taken from the commit attribution line.
