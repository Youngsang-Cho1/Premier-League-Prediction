import pytest
from app import app


@pytest.fixture(scope='module')
def client():
    return app.test_client()


def test_predict_returns_valid_probabilities(client):
    resp = client.post('/predict', json={'team1': 'Arsenal', 'team2': 'Chelsea'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['result'] in (0, 1, 2)
    probs = data['probabilities']
    assert len(probs) == 3
    assert sum(probs) == pytest.approx(1.0, abs=1e-6)
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert 'insights' in data
    # scoreline is an optional Dixon-Coles extra: present as "H-A" or null
    assert 'scoreline' in data
    if data['scoreline'] is not None:
        h, a = data['scoreline'].split('-')
        assert h.isdigit() and a.isdigit()


def test_unknown_team_is_400(client):
    resp = client.post('/predict', json={'team1': 'Real Madrid', 'team2': 'Arsenal'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_same_team_is_400(client):
    resp = client.post('/predict', json={'team1': 'Arsenal', 'team2': 'Arsenal'})
    assert resp.status_code == 400


def test_missing_field_is_400(client):
    resp = client.post('/predict', json={'team1': 'Arsenal'})
    assert resp.status_code == 400


def test_promoted_team_without_long_history_works(client):
    resp = client.post('/predict', json={'team1': 'Sunderland', 'team2': 'Manchester City'})
    assert resp.status_code == 200


def test_dashboard_route_serves(client):
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    assert b'Model Performance' in resp.data


def test_metrics_api_returns_backtest(client):
    resp = client.get('/api/metrics')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'backtest' in data and 'history' in data
    # backtest.csv is committed, so it should have season rows
    assert len(data['backtest']) >= 1
    row = data['backtest'][0]
    assert 'season' in row and 'model_rps' in row and 'odds_rps' in row
