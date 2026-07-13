"""Weekly evaluation job: score the deployed model on recently played
matches and compare it against the bookmaker-odds baseline.

Football gives real ground truth within days — every run appends one line
to metrics/history.csv so model quality is tracked over time. The odds
baseline (vig-removed implied probabilities from B365 prices) is the
market's forecast of the same matches: the gap between the two is the
single most honest health metric this project has.
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, accuracy_score
from src.preprocessor import load_and_clean
from src.train_model import feature_cols

HISTORY_PATH = 'metrics/history.csv'


def score_model(model, rows):
    """Log-loss and accuracy of `model` on prepared home-perspective rows."""
    X = rows[feature_cols]
    y = rows['Result'].astype(int)
    proba = model.predict_proba(X)
    return (log_loss(y, proba, labels=[0, 1, 2]),
            accuracy_score(y, proba.argmax(1)))


def odds_baseline(raw, rows):
    """Vig-removed implied probabilities from B365 odds for the same
    matches, ordered [L, D, W] from the home team's perspective."""
    key = rows[['Date', 'Team', 'Opponent']]
    odds = raw.merge(key, left_on=['Date', 'HomeTeam', 'AwayTeam'],
                     right_on=['Date', 'Team', 'Opponent'])
    odds = odds.dropna(subset=['B365H', 'B365D', 'B365A'])
    if odds.empty:
        return None, None
    inv = np.column_stack([1 / odds['B365A'], 1 / odds['B365D'], 1 / odds['B365H']])
    proba = inv / inv.sum(axis=1, keepdims=True)
    y = odds['FTR'].map({'A': 0, 'D': 1, 'H': 2}).astype(int)
    return (log_loss(y, proba, labels=[0, 1, 2]),
            accuracy_score(y, proba.argmax(1)))


def evaluation_rows(df, window_days):
    """Home-perspective rows of matches played in the last `window_days`
    (one row per match, so metrics count each fixture once)."""
    since = pd.Timestamp.now().normalize() - pd.Timedelta(days=window_days)
    return df[(df['is_home'] == 1) & (df['Date'] >= since)].dropna(
        subset=feature_cols + ['Result'])


def main(window_days=60, model_path='premier_model.pkl',
         data_path='data/matches.csv'):
    df = load_and_clean(data_path)
    raw = pd.read_csv(data_path, parse_dates=['Date'])

    rows = evaluation_rows(df, window_days)
    if rows.empty:
        print(f'No matches played in the last {window_days} days — '
              'off-season, nothing to evaluate.')
        return None

    model = joblib.load(model_path)
    model_ll, model_acc = score_model(model, rows)
    odds_ll, odds_acc = odds_baseline(raw, rows)

    record = {
        'run_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'window_days': window_days,
        'n_matches': len(rows),
        'first_match': rows['Date'].min().strftime('%Y-%m-%d'),
        'last_match': rows['Date'].max().strftime('%Y-%m-%d'),
        'model_logloss': round(model_ll, 4),
        'model_acc': round(model_acc, 4),
        'odds_logloss': round(odds_ll, 4) if odds_ll is not None else None,
        'odds_acc': round(odds_acc, 4) if odds_acc is not None else None,
    }

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    pd.DataFrame([record]).to_csv(
        HISTORY_PATH, mode='a', index=False,
        header=not os.path.exists(HISTORY_PATH))

    print(f"Evaluated {record['n_matches']} matches "
          f"({record['first_match']} ~ {record['last_match']})")
    print(f"  model: logloss={record['model_logloss']} acc={record['model_acc']}")
    print(f"  odds : logloss={record['odds_logloss']} acc={record['odds_acc']}")
    return record


if __name__ == '__main__':
    main()
