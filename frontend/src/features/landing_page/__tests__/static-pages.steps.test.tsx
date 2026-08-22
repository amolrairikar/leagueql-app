import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { http, HttpResponse } from 'msw';

import ChangelogPage from '@/features/changelog/changelog-page';
import InstructionsPage from '@/features/instructions/instructions-page';
import LeagueQLLanding from '@/features/landing_page/landing-page';
import PrivacyPage from '@/features/privacy/privacy-page';
import { server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/landing_page/__tests__/static-pages.feature',
);

defineFeature(feature, (test) => {
  test('The landing page renders its primary call to action', ({
    when,
    then,
  }) => {
    when('I open the landing page', async () => {
      // The landing page fetches a live league count from a hardcoded URL; stub
      // it so the social-proof line resolves (FE-001 degrades gracefully if not).
      server.use(
        http.get('https://api.leagueql.com/counts', () =>
          HttpResponse.json({ leagueCount: 3 }),
        ),
      );
      await renderRoute(<LeagueQLLanding />, { route: '/' });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('The landing page showcases the product and feature highlights', ({
    when,
    then,
    and,
  }) => {
    when('I open the landing page', async () => {
      server.use(
        http.get('https://api.leagueql.com/counts', () =>
          HttpResponse.json({ leagueCount: 3 }),
        ),
      );
      await renderRoute(<LeagueQLLanding />, { route: '/' });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('The landing page still renders when the league count endpoint fails', ({
    when,
    then,
  }) => {
    when(
      'I open the landing page with the counts endpoint unavailable',
      async () => {
        // FE-001: the league-count figure must degrade gracefully (the pill hides)
        // without blocking the rest of the page from rendering.
        server.use(
          http.get('https://api.leagueql.com/counts', () =>
            HttpResponse.error(),
          ),
        );
        await renderRoute(<LeagueQLLanding />, { route: '/' });
      },
    );
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('The docs page renders', ({ when, then }) => {
    when('I open the docs page', async () => {
      await renderRoute(<InstructionsPage />, { route: '/docs' });
    });
    then(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('The privacy policy page renders', ({ when, then }) => {
    when('I open the privacy page', async () => {
      await renderRoute(<PrivacyPage />, { route: '/privacy' });
    });
    then(/^I see the heading "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });

  test('The changelog page renders', ({ when, then, and }) => {
    when('I open the changelog page', async () => {
      await renderRoute(<ChangelogPage />, { route: '/changelog' });
    });
    then(/^I see the heading "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
    and(/^I see "(.*)"$/, async (text) => {
      expect((await screen.findAllByText(text)).length).toBeGreaterThan(0);
    });
  });
});
