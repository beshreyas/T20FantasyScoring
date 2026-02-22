"""Parse bowling stats from Cricbuzz scorecard page."""
import re


def parse_bowling(soup):
    """Parse bowling from Cricbuzz grid divs (scorecard-bowl-grid).
    Returns list of dicts: player, balls, maidens, runs, wickets.
    Overs are converted to balls (e.g. 4 -> 24, 2.3 -> 15).
    Deduplicates by player name (page often repeats sections for responsive layout).
    """
    bowling = []
    seen_players = set()

    for div in soup.find_all("div", class_=lambda c: c and "scorecard-bowl-grid" in str(c)):
        profile_link = div.find("a", href=re.compile(r"/profiles/"))
        if not profile_link:
            continue
        player_name = profile_link.get_text(strip=True)
        player_name = re.sub(r"\s*\(c\)\s*", " ", player_name, flags=re.IGNORECASE)
        player_name = re.sub(r"\s*\(wk\)\s*", " ", player_name, flags=re.IGNORECASE)
        player_name = " ".join(player_name.split())
        if not player_name or player_name.upper() == "BOWLER":
            continue
        if player_name in seen_players:
            continue
        seen_players.add(player_name)

        number_divs = div.find_all(
            "div",
            class_=lambda c: c and "justify-center" in str(c) and "items-center" in str(c),
        )
        values = []
        for d in number_divs:
            t = d.get_text(strip=True)
            if t.isdigit():
                values.append(int(t))
            elif t.replace(".", "").isdigit() and "." in t:
                values.append(float(t))
            if len(values) >= 4:
                break
        if len(values) < 4:
            continue

        overs_val = float(values[0])
        maidens = values[1] if len(values) > 1 else 0
        runs = values[2] if len(values) > 2 else 0
        wickets = values[3] if len(values) > 3 else 0

        whole_overs = int(overs_val)
        fraction = overs_val - whole_overs
        balls_bowled = whole_overs * 6 + int(round(fraction * 10))

        bowling.append({
            "player": player_name,
            "balls": balls_bowled,
            "maidens": maidens,
            "runs": runs,
            "wickets": wickets,
        })

    return bowling
