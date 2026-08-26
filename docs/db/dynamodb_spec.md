# DynamoDB Database Specification

## Table Overview

| Property | Value |
|---|---|
| Table name | `fantasy-football-recap-db` |
| Billing mode | On-demand (pay-per-request) |
| Primary key | `PK` (String) + `SK` (String) |
| GSIs | `GSI1` - Get all league IDs for a canonical league ID; `GSI2` - Look up a league by platform and league ID; `GSI3` - List all onboarded leagues (sparse index over METADATA items) |
| TTL | Enabled on the `ttl` attribute (Unix epoch seconds). Only JOB_STATUS items set it, so old onboard/refresh/migrate jobs are reaped ~24h after their last write; items without a `ttl` attribute never expire |

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

### GSI2: Platform index
| Attribute | Type | Role | Description |
|---|---|---|---|
| `platform` | String | Partition key | The platform the league belongs to (e.g., "ESPN", "SLEEPER") |
| `league_id` | String | Sort key | The league ID for the platform |

### GSI3: All-leagues index
Sparse index used to list every onboarded league (e.g. a leagues-overview dashboard) with a
single `SK = "METADATA"` query, replacing a full-table scan filtered to METADATA. The partition
key is the base-table sort key `SK` (the constant string `METADATA` on these items), and the
sort key is `onboarded_at`, so results come back ordered by onboard time (use
`ScanIndexForward=False` for newest-first). Because only METADATA items carry `onboarded_at`,
the big per-league view items (`MATCHUPS`, `STANDINGS`, `DRAFT`, …) are omitted — the index
stays sparse. Projection is `INCLUDE` of the dashboard display fields (`platform`,
`league_name`, `last_refresh_at`, `last_accessed_at`, `active_platform`, `migrated_from`,
`migrated_at`), so the query needs no follow-up `GetItem`.

| Attribute | Type | Role | Description |
|---|---|---|---|
| `SK` | String | Partition key | Base-table sort key; always `METADATA` for indexed items |
| `onboarded_at` | String | Sort key | ISO 8601 timestamp of when the league was onboarded |

---

## Items

Most items share the same partition key format `LEAGUE#{leagueId}`, with the sort key
determining the item type. The exceptions are LEAGUE_COUNT (`APP#STATS`) and JOB_STATUS
(`JOB#{correlation_id}`), which are keyed independently of any single league.

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
| `seasons` | List\<String\> | No | List of seasons onboarded (e.g. `["2022", "2023", "2024"]`). Absent on a **pending** renewal lookup (see below), which has no started season yet. |
| `platform` | String | Yes | The platform the league belongs to (e.g., "ESPN", "SLEEPER") |
| `league_id` | String | Yes | The league ID for the platform |
| `pending_season` | String | No | Present only on a **pending** Sleeper renewal lookup: the not-yet-started season being awaited (e.g. `"2026"`). See below. |

**Example:**
```json
{
  "PK": "LEAGUE#12345678#PLATFORM#ESPN",
  "SK": "LEAGUE_LOOKUP",
  "canonical_league_id": "uuid-string",
  "seasons": ["2022", "2023", "2024"],
  "platform": "ESPN",
  "league_id": "12345678"
}
```

**Pending renewal variant (Sleeper).** A Sleeper league renews each season under a brand-new
`league_id` linked to the prior season by `previous_league_id`. When a user connects the
renewed season before it starts (`pre_draft`/`drafting`), the new ID is registered as a
*pending* `LEAGUE_LOOKUP` — it carries `canonical_league_id` (the existing league) and a
`pending_season` marker, but **no `seasons`** (an empty DynamoDB string set is invalid, and the
season must not surface in any dropdown until it has data). This is essential because Sleeper
only links seasons *backwards*, so a discarded new ID could never be re-discovered. The
scheduled auto-refresh ([backend/scheduled-sleeper-auto-refresh](../requirements/backend/backend/scheduled-sleeper-auto-refresh-scheduled-sleeper-auto-refresh.md))
polls pending lookups and promotes this item to a normal lookup — adding `seasons` and removing
`pending_season` — the first run after the season flips to `in_season`
([backend/league-onboarding](../requirements/backend/backend/league-onboarding-league-onboarding.md) /
[backend/league-refresh](../requirements/backend/backend/league-refresh-league-refresh.md)).

