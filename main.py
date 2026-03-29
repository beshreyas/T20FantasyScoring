import csv
import io
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from calculate_points import recalculate_all

app = Flask(__name__)

# Store last auto-scrape results in memory
_last_auto_scrape = {"results": [], "timestamp": None}


# ---------------------------------------------------------------------------
# Tournament endpoints
# ---------------------------------------------------------------------------

@app.route('/tournaments', methods=['GET'])
def list_tournaments_endpoint():
    """List all tournaments."""
    from db import list_tournaments
    return jsonify(list_tournaments())


@app.route('/tournaments', methods=['POST'])
def create_tournament_endpoint():
    """Create a new tournament. Body: {tournament_id, name, players?}."""
    from db import create_tournament
    data = request.get_json(force=True)
    tid = (data.get("tournament_id") or "").strip()
    name = (data.get("name") or "").strip()
    if not tid or not name:
        return jsonify({"error": "tournament_id and name are required"}), 400
    try:
        series_url = (data.get("series_url") or "").strip()
        create_tournament(tid, name, data.get("players"), series_url=series_url)
        return jsonify({"status": "ok", "tournament_id": tid})
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@app.route('/tournaments/<slug>', methods=['PUT'])
def update_tournament_endpoint(slug):
    """Update a tournament. Body: {series_url?}."""
    from db import get_tournament, update_tournament_series_url
    t = get_tournament(slug)
    if not t:
        return jsonify({"error": "Tournament not found"}), 404
    data = request.get_json(force=True)
    series_url = data.get("series_url")
    if series_url is not None:
        update_tournament_series_url(slug, series_url.strip())
    return jsonify({"status": "ok"})


@app.route('/tournaments/<slug>', methods=['DELETE'])
def delete_tournament_endpoint(slug):
    """Delete a tournament and all its data."""
    from db import delete_tournament
    if delete_tournament(slug):
        return jsonify({"status": "ok", "tournament_id": slug})
    return jsonify({"error": "Tournament not found"}), 404


# ---------------------------------------------------------------------------
# Player roster endpoints
# ---------------------------------------------------------------------------

@app.route('/t/<slug>/players', methods=['GET'])
def get_players_endpoint(slug):
    """Return the player roster for a tournament."""
    from db import get_players
    return jsonify(get_players(slug))


@app.route('/t/<slug>/players', methods=['POST'])
def set_players_endpoint(slug):
    """Replace entire roster. Accepts JSON array or CSV file upload."""
    from db import set_players, get_tournament
    if not get_tournament(slug):
        return jsonify({"error": "Tournament not found"}), 404

    # CSV file upload
    if 'file' in request.files:
        file = request.files['file']
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)
        players = []
        for row in reader:
            name = (row.get("Player Name") or row.get("player_name") or "").strip()
            team = (row.get("Team") or row.get("team") or "").strip()
            if name and team:
                players.append({"player_name": name, "team": team})
        set_players(slug, players)
        return jsonify({"status": "ok", "players_count": len(players)})

    # JSON body
    data = request.get_json(force=True)
    if not isinstance(data, list):
        return jsonify({"error": "Expected JSON array of {player_name, team}"}), 400
    set_players(slug, data)
    return jsonify({"status": "ok", "players_count": len(data)})


@app.route('/t/<slug>/players', methods=['PUT'])
def add_player_endpoint(slug):
    """Add or update a single player. Body: {player_name, team}."""
    from db import add_player, get_tournament
    if not get_tournament(slug):
        return jsonify({"error": "Tournament not found"}), 404
    data = request.get_json(force=True)
    name = (data.get("player_name") or "").strip()
    team = (data.get("team") or "").strip()
    if not name or not team:
        return jsonify({"error": "player_name and team are required"}), 400
    add_player(slug, name, team)
    return jsonify({"status": "ok", "player_name": name, "team": team})


@app.route('/t/<slug>/players/<player_name>', methods=['DELETE'])
def remove_player_endpoint(slug, player_name):
    """Remove a player from the roster."""
    from db import remove_player
    if remove_player(slug, player_name):
        return jsonify({"status": "ok"})
    return jsonify({"error": "Player not found"}), 404


