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

def get_matchup_insights(team1, team2):
    """
    Extract historical H2H results and calculate draw rate directly from CSV.
    """
    try:
        df = pd.read_csv('prem_data.csv')
        
        # Simple name mapping for CSV hyphenated names
        team_rev_dict = {
            'Manchester City': 'Manchester-City',
            'Manchester Utd': 'Manchester-United',
            'Newcastle Utd': 'Newcastle-United',
            'Tottenham': 'Tottenham-Hotspur',
            'Wolves': 'Wolverhampton-Wanderers',
            'Sheffield Utd': 'Sheffield-United',
            'Leicester City': 'Leicester-City',
            'Leeds United': 'Leeds-United'
        }
        
        t1_norm = team_rev_dict.get(team1, team1.replace(' ', '-'))
        t2_norm = team_rev_dict.get(team2, team2.replace(' ', '-'))
        
        # Filter for matchups
        h2h_df = df[((df['Team'] == t1_norm) & (df['Opponent'] == t2_norm)) | 
                    ((df['Team'] == t2_norm) & (df['Opponent'] == t1_norm))].copy()
        
        if h2h_df.empty:
            return {"draw_rate": "0%", "count": 0, "history": []}
            
        h2h_df['Date'] = pd.to_datetime(h2h_df['Date'])
        # Drop duplicates as CSV has rows for both sides of a match
        h2h_df = h2h_df.drop_duplicates(subset=['Date'])
        h2h_df = h2h_df.sort_values('Date', ascending=False)
        
        # Draw Rate
        draws = len(h2h_df[h2h_df['Result'] == 'D'])
        draw_rate = f"{(draws / len(h2h_df) * 100):.1f}%"
        
        # Recent History
        history = []
        for _, row in h2h_df.head(5).iterrows():
            res = row['Result']
            score = f"{int(row['GF'])}-{int(row['GA'])}"
            history.append({
                "date": row['Date'].strftime('%Y-%m-%d'),
                "result": res,
                "score": score,
                "opponent": row['Opponent'].replace('-', ' ')
            })
            
        return {
            "draw_rate": draw_rate,
            "count": len(h2h_df),
            "history": history
        }
    except Exception as e:
        print(f"Error extracting insights: {e}")
        return {"draw_rate": "--", "count": 0, "history": []}