```json
{
  "PK": "LEAGUE#1377908026471645184#PLATFORM#SLEEPER",
  "SK": "LEAGUE_LOOKUP",
  "canonical_league_id": "uuid-string",
  "platform": "SLEEPER",
  "league_id": "1377908026471645184",
  "pending_season": "2026"
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
| `onboarded_at` | String | Yes | ISO 8601 timestamp of when the league was onboarded |
| `last_refresh_at` | String | No | ISO 8601 timestamp of when the most recent refresh completed successfully. Used to enforce the per-league refresh cooldown. |
| `last_accessed_at` | String | No | ISO 8601 (UTC) timestamp of when a member last opened the league via `GET /leagues/{leagueId}` (backend/league-access-tracking). Written at most once per hour (app-side throttle); absent on older items and on leagues never opened since the field shipped. Used to identify stale leagues for future pruning/archival. |
| `league_name` | String | No | League name from the most recent season's settings |
| `owner_user_id` | String | No | Clerk user ID of the league's owner — the authorization anchor for mutating endpoints (backend/league-authorization). Set **once** on first ONBOARD; never overwritten by REFRESH/MIGRATE. Absent for system-initiated onboards. |
| `members` | String Set | No | Clerk user IDs entitled to **read** an ESPN league (backend/league-authorization). Seeded with the owner at onboard; a verified caller is `ADD`ed via `POST /leagues/{id}/verify-membership`. Unused for Sleeper (Sleeper reads are open). |
| `transfer_token_hash` | String | No | sha256 of an outstanding ownership-transfer token (backend/league-authorization). Plaintext is never stored; set by `POST /leagues/{id}/transfer-token` and removed when redeemed. |
| `transfer_token_expires_at` | String | No | ISO 8601 (UTC) expiry of the outstanding transfer token (backend/league-authorization). |
| `active_job_id` | String | No | Concurrency-guard pointer to the league's most recently started in-flight job. Holds the `correlation_id` of the current onboard/refresh/migrate; the API dereferences it to the `JOB#{correlation_id}` / `JOB_STATUS` item and rejects a duplicate request only while that job is `IN_PROGRESS`. Written best-effort on job start; stale pointers self-heal because the JOB_STATUS item carries a 24h TTL. |
| `active_platform` | String | No | Current platform the league is served from after an ESPN → Sleeper migration. Set to the destination platform when a migration is initiated; before any migration `platform` is authoritative. Enum: `ESPN`, `SLEEPER`. |
| `migrated_from` | String | No | Source platform recorded when a league is migrated to a new platform (e.g. `ESPN` when migrating ESPN → Sleeper). Enum: `ESPN`, `SLEEPER`. |
| `migrated_at` | String | No | ISO 8601 (UTC) timestamp of when a platform migration was initiated (set together with `active_platform` and `migrated_from`). |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "METADATA",
  "platform": "ESPN",
  "onboarded_at": "2024-09-01T00:00:00Z",
  "owner_user_id": "user_2abc123",
  "members": ["user_2abc123"]
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
| `SK` | String | Yes | `MATCHUPS#{season}#WEEK#{week}` |
| `data` | List\<Object\> | Yes | A list of objects containing weekly matchup details |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `team_a_id` | String | Team ID for the first team |
| `team_a_display_name` | String | Platform username of team A's owner |
| `team_a_team_name` | String | Team name for team A |
| `team_a_team_logo` | String \| null | URL to team A's logo |
| `team_a_score` | Float | Team A's score for the week |
| `team_a_starters` | List\<Object\> | Team A's starting lineup with player stats (see **PlayerStat** below) |
| `team_a_bench` | List\<Object\> | Team A's bench with player stats (see **PlayerStat** below) |
| `team_a_primary_owner_id` | String | Platform user ID of team A's primary owner |
| `team_a_secondary_owner_id` | String \| null | Platform user ID of team A's co-owner |
| `team_b_id` | String | Team ID for the second team |
| `team_b_display_name` | String | Platform username of team B's owner |
| `team_b_team_name` | String | Team name for team B |
| `team_b_team_logo` | String \| null | URL to team B's logo |
| `team_b_score` | Float | Team B's score for the week |
| `team_b_starters` | List\<Object\> | Team B's starting lineup with player stats (see **PlayerStat** below) |
| `team_b_bench` | List\<Object\> | Team B's bench with player stats (see **PlayerStat** below) |
| `team_b_primary_owner_id` | String | Platform user ID of team B's primary owner |
| `team_b_secondary_owner_id` | String \| null | Platform user ID of team B's co-owner |
| `playoff_tier_type` | String | Playoff bracket type. Enum: `NONE`, `WINNERS_BRACKET`, `WINNERS_CONSOLATION_LADDER`, `LOSERS_BRACKET` |
| `playoff_round` | String \| null | Human-readable round name; `WINNERS_BRACKET` → `"Quarterfinals"`/`"Semifinals"`/`"Finals"`, `WINNERS_CONSOLATION_LADDER` → `"Winners Consolation"`, `LOSERS_BRACKET` → `"Losers Bracket"`; null for regular season (`NONE`) |
| `winner` | String | Team ID of the winner |
| `loser` | String | Team ID of the loser |
| `week` | String | Week number (e.g. `"1"`) |
| `season` | String | Season year (e.g. `"2025"`) |

