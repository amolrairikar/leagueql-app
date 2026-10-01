import { act, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';
import { expect } from 'vitest';

import { LineupBackfillBell } from '../lineup-backfill-bell';

import type { Platform } from '@/lib/cookie-handler';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/lineup_backfill/__tests__/lineup-backfill-bell.feature',
);

const BELL = { name: 'Player score notifications' };

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function renderBell(platform: Platform = 'YAHOO') {
  await renderRoute(<LineupBackfillBell />, {
    league: { leagueId: '100', platform, seasons: ['2024'] },
  });
}

defineFeature(feature, (test) => {
  test('Seasons still loading', ({ given, when, then }) => {
    given(/^a Yahoo league with pending lineup seasons "(.*)"$/, (seasons) => {
      server.use(
        leagueMetadata({ pending_lineup_seasons: seasons.split(',') }),
      );
    });
    when('I render the lineup bell', () => renderBell());
    then('I see the bell indicator', async () => {
      expect(await screen.findByRole('button', BELL)).toBeInTheDocument();
      expect(screen.getByTestId('lineup-bell-indicator')).toBeInTheDocument();
    });
    when('I open the bell', async () => {
      await userEvent.click(screen.getByRole('button', BELL));
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(new RegExp(text))).toBeInTheDocument();
    });
  });

  test("A season that couldn't be loaded yet", ({ given, when, and, then }) => {
    given(/^a Yahoo league with failed lineup season "(.*)"$/, (season) => {
      server.use(leagueMetadata({ failed_lineup_seasons: [season] }));
    });
    when('I render the lineup bell', () => renderBell());
    and('I open the bell', async () => {
      await userEvent.click(await screen.findByRole('button', BELL));
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect(await screen.findByText(new RegExp(text))).toBeInTheDocument();
    });
  });

  test('Nothing pending hides the bell', ({ given, when, then }) => {
    given('a Yahoo league with no pending lineup seasons', () => {
      server.use(leagueMetadata({}));
    });
    when('I render the lineup bell', () => renderBell());
    then('I do not see the bell', async () => {
      await flush();
      expect(screen.queryByRole('button', BELL)).not.toBeInTheDocument();
    });
  });

  test('A failed metadata request hides the bell', ({ given, when, then }) => {
    given('the league metadata request fails', () => {
      server.use(
        http.get('*/leagues/:id', () =>
          HttpResponse.json({ detail: 'boom' }, { status: 500 }),
        ),
      );
    });
    when('I render the lineup bell', () => renderBell());
    then('I do not see the bell', async () => {
      await flush();
      expect(screen.queryByRole('button', BELL)).not.toBeInTheDocument();
    });
  });

  test('Non-Yahoo leagues never show the bell', ({ given, when, then }) => {
    given('a Sleeper league', () => {
      // No metadata handler: a fetch would be an unhandled request and fail the test.
    });
    when('I render the lineup bell for a Sleeper league', () =>
      renderBell('SLEEPER'),
    );
    then('I do not see the bell', async () => {
      await flush();
      expect(screen.queryByRole('button', BELL)).not.toBeInTheDocument();
    });
  });
});
