import { Suspense, use, useMemo } from 'react';

import { Skeleton } from '@/components/ui/skeleton';
import {
  type SeasonStandingsItem,
  getSeasonStandings,
} from '@/features/home/api-calls';

const SEASON = '2025';

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

function initials(ownerId: string): string {
  const parts = ownerId
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .trim()
    .split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return ownerId.slice(0, 2).toUpperCase();
}

type StandingsResult =
  | { ok: true; data: SeasonStandingsItem[] }
  | { ok: false; error: string };

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
  const playoffCutoff = Math.ceil(standings.length / 2);

  return (
    <tbody>
      {standings.flatMap((row, i) => {
        const inPlayoffs = i < playoffCutoff;
        const rows = [];

        if (i === playoffCutoff) {
          rows.push(
            <tr key="playoff-cutoff">
              <td colSpan={6} className="p-0">
                <div className="flex items-center gap-2 px-3.5 py-1.5 bg-muted border-b border-border/50">
                  <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                    Playoff cutoff
                  </span>
                </div>
              </td>
            </tr>,
          );
        }

        rows.push(
          <tr
            key={row.team_id}
            className={`border-b border-border/50 last:border-0 ${inPlayoffs ? 'bg-card' : 'bg-muted/30'}`}
          >
            <td className="px-3.5 py-2.5">
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-muted-foreground w-4 text-right shrink-0">
                  {i + 1}
                </span>
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-medium text-white shrink-0"
                  style={{ background: avatarColor(i) }}
                >
                  {initials(row.owner_id)}
                </div>
                <div className="flex flex-col">
                  <span className="text-[13px] font-medium text-foreground font-mono">
                    {row.owner_id}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Team {row.team_id}
                  </span>
                </div>
              </div>
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.record}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.total_pf.toLocaleString(undefined, {
                maximumFractionDigits: 1,
              })}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.avg_pf.toFixed(1)}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {(row.win_pct * 100).toFixed(1)}%
            </td>
            <td className="px-3.5 py-2.5 text-right">
              {inPlayoffs ? (
                <span
                  className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                  style={{ background: '#EEEDFE', color: '#3C3489' }}
                >
                  Playoffs
                </span>
              ) : (
                <span
                  className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                  style={{ background: '#F1EFE8', color: '#444441' }}
                >
                  Eliminated
                </span>
              )}
            </td>
          </tr>,
        );

        return rows;
      })}
    </tbody>
  );
}

function SkeletonBody() {
  return (
    <tbody>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i} className="border-b border-border/50">
          <td className="px-3.5 py-2.5">
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

export default function Home() {
  const leagueId = getCookie('leagueId');
  const platform = (getCookie('leaguePlatform') || 'ESPN') as
    | 'ESPN'
    | 'SLEEPER';

  const standingsPromise = useMemo(
    (): Promise<StandingsResult> =>
      leagueId
        ? getSeasonStandings(leagueId, platform, SEASON)
            .then((res) => ({ ok: true as const, data: res.data }))
            .catch((err: unknown) => ({
              ok: false as const,
              error:
                err instanceof Error
                  ? err.message
                  : 'Failed to load standings.',
            }))
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground text-center mb-6">
          LeagueQL — {SEASON} Season Standings
        </p>

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Season standings
        </p>

        <div className="bg-card border border-border/50 rounded-lg overflow-hidden mb-6">
          <table
            className="w-full border-collapse text-[13px]"
            style={{ tableLayout: 'fixed' }}
          >
            <thead>
              <tr>
                <th
                  className="text-left text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '36%' }}
                >
                  Owner
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '12%' }}
                >
                  W-L-T
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '12%' }}
                >
                  Pts
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '12%' }}
                >
                  Avg
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
                  Status
                </th>
              </tr>
            </thead>
            <Suspense fallback={<SkeletonBody />}>
              <StandingsBody promise={standingsPromise} />
            </Suspense>
          </table>
        </div>
      </div>
    </div>
  );
}
