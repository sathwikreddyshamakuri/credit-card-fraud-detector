# Credit Card Fraud Detector (Streamlit + scikit-learn)

A VS Code project to train a model on the Kaggle credit-card fraud dataset and run an interactive UI for scoring transactions.

---

## Features
- **Training (`train.py`)** → exports `artifacts/model.joblib` and `artifacts/feature_stats.json`
- **Frontend (`app.py`)** → Tabs for **Batch CSV**, **JSON Row**, and **Quick Predict**
- **Threshold tuning** in the app, plus offline scripts:
  - `metrics.py` (confusion matrix at chosen threshold)
  - `metrics_sweep.py` (precision/recall vs threshold; writes `threshold_sweep.csv`)
  - `metrics_topk.py` (evaluate a fixed number of alerts / Top-K)
- Clean `.gitignore` to keep data and large artifacts out of Git

---

## Project structure

credit-card-fraud-detector/
├─ app.py
├─ train.py
├─ metrics.py
├─ metrics_sweep.py
├─ metrics_topk.py
├─ requirements.txt
├─ .gitignore
├─ README.md
├─ data/ # put Kaggle CSV here (ignored)
└─ artifacts/ # model + stats (model ignored by default)
├─ model.joblib
└─ feature_stats.json


---

## Prerequisites
- Python 3.10+
- VS Code (recommended)
- Git (for pushing to GitHub)
- Kaggle dataset: place `creditcard.csv` at `data/creditcard.csv` (do NOT commit it)

---

## Quickstart
~~~bash
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Put Kaggle CSV at:
# data/creditcard.csv

# Train and export artifacts (model + feature stats)
python train.py

# Run UI
streamlit run app.py
~~~

Open the local URL shown (usually http://localhost:8501).

---

## Using the app

### 1) Batch CSV (recommended)
Upload a CSV matching your model’s schema (`Time, V1..V28, Amount`).  
Click **Run Prediction on CSV**, then **Download all results (CSV)** to get `fraud_scores.csv` with:
- `fraud_probability` (model score for class 1 = fraud)
- `is_fraud_pred` (1=fraud, 0=legit) based on the current threshold

### 2) JSON Row (single transaction)
Paste one JSON object. Provide as many features as you can; missing values are filled from `feature_stats.json` (or 0.0 if absent).
~~~json
{"Time": 10000, "Amount": 250.75}
~~~
For best accuracy, paste the full schema (`Time, V1..V28, Amount`).

### 3) Quick Predict (what-if)
Enter **Amount** (and optional **Time**) and the app fills other features from defaults (median). Useful for demos; **not** a substitute for real rows.

---

## Threshold tuning

In the app, move the **Decision threshold** slider. Higher threshold → fewer flags, higher precision; lower threshold → more flags, higher recall.

Offline, you can analyze thresholds with:
~~~bash
python metrics.py        # Confusion matrix at your scored threshold
python metrics_sweep.py  # Writes threshold_sweep.csv with precision/recall vs threshold
python metrics_topk.py   # Evaluate a fixed number of alerts (Top-K)
~~~

**Tip:** You can set a default threshold via a small config:
- Create `artifacts/config.json`:
  ~~~json
  {"threshold": 0.999}
  ~~~
- In `app.py`, read it to initialize the slider (already scaffolded in comments).

---

## Training details

`train.py`:
- Loads `data/creditcard.csv`
- Splits into train/valid (stratified)
- Trains a baseline Logistic Regression with `class_weight="balanced"`
- Exports:
  - `artifacts/model.joblib` (inference pipeline)
  - `artifacts/feature_stats.json` (feature order, medians, and input ranges)

Re-run `python train.py` any time you change the model.

---

## Evaluating predictions

After downloading **all results** from the app as `fraud_scores.csv`, you can compute metrics:
~~~bash
python metrics.py
# prints confusion matrix, precision, recall, F1, accuracy
~~~

If you downloaded only **Top-K**, use a robust join approach:
1) Create dataset with a stable `row_id`:
   ~~~bash
   python make_with_id.py
   ~~~
2) Score `creditcard_with_id.csv`
3) Run a join-based `metrics.py` (included in repo instructions)

---

## Troubleshooting

- **No `model.joblib` / `feature_stats.json` in artifacts**
  - Run `python train.py` (ensure `data/creditcard.csv` exists)
- **Metrics say “Row count mismatch”**
  - You likely downloaded only Top-K. Re-download **all** predictions, or use the join method with `row_id`.
- **Port issue on 8501**
  ~~~bash
  streamlit run app.py --server.port 8502
  ~~~
- **Telemetry prompt / opt-out**
  Create `%USERPROFILE%\.streamlit\config.toml` (Windows):
  ~~~toml
  [browser]
  gatherUsageStats = false
  ~~~

---

## Keep large files out of Git

This repo ships with a `.gitignore` that excludes `data/` and model binaries.  
If you **want** to version the model:
~~~bash
git lfs install
git lfs track "artifacts/*.joblib"
git add .gitattributes artifacts/model.joblib
git commit -m "model: add via Git LFS"
git push
~~~

---


## Notes & Acknowledgements
- Dataset: “Credit Card Fraud Detection” (Kaggle).
- Consider probability calibration (e.g., `CalibratedClassifierCV`) and tree models for improved performance.

## License
MIT (replace with your preferred license)
