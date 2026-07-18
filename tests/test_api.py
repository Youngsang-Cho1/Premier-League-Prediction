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


def test_stats_page_serves(client):
    resp = client.get('/stats')
    assert resp.status_code == 200


def test_schedule_page_serves(client):
    resp = client.get('/schedule')
    assert resp.status_code == 200


def test_api_stats_returns_real_data(client):
    resp = client.get('/api/stats')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['kpis']) == 4
    assert len(data['xpoints']['table']) == 20
    # xPoints rows carry real computed fields
    row = data['xpoints']['table'][0]
    assert {'team', 'points', 'xpoints', 'diff'} <= set(row)


def test_api_schedule_returns_fixtures(client):
    resp = client.get('/api/schedule')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'fixtures' in data and 'is_past' in data
    # off-season falls back to recent played matches, but never empty here
    assert len(data['fixtures']) >= 1
    fx = data['fixtures'][0]
    assert 'home' in fx and 'away' in fx
