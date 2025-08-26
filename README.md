# Credit Card Fraud Detector (Streamlit + scikit-learn)

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Train a baseline model on the Kaggle credit-card fraud dataset and run an interactive Streamlit UI to score transactions and tune decision thresholds.

---

## Features

- **Training** (`train.py`) → exports `artifacts/model.joblib` and `artifacts/feature_stats.json`
- **Streamlit UI** (`streamlit_app.py`) with three tabs:
  - **Batch CSV** (recommended)
  - **JSON Row** (single transaction)
  - **Quick Predict** (what-if)
- **Threshold analysis scripts**
  - `metrics.py` – confusion matrix & metrics at a chosen threshold
  - `metrics_sweep.py` – precision/recall vs threshold (writes `threshold_sweep.csv`)
  - `metrics_topk.py` – evaluate a fixed alert budget (Top-K)
- Clean `.gitignore` to keep large data/artifacts out of Git
- Dockerfile for containerized runs
- (Optional) IaC in `infra/terraform` and an ECR push workflow for deployments

---

## Project structure

```text
credit-card-fraud-detector/
├─ app/                      # backend/infra helpers (optional)
├─ artifacts/                # model + stats (ignored by git)
│  └─ model.joblib
├─ data/                     # place Kaggle CSV here (ignored)
├─ infra/
│  └─ terraform/             # IaC (optional deploy)
├─ notebooks/                # EDA/experiments
├─ scripts/                  # helper scripts
├─ streamlit_app.py          # Streamlit UI (main demo)
├─ train.py                  # train + export artifacts
├─ metrics.py
├─ metrics_sweep.py
├─ metrics_topk.py
├─ requirements.txt
├─ Dockerfile
├─ ecr-push.yml              # GitHub Actions: build & push image
└─ README.md

```

> **Dataset**: “Credit Card Fraud Detection” (Kaggle). Place `creditcard.csv` at `data/creditcard.csv` (do **not** commit it).

---

## Prerequisites

- Python **3.10+**
- (Optional) VS Code
- Kaggle dataset file at `data/creditcard.csv`

---

## Quickstart

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt

# Train and export artifacts (model + feature stats)
python train.py

# Run the UI
streamlit run streamlit_app.py
```
Open the local URL Streamlit prints (usually http://localhost:8501).

## Using the app

### 1) Batch CSV (recommended)
Upload a CSV matching the model schema (`Time, V1..V28, Amount`).  
Click **Run Prediction on CSV**, then **Download all results (CSV)** to get `fraud_scores.csv` with:
- `fraud_probability` – model score for class 1 (fraud)
- `is_fraud_pred` – (1 = fraud, 0 = legit) given your current threshold

### 2) JSON Row (single transaction)
Paste one JSON object. Missing features are filled from `feature_stats.json` (or `0.0` if absent).

```json
{"Time": 10000, "Amount": 250.75}
```
For best accuracy, include full schema (Time, V1..V28, Amount).
### Quick Predict(what if)
Enter Amount (and optional Time); the app fills the rest from medians. Handy for demos, not for production decisions.

### Threshold tuning
Inside the app, adjust the Decision threshold slider:

- Higher threshold → fewer flags (↑ precision, ↓ recall)
  
- Lower threshold → more flags (↑ recall, ↓ precision)


Offline analysis:
```bash
python metrics.py        # Confusion matrix, precision, recall, F1, accuracy
python metrics_sweep.py  # Writes threshold_sweep.csv (precision/recall vs threshold)
python metrics_topk.py   # Evaluate a fixed alert budget (Top-K)
```
Optionally set a default threshold with a tiny config file:
```json
// artifacts/config.json
{"threshold": 0.999}
```
## Training details

`train.py`:
- Loads `data/creditcard.csv`
- Stratified train/validation split
- Baseline **LogisticRegression** with `class_weight="balanced"`
- Exports:
  - `artifacts/model.joblib` (inference pipeline)
  - `artifacts/feature_stats.json` (feature order, medians, ranges)

Re-run `python train.py` whenever you change features or model.

---

## Docker

Build and run locally:

```bash
# Build
docker build -t cc-fraud:latest .

# Run (maps port 8501; mount local dirs to reuse artifacts/data)
docker run --rm -p 8501:8501 \
  -v "$PWD/artifacts:/app/artifacts" \
  -v "$PWD/data:/app/data" \
  cc-fraud:latest
---
``````markdown
Then open http://localhost:8501
`````
---

## Deployment (high level)

- **Push image**: The included GitHub Actions workflow `ecr_push.yaml` can build and push a Docker image to Amazon ECR.
- **Infra**: `infra/terraform` contains Terraform to provision cloud resources (e.g., ECR/ECS/ALB).  
  Fill in variables for your AWS account/region, run `terraform init/plan/apply`, and point the service to the pushed image.

> Configure required GitHub Secrets (AWS creds/region, repo name, etc.) for the ECR workflow.

---

## Troubleshooting

- Missing `artifacts/model.joblib` or `feature_stats.json` → run `python train.py` (and ensure `data/creditcard.csv` exists).
- “Row count mismatch” in metrics → you likely evaluated only Top-K. Re-download **all** predictions or use a join-based approach with a stable `row_id`.
- Port conflict on 8501 → `streamlit run streamlit_app.py --server.port 8502`.
- Streamlit telemetry prompt/opt-out (Windows):

  ```toml
  # %USERPROFILE%\.streamlit\config.toml
  [browser]
  gatherUsageStats = false
  ```
---

## Security & privacy

- Never commit `data/creditcard.csv` or real customer data.
- Run a secret scan before pushing (`gitleaks`, `trufflehog`, etc.).
- This project is for **educational/demo** purposes; calibrate, validate, and govern appropriately for production.

---

## Roadmap (ideas)

- Probability calibration (`CalibratedClassifierCV`)
- Tree-based / boosted models; class-weight vs resampling
- Hyperparameter search & model registry
- SHAP/feature-importance report
- CI: lint/test, data-contract checks

---

## License

MIT – see [LICENSE](LICENSE).



