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


def ranked_probability_score(y_true, proba):
    """Mean RPS over ordered outcomes L < D < W.

    RPS is the football-standard scoring rule: it squares the error between
    cumulative predicted and actual probabilities, so predicting a Draw when
    the result was a Win is penalized less than predicting a Loss — because
    Draw is 'closer' on the ordinal scale. Log-loss, by contrast, ignores
    that ordering. Lower is better; a perfect forecast scores 0.
    """
    proba = np.asarray(proba, dtype=float)
    cum_pred = np.cumsum(proba, axis=1)
    onehot = np.zeros_like(proba)
    onehot[np.arange(len(y_true)), np.asarray(y_true)] = 1.0
    cum_true = np.cumsum(onehot, axis=1)
    # divide by (categories - 1) so RPS stays in [0, 1]
    return float(np.mean(np.sum((cum_pred - cum_true) ** 2, axis=1)) / (proba.shape[1] - 1))


def score_model(model, rows):
    """Log-loss, accuracy and RPS of `model` on prepared home rows."""
    X = rows[feature_cols]
    y = rows['Result'].astype(int)
    proba = model.predict_proba(X)
    return (log_loss(y, proba, labels=[0, 1, 2]),
            accuracy_score(y, proba.argmax(1)),
            ranked_probability_score(y.to_numpy(), proba))


def odds_baseline(raw, rows):
    """Vig-removed implied probabilities from B365 odds for the same
    matches, ordered [L, D, W] from the home team's perspective."""
    key = rows[['Date', 'Team', 'Opponent']]
    odds = raw.merge(key, left_on=['Date', 'HomeTeam', 'AwayTeam'],
                     right_on=['Date', 'Team', 'Opponent'])
    odds = odds.dropna(subset=['B365H', 'B365D', 'B365A'])
    if odds.empty:
        return None, None, None
    inv = np.column_stack([1 / odds['B365A'], 1 / odds['B365D'], 1 / odds['B365H']])
    proba = inv / inv.sum(axis=1, keepdims=True)
    y = odds['FTR'].map({'A': 0, 'D': 1, 'H': 2}).astype(int)
    return (log_loss(y, proba, labels=[0, 1, 2]),
            accuracy_score(y, proba.argmax(1)),
            ranked_probability_score(y.to_numpy(), proba))


def _append_history(record):
    """Append one evaluation record to the history CSV, tolerant of schema
    changes: if new metric columns are added over time, older rows are
    reconciled by union of columns rather than silently misaligning."""
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    new = pd.DataFrame([record])
    if os.path.exists(HISTORY_PATH):
        old = pd.read_csv(HISTORY_PATH)
        combined = pd.concat([old, new], ignore_index=True)
    else:
        combined = new
    combined.to_csv(HISTORY_PATH, index=False)


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
    model_ll, model_acc, model_rps = score_model(model, rows)
    odds_ll, odds_acc, odds_rps = odds_baseline(raw, rows)

    record = {
        'run_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'window_days': window_days,
        'n_matches': len(rows),
        'first_match': rows['Date'].min().strftime('%Y-%m-%d'),
        'last_match': rows['Date'].max().strftime('%Y-%m-%d'),
        'model_logloss': round(model_ll, 4),
        'model_acc': round(model_acc, 4),
        'model_rps': round(model_rps, 4),
        'odds_logloss': round(odds_ll, 4) if odds_ll is not None else None,
        'odds_acc': round(odds_acc, 4) if odds_acc is not None else None,
        'odds_rps': round(odds_rps, 4) if odds_rps is not None else None,
    }

    _append_history(record)

    print(f"Evaluated {record['n_matches']} matches "
          f"({record['first_match']} ~ {record['last_match']})")
    print(f"  model: logloss={record['model_logloss']} "
          f"rps={record['model_rps']} acc={record['model_acc']}")
    print(f"  odds : logloss={record['odds_logloss']} "
          f"rps={record['odds_rps']} acc={record['odds_acc']}")
    return record


if __name__ == '__main__':
    main()
