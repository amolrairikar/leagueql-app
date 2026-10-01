import { act, screen } from '@testing-library/react';
import { defineFeature, loadFeature } from 'jest-cucumber';
import { expect } from 'vitest';

import type { MatchupItem } from '@/components/api/types';
import { BoxScoreCard, type BoxScoreSide } from '@/components/box-score-card';
import { MATCHUPS } from '@/test/fixtures';
import { leagueMetadata, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature(
  'src/features/lineup_backfill/__tests__/box-score-pending.feature',
);

const M = MATCHUPS[0] as MatchupItem;
const side = (a: boolean): BoxScoreSide => ({
  teamLogo: null,
  teamName: a ? M.team_a_team_name : M.team_b_team_name,
  ownerUsername: a ? M.team_a_display_name : M.team_b_display_name,
  color: '#000',
  score: a ? M.team_a_score : M.team_b_score,
  starters: (a ? M.team_a_starters : M.team_b_starters) ?? [],
  bench: (a ? M.team_a_bench : M.team_b_bench) ?? [],
  isWinner: a,
});

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

defineFeature(feature, (test) => {
  const renderBoxScore = async () => {
    await renderRoute(
      <BoxScoreCard
        left={side(true)}
        right={side(false)}
        platform="YAHOO"
        season="2024"
      />,
      { league: { leagueId: '100', platform: 'YAHOO', seasons: ['2024'] } },
    );
    await flush();
  };

  test('A pending season shows the placeholder and no lineup efficiency', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a Yahoo league whose 2024 player scores are still loading', () => {
      server.use(leagueMetadata({ pending_lineup_seasons: ['2024'] }));
    });
    when('I render a 2024 box score', renderBoxScore);
    then(/^I see (\d+) "(.*)" placeholders$/, async (count, text) => {
      expect(await screen.findAllByText(text)).toHaveLength(Number(count));
    });
    and('I see no lineup efficiency', () => {
      expect(screen.queryByText(/% efficient/)).not.toBeInTheDocument();
    });
    and(/^I do not see the player "(.*)"$/, (name) => {
      expect(screen.queryByText(name)).not.toBeInTheDocument();
    });
  });

  test('A loaded season shows lineups and lineup efficiency', ({
    given,
    when,
    then,
    and,
  }) => {
    given('a Yahoo league whose 2024 player scores are loaded', () => {
      server.use(leagueMetadata({}));
    });
    when('I render a 2024 box score', renderBoxScore);
    then(/^I see the player "(.*)"$/, async (name) => {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0);
    });
    and('I see lineup efficiency', () => {
      expect(screen.getAllByText(/% efficient/).length).toBeGreaterThan(0);
    });
  });
});
