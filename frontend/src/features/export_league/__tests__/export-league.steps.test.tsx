import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { expect, vi } from 'vitest';

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
      expect(screen.getByLabelText('Select all')).toBeInTheDocument();
    });

    and('the export button is disabled', () => {
      expect(screen.getByRole('button', { name: /^export$/i })).toBeDisabled();
    });
  });

  test('Selecting all seasons and exporting downloads a ZIP', ({
    given,
    when,
    then,
    and,
  }) => {
    let requestedSeasons: string | null = null;

    given(
      /^the export dialog is open for a league with seasons "(.*)"$/,
      async (seasons) => {
        vi.mocked(downloadLeagueZip).mockClear();
        server.use(
          http.get(`${API}/leagues/:id/export`, ({ request }) => {
            requestedSeasons = new URL(request.url).searchParams.get('seasons');
            return HttpResponse.json({
              data: { '2024': { standings: [{ team: 'A' }] } },
            });
          }),
        );
        await openDialog(seasons.split(','));
      },
    );

    when('I select all seasons', async () => {
      await userEvent.click(screen.getByLabelText('Select all'));
    });

    when('I click export', async () => {
      await userEvent.click(screen.getByRole('button', { name: /^export$/i }));
    });

    then('the league data is downloaded as a ZIP', async () => {
      await vi.waitFor(() =>
        expect(vi.mocked(downloadLeagueZip)).toHaveBeenCalledTimes(1),
      );
      expect(vi.mocked(downloadLeagueZip)).toHaveBeenCalledWith(
        'leagueql_export_100.zip',
        { '2024': { standings: [{ team: 'A' }] } },
      );
    });

    and(/^the export was requested for seasons "(.*)"$/, (seasons: string) => {
      const expected = seasons.split(',').sort();
      expect((requestedSeasons ?? '').split(',').sort()).toEqual(expected);
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
