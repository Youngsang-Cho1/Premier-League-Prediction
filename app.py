from flask import Flask, request, jsonify, render_template
from src.infer import (predict_matches_bidirectional, get_matchup_insights,
                       predict_scoreline)
from src.xpoints import compute_xpoints, recent_predictions
from src.schedule_feed import upcoming_fixtures
import csv
import os

app = Flask(__name__,
            template_folder='frontend/templates',
            static_folder='frontend/static')

BACKTEST_PATH = 'metrics/backtest.csv'
HISTORY_PATH = 'metrics/history.csv'


def _read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _num(row, key):
    """Parse a CSV string field to float, or None if missing/blank."""
    v = row.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/metrics')
def metrics():
    """Backtest (per-season, model vs market) and weekly evaluation history.
    Powers the /dashboard charts; empty history is expected off-season."""
    return jsonify({
        'backtest': _read_csv(BACKTEST_PATH),
        'history': _read_csv(HISTORY_PATH),
    })


@app.route('/stats')
def stats():
    return render_template('stats.html')


@app.route('/schedule')
def schedule():
    return render_template('schedule.html')


@app.route('/api/stats')
def api_stats():
    """Real model-performance data for the stats page, derived from the
    season backtest and the xPoints table — no placeholders."""
    bt = _read_csv(BACKTEST_PATH)
    xpoints_table, xp_season = compute_xpoints()

    kpis, season_trend, market_compare = [], [], {}
    if bt:
        latest = bt[-1]
        seasons = [r['season'] for r in bt]
        model_acc = [_num(r, 'model_acc') for r in bt]
        model_rps = [_num(r, 'model_rps') for r in bt]
        odds_rps = [_num(r, 'odds_rps') for r in bt]

        # RPS edge over the market, averaged (lower RPS is better, so the
        # model's edge is odds_rps - model_rps when positive)
        edges = [o - m for o, m in zip(odds_rps, model_rps)
                 if o is not None and m is not None]
        avg_edge = sum(edges) / len(edges) if edges else 0.0
        total_matches = sum(int(_num(r, 'n_matches') or 0) for r in bt)

        kpis = [
            {'value': f"{(_num(latest, 'model_acc') or 0) * 100:.1f}%",
             'label': 'Latest-season accuracy',
             'delta': f"{latest['season']} test season", 'trend': ''},
            {'value': str(total_matches),
             'label': 'Matches backtested',
             'delta': f"across {len(bt)} seasons", 'trend': ''},
            {'value': f"{_num(latest, 'model_rps') or 0:.3f}",
             'label': 'Latest-season RPS',
             'delta': 'lower is better', 'trend': ''},
            {'value': f"{avg_edge:+.4f}",
             'label': 'Avg RPS edge vs market',
             'delta': 'vs Bet365 odds',
             'trend': 'pos' if avg_edge >= 0 else 'neg'},
        ]
        season_trend = [
            {'season': s, 'model_acc': a, 'model_rps': r}
            for s, a, r in zip(seasons, model_acc, model_rps)
        ]
        market_compare = {
            'seasons': seasons,
            'model_rps': model_rps,
            'odds_rps': odds_rps,
        }

    return jsonify({
        'kpis': kpis,
        'season_trend': season_trend,
        'market_compare': market_compare,
        'xpoints': {'season': xp_season, 'table': xpoints_table},
        'recent_predictions': recent_predictions(),
    })


@app.route('/api/schedule')
def api_schedule():
    """Upcoming fixtures from the FPL API. Off-season (no future fixtures),
    falls back to the most recent played round from our own data so the page
    is never empty."""
    fixtures, is_past = upcoming_fixtures()
    return jsonify({'fixtures': fixtures, 'is_past': is_past})


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
    scoreline = predict_scoreline(team1, team2)

    # proba is ordered [Lose, Draw, Win] for team1 (the home team)
    return jsonify({
        'result': pred,
        'probabilities': proba.tolist(),
        'insights': insights,
        'scoreline': scoreline
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(debug=debug, host='0.0.0.0', port=port)
