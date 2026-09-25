// In-app changelog content (frontend/changelog). This is the single source of truth for the
// LeagueQL changelog; add a new release here (newest first) when one ships.

export interface ChangelogSection {
  /** e.g. "Added", "Changed", "Fixed". */
  title: string;
  items: string[];
}

export interface ChangelogRelease {
  version: string;
  /** Human-readable release date, e.g. "June 12, 2026". */
  date: string;
  sections: ChangelogSection[];
}

// Newest release first.
export const CHANGELOG: ChangelogRelease[] = [
  {
    version: '1.9.0',
    date: 'September 24, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          'Playoff clinching scenarios on the Playoff Bracket page: below the projected standings, LeagueQL now spells out what each still-contending team needs down the stretch — a win that clinches a playoff berth ("win and in"), a loss that would knock them out ("must win"), or a single game that decides both. When a spot could come down to a tie, it shows the points-for margin a rival would have to make up. Scenarios update as you pick winners.',
        ],
      },
      {
        title: 'Changed',
        items: [
          "Connecting a league no longer fails when some seasons can't be read. LeagueQL now onboards every season it can access and skips only the ones it can't (for example, older ESPN seasons you no longer have access to) instead of failing the whole connection; the onboard only fails if no season could be loaded.",
        ],
      },
    ],
  },
  {
    version: '1.8.0',
    date: 'September 21, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          'Automatic weekly refresh for ESPN and Yahoo leagues (opt-in). Enable it when you connect a league and LeagueQL keeps your league up to date each week during the season. For ESPN, your cookies are stored encrypted so you no longer have to re-enter them each week (until they expire); Yahoo uses your existing connection. ESPN owners can turn it back off anytime with "Turn Off Auto-Refresh" in the sidebar.',
        ],
      },
      {
        title: 'Changed',
        items: [
          'Auto-refresh is now opt-in for Yahoo leagues. Existing Yahoo leagues will not auto-refresh until you enable it when connecting the league.',
        ],
      },
    ],
  },
  {
    version: '1.7.0',
    date: 'September 20, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          "Yahoo Fantasy support (Beta): connect a Yahoo league by selecting Yahoo on the landing page, entering your league ID, and authorizing LeagueQL through Yahoo's OAuth flow.",
        ],
      },
    ],
  },
  {
    version: '1.6.0',
    date: 'September 6, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          'Transactions page support for ESPN leagues: waivers, free-agent moves, and trades now appear for ESPN alongside Sleeper.',
          'Share a private ESPN league with your leaguemates using an invite link. Owners create a link from Invite Leaguemates in the sidebar; anyone who opens it and signs in can view the league.',
        ],
      },
    ],
  },
  {
    version: '1.5.0',
    date: 'August 27, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          "Playoff race predictor on the Playoff Bracket page: before the playoffs begin, step through the remaining regular-season weeks and pick each matchup's winner to watch the projected standings re-sort live. Standings are ordered by wins (season points-for breaks ties) and show seed-movement indicators, a cutoff line after your league's number of playoff teams, clinched-seed markers, and a playoff-odds column giving each team's chance of making the postseason.",
          'Available in demo mode, which replays the last three regular-season weeks as an interactive race.',
        ],
      },
    ],
  },
  {
    version: '1.4.0',
    date: 'August 22, 2026',
    sections: [
      {
        title: 'Changed',
        items: [
          'Redesigned landing page with a refreshed product showcase and clearer messaging.',
        ],
      },
    ],
  },
  {
    version: '1.3.0',
    date: 'July 20, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          "Schedule-swap simulator on the standings page: see what every team's record would be under each other manager's schedule, and find out who was schedule-lucky or robbed.",
          'Weekly awards & superlatives on the matchups page: per-week award cards (highest score, biggest blowout, closest call, and more) plus a running tally of who has collected the most.',
          'Lineup efficiency in every box score: see how many points each manager left on the bench, with a slot-by-slot start/sit report.',
          "Draft value chart on the draft recap page: a scatterplot of every pick's draft position against the points the pick scored.",
        ],
      },
    ],
  },
  {
    version: '1.2.0',
    date: 'June 14, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          "Owner summary table on the Transactions page: see each owner's waiver, free-agent, and trade counts for the season at a glance, with a combined total and rows ranked by who was most active.",
        ],
      },
    ],
  },
  {
    version: '1.1.0',
    date: 'June 12, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          "Transactions page for Sleeper leagues: browse each season's completed waivers, trades, and free-agent moves, newest first.",
          'Each transaction shows its type, week, and date, with the players and draft picks every team added (green) and dropped (red), plus the FAAB bid on waiver claims.',
          'Filter transactions by type (All, Trades, Waivers, Free Agents) and switch between onboarded seasons.',
        ],
      },
    ],
  },
  {
    version: '1.0.0',
    date: 'June 6, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          'Connect and onboard ESPN or Sleeper fantasy football leagues',
          'Home dashboard summarizing your league at a glance',
          'Season standings from each past + current season and season superlative awards',
          'All historical league matchups + box scores',
          'Playoff brackets from each season',
          'Head-to-head comparison of any two managers',
          "Year-to-year history of each manager's performance",
          'Recap of draft picks and grades',
          'All-time fantasy player performance records',
          'All-time fantasy team performance records',
          'League migration: track all-time metrics even if your fantasy league migrates platforms',
          'Refresh league data on demand (ESPN) or automatically each week during the season (Sleeper)',
          'League ownership controls: owner-gated management actions, private ESPN league access via membership verification, and ownership transfer via a one-time token',
          'Demo mode to explore a sample league without connecting your own',
          'LeagueQL ESPN Cookie Helper Chrome extension to autofill ESPN credentials',
          'Light and dark mode',
        ],
      },
    ],
  },
];
