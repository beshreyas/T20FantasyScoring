"""Build fielding stats (catches, runout, stumpings) from batting dismissals."""
import re


def resolve_player_name(short_name, all_player_names):
    """Resolve truncated name (e.g. Mohsin) to full roster name (e.g. Mohammad Mohsin)."""
    short_name = " ".join((short_name or "").split()).strip()
    if not short_name or not all_player_names:
        return short_name
    for full in all_player_names:
        if full == short_name:
            return full
    for full in all_player_names:
        if full.endswith(" " + short_name):
            return full
    for full in all_player_names:
        if short_name in full:
            return full
    return short_name


def build_fielding_from_batting(batting_records, batting_players, bowling_players):
    """Build fielding stats from batting dismissals.
    Key: player name, value: { catches, runout, stumpings }.
    batting_players and bowling_players are used to resolve truncated names in run outs.
    """
    fielding = {}
    roster = list(set((batting_players or []) + (bowling_players or [])))

    def normalize(name):
        return " ".join((name or "").split()).strip()

    def ensure_entry(name):
        n = normalize(name)
        if n and n not in fielding:
            fielding[n] = {"catches": 0, "runout": 0, "stumpings": 0}
        return normalize(name)

    def add_catch(name):
        n = ensure_entry(name)
        if n:
            fielding[n]["catches"] += 1

    def add_runout(name):
        n = resolve_player_name(name, roster)
        n = ensure_entry(n)
        if n:
            fielding[n]["runout"] += 1

    def add_stumping(name):
        n = ensure_entry(name)
        if n:
            fielding[n]["stumpings"] += 1

    for rec in batting_records:
        d = (rec.get("dismissal") or "").strip()

        if d.startswith("c "):
            if d.startswith("c and b "):
                add_catch(d[8:])  # "c and b " is 8 chars
            elif " b " in d:
                idx = d.find(" b ")
                if idx > 2:
                    add_catch(d[2:idx])

        if d.startswith("st ") and " b " in d:
            idx = d.find(" b ")
            if idx > 3:
                add_stumping(d[3:idx])

        if d.startswith("run out "):
            m = re.match(r"run out\s+\(([^)]+)\)", d)
            if m:
                inner = m.group(1).strip()
                for part in inner.split("/"):
                    add_runout(part.strip())

    return fielding
