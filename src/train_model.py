import joblib
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import f1_score, classification_report, log_loss, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
from src.preprocessor import load_and_clean
import xgboost as xgb

# Define date cutoff and feature_cols for train-test split.
CUTOFF = '2024-01-01'
feature_cols = (['Opponent_code', 'is_home', 'xG_diff', 'Recent_GF_avg5',
                 'Recent_GA_avg5', 'Recent_SoT_avg5', 'Recent_FK_avg5', 'Recent_PK_avg5',
                 'Recent_xG_diff_avg5', 'Recent_Result_avg5', 'h2h_record'])

# Define function that tunes and evaluates the model and compare each hyper parameter's performances
def tune_and_evaluate(estimator, cv, param_grid, model, X_train, y_train, X_test, y_test):
    grid = GridSearchCV(
        estimator=estimator,
        param_grid=param_grid,
        cv=cv,
        scoring='f1_macro',
        refit=True
    )
    grid.fit(X_train, y_train)
    best = grid.best_estimator_

    calib = CalibratedClassifierCV(best, method='isotonic', cv=cv)
    calib.fit(X_train, y_train)
 
    y_pred = best.predict(X_test)
    y_proba = calib.predict_proba(X_test)

    f1 = f1_score(y_test, y_pred, average='macro')
    print(f'\n[{model}] Test Macro‑F1: {f1:.4f}')
    print(classification_report(y_test, y_pred, target_names=['L','D','W']))
 
    ll = log_loss(y_test, y_proba, labels=[0,1,2])
    bs = brier_score_loss((y_test==1).astype(int), y_proba[:,1])
    print(f'Log‑Loss: {ll:.4f}')
    print(f'Brier Score (draw): {bs:.4f}')

    return model, best, f1


def main():
    df = load_and_clean('prem_data.csv')
    df = df.sort_values('Date')

    train = df[df['Date'] < CUTOFF].dropna(subset = feature_cols + ['Result'])
    test  = df[df['Date'] >= CUTOFF].dropna(subset = feature_cols + ['Result'])

    X_train = train[feature_cols]
    y_train = train['Result'].astype(int)

    X_test = test[feature_cols]
    y_test = test['Result'].astype(int)

    tscv = TimeSeriesSplit(n_splits=5)

    param_grid_rf = {
    'n_estimators':    [100, 200],
    'max_depth':       [5, 10, 20],
    'min_samples_split':[2, 5]
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

    results = []
    results.append(
        tune_and_evaluate(RandomForestClassifier(random_state=42, class_weight = 'balanced'), tscv, param_grid_rf, 'RandomForest', X_train, y_train, X_test, y_test)
    )
    results.append(
        tune_and_evaluate(GradientBoostingClassifier(random_state=42), tscv, param_grid_gb, 'GradientBoosting', X_train, y_train, X_test, y_test)
    )
    results.append(
        tune_and_evaluate(xgb.XGBClassifier(eval_metric='mlogloss', random_state=42), tscv, param_grid_xgb, 'XGBoost', X_train, y_train, X_test, y_test)
    )

    best = best_name, best_model, best_f1 = max(results, key=lambda x: x[2])
    final_model = best_model
    print(final_model)

    joblib.dump(final_model, 'premier_model.pkl')  

if __name__ == "__main__":
    main()