import { ArrowDown, ArrowUp, Check, Info } from 'lucide-react';
import { useMemo } from 'react';

import {
  projectStandings,
  type Picks,
  type PredictorModel,
} from './compute-projection';

import { TeamAvatar } from '@/components/team-avatar';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { PLAYOFF_ODDS_TOOLTIP } from '@/features/playoff_race_predictor/constants';
import { formatOdds } from '@/features/playoff_race_predictor/odds';
import { avatarColor } from '@/lib/color-constants';
import { cn } from '@/lib/utils';

export function StandingsTable({
  model,
  picks,
  colorByTeam,
  seedProbs,
}: {
  model: PredictorModel;
  picks: Picks;
  colorByTeam: Map<string, string>;
  seedProbs: Map<string, number[]>;
}) {
  const rows = useMemo(() => projectStandings(model, picks), [model, picks]);

  // Playoff odds = share of remaining outcomes each team makes the top-N seed,
  // i.e. the sum of its top-numPlayoffTeams seed probabilities.
  const odds = useMemo(() => {
    const map = new Map<string, number>();
    for (const [id, dist] of seedProbs) {
      let sum = 0;
      for (let k = 0; k < model.numPlayoffTeams && k < dist.length; k++) {
        sum += dist[k];
      }
      map.set(id, sum);
    }
    return map;
  }, [seedProbs, model.numPlayoffTeams]);

  // Games left = pickable matchups still involving each team.
  const gamesLeft = useMemo(() => {
    const counts = new Map<string, number>();
    for (const w of model.weeks) {
      for (const m of w.matchups) {
        if (picks[m.key]) continue;
        counts.set(m.teamAId, (counts.get(m.teamAId) ?? 0) + 1);
        counts.set(m.teamBId, (counts.get(m.teamBId) ?? 0) + 1);
      }
    }
    return counts;
  }, [model, picks]);

  const seeds = Array.from({ length: model.numPlayoffTeams }, (_, i) => i + 1);
  const metaHeadClass =
    'text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted';
  const minWidth = 560 + seeds.length * 52;

  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 pt-3.5 pb-2.5">
        <span className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          Projected standings
        </span>
        <span className="text-[11px] text-muted-foreground">
          Top {model.numPlayoffTeams} make the playoffs
          {model.numPlayoffTeamsAssumed && ' (assumed)'}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse text-[13px]"
          style={{ minWidth: `${minWidth}px` }}
        >
          <thead>
            <tr>
              <th
                rowSpan={2}
                className="text-left text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted align-bottom sticky left-0 z-10 w-67 sm:w-auto"
              >
                Seed · Owner
              </th>
              <th rowSpan={2} className={cn(metaHeadClass, 'align-bottom')}>
                Proj. record
              </th>
              <th rowSpan={2} className={cn(metaHeadClass, 'align-bottom')}>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="inline-flex items-center gap-1 cursor-default">
                        Playoff odds
                        <Info className="w-3 h-3 shrink-0" />
                      </span>
                    </TooltipTrigger>
                    <TooltipContent
                      side="top"
                      className="max-w-64 text-center leading-relaxed normal-case tracking-normal font-normal bg-popover text-popover-foreground border border-border shadow-md [&>svg]:fill-popover [&>svg]:bg-popover"
                    >
                      {PLAYOFF_ODDS_TOOLTIP}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </th>
              <th rowSpan={2} className={cn(metaHeadClass, 'align-bottom')}>
                PF
              </th>
              <th rowSpan={2} className={cn(metaHeadClass, 'align-bottom')}>
                Games left
              </th>
              <th
                colSpan={seeds.length}
                className="text-center text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 border-l border-dashed border-primary/40 bg-muted"
              >
                Seed odds
              </th>
            </tr>
            <tr>
              {seeds.map((s) => (
                <th
                  key={s}
                  className={cn(
                    metaHeadClass,
                    s === 1 && 'border-l border-dashed border-primary/40',
                  )}
                >
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <StandingRowView
                key={row.team.teamId}
                row={row}
                numPlayoffTeams={model.numPlayoffTeams}
                showLineAbove={i === model.numPlayoffTeams}
                color={colorByTeam.get(row.team.teamId) ?? avatarColor(i)}
                gamesLeft={gamesLeft.get(row.team.teamId) ?? 0}
                playoffOdds={odds.get(row.team.teamId) ?? null}
                dist={seedProbs.get(row.team.teamId) ?? null}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StandingRowView({
  row,
  numPlayoffTeams,
  showLineAbove,
  color,
  gamesLeft,
  playoffOdds,
  dist,
}: {
  row: ReturnType<typeof projectStandings>[number];
  numPlayoffTeams: number;
  showLineAbove: boolean;
  color: string;
  gamesLeft: number;
  playoffOdds: number | null;
  dist: number[] | null;
}) {
  // One cell per playoff seed; emphasize the team's single most-likely seed.
  const seedValues = Array.from(
    { length: numPlayoffTeams },
    (_, k) => dist?.[k] ?? 0,
  );
  let modal = 0;
  for (let k = 1; k < seedValues.length; k++) {
    if (seedValues[k] > seedValues[modal]) modal = k;
  }

  return (
    <>
      {showLineAbove && (
        <tr>
          <td colSpan={5 + numPlayoffTeams} className="p-0">
            <div className="flex items-center gap-2.5 px-3.5 py-1.5 border-y border-dashed border-primary">
              {/* Pinned like the frozen Seed · Owner column so the label stays
                  in view when the table scrolls horizontally. */}
              <span className="sticky left-3.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-primary whitespace-nowrap">
                Playoff line
              </span>
              <span className="flex-1 h-px bg-primary/35" />
            </div>
          </td>
        </tr>
      )}
      <tr
        className={cn(
          'border-b border-border/50',
          row.inPlayoffs && 'bg-primary/10',
        )}
      >
        {/* Frozen when the table scrolls horizontally. A sticky cell needs an
            opaque background, so playoff rows layer the row's translucent tint
            over bg-card instead of letting scrolled cells show through. */}
        <td
          className={cn(
            'px-3.5 py-2.5 sticky left-0 z-10 bg-card w-67 sm:w-auto',
            row.inPlayoffs && 'bg-linear-to-r from-primary/10 to-primary/10',
          )}
        >
          {/* On mobile the frozen column is a fixed w-67 (268px, matching
              Season Standings' 38%-of-720px owner column) and long names wrap,
              so it can't crowd out the scrolling columns. A max-width here
              alone isn't enough: auto table layout hands the table's spare
              width to this column too. Natural width from sm up. */}
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'w-5 shrink-0 text-right text-[12px] font-semibold',
                row.inPlayoffs ? 'text-primary' : 'text-muted-foreground',
              )}
            >
              {row.seed}
            </span>
            <TeamAvatar
              teamLogo={row.team.teamLogo}
              teamName={row.team.teamName}
              ownerUsername={row.team.ownerUsername}
              color={color}
            />
            <div className="flex flex-col leading-tight min-w-0 [overflow-wrap:anywhere]">
              <span className="text-[13px] font-medium inline-flex items-center gap-1.5">
                {row.team.ownerUsername}
                {row.clinched && (
                  <Check
                    className="w-3.5 h-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                    aria-label="Clinched a playoff spot"
                  />
                )}
              </span>
              <span className="text-[11px] text-muted-foreground sm:truncate">
                {row.team.teamName || `Team ${row.team.ownerUsername}`}
              </span>
            </div>
          </div>
        </td>
        <td className="px-3.5 py-2.5 text-right">
          <span className="font-medium text-foreground">
            {row.wins}-{row.losses}
            {row.ties > 0 ? `-${row.ties}` : ''}
          </span>
          {row.movement !== 0 && (
            <span
              className={cn(
                'inline-flex items-center gap-0.5 text-[10.5px] ml-1.5',
                row.movement > 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-destructive',
              )}
            >
              {row.movement > 0 ? (
                <ArrowUp className="w-2.5 h-2.5" />
              ) : (
                <ArrowDown className="w-2.5 h-2.5" />
              )}
              {Math.abs(row.movement)}
            </span>
          )}
        </td>
        <td className="px-3.5 py-2.5 text-right tabular-nums">
          <span
            className={cn(
              'font-medium',
              playoffOdds !== null && playoffOdds >= 0.99
                ? 'text-emerald-600 dark:text-emerald-400'
                : playoffOdds !== null && playoffOdds <= 0.01
                  ? 'text-muted-foreground'
                  : 'text-foreground',
            )}
          >
            {formatOdds(playoffOdds)}
          </span>
        </td>
        <td className="px-3.5 py-2.5 text-right tabular-nums text-muted-foreground">
          {row.pf.toFixed(2)}
        </td>
        <td className="px-3.5 py-2.5 text-right tabular-nums text-muted-foreground">
          {gamesLeft}
        </td>
        {seedValues.map((value, k) => (
          <td
            key={k}
            className={cn(
              'px-3.5 py-2.5 text-right tabular-nums',
              k === 0 && 'border-l border-dashed border-primary/40',
              modal === k
                ? 'font-semibold text-foreground'
                : value < 0.01
                  ? 'text-muted-foreground/60'
                  : 'text-muted-foreground',
            )}
          >
            {formatOdds(value)}
          </td>
        ))}
      </tr>
    </>
  );
}
