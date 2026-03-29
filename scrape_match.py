#!/usr/bin/env python3
"""Standalone CLI scraper for cricket matches via ESPN Cricinfo.

Usage:
    python scrape_match.py <cricinfo_url> --tournament <slug> [--local-only]
    python scrape_match.py --json-file <path> --tournament <slug> [--local-only]

The scraper fetches the ESPN Cricinfo scorecard page and extracts match data
from the embedded __NEXT_DATA__ JSON (same data as the internal API).

Examples:
    python scrape_match.py "https://www.espncricinfo.com/series/.../full-scorecard" --tournament wt20_2026
    python scrape_match.py --json-file match_data.json --tournament ipl_2025 --local-only
"""

import argparse
import json
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

MATCH_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "match_results")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _fetch_from_page(scorecard_url):
    """Fetch the Cricinfo scorecard page and extract __NEXT_DATA__ JSON.

    Uses curl_cffi to impersonate a Chrome browser (bypasses Akamai WAF).
    The scorecard page embeds all match data in a __NEXT_DATA__ script tag —
    same data structure as the internal hs-consumer-api.
    """
    from curl_cffi import requests as cffi_requests

    if "/full-scorecard" not in scorecard_url:
        scorecard_url = scorecard_url.rstrip("/") + "/full-scorecard"

    print(f"Fetching Cricinfo scorecard page: {scorecard_url}")
    resp = cffi_requests.get(scorecard_url, impersonate="chrome", timeout=30)
    resp.raise_for_status()

    html = resp.text
    if "__NEXT_DATA__" not in html:
        raise RuntimeError("Could not find __NEXT_DATA__ in page HTML. "
                           "ESPN Cricinfo may have changed their page structure.")

    # Extract the JSON from the <script id="__NEXT_DATA__"> tag
    marker = '__NEXT_DATA__'
    marker_pos = html.find(marker)
    script_start = html.rfind('<script', 0, marker_pos)
    content_start = html.find('>', script_start) + 1
    content_end = html.find('</script>', content_start)
    next_data = json.loads(html[content_start:content_end])

    # The match data lives under props.appPageProps.data
    data = next_data.get("props", {}).get("appPageProps", {}).get("data", {})
    if not data:
        raise RuntimeError("__NEXT_DATA__ found but no match data under props.appPageProps.data")

    return data


