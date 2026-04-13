variable "api_name" {
  description = "The name of the API Gateway"
  type        = string
}

variable "api_description" {
  description = "Description of the API"
  type        = string
  default     = "Managed by Terraform"
}

variable "cors_allow_origins" {
  description = "List of origins allowed for CORS handling."
  type        = list(string)
}

variable "lambda_function_name" {
  description = "Name of the Lambda function handling API requests."
  type        = string
}

variable "log_retention_days" {
  description = "Number of days to retain API Gateway logs."
  type        = number
}

variable "openapi_spec_path" {
  description = "The path to the OpenAPI YAML/JSON file"
  type        = string
}

variable "openapi_vars" {
  description = "Map of variables to replace in the OpenAPI spec (e.g., Lambda ARNs)"
  type        = map(string)
  default     = {}
}

variable "stage_name" {
  description = "The name of the deployment stage"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to the resource"
  type        = map(string)
  default     = {}
}

variable "clerk_issuer_url" {
  description = "Clerk Frontend API URL, used as JWT issuer (e.g. https://xxx.clerk.accounts.dev)"
  type        = string
}

variable "clerk_jwt_audience" {
  description = "Audience value that must match the `aud` claim in Clerk session tokens"
  type        = string
}