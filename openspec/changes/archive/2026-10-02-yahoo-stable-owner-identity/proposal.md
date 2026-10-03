# Proposal

## Why

Yahoo leagues credit championships, records, and finishes to the wrong managers in every
cross-season view (Manager History, Manager Comparison, all-time stats). Yahoo masks each
manager's `guid` (it returns `--hidden--`, even for the logged-in user), so the onboarder falls back
to Yahoo's per-league `manager_id`. That value is only a **team slot number**. When a manager leaves
and someone else takes the slot, the newcomer inherits the departed manager's id, so one person can
show another's title (e.g. two titles for a manager who won once) while the real winner shows none.
The per-season champion calculation is correct; the identity it is attributed to is not.

## What Changes

- Use a manager's Yahoo `guid` **per team** whenever it is real (not masked) and unique, instead of
  only when every team in the league has one. Masked values (`--hidden--`, `--`, empty) are treated
  as missing.
- Store each team's raw `guid` (or null) and its Yahoo slot `manager_id` as separate fields in the
  raw season data, so later processing can tell a real person id from a slot number.
- The processor resolves **one stable owner id per person across all seasons** of a Yahoo league,
  linking teams season to season by guid, then nickname, then team name, then custom logo, and
  never merging masked or ambiguous identities.
- A person's stable id is their real guid, or else the team key of the first season they appear
  in, so it never changes as new seasons are added.
- Incremental (single-season) refreshes resolve identities against every season's team data, so
  ids already written for earlier seasons stay consistent.
- A league migrated **to** Yahoo has its `PLATFORM_MIGRATION` mapping translated once from the
  members-proxy ids to the stable ids, so pre-migration history stays merged with each manager.
- **BREAKING (data):** Yahoo `owner_id` values in precomputed views change for leagues whose guids
  were masked. Existing Yahoo leagues are reprocessed to pick up the new ids. No league has
  migrated to Yahoo yet, so no stored mapping needs rewriting.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/league-onboarding`: the Yahoo team/manager identity requirement changes from
  "guid only when every team has a distinct one" to a per-team real-guid rule, and the raw team
  data keeps the guid and slot `manager_id` separately.
- `backend/data-processing-pipeline`: adds requirements for cross-season Yahoo owner identity
  resolution, consistency across incremental refreshes, and translating Yahoo migration mappings.
- `backend/yahoo-members-proxy`: `owner_id` follows the per-team real-guid rule (slot
  `manager_id` when the guid is masked), replacing the claim that it is always the Yahoo `guid`.

## Impact

- **Code:** `src/common/yahoo_members.py` (owner id resolution, used by the onboarder and the
  members proxy), `src/onboarder/yahoo_client.py` (raw teams record), `src/processor/handler.py`
  (identity resolution, loading other seasons' team data, migration-mapping translation).
- **Data:** Yahoo `TEAMS`/`MATCHUPS`/`STANDINGS`/`WEEKLY_STANDINGS` owner ids change. Raw Yahoo
  season files gain `guid`/`slot_manager_id` on team rows. Older files without them still work.
  `PLATFORM_MIGRATION` items for Yahoo destinations gain a one-time "resolved" flag.
- **Ops:** reprocess existing Yahoo leagues with `scripts/utility_scripts/backfill_leagues.py
  --platform YAHOO` after deploy.
- **Docs:** `docs/db/dynamodb_spec.md` (Yahoo owner id semantics, raw team fields, migration flag).
- **Frontend:** no change. It already groups cross-season data by `owner_id`.
