import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
} from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';

import { getLeagueSettings, getMatchups } from './api-calls';
import {
  buildPredictorModel,
  computePlayoffOdds,
  projectStandings,
  recordEnteringWeek,
  type PickableMatchup,
  type Picks,
  type PredictorMode,
  type PredictorModel,
} from './compute-projection';

import type {
  LeagueSettingsItem,
  MatchupItem,
  Platform,
} from '@/components/api/types';
import { TeamAvatar } from '@/components/team-avatar';
import { avatarColor } from '@/lib/color-constants';
import { type Result, toResult } from '@/lib/result';
import { cn } from '@/lib/utils';

const PREDICTOR_FALLBACK = 'Failed to load the playoff race data.';
export const PLAYOFF_EMPTY_MESSAGE =
  'No playoff bracket for this season yet. It will appear once the playoffs begin.';

interface PredictorData {
  matchups: MatchupItem[];
  settings: LeagueSettingsItem | null;
}

interface PredictorProps {
  leagueId: string;
  platform: Platform;
  season: string;
  mode: PredictorMode;
}

/**
 * The playoff-race predictor that replaces the empty playoff bracket for an
 * in-progress season (`live`), and drives the demo Bracket/Playoff-Race toggle
 * (`replay`). See {@link buildPredictorModel} for the two modes.
 */
export default function PlayoffRacePredictor({
  leagueId,
  platform,
  season,
  mode,
}: PredictorProps) {
  const dataPromise = useMemo(
    (): Promise<Result<PredictorData>> =>
      toResult(
        getMatchups(leagueId, platform, season).then(async (matchupsRes) => {
          // A league processed before LEAGUE_SETTINGS existed (or a settings
          // fetch error) leaves us without a configured cutoff; fall back to the
          // assumed default rather than failing the whole tool.
          const settings = await getLeagueSettings(leagueId, platform, season)
            .then((res) => res.data[0] ?? null)
            .catch(() => null);
          return { matchups: matchupsRes.data, settings };
        }),
        PREDICTOR_FALLBACK,
      ),
    [leagueId, platform, season],
  );

  return (
    <Suspense fallback={<PredictorLoading />}>
      <PredictorTool promise={dataPromise} mode={mode} />
    </Suspense>
  );
}

function PredictorLoading() {
  return (
    <div className="text-center py-12">
      <p className="text-muted-foreground">Loading playoff race...</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-12">
      <p className="text-muted-foreground">{PLAYOFF_EMPTY_MESSAGE}</p>
    </div>
  );
}

function PredictorTool({
  promise,
  mode,
}: {
  promise: Promise<Result<PredictorData>>;
  mode: PredictorMode;
}) {
  const result = use(promise);
  const [picks, setPicks] = useState<Picks>({});
  const [activeWeekIdx, setActiveWeekIdx] = useState(0);

  const model = useMemo(
    () =>
      result.ok
        ? buildPredictorModel(result.data.matchups, result.data.settings, mode)
        : null,
    [result, mode],
  );

  const colorByTeam = useMemo(() => {
    const map = new Map<string, string>();
    if (model) {
      [...model.teams.keys()].forEach((id, i) => map.set(id, avatarColor(i)));
    }
    return map;
  }, [model]);

  if (!result.ok) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">{result.error}</p>
      </div>
    );
  }

  // Self-gate: only show the live tool while the regular season is in progress.
  if (
    !model ||
    model.weeks.length === 0 ||
    (mode === 'live' && model.hasPlayedPlayoffMatchup)
  ) {
    return <EmptyState />;
  }

  const activeWeek =
    model.weeks[Math.min(activeWeekIdx, model.weeks.length - 1)];
  const pickCount = Object.keys(picks).length;

  const setPick = (matchup: PickableMatchup, teamId: string) => {
    setPicks((prev) => {
      const next = { ...prev };
      if (next[matchup.key] === teamId) delete next[matchup.key];
      else next[matchup.key] = teamId;
      return next;
    });
  };

  return (
    <div>
      <PredictorHeader canReset={pickCount > 0} onReset={() => setPicks({})} />

      <WeekStepper
        model={model}
        picks={picks}
        activeIdx={activeWeekIdx}
        onSelect={setActiveWeekIdx}
      />

      <div className="bg-card border border-border/50 rounded-lg overflow-hidden mb-5">
        <div className="p-3 flex flex-col gap-2">
          {activeWeek.matchups.map((m) => (
            <MatchupRow
              key={m.key}
              matchup={m}
              model={model}
              picks={picks}
              colorByTeam={colorByTeam}
              onPick={setPick}
            />
          ))}
        </div>
      </div>

      <StandingsTable model={model} picks={picks} colorByTeam={colorByTeam} />
    </div>
  );
}

