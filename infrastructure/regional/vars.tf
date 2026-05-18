variable "environment" {
  description = "Deployment environment (dev | prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for regional resources"
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

variable "otel_layer_arn" {
  description = "ARN of the AWS OpenTelemetry Distribution Lambda layer"
  type        = string
}

variable "honeycomb_api_key" {
  description = "Honeycomb API key for trace export"
  type        = string
  sensitive   = true
}

