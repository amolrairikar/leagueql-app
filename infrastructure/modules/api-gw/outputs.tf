output "api_id" {
  value = aws_apigatewayv2_api.this.id
}

output "invoke_url" {
  value = "${aws_apigatewayv2_stage.default.invoke_url}"
}

output "execution_arn" {
  value = aws_apigatewayv2_api.this.execution_arn
}