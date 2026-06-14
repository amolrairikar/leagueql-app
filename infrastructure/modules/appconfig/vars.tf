variable "application_name" {
  description = "Name of the AppConfig application (passed to the Lambdas as APPCONFIG_APPLICATION)"
  type        = string
}

variable "environment_name" {
  description = "Name of the AppConfig environment (passed to the Lambdas as APPCONFIG_ENVIRONMENT)"
  type        = string
}

variable "profile_name" {
  description = "Name of the feature-flag configuration profile (passed to the Lambdas as APPCONFIG_PROFILE)"
  type        = string
  default     = "feature-flags"
}

variable "environment" {
  description = "Deployment environment label (dev, prod) used in descriptions and the strategy name"
  type        = string
}

variable "region" {
  description = "AWS region this AppConfig instance is created in (used to build the data-plane ARN)"
  type        = string
}

variable "account_id" {
  description = "The 12 digit AWS account ID (used to build the data-plane ARN)"
  type        = string
}

variable "tags" {
  description = "Tags to apply to the AppConfig resources"
  type        = map(string)
  default     = {}
}
