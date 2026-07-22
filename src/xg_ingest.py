"""Per-match expected-goals (xG) from Understat.

football-data.co.uk (our primary source) has no xG, so this pulls it from
Understat's league endpoint — the same JSON its own front end consumes:

    GET https://understat.com/main/getLeagueData/EPL/{season}
    -> {"dates": [{h, a, goals, xG: {h, a}, datetime, ...}, ...], ...}

Output: data/xg.csv with one row per match (Date, HomeTeam, AwayTeam, xG_home,
xG_away), team names normalized to the names used in data/matches.csv so the
two join cleanly.

This is a secondary, best-effort source: it is scraped from an unofficial
endpoint and may break. Everything downstream treats xG as optional — if this
file is missing or stale, the model still trains on the primary features.
"""
import os

import pandas as pd
import requests

_URL = 'https://understat.com/main/getLeagueData/EPL/{season}'
_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://understat.com/',
}
_TIMEOUT = 20

# Understat season keys: 2015 == the 2015-16 season, matching our Season
# column ("2015-16"). Keep in sync with src.ingest.SEASONS.
SEASONS = list(range(2015, 2026))

OUTPUT_PATH = 'data/xg.csv'

# Understat display names -> the names used in data/matches.csv
TEAM_NAMES = {
    'Manchester United': 'Manchester Utd',
    'Newcastle United': 'Newcastle Utd',
    'Nottingham Forest': "Nott'ham Forest",
    'Sheffield United': 'Sheffield Utd',
    'Wolverhampton Wanderers': 'Wolves',
    'West Bromwich Albion': 'West Brom',
    'Leeds': 'Leeds United',
    'Leicester': 'Leicester City',
    'Norwich': 'Norwich City',
    'Luton': 'Luton Town',
    'Ipswich': 'Ipswich Town',
}


def _norm(name):
    return TEAM_NAMES.get(name, name)


def fetch_season(season):
    """Return played matches with xG for one Understat season key."""
    resp = requests.get(_URL.format(season=season), headers=_HEADERS,
                        timeout=_TIMEOUT)
    resp.raise_for_status()
    rows = []
    for m in resp.json().get('dates', []):
        if not m.get('isResult'):
            continue  # future fixture: no xG yet
        # Understat timestamps are UTC, so a late kickoff can land on the
        # next calendar day versus football-data's local date. Shifting back
        # a few hours puts every match on its local matchday.
        local_day = (pd.to_datetime(m['datetime']) - pd.Timedelta(hours=3)).normalize()
        rows.append({
            'Date': local_day,
            'HomeTeam': _norm(m['h']['title']),
            'AwayTeam': _norm(m['a']['title']),
            'xG_home': float(m['xG']['h']),
            'xG_away': float(m['xG']['a']),
        })
    return rows


def main(output_path=OUTPUT_PATH):
    rows = []
    for season in SEASONS:
        season_rows = fetch_season(season)
        print(f'{season}-{str(season + 1)[2:]}: {len(season_rows)} matches')
        rows.extend(season_rows)

    df = pd.DataFrame(rows).sort_values('Date').reset_index(drop=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f'\nSaved {len(df)} matches with xG '
          f'({df["Date"].min():%Y-%m-%d} ~ {df["Date"].max():%Y-%m-%d}) '
          f'to {output_path}')


if __name__ == '__main__':
    main()
