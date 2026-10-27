# Spec Delta

## ADDED Requirements

### Requirement: Deterministic export bundle
The export SHALL return the same bundle for the same stored data regardless of the order in which
the underlying view reads complete: seasons SHALL appear in the order requested (with unavailable
seasons omitted) and rows within each view SHALL keep their stored sort-key order.

#### Scenario: Result independent of read completion order
- **WHEN** an export is requested for several seasons and the reads for a later season finish
  before those of an earlier season
- **THEN** the response contains the same views and rows, with the seasons in requested order, as
  it would if the reads had completed in request order

### Requirement: Fail the whole export on a read error
If reading any requested view fails with a data-store error, the export SHALL return `500` with
the detail `Failed to retrieve league data` and SHALL NOT return a partial bundle.

#### Scenario: One view read fails
- **WHEN** the read for one season's view raises a DynamoDB error while the others succeed
- **THEN** the API returns `500` and no `data` bundle is returned
