# deploy-lambda.ps1
# Builds/pushes a new image is handled by GitHub Actions (.github/workflows/ecr-push.yml).
# This script creates or updates the Lambda function from an existing ECR image tag,
# and exposes a public Function URL for quick testing.

param(
    [string]$Profile = "default",
    [string]$Region  = "us-east-1",
    [string]$Account = "<YOUR_ACCOUNT_ID>",
    [string]$Repo    = "ccfd-repo"
)

# Use the newest non-'latest' tag from ECR (falls back to current commit SHA)
$Sha7 = aws ecr describe-images --profile $Profile --region $Region --repository-name $Repo `
  --query "reverse(sort_by(imageDetails,& imagePushedAt))[0].imageTags[?@!='latest'] | [0]" --output text
if (-not $Sha7 -or $Sha7 -eq "None" -or $Sha7 -eq "") { $Sha7 = git rev-parse --short=7 HEAD }
$ImageUri = "{0}.dkr.ecr.{1}.amazonaws.com/{2}:{3}" -f $Account, $Region, $Repo, $Sha7

# Get the Lambda execution role ARN (create it first if missing, with AWSLambdaBasicExecutionRole attached)
$RoleArn = aws iam get-role --profile $Profile --region $Region --role-name ccfd-lambda-role --query "Role.Arn" --output text

# Create the function (first deployment only — fails silently if it already exists)
aws lambda create-function `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --package-type Image `
  --code ImageUri=$ImageUri `
  --role $RoleArn `
  --timeout 15 --memory-size 1024 `
  --environment Variables="{APP_NAME=fraud-inference,MODEL_VERSION=v1,MODEL_PATH=/var/task/artifacts/model.joblib}" 2>$null

# Update the function code (subsequent deployments)
aws lambda update-function-code `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --image-uri $ImageUri

# Create a public Function URL for quick testing (fails silently if it already exists)
aws lambda create-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --auth-type NONE 2>$null

$FnUrl = aws lambda get-function-url-config `
  --profile $Profile --region $Region `
  --function-name ccfd-fn `
  --query "FunctionUrl" --output text

Write-Host "Function URL: $FnUrl"
