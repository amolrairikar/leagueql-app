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

# Stripe billing (BE-015). DEV is wired with sandbox (test) mode credentials/Price
# IDs and PROD with live mode; the values are supplied per environment from CI
# secrets (the secret key / webhook signing secret are sensitive).
variable "stripe_secret_key" {
  description = "Stripe secret API key (sk_test_… in dev, sk_live_… in prod)"
  type        = string
  sensitive   = true
}

variable "stripe_webhook_secret" {
  description = "Stripe webhook signing secret (whsec_…) for the matching mode"
  type        = string
  sensitive   = true
}

variable "stripe_price_id" {
  description = "Stripe Price ID for the league subscription (mode-specific)"
  type        = string
}

variable "stripe_trial_period_days" {
  description = "Free-trial length granted on a league's first subscription"
  type        = number
  default     = 14
}


