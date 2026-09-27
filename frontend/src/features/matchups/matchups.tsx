import { Suspense, use, useEffect, useMemo, useRef, useState } from 'react';

import { BoxScoreCard, type BoxScoreSide } from '@/components/box-score-card';
import { TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  getSeasonMatchups,
  getSeasonWeeklyStandings,
  type MatchupItem,
  type PlayerStat,
  type WeeklyStandingItem,
} from '@/features/matchups/api-calls';
import { buildMatchupPreview } from '@/features/matchups/compute-preview';
import {
  MatchupPreviewCard,
  type PreviewSide,
} from '@/features/matchups/matchup-preview';
import SeasonSelect from '@/features/season_select/season-select';
import WeeklyAwards from '@/features/weekly_awards/weekly-awards';
import { avatarColor } from '@/lib/color-constants';
import { MATCHUP_STATUS_COLORS } from '@/lib/color-constants';
import { getLeagueCookies, type Platform } from '@/lib/cookie-handler';
import { type Result, toResult } from '@/lib/result';
import { latestSeason } from '@/lib/season';

interface TeamSide {
  teamId: string;
  teamName: string;
  teamLogo: string | null;
  ownerUsername: string;
  score: number;
  avatarColor: string;
  starters: PlayerStat[];
  bench: PlayerStat[];
  record: string | null;
}

interface ProcessedMatchup {
  teamA: TeamSide;
  teamB: TeamSide;
  week: number;
  playoffRound: string | null;
}

interface MatchupsData {
  weeks: number[];
  matchupsByWeek: Record<number, ProcessedMatchup[]>;
  /** The season's raw matchups, used to build a live-week matchup preview. */
  allMatchups: MatchupItem[];
}

/** A live (in-progress) matchup has no scores yet — both sides are exactly 0. */
function isLiveMatchup(m: ProcessedMatchup): boolean {
  return m.teamA.score === 0 && m.teamB.score === 0;
}

const toPreviewSide = (t: TeamSide): PreviewSide => ({
  teamId: t.teamId,
  teamName: t.teamName,
  ownerUsername: t.ownerUsername,
  teamLogo: t.teamLogo,
  color: t.avatarColor,
});

type MatchupsResult = Result<MatchupsData>;

function processData(
  matchups: MatchupItem[],
  standings: WeeklyStandingItem[],
): MatchupsData {
  const recordsByWeek: Record<number, Record<string, string>> = {};
  for (const s of standings) {
    const week = parseInt(s.snapshot_week, 10);
    if (isNaN(week)) continue;
    (recordsByWeek[week] ??= {})[s.team_id] = s.record;
  }
  const regularSeasonWeeks = Object.keys(recordsByWeek).map(Number);
  const lastRegularSeasonRecords =
    regularSeasonWeeks.length > 0
      ? recordsByWeek[Math.max(...regularSeasonWeeks)]
      : {};

  const uniqueTeams = new Map<string, string>();
  for (const m of matchups) {
    uniqueTeams.set(m.team_a_id, m.team_a_display_name ?? '');
    uniqueTeams.set(m.team_b_id, m.team_b_display_name ?? '');
  }
  const sortedTeamIds = [...uniqueTeams.entries()]
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([id]) => id);
  const colorMap = new Map(sortedTeamIds.map((id, i) => [id, avatarColor(i)]));

  const byWeek: Record<number, ProcessedMatchup[]> = {};

  for (const m of matchups) {
    const week = parseInt(m.week, 10);
    if (isNaN(week)) continue;
    const weekRecords = recordsByWeek[week] ?? lastRegularSeasonRecords;

    const pm: ProcessedMatchup = {
      teamA: {
        teamId: m.team_a_id,
        teamName: m.team_a_team_name || `Team ${m.team_a_display_name ?? ''}`,
        teamLogo: m.team_a_team_logo ?? null,
        ownerUsername: m.team_a_display_name ?? '',
        score: Number(m.team_a_score),
        avatarColor: colorMap.get(m.team_a_id) ?? avatarColor(0),
        starters: m.team_a_starters ?? [],
        bench: m.team_a_bench ?? [],
        record: weekRecords[m.team_a_id] ?? null,
      },
      teamB: {
        teamId: m.team_b_id,
        teamName: m.team_b_team_name || `Team ${m.team_b_display_name ?? ''}`,
        teamLogo: m.team_b_team_logo ?? null,
        ownerUsername: m.team_b_display_name ?? '',
        score: Number(m.team_b_score),
        avatarColor: colorMap.get(m.team_b_id) ?? avatarColor(1),
        starters: m.team_b_starters ?? [],
        bench: m.team_b_bench ?? [],
        record: weekRecords[m.team_b_id] ?? null,
      },
      week,
      playoffRound: m.playoff_round ?? null,
    };

    (byWeek[week] ??= []).push(pm);
  }

  for (const week of Object.keys(byWeek)) {
    byWeek[Number(week)].sort((a, b) => {
      const rank = (r: string | null) => {
        if (r === null) return 3;
        if (r === 'Losers Bracket') return 2;
        if (r === 'Winners Consolation') return 1;
        return 0;
      };
      return rank(a.playoffRound) - rank(b.playoffRound);
    });
  }

  const allWeeks = Object.keys(byWeek)
    .map(Number)
    .sort((a, b) => a - b);

  // An in-progress season persists its future/unplayed weeks as `0-0`
  // placeholder matchups (see isUnplayedMatchup). A week is "played" once any of
  // its matchups has a non-zero score. Show every played week plus the current
  // week — the earliest unplayed week — and hide the future placeholder weeks
  // beyond it. A completed season has no unplayed weeks, so all weeks show.
  const isWeekPlayed = (w: number) =>
    (byWeek[w] ?? []).some((m) => m.teamA.score !== 0 || m.teamB.score !== 0);
  const unplayedWeeks = allWeeks.filter((w) => !isWeekPlayed(w));
  const currentWeek =
    unplayedWeeks.length > 0 ? Math.min(...unplayedWeeks) : null;
  const weeks =
    currentWeek === null
      ? allWeeks
      : allWeeks.filter((w) => isWeekPlayed(w) || w === currentWeek);

  return { weeks, matchupsByWeek: byWeek, allMatchups: matchups };
}

