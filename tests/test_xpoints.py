"""xPoints table sanity checks — the values are model-derived, so we pin
down the invariants rather than exact numbers."""
import pytest
from src.xpoints import compute_xpoints


@pytest.fixture(scope='module')
def result():
    return compute_xpoints()


def test_returns_table_and_season(result):
    table, season = result
    assert isinstance(table, list) and len(table) > 0
    assert isinstance(season, str)


def test_every_team_has_required_fields(result):
    table, _ = result
    for row in table:
        assert set(row) >= {'team', 'played', 'points', 'xpoints', 'diff'}
        assert row['played'] > 0
        assert row['points'] >= 0
        assert row['xpoints'] >= 0


def test_diff_is_points_minus_xpoints(result):
    table, _ = result
    for row in table:
        assert row['diff'] == pytest.approx(row['points'] - row['xpoints'], abs=0.05)


def test_sorted_by_points_desc(result):
    table, _ = result
    pts = [r['points'] for r in table]
    assert pts == sorted(pts, reverse=True)


def test_total_xpoints_reasonable(result):
    """Total xPoints across all teams should be close to total real points
    (the model is calibrated), and a full PL season has 20 teams."""
    table, _ = result
    assert len(table) == 20
    total_pts = sum(r['points'] for r in table)
    total_xp = sum(r['xpoints'] for r in table)
    # within 5% — calibrated probabilities conserve total points approximately
    assert abs(total_pts - total_xp) / total_pts < 0.05
