"""Schema and sanity checks for the master dataset — runs in CI before the
pipeline so a malformed upstream CSV can never silently poison training."""
import pandas as pd
import pytest

REQUIRED = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
            'HS', 'AS', 'HST', 'AST', 'HC', 'AC',
            'B365H', 'B365D', 'B365A', 'Season']


@pytest.fixture(scope='module')
def matches():
    return pd.read_csv('data/matches.csv', parse_dates=['Date'])


def test_required_columns(matches):
    for col in REQUIRED:
        assert col in matches.columns, f'missing column: {col}'


def test_results_and_goals_valid(matches):
    assert matches['FTR'].isin(['H', 'D', 'A']).all()
    assert (matches['FTHG'] >= 0).all() and (matches['FTAG'] >= 0).all()
    consistent = (
        ((matches['FTR'] == 'H') & (matches['FTHG'] > matches['FTAG'])) |
        ((matches['FTR'] == 'A') & (matches['FTHG'] < matches['FTAG'])) |
        ((matches['FTR'] == 'D') & (matches['FTHG'] == matches['FTAG']))
    )
    assert consistent.all()


def test_dates_sorted_and_plausible(matches):
    assert matches['Date'].is_monotonic_increasing
    assert matches['Date'].min().year >= 2015


def test_dataset_size(matches):
    assert len(matches) >= 4000
    # each season is 380 matches once complete
    complete = matches.groupby('Season').size()[:-1]
    assert (complete == 380).all()


def test_odds_are_valid_prices(matches):
    odds = matches[['B365H', 'B365D', 'B365A']].dropna()
    assert (odds > 1.0).all().all()
    assert len(odds) / len(matches) > 0.95
