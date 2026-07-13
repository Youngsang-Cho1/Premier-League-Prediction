import joblib
import numpy as np
import pandas as pd
from src.preprocessor import load_and_clean
from src.train_model import feature_cols

# Loaded once at import — reprocessing the CSV per request added seconds of
# latency and the data only changes when the model is retrained.
_MODEL = joblib.load('premier_model.pkl')
_DF = load_and_clean('data/matches.csv')

_TEAMS = set(_DF['Team'].unique())

# Neutral h2h prior: Result is encoded 0=L, 1=D, 2=W, matching the
# fillna(1.0) used in training for pairs with no meeting history.
_NEUTRAL_H2H = 1.0

# Rest days are unknown for a hypothetical fixture; assume a normal week
# for both sides.
_DEFAULT_DAYS_REST = 7.0

_RESULT_LETTER = {2: 'W', 1: 'D', 0: 'L'}


def _validate_team(name):
    if name not in _TEAMS:
        raise ValueError(f"Unknown team: {name}")


def _team_snapshot(team, is_home):
    """Current pre-match state of a team, aggregated directly over its most
    recent matches (training features are shift(1) rollings, so the freshest
    equivalent for a FUTURE fixture includes the team's latest result)."""
    rows = _DF[_DF['Team'] == team].sort_values('Date')
    if len(rows) < 5:
        raise ValueError(f"Not enough match history for {team}")

    last5 = rows.tail(5)
    snap = {
        'Recent_GF_avg5': last5['GF'].mean(),
        'Recent_GA_avg5': last5['GA'].mean(),
        'Recent_SoT_avg5': last5['SoT'].mean(),
        'Recent_SoTA_avg5': last5['SoTA'].mean(),
        'Recent_Result_avg5': last5['Result'].mean(),
        'Recent_Result_avg20': rows.tail(20)['Result'].mean(),
        'elo': rows.iloc[-1]['elo_post'],
    }

    venue_last5 = rows[rows['is_home'] == is_home].tail(5)
    snap['Recent_Result_venue_avg5'] = (
        venue_last5['Result'].mean() if len(venue_last5) >= 3
        else snap['Recent_Result_avg5']
    )

    denom = snap['Recent_SoT_avg5'] + snap['Recent_SoTA_avg5']
    snap['SoT_ratio5'] = snap['Recent_SoT_avg5'] / denom if denom > 0 else 0.5
    return snap


def _h2h_record(team, opponent):
    """Mean of the last two head-to-head results from `team`'s perspective,
    mirroring the shift(1).rolling(2) feature used in training."""
    results = (
        _DF[(_DF['Team'] == team) & (_DF['Opponent'] == opponent)]
        .sort_values('Date')['Result']
    )
    if len(results) < 2:
        return _NEUTRAL_H2H
    return results.tail(2).mean()


def predict_matches(team, opponent, is_home):
    """Predict `team`'s result against `opponent`, with `team` at home when
    is_home=1. The feature vector is assembled explicitly for this matchup
    from both sides' current snapshots."""
    _validate_team(team)
    _validate_team(opponent)

    own = _team_snapshot(team, is_home)
    opp = _team_snapshot(opponent, 1 - is_home)

    own_cols = ['Recent_GF_avg5', 'Recent_GA_avg5', 'Recent_SoT_avg5',
                'Recent_SoTA_avg5', 'Recent_Result_avg5', 'Recent_Result_avg20',
                'Recent_Result_venue_avg5', 'SoT_ratio5']
    features = {col: own[col] for col in own_cols}
    features.update({f'opp_{col}': opp[col] for col in own_cols})
    features['is_home'] = is_home
    features['days_rest'] = _DEFAULT_DAYS_REST
    features['rest_diff'] = 0.0
    features['elo_diff'] = own['elo'] - opp['elo']
    features['h2h_record'] = _h2h_record(team, opponent)

    X = pd.DataFrame([features], columns=feature_cols, dtype=float)
    if np.isnan(X.to_numpy()).any():
        raise ValueError(f"Not enough recent match history for {team} or {opponent}")

    return _MODEL.predict_proba(X)[0]


def predict_matches_bidirectional(team1, team2):
    """Predict team1 (home) vs team2 (away) by averaging the same fixture
    seen from both teams' perspectives. Probabilities are ordered
    [Lose, Draw, Win] for team1."""
    proba_home = predict_matches(team1, team2, is_home=1)
    proba_away = predict_matches(team2, team1, is_home=0)

    avg_proba = (proba_home + proba_away[::-1]) / 2
    final_pred = int(avg_proba.argmax())

    return final_pred, avg_proba


def get_matchup_insights(team1, team2):
    """Historical H2H summary from team1's perspective, computed on the
    preprocessed dataframe so team names are consistent."""
    h2h = (
        _DF[(_DF['Team'] == team1) & (_DF['Opponent'] == team2)]
        .sort_values('Date', ascending=False)
    )

    if h2h.empty:
        return {"draw_rate": "0%", "count": 0, "history": []}

    draw_rate = f"{(h2h['Result'] == 1).mean() * 100:.1f}%"

    history = []
    for _, row in h2h.head(5).iterrows():
        history.append({
            "date": row['Date'].strftime('%Y-%m-%d'),
            "result": _RESULT_LETTER[int(row['Result'])],
            "score": f"{int(row['GF'])}-{int(row['GA'])}",
            "opponent": team2,
        })

    return {
        "draw_rate": draw_rate,
        "count": len(h2h),
        "history": history,
    }
