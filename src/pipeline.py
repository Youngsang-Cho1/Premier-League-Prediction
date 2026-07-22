"""Weekly MLOps pipeline: ingest -> evaluate -> drift check -> conditional
retrain behind a deployment gate.

Retraining is triggered by evidence, not by the calendar:
  - the model's recent log-loss degrades in absolute terms, or
  - it falls too far behind the bookmaker baseline, or
  - feature drift is detected (guaranteed around season boundaries).

A retrain candidate only replaces the incumbent if it wins on a held-out
gate window (the most recent weeks, which the candidate never trained on).
Run with --check-only to see the decision without retraining.
"""
import os
import shutil
import sys
import joblib
import pandas as pd
from src import ingest, evaluate, drift, train_model, backtest
from src.preprocessor import load_and_clean
from src.train_model import feature_cols

WINDOW_DAYS = 60          # evaluation / drift lookback
GATE_WINDOW_DAYS = 60     # held out from candidate training, used to compare
LOGLOSS_ABS_MAX = 1.09    # worse than this ≈ barely better than guessing priors
ODDS_GAP_MAX = 0.08       # acceptable distance behind the market
CANDIDATE_PATH = 'candidate_model.pkl'
MODEL_PATH = 'premier_model.pkl'


def retrain_reasons(ev, dr):
    """Why (if at all) the model should be retrained.

    A bad absolute score only counts when the market did *not* also struggle:
    some rounds (the final matchday, heavy rotation) are unpredictable for
    everyone, and punishing the model for those would retrain on noise.
    """
    reasons = []
    if ev is not None:
        gap = (ev['model_logloss'] - ev['odds_logloss']
               if ev['odds_logloss'] is not None else None)

        market_also_bad = (ev['odds_logloss'] is not None
                           and ev['odds_logloss'] > LOGLOSS_ABS_MAX)
        if ev['model_logloss'] > LOGLOSS_ABS_MAX and not market_also_bad:
            reasons.append(f"log-loss {ev['model_logloss']} > {LOGLOSS_ABS_MAX}")

        if gap is not None and gap > ODDS_GAP_MAX:
            reasons.append(f"gap to odds baseline {gap:.4f} > {ODDS_GAP_MAX}")

    if dr is not None and dr['drift_detected']:
        reasons.append(f"feature drift: {', '.join(dr['drifted_features'])}")
    return reasons


def gate(candidate_path, incumbent_path):
    """Both models scored on the gate window; the candidate must win."""
    df = load_and_clean('data/matches.csv')
    rows = evaluate.evaluation_rows(df, GATE_WINDOW_DAYS)
    if rows.empty:
        print('Gate window empty — keeping incumbent.')
        return False
    cand_ll, _, _ = evaluate.score_model(joblib.load(candidate_path), rows)
    inc_ll, _, _ = evaluate.score_model(joblib.load(incumbent_path), rows)
    print(f'Gate ({len(rows)} matches): candidate {cand_ll:.4f} '
          f'vs incumbent {inc_ll:.4f}')
    return cand_ll < inc_ll


def main(check_only=False):
    ingest.main()

    # No new football, no pipeline. Between seasons there is nothing to score
    # and nothing to learn from, so stand down entirely rather than react to
    # stale matches.
    df = load_and_clean('data/matches.csv')
    stale, last_match, idle = evaluate.is_stale(df)
    if stale:
        print(f'\nLast match {last_match:%Y-%m-%d} ({idle} days ago) — '
              'between seasons. Pipeline standing down; model unchanged.')
        return

    ev = evaluate.main(window_days=WINDOW_DAYS)
    dr = drift.main(window_days=WINDOW_DAYS)

    reasons = retrain_reasons(ev, dr)
    if not reasons:
        print('\nPipeline done — model healthy, no retrain needed.')
        return

    print('\nRetrain triggered by: ' + '; '.join(reasons))
    if check_only:
        print('(--check-only: stopping before retrain)')
        return

    # Candidate trains on everything OLDER than the gate window, so the
    # gate comparison below is on data neither model has seen in training.
    gate_cutoff = (pd.Timestamp.now().normalize()
                   - pd.Timedelta(days=GATE_WINDOW_DAYS)).strftime('%Y-%m-%d')
    train_model.main(cutoff=gate_cutoff, output_path=CANDIDATE_PATH)

    if gate(CANDIDATE_PATH, MODEL_PATH):
        shutil.move(CANDIDATE_PATH, MODEL_PATH)
        print('Candidate wins — deployed as new model.')
        # Refresh the season backtest that powers the dashboard, since the
        # deployed model (and the data behind it) has changed.
        backtest.main()
    else:
        os.remove(CANDIDATE_PATH)
        print('Candidate loses — incumbent kept.')


if __name__ == '__main__':
    main(check_only='--check-only' in sys.argv)
