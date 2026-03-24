output "primary_table_arn" {
  description = "The ARN of the DynamoDB table in the primary region"
  value       = aws_dynamodb_table.global_table.arn
}

output "replica_table_arn" {
  description = "ARN of the replica DynamoDB table"
  value       = one(aws_dynamodb_table.global_table.replica).arn
}
