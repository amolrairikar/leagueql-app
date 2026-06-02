# FE-007: Manager Comparison

## Description
The `/manager_comparison` page compares any two managers head-to-head across all shared
history: head-to-head record, points, playoff appearances, and championships. Owner
identities are stabilized and remapped through platform migrations.

## Scope
- Route: `/manager_comparison` (protected, app layout).
- Component: `src/features/manager_comparison/manager-comparison.tsx`; API in `api-calls.ts`.
- Derives playoff appearances and championships from the winners' bracket; reads matchups,
  standings, teams, and playoff bracket via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Managers who never played each other:** head-to-head shows an empty/zero record clearly.
- **Migrated league:** both managers' identities remapped across platforms.
- **Championships:** counted as winners of the winners'-bracket Finals only.
- **Playoff appearances:** distinct seasons a manager reached the winners' bracket.
- **Self-comparison:** selecting the same manager twice is prevented or handled.
- **Co-owners:** owner identity resolved consistently.

## Acceptance Criteria
- [ ] The user can select two managers and see their head-to-head record and points.
- [ ] Playoff appearances and championships are derived from the winners' bracket.
- [ ] Identities are correct across migrated platforms.
- [ ] Managers with no shared matchups show a clear zero-state.

## Sources
`src/features/manager_comparison/`.
