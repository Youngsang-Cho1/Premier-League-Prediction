"""Dixon-Coles Poisson goal model (Dixon & Coles, 1997).

Instead of classifying W/D/L directly, this models the number of goals each
team scores as Poisson-distributed, then derives outcome probabilities from
the full scoreline distribution. Each team gets an attack and a defense
strength; a home-advantage term and a low-score correction (rho) complete it.

Why it complements the classifier:
  - draws fall out structurally as P(0-0)+P(1-1)+P(2-2)+...
  - it predicts scorelines ("most likely 2-1"), not just an outcome
  - being a different model family, it is a genuine ensemble ingredient

Expected goals:
  lambda_home = exp(attack_home - defense_away + home_adv)
  lambda_away = exp(attack_away - defense_home)

The Dixon-Coles tau term inflates/deflates the four low-scoring results
(0-0, 1-0, 0-1, 1-1) that a plain independent-Poisson model gets wrong,
which is precisely where draws live.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

MAX_GOALS = 10          # scoreline grid upper bound; P(>10 goals) is negligible
_SORTED_OUTCOMES = ['L', 'D', 'W']


def _tau(hg, ag, lam_h, lam_a, rho):
    """Dixon-Coles low-score correction for the four results 0-0/1-0/0-1/1-1."""
    tau = np.ones_like(hg, dtype=float)
    tau = np.where((hg == 0) & (ag == 0), 1 - lam_h * lam_a * rho, tau)
    tau = np.where((hg == 0) & (ag == 1), 1 + lam_h * rho, tau)
    tau = np.where((hg == 1) & (ag == 0), 1 + lam_a * rho, tau)
    tau = np.where((hg == 1) & (ag == 1), 1 - rho, tau)
    return tau


def _time_weights(dates, xi):
    """Exponential decay so recent matches matter more (half-life via xi).
    xi in units of 1/days; xi=0 disables weighting."""
    if xi <= 0:
        return np.ones(len(dates))
    age_days = (dates.max() - dates).dt.days.to_numpy()
    return np.exp(-xi * age_days)


class DixonColesModel:
    def __init__(self, xi=0.0018):
        # xi ~0.0018/day => weight halves after ~1 year, matching a season cycle
        self.xi = xi
        self.teams = None
        self.params = None  # attack[.], defense[.], home_adv, rho

    def _unpack(self, theta):
        n = len(self.teams)
        attack = dict(zip(self.teams, theta[:n]))
        defense = dict(zip(self.teams, theta[n:2 * n]))
        return attack, defense, theta[-2], theta[-1]  # home_adv, rho

    def fit(self, matches):
        """matches: DataFrame with HomeTeam, AwayTeam, FTHG, FTAG, Date."""
        self.teams = sorted(set(matches['HomeTeam']) | set(matches['AwayTeam']))
        idx = {t: i for i, t in enumerate(self.teams)}
        n = len(self.teams)

        hi = matches['HomeTeam'].map(idx).to_numpy()
        ai = matches['AwayTeam'].map(idx).to_numpy()
        hg = matches['FTHG'].to_numpy()
        ag = matches['FTAG'].to_numpy()
        w = _time_weights(matches['Date'], self.xi)

        def neg_log_likelihood(theta):
            attack = theta[:n]
            defense = theta[n:2 * n]
            home_adv, rho = theta[-2], theta[-1]
            lam_h = np.exp(attack[hi] - defense[ai] + home_adv)
            lam_a = np.exp(attack[ai] - defense[hi])
            tau = _tau(hg, ag, lam_h, lam_a, rho)
            tau = np.clip(tau, 1e-9, None)  # keep log finite
            ll = (np.log(tau)
                  + poisson.logpmf(hg, lam_h)
                  + poisson.logpmf(ag, lam_a))
            return -np.sum(w * ll)

        # attack/defense start at 0; identifiability via mean-attack=0 constraint
        theta0 = np.concatenate([np.zeros(2 * n), [0.25, -0.1]])
        constraint = {'type': 'eq', 'fun': lambda t: np.sum(t[:n])}
        res = minimize(neg_log_likelihood, theta0, method='SLSQP',
                       constraints=[constraint],
                       options={'maxiter': 200, 'ftol': 1e-7})
        self.params = self._unpack(res.x)
        return self

    def _score_matrix(self, home, away):
        attack, defense, home_adv, rho = self.params
        # unknown (promoted) teams fall back to league-average strength (0)
        a_h = attack.get(home, 0.0)
        d_h = defense.get(home, 0.0)
        a_a = attack.get(away, 0.0)
        d_a = defense.get(away, 0.0)
        lam_h = np.exp(a_h - d_a + home_adv)
        lam_a = np.exp(a_a - d_h)

        goals = np.arange(MAX_GOALS + 1)
        ph = poisson.pmf(goals, lam_h)
        pa = poisson.pmf(goals, lam_a)
        mat = np.outer(ph, pa)  # mat[i, j] = P(home i, away j)

        # apply Dixon-Coles correction to the 2x2 low-score corner
        for (i, j) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            mat[i, j] *= _tau(np.array(i), np.array(j), lam_h, lam_a, rho)
        return mat / mat.sum()

    def predict_proba(self, home, away):
        """Return [P(loss), P(draw), P(win)] from the home team's view."""
        mat = self._score_matrix(home, away)
        p_win = np.tril(mat, -1).sum()   # home goals > away goals
        p_draw = np.trace(mat)
        p_loss = np.triu(mat, 1).sum()
        return np.array([p_loss, p_draw, p_win])

    def predict_scoreline(self, home, away):
        """Most likely exact scoreline as (home_goals, away_goals)."""
        mat = self._score_matrix(home, away)
        i, j = np.unravel_index(mat.argmax(), mat.shape)
        return int(i), int(j)
