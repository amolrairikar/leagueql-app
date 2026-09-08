## Context

Two capability specs — `backend/yahoo-oauth` and `frontend/connect-yahoo-league` — were
written ahead of implementation and stored in `openspec/specs/` during the initial
OpenSpec migration (`6283b68`). Because `openspec/specs/` is the source of truth for
*implemented* behavior, and no Yahoo code exists, they represented spec drift. Yahoo is
on the roadmap but not officially committed, so the requirements should be retained —
just relocated to their correct OpenSpec home (a pending change) rather than deleted.

## Goals / Non-Goals

- **Goal:** `openspec/specs/` describes only shipped capabilities again.
- **Goal:** preserve the Yahoo requirements verbatim as the future implementation target.
- **Non-Goal:** implementing Yahoo support now. This change makes no code, infra, or doc
  changes beyond the spec relocation.

## Decisions

- **Model as a pending "add capability" change, not a deletion.** The delta specs use
  `## ADDED Requirements`, so archiving this change once Yahoo ships re-seeds both
  capabilities as implemented specs — the standard new-capability path. The change stays
  open (unapplied/unarchived) as the roadmap marker until then.
- **Verbatim carry-over.** The requirements and scenarios are copied unchanged so the
  relocation is behavior-preserving and reviewable as a pure move.
- **Alternative rejected:** removing the specs outright (`## REMOVED Requirements`). That
  would discard authored intent for a feature that is still planned. Relocating keeps the
  work discoverable via `openspec list` without polluting the live specs.

## Open Questions

- Final commitment and sequencing of Yahoo support (blocked on Yahoo developer-app
  approval and product prioritization) — resolved when the work is scheduled.
