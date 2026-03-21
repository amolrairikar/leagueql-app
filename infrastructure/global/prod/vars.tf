variable "environment" {
  description = "The environment (dev, prod) to deploy to"
  type        = string
}

variable "account_id" {
  description = "The 12 digit ID for the AWS account to deploy to"
  type        = string
}