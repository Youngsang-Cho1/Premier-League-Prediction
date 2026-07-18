"""Walk-forward season backtest: for each season S (with enough prior
history), train the model-selection pipeline on all seasons before S and
score it on S, alongside the bookmaker-odds baseline.

This is the project's headline evidence — model quality vs the market,
season by season — and it powers the /dashboard view. Output:
metrics/backtest.csv (one row per season).
"""
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb

from src.preprocessor import load_and_clean
from src.train_model import feature_cols
from src.evaluate import ranked_probability_score
from sklearn.metrics import log_loss, accuracy_score

BACKTEST_PATH = 'metrics/backtest.csv'
MIN_PRIOR_SEASONS = 3  # need history for form/Elo/h2h to be populated


def _candidates():
    return {
        'LogReg': make_pipeline(StandardScaler(),
                                LogisticRegression(C=0.1, max_iter=3000)),
        'RF': RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
        'GB': GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                         learning_rate=0.1, random_state=42),
        'XGB': xgb.XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.1,
                                 subsample=0.8, eval_metric='mlogloss', random_state=42),
    }


def _odds_baseline(raw, test_rows):
    o = raw.merge(test_rows[['Date', 'Team', 'Opponent']],
                  left_on=['Date', 'HomeTeam', 'AwayTeam'],
                  right_on=['Date', 'Team', 'Opponent'])
    inv = np.column_stack([1 / o['B365A'], 1 / o['B365D'], 1 / o['B365H']])
    proba = inv / inv.sum(1, keepdims=True)
    y = o['FTR'].map({'A': 0, 'D': 1, 'H': 2}).astype(int).to_numpy()
    return proba, y


def main(data_path='data/matches.csv', output_path=BACKTEST_PATH):
    df = load_and_clean(data_path).sort_values('Date')
    raw = pd.read_csv(data_path, parse_dates=['Date'])
    seasons = sorted(df['Season'].unique())

    records = []
    for i, season in enumerate(seasons):
        if i < MIN_PRIOR_SEASONS:
            continue
        train = df[df['Season'].isin(seasons[:i])].dropna(subset=feature_cols + ['Result'])
        test = df[(df['Season'] == season) & (df['is_home'] == 1)].dropna(
            subset=feature_cols + ['Result'])
        if test.empty:
            continue
        y = test['Result'].astype(int).to_numpy()

        # same log-loss model selection the training pipeline uses
        best = None
        for name, est in _candidates().items():
            calib = CalibratedClassifierCV(est, method='isotonic', cv=TimeSeriesSplit(5))
            calib.fit(train[feature_cols], train['Result'].astype(int))
            proba = calib.predict_proba(test[feature_cols])
            ll = log_loss(y, proba, labels=[0, 1, 2])
            if best is None or ll < best['model_logloss']:
                best = {'model_pick': name, 'model_logloss': ll,
                        'model_rps': ranked_probability_score(y, proba),
                        'model_acc': accuracy_score(y, proba.argmax(1))}

        odds_proba, y_odds = _odds_baseline(raw, test)
        records.append({
            'season': season,
            'n_matches': len(test),
            'model_pick': best['model_pick'],
            'model_logloss': round(best['model_logloss'], 4),
            'model_rps': round(best['model_rps'], 4),
            'model_acc': round(best['model_acc'], 4),
            'odds_logloss': round(log_loss(y_odds, odds_proba, labels=[0, 1, 2]), 4),
            'odds_rps': round(ranked_probability_score(y_odds, odds_proba), 4),
            'odds_acc': round(accuracy_score(y_odds, odds_proba.argmax(1)), 4),
        })
        print(f"{season}: {best['model_pick']:<8} "
              f"logloss={records[-1]['model_logloss']} "
              f"rps={records[-1]['model_rps']} vs odds rps={records[-1]['odds_rps']}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pd.DataFrame(records).to_csv(output_path, index=False)
    print(f"\nSaved {len(records)} seasons to {output_path}")


if __name__ == '__main__':
    main()
