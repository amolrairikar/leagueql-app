import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, vi } from 'vitest';

import { ExportLeagueDialog } from '../export-league-dialog';

import { downloadLeagueZip } from '@/lib/download';
import { API, leagueExportError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

// Downloading is a browser side effect jsdom can't perform, so the ZIP-build +
// download util is mocked; the test asserts the dialog invokes it with the bundle.
vi.mock('@/lib/download', () => ({
  downloadLeagueZip: vi.fn().mockResolvedValue(undefined),
}));

const feature = loadFeature(
  'src/features/export_league/__tests__/export-league.feature',
);

// Per-test export behaviour: seasons mapped to an error status (default: success with
// a one-view bundle for that season). `requestedSeasons` records each request's
// `seasons` query value so tests can assert one request per season.
let seasonStatus: Record<string, number> = {};
let requestedSeasons: string[] = [];

beforeEach(() => {
  seasonStatus = {};
  requestedSeasons = [];
  vi.mocked(downloadLeagueZip).mockClear();
  server.use(
    http.get(`${API}/leagues/:id/export`, ({ request }) => {
      const season = new URL(request.url).searchParams.get('seasons') ?? '';
      requestedSeasons.push(season);
      const status = seasonStatus[season];
      if (status) {
        return HttpResponse.json(
          { detail: status === 404 ? 'Not found' : 'Internal Server Error' },
          { status },
        );
      }
      return HttpResponse.json({
        data: { [season]: { standings: [{ team: 'A' }] } },
      });
    }),
  );
});

async function selectAll() {
  await userEvent.click(screen.getByLabelText('Export all seasons'));
}

async function clickExport() {
  await userEvent.click(screen.getByRole('button', { name: /^export$/i }));
}

function openDialog(seasons: string[]) {
  return renderRoute(<ExportLeagueDialog open onOpenChange={vi.fn()} />, {
    league: { leagueId: '100', platform: 'SLEEPER', seasons },
  });
}

defineFeature(feature, (test) => {
  test('Season checkboxes render and export is disabled until a season is picked', ({
    given,
    then,
    and,
  }) => {
    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        vi.mocked(downloadLeagueZip).mockClear();
        await openDialog(seasons.split(','));
      },
    );

    then('I see a checkbox for each season', () => {
      for (const season of ['2022', '2023', '2024']) {
        expect(screen.getByLabelText(season)).toBeInTheDocument();
      }
      expect(screen.getByLabelText('Export all seasons')).toBeInTheDocument();
    });

    and('the export button is disabled', () => {
      expect(screen.getByRole('button', { name: /^export$/i })).toBeDisabled();
    });
  });

  test('The dialog suggests uploading the export to an AI assistant', ({
    given,
    then,
  }) => {
    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        await openDialog(seasons.split(','));
      },
    );

    then('I see a hint about using the export with an AI assistant', () => {
      expect(
        screen.getByText(/upload the ZIP to an AI assistant/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/roast my draft/i)).toBeInTheDocument();
    });
  });

  test('Selecting all seasons and exporting downloads a ZIP', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        await openDialog(seasons.split(','));
      },
    );

    when('I select all seasons', selectAll);
    when('I click export', clickExport);

    then(
      /^the league data is downloaded as a ZIP containing seasons "(.*)"$/,
      async (seasons: string) => {
        await vi.waitFor(() =>
          expect(vi.mocked(downloadLeagueZip)).toHaveBeenCalledTimes(1),
        );
        const call = vi.mocked(downloadLeagueZip).mock.calls[0];
        expect(call[0]).toBe('leagueql_export_100.zip');
        expect(Object.keys(call[1]).sort()).toEqual(seasons.split(',').sort());
        expect(call[2]).toEqual(
          expect.objectContaining({
            leagueId: '100',
            platform: 'SLEEPER',
            exportedAt: expect.any(String) as string,
          }),
        );
      },
    );

    and(
      /^a separate export request was made for each of seasons "(.*)"$/,
      (seasons: string) => {
        // One request per season, each carrying a single season value.
        expect(requestedSeasons.sort()).toEqual(seasons.split(',').sort());
      },
    );
  });

  test('A season with no data is omitted from the ZIP', ({
    given,
    and,
    when,
    then,
  }) => {
    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        await openDialog(seasons.split(','));
      },
    );
    and(/^the export endpoint reports no data for season "(.*)"$/, (s) => {
      seasonStatus[s] = 404;
    });
    when('I select all seasons', selectAll);
    when('I click export', clickExport);
    then(
      /^the league data is downloaded as a ZIP containing seasons "(.*)"$/,
      async (seasons: string) => {
        await vi.waitFor(() =>
          expect(vi.mocked(downloadLeagueZip)).toHaveBeenCalledTimes(1),
        );
        expect(
          Object.keys(vi.mocked(downloadLeagueZip).mock.calls[0][1]),
        ).toEqual(seasons.split(','));
      },
    );
  });

  test('One season failing aborts the whole export', ({
    given,
    and,
    when,
    then,
  }) => {
    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        await openDialog(seasons.split(','));
      },
    );
    and(/^the export endpoint fails for season "(.*)"$/, (s) => {
      seasonStatus[s] = 500;
    });
    when('I select all seasons', selectAll);
    when('I click export', clickExport);
    then('I see an inline export error', async () => {
      expect(
        await screen.findByText(/internal server error/i),
      ).toBeInTheDocument();
    });
    and('no file is downloaded', () => {
      expect(vi.mocked(downloadLeagueZip)).not.toHaveBeenCalled();
    });
  });

  test('Every selected season having no data shows an inline error', ({
    given,
    and,
    when,
    then,
  }) => {
    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        await openDialog(seasons.split(','));
      },
    );
    and(/^the export endpoint reports no data for season "(.*)"$/, (s) => {
      seasonStatus[s] = 404;
    });
    and(/^the export endpoint reports no data for season "(.*)"$/, (s) => {
      seasonStatus[s] = 404;
    });
    when('I select all seasons', selectAll);
    when('I click export', clickExport);
    then('I see an inline no-data export error', async () => {
      expect(
        await screen.findByText(/no data found for the selected seasons/i),
      ).toBeInTheDocument();
    });
    and('no file is downloaded', () => {
      expect(vi.mocked(downloadLeagueZip)).not.toHaveBeenCalled();
    });
  });

  test('An export failure shows an inline error', ({
    given,
    when,
    then,
    and,
  }) => {
    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        vi.mocked(downloadLeagueZip).mockClear();
        await openDialog(seasons.split(','));
      },
    );

    and('the export endpoint will fail', () => {
      server.use(leagueExportError(500));
    });

    when(/^I select season "(.*)"$/, async (season) => {
      await userEvent.click(screen.getByLabelText(season));
    });

    when('I click export', async () => {
      await userEvent.click(screen.getByRole('button', { name: /^export$/i }));
    });

    then('I see an inline export error', async () => {
      expect(
        await screen.findByText(/internal server error/i),
      ).toBeInTheDocument();
    });

    and('no file is downloaded', () => {
      expect(vi.mocked(downloadLeagueZip)).not.toHaveBeenCalled();
    });
  });
});
