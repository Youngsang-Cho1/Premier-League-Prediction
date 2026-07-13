"""Tests for the Ranked Probability Score — the property that distinguishes
it from log-loss is ordinal awareness, so that is what we pin down."""
import numpy as np
import pytest
from src.evaluate import ranked_probability_score


def test_perfect_prediction_scores_zero():
    # certain and correct on every match -> RPS 0
    proba = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    y = [0, 1, 2]
    assert ranked_probability_score(y, proba) == pytest.approx(0.0)


def test_worst_prediction_scores_one():
    # certain of a Win when the result was a Loss (max ordinal distance)
    assert ranked_probability_score([0], [[0.0, 0.0, 1.0]]) == pytest.approx(1.0)


def test_respects_ordinal_distance():
    """Result was a Win (index 2). Betting fully on Draw (adjacent) must be
    penalized LESS than betting fully on Loss (far) — this is exactly what
    log-loss cannot see."""
    rps_near = ranked_probability_score([2], [[0.0, 1.0, 0.0]])  # said Draw
    rps_far = ranked_probability_score([2], [[1.0, 0.0, 0.0]])   # said Loss
    assert rps_near < rps_far


def test_bounded_between_zero_and_one():
    rng = np.random.default_rng(0)
    p = rng.dirichlet([1, 1, 1], size=200)
    y = rng.integers(0, 3, size=200)
    rps = ranked_probability_score(y, p)
    assert 0.0 <= rps <= 1.0
