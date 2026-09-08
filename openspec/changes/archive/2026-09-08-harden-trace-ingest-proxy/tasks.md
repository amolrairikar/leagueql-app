## 1. Worker — bound and validate before forwarding

- [x] 1.1 In `workers/leagueql-app/index.js` `handleTraces`, reject non-OTLP content types
      (anything other than `application/x-protobuf` or `application/json`) with `415` before reading
      the body or attaching the token.
- [x] 1.2 Enforce a body-size cap (`MAX_TRACE_BODY_BYTES` = 512 KB): reject with `413` before
      forwarding — checks `Content-Length` when present and also guards the actual read length.
- [x] 1.3 Lightweight structural sanity check: an `application/json` body must parse and carry a
      top-level `resourceSpans`, else `400`; protobuf bodies pass through on the content-type + size
      checks alone.
- [x] 1.4 Preserve existing behavior: `405` on non-POST, `204` pretend-ack when
      `OTEL_EXPORTER_TOKEN`/`OTEL_TRACES_URL` are unset, same-origin + server-side token injection,
      and no CSP change.

## 2. Tests / verification

- [x] 2.1 `workers/leagueql-app/index.test.js` (vitest) asserts an oversized body → `413` (via both
      the declared `Content-Length` and the actual read length) and is not forwarded.
- [x] 2.2 Asserts a disallowed Content-Type → `415` and is not forwarded.
- [x] 2.3 Asserts a valid OTLP JSON export within limits is forwarded to the upstream with
      `Authorization: Bearer <token>` attached. Also covers `405` (non-POST), `204` (unconfigured),
      `400` (malformed / missing `resourceSpans`), protobuf pass-through, and asset routing.
      A minimal vitest project (`package.json` + `index.test.js`) was added under `workers/leagueql-app`;
      `npm test` there → 10 passed.
- [x] 2.4 Confirmed the browser exporter's normal payloads stay well under the 512 KB cap (batched
      OTLP/JSON span exports are a few KB).

## 3. Quality gates

- [x] 3.1 Worker JS follows the existing file's style (no dedicated linter configured for it).
- [x] 3.2 `openspec validate --all` passes.
