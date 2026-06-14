# Data-plane resource ARN for the appconfigdata Data API
# (StartConfigurationSession / GetLatestConfiguration). These actions are
# authorized against the application/environment/configuration path, not the
# configuration-profile ARN, so it is built from the component IDs.
output "configuration_resource_arn" {
  description = "Resource ARN the Lambda execution roles grant appconfigdata read on"
  value       = "arn:aws:appconfig:${var.region}:${var.account_id}:application/${aws_appconfig_application.this.id}/environment/${aws_appconfig_environment.this.environment_id}/configuration/${aws_appconfig_configuration_profile.this.configuration_profile_id}"
}
