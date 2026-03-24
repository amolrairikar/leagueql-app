variable "environment" {
  description = "Deployment environment (dev | prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for regional resources"
  type        = string
}

variable "onboarder_lambda_role_arn" {
  description = "IAM role ARN for the onboarder Lambda function execution role"
  type        = string
}

variable "processor_lambda_role_arn" {
  description = "IAM role ARN for the processor Lambda function execution role"
  type        = string
}

variable "api_lambda_role_arn" {
  description = "IAM role ARN for the API Lambda function execution role"
  type        = string
}