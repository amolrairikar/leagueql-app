# DynamoDB Database Specification

## Table Overview

| Property | Value |
|---|---|
| Table name | `fantasy-football-recap-db` |
| Billing mode | On-demand (pay-per-request) |
| Primary key | `PK` (String) + `SK` (String) |
| GSIs | `GSI1` - Get all league IDs for a canonical league ID |

---

## Key Schema

### Base Table

| Attribute | Type | Role | Description |
|---|---|---|---|
| `PK` | String | Partition key | Always in the format `LEAGUE#{leagueId}` |
| `SK` | String | Sort key | Identifies the item type |

### GSI1: Canonical League index
| Attribute | Type | Role | Description |
|---|---|---|---|
| `canonical_league_id` | String | Partition key | The unified UUID for the league |

---

## Items

All items (with the exception of LEAGUE_COUNT) share the same partition key format
`LEAGUE#{leagueId}#`. The sort key determines the item type.

<details>
<summary><b>LEAGUE_COUNT</b></summary>

Counter representing the total number of leagues onboarded to the app. Incremented after the
metadata record is updated.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `APP#STATS` |
| `SK` | String | Yes | `LEAGUE_COUNT` |
| `league_count` | Integer | Yes | The number of leagues onboarded |

**Example:**
```json
{
  "PK": "APP#STATS",
  "SK": "LEAGUE_COUNT",
  "league_count": 10
}
```
</details>

<details>
<summary><b>LEAGUE_LOOKUP</b></summary>

Mapping allowing for lookup of a ESPN/SLEEPER league ID to its canonical league ID (used for associating different Sleeper leagues over consecutive seasons or ESPN to Sleeper league migrations).

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}#PLATFORM#{platform}` |
| `SK` | String | Yes | `LEAGUE_LOOKUP` |
| `canonical_league_id` | String | Yes | The UUID associated with this league |
| `seasons` | List\<String\> | Yes | List of seasons onboarded (e.g. `["2022", "2023", "2024"]`) |

**Example:**
```json
{
  "PK": "LEAGUE#12345678#PLATFORM#ESPN",
  "SK": "LEAGUE_LOOKUP",
  "canonical_league_id": "uuid-string",
  "seasons": ["2022", "2023", "2024"]
}
```
</details>

<details>
<summary><b>METADATA</b></summary>

Represents a successfully onboarded league. If onboarding fails before this item is written,
the league will not appear as onboarded and a retry will re-run the full onboarding flow.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `METADATA` |
| `platform` | String | Yes | Platform the league belongs to. Enum: `ESPN`, `SLEEPER` |
| `onboarding_id` | String | Yes | UUID corresponding to the onboarding execution for this league |
| `onboarded_at` | String | Yes | ISO 8601 timestamp of when onboarding completed |
| `onboarding_status` | String | Yes | Current onboarding status for league. Enum: `onboarding`, `failed`, `succeeded` |
| `last_refreshed_date` | String | No | ISO 8601 timestamp of when league data was last refreshed |
| `refresh_status` | String | No | Current refresh status for league. Enum: `refreshing`, `failed`, `succeeded` |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "METADATA",
  "platform": "ESPN",
  "onboarding_id": "uuid-string",
  "onboarded_at": "2024-09-01T00:00:00Z",
  "onboarding_status": "succeeded"
}
```
</details>

<details>
<summary><b>TEAMS</b></summary>

Represents all teams across all seasons in the fantasy league.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `METADATA` |
| `data` | List\<Array\> | Yes | A list of objects containing team details |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "TEAMS",
  "data": [
    {
      "display_name": "myusername123",
      "owner_first_name": "Player",
      "owner_last_name": "One",
      "team_abbreviation": "P1",
      "team_id": "1",
      "team_name": "Player One's Team",
      "team_logo": "www.logo.com",
      "season": "2025",
      "primary_owner_id": "primary_owner_one_id",
      "secondary_owner_id": "secondary_owner_one_id"
    }
  ]
}
```
</details>

<details>
<summary><b>MATCHUPS</b></summary>

Represents matchups for a given week in the fantasy league.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `MATCHUPS#{season}#{week}` |
| `data` | List\<Array\> | Yes | A list of objects containing weekly matchups details |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "MATCHUPS#2025#01",
  "data": [
    {
      "team_a_id": "1",
      "team_a_score": 95.46,
      "team_b_id": "2",
      "team_b_score": 90.12,
      "playoff_tier_type": "NONE",
      "winner": "1",
      "loser": "2",
      "week": "1",
      "season": "2025",
      "team_a_primary_owner_id": "pid1",
      "team_a_secondary_owner_id": "sid1",
      "team_b_primary_owner_id": "pid2",
      "team_b_secondary_owner_id": "sid2"
    }
  ]
}
```
</details>

<details>
<summary><b>STANDINGS</b></summary>

Represents standings for a given season in the fantasy league.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `STANDINGS#{season}` |
| `data` | List\<Array\> | Yes | A list of objects containing season standings details |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "STANDINGS#2025",
  "data": [
    {
      "season": "2025",
      "team_id": "1",
      "owner_id": "pid1",
      "games_played": 14,
      "wins": 11,
      "losses": 3,
      "ties": 0,
      "record": "11-3-0",
      "win_pct": 0.786,
      "total_vs_league_wins": 50,
      "total_vs_league_losses": 15,
      "win_pct_vs_league": 0.769,
      "total_pf": 1000.67,
      "total_pa": 900.67,
      "avg_pf": 95.46,
      "avg_pa": 90.12
    }
  ]
}
```
</details>

<details>
<summary><b>AI_RECAP</b></summary>

AI-generated narrative recap for a given season, produced by Claude Haiku using the season's standings and matchup data. Generated by the Processor Lambda after data writes complete. One item per season; skipped if an item already exists (idempotent).

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `AI_RECAP#{season}` |
| `data` | List\<Object\> | Yes | Single-element list containing the recap object |

**`data[0]` object:**

| Attribute | Type | Description |
|---|---|---|
| `season` | String | The season year (e.g., `"2025"`) |
| `recap_text` | String | 2–3 paragraph narrative recap generated by Claude |
| `generated_at` | String | ISO 8601 UTC timestamp of when the recap was generated |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "AI_RECAP#2025",
  "data": [
    {
      "season": "2025",
      "recap_text": "The 2025 season was defined by...",
      "generated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```
</details>
