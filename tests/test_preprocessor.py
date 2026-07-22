"""The tests that make automated retraining safe: if feature engineering
ever leaks a match's own outcome into its features, CI must fail before
the pipeline ships a model with inflated metrics."""
import numpy as np
import pandas as pd
import pytest
from src.preprocessor import load_and_clean, ELO_NEW_TEAM
from src.train_model import feature_cols


@pytest.fixture(scope='module')
def df():
    return load_and_clean('data/matches.csv')


def test_rolling_features_exclude_own_match(df):
    """Recent_*_avg5 on row i must equal the mean of the PREVIOUS 5 raw
    values — never including the row's own match."""
    team_rows = df[df['Team'] == 'Arsenal'].sort_values('Date').reset_index(drop=True)
    for i in [10, 50, 100]:
        expected = team_rows['GF'].iloc[i - 5:i].mean()
        assert team_rows['Recent_GF_avg5'].iloc[i] == pytest.approx(expected)
        expected_res = team_rows['Result'].iloc[i - 5:i].mean()
        assert team_rows['Recent_Result_avg5'].iloc[i] == pytest.approx(expected_res)


def test_elo_is_pre_match(df):
    """Teams in the very first round have no history: their Elo must be the
    new-team default, unaffected by that match's result."""
    first_date = df['Date'].min()
    opening = df[df['Date'] == first_date]
    assert (opening['elo'] == ELO_NEW_TEAM).all()


def test_h2h_neutral_for_first_meeting(df):
    """The first meeting of every (Team, Opponent) pair has no history, so
    h2h_record must be the neutral prior 1.0 — not 0 (= 'lost both')."""
    firsts = df.sort_values('Date').groupby(['Team', 'Opponent']).head(1)
    assert (firsts['h2h_record'] == 1.0).all()


def test_feature_columns_exist_and_finite(df):
    """Every declared model feature exists, and rows used for training are
    finite after dropna."""
    for col in feature_cols:
        assert col in df.columns, f'missing feature column: {col}'
    trainable = df.dropna(subset=feature_cols)
    assert len(trainable) > 5000
    assert np.isfinite(trainable[feature_cols].to_numpy()).all()


def test_opponent_features_are_mirrored(df):
    """A match's home row must carry the away team's form as opp_* and
    vice versa."""
    sample = df[(df['is_home'] == 1)].dropna(subset=feature_cols).iloc[100]
    mirror = df[(df['Team'] == sample['Opponent']) &
                (df['Date'] == sample['Date'])].iloc[0]
    assert sample['opp_Recent_GF_avg5'] == pytest.approx(mirror['Recent_GF_avg5'])
    assert sample['Recent_GF_avg5'] == pytest.approx(mirror['opp_Recent_GF_avg5'])


def test_xg_rolling_excludes_own_match(df):
    """Recent_xG_avg5 must be the mean of the PREVIOUS 5 matches' xG — a
    match's own xG is only known after kickoff, so including it would leak."""
    team_rows = df[df['Team'] == 'Arsenal'].sort_values('Date').reset_index(drop=True)
    for i in [20, 60, 120]:
        expected = team_rows['xG'].iloc[i - 5:i].mean()
        assert team_rows['Recent_xG_avg5'].iloc[i] == pytest.approx(expected, nan_ok=True)


def test_xg_diff_is_attack_minus_defence(df):
    rows = df.dropna(subset=['Recent_xG_avg5', 'Recent_xGA_avg5']).head(50)
    for r in rows.itertuples():
        assert r.xG_diff5 == pytest.approx(r.Recent_xG_avg5 - r.Recent_xGA_avg5)


def test_raw_xg_is_not_a_model_feature():
    """Only the shifted rolling xG may be used; raw per-match xG would leak."""
    assert 'xG' not in feature_cols
    assert 'xGA' not in feature_cols
