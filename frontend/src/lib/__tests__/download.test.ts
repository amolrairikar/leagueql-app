import JSZip from 'jszip';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { downloadLeagueZip } from '@/lib/download';

describe('downloadLeagueZip', () => {
  let captured: Blob | undefined;

  beforeEach(() => {
    captured = undefined;
    // jsdom has no object-URL support; capture the generated ZIP blob instead.
    URL.createObjectURL = vi.fn((blob: Blob) => {
      captured = blob;
      return 'blob:mock';
    });
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(
      () => undefined,
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('writes the README, manifest, and one JSON file per view per season', async () => {
    await downloadLeagueZip(
      'leagueql_export_100.zip',
      { '2024': { standings: [{ team_id: '1' }] } },
      {
        leagueId: '100',
        platform: 'SLEEPER',
        exportedAt: '2026-09-27T12:00:00.000Z',
      },
    );

    expect(captured).toBeDefined();
    const zip = await JSZip.loadAsync(await captured!.arrayBuffer());

    expect(Object.keys(zip.files).sort()).toEqual([
      '2024_standings.json',
      'README.md',
      'manifest.json',
    ]);
    expect(
      JSON.parse(await zip.file('2024_standings.json')!.async('string')),
    ).toEqual([{ team_id: '1' }]);
    const manifest = JSON.parse(
      await zip.file('manifest.json')!.async('string'),
    ) as { league_id: string; files: unknown[] };
    expect(manifest.league_id).toBe('100');
    expect(manifest.files).toHaveLength(1);
    expect(await zip.file('README.md')!.async('string')).toContain(
      '# LeagueQL league export',
    );
  });
});
