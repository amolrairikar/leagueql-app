variable "cloudflare_account_id" {
  description = "The Cloudflare account ID that owns the workers and KV namespace"
  type        = string
}

variable "zone_name" {
  description = "The Cloudflare zone serving the SPA custom domains and the /counts route"
  type        = string
  default     = "leagueql.com"
}

variable "otel_exporter_token" {
  description = "Better Stack OTLP source token injected by the leagueql-app /ingest/traces proxy"
  type        = string
  sensitive   = true
}
