from flask import Flask, request, jsonify, render_template
import pandas as pd
from src.infer import predict_matches_bidirectional
import joblib
import os

app = Flask(__name__)
model = joblib.load('premier_model.pkl')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    team1 = data['team1']
    team2 = data['team2']

    preds, proba = predict_matches_bidirectional(team1, team2)
    
    # Extract historical insights
    from src.infer import get_matchup_insights
    insights = get_matchup_insights(team1, team2)

    # Historical logic: proba indices are [Lose, Draw, Win]
    ordered_proba = proba[0]

    return jsonify({
        'result': int(preds),
        'probabilities': ordered_proba.tolist(),
        'insights': insights
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)