# ---------------------------------------------------------------------------
# Match endpoint (scrape + read)
# ---------------------------------------------------------------------------

@app.route('/t/<slug>/match/<match_id>', methods=['GET'])
def get_match_endpoint(slug, match_id):
    """Return match data. If not found, scrape from Cricinfo scorecard URL."""
    from db import get_match, save_match

    doc = get_match(slug, match_id)
    if doc:
        return jsonify(doc)

    # Need a scorecard URL to scrape
    scorecard_url = request.args.get("scorecard_url", "").strip()
    if not scorecard_url:
        return jsonify({"error": "scorecard_url query param required (ESPN Cricinfo full-scorecard URL)"}), 400

    # Scrape from Cricinfo
    try:
        from scrape_match import scrape_match
        match_data, vs_portion = scrape_match(scorecard_url)
        # Override match_id if user provided one in the URL path
        if match_id:
            match_data["match_id"] = str(match_id)
        save_match(slug, match_data)
        # Auto-recalculate
        try:
            recalculate_all(slug)
        except Exception as e:
            print("Warning: recalculate failed: {}".format(e))
        return jsonify(match_data)
    except Exception as e:
        return jsonify({"error": "Scrape failed: {}".format(str(e))}), 500


@app.route('/t/<slug>/match/auto', methods=['GET'])
def auto_scrape_match(slug):
    """Scrape a match from a Cricinfo scorecard URL (auto-extracts match_id).

    Used by the UI to add matches with just a URL — no manual ID needed.
    """
    from db import get_match, save_match

    scorecard_url = request.args.get("scorecard_url", "").strip()
    if not scorecard_url:
        return jsonify({"error": "scorecard_url query param required"}), 400

    try:
        from scrape_match import scrape_match
        match_data, vs_portion = scrape_match(scorecard_url)

        # Check if this match already exists
        match_id = match_data.get("match_id", "")
        existing = get_match(slug, match_id) if match_id else None
        if existing:
            return jsonify(existing)

        save_match(slug, match_data)
        # Auto-recalculate fantasy points
        try:
            recalculate_all(slug)
        except Exception as e:
            print("Warning: recalculate failed: {}".format(e))
        return jsonify(match_data)
    except Exception as e:
        return jsonify({"error": "Scrape failed: {}".format(str(e))}), 500



# ---------------------------------------------------------------------------
# Fantasy Scoring Endpoints (tournament-scoped)
# ---------------------------------------------------------------------------

@app.route('/t/<slug>/fantasy/leaderboard')
def fantasy_leaderboard(slug):
    """Player leaderboard for a tournament."""
    from db import get_leaderboard
    return jsonify(get_leaderboard(slug))


@app.route('/t/<slug>/fantasy/teams')
def fantasy_teams(slug):
    """Team leaderboard for a tournament."""
    from db import get_team_leaderboard
    return jsonify(get_team_leaderboard(slug))


@app.route('/t/<slug>/fantasy/player/<player_name>')
def fantasy_player(slug, player_name):
    """Per-match point breakdown for a player in a tournament."""
    from db import get_all_player_points
    all_players = get_all_player_points(slug)
    search_lower = player_name.lower()
    for p in all_players:
        if search_lower in p["player_name"].lower():
            return jsonify(p)
    return jsonify({"error": "Player not found"}), 404


