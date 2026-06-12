// In-app changelog content (FE-028). This is the single source of truth for the
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
    version: '1.1.0',
    date: 'June 12, 2026',
    sections: [
      {
        title: 'Added',
        items: [
          'Transactions page for Sleeper leagues: browse each season’s completed waivers, trades, and free-agent moves, newest first.',
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
          'Year-to-year history of each manager’s performance',
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
