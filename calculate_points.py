"""Aggregate fantasy points across all matches in match_results/.

Reads PlayersWithTeam.csv for the player→team mapping, scores every match
JSON, and writes three output files under player_points/:
    all_player_points.json   – per-player, per-match breakdown + totals
    leaderboard.json         – players sorted by total points
    team_leaderboard.json    – teams sorted by aggregate points
"""

import csv
import json
import os
import re

from scoring import (
    calculate_batting_points,
    calculate_bowling_points,
    calculate_fielding_points,
    MOM_BONUS,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MATCH_RESULTS_DIR = os.path.join(BASE_DIR, "match_results")
PLAYER_POINTS_DIR = os.path.join(BASE_DIR, "player_points")
PLAYERS_CSV       = os.path.join(BASE_DIR, "PlayersWithTeam.csv")


# ---------------------------------------------------------------------------
# Player → team mapping
# ---------------------------------------------------------------------------

def _load_player_team_map():
    """Load PlayersWithTeam.csv into {normalised_name: team}."""
    mapping = {}
    if not os.path.isfile(PLAYERS_CSV):
        return mapping
    with open(PLAYERS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Player Name", "").strip()
            team = row.get("Team", "").strip()
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
    # partial match (e.g. "Phil Salt" vs "Philip Salt")
    for csv_key, team in team_map.items():
        if csv_key in key or key in csv_key:
            return team
    return "Unknown"


# Canonical team-name mapping (CSV has mixed case: GKKani, GkKani, Gkkani)
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
    """Score a single match and accumulate into *players* dict.

    players: {normalised_name: {
        "player_name": str, "team": str,
        "matches": [{match_id, batting, bowling, fielding, mom, total}],
        "total_points": int
    }}
    """

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

    # --- batting ---
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

    # --- bowling ---
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

    # --- fielding ---
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

    # --- Man of the Match ---
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

def recalculate_all():
    """Re-score every match in match_results/ and write output files.

    Returns (leaderboard, team_leaderboard) lists.
    """
    team_map = _load_player_team_map()
    players = {}  # normalised_name → data

    if not os.path.isdir(MATCH_RESULTS_DIR):
        os.makedirs(MATCH_RESULTS_DIR, exist_ok=True)

    for fname in sorted(os.listdir(MATCH_RESULTS_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(MATCH_RESULTS_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            match_data = json.load(f)
        match_id = match_data.get("match_id", fname.replace(".json", ""))
        # Derive human-readable match name from filename, e.g. "England vs Sri Lanka"
        match_name = fname.replace(".json", "").rsplit("_", 1)[0] if "_" in fname else fname.replace(".json", "")
        _process_match(match_data, match_id, match_name, players, team_map)

    # Build sorted leaderboard
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

    # Team leaderboard — pre-seed all teams from CSV so 0-point teams appear
    all_csv_teams = set(team_map.values())
    teams = {}
    for t in all_csv_teams:
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

    # Write output files
    os.makedirs(PLAYER_POINTS_DIR, exist_ok=True)

    with open(os.path.join(PLAYER_POINTS_DIR, "all_player_points.json"), "w", encoding="utf-8") as f:
        json.dump(all_players, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PLAYER_POINTS_DIR, "leaderboard.json"), "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2, ensure_ascii=False)

    with open(os.path.join(PLAYER_POINTS_DIR, "team_leaderboard.json"), "w", encoding="utf-8") as f:
        json.dump(team_leaderboard, f, indent=2, ensure_ascii=False)

    print(f"Scored {len(all_players)} players across "
          f"{sum(len(p['matches']) for p in all_players)} match appearances.")
    return leaderboard, team_leaderboard


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    leaderboard, team_lb = recalculate_all()
    print("\n🏆  Player Leaderboard (top 10):")
    for i, p in enumerate(leaderboard[:10], 1):
        print(f"  {i:>2}. {p['player_name']:<25} {p['team']:<10} {p['total_points']:>6} pts  ({p['matches_played']} matches)")
    print("\n🏅  Team Standings:")
    for t in team_lb:
        print(f"  {t['team']:<10} {t['total_points']:>6} pts  ({t['player_count']} players)")
