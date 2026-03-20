output "primary_table_arn" {
  description = "The ARN of the DynamoDB table in the primary region"
  value       = aws_dynamodb_table.global_table.arn
}

output "replica_table_arn" {
  description = "The ARN of the DynamoDB table in the replica region"
  value = replace(
    aws_dynamodb_table.global_table.arn, 
    data.aws_region.primary.name, 
    var.replica_regions[0]
  )
}
