## Why

The `/ingest/traces` Cloudflare Worker route (`workers/leagueql-app/index.js`) forwards **any**
request body to the Better Stack OTLP endpoint with `Authorization: Bearer ${OTEL_EXPORTER_TOKEN}`
attached server-side. There is no size cap, no content-type check, and no payload validation
(security finding **SEC-02**). Any internet client can therefore POST arbitrary data through the
proxy, which will spend the project's Better Stack ingest quota (denial-of-wallet, and legitimate
telemetry gets rate-limited/dropped) and inject fabricated spans/logs into the observability backend
(telemetry poisoning — polluted dashboards, false or masked alerts).

The upstream is a fixed env var, so this is not SSRF, and the token is only ever attached
server-side (never returned), so the token itself does not leak. The exposure is availability/cost
and integrity of observability data.

Requiring authentication is explicitly **not** the fix: anonymous landing-page telemetry (Web
Vitals, document-load, public-page errors) is intended and valuable, and Clerk sign-up is open/free,
so any bot could still obtain a token. The effective controls are bounding and validating the
request before the token is attached.

## What Changes

- **Body-size cap:** `/ingest/traces` rejects request bodies larger than a configured OTLP size
  limit (a few hundred KB) with `413`, before reading/forwarding the body or attaching the token, so
  a single request cannot ship a huge volume.
- **Content-Type enforcement:** the proxy accepts only the OTLP content types
  (`application/x-protobuf` or `application/json`) and rejects anything else with `415`, before
  forwarding or attaching the token.
- Optional (defense-in-depth): a lightweight structural sanity check of the body before forwarding.
- Unchanged: the same-origin design, server-side token injection, no CSP change, the `204`
  pretend-ack when the Worker is unconfigured, and the `405` on non-POST.

## Impact

- Specs: `frontend/observability` (ADDED "Harden the trace-ingest proxy against abuse").
- Code: `workers/leagueql-app/index.js` (`handleTraces`).
- Tests/verification: Worker-level checks that an oversized body returns `413`, a non-OTLP
  content type returns `415`, and a valid OTLP export within limits is still forwarded with the token
  attached. No frontend bundle or API changes; the browser exporter's requests are unaffected.
