from flask import Flask, request, jsonify, render_template
from src.infer import predict_matches_bidirectional, get_matchup_insights
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(silent=True) or {}
    team1 = data.get('team1')
    team2 = data.get('team2')

    if not team1 or not team2:
        return jsonify({'error': 'Both team1 and team2 are required.'}), 400
    if team1 == team2:
        return jsonify({'error': 'Please select two different teams.'}), 400

    try:
        pred, proba = predict_matches_bidirectional(team1, team2)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    insights = get_matchup_insights(team1, team2)

    # proba is ordered [Lose, Draw, Win] for team1 (the home team)
    return jsonify({
        'result': pred,
        'probabilities': proba.tolist(),
        'insights': insights
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
