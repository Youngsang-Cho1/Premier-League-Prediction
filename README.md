# ⚽ Premier League Match Prediction

A full-stack machine learning web app that predicts English Premier League
match outcomes. Given a home team and an away team, it returns the most likely
result (Win / Draw / Lose) **as a calibrated probability distribution**, based
on both sides' recent form, long-term strength, and head-to-head history.

Beyond the app, the project is built as an **end-to-end MLOps system**: data is
refreshed automatically, the live model is scored against real results every
week, feature drift is monitored, and retraining happens automatically behind a
deployment gate — no manual model babysitting.

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| **Backend / API** | Flask, Gunicorn |
| **ML** | scikit-learn (LogisticRegression, RandomForest, GradientBoosting), XGBoost, isotonic calibration |
| **Data** | pandas, NumPy, football-data.co.uk CSVs |
| **MLOps** | GitHub Actions (CI + scheduled retraining), custom PSI drift detection, pytest |
| **Frontend** | HTML + CSS + JavaScript, Chart.js, GSAP |
| **Deploy** | Docker, Render |

---

## 📊 Which model, and why?

Every training run tunes and calibrates **four candidates** — LogisticRegression,
RandomForest, GradientBoosting, XGBoost — and automatically selects the one with
the lowest **log-loss** on the held-out test season (probability quality is what
matters, since the app serves probabilities, not just an argmax label).

The current winner is **multinomial Logistic Regression** (with `StandardScaler`
+ isotonic calibration). That surprises people who expect gradient boosting to
win, but it's the right answer *for this data*:

- The ~21 features are smooth and mostly monotone (better form → higher win
  probability). Tree ensembles shine on complex interactions; with only ~7k
  training rows they mostly find noise instead.
- A regularized linear model fits this structure cleanly **and** produces
  naturally well-calibrated probabilities.

Model selection is not hardcoded — if a future season's data favors a tree
model, the pipeline will pick it automatically.

### Honest performance

Football 1X2 prediction has a **low ceiling**: even bookmakers — the best
forecasters in the sport — only reach ~53% accuracy. So **accuracy is the wrong
headline metric**; log-loss (probability quality) is the real scorecard.

Benchmarked on the full 2025-26 test season:

| Predictor | Log-loss ↓ | Accuracy |
|---|---|---|
| Random guessing (class prior) | 1.099 | 38.5% |
| "Home team always wins" | — | 42.6% |
| **Our model (21 self-made features)** | **1.027** | ~48% |
| Bookmaker odds (the market) | ~1.02 | ~49% |

The model sits right on the market's shoulder. Adding odds *as a feature* barely
moves it (1.027 → 1.025) — confirming we're already near the information ceiling
of what pre-match form data can extract, not that the model is weak.

> **Why we don't use odds as a feature:** bookmaker odds would let the model
> simply copy the market, defeating the point of "how well can *our own*
> features do?" Instead odds are used only as an **evaluation baseline** — the
> honest yardstick the model is measured against each week.

---

## 🧠 Features

All 21 features are strictly **pre-match** (no data leakage — verified by
tests). The fixture is described symmetrically from both teams' perspectives:

