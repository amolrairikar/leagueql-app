import {
  Fragment,
  Suspense,
  use,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  getComparisonData,
  type ComparisonData,
} from '@/features/manager_comparison/api-calls';
import {
  buildGameLogs,
  buildManagers,
  longestWinStreak,
} from '@/features/manager_comparison/build-data';
import {
  GameLogPanel,
  ManagerBoxScoreView,
  MgrAvatar,
} from '@/features/manager_comparison/game-log-panel';
import { ManagerComparisonSkeleton } from '@/features/manager_comparison/skeleton';
import { STAT_DEFS } from '@/features/manager_comparison/stat-defs';
import { getLeagueCookies, type Platform } from '@/lib/cookie-handler';
import { pct } from '@/lib/utils';

function ManagerComparisonInner({
  matchupsPromise,
  platform,
}: {
  matchupsPromise: Promise<ComparisonData>;
  platform: Platform;
}) {
  const { matchups, standings, migrationMapping } = use(matchupsPromise);
  const managers = useMemo(
    () => buildManagers(matchups, standings, migrationMapping),
    [matchups, standings, migrationMapping],
  );

  const [li, setLi] = useState(0);
  const [ri, setRi] = useState(Math.min(1, managers.length - 1));
  const [selectedGameIdx, setSelectedGameIdx] = useState<number | null>(null);
  const boxScoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedGameIdx !== null) {
      boxScoreRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
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
    () =>
      L && R
        ? buildGameLogs(matchups, L.ownerId, R.ownerId, migrationMapping)
        : [],
    [matchups, L, R, migrationMapping],
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
        <div className="grid grid-cols-[minmax(0,1fr)] sm:grid-cols-[minmax(0,1fr)_minmax(0,275px)] gap-4 items-stretch">
          <div className="flex flex-col gap-3 min-w-0">
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

            {/* Comparison grid — flat so each row naturally aligns across all 3 columns.
                Sized to its content (w-max) so both 1fr manager columns resolve to the
                wider one's width — a long username never squeezes the other side — and
                scrolls horizontally when that doesn't fit (e.g. on mobile). */}
            <div className="overflow-x-auto">
              <div className="grid grid-cols-[1fr_110px_1fr] w-max min-w-full">
                {/* Header row: avatars + names */}
                <div className="flex flex-col items-center gap-1.5 pb-4.5 pt-2.5">
                  <MgrAvatar color={LWithH2H.color} init={LWithH2H.init} />
                  <span className="text-[13px] font-medium text-foreground text-center">
                    {LWithH2H.name}
                  </span>
                </div>
                <div />
                <div className="flex flex-col items-center gap-1.5 pb-4.5 pt-2.5">
                  <MgrAvatar color={RWithH2H.color} init={RWithH2H.init} />
                  <span className="text-[13px] font-medium text-foreground text-center">
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
          </div>

          <div className="relative h-96 sm:h-auto">
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

export default function ManagerComparison() {
  const { leagueId, platform } = getLeagueCookies();
  const matchupsPromise = useMemo(
    () =>
      leagueId
        ? getComparisonData(leagueId, platform)
        : Promise.resolve<ComparisonData>({
            matchups: [],
            standings: [],
            migrationMapping: new Map<string, string>(),
          }),
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