function playoffBadgeColors(playoffRound: string): {
  background: string;
  color: string;
} {
  if (playoffRound === 'Losers Bracket') {
    return {
      background: MATCHUP_STATUS_COLORS.pending.bg,
      color: MATCHUP_STATUS_COLORS.pending.text,
    };
  }
  if (playoffRound === 'Winners Consolation') {
    return {
      background: MATCHUP_STATUS_COLORS.consolation.bg,
      color: MATCHUP_STATUS_COLORS.consolation.text,
    };
  }
  return {
    background: MATCHUP_STATUS_COLORS.completed.bg,
    color: MATCHUP_STATUS_COLORS.completed.text,
  };
}

function MatchupCard({
  matchup,
  isSelected,
  onClick,
}: {
  matchup: ProcessedMatchup;
  isSelected: boolean;
  onClick: () => void;
}) {
  const aWins = matchup.teamA.score > matchup.teamB.score;

  return (
    <div
      className={`bg-card rounded-lg overflow-hidden cursor-pointer transition-colors ${
        isSelected
          ? 'border-2 border-primary'
          : 'border border-border/50 hover:border-border'
      }`}
      onClick={onClick}
    >
      <div className="px-3.5 pt-2.5 pb-0 flex items-center justify-between">
        <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
          Week {matchup.week}
        </span>
        {matchup.playoffRound !== null && (
          <span
            className="text-[10px] font-medium px-2 py-0.5 rounded-full"
            style={playoffBadgeColors(matchup.playoffRound)}
          >
            {matchup.playoffRound}
          </span>
        )}
      </div>
      <div className="p-3.5 pt-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TeamAvatar
              teamLogo={matchup.teamA.teamLogo}
              teamName={matchup.teamA.teamName}
              ownerUsername={matchup.teamA.ownerUsername}
              color={matchup.teamA.avatarColor}
            />
            <div>
              <div className="text-[13px] font-medium text-foreground">
                {matchup.teamA.ownerUsername}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {matchup.teamA.teamName}
                {matchup.teamA.record ? ` (${matchup.teamA.record})` : ''}
              </div>
            </div>
          </div>
          <span
            className={`text-[26px] font-medium tabular-nums ${
              aWins ? 'text-foreground' : 'text-muted-foreground'
            }`}
          >
            {matchup.teamA.score.toFixed(2)}
          </span>
        </div>

        <div className="h-px bg-border/50 my-2.5" />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TeamAvatar
              teamLogo={matchup.teamB.teamLogo}
              teamName={matchup.teamB.teamName}
              ownerUsername={matchup.teamB.ownerUsername}
              color={matchup.teamB.avatarColor}
            />
            <div>
              <div className="text-[13px] font-medium text-foreground">
                {matchup.teamB.ownerUsername}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {matchup.teamB.teamName}
                {matchup.teamB.record ? ` (${matchup.teamB.record})` : ''}
              </div>
            </div>
          </div>
          <span
            className={`text-[26px] font-medium tabular-nums ${
              !aWins ? 'text-foreground' : 'text-muted-foreground'
            }`}
          >
            {matchup.teamB.score.toFixed(2)}
          </span>
        </div>

        <div className="mt-2.5 flex justify-end">
          <span className="text-[11px] font-medium text-primary">
            {isLiveMatchup(matchup)
              ? 'View matchup preview →'
              : 'View box score →'}
          </span>
        </div>
      </div>
    </div>
  );
}

