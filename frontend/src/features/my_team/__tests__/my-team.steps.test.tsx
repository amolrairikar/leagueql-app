import {
  act,
  cleanup,
  fireEvent,
  screen,
  within,
} from '@testing-library/react';
import {
  defineFeature,
  loadFeature,
  type DefineStepFunction,
} from 'jest-cucumber';
import { http, HttpResponse, delay } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { expect } from 'vitest';

import { computeMyTeam, type InSeasonView } from '../compute-my-team';
import MyTeamPage from '../my-team';

import type { MatchupItem, PlayerStat } from '@/components/api/types';
import {
  DEMO_LEAGUE_ID,
  DEMO_PLATFORM,
  DEMO_SEASONS,
} from '@/lib/demo-constants';
import { API, leagueQuery, leagueQueryError, server } from '@/test/msw/server';
import { renderRoute } from '@/test/render';

const feature = loadFeature('src/features/my_team/__tests__/my-team.feature');

const SEASON = '2025';

function player(id: number, pos: string, pts: number): PlayerStat {
  return {
    player_id: id,
    full_name: `P${id}`,
    points_scored: pts,
    position: pos,
    fantasy_position: pos,
  };
}

function game(
  week: number,
  aId: string,
  aScore: number,
  bId: string,
  bScore: number,
  opts: {
    season?: string;
    tier?: string;
    aOwner?: string;
    bOwner?: string;
    aStarters?: PlayerStat[];
    aBench?: PlayerStat[];
  } = {},
): MatchupItem {
  return {
    team_a_id: aId,
    team_a_display_name: `user${aId}`,
    team_a_team_name: `Team ${aId}`,
    team_a_team_logo: null,
    team_a_score: aScore,
    team_a_starters: opts.aStarters ?? [],
    team_a_bench: opts.aBench ?? [],
    team_a_primary_owner_id: opts.aOwner ?? `owner-${aId}`,
    team_a_secondary_owner_id: null,
    team_b_id: bId,
    team_b_display_name: `user${bId}`,
    team_b_team_name: `Team ${bId}`,
    team_b_team_logo: null,
    team_b_score: bScore,
    team_b_starters: [],
    team_b_bench: [],
    team_b_primary_owner_id: opts.bOwner ?? `owner-${bId}`,
    team_b_secondary_owner_id: null,
    playoff_tier_type: opts.tier ?? 'NONE',
    playoff_round: null,
    winner: aScore >= bScore ? aId : bId,
    loser: aScore >= bScore ? bId : aId,
    week: String(week),
    season: opts.season ?? SEASON,
  };
}

// Team 1: week 1 perfect lineup (35/35); week 2 benches an 18 for a 6 (28/40)
// → season 63/75 = 84%, 12.0 left on the bench last week.
function baseMatchups(): MatchupItem[] {
  return [
    game(1, '1', 120, '2', 100, {
      aStarters: [player(1, 'QB', 20), player(2, 'WR', 15)],
      aBench: [player(3, 'WR', 5)],
    }),
    game(1, '3', 90, '4', 110),
    game(2, '1', 128.4, '3', 112.9, {
      aStarters: [player(1, 'QB', 22), player(2, 'WR', 6)],
      aBench: [player(3, 'WR', 18)],
    }),
    game(2, '2', 95, '4', 105),
    game(3, '1', 0, '4', 0),
    game(3, '2', 0, '3', 0),
    game(4, '1', 0, '2', 0),
    game(4, '3', 0, '4', 0),
    game(3, '7', 131, '8', 104.2, {
      season: '2024',
      aOwner: 'old-1',
      bOwner: 'old-4',
    }),
    game(9, '8', 140, '7', 100, {
      season: '2024',
      aOwner: 'old-4',
      bOwner: 'old-1',
    }),
  ];
}

const MIGRATION = [
  {
    current_platform_owner_id: 'old-1',
    new_platform_owner_id: 'owner-1',
    display_name: 'user1',
  },
  {
    current_platform_owner_id: 'old-4',
    new_platform_owner_id: 'owner-4',
    display_name: 'user4',
  },
];

const SETTINGS = [
  {
    season: SEASON,
    num_playoff_teams: 2,
    num_playoff_teams_assumed: false,
    playoff_week_start: 5,
    regular_season_weeks: 4,
  },
];

const STANDINGS = [
  {
    season: SEASON,
    team_id: '1',
    owner_id: 'owner-1',
    team_name: 'Team 1',
    team_logo: null,
    owner_username: 'user1',
    final_rank: 1,
    games_played: 2,
    wins: 2,
    losses: 0,
    ties: 0,
    record: '2-0-0',
    total_pf: 248.4,
    avg_pf: 124.2,
    champion: 'Yes',
  },
];

const tile = (label: string) =>
  screen.getByText(label, { selector: 'span' }).parentElement!;

type StepFn = (...args: string[]) => unknown;
type Register = (matcher: string | RegExp, fn: StepFn) => void;

