import { Fragment, Suspense, use, useEffect, useMemo, useRef, useState } from 'react';

import { BoxScoreCard, type BoxScoreSide } from '@/components/box-score-card';
import { avatarColor } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { getLeagueCookies } from '@/lib/cookie-handler';
import {
  getAllSeasonsMatchups,
  type MatchupItem,
} from '@/features/manager_comparison/api-calls';

interface Manager {
  name: string;
  team: string;
  color: string;
  init: string;
  ownerId: string;
  stats: {
    wins: number;
    losses: number;
    ties: number;
    avgPf: number;
    highScore: number;
    winPct: number;
    h2hWins: number;
    longestStreak: number;
  };
}

interface GameLog {
  week: string;
  season: string;
  lp: number;
  rp: number;
  matchupItem: MatchupItem;
  leftIsA: boolean;
}

interface StatDef {
  key: string;
  label: string;
  value: (m: Manager) => number;
  fmt: (m: Manager) => string;
  higher: boolean;
}

const STAT_DEFS: StatDef[] = [
  {
    key: 'h2hWins',
    label: 'H2H Wins',
    value: (m) => m.stats.h2hWins,
    fmt: (m) => String(m.stats.h2hWins),
    higher: true,
  },
  {
    key: 'longestStreak',
    label: 'Longest Streak',
    value: (m) => m.stats.longestStreak,
    fmt: (m) => String(m.stats.longestStreak),
    higher: true,
  },
  {
    key: 'record',
    label: 'Overall Record',
    value: (m) => m.stats.winPct,
    fmt: (m) => `${m.stats.wins}-${m.stats.losses}-${m.stats.ties}`,
    higher: true,
  },
  {
    key: 'winPct',
    label: 'Win %',
    value: (m) => m.stats.winPct,
    fmt: (m) =>
      '.' +
      Math.round(m.stats.winPct * 1000)
        .toString()
        .padStart(3, '0'),
    higher: true,
  },
  {
    key: 'avgPf',
    label: 'Avg PF',
    value: (m) => m.stats.avgPf,
    fmt: (m) => m.stats.avgPf.toFixed(1),
    higher: true,
  },
  {
    key: 'highScore',
    label: 'High Score',
    value: (m) => m.stats.highScore,
    fmt: (m) => m.stats.highScore.toFixed(1),
    higher: true,
  },
];

