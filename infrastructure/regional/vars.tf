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

variable "clerk_issuer_url" {
  description = "Clerk Frontend API URL, used as JWT issuer (e.g. https://xxx.clerk.accounts.dev)"
  type        = string
}

variable "clerk_jwt_audience" {
  description = "Audience value that must match the `aud` claim in Clerk session tokens"
  type        = string
}

variable "anthropic_api_key" {
  description = "Anthropic API key for AI recap generation in the processor Lambda"
  type        = string
  sensitive   = true
}