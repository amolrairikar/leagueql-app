import { screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import { MembershipGuard } from '../membership-guard';

import type { Platform } from '@/lib/cookie-handler';
import { leagueMetadata, leagueMetadataError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/ownership/__tests__/membership-guard.feature',
);

interface LeagueFixture {
  leagueId: string;
  platform: Platform;
  seasons: string[];
}

const league: LeagueFixture = {
  leagueId: '100',
  platform: 'ESPN',
  seasons: ['2024'],
};

const yahooLeague: LeagueFixture = {
  leagueId: '100',
  platform: 'YAHOO',
  seasons: ['2024'],
};

async function openGuardedLeague(leagueFixture: LeagueFixture = league) {
  await renderRoute(
    <MembershipGuard>
      <div>Protected dashboard</div>
    </MembershipGuard>,
    { league: leagueFixture },
  );
}

defineFeature(feature, (test) => {
  test('A non-member is directed to an invite link', ({
    given,
    when,
    then,
    and,
  }) => {
    given('the ESPN league returns 403 for the current caller', () => {
      server.use(leagueMetadataError(403));
    });
    when(
      'I open the ESPN league behind the membership guard',
      openGuardedLeague,
    );
    then(/^I see the guidance "(.*)"$/, async (text) => {
      expect(await screen.findByText(new RegExp(text))).toBeInTheDocument();
    });
    and(/^I do not see the gated content "(.*)"$/, (text) => {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    });
  });

  test('A Yahoo non-member is directed to an invite link', ({
    given,
    when,
    then,
    and,
  }) => {
    given('the Yahoo league returns 403 for the current caller', () => {
      server.use(leagueMetadataError(403));
    });
    when('I open the Yahoo league behind the membership guard', async () => {
      await openGuardedLeague(yahooLeague);
    });
    then(/^I see the guidance "(.*)"$/, async (text) => {
      expect(await screen.findByText(new RegExp(text))).toBeInTheDocument();
    });
    and(/^I do not see the gated content "(.*)"$/, (text) => {
      expect(screen.queryByText(text)).not.toBeInTheDocument();
    });
  });

  test('A member sees the gated content', ({ given, when, then }) => {
    given('the ESPN league returns 200 for the current caller', () => {
      server.use(leagueMetadata({ seasons: ['2024'], is_owner: false }));
    });
    when(
      'I open the ESPN league behind the membership guard',
      openGuardedLeague,
    );
    then(/^I see the gated content "(.*)"$/, async (text) => {
      expect(await screen.findByText(text)).toBeInTheDocument();
    });
  });
});
