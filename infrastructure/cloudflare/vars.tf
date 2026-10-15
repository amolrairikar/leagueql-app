variable "cloudflare_account_id" {
  description = "The Cloudflare account ID that owns the workers and KV namespace"
  type        = string
}

variable "zone_name" {
  description = "The Cloudflare zone serving the /counts route"
  type        = string
  default     = "leagueql.com"
}
