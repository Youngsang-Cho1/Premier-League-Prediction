import joblib
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import f1_score, classification_report, log_loss, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
from src.preprocessor import load_and_clean
import xgboost as xgb

# Test set = the most recent full season. All features are pre-match only
# (shifted rolling stats, pre-match Elo); the matchup is described by both
# sides' form rather than an opaque opponent category, so newly promoted
# teams work too. Set chosen by greedy group selection on a held-out
# validation season (2024-25): Elo diff, venue form, SoT ratio and rest
# difference earned their place; corners and EWM form did not.
CUTOFF = '2025-08-01'
feature_cols = (['is_home', 'days_rest',
                 'Recent_GF_avg5', 'Recent_GA_avg5',
                 'Recent_SoT_avg5', 'Recent_SoTA_avg5',
                 'Recent_Result_avg5', 'Recent_Result_avg20',
                 'opp_Recent_GF_avg5', 'opp_Recent_GA_avg5',
                 'opp_Recent_SoT_avg5', 'opp_Recent_SoTA_avg5',
                 'opp_Recent_Result_avg5', 'opp_Recent_Result_avg20',
                 'h2h_record', 'elo_diff',
                 'Recent_Result_venue_avg5', 'opp_Recent_Result_venue_avg5',
                 'SoT_ratio5', 'opp_SoT_ratio5', 'rest_diff'])

# Define function that tunes and evaluates the model and compare each hyper parameter's performances
def tune_and_evaluate(estimator, cv, param_grid, model, X_train, y_train, X_test, y_test):
    grid = GridSearchCV(
        estimator=estimator,
        param_grid=param_grid,
        cv=cv,
        scoring='f1_macro',
        refit=True,
        n_jobs=-1
    )
    grid.fit(X_train, y_train)
    best = grid.best_estimator_

    # The calibrated model is what gets evaluated AND returned — the app's
    # output is probabilities, so shipping the uncalibrated estimator while
    # measuring the calibrated one would misreport what is deployed.
    calib = CalibratedClassifierCV(best, method='isotonic', cv=cv)
    calib.fit(X_train, y_train)

    y_pred = calib.predict(X_test)
    y_proba = calib.predict_proba(X_test)

    f1 = f1_score(y_test, y_pred, average='macro')
    print(f'\n[{model}] Test Macro‑F1: {f1:.4f}')
    print(classification_report(y_test, y_pred, target_names=['L','D','W']))

    ll = log_loss(y_test, y_proba, labels=[0,1,2])
    bs = brier_score_loss((y_test==1).astype(int), y_proba[:,1])
    print(f'Log‑Loss: {ll:.4f}')
    print(f'Brier Score (draw): {bs:.4f}')

    return model, calib, f1, ll


def main(cutoff=CUTOFF, output_path='premier_model.pkl'):
    """Train, calibrate and select a model. `cutoff` splits train/test by
    date — the weekly pipeline passes a recent cutoff so the last weeks act
    as a held-out gate window for comparing against the incumbent model."""
    df = load_and_clean('data/matches.csv')
    df = df.sort_values('Date')

    train = df[df['Date'] < cutoff].dropna(subset = feature_cols + ['Result'])
    test  = df[df['Date'] >= cutoff].dropna(subset = feature_cols + ['Result'])

    X_train = train[feature_cols]
    y_train = train['Result'].astype(int)

    X_test = test[feature_cols]
    y_test = test['Result'].astype(int)

    tscv = TimeSeriesSplit(n_splits=5)

    # Draw upweighting trades a little accuracy/log-loss for draw recall;
    # let the grid decide whether it pays off on macro-F1.
    param_grid_rf = {
    'n_estimators':    [200],
    'max_depth':       [5, 10, 20],
    'min_samples_split':[2, 5],
    'class_weight':    [None, 'balanced', {0: 1, 1: 3, 2: 1}]
    }
    param_grid_gb = {
        'n_estimators': [100, 200],
        'learning_rate':[0.01, 0.1],
        'max_depth':    [3, 5]
    }
    param_grid_xgb = {
        'n_estimators': [100, 200],
        'max_depth':    [3, 5, 7],
        'learning_rate':[0.01, 0.1],
        'subsample':    [0.8, 1.0]
    }
    # With ~15 smooth, mostly monotone form features, a regularized linear
    # model is a serious candidate — trees tend to overfit interactions here.
    param_grid_lr = {
        'logisticregression__C': [0.01, 0.1, 1.0]
    }

    results = []
    results.append(
        tune_and_evaluate(RandomForestClassifier(random_state=42), tscv, param_grid_rf, 'RandomForest', X_train, y_train, X_test, y_test)
    )
    results.append(
        tune_and_evaluate(GradientBoostingClassifier(random_state=42), tscv, param_grid_gb, 'GradientBoosting', X_train, y_train, X_test, y_test)
    )
    results.append(
        tune_and_evaluate(xgb.XGBClassifier(eval_metric='mlogloss', random_state=42), tscv, param_grid_xgb, 'XGBoost', X_train, y_train, X_test, y_test)
    )
    results.append(
        tune_and_evaluate(make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)), tscv, param_grid_lr, 'LogisticRegression', X_train, y_train, X_test, y_test)
    )

    # The app serves probabilities, so select the model with the best
    # probability quality (lowest log-loss), not the best argmax F1.
    best_name, best_model, best_f1, best_ll = min(results, key=lambda x: x[3])
    print(f'\nSelected model: {best_name} (Log-Loss {best_ll:.4f}, Macro-F1 {best_f1:.4f})')

    joblib.dump(best_model, output_path)

if __name__ == "__main__":
    main()
