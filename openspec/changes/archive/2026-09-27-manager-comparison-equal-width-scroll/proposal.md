# Proposal

## Why

On `/manager_comparison` on a narrow (mobile) viewport, a manager whose username is much longer
than the other's forces their stat column wider. The other manager's column is squeezed and
their values and bars get cramped. The two sides of a head-to-head comparison should always get
equal space.

## What Changes

- The two managers' stat columns in the comparison grid (header names, values, bars) are always
  equal width.
- When the equal columns don't fit the viewport, for example on mobile with a long username, the
  comparison grid scrolls horizontally instead of compressing one side.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/manager-comparison`: new requirement that the comparison columns are equal width and
  scroll horizontally when they overflow.

## Impact

- **Frontend:** `frontend/src/features/manager_comparison/manager-comparison.tsx` (comparison grid
  layout only).
- **Backend:** none.
