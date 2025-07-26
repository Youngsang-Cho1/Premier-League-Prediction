import pandas as pd

def load_and_clean(filepath):
    df = pd.read_csv(filepath)

    # Drop unnecessary columns
    df = df.drop(columns = ['xG_x']).rename(columns = {'xG_y': 'xG'})
    df = df.drop(columns = ['Tkl.1'])
    useless_cols = [
        'Unnamed: 0', 'Time', 'Comp', 'Round', 'Day', 'Attendance',
        'Captain', 'Formation', 'Opp Formation', 'Referee',
        'Match Report', 'Notes'
    ]
    df = df.drop(columns=useless_cols)

    # Standardize team names
    team_dict = {
        'Manchester-City': 'Manchester City',
        'Arsenal': 'Arsenal',
        'Liverpool': 'Liverpool',
        'Aston-Villa': 'Aston Villa',
        'Tottenham-Hotspur': 'Tottenham',
        'Chelsea': 'Chelsea',
        'Newcastle-United': 'Newcastle Utd',
        'Manchester-United': 'Manchester Utd',
        'West-Ham-United': 'West Ham',
        'Crystal-Palace': 'Crystal Palace',
        'Brighton-and-Hove-Albion': 'Brighton',
        'Bournemouth': 'Bournemouth',
        'Fulham': 'Fulham',
        'Wolverhampton-Wanderers': 'Wolves',
        'Everton': 'Everton',
        'Brentford': 'Brentford',
        'Nottingham-Forest': "Nott'ham Forest",
        'Luton-Town': 'Luton Town',
        'Burnley': 'Burnley',
        'Sheffield-United': 'Sheffield Utd',
        'Leicester-City': 'Leicester City',
        'Leeds-United': 'Leeds United',
        'Southampton': 'Southampton',
        'Watford': 'Watford',
        'Norwich-City': 'Norwich City'
    }
    df['Team'] = df['Team'].map(team_dict)
    df['Date'] = pd.to_datetime(df['Date'])
    df['is_home'] = (df['Venue'] == 'Home').astype(int)
    df['Opponent_code'] = df['Opponent'].astype('category').cat.codes

    df = df.sort_values(['Team', 'Date'])

    df['xG_diff'] = df['xG'] - df['xGA']
    df['Result'] = df['Result'].map({'W': 2, 'D': 1, 'L': 0})

    roll_cols = ['GF','GA','SoT','FK','PK','xG_diff','Result']
    df = df.groupby('Team').apply(lambda x: add_rolling_stats(x, roll_cols, 5, 'Recent'))

    df = df.reset_index(drop=True)

    df['Draw_rate_3'] = (
    df.groupby('Team')['Result'] 
    .apply(lambda x: 
        x.shift(1).rolling(window = 3)
        .apply(lambda y: (y == 1).mean())
        ).reset_index(level = 0, drop = True)
    ) 
    df['Last_match_draw'] = df.groupby('Team')['Result'].shift(1).eq(1).astype(int)

    df = df.sort_values(['Team','Opponent','Date'])
    df['h2h_record'] = (df.groupby(['Team', 'Opponent'])['Result']
                          .apply(lambda x: x.shift(1).rolling(2).mean())
                          .reset_index(level=[0, 1], drop=True)
                          .fillna(0))
    print(df.columns)
    return df


def add_rolling_stats(df, cols, window, prefix):
    roll = df[cols].shift(1).rolling(window).mean()
    roll.columns = [f"{prefix}_{col}_avg{window}" for col in cols]
    return pd.concat([df, roll], axis=1)