**`PlayerStat` object** (each element of `team_*_starters` / `team_*_bench`):

| Attribute | Type | Description |
|---|---|---|
| `player_id` | Number | Platform player ID |
| `full_name` | String | Player's display name |
| `points_scored` | Float | Fantasy points the player scored that week |
| `position` | String | Player's real position (e.g. `QB`, `RB`, `WR`, `TE`, `D/ST`, `K`) |
| `fantasy_position` | String \| absent | The starter's lineup **slot** (e.g. `QB`, `RB`, `FLEX`, `D/ST`); present only on starters |

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
<summary><b>DRAFT</b></summary>

Represents all draft picks across all seasons in the fantasy league. One item per season; each pick in the draft is an element in the `data` list.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{league_id}` |
| `SK` | String | Yes | `DRAFT#{season}` |
| `data` | List\<Object\> | Yes | A list of objects, one per draft pick |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `team_id` | String | Team ID within the league that made the pick |
| `owner_username` | String | Platform display name of the team owner |
| `team_name` | String | Team name set by the owner |
| `team_logo` | String \| null | URL to the team logo |
| `pick_id` | String \| null | Platform-specific pick identifier; null for Sleeper |
| `round` | Integer | Round number in the draft |
| `round_pick_number` | Integer | Pick number within the round |
| `overall_pick_number` | Integer | Overall pick number across all rounds |
| `player_id` | String | Platform player ID of the drafted player |
| `player_name` | String \| null | Full name of the drafted player |
| `position` | String \| null | Player's primary position (e.g. `"QB"`, `"RB"`, `"WR"`, `"TE"`, `"K"`, `"D/ST"`) |
| `total_points` | Float \| null | Player's total scoring points for the season; null if unavailable |
| `keeper` | Boolean \| null | Whether the pick was a keeper |
| `reserved_for_keeper` | Boolean \| null | Whether the pick slot was reserved for a keeper; null for Sleeper |
| `auto_draft_type_id` | Integer \| null | ESPN auto-draft type identifier; null for Sleeper |
| `bid_amount` | Integer \| null | Auction bid amount; null for Sleeper |
| `lineup_slot_id` | Integer \| null | ESPN lineup slot identifier; null for Sleeper |
| `member_id` | String \| null | Platform user ID of the member who made the pick |
| `nominating_team_id` | String \| null | Team ID that nominated the player (auction drafts); null for Sleeper |
| `trade_locked` | Boolean \| null | Whether the pick is trade-locked; null for Sleeper |
| `season` | String | Season year (e.g. `"2025"`) |
| `drafted_position_rank` | Integer | Rank at which this player was drafted among players at the same position |
| `actual_position_rank` | Integer \| null | Player's actual end-of-season rank among players at the same position by total points |
| `draft_rank_delta` | Integer \| null | `drafted_position_rank - actual_position_rank`; negative means the player outperformed draft position |
| `vorp` | Float \| null | Value over replacement player (points above replacement level); null for K and D/ST positions |