def _load_json_file(path):
    """Load match data from a pre-downloaded JSON file.

    Supports both raw API responses and __NEXT_DATA__ extracted files.
    """
    print(f"Loading from file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # If it's a __NEXT_DATA__ wrapper, unwrap
    if "props" in raw and "appPageProps" in raw.get("props", {}):
        return raw["props"]["appPageProps"].get("data", raw)

    # If it has 'content' and 'match' at top level, it's a raw API response
    if "content" in raw and "match" in raw:
        return raw

    # If it looks like an IPL-2025-BACKEND-style file, return as-is
    return raw


# ---------------------------------------------------------------------------
# ESPN Cricinfo data extraction
# ---------------------------------------------------------------------------

def _extract_batting(innings_data):
    """Extract batting records from all innings (<=2)."""
    batting = []
    seen = set()
    for inning in innings_data:
        if inning.get("inningNumber", 99) > 2:
            continue
        for b in inning.get("inningBatsmen", []):
            player_obj = b.get("player", {})
            player_name = player_obj.get("longName", "").strip()
            if not player_name or player_name in seen:
                continue
            seen.add(player_name)

            # Build dismissal string for duck detection in scoring.py
            is_out = b.get("isOut", False)
            dismissal_text = ""
            if is_out:
                dt = b.get("dismissalText", {})
                dismissal_text = dt.get("long", dt.get("short", "out"))
            else:
                dismissal_text = "not out"

            batting.append({
                "player": player_name,
                "dismissal": dismissal_text,
                "runs": b.get("runs", 0) or 0,
                "balls": b.get("balls", 0) or 0,
                "fours": b.get("fours", 0) or 0,
                "sixes": b.get("sixes", 0) or 0,
            })
    return batting


def _extract_bowling(innings_data):
    """Extract bowling records (with dots!) from all innings (<=2)."""
    bowling = []
    seen = set()
    for inning in innings_data:
        if inning.get("inningNumber", 99) > 2:
            continue
        for bw in inning.get("inningBowlers", []):
            player_obj = bw.get("player", {})
            player_name = player_obj.get("longName", "").strip()
            if not player_name or player_name in seen:
                continue
            seen.add(player_name)

            bowling.append({
                "player": player_name,
                "balls": bw.get("balls", 0) or 0,
                "maidens": bw.get("maidens", 0) or 0,
                "runs": bw.get("conceded", 0) or 0,
                "wickets": bw.get("wickets", 0) or 0,
                "dots": bw.get("dots", 0) or 0,
            })
    return bowling


def _extract_fielding(innings_data):
    """Extract fielding stats from structured inningWickets data.

    Returns dict: { player_name: { catches, runout, stumpings } }

    dismissalType codes (from Cricinfo):
        1 = caught, 4 = run out, 5 = stumped
    """
    fielding = {}

    def _ensure(name):
        if name and name not in fielding:
            fielding[name] = {"catches": 0, "runout": 0, "stumpings": 0}

    for inning in innings_data:
        if inning.get("inningNumber", 99) > 2:
            continue
        for w in inning.get("inningWickets", []):
            d_type = w.get("dismissalType")
            fielders = w.get("dismissalFielders", [])

            for f in fielders:
                player_obj = f.get("player")
                if not player_obj:
                    continue
                name = player_obj.get("longName", "").strip()
                if not name:
                    continue
                _ensure(name)

                if d_type == 1:          # caught
                    fielding[name]["catches"] += 1
                elif d_type == 4:        # run out
                    fielding[name]["runout"] += 1
                elif d_type == 5:        # stumped
                    fielding[name]["stumpings"] += 1

    return fielding


def _extract_man_of_the_match(content):
    """Extract Man of the Match from matchPlayerAwards."""
    awards = content.get("matchPlayerAwards", [])
    if awards:
        player = awards[0].get("player", {})
        return player.get("longName", "").strip() or None
    return None


def _extract_match_name(data):
    """Build a 'Team A vs Team B' string from match.teams."""
    teams = data.get("match", {}).get("teams", [])
    if len(teams) >= 2:
        long1 = teams[0].get("team", {}).get("longName", "?")
        long2 = teams[1].get("team", {}).get("longName", "?")
        return f"{long1} vs {long2}"
    title = data.get("match", {}).get("title", "")
    return title or None


def _extract_match_id(data):
    """Extract match ID from the data."""
    return str(data.get("match", {}).get("id", ""))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_match(scorecard_url):
    """Fetch match data from a Cricinfo scorecard URL.

    Returns (match_dict, match_name).
    """
    raw = _fetch_from_page(scorecard_url)
    return _process_raw(raw)


def scrape_from_file(json_path):
    """Load match data from a JSON file. Returns (match_dict, match_name)."""
    raw = _load_json_file(json_path)
    return _process_raw(raw)


def _process_raw(raw):
    """Process raw Cricinfo data into our match dict format."""
    content = raw.get("content", {})
    innings = content.get("innings", [])

    batting_records = _extract_batting(innings)
    bowling_records = _extract_bowling(innings)
    fielding = _extract_fielding(innings)
    man_of_the_match = _extract_man_of_the_match(content)
    match_name = _extract_match_name(raw)
    match_id = _extract_match_id(raw)

    out = {
        "match_id": match_id,
        "match_name": match_name or f"Match {match_id}",
        "batting": batting_records,
        "bowling": bowling_records,
        "fielding": fielding,
        "man_of_the_match": man_of_the_match,
    }

    print(f"\nScraped: {match_name or match_id}")
    print(f"  Batters: {len(batting_records)}, Bowlers: {len(bowling_records)}, "
          f"Fielders: {len(fielding)}")
    if man_of_the_match:
        print(f"  Man of the Match: {man_of_the_match}")
    else:
        print("  Man of the Match: (not found)")

    return out, match_name


def save_to_disk(match_data, match_id, vs_portion):
    """Save match JSON to match_results/ directory."""
    safe = re.sub(r'[<>:"/\\|?*]', "", vs_portion or "match").strip() or "match"
    os.makedirs(MATCH_RESULTS_DIR, exist_ok=True)
    filename = "{}_{}.json".format(safe, match_id)
    path = os.path.join(MATCH_RESULTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(match_data, f, indent=2, ensure_ascii=False)
    print(f"Saved to disk: {path}")
    return path


def save_to_mongo(tournament_id, match_data):
    """Save match JSON to MongoDB Atlas under a tournament."""
    from db import save_match
    save_match(tournament_id, match_data)
    print(f"Saved to MongoDB: tournament={tournament_id}, match_id={match_data['match_id']}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape a cricket match from ESPN Cricinfo and save to MongoDB / disk."
    )
    parser.add_argument("scorecard_url", nargs="?", default="",
                        help="ESPN Cricinfo full-scorecard URL")
    parser.add_argument("--tournament", required=True,
                        help="Tournament slug (e.g. wt20_2026)")
    parser.add_argument("--json-file", default="",
                        help="Path to a pre-downloaded Cricinfo JSON file")
    parser.add_argument("--local-only", action="store_true",
                        help="Save to disk only, skip MongoDB")
    parser.add_argument("--recalculate", action="store_true",
                        help="Recalculate fantasy points after saving")
    args = parser.parse_args()

    # Load from file or fetch from URL
    if args.json_file:
        if not os.path.isfile(args.json_file):
            print(f"Error: file not found: {args.json_file}", file=sys.stderr)
            sys.exit(1)
        match_data, vs_portion = scrape_from_file(args.json_file)
    elif args.scorecard_url:
        match_data, vs_portion = scrape_match(args.scorecard_url)
    else:
        print("Error: provide a scorecard URL or --json-file", file=sys.stderr)
        sys.exit(1)

    match_id = match_data["match_id"]

    # Always save to disk as backup
    save_to_disk(match_data, match_id, vs_portion)

    # Save to MongoDB unless --local-only
    if not args.local_only:
        try:
            save_to_mongo(args.tournament, match_data)
        except Exception as e:
            print(f"Warning: MongoDB save failed: {e}", file=sys.stderr)

    if args.recalculate:
        print("\nRecalculating fantasy points...")
        from calculate_points import recalculate_all
        recalculate_all(args.tournament)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
