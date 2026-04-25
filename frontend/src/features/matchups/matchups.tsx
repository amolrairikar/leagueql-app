import { Suspense, use, useEffect, useMemo, useRef, useState } from 'react';

import { BoxScoreCard, type BoxScoreSide } from '@/components/box-score-card';
import { avatarColor, TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  getSeasonMatchups,
  type MatchupItem,
  type PlayerStat,
} from '@/features/matchups/api-calls';
import SeasonSelect from '@/features/season_select/season-select';

interface TeamSide {
  teamId: string;
  teamName: string;
  teamLogo: string | null;
  ownerUsername: string;
  score: number;
  avatarColor: string;
  starters: PlayerStat[];
  bench: PlayerStat[];
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
}

type MatchupsResult =
  | { ok: true; data: MatchupsData }
  | { ok: false; error: string };

function processData(matchups: MatchupItem[]): MatchupsData {
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

    const pm: ProcessedMatchup = {
      teamA: {
        teamId: m.team_a_id,
        teamName: m.team_a_team_name ?? '',
        teamLogo: m.team_a_team_logo ?? null,
        ownerUsername: m.team_a_display_name ?? '',
        score: Number(m.team_a_score),
        avatarColor: colorMap.get(m.team_a_id) ?? avatarColor(0),
        starters: m.team_a_starters ?? [],
        bench: m.team_a_bench ?? [],
      },
      teamB: {
        teamId: m.team_b_id,
        teamName: m.team_b_team_name ?? '',
        teamLogo: m.team_b_team_logo ?? null,
        ownerUsername: m.team_b_display_name ?? '',
        score: Number(m.team_b_score),
        avatarColor: colorMap.get(m.team_b_id) ?? avatarColor(1),
        starters: m.team_b_starters ?? [],
        bench: m.team_b_bench ?? [],
      },
      week,
      playoffRound: m.playoff_round ?? null,
    };

    (byWeek[week] ??= []).push(pm);
  }

  for (const week of Object.keys(byWeek)) {
    byWeek[Number(week)].sort((a, b) => {
      const rank = (r: string | null) =>
        r === null || r === 'Losers Bracket' ? 1 : 0;
      return rank(a.playoffRound) - rank(b.playoffRound);
    });
  }

  const weeks = Object.keys(byWeek)
    .map(Number)
    .sort((a, b) => a - b);

  return { weeks, matchupsByWeek: byWeek };
}

function getCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
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
          ? 'border-2 border-[#4338ca]'
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
            style={
              matchup.playoffRound === 'Losers Bracket'
                ? { background: '#f1f5f9', color: '#64748b' }
                : { background: '#fef3c7', color: '#92400e' }
            }
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
          <span className="text-[11px] font-medium text-[#4338ca]">
            View box score →
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
  platform: 'ESPN' | 'SLEEPER';
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
        subtitle={`Week ${matchup.week} · Final`}
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
      <div className="grid grid-cols-2 gap-3">
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
  platform: 'ESPN' | 'SLEEPER';
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

  const { weeks, matchupsByWeek } = result.data;
  const latestWeek = weeks[weeks.length - 1] ?? 1;
  const activeWeek = selectedWeek ?? latestWeek;
  const currentMatchups = matchupsByWeek[activeWeek] ?? [];
  const activeMatchup =
    selectedMatchup !== null
      ? (currentMatchups[selectedMatchup] ?? null)
      : null;

  return (
    <div>
      {/* Week buttons */}
      <div className="flex gap-1.5 flex-wrap mb-6">
        {weeks.map((w) => (
          <button
            key={w}
            className={`px-2.5 py-1.5 text-[12px] font-medium border rounded-md cursor-pointer transition-colors ${
              w === activeWeek
                ? 'bg-[#4338ca] border-[#4338ca] text-white'
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
        <div className="grid grid-cols-2 gap-3">
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

      {/* Box score */}
      {activeMatchup !== null && (
        <BoxScoreView
          key={selectedMatchup}
          matchup={activeMatchup}
          onClose={() => onMatchupSelect(null)}
          platform={platform}
          season={season}
        />
      )}
    </div>
  );
}

export default function Matchups() {
  const leagueId = getCookie('leagueId');
  const platform = (getCookie('leaguePlatform') || 'ESPN') as
    | 'ESPN'
    | 'SLEEPER';

  const seasons = useMemo(() => {
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
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const [selectedMatchup, setSelectedMatchup] = useState<number | null>(null);

  const matchupsPromise = useMemo(
    (): Promise<MatchupsResult> =>
      leagueId && selectedSeason
        ? getSeasonMatchups(leagueId, platform, selectedSeason)
            .then((res) => ({
              ok: true as const,
              data: processData(res.data),
            }))
            .catch((err) => ({
              ok: false as const,
              error:
                err instanceof Error ? err.message : 'Failed to load matchups.',
            }))
        : Promise.resolve({
            ok: true as const,
            data: { weeks: [], matchupsByWeek: {} },
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
        <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground text-center mb-6">
          {selectedSeason} Season Matchups
        </p>

        <div className="flex items-center justify-between mb-4">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            Matchups
          </p>
          {seasons.length > 0 && (
            <SeasonSelect
              seasons={seasons}
              value={selectedSeason}
              onValueChange={handleSeasonChange}
            />
          )}
        </div>

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
      </div>
    </div>
  );
}
