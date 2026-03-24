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
| `SK` | String | Sort key | Identifies the item type |

---

## Items

All items (with the exception of LEAGUE_COUNT and ONBOARDING_JOB_STATUS) share the same partition key format
`LEAGUE#{leagueId}#PLATFORM#{platform}`. The sort key determines the item type.

<details>
<summary><b>LEAGUE_COUNT</b></summary>

Counter representing the total number of leagues onboarded to the app. Written after the
metadata record is updated.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `APP#STATS` |
| `SK` | String | Yes | `LEAGUE_COUNT` |
| `count` | Integer | Yes | The number of leagues onboarded |

**Example:**
```json
{
  "PK": "APP#STATS",
  "SK": "LEAGUE_COUNT",
  "count": 10
}
```
</details>

<details>
<summary><b>ONBOARDING_JOB_STATUS</b></summary>

Entry representing the status of a given onboarding job. Has TTL setup to expire after 24 hours.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `JOB#<job_id>` |
| `SK` | String | Yes | `ONBOARDING_JOB_STATUS` |
| `status` | String | Yes | The current onboarding status |
| `expiration_time` | Number | Yes | Epoch timestamp representing expiration time of record 

**Example:**
```json
{
  "PK": "JOB#12345",
  "SK": "ONBOARDING_JOB_STATUS",
  "status": "12345678",
  "platform": "ESPN",
  "onboardedAt": "2024-09-01T00:00:00Z",
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
| `PK` | String | Yes | `LEAGUE#{league_id}#PLATFORM#{platform}` |
| `SK` | String | Yes | `METADATA` |
| `league_id` | String | Yes | The ESPN or Sleeper league ID |
| `canonical_league_id` | String | Yes | The UUID associated with this league to associate multiple league IDs for the same league together |
| `platform` | String | Yes | Platform the league belongs to. Enum: `ESPN`, `SLEEPER` |
| `onboarded_at` | String | Yes | ISO 8601 timestamp of when onboarding completed |
| `seasons` | List\<String\> | Yes | List of seasons onboarded (e.g. `["2016", "2017", "2018"]`) |

**Example:**
```json
{
  "PK": "LEAGUE#12345678#PLATFORM#ESPN",
  "SK": "METADATA",
  "league_id": "12345678",
  "canonical_league_id": "uuid-string",
  "platform": "ESPN",
  "onboarded_at": "2024-09-01T00:00:00Z",
  "seasons": ["2022", "2023", "2024"]
}
```
</details>

<details>
<summary><b>TEAMS</b></summary>

Represents all teams across all seasons in the fantasy league.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}#PLATFORM#{platform}` |
| `SK` | String | Yes | `METADATA` |
| `display_name` | String | Yes | The team owner's username |
| `owner_first_name` | String | Yes | The team owner's first name |
| `owner_last_name` | String | Yes | The team owner's last name |
| `team_abbreviation` | String | Yes | The team abbreviation |
| `team_id` | String | Yes | The unique ID for the team for the corresponding season |
| `team_name` | String | Yes | The team name |
| `team_logo` | String | Yes | A URL link to the team logo |
| `season` | String | Yes | The season the team was part of the league |
| `primary_owner_id` | String | Yes | ESPN SWID of primary owner |
| `secondary_owner_id` | String | No | Optional, ESPN SWID of secondary owner if a team has two owners |

**Example:**
```json
{
  "PK": "LEAGUE#12345678#PLATFORM#ESPN",
  "SK": "TEAMS",
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
```
</details>
