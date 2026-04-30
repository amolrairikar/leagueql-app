import { Suspense, use, useEffect, useMemo, useRef, useState } from 'react';

import { BoxScoreCard, type BoxScoreSide } from '@/components/box-score-card';
import { avatarColor } from '@/components/team-avatar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { POS_NORMALIZE } from '@/lib/position-constants';
import { POSITION_COLORS, UI_COLORS } from '@/lib/color-constants';
import {
  getAllMatchups,
  type MatchupItem,
} from '@/features/player_records/api-calls';

interface ScoringRecord {
  pos: string;
  player: string;
  pts: number;
  manager: string;
  managerColor: string;
  managerInit: string;
  season: string;
  week: number;
}

const POS_ORDER = ['QB', 'WR', 'RB', 'TE', 'DEF', 'K'];
const POS_SET = new Set(POS_ORDER);
const EMPTY_MATCHUPS: MatchupItem[] = [];

function buildColorMap(matchups: MatchupItem[]): Map<string, string> {
  const uniqueTeams = new Map<string, string>();
  for (const m of matchups) {
    uniqueTeams.set(m.team_a_id, m.team_a_display_name ?? '');
    uniqueTeams.set(m.team_b_id, m.team_b_display_name ?? '');
  }
  const sortedIds = [...uniqueTeams.entries()]
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([id]) => id);
  return new Map(sortedIds.map((id, i) => [id, avatarColor(i)]));
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (
      (parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')
    ).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

function extractEntries(
  matchups: MatchupItem[],
  colorMap: Map<string, string>,
): ScoringRecord[] {
  const entries: ScoringRecord[] = [];

  for (const m of matchups) {
    const week = parseInt(m.week, 10);
    if (isNaN(week)) continue;

    const aColor = colorMap.get(m.team_a_id) ?? UI_COLORS.default;
    const bColor = colorMap.get(m.team_b_id) ?? UI_COLORS.default;

    for (const player of m.team_a_starters ?? []) {
      const pos = POS_NORMALIZE[player.position] ?? player.position;
      if (!POS_SET.has(pos) || player.points_scored == null) continue;
      entries.push({
        pos,
        player: player.full_name,
        pts: player.points_scored,
        manager: m.team_a_display_name,
        managerColor: aColor,
        managerInit: initials(m.team_a_display_name),
        season: m.season,
        week,
      });
    }

    for (const player of m.team_b_starters ?? []) {
      const pos = POS_NORMALIZE[player.position] ?? player.position;
      if (!POS_SET.has(pos) || player.points_scored == null) continue;
      entries.push({
        pos,
        player: player.full_name,
        pts: player.points_scored,
        manager: m.team_b_display_name,
        managerColor: bColor,
        managerInit: initials(m.team_b_display_name),
        season: m.season,
        week,
      });
    }
  }

  return entries;
}

function PositionCard({
  pos,
  rows,
  selectedKey,
  onRowClick,
}: {
  pos: string;
  rows: ScoringRecord[];
  selectedKey: string | null;
  onRowClick: (key: string) => void;
}) {
  const meta = POSITION_COLORS[pos];
  const maxPts = rows[0]?.pts ?? 1;

  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2.5 px-3.5 py-2.5 border-b border-border/50 bg-muted">
        <span
          className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium"
          style={{ background: meta.bg, color: meta.tc }}
        >
          {pos}
        </span>
        <span className="text-[13px] font-medium text-foreground">
          {meta.label}
        </span>
      </div>

      <table
        className="w-full border-collapse text-[12px]"
        style={{ tableLayout: 'fixed' }}
      >
        <thead>
          <tr>
            <th
              className="text-left text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-1.5 border-b border-border/50"
              style={{ width: '28px' }}
            >
              #
            </th>
            <th className="text-left text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-1.5 border-b border-border/50">
              Player
            </th>
            <th
              className="text-right text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground px-3 py-1.5 border-b border-border/50"
              style={{ width: '130px' }}
            >
              Score
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const barPct = Math.round((r.pts / maxPts) * 100);
            const isGold = i === 0;
            const rowKey = `${r.player}-${r.season}-${r.week}`;
            const isSelected = selectedKey === rowKey;

            return (
              <tr
                key={rowKey}
                className={`border-b border-border/50 last:border-0 cursor-pointer transition-colors ${isSelected ? 'bg-muted/60' : 'hover:bg-muted/40'}`}
                onClick={() => onRowClick(isSelected ? '' : rowKey)}
              >
                <td
                  className="px-3 py-2"
                  style={
                    isGold ? { borderLeft: `2px solid ${UI_COLORS.gold}` } : undefined
                  }
                >
                  <span className="text-[11px] text-muted-foreground">
                    {i + 1}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <div className="text-[13px] font-medium text-foreground">
                    {r.player}
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                    <div
                      className="w-4.5 h-4.5 rounded-full flex items-center justify-center text-[8px] font-medium text-white shrink-0"
                      style={{ background: r.managerColor }}
                    >
                      {r.managerInit}
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      {r.manager}
                    </span>
                    <span className="inline-flex px-1.5 py-px rounded text-[10px] font-medium bg-muted text-muted-foreground">
                      {r.season} Wk {r.week}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden min-w-10">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${barPct}%`, background: meta.color }}
                      />
                    </div>
                    <span className="text-[13px] font-medium text-foreground min-w-9 text-right">
                      {r.pts.toFixed(1)}
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BoxScoreView({
  matchup,
  colorMap,
  onClose,
  platform,
}: {
  matchup: MatchupItem;
  colorMap: Map<string, string>;
  onClose: () => void;
  platform: 'ESPN' | 'SLEEPER';
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const aWins = matchup.team_a_score > matchup.team_b_score;
  const left: BoxScoreSide = {
    teamLogo: matchup.team_a_team_logo,
    teamName: matchup.team_a_team_name,
    ownerUsername: matchup.team_a_display_name,
    color: colorMap.get(matchup.team_a_id) ?? UI_COLORS.default,
    score: matchup.team_a_score,
    starters: matchup.team_a_starters ?? [],
    bench: matchup.team_a_bench ?? [],
    isWinner: aWins,
  };
  const right: BoxScoreSide = {
    teamLogo: matchup.team_b_team_logo,
    teamName: matchup.team_b_team_name,
    ownerUsername: matchup.team_b_display_name,
    color: colorMap.get(matchup.team_b_id) ?? UI_COLORS.default,
    score: matchup.team_b_score,
    starters: matchup.team_b_starters ?? [],
    bench: matchup.team_b_bench ?? [],
    isWinner: !aWins,
  };

  return (
    <div className="mt-8" ref={ref}>
      <BoxScoreCard
        left={left}
        right={right}
        subtitle={`Week ${matchup.week} · Final`}
        platform={platform}
        season={matchup.season}
        onClose={onClose}
      />
    </div>
  );
}

function SkeletonPlayerRecords() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="bg-card border border-border/50 rounded-lg overflow-hidden"
        >
          <div className="flex items-center gap-2.5 px-3.5 py-2.5 border-b border-border/50 bg-muted">
            <Skeleton className="h-5 w-10 rounded-full" />
            <Skeleton className="h-3.5 w-28" />
          </div>
          <div className="divide-y divide-border/50">
            {Array.from({ length: 5 }).map((_, j) => (
              <div key={j} className="px-3 py-2 flex items-center gap-3">
                <Skeleton className="h-3 w-3" />
                <div className="flex-1">
                  <Skeleton className="h-3.5 w-28 mb-1.5" />
                  <div className="flex items-center gap-1.5">
                    <Skeleton className="h-4 w-4 rounded-full" />
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-3 w-16" />
                  </div>
                </div>
                <Skeleton className="h-1.5 w-16" />
                <Skeleton className="h-3.5 w-10" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

type Result = { ok: true; data: MatchupItem[] } | { ok: false; error: string };

function PlayerRecordsContent({
  promise,
  platform,
}: {
  promise: Promise<Result>;
  platform: 'ESPN' | 'SLEEPER';
}) {
  const result = use(promise);

  const matchups = result.ok ? result.data : EMPTY_MATCHUPS;
  const colorMap = useMemo(() => buildColorMap(matchups), [matchups]);
  const allRecords = useMemo(
    () => extractEntries(matchups, colorMap),
    [matchups, colorMap],
  );
  const seasons = useMemo(
    () =>
      [...new Set(allRecords.map((r) => r.season))].sort(
        (a, b) => Number(b) - Number(a),
      ),
    [allRecords],
  );
  const managers = useMemo(
    () => [...new Set(allRecords.map((r) => r.manager))].sort(),
    [allRecords],
  );

  const [season, setSeason] = useState<string>('all');
  const [manager, setManager] = useState<string>('all');
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const positionCards = useMemo(() => {
    const filtered = allRecords.filter((r) => {
      if (season !== 'all' && r.season !== season) return false;
      if (manager !== 'all' && r.manager !== manager) return false;
      return true;
    });

    return POS_ORDER.map((pos) => {
      const rows = filtered
        .filter((r) => r.pos === pos)
        .sort((a, b) => b.pts - a.pts)
        .slice(0, 5);
      return { pos, rows };
    }).filter(({ rows }) => rows.length > 0);
  }, [allRecords, season, manager]);

  const selectedRecord = useMemo(() => {
    if (!selectedKey) return null;
    for (const { rows } of positionCards) {
      const found = rows.find(
        (r) => `${r.player}-${r.season}-${r.week}` === selectedKey,
      );
      if (found) return found;
    }
    return null;
  }, [selectedKey, positionCards]);

  const selectedMatchup = useMemo(() => {
    if (!selectedRecord) return null;
    return (
      matchups.find(
        (m) =>
          m.season === selectedRecord.season &&
          parseInt(m.week, 10) === selectedRecord.week &&
          (m.team_a_display_name === selectedRecord.manager ||
            m.team_b_display_name === selectedRecord.manager),
      ) ?? null
    );
  }, [selectedRecord, matchups]);

  const handleRowClick = (key: string) => {
    setSelectedKey(key || null);
  };

  if (!result.ok) {
    return <p className="text-[13px] text-destructive">{result.error}</p>;
  }

  return (
    <>
      <div className="flex items-center gap-2.5 mb-5 flex-wrap">
        <span className="text-[12px] font-medium text-muted-foreground">
          Season
        </span>
        <Select
          value={season}
          onValueChange={(v) => {
            setSeason(v);
            setSelectedKey(null);
          }}
        >
          <SelectTrigger size="sm" className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All seasons</SelectItem>
            {seasons.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <span className="text-[12px] font-medium text-muted-foreground ml-2">
          Manager
        </span>
        <Select
          value={manager}
          onValueChange={(v) => {
            setManager(v);
            setSelectedKey(null);
          }}
        >
          <SelectTrigger size="sm" className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All managers</SelectItem>
            {managers.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {positionCards.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          No records match the selected filters.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {positionCards.map(({ pos, rows }) => (
            <PositionCard
              key={pos}
              pos={pos}
              rows={rows}
              selectedKey={selectedKey}
              onRowClick={handleRowClick}
            />
          ))}
        </div>
      )}

      {selectedMatchup !== null && (
        <BoxScoreView
          key={selectedKey}
          matchup={selectedMatchup}
          colorMap={colorMap}
          onClose={() => setSelectedKey(null)}
          platform={platform}
        />
      )}
    </>
  );
}

export default function PlayerRecords() {
  const { leagueId, platform } = getLeagueCookies();

  const promise = useMemo(
    (): Promise<Result> =>
      leagueId
        ? getAllMatchups(leagueId, platform)
            .then((res) => ({ ok: true as const, data: res.data }))
            .catch((err) => ({
              ok: false as const,
              error:
                err instanceof Error
                  ? err.message
                  : 'Failed to load scoring records.',
            }))
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-4xl mx-auto w-full">
        <Suspense
          fallback={
            <div>
              <div className="flex items-center gap-2.5 mb-5 flex-wrap">
                <Skeleton className="h-3 w-12" />
                <Skeleton className="h-7 w-32 rounded-md" />
                <Skeleton className="h-3 w-16 ml-2" />
                <Skeleton className="h-7 w-36 rounded-md" />
              </div>
              <SkeletonPlayerRecords />
            </div>
          }
        >
          <PlayerRecordsContent promise={promise} platform={platform} />
        </Suspense>
      </div>
    </div>
  );
}