**Example:**
```json
{
  "PK": "LEAGUE#123456789",
  "SK": "DRAFT#2025",
  "data": [
    {
      "team_id": "1",
      "owner_username": "myusername123",
      "team_name": "Player One's Team",
      "team_logo": "https://example.com/logo.png",
      "pick_id": null,
      "round": 1,
      "round_pick_number": 1,
      "overall_pick_number": 1,
      "player_id": "4046",
      "player_name": "Christian McCaffrey",
      "position": "RB",
      "total_points": 312.4,
      "keeper": false,
      "reserved_for_keeper": null,
      "auto_draft_type_id": null,
      "bid_amount": null,
      "lineup_slot_id": null,
      "member_id": "pid1",
      "nominating_team_id": null,
      "trade_locked": null,
      "season": "2025",
      "drafted_position_rank": 1,
      "actual_position_rank": 1,
      "draft_rank_delta": 0,
      "vorp": 201.3
    }
  ]
}
```
</details>

<details>
<summary><b>TRANSACTIONS</b></summary>

Sleeper-only ([backend/sleeper-transactions](../requirements/backend/backend/sleeper-transactions-sleeper-transactions.md)). Represents completed league transactions (waivers, trades, free-agent moves, commissioner moves) for a season. One item per season; each transaction is an element in the `data` list. ESPN leagues have no equivalent data and no `TRANSACTIONS` item is written.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{canonical_league_id}` |
| `SK` | String | Yes | `TRANSACTIONS#{season}` |
| `data` | List\<Object\> | Yes | A list of objects, one per completed transaction |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `season` | String | Season year (e.g. `"2025"`) |
| `transaction_id` | String | Sleeper transaction ID |
| `type` | String | `"waiver"`, `"trade"`, `"free_agent"`, or `"commissioner"` |
| `week` | Integer | Sleeper `leg` (week of the transaction) |
| `created` | Integer | Creation time (Unix epoch milliseconds); used to order newest-first |
| `roster_ids` | List\<String\> | Roster IDs involved in the transaction |
| `teams` | List\<Object\> | Involved teams: `{roster_id, team_name, display_name}` (`team_name`/`display_name` null if unresolved) |
| `adds` | List\<Object\> | Players added: `{player_id, player_name, position, roster_id}` (`player_name`/`position` null if unknown) |
| `drops` | List\<Object\> | Players dropped: same shape as `adds` |
| `draft_picks` | List\<Object\> | Picks exchanged: `{round, season, from_roster_id, to_roster_id}` |
| `waiver_bid` | Integer \| null | FAAB bid amount for waiver claims; null otherwise |

**Example:**
```json
{
  "PK": "LEAGUE#uuid-string",
  "SK": "TRANSACTIONS#2025",
  "data": [
    {
      "season": "2025",
      "transaction_id": "1271340777452085248",
      "type": "waiver",
      "week": 1,
      "created": 1757473771015,
      "roster_ids": ["8"],
      "teams": [
        { "roster_id": "8", "team_name": "Team X", "display_name": "user8" }
      ],
      "adds": [
        { "player_id": "9504", "player_name": "Player A", "position": "RB", "roster_id": "8" }
      ],
      "drops": [
        { "player_id": "10219", "player_name": "Player B", "position": "WR", "roster_id": "8" }
      ],
      "draft_picks": [],
      "waiver_bid": 0
    }
  ]
}
```
</details>

<details>
<summary><b>PLATFORM_MIGRATION</b></summary>

