## REMOVED Requirements

### Requirement: Gate integrations endpoints behind a feature flag
**Reason**: The Integrations feature has launched; the `integrations` flag is retired.
**Migration**: None. `GET /integrations` and `POST /integrations` are always served (still requiring
authentication), and `GET /feature-flags` no longer includes an `integrations` key.
