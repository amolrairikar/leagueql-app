import { Suspense, use, useEffect, useMemo, useRef, useState } from 'react';

import {
  getPlayoffBracket,
  getMatchups,
  getWeeklyStandings,
} from './api-calls';

import type { Platform } from '@/components/api/types';
import { BracketGrid } from '@/features/playoff_bracket/bracket-grid';
import {
  buildWildcardRoundItems,
  findMatchupForBracketMatch,
} from '@/features/playoff_bracket/bracket-layout';
import {
  BracketLoading,
  DemoBracketToggle,
} from '@/features/playoff_bracket/bracket-parts';
import {
  processBracketData,
  type BracketResult,
} from '@/features/playoff_bracket/process-bracket';
import { SelectedMatchBoxScore } from '@/features/playoff_bracket/selected-match-box-score';
import PlayoffRacePredictor from '@/features/playoff_race_predictor/playoff-race-predictor';
import SeasonSelect from '@/features/season_select/season-select';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';
import { toResult } from '@/lib/result';
import { latestSeason } from '@/lib/season';

const PLAYOFF_FALLBACK = 'Failed to load playoff bracket data.';
const NO_LEAGUE_MESSAGE = 'No league selected. Please connect a league first.';
const PLAYOFF_EMPTY_MESSAGE =
  'No playoff bracket for this season yet. It will appear once the playoffs begin.';

export default function PlayoffBracket() {
  const {
    leagueId,
    platform,
    seasons: allSeasons,
  } = useMemo(() => getLeagueCookies(), []);

  const [selectedSeason, setSelectedSeason] = useState(() =>
    allSeasons.length > 0 ? allSeasons[allSeasons.length - 1] : '2025',
  );
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);

  // Only the most recent season can still be in progress (playoffs not yet
  // decided); any earlier season is complete.
  const mostRecentSeason = useMemo(
    () => latestSeason(allSeasons),
    [allSeasons],
  );

  const bracketPromise = useMemo(
    (): Promise<BracketResult> =>
      leagueId
        ? toResult(
            Promise.all([
              getPlayoffBracket(leagueId, platform, selectedSeason),
              getMatchups(leagueId, platform, selectedSeason),
              getWeeklyStandings(leagueId, platform, selectedSeason),
            ]).then(([bracketRes, matchupsRes, standingsRes]) =>
              processBracketData(
                bracketRes.data,
                matchupsRes.data,
                standingsRes.data,
                selectedSeason,
              ),
            ),
            PLAYOFF_FALLBACK,
          )
        : Promise.resolve({ ok: false as const, error: NO_LEAGUE_MESSAGE }),
    [leagueId, platform, selectedSeason],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-262.5 mx-auto w-full">
        {allSeasons.length > 0 && (
          <div className="mb-7">
            <SeasonSelect
              seasons={allSeasons}
              value={selectedSeason}
              onValueChange={setSelectedSeason}
            />
          </div>
        )}

        <Suspense fallback={<BracketLoading />}>
          <BracketContent
            promise={bracketPromise}
            platform={platform}
            leagueId={leagueId}
            season={selectedSeason}
            isLatestSeason={selectedSeason === mostRecentSeason}
            selectedMatchId={selectedMatchId}
            onSelectMatch={setSelectedMatchId}
          />
        </Suspense>
      </div>
    </div>
  );
}

function BracketContent({
  promise,
  platform,
  leagueId,
  season,
  isLatestSeason,
  selectedMatchId,
  onSelectMatch,
}: {
  promise: Promise<BracketResult>;
  platform: Platform;
  leagueId: string;
  season: string;
  isLatestSeason: boolean;
  selectedMatchId: number | null;
  onSelectMatch: (id: number | null) => void;
}) {
  const result = use(promise);
  const boxScoreRef = useRef<HTMLDivElement>(null);
  const [demoView, setDemoView] = useState<'bracket' | 'predictor'>('bracket');

  useEffect(() => {
    if (selectedMatchId !== null) {
      boxScoreRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  }, [selectedMatchId]);

  if (!result.ok) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">{result.error}</p>
      </div>
    );
  }

  const { matches, matchups, recordMap, championshipWeek, maxRound } =
    result.data;

  // A bracket with no decided result and no final placement is a seeded-but-
  // unplayed "null bracket" (e.g. an early-season Sleeper league where only
  // round-1 matchups carry concrete teams, so the processor drops the null-team
  // championship/later rounds). It has no championship or semifinals to draw, so
  // treat it the same as an empty bracket rather than rendering blank columns.
  const hasRenderableBracket = matches.some(
    (m) => m.winner !== null || m.position !== null,
  );

  if (!hasRenderableBracket) {
    // While the latest season's regular season is still in progress there is no
    // bracket yet — offer the interactive predictor instead of a dead empty state.
    // The predictor self-gates (renders the empty message if the season isn't
    // actually in progress).
    if (isLatestSeason) {
      return (
        <PlayoffRacePredictor
          leagueId={leagueId}
          platform={platform}
          season={season}
          mode="live"
        />
      );
    }
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">{PLAYOFF_EMPTY_MESSAGE}</p>
      </div>
    );
  }

  const championship = matches.find((m) => m.position === 1);
  const semifinals = matches.filter(
    (m) => m.round === maxRound - 1 && m.position === null,
  );
  const wildcard =
    maxRound >= 3
      ? matches.filter((m) => m.round === maxRound - 2 && m.position === null)
      : [];
  // Pair bye teams with their corresponding wildcard matchups
  const wildcardRoundItems = buildWildcardRoundItems(semifinals, wildcard);

  // Helper function to find the corresponding matchup data for a selected bracket match

  // Get the selected matchup data
  const selectedMatch =
    selectedMatchId !== null
      ? matches.find((m) => m.match_id === selectedMatchId)
      : null;
  const selectedMatchupData = selectedMatch
    ? findMatchupForBracketMatch(
        matchups,
        championshipWeek,
        maxRound,
        selectedMatch,
      )
    : null;

  // Demo mode only: a toggle lets visitors explore the predictor over a completed
  // season (replaying its final regular-season weeks) alongside the real bracket.
  const demo = isDemoMode();
  if (demo && demoView === 'predictor') {
    return (
      <>
        <DemoBracketToggle value={demoView} onChange={setDemoView} />
        <PlayoffRacePredictor
          leagueId={leagueId}
          platform={platform}
          season={season}
          mode="replay"
        />
      </>
    );
  }

  return (
    <>
      {demo && <DemoBracketToggle value={demoView} onChange={setDemoView} />}
      <BracketGrid
        maxRound={maxRound}
        wildcardRoundItems={wildcardRoundItems}
        semifinals={semifinals}
        championship={championship}
        recordMap={recordMap}
        selectedMatchId={selectedMatchId}
        onSelectMatch={onSelectMatch}
      />

      {selectedMatchupData && selectedMatch && (
        <>
          <div className="mt-6 mb-2 border-t border-border/50" />
          <div ref={boxScoreRef}>
            <SelectedMatchBoxScore
              selectedMatch={selectedMatch}
              selectedMatchupData={selectedMatchupData}
              platform={platform}
              onClose={() => onSelectMatch(null)}
            />
          </div>
        </>
      )}
    </>
  );
}
