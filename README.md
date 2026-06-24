# Credit Card Fraud Detector

[![Build and Push to ECR](https://github.com/sathwikreddyshamakuri/credit-card-fraud-detector/actions/workflows/ecr-push.yml/badge.svg?branch=main)](https://github.com/sathwikreddyshamakuri/credit-card-fraud-detector/actions/workflows/ecr-push.yml)

A scikit-learn fraud detection model (ROC AUC ≈ 0.972) served two ways: a containerized inference API on AWS Lambda, and an interactive Streamlit demo.

**🔗 Try it live:** https://credit-card-fraud-detector-vccedjxmuqhmuiixb6vhj8.streamlit.app
**🔗 Raw API:** https://a6nsppzltewpdh36j3ywsoalfe0gpwgk.lambda-url.us-east-1.on.aws/healthz

---

## What it does

Trains a logistic regression model on the Kaggle "Credit Card Fraud Detection" dataset, then serves predictions two ways:

- **API** — FastAPI app, packaged as a Docker container, deployed on AWS Lambda. `GET /healthz`, `POST /predict`.
- **UI** — a Streamlit app for interactively testing single transactions, batch CSVs, or raw JSON, with an adjustable fraud-threshold slider.

This project started as a model-training exercise for a Machine Learning course; the AWS deployment layer was added afterward to practice packaging and shipping a model as a real, callable service rather than leaving it as a notebook.

---

## Architecture

```
train.py  ──>  artifacts/model.joblib
   │
   ▼
FastAPI app (Dockerfile)  ──>  GitHub Actions  ──>  Amazon ECR
   │
   ▼
AWS Lambda (container image)  ──>  Function URL (/healthz, /predict)
```

**Stack:** Python, scikit-learn, FastAPI, Docker, AWS Lambda (container images), Amazon ECR, GitHub Actions, Streamlit

**Note on `infra/terraform/`:** this directory contains a complete Terraform configuration for the same architecture plus an API Gateway in front of Lambda. It's written and valid, but was never actually applied — the live deployment was provisioned manually via the AWS CLI script below. Running `terraform apply` against this config is the natural next step toward fully IaC-managed deployment.

---

## Repo layout

```
├─ app/
│  ├─ main.py              # FastAPI app (local + Lambda via Mangum)
│  └─ lambda_handler.py    # Lambda entrypoint
├─ artifacts/
│  └─ model.joblib         # Trained model
├─ infra/terraform/        # IaC for Lambda + ECR + API Gateway (written, not yet applied)
├─ scripts/
│  ├─ deploy-lambda.ps1    # Create/update the Lambda function from an ECR image
│  ├─ smoke.ps1            # Quick health/predict/metrics check against a running API
│  └─ make_dummy_model.py
├─ streamlit_app.py        # Interactive demo UI
├─ train.py                # Train + evaluate the model
└─ .github/workflows/
   └─ ecr-push.yml         # CI: build & push container image to ECR on push to main
```

---

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

python train.py                  # writes artifacts/model.joblib + feature_stats.json
uvicorn app.main:app --reload --port 8000

# or, for the interactive UI:
streamlit run streamlit_app.py
```

> The Streamlit Cloud deployment runs on Python 3.11 — `requirements.txt` is pinned to versions that have prebuilt wheels for 3.11/3.12. Building from source on newer Python versions (e.g. 3.14) will fail on `scipy`/`numpy`.

---

## API

* `GET /healthz` → `{"ok": true, "version": "v1", "has_model": true}`
* `POST /predict`
  ```json
  // request
  { "features": [0.1, 0.2, "... 30 floats total ..."], "threshold": 0.5 }

  // response
  { "request_id": "uuid", "model_version": "v1", "prob": 0.009, "label": 0 }
  ```

Run `scripts/smoke.ps1 -ApiUrl <your-url>` for a quick end-to-end check of `/healthz`, `/predict`, and `/metrics`.

---

## Deploying

1. Push to `main` — GitHub Actions builds the Docker image and pushes it to ECR (`.github/workflows/ecr-push.yml`)
2. Run `scripts/deploy-lambda.ps1` to point the Lambda function at the new image and ensure a Function URL exists

ECR has a lifecycle policy keeping only the 3 most recent image tags, so old builds don't accumulate storage cost.

---

## Dataset

Expects `data/creditcard.csv` (Kaggle: "Credit Card Fraud Detection"). Not committed to this repo — download it separately and run `python train.py` to train.

---

## Security & privacy

- No secrets in code or committed config; CI uses GitHub Actions Secrets.
- The Lambda Function URL is intentionally public (`auth-type NONE`) for quick demo purposes. For a production deployment, this should sit behind API Gateway with proper auth, or use `AWS_IAM` auth on the Function URL itself.
- IAM role (`ccfd-lambda-role`) uses the AWS-managed `AWSLambdaBasicExecutionRole` — sufficient here since the function only needs to write CloudWatch logs, nothing else.

---

## License

MIT — see `LICENSE`.