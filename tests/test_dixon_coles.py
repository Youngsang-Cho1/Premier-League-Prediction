"""Dixon-Coles goal model: check it learns sane strengths and produces
valid probability/scoreline outputs."""
import numpy as np
import pandas as pd
import pytest
from src.dixon_coles import DixonColesModel


@pytest.fixture(scope='module')
def model():
    matches = pd.read_csv('data/matches.csv', parse_dates=['Date'])
    return DixonColesModel().fit(matches)


def test_probabilities_are_valid(model):
    p = model.predict_proba('Arsenal', 'Chelsea')
    assert len(p) == 3
    assert p.sum() == pytest.approx(1.0, abs=1e-6)
    assert (p >= 0).all()


def test_home_advantage_is_positive(model):
    # a positive home-advantage term is a basic sanity check on the fit
    _, _, home_adv, _ = model.params
    assert home_adv > 0


def test_stronger_team_favored(model):
    # Man City at home to a weak side should be strong favorites
    p = model.predict_proba('Manchester City', 'Burnley')
    assert p[2] > p[0]  # P(win) > P(loss)
    assert p[2] > 0.5


def test_scoreline_is_nonnegative_pair(model):
    h, a = model.predict_scoreline('Arsenal', 'Chelsea')
    assert isinstance(h, int) and isinstance(a, int)
    assert h >= 0 and a >= 0


def test_unknown_team_falls_back_not_crashes(model):
    # promoted/unknown team uses league-average strength instead of raising
    p = model.predict_proba('Some New Team', 'Arsenal')
    assert p.sum() == pytest.approx(1.0, abs=1e-6)