- **Short-term form (last 5):** goals for/against, shots on target for/against, results
- **Long-term strength (last 20):** rolling result average
- **Elo rating:** with home advantage and between-season regression to the mean; handles promoted teams via a below-average starting rating
- **Venue form:** home form when playing at home, away form when away
- **Shots-on-target ratio:** share of on-target shots (a ratio a linear model can't build from parts alone)
- **Rest days & rest difference** between the two sides
- **Head-to-head:** rolling record, with a neutral prior for first meetings

Prediction is **bi-directional**: the fixture is predicted from each team's
perspective and averaged, which balances the home/away framing.

---

## 📡 Data Source & Ingestion

Match data (**2015-16 → current season**, ~4,180 matches) comes from
[**football-data.co.uk**](https://www.football-data.co.uk/englandm.php) — free
season CSVs at stable URLs, **no API key, no web scraping** (the project's
original Selenium/FBref scraper was replaced after it was blocked).

Each season is a plain CSV (e.g. `.../mmz4281/2526/E0.csv`) containing scores,
shots, shots on target, corners, and **B365 bookmaker odds** (kept only as the
evaluation baseline, not as model features).

```bash
python -m src.ingest        # download/refresh -> data/matches.csv
python -m src.train_model   # retrain + calibrate -> premier_model.pkl
```

---

## 🔁 MLOps: Continuous Training

A scheduled GitHub Actions workflow
([`weekly-pipeline.yml`](.github/workflows/weekly-pipeline.yml)) runs every
**Monday during the season** (`src/pipeline.py`):

```
tests → ingest → evaluate → drift check → conditional retrain (gated) → deploy
```

1. **Ingest** — refresh `data/matches.csv`.
2. **Evaluate** (`src/evaluate.py`) — score the *deployed* model on matches
   played in the last 60 days against real results, and against the
   **vig-removed B365 odds baseline**. Every run appends a row to
   `metrics/history.csv`, so model quality (and the gap to the market) is
   tracked over time. Football gives real ground truth within days — a luxury
   most ML projects don't have.
3. **Drift check** (`src/drift.py`) — see below. Writes
   `metrics/drift_latest.json`.
4. **Conditional retrain** (`src/pipeline.py`) — retraining is triggered by
   **evidence, not the calendar**:
   - model log-loss degrades past an absolute threshold, **or**
   - it falls too far behind the odds baseline, **or**
   - feature drift is detected.
5. **Deployment gate** — a retrain candidate trains on everything *older* than a
   held-out gate window, then must **beat the incumbent on that window** before
   it's allowed to replace `premier_model.pkl`. A worse model can never ship.
6. **Deploy** — updated data/metrics/model are committed, and a Render deploy
   hook is triggered (if configured).

### How drift is measured

`src/drift.py` computes the **Population Stability Index (PSI)** for each
feature, comparing the recent-matches distribution against the training-period
reference distribution (quantile-binned):

```
PSI = Σ (curr% − ref%) · ln(curr% / ref%)
```

Conventional reading: **< 0.10** stable, **0.10–0.25** moderate shift,
**> 0.25** significant drift (our alert threshold). EPL drift is *structural* —
every August three promoted teams arrive plus a transfer window — so this is
expected to fire around season boundaries, which is exactly when a retrain check
is warranted. During the off-season (too few recent matches) the check safely
skips.

---

## 🔒 CI/CD & Testing

- **CI** ([`ci.yml`](.github/workflows/ci.yml)) — on every push to `main` and
  every PR, the `tests/` suite runs:
  - **Anti-leakage tests** — assert rolling features never include their own
    match's outcome, and Elo is strictly pre-match. This is what makes automated
    retraining *safe* to trust.
  - **API contract tests** — `/predict` returns valid, summing-to-one
    probabilities; bad input returns 4xx; promoted teams don't crash.
  - **Data schema tests** — required columns, valid scores/odds, expected size.
- **CT (Continuous Training)** — the weekly pipeline above; its retrain gate is
  the model-equivalent of a PR review.
- **CD** — Render auto-deploys on push; the pipeline can also trigger a deploy
  hook after a successful retrain.

```bash
pip install -r requirements.txt
python -m pytest tests/ -q          # run the full suite
python -m src.pipeline --check-only # dry-run the pipeline decision, no retrain
```

---

## 📦 Local Setup

```bash
git clone https://github.com/your-username/Premier-League-Prediction.git
cd Premier-League-Prediction

python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

python app.py                       # http://localhost:5001
```

---

## 📡 API Usage

### `POST /predict`

**Request** — `team1` is the **home** team, `team2` the away team:
```json
{ "team1": "Manchester City", "team2": "Liverpool" }
```

**Response:**
```json
{
  "result": 2,
  "probabilities": [0.18, 0.25, 0.57],
  "insights": { "draw_rate": "20.0%", "count": 12, "history": [] }
}
```
- `result`: 0 = Lose, 1 = Draw, 2 = Win (for `team1`)
- `probabilities`: order is `[Lose, Draw, Win]`
- Invalid/unknown/duplicate teams return HTTP 400 with an `error` message.

---

## 🗂️ Project Structure

```
premier-prediction/
├── app.py                     # Flask backend entry
├── premier_model.pkl          # Trained (calibrated) model — selected by the pipeline
├── data/
│   └── matches.csv            # Master match dataset (from football-data.co.uk)
├── metrics/
│   ├── history.csv            # Weekly model-vs-odds scores over time
│   └── drift_latest.json      # Latest PSI drift report
├── src/
│   ├── ingest.py              # Data download / refresh
│   ├── preprocessor.py        # Leakage-safe feature engineering (rolling, Elo)
│   ├── train_model.py         # Tuning, calibration, model selection
│   ├── infer.py               # Feature assembly + prediction for the app
│   ├── evaluate.py            # Weekly scoring vs real results & odds baseline
│   ├── drift.py               # PSI drift detection
│   └── pipeline.py            # Orchestration + retrain gate
├── tests/                     # Anti-leakage, API, and data-schema tests
├── .github/workflows/
│   ├── ci.yml                 # Tests on every push/PR
│   └── weekly-pipeline.yml    # Scheduled continuous-training pipeline
├── static/ · templates/       # Frontend (JS/CSS, team logos, HTML)
├── notebooks/                 # Archive: original FBref scraping & prototyping
├── Dockerfile · render.yaml   # Deployment
└── requirements.txt
```

---

## 📝 License

MIT License © 2025 Aiden Cho
