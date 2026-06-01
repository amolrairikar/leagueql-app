import { useEffect, useMemo, useRef, useState } from 'react';

import { Trophy } from 'lucide-react';

import { BoxScoreCard } from '@/components/box-score-card';
import SeasonSelect from '@/features/season_select/season-select';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { AVATAR_COLORS, UI_COLORS } from '@/lib/color-constants';
import { logger } from '@/lib/logger';
import {
  getPlayoffBracket,
  getMatchups,
  getWeeklyStandings,
  type BracketMatch,
  type Matchup,
} from './api-calls';

interface Team {
  team_id: string;
  display_name: string;
  team_name: string;
  team_logo: string | null;
}

// Generate consistent color from team ID
function getTeamColor(teamId: string): string {
  let hash = 0;
  for (let i = 0; i < teamId.length; i++) {
    hash = teamId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function TeamRow({
  team,
  score,
  isWinner,
  played,
  isBye,
  record,
  isChampion,
}: {
  team: Team | null;
  score: number | null;
  isWinner: boolean;
  played: boolean;
  isBye: boolean;
  record?: string | null;
  isChampion?: boolean;
}) {
  if (!team) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-border/30 last:border-b-0 opacity-55">
        <span className="text-[10px] font-medium text-muted-foreground w-3 text-center">
          —
        </span>
        <div className="w-5.5 h-5.5 rounded-full bg-border/50 flex items-center justify-center shrink-0" />
        <span className="text-[12px] font-medium text-muted-foreground italic flex-1 truncate">
          TBD
        </span>
      </div>
    );
  }

  const color = getTeamColor(team.team_id);
  const init = team.display_name.slice(0, 2).toUpperCase();
  const rowClass = played
    ? isWinner
      ? 'bg-muted'
      : 'opacity-40'
    : isBye
      ? 'opacity-55'
      : '';

  const scoreHtml = isBye ? (
    <span
      className="text-[9px] font-medium uppercase tracking-[0.05em] px-1 py-0.5 rounded"
      style={{
        color: UI_COLORS.champion.text,
        background: UI_COLORS.champion.bg,
      }}
    >
      BYE
    </span>
  ) : played && score !== null ? (
    <span
      className={`text-[12px] font-medium tabular-nums ${isWinner ? 'text-foreground' : 'text-muted-foreground'}`}
    >
      {Number(score).toFixed(1)}
    </span>
  ) : (
    <span className="text-[10px] font-medium text-muted-foreground italic">
      TBD
    </span>
  );

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1.5 border-b border-border/30 last:border-b-0 ${rowClass}`}
    >
      <div
        className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[8px] font-medium text-white shrink-0"
        style={{ background: color }}
      >
        {init}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-medium text-foreground truncate">
            {team.display_name}
          </span>
          {isChampion && (
            <Trophy
              className="w-3 h-3 shrink-0"
              style={{ color: UI_COLORS.gold }}
            />
          )}
        </div>
        <div className="text-[10px] text-muted-foreground truncate">
          {team.team_name || `Team ${team.display_name}`}
          {record ? ` (${record})` : ''}
        </div>
      </div>
      {scoreHtml}
    </div>
  );
}

function MatchupCard({
  match,
  extraClass,
  extraStyle,
  played,
  onClick,
  record1,
  record2,
  championId,
}: {
  match: BracketMatch | null;
  extraClass?: string;
  extraStyle?: React.CSSProperties;
  played: boolean;
  onClick?: () => void;
  record1?: string | null;
  record2?: string | null;
  championId?: string | null;
}) {
  if (!match) {
    return (
      <div className="bg-transparent border border-dashed border-border/30 rounded-md flex items-center justify-center p-3">
        <span className="text-[10px] text-muted-foreground italic">
          bye week
        </span>
      </div>
    );
  }

  const team1: Team = {
    team_id: match.team_1_id,
    display_name: match.team_1_display_name,
    team_name: match.team_1_team_name,
    team_logo: match.team_1_team_logo,
  };
  const team2: Team = {
    team_id: match.team_2_id,
    display_name: match.team_2_display_name,
    team_name: match.team_2_team_name,
    team_logo: match.team_2_team_logo,
  };

  const aWins = match.winner === match.team_1_id;
  const score1 = match.team_1_score ?? null;
  const score2 = match.team_2_score ?? null;

  return (
    <div
      className={`bg-card border border-border/30 rounded-md overflow-hidden ${extraClass || ''} ${onClick ? 'cursor-pointer hover:border-border/60' : ''}`}
      style={extraStyle}
      onClick={onClick}
    >
      <TeamRow
        team={team1}
        score={score1}
        isWinner={played && aWins}
        played={played}
        isBye={false}
        record={record1}
        isChampion={championId === team1.team_id}
      />
      <TeamRow
        team={team2}
        score={score2}
        isWinner={played && !aWins}
        played={played}
        isBye={false}
        record={record2}
        isChampion={championId === team2.team_id}
      />
    </div>
  );
}

function ByeCard({ team }: { team: Team }) {
  const color = getTeamColor(team.team_id);
  const init = team.display_name.slice(0, 2).toUpperCase();

  return (
    <div className="bg-card border border-border/30 rounded-md overflow-hidden opacity-70">
      <div className="flex items-center gap-1.5 px-2 py-1.5">
        <div
          className="w-5.5 h-5.5 rounded-full flex items-center justify-center text-[8px] font-medium text-white shrink-0"
          style={{ background: color }}
        >
          {init}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[12px] font-medium text-foreground truncate">
            {team.display_name}
          </div>
          <div className="text-[10px] text-muted-foreground truncate">
            {team.team_name || `Team ${team.display_name}`}
          </div>
        </div>
        <span
          className="text-[9px] font-medium uppercase tracking-[0.05em] px-1 py-0.5 rounded"
          style={{
            color: UI_COLORS.champion.text,
            background: UI_COLORS.champion.bg,
          }}
        >
          BYE
        </span>
      </div>
    </div>
  );
}

export default function PlayoffBracket() {
  const {
    leagueId,
    platform,
    seasons: allSeasons,
  } = useMemo(() => getLeagueCookies(), []);

  const [selectedSeason, setSelectedSeason] = useState(() =>
    allSeasons.length > 0 ? allSeasons[allSeasons.length - 1] : '2025',
  );
  const [matches, setMatches] = useState<BracketMatch[]>([]);
  const [matchups, setMatchups] = useState<Matchup[]>([]);
  const [recordMap, setRecordMap] = useState<Record<string, string>>({});
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const boxScoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedMatchId !== null) {
      boxScoreRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  }, [selectedMatchId]);

  useEffect(() => {
    if (!leagueId) {
      setError('No league selected. Please connect a league first.');
      setLoading(false);
      return;
    }

    async function fetchBracketData() {
      setLoading(true);
      setError(null);
      try {
        const [bracketResponse, matchupsResponse, standingsResponse] =
          await Promise.all([
            getPlayoffBracket(leagueId!, platform, selectedSeason),
            getMatchups(leagueId!, platform, selectedSeason),
            getWeeklyStandings(leagueId!, platform, selectedSeason),
          ]);

        const bracketMatches = bracketResponse.data;
        const matchupsData: Matchup[] = matchupsResponse.data;

        // Derive end-of-regular-season record per team from the last standings snapshot week
        const standingsData = standingsResponse.data;
        const recordsByWeek: Record<number, Record<string, string>> = {};
        for (const s of standingsData) {
          const week = parseInt(s.snapshot_week, 10);
          if (!isNaN(week)) (recordsByWeek[week] ??= {})[s.team_id] = s.record;
        }
        const snapshotWeeks = Object.keys(recordsByWeek).map(Number);
        const lastWeekRecords =
          snapshotWeeks.length > 0
            ? recordsByWeek[Math.max(...snapshotWeeks)]
            : {};
        setRecordMap(lastWeekRecords);

        // Store matchups in state for later use
        setMatchups(matchupsData);

        // Derive championship week from actual playoff matchup data (handles week-17, week-18, etc.)
        const playoffWeeks = matchupsData
          .filter((m) => m.playoff_tier_type && m.playoff_tier_type !== 'NONE')
          .map((m) => parseInt(m.week, 10))
          .filter((w) => !isNaN(w));
        const champWeek =
          playoffWeeks.length > 0
            ? Math.max(...playoffWeeks)
            : parseInt(selectedSeason, 10) < 2021
              ? 16
              : 17;
        const maxRound =
          bracketMatches.length > 0
            ? Math.max(...bracketMatches.map((m) => m.round))
            : 0;

        // Match each bracket match with its corresponding matchup to get scores
        const matchesWithScores = bracketMatches.map((bracketMatch) => {
          const week = champWeek - (maxRound - bracketMatch.round);
          const matchup = matchupsData.find(
            (m) =>
              m.season === bracketMatch.season &&
              parseInt(m.week, 10) === week &&
              ((m.team_a_id === bracketMatch.team_1_id &&
                m.team_b_id === bracketMatch.team_2_id) ||
                (m.team_a_id === bracketMatch.team_2_id &&
                  m.team_b_id === bracketMatch.team_1_id)),
          );

          if (matchup) {
            // Match found, assign scores (handle team order)
            const team1IsA = matchup.team_a_id === bracketMatch.team_1_id;
            return {
              ...bracketMatch,
              team_1_score: team1IsA
                ? matchup.team_a_score
                : matchup.team_b_score,
              team_2_score: team1IsA
                ? matchup.team_b_score
                : matchup.team_a_score,
            };
          }

          // No matchup found, return bracket match without scores
          return bracketMatch;
        });

        setMatches(matchesWithScores);
      } catch (err) {
        logger.error('Failed to fetch playoff bracket', err);
        setError('Failed to load playoff bracket data.');
        setMatches([]);
      } finally {
        setLoading(false);
      }
    }

    fetchBracketData();
  }, [leagueId, platform, selectedSeason]);

  // Parse matches from DynamoDB format
  const maxRound =
    matches.length > 0 ? Math.max(...matches.map((m) => m.round)) : 0;
  const championship = matches.find((m) => m.position === 1);
  const semifinals = matches.filter(
    (m) => m.round === maxRound - 1 && m.position === null,
  );
  const wildcard =
    maxRound >= 3
      ? matches.filter((m) => m.round === maxRound - 2 && m.position === null)
      : [];
  // Pair bye teams with their corresponding wildcard matchups
  const wildcardRoundItems = semifinals.map((semi) => {
    // Determine which team had a bye and which comes from a wildcard match
    let byeTeamId: string | null = null;
    let wildcardMatchId: number | null = null;

    if (semi.team_1_from === null) {
      byeTeamId = semi.team_1_id;
      // team_2_from should be like {"w": 1} or {"l": 1}
      if (semi.team_2_from) {
        const from = JSON.parse(semi.team_2_from);
        wildcardMatchId = from.w || from.l;
      }
    } else if (semi.team_2_from === null) {
      byeTeamId = semi.team_2_id;
      // team_1_from should be like {"w": 1} or {"l": 1}
      if (semi.team_1_from) {
        const from = JSON.parse(semi.team_1_from);
        wildcardMatchId = from.w || from.l;
      }
    }

    const wildcardMatch = wildcardMatchId
      ? wildcard.find((m) => m.match_id === wildcardMatchId)
      : null;
    const byeTeam = byeTeamId
      ? {
          team_id: byeTeamId,
          display_name:
            semi.team_1_id === byeTeamId
              ? semi.team_1_display_name
              : semi.team_2_display_name,
          team_name:
            semi.team_1_id === byeTeamId
              ? semi.team_1_team_name
              : semi.team_2_team_name,
          team_logo:
            semi.team_1_id === byeTeamId
              ? semi.team_1_team_logo
              : semi.team_2_team_logo,
        }
      : null;

    return { byeTeam, wildcardMatch };
  });

  const seasonOptions = allSeasons;

  // Derive championship week from matchup state (same logic as fetchBracketData)
  const championshipWeek = useMemo(() => {
    const playoffWeeks = matchups
      .filter((m) => m.playoff_tier_type && m.playoff_tier_type !== 'NONE')
      .map((m) => parseInt(m.week, 10))
      .filter((w) => !isNaN(w));
    return playoffWeeks.length > 0
      ? Math.max(...playoffWeeks)
      : parseInt(selectedSeason, 10) < 2021
        ? 16
        : 17;
  }, [matchups, selectedSeason]);

  // Helper function to find the corresponding matchup data for a selected bracket match
  const findMatchupForBracketMatch = (
    bracketMatch: BracketMatch,
  ): Matchup | null => {
    const week = championshipWeek - (maxRound - bracketMatch.round);
    return (
      matchups.find(
        (m) =>
          m.season === bracketMatch.season &&
          parseInt(m.week, 10) === week &&
          ((m.team_a_id === bracketMatch.team_1_id &&
            m.team_b_id === bracketMatch.team_2_id) ||
            (m.team_a_id === bracketMatch.team_2_id &&
              m.team_b_id === bracketMatch.team_1_id)),
      ) || null
    );
  };

  // Get the selected matchup data
  const selectedMatch =
    selectedMatchId !== null
      ? matches.find((m) => m.match_id === selectedMatchId)
      : null;
  const selectedMatchupData = selectedMatch
    ? findMatchupForBracketMatch(selectedMatch)
    : null;

  if (loading) {
    return (
      <div className="flex flex-1 flex-col p-6 overflow-auto">
        <div className="max-w-262.5 mx-auto w-full">
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading playoff bracket...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col p-6 overflow-auto">
        <div className="max-w-262.5 mx-auto w-full">
          <div className="text-center py-12">
            <p className="text-destructive">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-262.5 mx-auto w-full">
        <div className="mb-7">
          <SeasonSelect
            seasons={seasonOptions}
            value={selectedSeason}
            onValueChange={setSelectedSeason}
          />
        </div>

        {/* Main bracket */}
        <div className="overflow-x-auto -mx-6 px-6 mb-6">
          <div
            className={`grid ${maxRound >= 3 ? 'grid-cols-[1fr_8px_1fr_8px_1fr]' : 'grid-cols-[1fr_8px_1fr]'} gap-0 items-stretch ${maxRound >= 3 ? 'min-w-[560px]' : 'min-w-[380px]'}`}
          >
            {/* Wild Card Round (6-team+ formats only) */}
            {maxRound >= 3 && (
              <div className="flex flex-col">
                <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground text-center pb-2.5 border-b border-border/20 mb-0">
                  Wild card
                </div>
                <div className="flex-1 flex flex-col justify-around">
                  {wildcardRoundItems.map((item, idx) => (
                    <div key={idx} className="flex flex-col gap-2.5">
                      {item.byeTeam && <ByeCard team={item.byeTeam} />}
                      {item.wildcardMatch && (
                        <MatchupCard
                          match={item.wildcardMatch}
                          played={true}
                          onClick={() =>
                            setSelectedMatchId(
                              item.wildcardMatch?.match_id === selectedMatchId
                                ? null
                                : (item.wildcardMatch?.match_id ?? null),
                            )
                          }
                          record1={
                            recordMap[item.wildcardMatch.team_1_id] ?? null
                          }
                          record2={
                            recordMap[item.wildcardMatch.team_2_id] ?? null
                          }
                        />
                      )}
                      {idx === 0 && <div className="h-8" />}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Connector 1 (6-team+ formats only) */}
            {maxRound >= 3 && (
              <div className="flex flex-col justify-around pt-11">
                <svg
                  width="20"
                  height="58"
                  viewBox="0 0 20 58"
                  overflow="visible"
                  className="block"
                >
                  <path
                    d="M0,15 H10 V43 H0"
                    stroke="hsl(var(--border))"
                    strokeWidth="1"
                    fill="none"
                  />
                  <line
                    x1="10"
                    y1="29"
                    x2="20"
                    y2="29"
                    stroke="hsl(var(--border))"
                    strokeWidth="1"
                  />
                </svg>
                <svg
                  width="20"
                  height="58"
                  viewBox="0 0 20 58"
                  overflow="visible"
                  className="block"
                >
                  <path
                    d="M0,15 H10 V43 H0"
                    stroke="hsl(var(--border))"
                    strokeWidth="1"
                    fill="none"
                  />
                  <line
                    x1="10"
                    y1="29"
                    x2="20"
                    y2="29"
                    stroke="hsl(var(--border))"
                    strokeWidth="1"
                  />
                </svg>
              </div>
            )}

            {/* Semifinals */}
            <div className="flex flex-col">
              <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground text-center pb-2.5 border-b border-border/20 mb-0">
                Semifinals
              </div>
              <div className="flex-1 flex flex-col justify-around">
                {semifinals.map((match) => (
                  <MatchupCard
                    key={match.match_id}
                    match={match}
                    played={true}
                    onClick={() =>
                      setSelectedMatchId(
                        match.match_id === selectedMatchId
                          ? null
                          : match.match_id,
                      )
                    }
                    record1={recordMap[match.team_1_id] ?? null}
                    record2={recordMap[match.team_2_id] ?? null}
                  />
                ))}
              </div>
            </div>

            {/* Connector 2 */}
            <div className="flex flex-col justify-around pt-11">
              <svg
                width="20"
                height="130"
                viewBox="0 0 20 130"
                overflow="visible"
                className="block"
              >
                <path
                  d="M0,25 H10 V105 H0"
                  stroke="hsl(var(--border))"
                  strokeWidth="1"
                  fill="none"
                />
                <line
                  x1="10"
                  y1="65"
                  x2="20"
                  y2="65"
                  stroke="hsl(var(--border))"
                  strokeWidth="1"
                />
              </svg>
            </div>

            {/* Championship */}
            <div className="flex flex-col">
              <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground text-center pb-2.5 border-b border-border/20 mb-0">
                Championship
              </div>
              <div className="flex-1 flex flex-col justify-around">
                {championship && (
                  <MatchupCard
                    match={championship}
                    extraClass={`border-2`}
                    extraStyle={{ borderColor: UI_COLORS.gold }}
                    played={true}
                    onClick={() =>
                      setSelectedMatchId(
                        championship.match_id === selectedMatchId
                          ? null
                          : championship.match_id,
                      )
                    }
                    record1={recordMap[championship.team_1_id] ?? null}
                    record2={recordMap[championship.team_2_id] ?? null}
                    championId={championship.winner}
                  />
                )}
              </div>
            </div>
          </div>
        </div>

        {selectedMatchupData && selectedMatch && (
          <>
            <div className="mt-6 mb-2 border-t border-border/50" />
            <div ref={boxScoreRef}>
              <BoxScoreCard
                left={{
                  teamLogo: selectedMatch.team_1_team_logo,
                  teamName:
                    selectedMatch.team_1_team_name ||
                    `Team ${selectedMatch.team_1_display_name}`,
                  ownerUsername: selectedMatch.team_1_display_name,
                  color: getTeamColor(selectedMatch.team_1_id),
                  score: selectedMatch.team_1_score ?? 0,
                  starters:
                    selectedMatchupData.team_a_id === selectedMatch.team_1_id
                      ? selectedMatchupData.team_a_starters
                      : selectedMatchupData.team_b_starters,
                  bench:
                    selectedMatchupData.team_a_id === selectedMatch.team_1_id
                      ? selectedMatchupData.team_a_bench
                      : selectedMatchupData.team_b_bench,
                  isWinner: selectedMatch.winner === selectedMatch.team_1_id,
                }}
                right={{
                  teamLogo: selectedMatch.team_2_team_logo,
                  teamName:
                    selectedMatch.team_2_team_name ||
                    `Team ${selectedMatch.team_2_display_name}`,
                  ownerUsername: selectedMatch.team_2_display_name,
                  color: getTeamColor(selectedMatch.team_2_id),
                  score: selectedMatch.team_2_score ?? 0,
                  starters:
                    selectedMatchupData.team_a_id === selectedMatch.team_2_id
                      ? selectedMatchupData.team_a_starters
                      : selectedMatchupData.team_b_starters,
                  bench:
                    selectedMatchupData.team_a_id === selectedMatch.team_2_id
                      ? selectedMatchupData.team_a_bench
                      : selectedMatchupData.team_b_bench,
                  isWinner: selectedMatch.winner === selectedMatch.team_2_id,
                }}
                platform={platform}
                season={selectedMatch.season}
                onClose={() => setSelectedMatchId(null)}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