function pct(a: number, b: number): number {
  const total = a + b;
  return total === 0 ? 50 : Math.round((a / total) * 100);
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

function longestWinStreak(games: GameLog[], side: 'left' | 'right'): number {
  let best = 0;
  let current = 0;
  for (const g of games) {
    const won = side === 'left' ? g.lp > g.rp : g.rp > g.lp;
    if (won) {
      current++;
      if (current > best) best = current;
    } else {
      current = 0;
    }
  }
  return best;
}

function buildManagers(matchups: MatchupItem[]): Manager[] {
  const ownerMap = new Map<
    string,
    {
      name: string;
      team: string;
      scores: number[];
      wins: number;
      losses: number;
      ties: number;
    }
  >();

  for (const m of matchups) {
    for (const side of ['a', 'b'] as const) {
      const ownerId = m[`team_${side}_primary_owner_id`];
      const displayName = m[`team_${side}_display_name`];
      const teamName = m[`team_${side}_team_name`];
      const score = Number(m[`team_${side}_score`]);

      if (!ownerMap.has(ownerId)) {
        ownerMap.set(ownerId, {
          name: displayName,
          team: teamName,
          scores: [],
          wins: 0,
          losses: 0,
          ties: 0,
        });
      }

      const entry = ownerMap.get(ownerId)!;
      entry.team = teamName;
      entry.scores.push(score);

      const otherSide = side === 'a' ? 'b' : 'a';
      const otherScore = Number(m[`team_${otherSide}_score`]);
      if (score > otherScore) entry.wins++;
      else if (score < otherScore) entry.losses++;
      else entry.ties++;
    }
  }

  const sortedIds = [...ownerMap.keys()].sort((a, b) =>
    ownerMap.get(a)!.name.localeCompare(ownerMap.get(b)!.name),
  );

  return sortedIds.map((ownerId, i) => {
    const entry = ownerMap.get(ownerId)!;
    const scores = entry.scores;
    const avgPf =
      scores.length > 0 ? scores.reduce((s, x) => s + x, 0) / scores.length : 0;
    const highScore = scores.length > 0 ? Math.max(...scores) : 0;
    return {
      ownerId,
      name: entry.name,
      team: entry.team,
      color: avatarColor(i),
      init: initials(entry.name),
      stats: {
        wins: entry.wins,
        losses: entry.losses,
        ties: entry.ties,
        winPct:
          entry.wins + entry.losses + entry.ties > 0
            ? entry.wins / (entry.wins + entry.losses + entry.ties)
            : 0,
        avgPf,
        highScore,
        h2hWins: 0,
        longestStreak: 0,
      },
    };
  });
}

function buildGameLogs(
  matchups: MatchupItem[],
  leftOwnerId: string,
  rightOwnerId: string,
): GameLog[] {
  const logs: GameLog[] = [];
  for (const m of matchups) {
    const aOwner = m.team_a_primary_owner_id;
    const bOwner = m.team_b_primary_owner_id;

    if (
      (aOwner === leftOwnerId && bOwner === rightOwnerId) ||
      (aOwner === rightOwnerId && bOwner === leftOwnerId)
    ) {
      const leftIsA = aOwner === leftOwnerId;
      logs.push({
        week: `Week ${m.week}`,
        season: m.season,
        lp: leftIsA ? Number(m.team_a_score) : Number(m.team_b_score),
        rp: leftIsA ? Number(m.team_b_score) : Number(m.team_a_score),
        matchupItem: m,
        leftIsA,
      });
    }
  }
  logs.sort((a, b) => {
    const seasonDiff = Number(a.season) - Number(b.season);
    if (seasonDiff !== 0) return seasonDiff;
    return (
      parseInt(a.week.replace('Week ', ''), 10) -
      parseInt(b.week.replace('Week ', ''), 10)
    );
  });
  return logs;
}

function MgrAvatar({ color, init }: { color: string; init: string }) {
  return (
    <div
      className="w-14 h-14 rounded-full flex items-center justify-center text-[17px] font-medium text-white shrink-0"
      style={{ background: color }}
    >
      {init}
    </div>
  );
}

function GameLogPanel({
  left,
  right,
  games,
  selectedIdx,
  onGameSelect,
}: {
  left: Manager;
  right: Manager;
  games: GameLog[];
  selectedIdx: number | null;
  onGameSelect: (idx: number | null) => void;
}) {
  return (
    <div className="absolute inset-0 bg-card border border-border/50 rounded-lg overflow-hidden flex flex-col">
      <div className="px-3.5 py-2.5 border-b border-border/50 bg-muted shrink-0">
        <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-muted-foreground">
          Game Log
        </span>
      </div>

      <div className="overflow-y-auto flex-1 min-h-0">
        {games.length === 0 ? (
          <div className="px-3.5 py-6 text-center text-[13px] text-muted-foreground">
            No matchups played yet.
          </div>
        ) : (
          games.map((g, idx) => {
            const lWin = g.lp > g.rp;
            const isSelected = selectedIdx === idx;
            return (
              <div
                key={idx}
                className={`px-3.5 py-2.5 border-b border-border/50 last:border-0 flex flex-col gap-1.5 cursor-pointer transition-colors ${isSelected ? 'bg-muted' : 'hover:bg-muted/50'}`}
                onClick={() => onGameSelect(isSelected ? null : idx)}
              >
                <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                  {g.season} — {g.week}
                </span>
                <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-1.5">
                  <div className="flex items-center gap-1.5">
                    <div
                      className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[9px] font-medium text-white shrink-0"
                      style={{ background: left.color }}
                    >
                      {left.init}
                    </div>
                    <div>
                      <div className="text-[11px] font-medium text-foreground">
                        {left.name}
                      </div>
                      <div
                        className="text-[14px] font-medium"
                        style={{ color: lWin ? left.color : undefined }}
                      >
                        {g.lp.toFixed(1)}
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] text-muted-foreground text-center">
                    vs
                  </span>
                  <div className="flex items-center gap-1.5 flex-row-reverse">
                    <div
                      className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[9px] font-medium text-white shrink-0"
                      style={{ background: right.color }}
                    >
                      {right.init}
                    </div>
                    <div className="text-right">
                      <div className="text-[11px] font-medium text-foreground">
                        {right.name}
                      </div>
                      <div
                        className="text-[14px] font-medium"
                        style={{ color: !lWin ? right.color : undefined }}
                      >
                        {g.rp.toFixed(1)}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-0.75">
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full ml-auto"
                      style={{
                        width: `${pct(g.lp, g.rp)}%`,
                        background: lWin ? left.color : 'var(--color-border)',
                      }}
                    />
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct(g.rp, g.lp)}%`,
                        background: !lWin ? right.color : 'var(--color-border)',
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function ManagerBoxScoreView({
  game,
  left,
  right,
  platform,
  onClose,
}: {
  game: GameLog;
  left: Manager;
  right: Manager;
  platform: 'ESPN' | 'SLEEPER';
  onClose: () => void;
}) {
  const m = game.matchupItem;
  const lWins = game.lp > game.rp;
  const leftSide: BoxScoreSide = {
    teamLogo: game.leftIsA ? m.team_a_team_logo : m.team_b_team_logo,
    teamName: game.leftIsA ? m.team_a_team_name : m.team_b_team_name,
    ownerUsername: left.name,
    color: left.color,
    score: game.lp,
    starters: game.leftIsA ? m.team_a_starters : m.team_b_starters,
    bench: game.leftIsA ? m.team_a_bench : m.team_b_bench,
    isWinner: lWins,
  };
  const rightSide: BoxScoreSide = {
    teamLogo: game.leftIsA ? m.team_b_team_logo : m.team_a_team_logo,
    teamName: game.leftIsA ? m.team_b_team_name : m.team_a_team_name,
    ownerUsername: right.name,
    color: right.color,
    score: game.rp,
    starters: game.leftIsA ? m.team_b_starters : m.team_a_starters,
    bench: game.leftIsA ? m.team_b_bench : m.team_a_bench,
    isWinner: !lWins,
  };
  return (
    <div className="mt-4">
      <BoxScoreCard
        left={leftSide}
        right={rightSide}
        subtitle={`${game.season} — ${game.week} · Final`}
        platform={platform}
        season={game.season}
        onClose={onClose}
      />
    </div>
  );
}

function ManagerComparisonInner({
  matchupsPromise,
  platform,
}: {
  matchupsPromise: Promise<MatchupItem[]>;
  platform: 'ESPN' | 'SLEEPER';
}) {
  const matchups = use(matchupsPromise);
  const managers = useMemo(() => buildManagers(matchups), [matchups]);

  const [li, setLi] = useState(0);
  const [ri, setRi] = useState(Math.min(1, managers.length - 1));
  const [selectedGameIdx, setSelectedGameIdx] = useState<number | null>(null);
  const boxScoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedGameIdx !== null) {
      boxScoreRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [selectedGameIdx]);

  function handleLeftChange(val: number) {
    if (val === ri) setRi(li);
    setLi(val);
    setSelectedGameIdx(null);
  }

  function handleRightChange(val: number) {
    if (val === li) setLi(ri);
    setRi(val);
    setSelectedGameIdx(null);
  }

  const L = managers[li];
  const R = managers[ri];
  const games = useMemo(
    () => (L && R ? buildGameLogs(matchups, L.ownerId, R.ownerId) : []),
    [matchups, L, R],
  );

  if (managers.length < 2 || !L || !R) {
    return (
      <div className="flex flex-1 items-center justify-center text-[13px] text-muted-foreground">
        Not enough manager data to compare.
      </div>
    );
  }

  const lH2hWins = games.filter((g) => g.lp > g.rp).length;
  const rH2hWins = games.filter((g) => g.rp > g.lp).length;
  const lLongestStreak = longestWinStreak(games, 'left');
  const rLongestStreak = longestWinStreak(games, 'right');
  const LWithH2H = {
    ...L,
    stats: { ...L.stats, h2hWins: lH2hWins, longestStreak: lLongestStreak },
  };
  const RWithH2H = {
    ...R,
    stats: { ...R.stats, h2hWins: rH2hWins, longestStreak: rLongestStreak },
  };

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-275 mx-auto w-full">
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,275px)] gap-4 items-stretch">
          <div className="flex flex-col gap-3">
            {/* Manager selectors */}
            <div className="grid grid-cols-[1fr_56px_1fr] items-center">
              <select
                className="w-full px-3 py-2 text-[14px] font-medium bg-card border border-border/50 rounded-md text-foreground appearance-none cursor-pointer focus:outline-none"
                value={li}
                onChange={(e) => handleLeftChange(Number(e.target.value))}
              >
                {managers.map((m, i) => (
                  <option key={m.ownerId} value={i}>
                    {m.name}
                  </option>
                ))}
              </select>
              <div className="w-8.5 h-8.5 rounded-full bg-muted border border-border/50 flex items-center justify-center text-[11px] font-medium text-muted-foreground mx-auto">
                vs
              </div>
              <select
                className="w-full px-3 py-2 text-[14px] font-medium bg-card border border-border/50 rounded-md text-foreground appearance-none cursor-pointer focus:outline-none"
                value={ri}
                onChange={(e) => handleRightChange(Number(e.target.value))}
              >
                {managers.map((m, i) => (
                  <option key={m.ownerId} value={i}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Comparison grid — flat so each row naturally aligns across all 3 columns */}
            <div className="grid grid-cols-[1fr_110px_1fr]">
              {/* Header row: avatars + names */}
              <div className="flex flex-col items-center gap-1.5 pb-4.5 pt-2.5">
                <MgrAvatar color={LWithH2H.color} init={LWithH2H.init} />
                <span className="text-[13px] font-medium text-foreground text-center">
                  {LWithH2H.team}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {LWithH2H.name}
                </span>
              </div>
              <div />
              <div className="flex flex-col items-center gap-1.5 pb-4.5 pt-2.5">
                <MgrAvatar color={RWithH2H.color} init={RWithH2H.init} />
                <span className="text-[13px] font-medium text-foreground text-center">
                  {RWithH2H.team}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {RWithH2H.name}
                </span>
              </div>

              {/* Stat rows */}
              {STAT_DEFS.map((s) => {
                const lVal = s.value(LWithH2H);
                const rVal = s.value(RWithH2H);
                const lWin = s.higher ? lVal >= rVal : lVal <= rVal;
                const rWin = s.higher ? rVal >= lVal : rVal <= lVal;
                const lP = pct(lVal, rVal);
                const rP = pct(rVal, lVal);
                return (
                  <Fragment key={s.key}>
                    <div className="h-13 flex flex-col justify-center gap-1.25 px-2 text-left">
                      <span
                        className="text-[15px] font-medium"
                        style={{ color: lWin ? LWithH2H.color : undefined }}
                      >
                        {s.fmt(LWithH2H)}
                      </span>
                      <div className="h-2 rounded-full bg-muted overflow-hidden w-full">
                        <div
                          className="h-full rounded-full ml-auto"
                          style={{
                            width: `${lP}%`,
                            background: lWin
                              ? LWithH2H.color
                              : 'var(--color-border)',
                          }}
                        />
                      </div>
                    </div>
                    <div className="h-13 flex items-center justify-center text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground text-center">
                      {s.label}
                    </div>
                    <div className="h-13 flex flex-col justify-center gap-1.25 px-2 text-right">
                      <span
                        className="text-[15px] font-medium"
                        style={{ color: rWin ? RWithH2H.color : undefined }}
                      >
                        {s.fmt(RWithH2H)}
                      </span>
                      <div className="h-2 rounded-full bg-muted overflow-hidden w-full">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${rP}%`,
                            background: rWin
                              ? RWithH2H.color
                              : 'var(--color-border)',
                          }}
                        />
                      </div>
                    </div>
                  </Fragment>
                );
              })}
            </div>
          </div>

          <div className="relative">
            <GameLogPanel
              left={L}
              right={R}
              games={games}
              selectedIdx={selectedGameIdx}
              onGameSelect={setSelectedGameIdx}
            />
          </div>
        </div>

        {selectedGameIdx !== null && games[selectedGameIdx] && (
          <>
            <div className="mt-6 mb-2 border-t border-border/50" />
            <div ref={boxScoreRef}>
              <ManagerBoxScoreView
                game={games[selectedGameIdx]}
                left={LWithH2H}
                right={RWithH2H}
                platform={platform}
                onClose={() => setSelectedGameIdx(null)}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ManagerComparisonSkeleton() {
  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-275 mx-auto w-full">
        <Skeleton className="h-4 w-48 mx-auto mb-5" />
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,275px)] gap-4 items-start">
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-[1fr_56px_1fr] items-center gap-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="w-8.5 h-8.5 rounded-full mx-auto" />
              <Skeleton className="h-9 w-full" />
            </div>
            <div className="grid grid-cols-[1fr_110px_1fr] gap-2">
              {[0, 1].map((i) => (
                <div key={i} className="flex flex-col gap-3 pt-2">
                  <Skeleton className="w-14 h-14 rounded-full mx-auto" />
                  <Skeleton className="h-3 w-24 mx-auto" />
                  {[0, 1, 2, 3, 4, 5, 6].map((j) => (
                    <Skeleton key={j} className="h-13 w-full" />
                  ))}
                </div>
              ))}
            </div>
          </div>
          <Skeleton className="h-111 w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export default function ManagerComparison() {
  const { leagueId, platform } = getLeagueCookies();
  const matchupsPromise = useMemo(
    () =>
      leagueId ? getAllSeasonsMatchups(leagueId, platform) : Promise.resolve([] as MatchupItem[]),
    [leagueId, platform],
  );

  return (
    <Suspense fallback={<ManagerComparisonSkeleton />}>
      <ManagerComparisonInner
        matchupsPromise={matchupsPromise}
        platform={platform}
      />
    </Suspense>
  );
}
