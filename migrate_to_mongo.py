#!/usr/bin/env python3
"""Migrate existing match_results/ JSON files and PlayersWithTeam.csv to MongoDB.

Usage:
    python migrate_to_mongo.py --tournament wt20_2026 [--name "ICC T20 World Cup 2026"] [--recalculate]

Creates the tournament (if needed), uploads the player roster from
PlayersWithTeam.csv, and upserts all match JSON files into MongoDB.
"""

import csv
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MATCH_RESULTS_DIR = os.path.join(BASE_DIR, "match_results")
PLAYERS_CSV = os.path.join(BASE_DIR, "PlayersWithTeam.csv")


def load_players_from_csv():
    """Read PlayersWithTeam.csv and return list of {player_name, team}."""
    players = []
    if not os.path.isfile(PLAYERS_CSV):
        print(f"Warning: {PLAYERS_CSV} not found, skipping roster upload.")
        return players
    with open(PLAYERS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Player Name") or "").strip()
            team = (row.get("Team") or "").strip()
            if name and team:
                players.append({"player_name": name, "team": team})
    return players


def migrate(tournament_id, tournament_name):
    from db import create_tournament, get_tournament, set_players, save_match, get_db

    # Create tournament if needed
    if not get_tournament(tournament_id):
        players = load_players_from_csv()
        create_tournament(tournament_id, tournament_name, players)
        print(f"Created tournament '{tournament_id}' with {len(players)} players.")
    else:
        # Update roster from CSV
        players = load_players_from_csv()
        if players:
            set_players(tournament_id, players)
            print(f"Updated roster for '{tournament_id}' with {len(players)} players.")

    # Migrate match files
    if not os.path.isdir(MATCH_RESULTS_DIR):
        print(f"No match_results/ directory found at {MATCH_RESULTS_DIR}")
        return 0

    files = sorted(f for f in os.listdir(MATCH_RESULTS_DIR) if f.endswith(".json"))
    if not files:
        print("No JSON files found in match_results/")
        return 0

    print(f"\nMigrating {len(files)} match files...\n")

    for fname in files:
        fpath = os.path.join(MATCH_RESULTS_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)

        if "match_name" not in data:
            match_name = fname.replace(".json", "").rsplit("_", 1)[0] if "_" in fname else fname.replace(".json", "")
            data["match_name"] = match_name

        save_match(tournament_id, data)
        print(f"  ✅  {fname} → match_id={data.get('match_id', '')}")

    # Verify
    db = get_db()
    count = db.matches.count_documents({"tournament_id": tournament_id})
    print(f"\nMigrated {len(files)} matches. {count} docs in collection for '{tournament_id}'.")
    return len(files)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migrate match data to MongoDB for a tournament.")
    parser.add_argument("--tournament", required=True,
                        help="Tournament slug (e.g. wt20_2026)")
    parser.add_argument("--name", default="",
                        help="Tournament display name (default: same as slug)")
    parser.add_argument("--recalculate", action="store_true",
                        help="Recalculate fantasy points after migration")
    args = parser.parse_args()

    if not os.environ.get("MONGODB_URI"):
        print("Error: MONGODB_URI not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)

    tournament_name = args.name or args.tournament
    migrate(args.tournament, tournament_name)

    if args.recalculate:
        print("\nRecalculating fantasy points...")
        from calculate_points import recalculate_all
        recalculate_all(args.tournament)
        print("✅ Fantasy points recalculated.")


if __name__ == "__main__":
    main()
