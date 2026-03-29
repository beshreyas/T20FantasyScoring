# Fantasy Cricket Scoring System

This document outlines the point calculation rules used for fantasy scoring, based on `scoring.py` ported from `fipl`'s `calculate_points.ts`.

## Batting Points

| Action / Event | Points awarded | Description |
| :--- | :---: | :--- |
| **Every Run** | 1 | Base run points. |
| **Every Boundary Hit (Four)** | 2 | Bonus points for each boundary (total 6 pts per four). |
| **Every Six Hit** | 3 | Bonus points for each six (total 9 pts per six). |
| **Milestone Bonus** | 10 | Awarded for every 25 runs scored (25, 50, 75, 100, etc). |
| **Strike Rate Bonus/Penalty**| (Runs - Balls) | Difference between runs scored and balls faced. Can be positive or negative. |
| **Duck Penalty** | -10 | Deducted if a player gets out for exactly 0 runs. |

## Bowling Points

| Action / Event | Points awarded | Description |
| :--- | :---: | :--- |
| **Every Wicket** | 25 | Standard wicket points. |
| **Maiden Over** | 15 | Bonus points per maiden over bowled. |
| **Economy Rate Bonus** | (Overs × 12) - Runs | Bonus points factoring over-to-run difference. |
| **Every Dot Ball** | 1 | Bonus points for dot deliveries. |
| **3-Wicket Haul** | 25 | Milestone bonus points for taking 3 or 4 wickets. |
| **5-Wicket Haul** | 50 | Cumulative milestone (Total 75 points for taking 5-6 wickets). |
| **7-Wicket Haul** | 100 | Cumulative milestone (Total 175 points for taking 7+ wickets). |

## Fielding Points

| Action / Event | Points awarded | Description |
| :--- | :---: | :--- |
| **Catch** | 15 | Points per catch taken. |
| **Run Out** | 10 | Points per run out involvement. |
| **Stumping** | 10 | Points per stumping. |

## Other Points

| Action / Event | Points awarded | Description |
| :--- | :---: | :--- |
| **Man of the Match** | 25 | Bonus points for winning the Man of the Match award. |