const steps = ({
  given,
  and,
  when,
  then,
}: Record<'given' | 'and' | 'when' | 'then', Register>) => {
  let matchups = baseMatchups();
  let claimed: string | null = null;
  let demo = false;
  const saved: string[] = [];
  let putStatus = 200;

  function handlers() {
    return [
      leagueQuery({
        MATCHUPS: matchups,
        SEASON_STANDINGS: STANDINGS,
        PLATFORM_MIGRATION: MIGRATION,
        LEAGUE_SETTINGS: SETTINGS,
      }),
      http.get(`${API}/leagues/:id/me`, () =>
        HttpResponse.json({ detail: 'ok', data: { owner_id: claimed } }),
      ),
      http.put(`${API}/leagues/:id/me`, async ({ request }) => {
        const body = (await request.json()) as { owner_id: string };
        if (putStatus !== 200) {
          return HttpResponse.json(
            { detail: 'Internal Server Error' },
            { status: putStatus },
          );
        }
        saved.push(body.owner_id);
        claimed = body.owner_id;
        return HttpResponse.json({ detail: 'ok', data: body });
      }),
    ];
  }

  async function openMyTeam() {
    await renderRoute(
      <Routes>
        <Route path="/my_team" element={<MyTeamPage />} />
      </Routes>,
      {
        route: '/my_team',
        demo,
        // Demo mode seeds the demo league into storage (setDemoCookies) in the app.
        league: demo
          ? {
              leagueId: DEMO_LEAGUE_ID,
              platform: DEMO_PLATFORM,
              seasons: DEMO_SEASONS,
            }
          : { leagueId: '100', platform: 'SLEEPER', seasons: ['2024', SEASON] },
      },
    );
  }

  async function pickAndSave(name: string) {
    fireEvent.click(
      await screen.findByRole('radio', { name: new RegExp(name) }),
    );
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Save my team' }));
      // Flush the save request's resolution inside act.
      await Promise.resolve();
    });
  }

  given('the league data is available', () => {
    server.use(...handlers());
  });
  and('I have not claimed a team', () => {
    claimed = null;
  });
  and(/^I have claimed owner "(.*)"$/, (owner) => {
    claimed = owner;
  });
  and('saving a claim fails', () => {
    putStatus = 500;
  });
  and('my team has a bye in Week 3', () => {
    matchups = matchups.filter((m) => !(m.week === '3' && m.team_a_id === '1'));
    server.use(...handlers());
  });
  and('no game of the season has been played', () => {
    matchups = matchups.map((m) =>
      m.season === SEASON ? { ...m, team_a_score: 0, team_b_score: 0 } : m,
    );
    server.use(...handlers());
  });
  and('every matchup of the season has been played', () => {
    matchups = matchups.filter((m) => m.season !== SEASON || m.week !== '4');
    matchups = matchups.map((m) =>
      m.season === SEASON && m.week === '3'
        ? { ...m, team_a_score: 110, team_b_score: 100 }
        : m,
    );
    server.use(...handlers());
  });
  and('the league data is slow to load', () => {
    server.use(
      http.get(`${API}/leagues/:id/query`, async () => {
        await delay('infinite');
        return HttpResponse.json({ data: [] });
      }),
    );
  });
  and('loading my claim fails', () => {
    server.use(
      http.get(`${API}/leagues/:id/me`, () =>
        HttpResponse.json({ detail: 'Internal Server Error' }, { status: 500 }),
      ),
    );
  });
  and('the league data fails to load', () => {
    server.use(leagueQueryError(500));
  });
  and('demo mode is active', () => {
    demo = true;
  });

  when('I open My Team', openMyTeam);
  when('I reopen My Team', async () => {
    cleanup();
    await openMyTeam();
  });
  and(/^I pick "(.*)" and save$/, pickAndSave);
  and(/^I choose "Change team"$/, async () => {
    fireEvent.click(await screen.findByRole('button', { name: 'Change team' }));
  });
  and("I pick the demo league's second team and save", () =>
    pickAndSave('Stat Hunters'),
  );
  and(/^I try to toggle "(.*)"$/, async (label) => {
    fireEvent.click(await screen.findByRole('switch', { name: label }));
  });

  then(
    /^I see the "Which team is yours\?" picker listing (\d+) teams$/,
    async (count) => {
      expect(
        await screen.findByRole('heading', { name: 'Which team is yours?' }),
      ).toBeInTheDocument();
      expect(screen.getAllByRole('radio')).toHaveLength(Number(count));
    },
  );
  and('I do not see the Your week card', () => {
    expect(screen.queryByRole('region', { name: 'Your week' })).toBeNull();
  });
  then(/^my claim for "(.*)" was saved$/, (owner) => {
    expect(saved.at(-1)).toBe(owner);
  });
  and('no claim was saved', () => {
    expect(saved).toEqual([]);
  });
  then(/^I see the Your week card for "(.*)"$/, async (name) => {
    const card = await screen.findByRole('region', { name: 'Your week' });
    expect(within(card).getAllByText(name).length).toBeGreaterThan(0);
  });
  then(
    /^I see the Your week card for the demo league's (first|second) team$/,
    async (which) => {
      const card = await screen.findByRole('region', { name: 'Your week' });
      const name = which === 'first' ? 'Gridiron Gurus' : 'Stat Hunters';
      expect(within(card).getAllByText(name).length).toBeGreaterThan(0);
    },
  );
  then(/^I see the error "(.*)"$/, async (message) => {
    expect(await screen.findByText(message)).toBeInTheDocument();
  });
  and(/^the picker is still shown with "(.*)" selected$/, (name) => {
    expect(
      screen.getByRole('radio', { name: new RegExp(name) }),
    ).toHaveAttribute('aria-checked', 'true');
  });
  then(/^the card heading reads "(.*)"$/, async (text) => {
    expect(
      await screen.findByRole('heading', { name: text }),
    ).toBeInTheDocument();
  });
  and(/^the "(.*)" tile shows "(.*)" and "(.*)"$/, (label, value, sub) => {
    const t = tile(label);
    expect(t.children[1]).toHaveTextContent(value);
    expect(t.children[2]).toHaveTextContent(sub);
  });
  and(/^the "(.*)" tile has no subtext$/, (label) => {
    // Label + value only; the optional subtext span is not rendered.
    expect(tile(label).children).toHaveLength(2);
  });
  and(/^the "(.*)" tile sub reads "(.*)"$/, (label, sub) => {
    expect(tile(label).children[2]).toHaveTextContent(sub);
  });
  and('the "Playoff odds" tile shows the predictor\'s odds and change', () => {
    const view = computeMyTeam(
      {
        matchups,
        standings: [],
        migrationMapping: new Map(
          MIGRATION.map((e) => [
            e.current_platform_owner_id,
            e.new_platform_owner_id,
          ]),
        ),
        settings: SETTINGS[0],
        season: SEASON,
      },
      'owner-1',
    ) as InSeasonView;
    const t = tile('Playoff odds');
    expect(t.children[1]).toHaveTextContent(
      `${Math.round(view.playoffOdds * 100)}%`,
    );
    const delta = Math.round(view.playoffOddsChange! * 100);
    expect(t.children[2]).toHaveTextContent(
      delta > 0
        ? `▲ ${delta} pts since last week`
        : delta < 0
          ? `▼ ${-delta} pts since last week`
          : 'No change since last week',
    );
  });
  and(/^the awards row reads "(.*)" and "(.*)"$/, (first, second) => {
    expect(screen.getByText(first)).toBeInTheDocument();
    expect(screen.getByText(second)).toBeInTheDocument();
  });
  then(/^the matchup panel shows "(.*)" as the opponent$/, async (name) => {
    const panel = await screen.findByLabelText("This week's matchup");
    expect(within(panel).getByText(name)).toBeInTheDocument();
  });
  and(/^the matchup panel shows "(.*)"$/, async (text) => {
    const panel =
      screen.queryByLabelText("This week's matchup") ??
      (await screen.findByText(text)).closest('div')!;
    expect(panel).toHaveTextContent(text);
  });
  and('the matchup panel links to the full preview on Matchups', () => {
    expect(
      screen.getByRole('link', { name: 'Open full preview →' }),
    ).toHaveAttribute('href', '/matchups');
  });
  and(/^the win probability is "(.*)"$/, (text) => {
    expect(screen.getByText(text)).toBeInTheDocument();
  });
  then(/^the "(.*)" switch is disabled and off$/, (label) => {
    const sw = screen.getByRole('switch', { name: label });
    expect(sw).toBeDisabled();
    expect(sw).toHaveAttribute('aria-checked', 'false');
  });
  and(/^"(.*)" is shown$/, (text) => {
    expect(screen.getByText(text)).toBeInTheDocument();
  });
  then('I see the loading skeleton', () => {
    expect(screen.getByLabelText('Loading My Team')).toBeInTheDocument();
  });
};

// Bind each scenario's steps to the shared definitions above. Unlike
// jest-cucumber's autoBindSteps, one definition may serve several steps of the same
// scenario (e.g. the repeated "tile shows" assertions). State is per scenario:
// the definitions are re-registered inside every test.
defineFeature(feature, (test) => {
  for (const scenario of feature.scenarios) {
    test(scenario.title, (fns) => {
      const registry: [string | RegExp, StepFn][] = [];
      const register: Register = (m, fn) => registry.push([m, fn]);
      steps({ given: register, and: register, when: register, then: register });
      for (const step of scenario.steps) {
        const def = registry.find(([m]) =>
          typeof m === 'string' ? m === step.stepText : m.test(step.stepText),
        );
        if (!def) throw new Error(`No step definition for "${step.stepText}"`);
        const keyword = step.keyword.trim().toLowerCase() as keyof typeof fns;
        (fns[keyword] as DefineStepFunction)(def[0], def[1]);
      }
    });
  }
});
