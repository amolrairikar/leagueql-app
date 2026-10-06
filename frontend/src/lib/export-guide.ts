import type { Platform } from '@/components/api/types';

/** An export bundle: season → view name → rows (matches the /export response `data`). */
export type ExportBundle = Record<string, Record<string, unknown[]>>;

/** Describes the export a bundle came from; written into the README and manifest. */
export interface ExportMeta {
  leagueId: string;
  platform: Platform;
  /** ISO 8601 timestamp of when the export was taken. */
  exportedAt: string;
}

interface ViewDoc {
  summary: string;
  fields: Record<string, string>;
  notes?: string[];
  platformNotes?: Partial<Record<Platform, string>>;
}

export interface ExportManifest {
  league_id: string;
  platform: Platform;
  exported_at: string;
  seasons: string[];
  files: { path: string; season: string; view: string; row_count: number }[];
}

/**
 * Data dictionary for each view in a league export (frontend/export-league-data). Field
 * meanings mirror the processed views written by the processor (`src/processor/queries.py`);
 * update this map in the same change whenever a view's schema changes.
 */
export const EXPORT_VIEW_DOCS: Record<string, ViewDoc> = {
  teams: {
    summary:
      'One row per team in the season, with its owner(s) and final rank.',
    fields: {
      team_id: 'Team id; the join key used across every view for this season.',
      team_name: 'Team name.',
      display_name: "Primary owner's username.",
      team_logo: 'Team logo URL (may be null).',
      primary_owner_id: 'Owner (manager) id; stable across seasons.',
      secondary_owner_id: 'Co-owner id, or null.',
      final_rank: 'Final league placement (1 = champion).',
      season: 'Season year.',
    },
  },
  standings: {
    summary:
      'Final regular-season standings, one row per team. Playoff games are not included.',
    fields: {
      team_id: 'Team id (joins to teams.team_id).',
      owner_id: 'Owner id; stable across seasons.',
      owner_username: "Owner's username.",
      team_name: 'Team name.',
      final_rank: 'Final league placement including playoffs (1 = champion).',
      games_played: 'Regular-season games played.',
      'wins / losses / ties': 'Head-to-head regular-season record.',
      record: 'Record as "W-L-T".',
      win_pct: 'Head-to-head win percentage.',
      'total_vs_league_wins / total_vs_league_losses':
        '"All-play" record: results if the team had played every other team every week.',
      win_pct_vs_league:
        'All-play win percentage; compare with win_pct to gauge schedule luck.',
      'total_pf / total_pa': 'Total points for / against.',
      'avg_pf / avg_pa': 'Average points for / against per game.',
      champion: '"Yes" if the team won the league championship, else "No".',
      season: 'Season year.',
    },
  },
  weekly_standings: {
    summary:
      'Cumulative regular-season standings snapshot after each week, one row per team per week.',
    fields: {
      snapshot_week: 'Week the snapshot was taken after.',
      team_id: 'Team id (joins to teams.team_id).',
      owner_id: 'Owner id.',
      owner_username: "Owner's username.",
      '(remaining fields)':
        'Same meaning as in standings, cumulative through snapshot_week.',
    },
  },
  matchups: {
    summary:
      'Every head-to-head game (regular season and playoffs), one row per game with both teams.',
    fields: {
      week: 'Week number (string).',
      season: 'Season year.',
      'team_a_id / team_b_id': 'The two team ids (join to teams.team_id).',
      'team_a_display_name / team_b_display_name': "Owners' usernames.",
      'team_a_team_name / team_b_team_name': 'Team names.',
      'team_a_score / team_b_score': 'Points scored.',
      'team_a_starters / team_b_starters':
        'Started players: [{ player_id, full_name, position, fantasy_position, points_scored }]. fantasy_position is the lineup slot.',
      'team_a_bench / team_b_bench': 'Benched players, same shape as starters.',
      'team_a_primary_owner_id / team_b_primary_owner_id': 'Owner ids.',
      winner: 'Winning team id, or "TIE".',
      loser: 'Losing team id, or "TIE".',
      playoff_tier_type:
        '"NONE" for regular-season games; otherwise the playoff bracket (e.g. "WINNERS_BRACKET").',
      playoff_round:
        'Playoff round label (e.g. "Semifinals", "Finals", "Losers Bracket"), or null in the regular season.',
    },
    notes: [
      'Filter playoff_tier_type = "NONE" for regular-season-only analysis.',
      'Starters vs. bench points let you measure lineup decisions (points left on the bench).',
    ],
  },
  draft: {
    summary:
      'Every draft pick for the season, with how the player actually performed.',
    fields: {
      team_id: 'Drafting team id (joins to teams.team_id).',
      owner_username: "Drafting owner's username.",
      team_name: 'Drafting team name.',
      round: 'Draft round.',
      round_pick_number: 'Pick number within the round.',
      overall_pick_number: 'Overall pick number.',
      'player_id / player_name / position': 'The drafted player.',
      total_points: 'Fantasy points the player scored that season.',
      keeper: 'Whether the pick was a keeper.',
      is_auction: 'Whether the season used an auction draft.',
      bid_amount: 'Auction price (0 in snake drafts).',
      drafted_position_rank:
        'Where the player was drafted among their position (by pick order, or by price in auctions).',
      actual_position_rank:
        'Where the player finished among their position by total_points.',
      draft_rank_delta:
        'drafted_position_rank − actual_position_rank. Positive = the player outperformed their draft slot (a value pick); negative = underperformed (a reach/bust).',
      vorp: 'Value over a replacement-level player at the position (points). Null for K and D/ST.',
    },
  },
  transactions: {
    summary:
      'Completed roster transactions: waiver claims, free-agent pickups, and trades.',
    fields: {
      transaction_id: 'Transaction id.',
      type: '"waiver", "free_agent", "trade", or "commissioner".',
      week: 'Week the transaction happened.',
      created: 'Unix epoch milliseconds.',
      roster_ids: 'Team ids involved (roster_id corresponds to teams.team_id).',
      teams: 'Teams involved: [{ roster_id, team_name, display_name }].',
      adds: 'Players added: [{ player_id, player_name, position, roster_id }] (roster_id = receiving team).',
      drops:
        'Players dropped, same shape as adds (roster_id = team that dropped).',
      draft_picks:
        'Draft picks traded: [{ round, season, from_roster_id, to_roster_id }].',
      waiver_bid: 'FAAB bid amount, or null.',
    },
    platformNotes: {
      ESPN: 'ESPN transactions cover only the current season, include waiver, free-agent, and trade moves, and never include draft picks.',
    },
  },
  playoff_bracket: {
    summary: 'Winners-bracket playoff games, one row per bracket match.',
    fields: {
      match_id: 'Bracket match id.',
      round: 'Bracket round (1 = first round).',
      'team_1_id / team_2_id': 'The two team ids (join to teams.team_id).',
      'team_1_team_name / team_2_team_name': 'Team names.',
      'winner / loser': 'Winning / losing team id.',
      position:
        'Final placement decided by this game (1 = championship game), or null.',
      'team_1_from / team_2_from':
        'Where each team came from, e.g. {"w": 1} = winner of match 1; null for seeded teams.',
    },
  },
  league_settings: {
    summary: 'Playoff configuration for the season (one row).',
    fields: {
      num_playoff_teams: 'Number of teams that make the playoffs.',
      num_playoff_teams_assumed:
        'True when the platform did not report a playoff-team count and a default of 6 was used.',
      playoff_week_start: 'First playoff week.',
      regular_season_weeks: 'Number of regular-season weeks.',
    },
  },
};

