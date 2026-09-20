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

variable "clerk_issuer_url" {
  description = "Clerk Frontend API URL, used as JWT issuer (e.g. https://xxx.clerk.accounts.dev)"
  type        = string
}

variable "clerk_jwt_audience" {
  description = "Audience value that must match the `aud` claim in Clerk session tokens"
  type        = string
}

# backend/yahoo-oauth: per-environment URLs for the Yahoo OAuth flow. These are external
# values (the redirect_uri MUST exactly match the callback registered in the Yahoo developer
# app for this environment; the return URL is the frontend page the callback bounces back to),
# so they are supplied per env. Defaults are the prod values; dev overrides them (dev has no
# api.leagueql.com custom domain — pass the dev API's public callback URL and the dev
# frontend's /connect_league URL, matching the Yahoo dev app registration).
variable "yahoo_redirect_uri" {
  description = "Yahoo OAuth redirect_uri (must match the callback registered in the Yahoo app)"
  type        = string
  default     = "https://api.leagueql.com/leagues/yahoo/oauth/callback"
}

variable "yahoo_connect_return_url" {
  description = "Frontend /connect_league URL the Yahoo callback 302s back to"
  type        = string
  default     = "https://leagueql.app/connect_league"
}
