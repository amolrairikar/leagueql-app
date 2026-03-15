# DynamoDB Database Specification

## Table Overview

| Property | Value |
|---|---|
| Table name | `fantasy-football-recap-db` |
| Billing mode | On-demand (pay-per-request) |
| Primary key | `PK` (String) + `SK` (String) |
| GSIs | None |

---

## Key Schema

| Attribute | Type | Role | Description |
|---|---|---|---|
| `PK` | String | Partition key | Always in the format `LEAGUE#{leagueId}#PLATFORM#{platform}` |
| `SK` | String | Sort key | Identifies the item type and optional season scope |

---

## Items

All items share the same partition key format `LEAGUE#{leagueId}#PLATFORM#{platform}`. The sort key
determines the item type.

### METADATA

Represents a successfully onboarded league. Written **last** during onboarding —
its presence is the canonical signal that onboarding completed successfully.
If onboarding fails before this item is written, the league will not appear as
onboarded and a retry will re-run the full onboarding flow.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{leagueId}#PLATFORM#{platform}` |
| `SK` | String | Yes | `METADATA` |
| `leagueId` | String | Yes | The ESPN or Sleeper league ID |
| `platform` | String | Yes | Platform the league belongs to. Enum: `ESPN`, `SLEEPER` |
| `onboardedAt` | String | Yes | ISO 8601 timestamp of when onboarding completed |
| `seasons` | List\<String\> | Yes | List of seasons onboarded (e.g. `["2016", "2017", "2018"]`) |

**Example:**
```json
{
  "PK": "LEAGUE#12345678#PLATFORM#ESPN",
  "SK": "METADATA",
  "leagueId": "12345678",
  "platform": "ESPN",
  "onboardedAt": "2024-09-01T00:00:00Z",
  "seasons": ["2022", "2023", "2024"]
}
```

---

## Access Patterns

All reads are single `GetItem` calls — no scans, no queries, no GSIs.

| Operation | PK | SK | Notes |
|---|---|---|---|
| Check if league is onboarded | `LEAGUE#{leagueId}` | `METADATA` | Used by GET /leagues/{leagueId} and the conditional onboard check |

---

## Item Count Estimate

For a league with `n` seasons onboarded, the table holds `n` items:

| Item type | Count |
|---|---|
| `METADATA` | 1 |
| **Total** | **n** |

---

## Capacity and Cost Notes

- **Billing mode:** On-demand. No provisioned capacity to manage.
- **Write cost:** Onboarding writes `n` items once per league. At 10 seasons this is 10 `PutItem` calls per onboarding, each billed at 1 WRU per KB. Typical item sizes are well under 400KB.
- **Read cost:** Every API query is a single `GetItem` billed at 0.5 RRU per 4KB (eventually consistent) or 1 RRU per 4KB (strongly consistent).
- **No GSIs:** Eliminates any extra write costs.
- **Conditional writes:** The `METADATA` item uses `attribute_not_exists(PK)` on first write to prevent duplicate onboarding. This is billed as a standard `PutItem`.