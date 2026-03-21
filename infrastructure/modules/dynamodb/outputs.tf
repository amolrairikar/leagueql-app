output "primary_table_arn" {
  description = "The ARN of the DynamoDB table in the primary region"
  value       = aws_dynamodb_table.global_table.arn
}
