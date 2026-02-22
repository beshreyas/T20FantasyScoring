"""Parse batting stats from Cricbuzz scorecard page."""
import re


def parse_batting(soup):
    """Parse batting from Cricbuzz grid divs (scorecard-bat-grid).
    Returns list of dicts: player, dismissal, runs, balls, fours, sixes.
    Deduplicates by player name (page often repeats sections for responsive layout).
    """
    batting = []
    seen_players = set()

    for div in soup.find_all("div", class_=lambda c: c and "scorecard-bat-grid" in str(c)):
        profile_link = div.find("a", href=re.compile(r"/profiles/"))
        if not profile_link:
            continue
        player_name = profile_link.get_text(strip=True)
        player_name = re.sub(r"\s*\(c\)\s*", " ", player_name, flags=re.IGNORECASE)
        player_name = re.sub(r"\s*\(wk\)\s*", " ", player_name, flags=re.IGNORECASE)
        player_name = " ".join(player_name.split())
        if not player_name or player_name.upper() in ("EXTRAS", "TOTAL"):
            continue
        if player_name in seen_players:
            continue
        seen_players.add(player_name)

        dismissal_el = div.find("div", class_=lambda c: c and "text-cbTxtSec" in str(c))
        dismissal = dismissal_el.get_text(strip=True) if dismissal_el else ""

        number_divs = div.find_all(
            "div",
            class_=lambda c: c and "justify-center" in str(c) and "items-center" in str(c),
        )
        numeric_texts = []
        for d in number_divs:
            t = d.get_text(strip=True)
            if t.isdigit():
                numeric_texts.append(t)
        runs = balls = fours = sixes = 0
        if len(numeric_texts) >= 4:
            runs = int(numeric_texts[0])
            balls = int(numeric_texts[1])
            fours = int(numeric_texts[2])
            sixes = int(numeric_texts[3])

        batting.append({
            "player": player_name,
            "dismissal": dismissal,
            "runs": runs,
            "balls": balls,
            "fours": fours,
            "sixes": sixes,
        })

    return batting