Stores the manager identity mapping created when a league migrates from one platform to another (e.g. ESPN → Sleeper). Written by the API at migration initiation and read by the onboarder Lambda to resolve cross-platform owner IDs during data processing.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `LEAGUE#{canonical_league_id}` |
| `SK` | String | Yes | `PLATFORM_MIGRATION#{fromPlatform}#{toPlatform}` (e.g. `PLATFORM_MIGRATION#ESPN#SLEEPER`) |
| `data` | List\<Object\> | Yes | One entry per manager mapping |

**`data[n]` object:**

| Attribute | Type | Description |
|---|---|---|
| `currentPlatformOwnerId` | String | Owner ID on the source platform |
| `newPlatformOwnerId` | String | Owner ID on the destination platform; `__not_returning__` for managers who left the league |
| `displayName` | String | Human-readable name used for display (typically the source-platform username) |

**Example:**
```json
{
  "PK": "LEAGUE#uuid-string",
  "SK": "PLATFORM_MIGRATION#ESPN#SLEEPER",
  "data": [
    {
      "currentPlatformOwnerId": "espn-owner-id-1",
      "newPlatformOwnerId": "sleeper-owner-id-1",
      "displayName": "myusername123"
    },
    {
      "currentPlatformOwnerId": "espn-owner-id-2",
      "newPlatformOwnerId": "__not_returning__",
      "displayName": "formeruser456"
    }
  ]
}
```
</details>

<details>
<summary><b>JOB_STATUS</b></summary>

Tracks the lifecycle of a single onboard/refresh/migrate job so the frontend can poll it
(`GET /jobs/{jobId}`) and surface a real failure reason. Keyed by `correlation_id` — the only
identifier known end-to-end at job-creation time, even before a league lookup record exists
(e.g. a brand-new onboard). The API creates the item as `IN_PROGRESS` when it triggers a job;
the onboarder / processor later upsert it to `COMPLETED` / `FAILED`. All writes are best-effort
(a failed write is logged and swallowed, never crashing the Lambda), and every write refreshes
the 24h TTL so old jobs self-clean. The METADATA `active_job_id` field points at the current
job's item.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `PK` | String | Yes | `JOB#{correlation_id}` |
| `SK` | String | Yes | `JOB_STATUS` |
| `status` | String | Yes | Job lifecycle state. Enum: `IN_PROGRESS`, `COMPLETED`, `FAILED` |
| `request_type` | String | Yes | The triggering request. Enum: `ONBOARD`, `REFRESH`, `MIGRATE`. Set by the creator; preserved on terminal writes that omit it |
| `created_at` | String | Yes | ISO 8601 (UTC) timestamp of when the job was created (`if_not_exists`, so preserved across upserts) |
| `updated_at` | String | Yes | ISO 8601 (UTC) timestamp of the most recent write |
| `ttl` | Number | Yes | Unix epoch seconds after which DynamoDB TTL reaps the item (24h from the last write) |
| `failure_code` | String | No | Machine-readable failure classification, only set on `FAILED`. Enum: `INVALID_INPUT`, `ESPN_AUTH`, `NOT_FOUND`, `NOT_STARTED`, `UPSTREAM`, `PROCESSING`, `INTERNAL` |
| `failure_reason` | String | No | User-facing failure message derived from `failure_code`. Never contains raw exception detail, credentials, or stack traces |
| `league_id` | String | No | Platform league ID, recorded for observability when known |
| `platform` | String | No | Platform the job targets (observability). Enum: `ESPN`, `SLEEPER` |
| `canonical_league_id` | String | No | Canonical league ID, recorded for observability when known |

**Example:**
```json
{
  "PK": "JOB#8f2c1a90-2b7e-4d3a-9c1e-0a1b2c3d4e5f",
  "SK": "JOB_STATUS",
  "status": "FAILED",
  "request_type": "ONBOARD",
  "created_at": "2024-09-01T00:00:00Z",
  "updated_at": "2024-09-01T00:00:12Z",
  "ttl": 1725238812,
  "failure_code": "NOT_FOUND",
  "failure_reason": "We couldn't find that league on ESPN. Please confirm the league ID is correct.",
  "league_id": "123456789",
  "platform": "ESPN"
}
```
</details>
