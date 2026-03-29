"""MongoDB persistence layer for T20 Fantasy Hub.

Multi-tournament support: every document is scoped by tournament_id.
Connection string from MONGODB_URI env var (or .env file).

Collections:
    tournaments      — one doc per tournament (metadata + player roster)
    matches          — one doc per match (keyed by tournament_id + match_id)
    player_points    — one doc per player per tournament
    leaderboard      — one doc per tournament
    team_leaderboard — one doc per tournament
"""

import os
import copy
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

# Load .env file (if present) so you don't need to export vars manually
load_dotenv()

_client = None
_db = None

DB_NAME = os.environ.get("MONGODB_DB_NAME", "wt20")


def get_db():
    """Return the MongoDB database handle, creating the connection on first call."""
    global _client, _db
    if _db is not None:
        return _db
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI environment variable is not set. "
            "Set it to your MongoDB Atlas connection string."
        )
    _client = MongoClient(uri, tlsCAFile=certifi.where())
    _db = _client[DB_NAME]
    return _db


# ---------------------------------------------------------------------------
# Tournament helpers
# ---------------------------------------------------------------------------

def create_tournament(tournament_id, name, players=None, series_url=""):
    """Create a new tournament. players is a list of {player_name, team} dicts."""
    db = get_db()
    if db.tournaments.find_one({"tournament_id": tournament_id}):
        raise ValueError("Tournament '{}' already exists".format(tournament_id))
    doc = {
        "tournament_id": tournament_id,
        "name": name,
        "players": players or [],
        "series_url": series_url or "",
    }
    db.tournaments.insert_one(doc)
    return doc


def get_tournament(tournament_id):
    """Return a tournament document or None."""
    db = get_db()
    return db.tournaments.find_one({"tournament_id": tournament_id}, {"_id": 0})


def list_tournaments():
    """Return all tournaments (summary: id, name, player count, series_url)."""
    db = get_db()
    docs = db.tournaments.find({}, {"_id": 0, "tournament_id": 1, "name": 1, "players": 1, "series_url": 1})
    results = []
    for doc in docs:
        results.append({
            "tournament_id": doc["tournament_id"],
            "name": doc.get("name", doc["tournament_id"]),
            "player_count": len(doc.get("players", [])),
            "series_url": doc.get("series_url", ""),
        })
    return results


def update_tournament_series_url(tournament_id, series_url):
    """Update the Cricinfo series URL for a tournament."""
    db = get_db()
    db.tournaments.update_one(
        {"tournament_id": tournament_id},
        {"$set": {"series_url": series_url}},
    )


def update_tournament_name(tournament_id, name):
    """Update tournament display name."""
    db = get_db()
    db.tournaments.update_one(
        {"tournament_id": tournament_id},
        {"$set": {"name": name}},
    )


def delete_tournament(tournament_id):
    """Delete a tournament and ALL its associated data."""
    db = get_db()
    if not db.tournaments.find_one({"tournament_id": tournament_id}):
        return False
    db.tournaments.delete_one({"tournament_id": tournament_id})
    db.matches.delete_many({"tournament_id": tournament_id})
    db.player_points.delete_many({"tournament_id": tournament_id})
    db.leaderboard.delete_many({"tournament_id": tournament_id})
    db.team_leaderboard.delete_many({"tournament_id": tournament_id})
    return True


# ---------------------------------------------------------------------------
# Player roster helpers (stored inside tournament doc)
# ---------------------------------------------------------------------------

def get_players(tournament_id):
    """Return the player roster [{player_name, team}, ...] for a tournament."""
    doc = get_tournament(tournament_id)
    if not doc:
        return []
    return doc.get("players", [])


def set_players(tournament_id, players):
    """Replace the entire roster for a tournament."""
    db = get_db()
    db.tournaments.update_one(
        {"tournament_id": tournament_id},
        {"$set": {"players": players}},
    )


def add_player(tournament_id, player_name, team):
    """Add or update a single player in the roster."""
    db = get_db()
    # Remove existing entry for this player (if any)
    db.tournaments.update_one(
        {"tournament_id": tournament_id},
        {"$pull": {"players": {"player_name": player_name}}},
    )
    # Add the new/updated entry
    db.tournaments.update_one(
        {"tournament_id": tournament_id},
        {"$push": {"players": {"player_name": player_name, "team": team}}},
    )


