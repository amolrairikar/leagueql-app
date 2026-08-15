# LeagueQL Feature Requirements

Live requirements documents for every feature in LeagueQL. **These docs are the source of
truth and must be kept current.** Before writing or changing any code, review the relevant
feature doc and update it first (see the repo-root `CLAUDE.md`).

Each document contains: feature ID + title, description, scope, edge cases, and acceptance
criteria. Frontend, backend, and extension features are kept separate.

## Conventions
- **IDs:** `BE-xxx` (backend), `FE-xxx` (frontend), `EXT-xxx` (extension). IDs are stable in
  day-to-day work — don't renumber existing docs for an ordinary add/change, and give a new
  feature the next free ID in its prefix. Renumbering (including reusing a freed ID) is allowed
  only as part of a **deliberate, one-shot consolidation** that renumbers docs and rewrites every
  reference in the same change.
- **One feature per file**, named `<ID>-<kebab-title>.md`.
- New feature → add a doc here and link it in this index before implementation.

## Backend (`backend/`)
| ID | Feature |
|----|---------|
| [BE-001](backend/BE-001-league-onboarding.md) | League Onboarding |
| [BE-002](backend/BE-002-league-refresh.md) | League Refresh |
| [BE-003](backend/BE-003-league-migration.md) | League Migration |
| [BE-004](backend/BE-004-data-processing-pipeline.md) | Data Processing Pipeline (Precomputed Views) |
| [BE-005](backend/BE-005-query-precomputed-views-api.md) | Query Precomputed Views API |
| [BE-006](backend/BE-006-get-league-metadata-api.md) | Get League Metadata API |
| [BE-007](backend/BE-007-delete-league-api.md) | Delete League API |
| [BE-008](backend/BE-008-job-status-tracking.md) | Job Status Tracking |
| [BE-009](backend/BE-009-espn-members-proxy-api.md) | ESPN Members Proxy API |
| [BE-010](backend/BE-010-player-metadata-refresher.md) | Player Metadata Refresher |
| [BE-011](backend/BE-011-sleeper-player-stats-refresher.md) | Sleeper Player Stats Refresher |
| [BE-012](backend/BE-012-scheduled-sleeper-auto-refresh.md) | Scheduled Sleeper Auto-Refresh |
| [BE-013](backend/BE-013-app-stats-league-count.md) | App Stats / League Count |
| [BE-016](backend/BE-016-league-ownership-authorization.md) | League Ownership & Authorization |
| [BE-017](backend/BE-017-feature-flags.md) | Feature Flags (OpenFeature + SSM Parameter Store) |
| [BE-018](backend/BE-018-league-access-tracking.md) | League Access Tracking |
| [BE-019](backend/BE-019-sleeper-transactions.md) | Sleeper Transactions (Waivers, Trades, Free Agents) |
| [BE-020](backend/BE-020-backend-otel-tracing.md) | Backend OpenTelemetry Tracing → Better Stack (API + async chain) |
| [BE-022](backend/BE-022-yahoo-oauth.md) | Yahoo OAuth Authorization & Token Management |
| [BE-023](backend/BE-023-api-health-check-alerting.md) | API Health Check & Uptime Alerting (public `/health` for external monitor) |
| [BE-024](backend/BE-024-api-security-headers.md) | API Security Response Headers & Cache-Control Policy |

## Frontend (`frontend/`)
| ID | Feature |
|----|---------|
| [FE-001](frontend/FE-001-landing-page.md) | Landing Page |
| [FE-002](frontend/FE-002-connect-league.md) | Connect League (Onboarding Flow) |
| [FE-003](frontend/FE-003-migrate-league.md) | Migrate League |
| [FE-004](frontend/FE-004-home-dashboard.md) | Home Dashboard |
| [FE-005](frontend/FE-005-season-standings.md) | Season Standings |
| [FE-006](frontend/FE-006-matchups.md) | Matchups & Box Scores |
| [FE-007](frontend/FE-007-manager-comparison.md) | Manager Comparison |
| [FE-008](frontend/FE-008-playoff-bracket.md) | Playoff Bracket |
| [FE-009](frontend/FE-009-manager-history.md) | Manager History |
| [FE-010](frontend/FE-010-player-records.md) | Player Records |
| [FE-011](frontend/FE-011-matchup-records.md) | Matchup Records |
| [FE-012](frontend/FE-012-draft-recap.md) | Draft Recap (Draft Board) |
| [FE-013](frontend/FE-013-draft-grades.md) | Draft Grades |
| [FE-014](frontend/FE-014-navigation-sidebar.md) | Navigation Sidebar & App Layout |
| [FE-015](frontend/FE-015-demo-mode.md) | Demo Mode |
| [FE-016](frontend/FE-016-instructions-docs-page.md) | Instructions / Docs Page |
| [FE-018](frontend/FE-018-privacy-pages.md) | Privacy Pages |
| [FE-019](frontend/FE-019-authentication.md) | Authentication & Protected Routes |
| [FE-020](frontend/FE-020-theme-toggle.md) | Theme (Light/Dark Mode) |
| [FE-024](frontend/FE-024-security-headers.md) | Security Response Headers & Content-Security-Policy |
| [FE-025](frontend/FE-025-ownership-transfer-owner-gated-actions.md) | Ownership Transfer & Owner-Gated Actions |
| [FE-026](frontend/FE-026-feature-flags.md) | Feature Flags (OpenFeature + SSM Parameter Store) |
| [FE-027](frontend/FE-027-transactions.md) | Transactions |
| [FE-028](frontend/FE-028-changelog-page.md) | Changelog Page |
| [FE-029](frontend/FE-029-frontend-observability.md) | Frontend Observability (OpenTelemetry + RUM → Better Stack) |
| [FE-030](frontend/FE-030-informational-banner.md) | Informational Banner |
| [FE-031](frontend/FE-031-schedule-swap-simulator.md) | Schedule-Swap Simulator (Standings) |
| [FE-032](frontend/FE-032-weekly-awards-superlatives.md) | Weekly Awards & Superlatives (Matchups) |
| [FE-034](frontend/FE-034-lineup-efficiency.md) | Lineup Efficiency / Points Left on Bench (Box-score) |
| [FE-036](frontend/FE-036-draft-value-scatter.md) | Draft Value Scatter (Draft Recap) |
| [FE-037](frontend/FE-037-connect-yahoo-league.md) | Connect Yahoo League (OAuth Account Linking) |

## Extension (`extension/`)
| ID | Feature |
|----|---------|
| [EXT-001](extension/EXT-001-espn-cookie-autofill.md) | ESPN Cookie Auto-Fill Chrome Extension |

## Related references
- API contract: [`docs/api/openapi_spec.yaml`](../api/openapi_spec.yaml)
- Data model: [`docs/db/dynamodb_spec.md`](../db/dynamodb_spec.md)
