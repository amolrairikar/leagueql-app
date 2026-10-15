# One-time adoption of the resources that were created by hand (wrangler / AWS console).
# Delete this file after the first successful apply; the imports are then recorded in state.
#
# aws_iam_access_key.sync_counts is intentionally NOT imported (a secret can't be read back):
# Terraform mints a new key on leagueql-user (owned by account-setup) and wires it into the
# worker, after which the old hand-made key is deactivated and deleted manually.

data "cloudflare_workers_routes" "leagueql" {
  zone_id = data.cloudflare_zone.leagueql.zone_id
}

locals {
  counts_route_id = one([
    for r in data.cloudflare_workers_routes.leagueql.result : r.id
    if r.pattern == "api.${var.zone_name}/counts"
  ])
}

import {
  to = cloudflare_workers_kv_namespace.counts
  id = "${var.cloudflare_account_id}/15d97bbfce4842aea2e15817010aeb58"
}

import {
  to = cloudflare_workers_script.get_counts
  id = "${var.cloudflare_account_id}/get-counts"
}

import {
  to = cloudflare_workers_script.sync_counts
  id = "${var.cloudflare_account_id}/sync-counts"
}

import {
  to = cloudflare_workers_route.counts
  id = "${data.cloudflare_zone.leagueql.zone_id}/${local.counts_route_id}"
}

import {
  to = cloudflare_workers_cron_trigger.sync_counts
  id = "${var.cloudflare_account_id}/sync-counts"
}
