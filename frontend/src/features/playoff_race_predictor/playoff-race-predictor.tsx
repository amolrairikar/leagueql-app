import { Suspense, use, useMemo, useState } from 'react';

import { getLeagueSettings, getMatchups } from './api-calls';
import {
  buildPredictorModel,
  computeSeedProbabilities,
  type PickableMatchup,
  type Picks,
  type PredictorMode,
} from './compute-projection';

import type {
  LeagueSettingsItem,
  MatchupItem,
  Platform,
} from '@/components/api/types';
import { ClinchScenarios } from '@/features/playoff_race_predictor/clinch-scenarios';
import { PLAYOFF_EMPTY_MESSAGE } from '@/features/playoff_race_predictor/constants';
import { MatchupRow } from '@/features/playoff_race_predictor/matchup-picker';
import {
  PredictorHeader,
  WeekStepper,
} from '@/features/playoff_race_predictor/predictor-header';
import { StandingsTable } from '@/features/playoff_race_predictor/standings-table';
import { avatarColor } from '@/lib/color-constants';
import { type Result, toResult } from '@/lib/result';

const PREDICTOR_FALLBACK = 'Failed to load the playoff race data.';
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

  // Per-team seed distribution over the remaining outcomes, enumerated once and
  // shared by the standings odds column and the seed-probability table below.
  const seedProbs = useMemo(
    () => (model ? computeSeedProbabilities(model, picks) : null),
    [model, picks],
  );

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

      {/* On narrow screens, long owner/team names can exceed the viewport, so
          the card scrolls horizontally instead of clipping them. Sizing the
          rows at max-content (never narrower than the card) makes each row's
          1fr tracks resolve equally to the widest team card, so every team
          card stays the same width on mobile as on desktop. */}
      <div
        className="bg-card border border-border/50 rounded-lg overflow-x-auto mb-5"
        data-testid="predictor-matchups"
      >
        <div className="p-3 flex w-max min-w-full flex-col gap-2">
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

      <StandingsTable
        model={model}
        picks={picks}
        colorByTeam={colorByTeam}
        seedProbs={seedProbs!}
      />

      <ClinchScenarios model={model} picks={picks} colorByTeam={colorByTeam} />
    </div>
  );
}
