import { Clover, Info } from 'lucide-react';
import { Suspense, use, useMemo, useState, useCallback } from 'react';

import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import SeasonSelect from '@/features/season_select/season-select';
import {
  type SeasonRecapItem,
  type SeasonStandingsItem,
  getSeasonRecap,
  getSeasonStandings,
} from '@/features/season_standings/api-calls';

const AVATAR_COLORS = [
  '#4338ca',
  '#0f6e56',
  '#993c1d',
  '#993556',
  '#185FA5',
  '#854F0B',
  '#5F5E5A',
  '#A32D2D',
  '#7c3aed',
  '#b45309',
  '#0891b2',
  '#be185d',
];

function avatarColor(index: number): string {
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}

function TeamAvatar({
  teamLogo,
  teamName,
  ownerUsername,
  index,
}: {
  teamLogo: string | null | undefined;
  teamName: string;
  ownerUsername: string;
  index: number;
}) {
  const [imgError, setImgError] = useState(false);
  const handleError = useCallback(() => setImgError(true), []);

  return (
    <div
      className="w-7 h-7 rounded-full overflow-hidden shrink-0 flex items-center justify-center text-[11px] font-medium text-white"
      style={{ background: avatarColor(index) }}
    >
      {teamLogo && !imgError ? (
        <img
          src={teamLogo}
          alt={teamName}
          className="w-full h-full object-cover"
          onError={handleError}
        />
      ) : (
        initials(ownerUsername)
      )}
    </div>
  );
}

function initials(username: string): string {
  const parts = username
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .trim()
    .split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return username.slice(0, 2).toUpperCase();
}

type StandingsResult =
  | { ok: true; data: SeasonStandingsItem[] }
  | { ok: false; error: string };

function RecapBody({ promise }: { promise: Promise<SeasonRecapItem | null> }) {
  const result = use(promise);
  return (
    <p className="text-[13px] leading-[1.75] text-muted-foreground border-t border-border/50 pt-3">
      {result ? result.recap_text : 'Recap not yet available for this season.'}
    </p>
  );
}

function StandingsBody({ promise }: { promise: Promise<StandingsResult> }) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <tbody>
        <tr>
          <td
            colSpan={6}
            className="px-3.5 py-4 text-center text-[13px] text-destructive"
          >
            {result.error}
          </td>
        </tr>
      </tbody>
    );
  }

  const { data: standings } = result;

  return (
    <tbody>
      {standings.map((row, i) => {
        return (
          <tr
            key={row.team_id}
            className="border-b border-border/50 last:border-0 bg-card"
          >
            <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-muted-foreground w-4 text-right shrink-0">
                  {i + 1}
                </span>
                <TeamAvatar
                  teamLogo={row.team_logo}
                  teamName={row.team_name}
                  ownerUsername={row.owner_username}
                  index={i}
                />
                <div className="flex flex-col">
                  <span className="text-[13px] font-medium text-foreground font-mono">
                    {row.owner_username}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    {row.team_name}
                  </span>
                </div>
              </div>
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.record}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.avg_pf.toFixed(1)}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.avg_pa.toFixed(1)}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.win_pct.toFixed(3)}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.win_pct_vs_league.toFixed(3)}
            </td>
          </tr>
        );
      })}
    </tbody>
  );
}

function AwardsGrid({ promise }: { promise: Promise<StandingsResult> }) {
  const result = use(promise);
  if (!result.ok || result.data.length === 0) return null;

  const standings = result.data;

  const champion = standings.find((s) => s.champion === 'Yes') ?? null;
  const highScorer = standings.reduce((a, b) => (a.avg_pf > b.avg_pf ? a : b));
  const luckiest = standings.reduce((a, b) =>
    a.win_pct - a.win_pct_vs_league > b.win_pct - b.win_pct_vs_league ? a : b,
  );
  const luckDiff = luckiest.win_pct - luckiest.win_pct_vs_league;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      {/* Season Champion */}
      <div className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
            style={{ background: '#EEEDFE' }}
          >
            <svg
              className="w-4.5 h-4.5"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 2v14M8 20h8M6 2h12v8a6 6 0 01-12 0V2z"
                stroke="#534AB7"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M6 6H3a2 2 0 002 2h1M18 6h3a2 2 0 01-2 2h-1"
                stroke="#534AB7"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <span
            className="text-[11px] font-medium uppercase tracking-[0.07em]"
            style={{ color: '#534AB7' }}
          >
            Season Champion
          </span>
        </div>
        <div>
          {champion ? (
            <>
              <div className="text-[15px] font-medium text-foreground font-mono">
                {champion.owner_username}
              </div>
              <div className="text-[12px] text-muted-foreground">
                {champion.team_name}
              </div>
              <div
                className="text-[11px] font-medium mt-0.5"
                style={{ color: '#534AB7' }}
              >
                {champion.record} · {champion.win_pct.toFixed(3)} Win%
              </div>
            </>
          ) : (
            <>
              <div className="text-[15px] font-medium text-foreground font-mono">
                TBD
              </div>
              <div className="text-[12px] text-muted-foreground">
                Season in progress
              </div>
            </>
          )}
        </div>
      </div>

      {/* High Scorer */}
      <div className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
            style={{ background: '#FAEEDA' }}
          >
            <svg
              className="w-4.5 h-4.5"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"
                stroke="#BA7517"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            className="text-[11px] font-medium uppercase tracking-[0.07em]"
            style={{ color: '#BA7517' }}
          >
            High Scorer
          </span>
        </div>
        <div>
          <div className="text-[15px] font-medium text-foreground font-mono">
            {highScorer.owner_username}
          </div>
          <div className="text-[12px] text-muted-foreground">
            {highScorer.team_name}
          </div>
          <div
            className="text-[11px] font-medium mt-0.5"
            style={{ color: '#BA7517' }}
          >
            {highScorer.avg_pf.toFixed(1)} PF/Game
          </div>
        </div>
      </div>

      {/* Luckiest Team */}
      <div className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
            style={{ background: '#E1F5EE' }}
          >
            <Clover size={18} stroke="#0F6E56" strokeWidth={1.5} />
          </div>
          <span
            className="text-[11px] font-medium uppercase tracking-[0.07em]"
            style={{ color: '#0F6E56' }}
          >
            Luckiest Team
          </span>
        </div>
        <div>
          <div className="text-[15px] font-medium text-foreground font-mono">
            {luckiest.owner_username}
          </div>
          <div className="text-[12px] text-muted-foreground">
            {luckiest.team_name}
          </div>
          <div
            className="text-[11px] font-medium mt-0.5"
            style={{ color: '#0F6E56' }}
          >
            {luckDiff >= 0 ? '+' : ''}
            {luckDiff.toFixed(3)} vs. expected Win%
          </div>
        </div>
      </div>
    </div>
  );
}

