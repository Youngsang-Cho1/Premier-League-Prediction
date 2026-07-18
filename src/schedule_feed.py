"""Upcoming-fixtures feed for the schedule page.

Primary source: the free FPL API (future fixtures + team-name mapping).
Off-season fallback: the most recent played round from our own dataset, so
the page always has real matches to show. Team names are normalized to the
display names used elsewhere in the app.
"""
import pandas as pd
import requests

_FPL_FIXTURES = 'https://fantasy.premierleague.com/api/fixtures/?future=1'
_FPL_BOOTSTRAP = 'https://fantasy.premierleague.com/api/bootstrap-static/'
_HEADERS = {'User-Agent': 'Mozilla/5.0'}

# FPL team names -> the display names used across the app / logo filenames.
_FPL_TEAM_NAMES = {
    'Man City': 'Manchester City',
    'Man Utd': 'Manchester Utd',
    'Spurs': 'Tottenham',
    'Newcastle': 'Newcastle Utd',
    "Nott'm Forest": "Nott'ham Forest",
    'Sheffield Utd': 'Sheffield Utd',
    'Luton': 'Luton Town',
    'Leeds': 'Leeds United',
    'Norwich': 'Norwich City',
    'Leicester': 'Leicester City',
    'Ipswich': 'Ipswich Town',
}


def _norm(name):
    return _FPL_TEAM_NAMES.get(name, name)


def _from_fpl():
    """Return upcoming fixtures from FPL, or [] if none/unavailable."""
    try:
        fx = requests.get(_FPL_FIXTURES, headers=_HEADERS, timeout=15).json()
        if not fx:
            return []
        boot = requests.get(_FPL_BOOTSTRAP, headers=_HEADERS, timeout=15).json()
        teams = {t['id']: t['name'] for t in boot['teams']}
    except Exception:
        return []

    out = []
    for m in fx:
        if not m.get('kickoff_time') or m.get('team_h') not in teams:
            continue
        kickoff = pd.to_datetime(m['kickoff_time'])
        out.append({
            'day': kickoff.strftime('%a'),
            'date': kickoff.strftime('%b %d'),
            'time': kickoff.strftime('%H:%M'),
            'home': _norm(teams[m['team_h']]),
            'away': _norm(teams[m['team_a']]),
        })
    return out[:10]


def _from_recent_data(data_path='data/matches.csv'):
    """Fallback: the most recent played round from our own dataset."""
    df = pd.read_csv(data_path, parse_dates=['Date'])
    last_date = df['Date'].max()
    recent = df[df['Date'] >= last_date - pd.Timedelta(days=4)].tail(10)
    fixtures = []
    for r in recent.itertuples():
        fixtures.append({
            'day': r.Date.strftime('%a'),
            'date': r.Date.strftime('%b %d'),
            'time': '—',
            'home': r.HomeTeam,
            'away': r.AwayTeam,
        })
    return fixtures


def upcoming_fixtures():
    """(fixtures, is_past). is_past=True means the FPL feed had no future
    fixtures (off-season) and we fell back to recent played matches."""
    fixtures = _from_fpl()
    if fixtures:
        return fixtures, False
    return _from_recent_data(), True
