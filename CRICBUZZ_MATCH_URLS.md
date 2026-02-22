# Cricbuzz completed match URL structure

The **match ID** is the single parameter you need to fetch any completed (or live) game. Same ID works for both commentary and scorecard.

## URL pattern

| Page       | URL pattern                                                  | Use case                          |
|-----------|---------------------------------------------------------------|-----------------------------------|
| **Commentary** | `https://www.cricbuzz.com/live-cricket-scores/<match_id>/`   | Result, summary, ball-by-ball, PoTM |
| **Scorecard**  | `https://www.cricbuzz.com/live-cricket-scorecard/<match_id>/`| Batting & bowling tables, FoW, match info |

- **Path difference:** `live-cricket-scores` (commentary) vs `live-cricket-scorecard` (scorecard).
- **Match ID:** Numeric only (e.g. `139373`). Trailing slash is optional; slug after the ID is optional (SEO only).
- **Reuse:** For any tournament or series, once you have the list of match IDs, you can request any game with  
  `https://www.cricbuzz.com/live-cricket-scorecard/<id>/` or  
  `https://www.cricbuzz.com/live-cricket-scores/<id>/`.

## Example

- First completed game: [https://www.cricbuzz.com/live-cricket-scores/139373/](https://www.cricbuzz.com/live-cricket-scores/139373/)
- Same game, scorecard: [https://www.cricbuzz.com/live-cricket-scorecard/139373/](https://www.cricbuzz.com/live-cricket-scorecard/139373/)

So for match ID `139373` you get:
- **Commentary:** result (“England won by 51 runs”), team scores (ENG 146/9, SL 95), Player of the Match, full commentary.
- **Scorecard:** match title, result, team totals, batting table (Batter, R, B, 4s, 6s, SR, dismissal), bowling table (Bowler, O, M, R, W, ECO), fall of wickets, match info (series, venue, toss, umpires).

## API usage (this repo)

- **`GET /match/<match_id>`** — Fetches the scorecard URL and returns JSON:
  - `match_id`, `match_title`, `result` (e.g. "England won by 51 runs")
  - `team_scores`: `[{ "team": "ENG", "score": "146-9 (20 Ov)" }, ...]`
  - `batting`: list of `{ "player", "runs", "balls", "fours", "sixes" }`
  - `bowling`: list of `{ "player", "overs", "maidens", "runs", "wickets" }`
  - `scorecard_url`
  - Example: `GET /match/139373`
