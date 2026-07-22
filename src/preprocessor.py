import os

import numpy as np
import pandas as pd

# Result encoding used throughout: 0 = Loss, 1 = Draw, 2 = Win.

ELO_BASE = 1500.0
ELO_NEW_TEAM = 1400.0      # promoted/new teams start below average
ELO_K = 20.0
ELO_HOME_ADV = 60.0
ELO_SEASON_REGRESS = 0.25  # pull ratings toward base between seasons


def _compute_elo(matches):
    """Pre-match and post-match Elo per side. Ratings are recorded BEFORE
    applying the match result, so the pre columns are leakage-free features;
    the post columns exist only so inference can read each team's current
    rating from its latest row."""
    ratings = {}
    prev_season = None
    pre_h, pre_a, post_h, post_a = [], [], [], []

    for row in matches.itertuples():
        if prev_season is not None and row.Season != prev_season:
            ratings = {t: r + ELO_SEASON_REGRESS * (ELO_BASE - r)
                       for t, r in ratings.items()}
        prev_season = row.Season

        rh = ratings.get(row.HomeTeam, ELO_NEW_TEAM)
        ra = ratings.get(row.AwayTeam, ELO_NEW_TEAM)
        expected_home = 1.0 / (1.0 + 10 ** (-((rh + ELO_HOME_ADV) - ra) / 400.0))
        score_home = {'H': 1.0, 'D': 0.5, 'A': 0.0}[row.FTR]
        delta = ELO_K * (score_home - expected_home)

        pre_h.append(rh)
        pre_a.append(ra)
        ratings[row.HomeTeam] = rh + delta
        ratings[row.AwayTeam] = ra - delta
        post_h.append(ratings[row.HomeTeam])
        post_a.append(ratings[row.AwayTeam])

    return pre_h, pre_a, post_h, post_a


XG_PATH = 'data/xg.csv'


def _attach_xg(matches, xg_path=XG_PATH):
    """Left-join per-match xG (from src.xg_ingest) onto the match table.

    xG is an optional secondary source: if the file is missing the columns
    come back as NaN and the xG-derived features simply drop out, so the
    pipeline keeps working on the primary data alone.
    """
    if not os.path.exists(xg_path):
        matches['xG_home'] = np.nan
        matches['xG_away'] = np.nan
        return matches

    xg = pd.read_csv(xg_path, parse_dates=['Date'])
    return matches.merge(xg, on=['Date', 'HomeTeam', 'AwayTeam'], how='left')


