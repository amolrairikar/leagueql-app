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