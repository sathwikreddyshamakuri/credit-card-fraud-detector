data "aws_ecr_image" "image" {
  repository_name = aws_ecr_repository.repo.name
  image_tag       = var.image_tag
}
resource "aws_cloudwatch_log_group" "lambda_lg" {
  name              = "/aws/lambda/${var.project_name}-fn"
  retention_in_days = 14
}
resource "aws_lambda_function" "fn" {
  function_name = "${var.project_name}-fn"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repo.repository_url}@${data.aws_ecr_image.image.image_digest}"
  timeout       = 10
  memory_size   = 512
  environment {
    variables = {
      APP_NAME      = var.project_name
      MODEL_VERSION = "v1"
      MODEL_PATH    = "/var/task/artifacts/model.joblib"
    }
  }
  depends_on = [aws_iam_role_policy_attachment.basic_logs, aws_cloudwatch_log_group.lambda_lg]
}
