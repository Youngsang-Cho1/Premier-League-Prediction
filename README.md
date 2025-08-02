# ⚽ Premier League Match Prediction

A full-stack machine learning web app that predicts English Premier League match outcomes — given two teams, it returns the most likely result (Win, Draw, or Lose) based on recent form and head-to-head history.
---

## 🛠️ Technologies Used

- 🐍 Python 3.10+
- 🔥 Flask — lightweight backend API
- 🤖 scikit-learn, Random Forest, Gradient Boost, XGBoost — ML model training and prediction
- 📊 pandas, NumPy — data preprocessing
- 🎯 GridSearchCV — model tuning
- 🎨 HTML + CSS + JavaScript — responsive, interactive UI
- 🧠 joblib — model serialization
- 🌐 CORS — cross-origin communication
- 📈 Matplotlib / Seaborn — model evaluation (heatmaps, correlation)

---

## ✨ Features

- 📊 Recent 5-game rolling averages (GF, GA, xG, SoT, FK, etc.)
- 🔁 Head-to-head record encoding & draw rate calculations
- 🔄 Bi-directional prediction logic for better balance
- 📦 REST API returning predictions & probability distribution
- 🎨 Clean, responsive team selector interface with logos & colors
- 🧪 Graceful fallback for teams with no match history due to promotion/relegation

---

## 📦 Local Setup

### 1. Clone the Repo
```bash
git clone https://github.com/your-username/Premier-League-Prediction.git
cd Premier-League-Prediction
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Running the App

```bash
python app.py
```

App will be live at: [http://localhost:5000](http://localhost:5000)

---

## 📡 API Usage

### POST `/predict`

**Request:**
```json
{
  "team1": "Manchester City",
  "team2": "Liverpool"
}
```

**Response:**
```json
{
  "result": 2,
  "probabilities": [0.18, 0.25, 0.57]
}
```
- `result`: 0 = Lose, 1 = Draw, 2 = Win (for team1)
- `probabilities`: order is [Lose, Draw, Win]

---

## 🧠 Project Structure

```
premier-prediction/
├── app.py                 # Flask backend entry
├── premier_model.pkl      # Trained model
├── prem_data.csv          # Cleaned match data
├── requirements.txt
├── notebooks/             
│   ├── Prem_Prediction_Scraping.ipynb     # Web scraping logic
│   └── Prem_Prediction_Model.ipynb        # EDA, feature engineering, model prototyping
├── static/                
│   ├── script.js
│   ├── styles.css
│   └── images/            # team logo png files
├── templates/
│   └── index.html
├── src/
│   ├── preprocessor.py
│   ├── train_model.py
│   └── infer.py
```

---

## 📝 License

MIT License © 2025 Aiden Cho
