from flask import Flask, request, jsonify, render_template
import pandas as pd
from src.infer import predict_matches, predict_matches_bidirectional
import joblib

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

    ordered_proba = proba[0][[2,1,0]]

    return jsonify({
        'result': int(preds),
        'probabilities': ordered_proba.tolist()
    })

print(model.classes_)

if __name__ == '__main__':
    app.run(debug=True)
    