def load_and_clean(filepath):
    """Build team-perspective feature rows from the match-level dataset
    (data/matches.csv, produced by src.ingest).

    Every feature is computed strictly from information available BEFORE
    kickoff: rolling stats are shift(1)-ed and Elo is pre-match, so a match
    never sees its own outcome (no leakage).
    """
    matches = pd.read_csv(filepath)
    matches['Date'] = pd.to_datetime(matches['Date'])
    matches = matches.sort_values('Date').reset_index(drop=True)
    matches = _attach_xg(matches)

    elo_h, elo_a, elo_h_post, elo_a_post = _compute_elo(matches)

    # One row per team per match: home perspective + mirrored away perspective.
    home = pd.DataFrame({
        'Date': matches['Date'], 'Season': matches['Season'],
        'Team': matches['HomeTeam'], 'Opponent': matches['AwayTeam'],
        'is_home': 1,
        'GF': matches['FTHG'], 'GA': matches['FTAG'],
        'SoT': matches['HST'], 'SoTA': matches['AST'],
        'Cor': matches['HC'], 'CorA': matches['AC'],
        'xG': matches['xG_home'], 'xGA': matches['xG_away'],
        'elo': elo_h, 'opp_elo': elo_a, 'elo_post': elo_h_post,
        'Result': matches['FTR'].map({'H': 2, 'D': 1, 'A': 0}),
    })
    away = pd.DataFrame({
        'Date': matches['Date'], 'Season': matches['Season'],
        'Team': matches['AwayTeam'], 'Opponent': matches['HomeTeam'],
        'is_home': 0,
        'GF': matches['FTAG'], 'GA': matches['FTHG'],
        'SoT': matches['AST'], 'SoTA': matches['HST'],
        'Cor': matches['AC'], 'CorA': matches['HC'],
        'xG': matches['xG_away'], 'xGA': matches['xG_home'],
        'elo': elo_a, 'opp_elo': elo_h, 'elo_post': elo_a_post,
        'Result': matches['FTR'].map({'H': 0, 'D': 1, 'A': 2}),
    })
    df = pd.concat([home, away], ignore_index=True).sort_values(['Team', 'Date'])
    df['elo_diff'] = df['elo'] - df['opp_elo']

    # Short-term form: last 5 matches.
    # xG joins the rolling set: only the shift(1) rolling means are ever used
    # as features, never a match's own xG (that would be leakage).
    roll_cols = ['GF', 'GA', 'SoT', 'SoTA', 'Cor', 'CorA', 'xG', 'xGA', 'Result']
    for col in roll_cols:
        df[f'Recent_{col}_avg5'] = (
            df.groupby('Team')[col]
              .transform(lambda s: s.shift(1).rolling(5).mean())
        )

    # Long-term strength proxy: last 20 matches. min_periods lets newly
    # promoted teams get a value once they have played 5 games.
    df['Recent_Result_avg20'] = (
        df.groupby('Team')['Result']
          .transform(lambda s: s.shift(1).rolling(20, min_periods=5).mean())
    )

    # Exponentially weighted form: recent matches count more than older ones.
    df['Recent_Result_ewm'] = (
        df.groupby('Team')['Result']
          .transform(lambda s: s.shift(1).ewm(halflife=5, min_periods=3).mean())
    )

    # Venue-specific form: home form when at home, away form when away.
    df['Recent_Result_venue_avg5'] = (
        df.groupby(['Team', 'is_home'])['Result']
          .transform(lambda s: s.shift(1).rolling(5, min_periods=3).mean())
    )

    # Shots-on-target ratio: share of on-target shots in the team's matches
    # (a linear model cannot form this ratio from the parts by itself).
    df['SoT_ratio5'] = (
        df['Recent_SoT_avg5']
        / (df['Recent_SoT_avg5'] + df['Recent_SoTA_avg5'])
    ).fillna(0.5)

    # xG differential over the last 5: how much better the team's chances
    # were than its opponents'. Underlying performance, less noisy than goals.
    df['xG_diff5'] = df['Recent_xG_avg5'] - df['Recent_xGA_avg5']

    # Finishing luck: goals scored minus goals expected. Positive means the
    # team has been converting above its chance quality (often regresses).
    df['xG_overperf5'] = df['Recent_GF_avg5'] - df['Recent_xG_avg5']

    df['days_rest'] = (
        df.groupby('Team')['Date'].diff().dt.days.clip(upper=21).fillna(7)
    )

    # The opponent's form on the same date — each match has a row for both
    # sides, so a self-merge attaches the opposing team's pre-match form.
    form_cols = ([f'Recent_{c}_avg5' for c in roll_cols]
                 + ['Recent_Result_avg20', 'Recent_Result_ewm',
                    'Recent_Result_venue_avg5', 'SoT_ratio5',
                    'xG_diff5', 'xG_overperf5', 'days_rest'])
    opp_form = df[['Team', 'Date'] + form_cols].rename(
        columns={'Team': 'Opponent', **{c: f'opp_{c}' for c in form_cols}}
    )
    df = df.merge(opp_form, on=['Opponent', 'Date'], how='left')
    df['rest_diff'] = df['days_rest'] - df['opp_days_rest']

    # h2h_record is a rolling mean of Result (0=L, 1=D, 2=W), so missing
    # history must be filled with the neutral value 1.0 — filling with 0
    # would claim the team lost its recent meetings.
    df = df.sort_values(['Team', 'Opponent', 'Date'])
    df['h2h_record'] = (
        df.groupby(['Team', 'Opponent'])['Result']
          .transform(lambda s: s.shift(1).rolling(2).mean())
          .fillna(1.0)
    )

    return df.sort_values('Date').reset_index(drop=True)
