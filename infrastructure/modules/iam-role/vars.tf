variable "role_name" {
  description = "The name of the IAM role"
  type        = string
}

variable "role_description" {
  description = "A description of what this role is for"
  type        = string
  default     = "Managed by Terraform"
}

variable "trust_policy_json" {
  description = "The Terraform JSON definition containing the trust (assume role) policy"
  type        = string
}

variable "role_policy_json" {
  description = "The Terraform JSON definition containing the permissions policy"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to the IAM role"
  type        = map(string)
  default     = {}
}