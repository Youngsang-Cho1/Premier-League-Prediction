import joblib
import pandas as pd
from preprocessor import load_and_clean
from train_model import feature_cols

_bundle = joblib.load('model/premier_model.pkl')
_MODEL = _bundle['model']

def predict_matches(team1, team2):
    df = load_and_clean('prem_data.csv')
    # Get all records of two teams and extract the most recent h2h record
    match_df = df[(df['Team'] == team1) & (df['Opponent'] == team2)].sort_values('Date', ascending = False)
    h2h_data = match_df.iloc[0]['h2h_record']

    # Get the most recent data of team 1
    team1_data = df[(df['Team'] == team1)].sort_values(by = 'Date', ascending = False).iloc[0]

    feature_input = team1_data[feature_cols].copy()
    feature_input['h2h_record'] = h2h_data 

    X = pd.DataFrame([feature_input])

    proba = _MODEL.predict_proba(X)
    preds = _MODEL.predict(X)
    return preds, proba