#!/usr/bin/env python3
"""Auto-scrape agent for T20 Fantasy Hub.

Checks the Cricinfo series results page for new completed matches
and automatically imports any that haven't been scored yet.

Usage:
    python auto_scrape.py                  # Check all tournaments with a series_url
    python auto_scrape.py --tournament X   # Check a specific tournament only

Designed to be called by APScheduler at 00:15 IST daily from main.py,
but can also run standalone.
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def _fetch_series_results(series_url):
    """Fetch the Cricinfo series results page and return match list.

    Returns a list of match dicts with: id, slug, status, teams, series info.
    """
    from curl_cffi import requests as cffi_requests

    print(f"  Fetching series results: {series_url}")
    resp = cffi_requests.get(series_url, impersonate="chrome", timeout=30)
    resp.raise_for_status()

    html = resp.text
    if "__NEXT_DATA__" not in html:
        raise RuntimeError("No __NEXT_DATA__ found in series results page")

    marker = "__NEXT_DATA__"
    marker_pos = html.find(marker)
    script_start = html.rfind("<script", 0, marker_pos)
    content_start = html.find(">", script_start) + 1
    content_end = html.find("</script>", content_start)
    next_data = json.loads(html[content_start:content_end])

    data = next_data.get("props", {}).get("appPageProps", {}).get("data", {})
    series = data.get("series", {})
    matches = data.get("content", {}).get("matches", [])

    return matches, series


def _build_scorecard_url(series, match):
    """Build the full scorecard URL for a match."""
    series_slug = series.get("slug", "")
    series_id = series.get("objectId", series.get("id", ""))
    match_slug = match.get("slug", "")
    match_id = match.get("objectId", match.get("id", ""))
    return (
        f"https://www.espncricinfo.com/series/"
        f"{series_slug}-{series_id}/"
        f"{match_slug}-{match_id}/full-scorecard"
    )


def _get_match_label(match):
    """Build a human-readable label for logging."""
    teams = match.get("teams", [])
    if len(teams) >= 2:
        t1 = teams[0].get("team", {}).get("abbreviation", "?")
        t2 = teams[1].get("team", {}).get("abbreviation", "?")
        return f"{t1} vs {t2} ({match.get('title', '')})"
    return match.get("title", f"Match {match.get('objectId', '?')}")


def check_tournament(tournament_id, series_url):
    """Check a single tournament for new completed matches.

    Returns a dict with: checked, new_matches, errors.
    """
    from db import get_match, save_match
    from scrape_match import scrape_match
    from calculate_points import recalculate_all

    result = {
        "tournament_id": tournament_id,
        "series_url": series_url,
        "checked_at": datetime.utcnow().isoformat(),
        "total_completed": 0,
        "already_scored": 0,
        "new_matches": [],
        "errors": [],
    }

    try:
        matches, series = _fetch_series_results(series_url)
    except Exception as e:
        result["errors"].append(f"Failed to fetch series results: {e}")
        print(f"  ❌ {result['errors'][-1]}")
        return result

    # Filter to completed matches only
    completed = [m for m in matches if m.get("status") == "RESULT"]
    result["total_completed"] = len(completed)
    print(f"  Found {len(completed)} completed matches in series")

    new_count = 0
    for match in completed:
        match_id = str(match.get("objectId", match.get("id", "")))
        if not match_id:
            continue

        # Check if already in MongoDB
        existing = get_match(tournament_id, match_id)
        if existing:
            result["already_scored"] += 1
            continue

        # New match — scrape it
        label = _get_match_label(match)
        scorecard_url = _build_scorecard_url(series, match)
        print(f"  🆕 New match: {label} (ID: {match_id})")

        try:
            match_data, vs_portion = scrape_match(scorecard_url)
            # Ensure the match_id matches what the series page reports
            match_data["match_id"] = match_id
            save_match(tournament_id, match_data)
            result["new_matches"].append({
                "match_id": match_id,
                "match_name": match_data.get("match_name", label),
            })
            new_count += 1
            print(f"    ✅ Scraped and saved: {match_data.get('match_name', label)}")
        except Exception as e:
            err = f"Failed to scrape {label} (ID: {match_id}): {e}"
            result["errors"].append(err)
            print(f"    ❌ {err}")

    # Recalculate if we added any new matches
    if new_count > 0:
        print(f"  Recalculating fantasy points for {tournament_id}...")
        try:
            recalculate_all(tournament_id)
            print(f"  ✅ Recalculated")
        except Exception as e:
            err = f"Recalculate failed: {e}"
            result["errors"].append(err)
            print(f"  ❌ {err}")

    print(f"  Done: {new_count} new, {result['already_scored']} existing, "
          f"{len(result['errors'])} errors")
    return result


def check_all_tournaments():
    """Check all tournaments that have a series_url configured.

    Returns a list of result dicts.
    """
    from db import list_tournaments, get_tournament

    print(f"\n{'='*60}")
    print(f"Auto-scrape run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    tournaments = list_tournaments()
    results = []

    for t in tournaments:
        tid = t["tournament_id"]
        # Get full tournament doc to check for series_url
        full = get_tournament(tid)
        series_url = (full or {}).get("series_url", "")

        if not series_url:
            print(f"\n⏭  {t.get('name', tid)}: no series_url configured, skipping")
            continue

        print(f"\n🔍 Checking: {t.get('name', tid)} ({tid})")
        result = check_tournament(tid, series_url)
        results.append(result)

    total_new = sum(len(r["new_matches"]) for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    print(f"\n{'='*60}")
    print(f"Summary: {len(results)} tournaments checked, "
          f"{total_new} new matches imported, {total_errors} errors")
    print(f"{'='*60}\n")

    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Auto-scrape new matches from Cricinfo")
    parser.add_argument("--tournament", default="",
                        help="Check only this tournament (slug)")
    args = parser.parse_args()

    if args.tournament:
        from db import get_tournament
        t = get_tournament(args.tournament)
        if not t:
            print(f"Tournament not found: {args.tournament}", file=sys.stderr)
            sys.exit(1)
        series_url = t.get("series_url", "")
        if not series_url:
            print(f"No series_url set for {args.tournament}", file=sys.stderr)
            sys.exit(1)
        print(f"🔍 Checking: {t.get('name', args.tournament)}")
        result = check_tournament(args.tournament, series_url)
        print(json.dumps(result, indent=2))
    else:
        results = check_all_tournaments()
        for r in results:
            if r["new_matches"]:
                print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
