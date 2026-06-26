variable "environment" {
  description = "Deployment environment (dev | prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for regional resources"
  type        = string
}

variable "image_tag" {
  description = "Container image tag for the Sleeper player stats refresher Fargate task (git short SHA in CI)"
  type        = string
  default     = "latest"
}

variable "recap_generator_image_tag" {
  description = "Container image tag for the AI recap generator Fargate task (BE-022; content-addressed in CI)"
  type        = string
  default     = "latest"
}

variable "clerk_issuer_url" {
  description = "Clerk Frontend API URL, used as JWT issuer (e.g. https://xxx.clerk.accounts.dev)"
  type        = string
}

variable "clerk_jwt_audience" {
  description = "Audience value that must match the `aud` claim in Clerk session tokens"
  type        = string
}

# Stripe billing (BE-015). DEV is wired with sandbox (test) mode Price IDs and PROD
# with live mode. The sensitive secret key / webhook signing secret are NOT
# Terraform vars — they live as SecureString SSM parameters
# (/leagueql/{env}/stripe/{secret_key,webhook_secret}) set out-of-band and fetched
# by the Lambdas at runtime; the Lambda roles are granted ssm:GetParameter in
# infrastructure/global/{dev,prod}/main.tf.
variable "stripe_price_id_monthly" {
  description = "Stripe recurring Price ID for the monthly plan (mode-specific)"
  type        = string
}

variable "stripe_price_id_yearly" {
  description = "Stripe recurring Price ID for the yearly plan (mode-specific)"
  type        = string
}

variable "stripe_trial_period_days" {
  description = "Free-trial length granted on a league's first subscription"
  type        = number
  default     = 14
}


