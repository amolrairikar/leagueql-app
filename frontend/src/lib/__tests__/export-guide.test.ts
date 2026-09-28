import { describe, expect, it } from 'vitest';

import {
  buildExportManifest,
  buildExportReadme,
  type ExportMeta,
} from '@/lib/export-guide';

const sleeperMeta: ExportMeta = {
  leagueId: '100',
  platform: 'SLEEPER',
  exportedAt: '2026-09-27T12:00:00.000Z',
};
const espnMeta: ExportMeta = { ...sleeperMeta, platform: 'ESPN' };

describe('export README', () => {
  it('lists only the included files and documents only the included views', () => {
    const readme = buildExportReadme(
      { '2024': { standings: [{}, {}], matchups: [{}] } },
      sleeperMeta,
    );

    expect(readme).toContain('`2024_standings.json` — 2 rows');
    expect(readme).toContain('`2024_matchups.json` — 1 row');
    expect(readme).toContain('### standings');
    expect(readme).toContain('### matchups');
    expect(readme).not.toContain('### draft');
    expect(readme).not.toContain('### transactions');
  });

  it('states the league, platform, seasons, and export time', () => {
    const readme = buildExportReadme(
      { '2024': { teams: [] }, '2023': { teams: [] } },
      sleeperMeta,
    );

    expect(readme).toContain('**League id:** 100');
    expect(readme).toContain('**Platform:** SLEEPER');
    expect(readme).toContain('**Seasons:** 2023, 2024');
    expect(readme).toContain('**Exported at:** 2026-09-27T12:00:00.000Z');
  });

  it('includes the ESPN transactions caveat only for ESPN exports', () => {
    const bundle = { '2025': { transactions: [{}] } };

    expect(buildExportReadme(bundle, espnMeta)).toMatch(
      /ESPN transactions cover only the current season/,
    );
    expect(buildExportReadme(bundle, sleeperMeta)).not.toMatch(
      /ESPN transactions/,
    );
  });

  it('marks an undocumented view instead of throwing', () => {
    const readme = buildExportReadme(
      { '2024': { mystery_view: [{}] } },
      sleeperMeta,
    );

    expect(readme).toContain('`2024_mystery_view.json` — 1 row');
    expect(readme).toContain('### mystery_view');
    expect(readme).toContain('Undocumented view');
  });

  it('suggests questions to ask an AI assistant', () => {
    const readme = buildExportReadme({ '2024': { teams: [] } }, sleeperMeta);

    expect(readme).toContain('## Questions to ask an AI assistant');
  });
});

describe('export manifest', () => {
  it('describes every data file with its season, view, and row count', () => {
    const manifest = buildExportManifest(
      {
        '2024': { standings: [{}], draft: [{}, {}] },
        '2023': { standings: Array.from({ length: 10 }, () => ({})) },
      },
      sleeperMeta,
    );

    expect(manifest).toEqual({
      league_id: '100',
      platform: 'SLEEPER',
      exported_at: '2026-09-27T12:00:00.000Z',
      seasons: ['2023', '2024'],
      files: [
        {
          path: '2023_standings.json',
          season: '2023',
          view: 'standings',
          row_count: 10,
        },
        {
          path: '2024_draft.json',
          season: '2024',
          view: 'draft',
          row_count: 2,
        },
        {
          path: '2024_standings.json',
          season: '2024',
          view: 'standings',
          row_count: 1,
        },
      ],
    });
  });
});
