# Credit Card Fraud Detector — FastAPI + Lambda + Streamlit

Train a scikit-learn model on the credit-card fraud dataset and run a production-style **inference API** (FastAPI) packaged as a **container** and deployed on **AWS Lambda** (via **Amazon ECR**). Optional Streamlit UI for local demos. CI/CD builds and pushes images to ECR.

- **Model:** Logistic Regression (30 features), hold-out **ROC AUC ≈ 0.972**
- **API:** FastAPI (`/healthz`, `/predict`) adapted for Lambda with Mangum
- **Infra:** Container in **ECR**, executed by **AWS Lambda** (Function URL for testing)
- **CI/CD:** GitHub Actions pushes **`:latest`** and **`:<commit-sha7>`** tags (immutable deploys recommended)

---

## Architecture

train.py  --->  artifacts/model.joblib
    |
    v
FastAPI app + Dockerfile  --->  GitHub Actions  --->  Amazon ECR
    |
    v
AWS Lambda (container image)  --->  Function URL (/healthz, /predict)


> Tip: Prefer deploying Lambda with `:<commit-sha7>` instead of `:latest`.

## Repo layout


app/
  __init__.py
  main.py              # FastAPI app (local + Lambda via Mangum)
  lambda_handler.py    # Lambda entrypoint
artifacts/
  model.joblib         # Trained model (from train.py or baked in image)
data/
  creditcard.csv       # (not committed) see “Dataset”
scripts/
  __init__.py
  make_dummy_model.py
  smoke.ps1
streamlit_app.py       # Optional local demo UI
train.py               # Train + evaluate; writes artifacts/*
requirements.txt       # Pinned wheels for Lambda (no compilers)
Dockerfile             # Lambda Python 3.11 base; bakes model
.github/workflows/
  ecr_push.yaml


---

## Quickstart (local, Windows PowerShell)

```powershell
# 1) Create & activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
# 2) Install dependencies
pip install -r requirements.txt

# 3) Train (writes artifacts/model.joblib + artifacts/feature_stats.json)
python .\train.py

# 4) Run API locally
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 5) Health
irm http://127.0.0.1:8000/healthz | ConvertTo-Json -Depth 5

# 6) Predict (30 features)
```
$body = @{ features = @(0.1,0.2,0.3,0.4,0.5,0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0); threshold = 0.5 } |
  ConvertTo-Json -Compress
irm -Method Post -Uri "http://127.0.0.1:8000/predict" -ContentType 'application/json' -Body $body |
  ConvertTo-Json -Depth 5
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

Workflow file path: `.github/workflows/ecr_push.yaml`

```
name: Build and Push to ECR
on:
  push:
    branches: [ main ]
  workflow_dispatch:
jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id:     ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}
      - name: Login to Amazon ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2
      - name: Extract short SHA
        id: vars
        run: echo "SHA7=$(echo ${GITHUB_SHA} | cut -c1-7)" >> $GITHUB_OUTPUT
      - name: Build image
        run: |
          docker build -t ${{ steps.ecr.outputs.registry }}/ccfd-repo:latest \
                       -t ${{ steps.ecr.outputs.registry }}/ccfd-repo:${{ steps.vars.outputs.SHA7 }} .
      - name: Push image
        run: |
          docker push ${{ steps.ecr.outputs.registry }}/ccfd-repo:latest
          docker push ${{ steps.ecr.outputs.registry }}/ccfd-repo:${{ steps.vars.outputs.SHA7 }}
```

> Ensure repo secrets exist: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.  
> Actions must be enabled in **Settings → Actions → General**.

---

## Deploy to AWS Lambda (container image)

**Prereqs:** ECR image exists; IAM role `ccfd-lambda-role` with `AWSLambdaBasicExecutionRole`.

**Create or update**
```powershell
$Profile="YOUR_AWS_PROFILE"; $Region="us-east-1"
$Account="<ACCOUNT_ID>"; $Sha7="<sha7-from-ECR-or-Actions>"
$ImageUri="$Account.dkr.ecr.$Region.amazonaws.com/ccfd-repo:$Sha7"
```
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


**Function URL (quick testing)**
```powershell
aws lambda create-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn --auth-type NONE 2>$null

$FnUrl = aws lambda get-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn --query "FunctionUrl" --output text
"Function URL: $FnUrl"
```

---

## Dataset

Place `data/creditcard.csv` (Kaggle: “Credit Card Fraud Detection”) under `./data/` and run:

```powershell
python .\train.py
```

Outputs:
```
artifacts/model.joblib
artifacts/feature_stats.json
```

---

## License

Code is under the terms in [LICENSE](./LICENSE).  
Dataset licensing is governed by its provider; do not commit or redistribute the raw CSV.
