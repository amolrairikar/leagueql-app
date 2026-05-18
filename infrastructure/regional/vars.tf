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

variable "new_relic_license_key" {
  description = "New Relic ingest license key"
  type        = string
  sensitive   = true
}

variable "new_relic_extension_layer_arn" {
  description = "ARN of the NewRelicLambdaExtension layer for the deployment region"
  type        = string
}