def remove_player(tournament_id, player_name):
    """Remove a player from the roster."""
    db = get_db()
    result = db.tournaments.update_one(
        {"tournament_id": tournament_id},
        {"$pull": {"players": {"player_name": player_name}}},
    )
    return result.modified_count > 0


# ---------------------------------------------------------------------------
# Match helpers (scoped by tournament_id)
# ---------------------------------------------------------------------------

def save_match(tournament_id, match_data):
    """Upsert a match document (keyed by tournament_id + match_id)."""
    db = get_db()
    match_id = str(match_data.get("match_id", ""))
    if not match_id:
        raise ValueError("match_data must contain a 'match_id' field")
    match_data["tournament_id"] = tournament_id
    db.matches.update_one(
        {"tournament_id": tournament_id, "match_id": match_id},
        {"$set": match_data},
        upsert=True,
    )


def get_match(tournament_id, match_id):
    """Return a single match document or None."""
    db = get_db()
    return db.matches.find_one(
        {"tournament_id": tournament_id, "match_id": str(match_id)},
        {"_id": 0},
    )


def get_all_matches(tournament_id):
    """Return every match document for a tournament."""
    db = get_db()
    return list(db.matches.find({"tournament_id": tournament_id}, {"_id": 0}))


def delete_match(tournament_id, match_id):
    """Delete a match. Returns True if something was deleted."""
    db = get_db()
    result = db.matches.delete_one(
        {"tournament_id": tournament_id, "match_id": str(match_id)}
    )
    return result.deleted_count > 0


def get_match_summaries(tournament_id):
    """Return lightweight list of matches for a tournament."""
    db = get_db()
    docs = db.matches.find(
        {"tournament_id": tournament_id},
        {"_id": 0, "match_id": 1, "match_name": 1, "cricinfo_url": 1},
    )
    return [
        {
            "match_id": d.get("match_id", ""),
            "match_name": d.get("match_name", ""),
            "cricinfo_url": d.get("cricinfo_url", ""),
        }
        for d in docs
    ]


# ---------------------------------------------------------------------------
# Player-points / leaderboard helpers (scoped by tournament_id)
# ---------------------------------------------------------------------------

def save_all_player_points(tournament_id, player_points_list):
    """Replace all player points for a tournament."""
    db = get_db()
    db.player_points.delete_many({"tournament_id": tournament_id})
    if player_points_list:
        docs = copy.deepcopy(player_points_list)
        for d in docs:
            d["tournament_id"] = tournament_id
        db.player_points.insert_many(docs)


def get_all_player_points(tournament_id):
    """Return every player-points document for a tournament."""
    db = get_db()
    return list(db.player_points.find({"tournament_id": tournament_id}, {"_id": 0, "tournament_id": 0}))


def save_leaderboard(tournament_id, leaderboard):
    """Replace the leaderboard for a tournament."""
    db = get_db()
    db.leaderboard.delete_many({"tournament_id": tournament_id})
    if leaderboard:
        db.leaderboard.insert_one({"tournament_id": tournament_id, "data": leaderboard})


def get_leaderboard(tournament_id):
    """Return the leaderboard list for a tournament."""
    db = get_db()
    doc = db.leaderboard.find_one({"tournament_id": tournament_id}, {"_id": 0})
    return doc.get("data", []) if doc else []


def save_team_leaderboard(tournament_id, team_leaderboard):
    """Replace the team leaderboard for a tournament."""
    db = get_db()
    db.team_leaderboard.delete_many({"tournament_id": tournament_id})
    if team_leaderboard:
        db.team_leaderboard.insert_one({"tournament_id": tournament_id, "data": team_leaderboard})


def get_team_leaderboard(tournament_id):
    """Return the team leaderboard list for a tournament."""
    db = get_db()
    doc = db.team_leaderboard.find_one({"tournament_id": tournament_id}, {"_id": 0})
    return doc.get("data", []) if doc else []
