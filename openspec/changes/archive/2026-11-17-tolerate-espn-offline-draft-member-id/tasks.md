## 1. Backend

- [x] 1.1 Default `memberId` to null on ESPN draft picks before registration

## 2. Tests

- [x] 2.1 Unit tests: missing `memberId` defaults to null; existing value preserved
- [x] 2.2 Component scenario: ESPN offline-draft league onboards and builds the DRAFT view

## 3. Docs & types

- [x] 3.1 `member_id` typed `string | null` in the frontend; data-model doc updated
- [x] 3.2 Delta spec for data-processing-pipeline

## 4. Verify

- [x] 4.1 Run behave, processor unit tests, ruff, eslint, prettier, tsc and `openspec validate --all`
