# Credit Card Fraud Detector — FastAPI + Lambda + Streamlit

Train a scikit-learn model on the credit-card fraud dataset and run a production-style *inference API* (FastAPI) packaged as a *container* and deployed on *AWS Lambda* (via *Amazon ECR*). Optional Streamlit UI for local demos. CI/CD builds and pushes images to ECR.

- *Model:* Logistic Regression (30 features), hold-out *ROC AUC ≈ 0.972*
- *API:* FastAPI (/healthz, /predict) adapted for Lambda with Mangum
- *Infra:* Container in *ECR, executed by **AWS Lambda* (Function URL for testing)
- *CI/CD:* GitHub Actions pushes **:latest** and **:<commit-sha7>** tags (immutable deploys recommended)

---

## Architecture

text
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


> Tip: Prefer deploying Lambda with **:<commit-sha7>** instead of :latest.

---

## Repo layout

text
├─ app/
│  ├─ __init__.py
│  ├─ main.py              # FastAPI app (local + Lambda via Mangum)
│  └─ lambda_handler.py    # Lambda entrypoint
├─ artifacts/
│  └─ model.joblib         # Trained model (from train.py or baked in image)
├─ data/
│  └─ creditcard.csv       # (not committed) see “Dataset”
├─ scripts/
│  ├─ __init__.py
│  ├─ make_dummy_model.py
│  └─ smoke.ps1
├─ streamlit_app.py        # Optional local demo UI
├─ train.py                # Train + evaluate; writes artifacts/*
├─ requirements.txt        # Pinned wheels for Lambda (no compilers)
├─ Dockerfile              # Lambda Python 3.11 base; bakes model
└─ .github/workflows/
   └─ ecr_push.yaml


---

## Quickstart (local, Windows PowerShell)

powershell
# 1) Create & activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt

# 3) Train (writes artifacts/model.joblib + artifacts/feature_stats.json)
python .	rain.py

# 4) Run API locally
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 5) Health
irm http://127.0.0.1:8000/healthz | ConvertTo-Json -Depth 5

# 6) Predict (30 features)
$body = @{ features = @(0.1,0.2,0.3,0.4,0.5,0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0); threshold = 0.5 } |
  ConvertTo-Json -Compress
irm -Method Post -Uri "http://127.0.0.1:8000/predict" -ContentType 'application/json' -Body $body |
  ConvertTo-Json -Depth 5


---

## API

*Base:* local http://127.0.0.1:8000 or your *Lambda Function URL*

- GET /healthz → {"ok": true, "version": "v1", "has_model": true}
- POST /predict
  - *Request*
    json
    {
      "features": [0.1, 0.2, "... 30 floats total ..."],
      "threshold": 0.5
    }
    
  - *Response*
    json
    {
      "request_id": "uuid",
      "model_version": "v1",
      "prob": 0.009,
      "label": 0
    }
    

---

## CI/CD (GitHub Actions → ECR)

Workflow: .github/workflows/ecr_push.yaml  
Secrets (Repo → Settings → Secrets and variables → Actions):
- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
- Optional env: AWS_REGION=us-east-1, ECR_REGISTRY=<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com, ECR_REPO=ccfd-repo

*Images pushed*
text
<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ccfd-repo:latest
<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ccfd-repo:<commit-sha7>   # recommended for deploys


---

## Deploy to AWS Lambda (container image)

*Prereqs:* ECR image exists; IAM role with AWSLambdaBasicExecutionRole.

*Create or update*
powershell
$Profile="YOUR_AWS_PROFILE"; $Region="us-east-1"
$Account="<ACCOUNT_ID>"; $Sha7="<sha7-from-ECR-or-Actions>"
$ImageUri="$Account.dkr.ecr.$Region.amazonaws.com/ccfd-repo:$Sha7"

# First time
$RoleArn = aws iam get-role --profile $Profile --region $Region --role-name ccfd-lambda-role --query "Role.Arn" --output text
aws lambda create-function `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --package-type Image --code ImageUri=$ImageUri `
  --role $RoleArn --timeout 15 --memory-size 1024 `
  --environment Variables="{APP_NAME=fraud-inference,MODEL_VERSION=v1,MODEL_PATH=/var/task/artifacts/model.joblib}" 2>$null

# Update next times
aws lambda update-function-code `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --image-uri $ImageUri


*Function URL (quick testing)*
powershell
aws lambda create-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn --auth-type NONE 2>$null

$FnUrl = aws lambda get-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn --query "FunctionUrl" --output text
"Function URL: $FnUrl"


> For production, consider --auth-type AWS_IAM or fronting with API Gateway.

---

## Dataset

Place data/creditcard.csv (Kaggle: “Credit Card Fraud Detection”) under ./data/.  
The CSV is *not* committed. After download:

powershell
python .	rain.py


Outputs:
text
artifacts/model.joblib
artifacts/feature_stats.json


---

## License

Code is under the terms in [LICENSE](./LICENSE).  
Dataset licensing is governed by its provider; do not commit or redistribute the raw CSV.