@app.route('/t/<slug>/fantasy/recalculate', methods=['GET', 'POST'])
def fantasy_recalculate(slug):
    """Recalculate fantasy points for a tournament."""
    try:
        leaderboard, team_lb = recalculate_all(slug)
        return jsonify({
            "status": "ok",
            "players_scored": len(leaderboard),
            "teams": len(team_lb),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/t/<slug>/fantasy/team/<team_name>')
def fantasy_team_players(slug, team_name):
    """All players for a team in a tournament."""
    from db import get_all_player_points
    all_players = get_all_player_points(slug)
    search_lower = team_name.lower()
    team_players = [p for p in all_players if p.get("team", "").lower() == search_lower]
    team_players.sort(key=lambda p: p["total_points"], reverse=True)
    return jsonify(team_players)


@app.route('/t/<slug>/fantasy/matches')
def fantasy_matches(slug):
    """List scraped matches for a tournament."""
    from db import get_match_summaries
    return jsonify(get_match_summaries(slug))


@app.route('/t/<slug>/fantasy/match/<match_id>', methods=['DELETE'])
def fantasy_delete_match(slug, match_id):
    """Delete a match and recalculate points."""
    from db import delete_match
    if not delete_match(slug, match_id):
        return jsonify({"error": "Match not found"}), 404
    try:
        recalculate_all(slug)
    except Exception as e:
        print("Warning: Fantasy recalculation failed: {}".format(e))
    return jsonify({"status": "ok", "match_id": match_id})


# ---------------------------------------------------------------------------
# Auto-scrape endpoints
# ---------------------------------------------------------------------------

@app.route('/auto-scrape/trigger', methods=['GET', 'POST'])
def trigger_auto_scrape():
    """Manually trigger the auto-scrape agent."""
    global _last_auto_scrape
    try:
        from auto_scrape import check_all_tournaments
        results = check_all_tournaments()
        _last_auto_scrape = {
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
        total_new = sum(len(r["new_matches"]) for r in results)
        return jsonify({
            "status": "ok",
            "tournaments_checked": len(results),
            "new_matches": total_new,
            "details": results,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/auto-scrape/status', methods=['GET'])
def auto_scrape_status():
    """Return the last auto-scrape run results."""
    return jsonify(_last_auto_scrape)


@app.route('/auto-scrape/test-scheduler', methods=['POST'])
def test_scheduler_endpoint():
    """Schedule a one-off auto-scrape run 10 seconds from now to test APScheduler."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from datetime import datetime, timedelta
        
        # We need the global scheduler instance to add a job to it dynamically,
        # but since we create it in _start_scheduler, the easiest way to test
        # without global variable refactoring is to just run a thread with a delay.
        # However, to explicitly test APScheduler itself works:
        global _scheduler
        if not _scheduler:
            return jsonify({"error": "Scheduler not running"}), 500
            
        run_time = datetime.now() + timedelta(seconds=10)
        
        def _test_job():
            global _last_auto_scrape
            print(f"\\n[{datetime.now().isoformat()}] 🕒 TEST SCHEDULER FIRED!")
            try:
                from auto_scrape import check_all_tournaments
                with app.app_context():
                    results = check_all_tournaments()
                    _last_auto_scrape = {
                        "results": results,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                print(f"Auto-scrape test error: {e}")
                
        _scheduler.add_job(_test_job, 'date', run_date=run_time, id='test_run')
        return jsonify({"status": "ok", "message": "Auto-scrape scheduled to run in 10 seconds. Check terminal logs."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

@app.route('/')
def website():
    return render_template('index.html')


# ---------------------------------------------------------------------------
# APScheduler — runs auto-scrape at 00:15 IST daily
# ---------------------------------------------------------------------------

_scheduler = None

def _start_scheduler():
    """Start APScheduler for the daily auto-scrape job."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz
    except ImportError:
        print("⚠️  APScheduler not installed — daily auto-scrape disabled.")
        print("   Install with: pip install APScheduler pytz")
        return

    def _scheduled_job():
        global _last_auto_scrape
        try:
            from auto_scrape import check_all_tournaments
            with app.app_context():
                results = check_all_tournaments()
                _last_auto_scrape = {
                    "results": results,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            print(f"Auto-scrape error: {e}")

    ist = pytz.timezone("Asia/Kolkata")
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _scheduled_job,
        CronTrigger(hour=0, minute=15, timezone=ist),
        id="auto_scrape_daily",
        name="Daily auto-scrape at 00:15 IST",
    )
    _scheduler.start()
    print("✅ APScheduler started: auto-scrape at 00:15 IST daily")


if __name__ == "__main__":
    _start_scheduler()
    app.run(debug=True, use_reloader=False)
