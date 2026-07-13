"""Feature drift detection via Population Stability Index (PSI).

Reference distribution = the training period; current = recently played
matches. PSI is computed per feature over quantile bins of the reference.
Conventional reading: < 0.10 stable, 0.10-0.25 moderate shift, > 0.25
significant drift. EPL drift is structural — every August three promoted
teams and a transfer window arrive — so this is expected to fire around
season boundaries, which is exactly when a retrain check is wanted.
"""
import json
import os
import numpy as np
import pandas as pd
from src.preprocessor import load_and_clean
from src.train_model import feature_cols, CUTOFF

REPORT_PATH = 'metrics/drift_latest.json'
PSI_ALERT = 0.25
MIN_ROWS = 50


def psi(reference, current, bins=10):
    edges = np.quantile(reference, np.linspace(0, 1, bins + 1))
    edges = np.unique(edges)
    if len(edges) < 3:  # near-constant feature (e.g. is_home)
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf

    ref_frac = np.histogram(reference, bins=edges)[0] / len(reference)
    cur_frac = np.histogram(current, bins=edges)[0] / len(current)
    ref_frac = np.clip(ref_frac, 1e-4, None)
    cur_frac = np.clip(cur_frac, 1e-4, None)
    return float(np.sum((cur_frac - ref_frac) * np.log(cur_frac / ref_frac)))


def main(window_days=60, data_path='data/matches.csv'):
    df = load_and_clean(data_path)
    reference = df[df['Date'] < CUTOFF].dropna(subset=feature_cols)
    since = pd.Timestamp.now().normalize() - pd.Timedelta(days=window_days)
    current = df[df['Date'] >= since].dropna(subset=feature_cols)

    if len(current) < MIN_ROWS:
        print(f'Only {len(current)} recent rows — too few for a drift '
              'check (off-season). Skipping.')
        return None

    scores = {col: round(psi(reference[col].to_numpy(),
                             current[col].to_numpy()), 4)
              for col in feature_cols}
    drifted = sorted([c for c, v in scores.items() if v > PSI_ALERT],
                     key=scores.get, reverse=True)

    report = {
        'run_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'window_days': window_days,
        'n_current_rows': len(current),
        'psi_alert_threshold': PSI_ALERT,
        'drift_detected': bool(drifted),
        'drifted_features': drifted,
        'psi': dict(sorted(scores.items(), key=lambda kv: -kv[1])),
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2)

    top = list(report['psi'].items())[:3]
    print(f"Drift check on {len(current)} rows: "
          f"{'DRIFT in ' + ', '.join(drifted) if drifted else 'stable'} "
          f"(top PSI: {top})")
    return report


if __name__ == '__main__':
    main()
