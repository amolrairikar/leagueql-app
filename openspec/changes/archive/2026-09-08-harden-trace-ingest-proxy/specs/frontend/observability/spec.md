## ADDED Requirements

### Requirement: Harden the trace-ingest proxy against abuse
The `/ingest/traces` proxy SHALL bound and validate each request before attaching the source token and forwarding it, so the endpoint cannot be used to exhaust the telemetry ingest quota or inject arbitrary non-OTLP data. Authentication SHALL NOT be required, because anonymous landing-page telemetry is intended and open sign-up would make authentication an ineffective abuse control.

#### Scenario: Oversized payload rejected
- **WHEN** a request to `/ingest/traces` has a body larger than the configured OTLP size cap (a few hundred KB)
- **THEN** the proxy returns `413` and neither forwards the request nor attaches the source token

#### Scenario: Disallowed content type rejected
- **WHEN** a request to `/ingest/traces` has a Content-Type other than `application/x-protobuf` or `application/json`
- **THEN** the proxy returns `415` and neither forwards the request nor attaches the source token

#### Scenario: Valid OTLP export forwarded
- **WHEN** a well-formed OTLP export within the size cap and with an accepted content type arrives
- **THEN** the proxy attaches the source token server-side and forwards it to the configured upstream unchanged

#### Scenario: Unconfigured worker still acks
- **WHEN** the Worker has no `OTEL_EXPORTER_TOKEN`/`OTEL_TRACES_URL` configured
- **THEN** the proxy returns `204` (pretend-ack) so the browser exporter does not retry-storm
