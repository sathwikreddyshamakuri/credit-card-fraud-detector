# Credit Card Fraud Detector — FastAPI + Lambda + Streamlit

Train a scikit-learn model on the credit-card fraud dataset and run a production-style **inference API** (FastAPI) packaged as a **container** and deployed on **AWS Lambda** (via **Amazon ECR**). Includes an optional Streamlit UI for local demos and a GitHub Actions workflow that builds & pushes images to ECR.

- **Model:** Logistic Regression (30 features), hold-out **ROC AUC ≈ 0.972**
- **API:** FastAPI (`/healthz`, `/predict`) adapted for Lambda with Mangum
- **Infra:** Container image in **ECR**, executed by **AWS Lambda** (Function URL for testing)
- **CI/CD:** GitHub Actions builds & pushes **`:latest`** and **`:<commit-sha>`** tags for reproducible rollouts

---

## Architecture

[train.py] ──> artifacts/model.joblib
│
▼
[FastAPI app] ──(Dockerfile)──> GitHub Actions ──> Amazon ECR
│
▼
AWS Lambda (container image)
│
▼
Function URL: /healthz, /predict
---


> **Tip:** Deploy Lambda with an immutable **commit-SHA tag** (e.g., `:49f95a8`) instead of `:latest`.

---

## Repo layout

├─ app/
│ ├─ init.py
│ ├─ main.py # FastAPI app (local + Lambda via Mangum)
│ └─ lambda_handler.py # Lambda entrypoint
├─ artifacts/
│ └─ model.joblib # Trained model (from train.py or baked in image)
├─ data/
│ └─ creditcard.csv # Dataset (see Dataset section)
├─ infra/
│ └─ terraform/ # IaC sources (provider cache not committed)
├─ scripts/
│ ├─ make_dummy_model.py # Scaffold helper
│ └─ smoke.ps1 # Simple smoke test
├─ streamlit_app.py # Optional local demo UI
├─ train.py # Train + evaluate model; writes artifacts/*
├─ requirements.txt # Pinned wheels for Lambda (no compilers)
├─ Dockerfile # Lambda Python 3.11 base; bakes model
└─ .github/workflows/
└─ ecr_push.yaml
---


---

## Tech stack

- **Modeling:** scikit-learn, numpy, joblib  
- **Service:** FastAPI, Pydantic v2, Mangum (Lambda adapter), Uvicorn (local)  
- **Infra:** Docker, Amazon ECR, AWS Lambda (container image), CloudWatch Logs  
- **CI/CD:** GitHub Actions

---

## Quickstart (local, Windows PowerShell)

```powershell
# 1) Create & activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt

# 3) Train the model (writes artifacts/model.joblib + artifacts/feature_stats.json)
python .\train.py

# 4) Run API locally
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 5) Health check
irm http://127.0.0.1:8000/healthz | ConvertTo-Json -Depth 5

# 6) Predict (30 features)
$body = @{ features = @(0.1,0.2,0.3,0.4,0.5,0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0); threshold = 0.5 } |
  ConvertTo-Json -Compress
irm -Method Post -Uri "http://127.0.0.1:8000/predict" -ContentType 'application/json' -Body $body |
  ConvertTo-Json -Depth 5

# (Optional) Streamlit UI
streamlit run .\streamlit_app.py
```
## API

**Base:** local `http://127.0.0.1:8000` or your **Lambda Function URL**

- `GET /healthz` → `{"ok": true, "version": "v1", "has_model": true}`
- `POST /predict`
  - **Request**
    ```json
    {
      "features": [0.1, 0.2, "... 30 floats total ..."],
      "threshold": 0.5
    }
    ```
  - **Response**
    ```json
    {
      "request_id": "uuid",
      "model_version": "v1",
      "prob": 0.009,
      "label": 0
    }
    ```

---

## CI/CD (GitHub Actions → ECR)

- Workflow: `.github/workflows/ecr_push.yaml`
- Secrets (Repo → Settings → Secrets and variables → Actions):  
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`  
  Optional env: `AWS_REGION=us-east-1`, `ECR_REGISTRY=<ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com`, `ECR_REPO=ccfd-repo`
- Output images:
<ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/ccfd-repo:latest
<ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/ccfd-repo:<sha7>
---
```sql

---

## Deploy to AWS Lambda (container image)

**Prereqs:** ECR image exists; IAM role with policy `AWSLambdaBasicExecutionRole`.

**Create or update function**
```powershell
$Profile="YOUR_AWS_PROFILE"; $Region="us-east-1"
$Account="<YOUR_ACCOUNT_ID>"; $Sha7="<sha7-from-ECR-or-Actions>"
$ImageUri="$Account.dkr.ecr.$Region.amazonaws.com/ccfd-repo:$Sha7"

# (First time) get/create role and set $RoleArn accordingly
$RoleArn = (aws iam get-role --profile $Profile --region $Region --role-name ccfd-lambda-role --query "Role.Arn" --output text)

# Create (first time)
aws lambda create-function `
--profile $Profile --region $Region `
--function-name ccfd-fn `
--package-type Image `
--code ImageUri=$ImageUri `
--role $RoleArn `
--timeout 15 --memory-size 1024 `
--environment Variables="{APP_NAME=fraud-inference,MODEL_VERSION=v1,MODEL_PATH=/var/task/artifacts/model.joblib}" 2>$null

# Update (subsequent)
aws lambda update-function-code `
--profile $Profile --region $Region `
--function-name ccfd-fn `
--image-uri $ImageUri
```
## Function URL(For Quick Testing)
```powershell
aws lambda create-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --auth-type NONE 2>$null

$FnUrl = aws lambda get-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --query "FunctionUrl" --output text
"Function URL: $FnUrl"
```
## Test (PowerShell)
```powershell
# Health
irm "$FnUrl/healthz" | ConvertTo-Json -Depth 5

# Predict (30 features)
$body = @{ features = @(0.1,0.2,0.3,0.4,0.5,0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0); threshold = 0.5 } |
  ConvertTo-Json -Compress
irm -Method Post -Uri "$FnUrl/predict" -ContentType 'application/json' -Body $body |
  ConvertTo-Json -Depth 5
```
## Data/creditcard.csv

**Get the data:** download `creditcard.csv` from the Kaggle “Credit Card Fraud Detection” dataset page and save it under `./data/`.  
> Note: the dataset’s license/terms are controlled by its provider; do not commit or redistribute the raw CSV in this repo.

After placing the file, you can train and evaluate:

```powershell
python .\train.py
```
This writes the artifacts used by the API:
```bash
artifacts/model.joblib
artifacts/feature_stats.json
```
---
