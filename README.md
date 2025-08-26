# Credit Card Fraud Detector — FastAPI + AWS Lambda (container) + Streamlit

[![Build and Push to ECR](https://github.com/sathwikreddyshamakuri/credit-card-fraud-detector/actions/workflows/ecr-push.yml/badge.svg?branch=main)](https://github.com/sathwikreddyshamakuri/credit-card-fraud-detector/actions/workflows/ecr-push.yml)

Train a scikit-learn model on the credit-card fraud dataset and run a production-style **inference API** (FastAPI) packaged as a **container** and deployed on **AWS Lambda** (via **Amazon ECR**). Includes an optional Streamlit UI for local demos and a GitHub Actions workflow that builds & pushes images to ECR.

- **Model:** Logistic Regression (30 features), hold-out **ROC AUC ≈ 0.972**
- **API:** FastAPI endpoints `GET /healthz`, `POST /predict` (Lambda via Mangum)
- **Infra:** Container image in **ECR**, executed by **AWS Lambda** (Function URL for quick tests)
- **CI/CD:** GitHub Actions builds & pushes `:latest` and `:<commit-sha>` tags for reproducible rollouts

---

## Architecture
```text
├─ train.py ──> artifacts/model.joblib
   │
   ▼
├─ FastAPI app ──(Dockerfile)──> GitHub Actions ──> Amazon ECR
   │
   ▼
├─ AWS Lambda (container image)
   │
   ▼
└─ Function URL: /healthz, /predict
```

> **Tip:** Prefer deploying Lambda with an immutable **commit-SHA tag** (e.g., `:2918ddb`) instead of `:latest`.

## Repo layout
```text
├─ app/
│  ├─ __init__.py
│  ├─ main.py            # FastAPI app (local + Lambda via Mangum)
│  └─ lambda_handler.py  # Lambda entrypoint
├─ artifacts/
│  └─ model.joblib       # Trained model (from train.py or baked in image)
├─ data/
│  └─ creditcard.csv     # Dataset (see Dataset section)
├─ scripts/
│  ├─ __init__.py
│  ├─ make_dummy_model.py
│  └─ smoke.ps1
├─ infra/
│  └─ terraform/         # (IaC sources only)
├─ streamlit_app.py      # Optional local demo UI
├─ train.py              # Train + evaluate model; writes artifacts/*
├─ requirements.txt      # Pinned wheels for Lambda
├─ Dockerfile            # Lambda Python 3.11 base; bakes model
└─ .github/workflows/
   └─ ecr-push.yml       # CI to build & push to ECR
```

---

## Quickstart (local, Windows PowerShell)

```powershell
# 1) Create & activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt

# 3) Train the model (writes artifacts/model.joblib + artifacts/feature_stats.json)
python .	rain.py

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

---

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

- Workflow: `.github/workflows/ecr-push.yml` (badge at top of this README)
- Secrets (Repo → **Settings** → **Secrets and variables** → **Actions**):  
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`  
  Optional env (defaults assumed): `AWS_REGION=us-east-1`, `ECR_REPO=ccfd-repo`
- Output images:
  - `<ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/ccfd-repo:latest`
  - `<ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/ccfd-repo:<commit-sha>`

Trigger a run by pushing to `main` or use **Actions → Build and Push to ECR → Run workflow**.

---

## Deploy to AWS Lambda (container image)

**Prereqs:** ECR image exists; IAM role with policy `AWSLambdaBasicExecutionRole`.

**Create or update function (PowerShell)**
```powershell
$Profile="YOUR_AWS_PROFILE"; $Region="us-east-1"
$Account="<YOUR_ACCOUNT_ID>"; $Repo="ccfd-repo"

# Use newest non-'latest' tag from ECR (or fall back to your current commit)
$Sha7 = aws ecr describe-images --profile $Profile --region $Region --repository-name $Repo `
  --query "reverse(sort_by(imageDetails,& imagePushedAt))[0].imageTags[?@!='latest'] | [0]" --output text
if (-not $Sha7 -or $Sha7 -eq "None" -or $Sha7 -eq "") { $Sha7 = git rev-parse --short=7 HEAD }
$ImageUri = "{0}.dkr.ecr.{1}.amazonaws.com/{2}:{3}" -f $Account, $Region, $Repo, $Sha7

# Get role ARN (create & attach AWSLambdaBasicExecutionRole if missing)
$RoleArn = aws iam get-role --profile $Profile --region $Region --role-name ccfd-lambda-role --query "Role.Arn" --output text

# Create (first time) or update (subsequent)
aws lambda create-function `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --package-type Image `
  --code ImageUri=$ImageUri `
  --role $RoleArn `
  --timeout 15 --memory-size 1024 `
  --environment Variables="{APP_NAME=fraud-inference,MODEL_VERSION=v1,MODEL_PATH=/var/task/artifacts/model.joblib}" 2>$null

aws lambda update-function-code `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --image-uri $ImageUri

# Function URL (public, for quick tests)
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

---

## Dataset

This project expects `data/creditcard.csv` (Kaggle: **“Credit Card Fraud Detection”**). Put the file under `data/` and run `python train.py` to (re)train.

> **Note:** Do **not** commit the dataset to Git.

---

## Security & privacy

- No secrets in code. CI uses GitHub **Actions Secrets** only.  
- Function URL is **public** in quick-start scripts. For production, prefer **AWS_IAM** or API Gateway with auth & CORS.  
- Model artifact (`artifacts/model.joblib`) is baked into the container; rotate image tags for immutable deploys.

---

## License

MIT License — see `LICENSE`.
