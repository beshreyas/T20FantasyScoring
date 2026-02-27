"""Fantasy scoring functions ported from fipl's calculate_points.ts.

Every function is pure (no file I/O) and works on the match-result dicts
already produced by the WT20 scraper (batting.py, bowling.py, fielding.py).
"""

import math


# ---------------------------------------------------------------------------
# Batting
# ---------------------------------------------------------------------------

def calculate_batting_points(record):
    """Calculate batting points for a single batting record dict.

    Formula (from fipl):
        runs + (fours * 2) + (sixes * 3)
        + floor(runs / 25) * 10              # milestone bonus every 25 runs
        + (runs - balls)                      # strike-rate bonus / penalty
        - 10 if duck (0 runs & out)
    """
    runs  = record.get("runs", 0)
    balls = record.get("balls", 0)
    fours = record.get("fours", 0)
    sixes = record.get("sixes", 0)
    dismissal = record.get("dismissal", "")

    duck_penalty = -10 if (runs == 0 and dismissal and "not out" not in dismissal.lower()) else 0

    runs_pts      = runs
    boundary_pts  = (fours * 2) + (sixes * 3)
    milestone_pts = math.floor(runs / 25) * 10
    sr_pts        = runs - balls

    return runs_pts + boundary_pts + milestone_pts + sr_pts + duck_penalty


# ---------------------------------------------------------------------------
# Bowling
# ---------------------------------------------------------------------------

def calculate_bowling_points(record):
    """Calculate bowling points for a single bowling record dict.

    Formula (from fipl):
        wickets * 25
        + maidens * 10
        + (overs * 12 - runs_conceded)        # economy bonus
        + dots * 1                             # dot-ball bonus
        + milestone bonuses (3W +25, 5W +50, 7W +100  – cumulative)
    """
    balls   = record.get("balls", 0)
    if balls == 0:
        return 0

    maidens = record.get("maidens", 0)
    runs    = record.get("runs", 0)
    wickets = record.get("wickets", 0)
    dots    = record.get("dots", 0)

    overs = balls / 6.0

    wicket_pts  = wickets * 25
    maiden_pts  = maidens * 10
    economy_pts = (overs * 12) - runs
    dot_pts     = dots * 1

    bonus = 0
    if wickets >= 7:
        bonus = 25 + 50 + 100          # 3-fer + 5-fer + 7-fer
    elif wickets >= 5:
        bonus = 25 + 50                # 3-fer + 5-fer
    elif wickets >= 3:
        bonus = 25                     # 3-fer

    return wicket_pts + maiden_pts + economy_pts + dot_pts + bonus


# ---------------------------------------------------------------------------
# Fielding
# ---------------------------------------------------------------------------

def calculate_fielding_points(fielding_entry):
    """Calculate fielding points for a single player's fielding dict.

    Points (from fipl):
        catch   = 15
        runout  = 10  (already counted per involvement in fielding.py)
        stumping = 10
    """
    catches   = fielding_entry.get("catches", 0)
    runout    = fielding_entry.get("runout", 0)
    stumpings = fielding_entry.get("stumpings", 0)

    return (catches * 15) + (runout * 10) + (stumpings * 10)


# ---------------------------------------------------------------------------
# Man of the Match
# ---------------------------------------------------------------------------

MOM_BONUS = 25
