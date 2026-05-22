# LeagueQL User Guide

## Table of Contents

1. [Getting Started](#getting-started)
   - [Authentication](#authentication)
   - [Demo Mode](#demo-mode)
   - [Connecting a League](#connecting-a-league)
     - [ESPN Leagues](#espn-leagues)
     - [Sleeper Leagues](#sleeper-leagues)
2. [Navigation](#navigation)
3. [Pages and Features](#pages-and-features)
   - [Home](#home)
   - [Standings](#standings)
   - [Matchups](#matchups)
   - [Playoff Bracket](#playoff-bracket)
   - [Manager Comparison](#manager-comparison)
   - [Manager History](#manager-history)
   - [Draft Recap](#draft-recap)
   - [Player Records](#player-records)
   - [Matchup Records](#matchup-records)
4. [Managing Your League](#managing-your-league)
   - [Refreshing League Data](#refreshing-league-data)
   - [Switching Leagues](#switching-leagues)
   - [Deleting a League](#deleting-a-league)
5. [FAQ and Troubleshooting](#faq-and-troubleshooting)

---

## Getting Started
Note that this app is designed for a web browser, not a mobile browser. Your experience may vary on mobile devices.

### Authentication

LeagueQL uses Clerk for authentication. From the landing page, click **Connect Your League** and sign in when prompted. After signing in you are redirected to the league selection page.

### Demo Mode

Want to explore the app before connecting your own league? Click **View Demo** on the landing page. A sample league is pre-loaded so you can navigate every page. A blue banner at the top of the screen indicates you are in demo mode. Click **Exit Demo** in the sidebar to return to the landing page and connect your own league.

### Connecting a League

Navigate to **Connect a new league** from the league selection page. Choose your platform (ESPN or Sleeper) and fill in the required fields. The system automatically detects whether this is a new league or an existing one and either onboards or refreshes accordingly.

It will typically take ~45 seconds to onboard a new league (there is a lot of data being fetched and processed on the backend!). On success you are redirected to your league's home dashboard.

#### ESPN Leagues

| Field | Description |
|---|---|
| League ID | The numeric ID in your ESPN fantasy URL (e.g. `?leagueId=12345`) |
| Latest Season | The most recent year your league was active |
| SWID Cookie | Found in your browser's DevTools under **Application → Cookies → fantasy.espn.com** |
| ESPN S2 Cookie | Found in the same location as SWID |

> Your SWID and ESPN S2 cookies are transmitted once over HTTPS to fetch your data and are never stored by LeagueQL.

#### Sleeper Leagues

| Field | Description |
|---|---|
| League ID | The numeric ID found in your Sleeper league URL |

Sleeper leagues are public, so no credentials are required.

---

## Navigation

All analysis pages are accessible from the **sidebar** on the left side of the screen. The sidebar can be collapsed to icon-only mode using the toggle button in the top header.

The top header also contains:
- **LeagueQL logo** — returns you to the home dashboard
- **GitHub, Changelog, Docs** links
- **Dark/light mode toggle**

At the bottom of the sidebar you will find league management options: refresh your league, switch to view another league, and delete the current league.

---

## Pages and Features

### Home

A high-level overview of your entire league history.

- Total seasons played, total matchups, and total members
- Record-setting single-game scores
- **Championship timeline gallery** — every season's champion at a glance
- **All-time standings chart** — a line chart tracking each manager's final standings position across every season, showing trends and consistency over time

---

### Standings

Tracks how the regular season unfolded week by week.

- Select a season from the dropdown at the top of the page
- A chart shows each team's cumulative win progression over the course of the regular season, revealing which teams surged late or faded down the stretch

---

### Matchups

The complete game-by-game log for your league.

- Filter by season and week using the dropdowns
- Each matchup card shows the final score for both teams
- View the box score to see full box scores including starters and bench players

---

### Playoff Bracket

A visual representation of the playoff field for any season.

- Select a season to view its bracket
- Scores and results are displayed for each matchup, from the first round through the championship

---

### Manager Comparison

Head-to-head analysis between any two managers across all seasons.

- Select two managers from the dropdowns
- View the complete game log of every matchup between them
- Summary statistics include all-time wins, average points scored, single-game high score, and longest win streak for each manager in the head-to-head series

---

### Manager History

An individual manager's full performance profile.

- Select a manager from the dropdown
- See championship wins, playoff appearances, and season-by-season records
- View average scoring trends over the years
- Review rivalry records against every other manager in the league

---

### Draft Recap

A season-by-season breakdown of how each draft played out.

- Select a season to analyze
- Every pick is evaluated against actual in-season performance
- **Steals** — players who significantly outperformed their draft position
- **Busts** — players who significantly underperformed
- Suggested alternatives show who was available nearby in the draft and would have been a better pick

---

### Player Records

The best individual player performances in league history.

- **Single-game records** — highest score posted by any player in a single week
- **Season records** — top cumulative scoring seasons
- Results are broken down by position

---

### Matchup Records

All-time team-level records across every game ever played.

| Record | Description |
|---|---|
| Highest team score | The single-game team high |
| Lowest team score | The single-game team low |
| Biggest blowout | Largest margin of victory |
| Closest game | Smallest margin of victory |
| Highest combined score | Most total points in a single matchup |
| Lowest combined score | Fewest total points in a single matchup |

---

## Managing Your League

### Refreshing League Data

#### ESPN
To refresh your ESPN league, click the "Refresh League" button in the sidebar. This will navigate you to the league connection page where you can submit your league credentials again. The system detects the league already exists and runs a refresh instead of a full re-onboard, which is faster.

#### Sleeper
If refreshing during the current season, simply click the "Refresh League" button in the sidebar. This will navigate you to the league connection page where you can submit your league ID again. The system detects the league already exists and runs a refresh instead of a full re-onboard, which is faster.

If refreshing for a new season, you will need to enter your new league ID as Sleeper league IDs change each season. The system will automatically associate the new league ID with previous league IDs from the same league.

### Switching Leagues

Click the **View Another League** button in the sidebar. You are taken to the league selection page where you can pick a previously connected league or add a new one.

### Deleting a League

Click **Delete League** at the bottom of the sidebar. This permanently removes all stored data for the league from LeagueQL's backend. This action cannot be undone.

---

## FAQ and Troubleshooting

**Why do I need ESPN cookies?**  <br>
ESPN private leagues require authentication. The SWID and ESPN S2 cookies prove you are a member of the league. They are used once to fetch data and are not stored.

**Where do I find my ESPN cookies?**  <br>
1. Open your browser and go to [fantasy.espn.com](https://fantasy.espn.com)
2. Log in to your account
3. Open DevTools (`F12` or `Cmd+Option+I`)
4. Go to **Application → Cookies → fantasy.espn.com**
5. Find `SWID` and `espn_s2` and copy their values

**The connection timed out — what happened?**  <br>
If the page shows a timeout error, note the **operation ID** displayed and try again. If the issue persists, file a bug report with the operation ID so it can be investigated.

**My data looks outdated — how do I refresh it?**  <br>
Go to the league connection page and re-submit your league details. The refresh pulls the latest data from ESPN or Sleeper.

**Can I connect more than one league?**  <br>
Yes. Use the **View Another League** option in the sidebar to view/onboard another league. Each league is stored independently.
