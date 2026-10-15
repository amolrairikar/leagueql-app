# One-time adoption of the leagueql-app worker, which was deployed by Workers Builds (wrangler)
# with its custom domains attached in the dashboard. Delete this file after the first
# successful apply; the imports are then recorded in state.

data "cloudflare_workers_custom_domains" "leagueql_app" {
  account_id = var.cloudflare_account_id
  service    = "leagueql-app"
}

locals {
  leagueql_app_domain_ids = {
    for d in data.cloudflare_workers_custom_domains.leagueql_app.result : d.hostname => d.id
  }
}

import {
  to = cloudflare_workers_script.leagueql_app
  id = "${var.cloudflare_account_id}/leagueql-app"
}

import {
  for_each = toset([var.zone_name, "www.${var.zone_name}"])
  to       = cloudflare_workers_custom_domain.leagueql_app[each.value]
  id       = "${var.cloudflare_account_id}/${local.leagueql_app_domain_ids[each.value]}"
}
