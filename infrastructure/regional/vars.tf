variable "environment" {
  description = "Deployment environment (dev | prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for regional resources"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN for the Lambda function execution role"
  type        = string
}