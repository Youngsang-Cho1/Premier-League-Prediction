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
