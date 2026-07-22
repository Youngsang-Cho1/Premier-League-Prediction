"""The pipeline must stand down between seasons and ignore noisy windows.

Without these guards it once retrained off the final matchday alone — ten
games, played two months earlier, on which the bookmakers scored just as
badly as the model.
"""
import pandas as pd
import pytest

from src.evaluate import MAX_IDLE_DAYS, MIN_MATCHES, is_stale
from src.pipeline import retrain_reasons


def _df(last_match_days_ago):
    day = pd.Timestamp.now().normalize() - pd.Timedelta(days=last_match_days_ago)
    return pd.DataFrame({'Date': [day - pd.Timedelta(days=7), day]})


def test_is_stale_between_seasons():
    stale, _, idle = is_stale(_df(MAX_IDLE_DAYS + 10))
    assert stale
    assert idle == MAX_IDLE_DAYS + 10


def test_is_not_stale_during_season():
    stale, _, _ = is_stale(_df(3))
    assert not stale


def test_no_retrain_when_market_also_struggled():
    """A round everyone got wrong is not evidence the model is broken."""
    ev = {'model_logloss': 1.232, 'odds_logloss': 1.219}
    assert retrain_reasons(ev, None) == []


def test_retrain_when_only_model_is_bad():
    ev = {'model_logloss': 1.20, 'odds_logloss': 0.95}
    reasons = retrain_reasons(ev, None)
    assert reasons  # both the absolute threshold and the gap should fire


def test_retrain_on_drift_alone():
    dr = {'drift_detected': True, 'drifted_features': ['elo_diff']}
    assert any('drift' in r for r in retrain_reasons(None, dr))


def test_no_reasons_when_nothing_evaluated():
    assert retrain_reasons(None, None) == []


def test_min_matches_threshold_is_meaningful():
    """Guard against someone lowering it back to a single round."""
    assert MIN_MATCHES >= 20
