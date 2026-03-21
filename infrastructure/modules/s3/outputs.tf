output "primary_bucket_id" {
  description = "The name of the primary bucket."
  value       = aws_s3_bucket.primary.id
}

output "primary_bucket_arn" {
  description = "The ARN of the primary bucket. Will be of format arn:aws:s3:::bucketname."
  value       = aws_s3_bucket.primary.arn
}

output "secondary_bucket_id" {
  description = "The name of the secondary bucket."
  value       = aws_s3_bucket.primary.id
}

output "secondary_bucket_arn" {
  description = "The ARN of the secondary bucket. Will be of format arn:aws:s3:::bucketname."
  value       = aws_s3_bucket.primary.arn
}