function BoxScoreView({
  matchup,
  onClose,
  platform,
  season,
}: {
  matchup: ProcessedMatchup;
  onClose: () => void;
  platform: Platform;
  season: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const aWins = matchup.teamA.score > matchup.teamB.score;
  const left: BoxScoreSide = {
    teamLogo: matchup.teamA.teamLogo,
    teamName: matchup.teamA.teamName,
    ownerUsername: matchup.teamA.ownerUsername,
    color: matchup.teamA.avatarColor,
    score: matchup.teamA.score,
    starters: matchup.teamA.starters,
    bench: matchup.teamA.bench,
    isWinner: aWins,
  };
  const right: BoxScoreSide = {
    teamLogo: matchup.teamB.teamLogo,
    teamName: matchup.teamB.teamName,
    ownerUsername: matchup.teamB.ownerUsername,
    color: matchup.teamB.avatarColor,
    score: matchup.teamB.score,
    starters: matchup.teamB.starters,
    bench: matchup.teamB.bench,
    isWinner: !aWins,
  };
  return (
    <div className="mt-8" ref={ref}>
      <BoxScoreCard
        left={left}
        right={right}
        platform={platform}
        season={season}
        onClose={onClose}
      />
    </div>
  );
}

function SkeletonMatchupsContent() {
  return (
    <div>
      <div className="flex gap-1.5 flex-wrap mb-6">
        {Array.from({ length: 13 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-13 rounded-md" />
        ))}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="bg-card border border-border/50 rounded-lg p-3.5"
          >
            <Skeleton className="h-2.5 w-12 mb-3" />
            {[0, 1].map((j) => (
              <div key={j}>
                {j === 1 && <div className="h-px bg-border/50 my-2.5" />}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Skeleton className="w-8 h-8 rounded-full shrink-0" />
                    <div>
                      <Skeleton className="h-3 w-20 mb-1" />
                      <Skeleton className="h-2.5 w-14" />
                    </div>
                  </div>
                  <Skeleton className="h-6 w-14" />
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function MatchupsContent({
  promise,
  selectedWeek,
  onWeekChange,
  selectedMatchup,
  onMatchupSelect,
  platform,
  season,
}: {
  promise: Promise<MatchupsResult>;
  selectedWeek: number | null;
  onWeekChange: (week: number) => void;
  selectedMatchup: number | null;
  onMatchupSelect: (idx: number | null) => void;
  platform: Platform;
  season: string;
}) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <div className="text-center py-8 text-[13px] text-destructive">
        {result.error}
      </div>
    );
  }

  const { weeks, matchupsByWeek, allMatchups } = result.data;
  const latestWeek = weeks[weeks.length - 1] ?? 1;
  const activeWeek = selectedWeek ?? latestWeek;
  const currentMatchups = matchupsByWeek[activeWeek] ?? [];
  const activeMatchup =
    selectedMatchup !== null
      ? (currentMatchups[selectedMatchup] ?? null)
      : null;
  const activeIsLive = activeMatchup !== null && isLiveMatchup(activeMatchup);

  return (
    <div>
      {/* Week buttons */}
      <div className="flex gap-1.5 flex-wrap mb-6">
        {weeks.map((w) => (
          <button
            key={w}
            className={`px-2.5 py-1.5 text-[12px] font-medium border rounded-md cursor-pointer transition-colors ${
              w === activeWeek
                ? 'bg-primary border-primary text-primary-foreground'
                : 'bg-card border-border/50 text-muted-foreground hover:border-border'
            }`}
            onClick={() => onWeekChange(w)}
          >
            Wk {w}
          </button>
        ))}
      </div>

      {/* Matchup grid */}
      {currentMatchups.length === 0 ? (
        <div className="text-center py-8 text-[13px] text-muted-foreground">
          No matchups found for week {activeWeek}.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {currentMatchups.map((m, i) => (
            <MatchupCard
              key={i}
              matchup={m}
              isSelected={selectedMatchup === i}
              onClick={() => onMatchupSelect(selectedMatchup === i ? null : i)}
            />
          ))}
        </div>
      )}

      {/* Live-week matchups open a preview; played matchups open the box score. */}
      {activeMatchup !== null &&
        (activeIsLive ? (
          <MatchupPreviewView
            key={selectedMatchup}
            matchup={activeMatchup}
            matchups={allMatchups}
            onClose={() => onMatchupSelect(null)}
          />
        ) : (
          <BoxScoreView
            key={selectedMatchup}
            matchup={activeMatchup}
            onClose={() => onMatchupSelect(null)}
            platform={platform}
            season={season}
          />
        ))}
    </div>
  );
}

function MatchupPreviewView({
  matchup,
  matchups,
  onClose,
}: {
  matchup: ProcessedMatchup;
  matchups: MatchupItem[];
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const data = useMemo(
    () =>
      buildMatchupPreview(matchups, matchup.teamA.teamId, matchup.teamB.teamId),
    [matchups, matchup.teamA.teamId, matchup.teamB.teamId],
  );

  return (
    <div className="mt-8" ref={ref}>
      <MatchupPreviewCard
        left={toPreviewSide(matchup.teamA)}
        right={toPreviewSide(matchup.teamB)}
        data={data}
        onClose={onClose}
      />
    </div>
  );
}

export default function Matchups() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const [selectedSeason, setSelectedSeason] = useState(latestSeason(seasons));
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const [selectedMatchup, setSelectedMatchup] = useState<number | null>(null);

  const matchupsPromise = useMemo(
    (): Promise<MatchupsResult> =>
      leagueId && selectedSeason
        ? toResult(
            Promise.all([
              getSeasonMatchups(leagueId, platform, selectedSeason),
              getSeasonWeeklyStandings(leagueId, platform, selectedSeason),
            ]).then(([matchupsRes, standingsRes]) =>
              processData(matchupsRes.data, standingsRes.data),
            ),
            'Failed to load matchups.',
          )
        : Promise.resolve({
            ok: true as const,
            data: { weeks: [], matchupsByWeek: {}, allMatchups: [] },
          }),
    [leagueId, platform, selectedSeason],
  );

  function handleSeasonChange(season: string) {
    setSelectedSeason(season);
    setSelectedWeek(null);
    setSelectedMatchup(null);
  }

  function handleWeekChange(week: number) {
    setSelectedWeek(week);
    setSelectedMatchup(null);
  }

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        {seasons.length > 0 && (
          <div className="mb-4">
            <SeasonSelect
              seasons={seasons}
              value={selectedSeason}
              onValueChange={handleSeasonChange}
            />
          </div>
        )}

        <Suspense fallback={<SkeletonMatchupsContent />}>
          <MatchupsContent
            promise={matchupsPromise}
            selectedWeek={selectedWeek}
            onWeekChange={handleWeekChange}
            selectedMatchup={selectedMatchup}
            onMatchupSelect={setSelectedMatchup}
            platform={platform}
            season={selectedSeason}
          />
        </Suspense>

        {/* Weekly awards is a free section (frontend/weekly-awards) and always renders. */}
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mt-8 mb-2.5">
          Weekly awards &amp; superlatives
        </p>
        <WeeklyAwards
          leagueId={leagueId}
          platform={platform}
          season={selectedSeason}
          selectedWeek={selectedWeek}
        />
      </div>
    </div>
  );
}
