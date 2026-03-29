"""Aggregate fantasy points for a tournament.

Reads player→team mapping from MongoDB (tournament doc), scores every match,
and writes results to MongoDB.
"""

import re

from scoring import (
    calculate_batting_points,
    calculate_bowling_points,
    calculate_fielding_points,
    MOM_BONUS,
)


# ---------------------------------------------------------------------------
# Player → team mapping (from MongoDB)
# ---------------------------------------------------------------------------

def _load_player_team_map(tournament_id):
    """Load player→team mapping from the tournament's roster in MongoDB."""
    from db import get_players
    players = get_players(tournament_id)
    mapping = {}
    for p in players:
        name = p.get("player_name", "").strip()
        team = p.get("team", "").strip()
        if name and team:
            mapping[_normalise(name)] = team
    return mapping


def _normalise(name):
    """Lowercase, collapse whitespace, strip designations."""
    name = re.sub(r"\s*\(c\)\s*", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\(wk\)\s*", " ", name, flags=re.IGNORECASE)
    return " ".join(name.lower().split())


def _resolve_team(player_name, team_map):
    """Fuzzy-ish lookup: exact → substring → 'Unknown'."""
    key = _normalise(player_name)
    if key in team_map:
        return team_map[key]
    for csv_key, team in team_map.items():
        if csv_key in key or key in csv_key:
            return team
    return "Unknown"


# Canonical team-name mapping
_TEAM_CANONICAL = {
    "gkkani": "GKKani",
    "ppt": "PPT",
    "ramsurya": "RamSurya",
    "rsk": "RSK",
    "cni": "CNI",
}


def _normalise_team(team):
    """Return canonical team name (case-insensitive)."""
    if not team:
        return "Unknown"
    low = team.strip().lower()
    return _TEAM_CANONICAL.get(low, team.strip())


# ---------------------------------------------------------------------------
# Match processing
# ---------------------------------------------------------------------------

def _process_match(match_data, match_id, match_name, players, team_map):
    """Score a single match and accumulate into *players* dict."""

    def _ensure_player(name):
        key = _normalise(name)
        if key not in players:
            players[key] = {
                "player_name": name,
                "team": _normalise_team(_resolve_team(name, team_map)),
                "matches": [],
                "total_points": 0,
            }
        return key

    def _get_or_create_match_record(key, mid):
        for rec in players[key]["matches"]:
            if rec["match_id"] == mid:
                return rec
        rec = {
            "match_id": mid,
            "match_name": match_name,
            "batting_points": 0,
            "bowling_points": 0,
            "fielding_points": 0,
            "mom": 0,
            "total": 0,
        }
        players[key]["matches"].append(rec)
        return rec

    for rec in match_data.get("batting", []):
        name = rec.get("player", "")
        if not name:
            continue
        pts = calculate_batting_points(rec)
        key = _ensure_player(name)
        mr = _get_or_create_match_record(key, match_id)
        mr["batting_points"] += pts
        mr["total"] += pts
        players[key]["total_points"] += pts

    for rec in match_data.get("bowling", []):
        name = rec.get("player", "")
        if not name:
            continue
        pts = calculate_bowling_points(rec)
        key = _ensure_player(name)
        mr = _get_or_create_match_record(key, match_id)
        mr["bowling_points"] += pts
        mr["total"] += pts
        players[key]["total_points"] += pts

    fielding = match_data.get("fielding", {})
    for name, entry in fielding.items():
        if not name:
            continue
        pts = calculate_fielding_points(entry)
        key = _ensure_player(name)
        mr = _get_or_create_match_record(key, match_id)
        mr["fielding_points"] += pts
        mr["total"] += pts
        players[key]["total_points"] += pts

    mom_name = match_data.get("man_of_the_match")
    if mom_name:
        key = _ensure_player(mom_name)
        mr = _get_or_create_match_record(key, match_id)
        mr["mom"] = MOM_BONUS
        mr["total"] += MOM_BONUS
        players[key]["total_points"] += MOM_BONUS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recalculate_all(tournament_id):
    """Re-score every match for a tournament and write to MongoDB.

    Returns (leaderboard, team_leaderboard) lists.
    """
    from db import (
        get_all_matches, save_all_player_points,
        save_leaderboard, save_team_leaderboard,
    )

    team_map = _load_player_team_map(tournament_id)
    players = {}

    all_matches = get_all_matches(tournament_id)
    for doc in all_matches:
        match_id = doc.get("match_id", "")
        match_name = doc.get("match_name", "Match {}".format(match_id))
        _process_match(doc, str(match_id), match_name, players, team_map)

    all_players = sorted(players.values(), key=lambda p: p["total_points"], reverse=True)

    leaderboard = [
        {
            "player_name": p["player_name"],
            "team": p["team"],
            "matches_played": len(p["matches"]),
            "total_points": p["total_points"],
        }
        for p in all_players
    ]

    # Team leaderboard
    all_roster_teams = set(team_map.values())
    teams = {}
    for t in all_roster_teams:
        norm_t = _normalise_team(t)
        if norm_t not in teams:
            teams[norm_t] = {"team": norm_t, "total_points": 0, "player_count": 0}
    for p in all_players:
        t = _normalise_team(p["team"])
        if t == "Unknown":
            continue
        if t not in teams:
            teams[t] = {"team": t, "total_points": 0, "player_count": 0}
        teams[t]["total_points"] += p["total_points"]
        teams[t]["player_count"] += 1
    team_leaderboard = sorted(teams.values(), key=lambda t: t["total_points"], reverse=True)

    # Save to MongoDB
    save_all_player_points(tournament_id, all_players)
    save_leaderboard(tournament_id, leaderboard)
    save_team_leaderboard(tournament_id, team_leaderboard)

    print(f"[{tournament_id}] Scored {len(all_players)} players across "
          f"{sum(len(p['matches']) for p in all_players)} match appearances.")
    return leaderboard, team_leaderboard


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Recalculate fantasy points for a tournament.")
    parser.add_argument("tournament_id", help="Tournament slug (e.g. wt20_2026)")
    args = parser.parse_args()

    leaderboard, team_lb = recalculate_all(args.tournament_id)
    print("\n🏆  Player Leaderboard (top 10):")
    for i, p in enumerate(leaderboard[:10], 1):
        print(f"  {i:>2}. {p['player_name']:<25} {p['team']:<10} {p['total_points']:>6} pts  ({p['matches_played']} matches)")
    print("\n🏅  Team Standings:")
    for t in team_lb:
        print(f"  {t['team']:<10} {t['total_points']:>6} pts  ({t['player_count']} players)")