function PredictorHeader({
  canReset,
  onReset,
}: {
  canReset: boolean;
  onReset: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">
          Playoff Picture
        </h2>
        <p className="text-[13px] text-muted-foreground mt-1 max-w-[62ch]">
          The bracket isn&apos;t set yet — the regular season is still in
          progress. Pick the winners of the remaining games to project who makes
          the playoffs.
        </p>
      </div>
      <button
        type="button"
        onClick={onReset}
        disabled={!canReset}
        className="inline-flex items-center gap-1.5 text-[13px] font-medium px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-muted disabled:opacity-45 disabled:hover:bg-card whitespace-nowrap cursor-pointer disabled:cursor-default"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        Reset picks
      </button>
    </div>
  );
}

function WeekStepper({
  model,
  picks,
  activeIdx,
  onSelect,
}: {
  model: PredictorModel;
  picks: Picks;
  activeIdx: number;
  onSelect: (idx: number) => void;
}) {
  const active = Math.min(activeIdx, model.weeks.length - 1);
  const pickedInWeek = (m: PickableMatchup[]) =>
    m.filter((mm) => picks[mm.key]).length;

  return (
    <div className="flex items-center gap-2 mb-4">
      <button
        type="button"
        aria-label="Previous week"
        disabled={active === 0}
        onClick={() => onSelect(active - 1)}
        className="w-8 h-8 rounded-lg border border-border bg-card grid place-items-center hover:bg-muted disabled:opacity-40 disabled:hover:bg-card cursor-pointer disabled:cursor-default"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <div className="flex gap-1.5 overflow-x-auto">
        {model.weeks.map((w, i) => {
          const done = pickedInWeek(w.matchups);
          const complete = done === w.matchups.length;
          return (
            <button
              key={w.week}
              type="button"
              onClick={() => onSelect(i)}
              className={cn(
                'flex flex-col items-center gap-0.5 min-w-[74px] px-3 py-1 rounded-lg border cursor-pointer',
                i === active
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-card hover:bg-muted',
              )}
            >
              <span
                className={cn(
                  'text-[13px] font-semibold',
                  i === active ? 'text-primary' : 'text-foreground',
                )}
              >
                Week {w.week}
              </span>
              <span className="text-[10px] text-muted-foreground inline-flex items-center gap-1">
                {complete && (
                  <Check className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" />
                )}
                {done}/{w.matchups.length}
              </span>
            </button>
          );
        })}
      </div>
      <button
        type="button"
        aria-label="Next week"
        disabled={active === model.weeks.length - 1}
        onClick={() => onSelect(active + 1)}
        className="w-8 h-8 rounded-lg border border-border bg-card grid place-items-center hover:bg-muted disabled:opacity-40 disabled:hover:bg-card cursor-pointer disabled:cursor-default"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}

function MatchupRow({
  matchup,
  model,
  picks,
  colorByTeam,
  onPick,
}: {
  matchup: PickableMatchup;
  model: PredictorModel;
  picks: Picks;
  colorByTeam: Map<string, string>;
  onPick: (m: PickableMatchup, teamId: string) => void;
}) {
  const pick = picks[matchup.key];
  return (
    <div className="grid grid-cols-[1fr_40px_1fr] items-stretch">
      <TeamCard
        teamId={matchup.teamAId}
        matchup={matchup}
        model={model}
        picks={picks}
        state={pick ? (pick === matchup.teamAId ? 'win' : 'lose') : 'none'}
        color={colorByTeam.get(matchup.teamAId) ?? avatarColor(0)}
        onPick={onPick}
      />
      <div className="grid place-items-center text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        vs
      </div>
      <TeamCard
        teamId={matchup.teamBId}
        matchup={matchup}
        model={model}
        picks={picks}
        state={pick ? (pick === matchup.teamBId ? 'win' : 'lose') : 'none'}
        color={colorByTeam.get(matchup.teamBId) ?? avatarColor(0)}
        onPick={onPick}
      />
    </div>
  );
}

function TeamCard({
  teamId,
  matchup,
  model,
  picks,
  state,
  color,
  onPick,
}: {
  teamId: string;
  matchup: PickableMatchup;
  model: PredictorModel;
  picks: Picks;
  state: 'win' | 'lose' | 'none';
  color: string;
  onPick: (m: PickableMatchup, teamId: string) => void;
}) {
  const team = model.teams.get(teamId)!;
  const rec = recordEnteringWeek(model, teamId, matchup.week, picks);
  return (
    <button
      type="button"
      onClick={() => onPick(matchup, teamId)}
      className={cn(
        'flex items-center gap-2.5 px-3.5 py-2.5 rounded-[10px] border w-full text-left transition-colors cursor-pointer',
        state === 'win' && 'border-primary bg-primary/10',
        state === 'lose' && 'opacity-50 border-border',
        state === 'none' && 'border-border bg-card hover:border-ring',
      )}
    >
      <TeamAvatar
        teamLogo={team.teamLogo}
        teamName={team.teamName}
        ownerUsername={team.ownerUsername}
        color={color}
      />
      <div className="flex flex-col min-w-0">
        <span className="text-[13px] font-medium truncate">
          {team.ownerUsername}
        </span>
        <span className="text-[11px] text-muted-foreground truncate">
          {team.teamName || `Team ${team.ownerUsername}`}
        </span>
      </div>
      <span className="ml-auto text-[12px] tabular-nums text-muted-foreground">
        {rec.wins}-{rec.losses}
        {rec.ties > 0 ? `-${rec.ties}` : ''}
      </span>
      {state === 'win' && <Check className="w-4 h-4 text-primary shrink-0" />}
    </button>
  );
}

function StandingsTable({
  model,
  picks,
  colorByTeam,
}: {
  model: PredictorModel;
  picks: Picks;
  colorByTeam: Map<string, string>;
}) {
  const rows = useMemo(() => projectStandings(model, picks), [model, picks]);

  // Playoff odds = share of remaining outcomes each team makes the top-N seed.
  const odds = useMemo(() => computePlayoffOdds(model, picks), [model, picks]);

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
          style={{ minWidth: '640px' }}
        >
          <thead>
            <tr>
              <th className="text-left text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted">
                Seed · Owner
              </th>
              <th className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted">
                Proj. record
              </th>
              <th className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted">
                Playoff odds
              </th>
              <th className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted">
                Win %
              </th>
              <th className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted">
                PF
              </th>
              <th className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2 border-b border-border/50 bg-muted">
                Games left
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <StandingRowView
                key={row.team.teamId}
                row={row}
                showLineAbove={i === model.numPlayoffTeams}
                color={colorByTeam.get(row.team.teamId) ?? avatarColor(i)}
                gamesLeft={gamesLeft.get(row.team.teamId) ?? 0}
                playoffOdds={odds.get(row.team.teamId) ?? null}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Format a 0..1 playoff-odds value: exact 0/100, `<1%`/`>99%` extremes, else integer %. */
function formatOdds(odds: number | null): string {
  if (odds === null) return '—';
  if (odds <= 0) return '0%';
  if (odds >= 1) return '100%';
  if (odds < 0.01) return '<1%';
  if (odds > 0.99) return '>99%';
  return `${Math.round(odds * 100)}%`;
}

function StandingRowView({
  row,
  showLineAbove,
  color,
  gamesLeft,
  playoffOdds,
}: {
  row: ReturnType<typeof projectStandings>[number];
  showLineAbove: boolean;
  color: string;
  gamesLeft: number;
  playoffOdds: number | null;
}) {
  return (
    <>
      {showLineAbove && (
        <tr>
          <td colSpan={6} className="p-0">
            <div className="flex items-center gap-2.5 px-3.5 py-1.5 border-y border-dashed border-primary">
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-primary whitespace-nowrap">
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
        <td className="px-3.5 py-2.5">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'w-5 text-right text-[12px] font-semibold',
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
            <div className="flex flex-col leading-tight min-w-0">
              <span className="text-[13px] font-medium inline-flex items-center gap-1.5">
                {row.team.ownerUsername}
                {row.clinched && (
                  <Check
                    className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400"
                    aria-label="Clinched a playoff spot"
                  />
                )}
              </span>
              <span className="text-[11px] text-muted-foreground truncate">
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
          {row.winPct.toFixed(3)}
        </td>
        <td className="px-3.5 py-2.5 text-right tabular-nums text-muted-foreground">
          {Math.round(row.pf)}
        </td>
        <td className="px-3.5 py-2.5 text-right tabular-nums text-muted-foreground">
          {gamesLeft}
        </td>
      </tr>
    </>
  );
}