function SkeletonAwards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5"
        >
          <div className="flex items-center gap-2.5">
            <Skeleton className="w-9 h-9 rounded-md shrink-0" />
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

function SkeletonBody() {
  return (
    <tbody>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i} className="border-b border-border/50">
          <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
            <div className="flex items-center gap-2">
              <Skeleton className="w-4 h-3 shrink-0" />
              <Skeleton className="w-7 h-7 rounded-full shrink-0" />
              <Skeleton className="h-3 w-28" />
            </div>
          </td>
          {Array.from({ length: 5 }).map((_, j) => (
            <td key={j} className="px-3.5 py-2.5 text-right">
              <Skeleton className="h-3 w-12 ml-auto" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

function getCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
}

export default function SeasonStandings() {
  const leagueId = getCookie('leagueId');
  const platform = (getCookie('leaguePlatform') || 'ESPN') as
    | 'ESPN'
    | 'SLEEPER';

  const seasons: string[] = useMemo(() => {
    try {
      return JSON.parse(
        decodeURIComponent(getCookie('leagueSeasons')),
      ) as string[];
    } catch {
      return [];
    }
  }, []);

  const defaultSeason =
    [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);

  const standingsPromise = useMemo(
    (): Promise<StandingsResult> =>
      leagueId && selectedSeason
        ? getSeasonStandings(leagueId, platform, selectedSeason)
            .then((res) => ({ ok: true as const, data: res.data }))
            .catch((err: unknown) => ({
              ok: false as const,
              error:
                err instanceof Error
                  ? err.message
                  : 'Failed to load standings.',
            }))
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason],
  );

  const recapPromise = useMemo(
    (): Promise<SeasonRecapItem | null> =>
      leagueId && selectedSeason
        ? getSeasonRecap(leagueId, platform, selectedSeason)
        : Promise.resolve(null),
    [leagueId, platform, selectedSeason],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground text-center mb-6">
          {selectedSeason} Season Standings
        </p>

        <Suspense fallback={<SkeletonAwards />}>
          <AwardsGrid promise={standingsPromise} />
        </Suspense>

        <div className="flex items-center justify-between mb-2.5">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            Season standings
          </p>
          {seasons.length > 0 && (
            <SeasonSelect
              seasons={seasons}
              value={selectedSeason}
              onValueChange={setSelectedSeason}
            />
          )}
        </div>

        <div className="bg-card border border-border/50 rounded-lg overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table
              className="w-full border-collapse text-[13px]"
              style={{ tableLayout: 'fixed', minWidth: '540px' }}
            >
              <thead>
                <tr>
                  <th
                    className="text-left text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted sticky left-0 z-10"
                    style={{ width: '48%' }}
                  >
                    Owner
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '15%' }}
                  >
                    Record
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '12%' }}
                  >
                    PF/Game
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '12%' }}
                  >
                    PA/Game
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '14%' }}
                  >
                    Win %
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '14%' }}
                  >
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="inline-flex items-center justify-end gap-1 cursor-default">
                            Win % vs. League
                            <Info className="w-3 h-3 shrink-0" />
                          </span>
                        </TooltipTrigger>
                        <TooltipContent
                          side="top"
                          className="max-w-64 text-center leading-relaxed bg-popover text-popover-foreground border border-border shadow-md [&>svg]:fill-popover [&>svg]:bg-popover"
                        >
                          This percentage measures a team&apos;s win percentage
                          if they played every team in the league each week
                          aggregated over the season (i.e., if a team was the
                          2nd highest scoring team in a 10 team league, their
                          win % vs. league for that week would be .900)
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </th>
                </tr>
              </thead>
              <Suspense fallback={<SkeletonBody />}>
                <StandingsBody promise={standingsPromise} />
              </Suspense>
            </table>
          </div>
        </div>

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Season recap
        </p>
        <div className="bg-card border border-border/50 rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[13px] font-medium text-foreground">
              Season summary
            </span>
            <span
              className="text-[10px] font-medium px-2 py-0.5 rounded-full"
              style={{ background: '#EEEDFE', color: '#3C3489' }}
            >
              LeagueQL AI
            </span>
          </div>
          <Suspense fallback={<Skeleton className="h-20 w-full mt-3" />}>
            <RecapBody promise={recapPromise} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
