import joblib
import pandas as pd
from src.preprocessor import load_and_clean
from src.train_model import feature_cols

_MODEL = joblib.load('premier_model.pkl')

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

def predict_matches_bidirectional(team1, team2):
    preds1, proba1 = predict_matches(team1, team2)
    preds2, proba2 = predict_matches(team2, team1)

    reversed_proba2 = proba2[0][[2,1,0]]

    avg_proba = (proba1 + reversed_proba2) / 2

    final_pred = avg_proba.argmax()

    return final_pred, avg_proba