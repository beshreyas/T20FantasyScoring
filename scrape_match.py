#!/usr/bin/env python3
"""Standalone CLI scraper for cricket matches.

Usage:
    python scrape_match.py <match_id> --tournament <slug> [--cricinfo-url <url>] [--local-only]

Examples:
    python scrape_match.py 139437 --tournament wt20_2026 --cricinfo-url "https://..."
    python scrape_match.py 139437 --tournament wt20_2026 --local-only
"""

import argparse
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

from batting import parse_batting
from bowling import parse_bowling
from fielding import build_fielding_from_batting
from cricinfo_dots import get_dots_by_bowler_cricinfo
from cricinfo_mom import get_man_of_the_match

MATCH_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "match_results")


def _match_title_vs_portion(soup):
    """Extract 'Team A vs Team B' from page title."""
    title_el = soup.find("title") or soup.find("h1")
    if not title_el:
        return None
    raw = title_el.get_text(strip=True)
    if " - Scorecard" in raw:
        raw = raw.replace(" - Scorecard", "").strip()
    if " | " in raw:
        raw = raw.split(" | ", 1)[-1].strip()
    if "," in raw:
        raw = raw.split(",")[0].strip()
    if " vs " in raw:
        return raw
    return None


def scrape_match(match_id, cricinfo_url=None):
    """Scrape a match from Cricbuzz (+ optional ESPNcricinfo) and return dict."""
    url = "https://www.cricbuzz.com/live-cricket-scorecard/{}/".format(match_id)
    print(f"Fetching Cricbuzz scorecard: {url}")

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    batting_records = parse_batting(soup)
    bowling_records = parse_bowling(soup)

    dots_by_bowler = {}
    man_of_the_match = None
    if cricinfo_url and "/full-scorecard" in cricinfo_url:
        print(f"Fetching ESPNcricinfo dots: {cricinfo_url}")
        dots_by_bowler = get_dots_by_bowler_cricinfo(cricinfo_url)
        print(f"  Found dots for {len(dots_by_bowler)} bowlers")
        print("Fetching Man of the Match...")
        man_of_the_match = get_man_of_the_match(cricinfo_url)
        print(f"  MoM: {man_of_the_match or '(not found)'}")
    else:
        print("No cricinfo_url provided — skipping dots and MoM")

    for record in bowling_records:
        record["dots"] = dots_by_bowler.get(record["player"], 0)

    batting_players = [r["player"] for r in batting_records if r.get("player")]
    bowling_players = [r["player"] for r in bowling_records if r.get("player")]
    fielding = build_fielding_from_batting(
        batting_records, batting_players, bowling_players
    )

    vs_portion = _match_title_vs_portion(soup)

    out = {
        "match_id": str(match_id),
        "match_name": vs_portion or "Match {}".format(match_id),
        "batting": batting_records,
        "bowling": bowling_records,
        "fielding": fielding,
        "scorecard_url": url,
        "man_of_the_match": man_of_the_match,
        "cricinfo_url": cricinfo_url or None,
    }

    print(f"\nScraped: {vs_portion or match_id}")
    print(f"  Batters: {len(batting_records)}, Bowlers: {len(bowling_records)}, "
          f"Fielders: {len(fielding)}")

    return out, vs_portion


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
        description="Scrape a cricket match and save to MongoDB / disk."
    )
    parser.add_argument("match_id", help="Cricbuzz match ID (numeric)")
    parser.add_argument("--tournament", required=True,
                        help="Tournament slug (e.g. wt20_2026)")
    parser.add_argument("--cricinfo-url", default="",
                        help="ESPNcricinfo full-scorecard URL for dots & MoM")
    parser.add_argument("--local-only", action="store_true",
                        help="Save to disk only, skip MongoDB")
    parser.add_argument("--recalculate", action="store_true",
                        help="Recalculate fantasy points after saving")
    args = parser.parse_args()

    if not args.match_id.isdigit():
        print("Error: match_id must be numeric", file=sys.stderr)
        sys.exit(1)

    match_data, vs_portion = scrape_match(args.match_id, args.cricinfo_url or None)

    # Always save to disk as backup
    save_to_disk(match_data, args.match_id, vs_portion)

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
