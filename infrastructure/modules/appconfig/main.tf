terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# AWS AppConfig scaffolding for runtime feature flags (BE-017 / FE-026). The
# application, environment, profile, and rollout strategy are managed here; the
# flag *values* and their deployments are set out-of-band in the AppConfig console
# (the runtime toggle), so no hosted configuration version is managed in TF — that
# keeps a toggle from requiring a `terraform apply` / causing drift. Mirrors the
# "scaffolding in TF, value set out-of-band" pattern used for the Stripe SSM secret.

resource "aws_appconfig_application" "this" {
  name        = var.application_name
  description = "LeagueQL feature flags (${var.environment})"
  tags        = var.tags
}

resource "aws_appconfig_environment" "this" {
  name           = var.environment_name
  application_id = aws_appconfig_application.this.id
  description    = "LeagueQL ${var.environment} feature-flag environment"
  tags           = var.tags
}

resource "aws_appconfig_configuration_profile" "this" {
  application_id = aws_appconfig_application.this.id
  name           = var.profile_name
  description    = "LeagueQL feature-flag values (set in the AppConfig console)"
  # "hosted" stores the flag values in AppConfig itself (no S3 / SSM source).
  location_uri = "hosted"
  type         = "AWS.AppConfig.FeatureFlags"
  tags         = var.tags
}

# All-at-once rollout with no bake time — the flags are global booleans with the
# backend as the real enforcement boundary, so there is nothing to canary.
resource "aws_appconfig_deployment_strategy" "this" {
  name                           = "leagueql-flags-${var.environment}"
  description                    = "All-at-once rollout for LeagueQL feature flags"
  deployment_duration_in_minutes = 0
  final_bake_time_in_minutes     = 0
  growth_factor                  = 100
  growth_type                    = "LINEAR"
  replicate_to                   = "NONE"
  tags                           = var.tags
}