const EXAMPLE_PROMPTS = [
  'Write a season-in-review recap for this league, with awards for each team.',
  "Roast my draft: which of my picks were the biggest busts and steals? (I'm <your username>)",
  'Build a profile for each manager, highlighting their tendencies.',
  "Which teams were luckiest or unluckiest? Compare each team's record to its all-play record.",
  'How many points did each team leave on the bench this season?',
];

function sortedSeasons(bundle: ExportBundle): string[] {
  return Object.keys(bundle).sort();
}

/** One entry per data file in the bundle, in season then view order. */
function dataFiles(bundle: ExportBundle): ExportManifest['files'] {
  return sortedSeasons(bundle).flatMap((season) =>
    Object.keys(bundle[season])
      .sort()
      .map((view) => ({
        path: `${season}_${view}.json`,
        season,
        view,
        row_count: bundle[season][view].length,
      })),
  );
}

/** Machine-readable description of an export (`manifest.json`). */
export function buildExportManifest(
  bundle: ExportBundle,
  meta: ExportMeta,
): ExportManifest {
  return {
    league_id: meta.leagueId,
    platform: meta.platform,
    exported_at: meta.exportedAt,
    seasons: sortedSeasons(bundle),
    files: dataFiles(bundle),
  };
}

/**
 * Markdown data guide (`README.md`) for an export, tailored to the views, seasons,
 * and platform actually present so an AI assistant can interpret the files.
 */
export function buildExportReadme(
  bundle: ExportBundle,
  meta: ExportMeta,
): string {
  const seasons = sortedSeasons(bundle);
  const files = dataFiles(bundle);
  const views = [...new Set(files.map((f) => f.view))].sort();

  const lines: string[] = [
    '# LeagueQL league export',
    '',
    'Processed fantasy football data for one league, exported from LeagueQL (https://leagueql.app).',
    'This guide explains every file so you — or an AI assistant you upload this ZIP to — can analyze it.',
    '',
    `- **League id:** ${meta.leagueId}`,
    `- **Platform:** ${meta.platform}`,
    `- **Seasons:** ${seasons.join(', ')}`,
    `- **Exported at:** ${meta.exportedAt}`,
    '',
    '## Files',
    '',
    'Each data file is a JSON array of rows, named `<season>_<view>.json`. A view with no data',
    'for a season is omitted rather than included as an empty file. `manifest.json` lists the',
    'same files in machine-readable form.',
    '',
    ...files.map(
      (f) =>
        `- \`${f.path}\` — ${f.row_count} ${f.row_count === 1 ? 'row' : 'rows'}`,
    ),
    '',
    '## How the files join',
    '',
    '- `team_id` identifies a team within a season and joins every view (transactions call it `roster_id`).',
    '- Team ids are per season; use `owner_id` / `primary_owner_id` to follow a manager across seasons.',
    '- `season` is a year string; matchups and transactions also carry `week`.',
    '',
    '## Views',
  ];

  for (const view of views) {
    const doc = EXPORT_VIEW_DOCS[view];
    lines.push('', `### ${view}`, '');
    if (!doc) {
      lines.push('_Undocumented view — inspect the rows to infer its fields._');
      continue;
    }
    lines.push(doc.summary, '');
    for (const [field, description] of Object.entries(doc.fields)) {
      lines.push(`- \`${field}\`: ${description}`);
    }
    const notes = [...(doc.notes ?? [])];
    const platformNote = doc.platformNotes?.[meta.platform];
    if (platformNote) notes.push(platformNote);
    if (notes.length > 0) {
      lines.push('', ...notes.map((note) => `> ${note}`));
    }
  }

  lines.push(
    '',
    '## Questions to ask an AI assistant',
    '',
    ...EXAMPLE_PROMPTS.map((prompt) => `- ${prompt}`),
    '',
  );

  return lines.join('\n');
}
