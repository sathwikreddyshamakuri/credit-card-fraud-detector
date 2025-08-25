output "api_url" { value = aws_apigatewayv2_api.http.api_endpoint }
output "ecr_repository_url" { value = aws_ecr_repository.repo.repository_url }
