"""Download EPL match data from football-data.co.uk (free, no key, no scraping).

Each season is a plain CSV at a stable URL. Running this module refreshes
data/matches.csv, the master match-level dataset used by the pipeline.
"""
import io
import requests
import pandas as pd

SEASONS = ['1516', '1617', '1718', '1819', '1920', '2021',
           '2122', '2223', '2324', '2425', '2526']
URL = 'https://www.football-data.co.uk/mmz4281/{season}/E0.csv'

# B365 odds are NOT model features — they are kept as the market baseline
# that the weekly evaluation job compares the model against.
KEEP_COLS = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
             'HS', 'AS', 'HST', 'AST', 'HC', 'AC',
             'B365H', 'B365D', 'B365A']

# football-data.co.uk names -> display names already used by the frontend
TEAM_NAMES = {
    'Man City': 'Manchester City',
    'Man United': 'Manchester Utd',
    'Newcastle': 'Newcastle Utd',
    "Nott'm Forest": "Nott'ham Forest",
    'Sheffield United': 'Sheffield Utd',
    'Leicester': 'Leicester City',
    'Leeds': 'Leeds United',
    'Norwich': 'Norwich City',
    'Luton': 'Luton Town',
    'Ipswich': 'Ipswich Town',
}


def fetch_season(season):
    resp = requests.get(URL.format(season=season), timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.content.decode('utf-8-sig', errors='replace')))
    df = df.dropna(subset=['HomeTeam', 'AwayTeam'])[KEEP_COLS].copy()
    df['Season'] = f'20{season[:2]}-{season[2:]}'
    return df


def main():
    frames = []
    for season in SEASONS:
        df = fetch_season(season)
        print(f'{df["Season"].iloc[0]}: {len(df)} matches')
        frames.append(df)

    matches = pd.concat(frames, ignore_index=True)
    # Older seasons use dd/mm/yy, newer ones dd/mm/yyyy
    matches['Date'] = pd.to_datetime(matches['Date'], format='mixed', dayfirst=True)
    for col in ['HomeTeam', 'AwayTeam']:
        matches[col] = matches[col].replace(TEAM_NAMES)
    matches = matches.sort_values('Date').reset_index(drop=True)

    matches.to_csv('data/matches.csv', index=False)
    print(f'\nSaved {len(matches)} matches '
          f'({matches["Date"].min():%Y-%m-%d} ~ {matches["Date"].max():%Y-%m-%d}) '
          f'to data/matches.csv')


if __name__ == '__main__':
    main()
