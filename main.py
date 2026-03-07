import csv
import io

from flask import Flask, jsonify, render_template, request

from calculate_points import recalculate_all

app = Flask(__name__)


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
        create_tournament(tid, name, data.get("players"))
        return jsonify({"status": "ok", "tournament_id": tid})
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


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
    """Return match data. If not found and cricinfo_url is provided, scrape it."""
    if not match_id.isdigit():
        return jsonify({"error": "match_id must be numeric"}), 400
    from db import get_match, save_match

    doc = get_match(slug, match_id)
    if doc:
        return jsonify(doc)

    # Try to scrape
    cricinfo_url = request.args.get("cricinfo_url", "").strip()
    try:
        from scrape_match import scrape_match
        match_data, vs_portion = scrape_match(match_id, cricinfo_url or None)
        save_match(slug, match_data)
        # Auto-recalculate
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
# Frontend
# ---------------------------------------------------------------------------

@app.route('/')
def website():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=True)
