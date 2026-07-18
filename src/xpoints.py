"""Expected Points (xPoints) table.

For every match in a season, the model's pre-match probabilities give each
team an expected points value (xP = P(win)*3 + P(draw)*1), while the actual
result gives real points. Summing per team across the season produces an
xPoints league table: who is over- or under-performing what the model
expected. This is real, computed data — not a placeholder.

The heavy lifting (feature engineering, the trained model) is reused from
src.infer, so this module only aggregates.
"""
from functools import lru_cache

import numpy as np
import pandas as pd
from src.infer import _MODEL, _DF
from src.train_model import feature_cols

_POINTS = np.array([0.0, 1.0, 3.0])  # index by result code: L, D, W


def _season_home_rows(season=None):
    """One row per match (home perspective) with features present.
    Defaults to the most recent season in the data."""
    rows = _DF[(_DF['is_home'] == 1)].dropna(subset=feature_cols + ['Result'])
    if season is None:
        season = sorted(rows['Season'].unique())[-1]
    return rows[rows['Season'] == season], season


# Both outputs depend only on _MODEL and _DF, which are loaded once at import
# and never change while the process runs — so cache the (expensive) batch
# prediction instead of recomputing it on every request.
@lru_cache(maxsize=4)
def compute_xpoints(season=None):
    """Return the xPoints table for `season` (most recent by default) as a
    list of dicts sorted by actual points desc:
    [{team, played, points, xpoints, diff}, ...]."""
    rows, season = _season_home_rows(season)
    if rows.empty:
        return [], season

    # Batch-predict all home-perspective matches at once.
    proba = _MODEL.predict_proba(rows[feature_cols])  # columns: [L, D, W]
    home_xp = proba @ _POINTS
    away_xp = proba[:, ::-1] @ _POINTS  # away sees the mirrored outcome

    home_result = rows['Result'].astype(int).to_numpy()
    home_pts = _POINTS[home_result]
    away_pts = _POINTS[2 - home_result]

    agg = {}  # team -> [played, points, xpoints]
    for i, row in enumerate(rows.itertuples()):
        for team, pts, xp in ((row.Team, home_pts[i], home_xp[i]),
                              (row.Opponent, away_pts[i], away_xp[i])):
            a = agg.setdefault(team, [0, 0.0, 0.0])
            a[0] += 1
            a[1] += pts
            a[2] += xp

    table = [{
        'team': team,
        'played': v[0],
        'points': int(round(v[1])),
        'xpoints': round(v[2], 1),
        'diff': round(v[1] - v[2], 1),
    } for team, v in agg.items()]
    table.sort(key=lambda r: (-r['points'], -r['xpoints']))
    return table, season


@lru_cache(maxsize=1)
def recent_predictions(n=6):
    """Model predictions on the most recent played matches, checked against
    the actual result — the 'hit' flag is real, not fabricated. Cached like
    compute_xpoints since it depends only on the model and data."""
    rows, _ = _season_home_rows()
    if rows.empty:
        return []
    rows = rows.sort_values('Date').tail(n)
    proba = _MODEL.predict_proba(rows[feature_cols])  # [L, D, W] for home

    out = []
    for i, r in enumerate(rows.itertuples()):
        pick_idx = int(proba[i].argmax())
        actual = int(r.Result)  # 0=L, 1=D, 2=W from home perspective
        pick_name = (r.Team + ' Win' if pick_idx == 2
                     else r.Opponent + ' Win' if pick_idx == 0 else 'Draw')
        out.append({
            'date': r.Date.strftime('%b %d'),
            'home': r.Team, 'away': r.Opponent,
            'pick': pick_name,
            'conf': int(round(proba[i][pick_idx] * 100)),
            'score': f"{int(r.GF)}-{int(r.GA)}",
            'hit': pick_idx == actual,
        })
    return list(reversed(out))


if __name__ == '__main__':
    table, season = compute_xpoints()
    print(f"xPoints table — {season}")
    print(f"{'Team':<22}{'Pld':>4}{'Pts':>5}{'xPts':>7}{'Diff':>7}")
    for r in table:
        print(f"{r['team']:<22}{r['played']:>4}{r['points']:>5}"
              f"{r['xpoints']:>7}{r['diff']:>+7}")
