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
| `league_name` | String | No | League name from the most recent season's settings (ESPN leagues only) |

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
| `SK` | String | Yes | `TEAMS` |
| `data` | List\<Object\> | Yes | A list of objects containing team details |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `display_name` | String | Platform username of the team owner |
| `team_id` | String | Team ID within the league |
| `team_name` | String | Team name set by the owner |
| `team_logo` | String \| null | URL to the team logo |
| `season` | String | Season year (e.g. `"2025"`) |
| `primary_owner_id` | String | Platform user ID of the primary owner |
| `secondary_owner_id` | String \| null | Platform user ID of a co-owner, if present |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "TEAMS",
  "data": [
    {
      "display_name": "myusername123",
      "team_id": "1",
      "team_name": "Player One's Team",
      "team_logo": "https://example.com/logo.png",
      "season": "2025",
      "primary_owner_id": "primary_owner_one_id",
      "secondary_owner_id": null
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
| `data` | List\<Object\> | Yes | A list of objects containing weekly matchup details |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `team_a_id` | String | Team ID for the first team |
| `team_a_display_name` | String | Platform username of team A's owner |
| `team_a_team_name` | String | Team name for team A |
| `team_a_team_logo` | String \| null | URL to team A's logo |
| `team_a_score` | Float | Team A's score for the week |
| `team_a_starters` | List\<Object\> | Team A's starting lineup with player stats |
| `team_a_bench` | List\<Object\> | Team A's bench with player stats |
| `team_a_primary_owner_id` | String | Platform user ID of team A's primary owner |
| `team_a_secondary_owner_id` | String \| null | Platform user ID of team A's co-owner |
| `team_b_id` | String | Team ID for the second team |
| `team_b_display_name` | String | Platform username of team B's owner |
| `team_b_team_name` | String | Team name for team B |
| `team_b_team_logo` | String \| null | URL to team B's logo |
| `team_b_score` | Float | Team B's score for the week |
| `team_b_starters` | List\<Object\> | Team B's starting lineup with player stats |
| `team_b_bench` | List\<Object\> | Team B's bench with player stats |
| `team_b_primary_owner_id` | String | Platform user ID of team B's primary owner |
| `team_b_secondary_owner_id` | String \| null | Platform user ID of team B's co-owner |
| `playoff_tier_type` | String | Playoff bracket type. Enum: `NONE`, `WINNERS_BRACKET` |
| `playoff_round` | String \| null | Human-readable round name (e.g. `"Semifinals"`); null for regular season |
| `winner` | String | Team ID of the winner |
| `loser` | String | Team ID of the loser |
| `week` | String | Week number (e.g. `"1"`) |
| `season` | String | Season year (e.g. `"2025"`) |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "MATCHUPS#2025#01",
  "data": [
    {
      "team_a_id": "1",
      "team_a_display_name": "myusername123",
      "team_a_team_name": "Player One's Team",
      "team_a_team_logo": "https://example.com/logo1.png",
      "team_a_score": 95.46,
      "team_a_starters": [],
      "team_a_bench": [],
      "team_a_primary_owner_id": "pid1",
      "team_a_secondary_owner_id": null,
      "team_b_id": "2",
      "team_b_display_name": "otherusername456",
      "team_b_team_name": "Player Two's Team",
      "team_b_team_logo": null,
      "team_b_score": 90.12,
      "team_b_starters": [],
      "team_b_bench": [],
      "team_b_primary_owner_id": "pid2",
      "team_b_secondary_owner_id": null,
      "playoff_tier_type": "NONE",
      "playoff_round": null,
      "winner": "1",
      "loser": "2",
      "week": "1",
      "season": "2025"
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
<summary><b>WEEKLY_STANDINGS</b></summary>

Represents cumulative standings snapshots through each regular-season week for a given season. All weekly snapshots for a season are stored in a single item.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `WEEKLY_STANDINGS#{season}` |
| `data` | List\<Object\> | Yes | A list of objects, one per team per week snapshot |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `season` | String | Season year (e.g. `"2025"`) |
| `snapshot_week` | String | Week number this snapshot represents (e.g. `"3"`) |
| `team_id` | String | Team ID within the league |
| `owner_id` | String | Platform user ID of the primary owner |
| `team_name` | String | Team name set by the owner |
| `team_logo` | String \| null | URL to the team logo |
| `owner_username` | String | Platform display name of the team owner |
| `games_played` | Integer | Cumulative games played through this week |
| `wins` | Integer | Cumulative wins through this week |
| `losses` | Integer | Cumulative losses through this week |
| `ties` | Integer | Cumulative ties through this week |
| `record` | String | Formatted record (e.g. `"3-1-0"`) |
| `win_pct` | Float | Win percentage (wins / games_played), rounded to 3 decimal places |
| `total_vs_league_wins` | Integer | Cumulative vs-league wins (beat all teams with a lower score each week) |
| `total_vs_league_losses` | Integer | Cumulative vs-league losses (lost to all teams with a higher score each week) |
| `win_pct_vs_league` | Float | vs-league win percentage, rounded to 3 decimal places |
| `total_pf` | Float | Cumulative points scored through this week |
| `total_pa` | Float | Cumulative points allowed through this week |
| `avg_pf` | Float | Average points scored per game, rounded to 2 decimal places |
| `avg_pa` | Float | Average points allowed per game, rounded to 2 decimal places |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "WEEKLY_STANDINGS#2025",
  "data": [
    {
      "season": "2025",
      "snapshot_week": "1",
      "team_id": "1",
      "owner_id": "pid1",
      "team_name": "Player One's Team",
      "team_logo": "https://example.com/logo.png",
      "owner_username": "myusername123",
      "games_played": 1,
      "wins": 1,
      "losses": 0,
      "ties": 0,
      "record": "1-0-0",
      "win_pct": 1.0,
      "total_vs_league_wins": 8,
      "total_vs_league_losses": 1,
      "win_pct_vs_league": 0.889,
      "total_pf": 130.45,
      "total_pa": 102.30,
      "avg_pf": 130.45,
      "avg_pa": 102.30
    },
    {
      "season": "2025",
      "snapshot_week": "2",
      "team_id": "1",
      "owner_id": "pid1",
      "team_name": "Player One's Team",
      "team_logo": "https://example.com/logo.png",
      "owner_username": "myusername123",
      "games_played": 2,
      "wins": 2,
      "losses": 0,
      "ties": 0,
      "record": "2-0-0",
      "win_pct": 1.0,
      "total_vs_league_wins": 17,
      "total_vs_league_losses": 2,
      "win_pct_vs_league": 0.895,
      "total_pf": 265.10,
      "total_pa": 198.75,
      "avg_pf": 132.55,
      "avg_pa": 99.38
    }
  ]
}
```
</details>

<details>
<summary><b>PLAYOFF_BRACKET</b></summary>

Represents the playoff bracket structure for a given season. One item per season; each match in the bracket is an element in the `data` list.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `PLAYOFF_BRACKET#{season}` |
| `data` | List\<Object\> | Yes | A list of objects, one per bracket matchup |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `match_id` | Integer | Unique match identifier within the bracket |
| `round` | Integer | Round number (1 = first round, 2 = semifinals, etc.) |
| `team_1_id` | String | Roster ID of the first team |
| `team_1_display_name` | String | Platform username of team 1's owner |
| `team_1_team_name` | String | Team name for team 1 |
| `team_1_team_logo` | String \| null | URL to team 1's logo |
| `team_2_id` | String | Roster ID of the second team |
| `team_2_display_name` | String | Platform username of team 2's owner |
| `team_2_team_name` | String | Team name for team 2 |
| `team_2_team_logo` | String \| null | URL to team 2's logo |
| `winner` | String \| null | Roster ID of the winner; null if the match has not been played |
| `loser` | String \| null | Roster ID of the loser; null if the match has not been played |
| `position` | Integer \| null | Final placement this match determines (e.g. `1` = champion, `3` = 3rd place); null for non-placement matches |
| `team_1_from` | String \| null | JSON string indicating which match seeded team 1 (e.g. `{"w": 1}` = winner of match 1, `{"l": 2}` = loser of match 2); null for first-round teams |
| `team_2_from` | String \| null | JSON string indicating which match seeded team 2; null for first-round teams |
| `season` | String | Season year (e.g. `"2025"`) |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "PLAYOFF_BRACKET#2025",
  "data": [
    {
      "match_id": 1,
      "round": 1,
      "team_1_id": "6",
      "team_1_display_name": "myusername123",
      "team_1_team_name": "Player One's Team",
      "team_1_team_logo": "https://sleepercdn.com/avatars/thumbs/abc123",
      "team_2_id": "4",
      "team_2_display_name": "otherusername456",
      "team_2_team_name": "Player Two's Team",
      "team_2_team_logo": null,
      "winner": "6",
      "loser": "4",
      "position": null,
      "team_1_from": null,
      "team_2_from": null,
      "season": "2025"
    },
    {
      "match_id": 6,
      "round": 3,
      "team_1_id": "6",
      "team_1_display_name": "myusername123",
      "team_1_team_name": "Player One's Team",
      "team_1_team_logo": "https://sleepercdn.com/avatars/thumbs/abc123",
      "team_2_id": "9",
      "team_2_display_name": "thirduser789",
      "team_2_team_name": "Player Three's Team",
      "team_2_team_logo": null,
      "winner": "9",
      "loser": "6",
      "position": 1,
      "team_1_from": "{\"w\": 3}",
      "team_2_from": "{\"w\": 4}",
      "season": "2025"
    }
  ]
}
```
</details>

<details>
<summary><b>AI_RECAP</b></summary>

AI-generated narrative recap for a given season, produced by Claude Haiku using the season's standings and matchup data. Generated by the Processor Lambda after data writes complete. One item per season; always overwritten on each league refresh.

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

<details>
<summary><b>AI_RECAP#MANAGER</b></summary>

AI-generated career retrospective for a single manager, produced by Claude Haiku using all-time standings and matchup data. Generated by the Processor Lambda after data writes complete. One item per manager; always overwritten on each league refresh so career stats reflect the latest data.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `AI_RECAP#MANAGER#{owner_id}` |
| `data` | List\<Object\> | Yes | Single-element list containing the recap object |

**`data[0]` object:**

| Attribute | Type | Description |
|---|---|---|
| `owner_id` | String | Platform user ID of the manager |
| `owner_username` | String | Manager's display name at generation time |
| `recap_text` | String | 3-paragraph career narrative generated by Claude |
| `generated_at` | String | ISO 8601 UTC timestamp of when the recap was generated |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "AI_RECAP#MANAGER#pid1",
  "data": [
    {
      "owner_id": "pid1",
      "owner_username": "myusername123",
      "recap_text": "Over six seasons myusername123 has...\n\nTheir best year came in...\n\nWhen it comes to rivalries...",
      "generated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```
</details>
