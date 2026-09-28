import { Info, Mail, Trophy } from 'lucide-react';
import { Suspense, use, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

import {
  getDraftData,
  getLeagueSettings,
  getManagerHistoryData,
  getMyTeam,
  putMyTeam,
} from './api-calls';
import {
  computeMyTeam,
  listSeasonTeams,
  type GameResult,
  type InSeasonView,
  type MyTeamInput,
  type MyTeamView,
  type OffseasonView,
  type TeamOption,
  type TeamSummary,
  type ThisWeekMatchup,
  type TopDraftPick,
} from './compute-my-team';

import { TeamAvatar } from '@/components/team-avatar';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { assignAvatarColors, avatarColor } from '@/lib/color-constants';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';
import { toResult, type Result } from '@/lib/result';

const LABEL =
  'text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground';

const fmtPts = (n: number) => n.toFixed(1);
// Points for is shown to two decimals on the record tiles.
const fmtPf = (n: number) => n.toFixed(2);
const fmtPct = (n: number) => `${Math.round(n * 100)}%`;
const ordinal = (n: number) => {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] ?? s[v] ?? s[0]}`;
};
const record = (t: { wins: number; losses: number; ties: number }) =>
  t.ties > 0 ? `${t.wins}–${t.losses}–${t.ties}` : `${t.wins}–${t.losses}`;

function PageSkeleton() {
  return (
    <div
      className="bg-card border border-border/50 rounded-xl p-5 flex flex-col gap-4"
      aria-label="Loading My Team"
    >
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-full" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
      <Skeleton className="h-40" />
    </div>
  );
}

interface PageData {
  input: MyTeamInput;
  teams: TeamOption[];
}

export default function MyTeamPage() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);
  const season = useMemo(() => [...seasons].sort().at(-1) ?? '', [seasons]);

  const claimPromise = useMemo(
    (): Promise<Result<string | null>> =>
      toResult(
        getMyTeam(leagueId, platform).then((r) => r.data.owner_id),
        'Failed to load your team.',
      ),
    [leagueId, platform],
  );

  const dataPromise = useMemo(
    (): Promise<Result<PageData>> =>
      toResult(
        Promise.all([
          getManagerHistoryData(leagueId, platform, seasons),
          // Same fallback as the playoff predictor: without settings the odds use
          // the assumed default cutoff rather than failing the page.
          getLeagueSettings(leagueId, platform, season)
            .then((r) => r.data[0] ?? null)
            .catch(() => null),
          // Optional section: no draft (404) or a failed load shows the empty
          // message rather than failing the page.
          getDraftData(leagueId, platform, season)
            .then((r) => r.data)
            .catch(() => []),
        ]).then(([history, settings, draftPicks]) => ({
          input: { ...history, settings, season, draftPicks },
          teams: listSeasonTeams(history.matchups, season),
        })),
        'Failed to load league data.',
      ),
    [leagueId, platform, seasons, season],
  );

  return (
    <div className="flex flex-1 flex-col p-4 sm:p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-foreground">My Team</h1>
        </div>
        <Suspense fallback={<PageSkeleton />}>
          <MyTeamContent
            claimPromise={claimPromise}
            dataPromise={dataPromise}
            leagueId={leagueId}
            platform={platform}
          />
        </Suspense>
      </div>
    </div>
  );
}

function MyTeamContent({
  claimPromise,
  dataPromise,
  leagueId,
  platform,
}: {
  claimPromise: Promise<Result<string | null>>;
  dataPromise: Promise<Result<PageData>>;
  leagueId: string;
  platform: Parameters<typeof putMyTeam>[1];
}) {
  const claim = use(claimPromise);
  const data = use(dataPromise);
  const [ownerId, setOwnerId] = useState<string | null>(
    claim.ok ? claim.data : null,
  );
  const [picking, setPicking] = useState(false);

  const view = useMemo(
    () => (data.ok ? computeMyTeam(data.data.input, ownerId) : null),
    [data, ownerId],
  );
  const colors = useMemo(
    () =>
      data.ok
        ? assignAvatarColors(data.data.teams.map((t) => t.teamId))
        : new Map<string, string>(),
    [data],
  );

  if (!claim.ok) return <ErrorAlert message={claim.error} />;
  if (!data.ok) return <ErrorAlert message={data.error} />;

  if (!view || picking) {
    return (
      <TeamPicker
        teams={data.data.teams}
        colors={colors}
        initialTeamId={view?.team.teamId ?? null}
        changing={view != null}
        onCancel={() => setPicking(false)}
        onSave={async (team) => {
          await putMyTeam(leagueId, platform, team.ownerId);
          setOwnerId(team.ownerId);
          setPicking(false);
        }}
      />
    );
  }

  return (
    <YourWeekCard
      view={view}
      colors={colors}
      onChangeTeam={() => setPicking(true)}
    />
  );
}

function TeamPicker({
  teams,
  colors,
  initialTeamId,
  changing,
  onCancel,
  onSave,
}: {
  teams: TeamOption[];
  colors: Map<string, string>;
  initialTeamId: string | null;
  changing: boolean;
  onCancel: () => void;
  onSave: (team: TeamOption) => Promise<void>;
}) {
  const [selected, setSelected] = useState<string | null>(initialTeamId);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    const team = teams.find((t) => t.teamId === selected);
    if (!team) return;
    setSaving(true);
    setError(null);
    const result = await toResult(onSave(team), 'Failed to save your team.');
    if (!result.ok) setError(result.error);
    setSaving(false);
  }

  return (
    <section
      aria-labelledby="claim-heading"
      className="bg-card border border-border/50 rounded-xl p-5 sm:p-6 flex flex-col gap-4"
    >
      <div className="flex flex-col gap-1.5">
        <h2 id="claim-heading" className="text-lg font-semibold">
          Which team is yours?
        </h2>
        <p className="text-[13px] text-muted-foreground max-w-xl">
          Pick your team and this page will show your week: your matchup,
          playoff odds, and how last week went. Only you see this.
        </p>
      </div>
      <div
        role="radiogroup"
        aria-label="Teams"
        className="grid grid-cols-2 sm:grid-cols-5 gap-2"
      >
        {teams.map((t, i) => {
          const checked = selected === t.teamId;
          return (
            <button
              key={t.teamId}
              type="button"
              role="radio"
              aria-checked={checked}
              onClick={() => setSelected(t.teamId)}
              className={`flex flex-col items-center gap-1.5 px-2 py-3.5 rounded-lg border-2 text-center cursor-pointer transition-colors ${
                checked
                  ? 'border-primary bg-primary/5'
                  : 'border-border bg-background hover:bg-muted'
              }`}
            >
              <TeamAvatar
                teamLogo={t.teamLogo}
                teamName={t.teamName}
                ownerUsername={t.ownerUsername}
                color={colors.get(t.teamId) ?? avatarColor(i)}
                size="lg"
              />
              <span className="text-[13px] font-semibold text-foreground">
                {t.teamName}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {t.ownerUsername}
              </span>
            </button>
          );
        })}
      </div>
      {error && <ErrorAlert message={error} />}
      <div className="flex items-center gap-4 border-t border-border/50 pt-4">
        <Button
          onClick={() => void save()}
          disabled={!selected || saving}
          className="min-h-11 cursor-pointer"
        >
          Save my team
        </Button>
        {changing ? (
          <Button variant="ghost" className="cursor-pointer" onClick={onCancel}>
            Cancel
          </Button>
        ) : (
          <Link
            to="/home"
            className="text-[13px] text-muted-foreground cursor-pointer"
          >
            Not now
          </Link>
        )}
        <span className="ml-auto text-[12px] text-muted-foreground hidden sm:inline">
          You can change this anytime.
        </span>
      </div>
    </section>
  );
}

function Tile({
  label,
  value,
  sub,
  subTone = 'muted',
  to,
}: {
  label: string;
  value: ReactNode;
  /** Omit for a tile with no subtext. */
  sub?: ReactNode;
  subTone?: 'muted' | 'up' | 'down';
  to?: string;
}) {
  const tone =
    subTone === 'up'
      ? 'text-green-700 dark:text-green-400'
      : subTone === 'down'
        ? 'text-red-700 dark:text-red-400'
        : 'text-muted-foreground';
  const body = (
    <>
      <span className={LABEL}>{label}</span>
      <span className="text-[22px] font-semibold tabular-nums text-foreground">
        {value}
      </span>
      {sub != null && <span className={`text-[12px] ${tone}`}>{sub}</span>}
    </>
  );
  const cls =
    'bg-background border border-border/50 rounded-lg p-3 flex flex-col gap-1';
  return to ? (
    <Link
      to={to}
      className={`${cls} hover:bg-muted transition-colors cursor-pointer`}
    >
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

function CardHeader({
  team,
  heading,
  colors,
  onChangeTeam,
}: {
  team: TeamSummary;
  heading: string;
  colors: Map<string, string>;
  onChangeTeam: () => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <TeamAvatar
        teamLogo={team.teamLogo}
        teamName={team.teamName}
        ownerUsername={team.ownerUsername}
        color={colors.get(team.teamId) ?? avatarColor(0)}
        size="lg"
      />
      <div className="flex-1 flex flex-col gap-0.5 min-w-0">
        <h2 className={LABEL}>{heading}</h2>
        <div className="text-base font-semibold truncate">
          {team.teamName}{' '}
          <span className="font-normal text-muted-foreground text-[13px]">
            · {team.ownerUsername}
          </span>
        </div>
      </div>
      <Button
        variant="link"
        className="text-[12px] px-0 cursor-pointer"
        onClick={onChangeTeam}
      >
        Change team
      </Button>
    </div>
  );
}

function efficiencyTile(view: MyTeamView) {
  const { seasonPct, lastWeekPointsLeft } = view.efficiency;
  const sub =
    view.kind === 'in-season'
      ? lastWeekPointsLeft != null
        ? `${fmtPts(lastWeekPointsLeft)} pts left on bench last week`
        : 'No lineup data last week'
      : undefined;
  return (
    <Tile
      label="Lineup efficiency"
      value={seasonPct != null ? fmtPct(seasonPct) : '—'}
      sub={seasonPct != null ? sub : 'Not available yet'}
      subTone={lastWeekPointsLeft ? 'down' : 'muted'}
      to="/matchups"
    />
  );
}

function AwardsRow({ view }: { view: MyTeamView }) {
  const { lastWeek, highestScoreCount } = view.awards;
  return (
    <div className="border border-border/50 rounded-lg px-3.5 py-3 flex items-center gap-3">
      <Trophy className="h-5 w-5 text-yellow-500 shrink-0" aria-hidden />
      <div className="flex-1 flex flex-col gap-0.5">
        <span className="text-[13px] font-medium">
          {lastWeek.length > 0
            ? `Last week: ${lastWeek.join(', ')}`
            : 'No awards last week'}
        </span>
        <span className="text-[12px] text-muted-foreground">
          Highest Score {highestScoreCount}× this season
        </span>
      </div>
      <Link to="/matchups" className="text-[12px] text-primary cursor-pointer">
        Awards
      </Link>
    </div>
  );
}

function DraftSlot({ pick }: { pick: TopDraftPick }) {
  return pick.bid != null ? (
    <>${pick.bid}</>
  ) : (
    <>
      Rd {pick.round}, Pick {pick.roundPick} (#{pick.overallPick})
    </>
  );
}

function TopDraftPicks({ picks }: { picks: TopDraftPick[] }) {
  return (
    <section
      className="border border-border/50 rounded-lg p-4 flex flex-col gap-3"
      aria-label="My top 3 draft picks"
    >
      <div className="flex items-center justify-between">
        <span className={LABEL}>My top 3 draft picks</span>
        <Link
          to="/draft_grades"
          className="text-[12px] font-medium text-primary cursor-pointer"
        >
          Draft grades →
        </Link>
      </div>
      {picks.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          No draft value data yet
        </p>
      ) : (
        <ol className="flex flex-col divide-y divide-border/50">
          {picks.map((p, i) => (
            <li key={p.overallPick} className="flex items-center gap-3 py-2">
              <span className="text-[12px] text-muted-foreground w-4 text-right shrink-0">
                {i + 1}
              </span>
              <div className="flex-1 min-w-0 flex flex-col">
                <span className="text-[13px] font-medium truncate">
                  {p.playerName}{' '}
                  <span className="text-[11px] font-normal text-muted-foreground">
                    {p.position}
                  </span>
                </span>
                <span className="text-[12px] text-muted-foreground">
                  <DraftSlot pick={p} />
                </span>
              </div>
              <div className="flex flex-col items-end shrink-0 tabular-nums">
                <span className="text-[13px] font-semibold">
                  {p.vorp >= 0 ? '+' : ''}
                  {fmtPts(p.vorp)} VORP
                </span>
                <span className="text-[12px] text-muted-foreground">
                  {p.totalPoints != null ? `${fmtPts(p.totalPoints)} pts` : '—'}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function EmailPlaceholderRow() {
  return (
    <div className="border border-border/50 rounded-lg px-3.5 py-3 flex items-center gap-3">
      <Mail className="h-5 w-5 text-muted-foreground shrink-0" aria-hidden />
      <div className="flex-1 flex flex-col gap-1 items-start">
        <div className="flex items-center gap-1.5">
          <label
            htmlFor="email-digest"
            className="text-[13px] font-medium text-muted-foreground"
          >
            Email me each week
          </label>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label="What's in the weekly emails"
                className="text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <Info className="h-3.5 w-3.5" aria-hidden />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-72">
              You will receive 2 weekly emails. On Tuesday, a recap of last
              week, and on Thursday, a preview of your upcoming matchup. You can
              opt out of the email recaps at any time and are opted out by
              default.
            </TooltipContent>
          </Tooltip>
        </div>
        <span className="text-[10px] font-bold tracking-[0.06em] text-primary bg-primary/10 rounded px-1.5 py-0.5">
          COMING SOON!
        </span>
      </div>
      <Switch id="email-digest" checked={false} disabled aria-disabled="true" />
    </div>
  );
}

function ResultLetter({ r }: { r: GameResult }) {
  const tone =
    r === 'W'
      ? 'text-green-700 dark:text-green-400'
      : r === 'L'
        ? 'text-red-700 dark:text-red-400'
        : 'text-muted-foreground';
  return <span className={tone}>{r}</span>;
}

function MatchupPanel({
  team,
  matchup,
  colors,
}: {
  team: TeamSummary;
  matchup: ThisWeekMatchup | null;
  colors: Map<string, string>;
}) {
  if (!matchup) {
    return (
      <div className="border border-border/50 rounded-lg p-4 bg-primary/5">
        <span className={LABEL}>This week&apos;s matchup</span>
        <p className="text-[13px] text-muted-foreground mt-2">
          No matchup this week
        </p>
      </div>
    );
  }
  const { opponent: opp } = matchup;
  const mine = Math.round(matchup.winProbMine * 100);
  const { h2h, lastMeeting } = matchup;
  const h2hText = record(h2h);
  const lead =
    h2h.wins > h2h.losses
      ? '(you lead)'
      : h2h.wins < h2h.losses
        ? '(they lead)'
        : h2h.wins + h2h.losses + h2h.ties > 0
          ? '(tied)'
          : '(first meeting)';
  const side = (t: TeamSummary, align: 'start' | 'end') => (
    <div
      className={`flex items-center gap-2.5 min-w-0 ${align === 'end' ? 'justify-end flex-row-reverse' : ''}`}
    >
      <TeamAvatar
        teamLogo={t.teamLogo}
        teamName={t.teamName}
        ownerUsername={t.ownerUsername}
        color={colors.get(t.teamId) ?? avatarColor(1)}
      />
      <div
        className={`flex flex-col min-w-0 ${align === 'end' ? 'items-end' : ''}`}
      >
        <span className="text-[14px] font-semibold truncate">{t.teamName}</span>
        <span className="text-[12px] text-muted-foreground">
          {record(t)} · {ordinal(t.rank)}
        </span>
      </div>
    </div>
  );
  return (
    <div
      className="border border-border/50 rounded-lg p-4 flex flex-col gap-3.5 bg-primary/5"
      aria-label="This week's matchup"
    >
      <div className="flex items-center justify-between">
        <span className={LABEL}>This week&apos;s matchup</span>
        <Link
          to="/matchups"
          className="text-[12px] font-medium text-primary cursor-pointer"
        >
          Open full preview →
        </Link>
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        {side(team, 'start')}
        <div className="flex flex-col items-center">
          <span className="font-mono text-base sm:text-lg font-medium tabular-nums">
            {matchup.projMine != null && matchup.projOpp != null
              ? `${fmtPts(matchup.projMine)} – ${fmtPts(matchup.projOpp)}`
              : '— – —'}
          </span>
          <span className="text-[11px] text-muted-foreground">projected</span>
        </div>
        {side(opp, 'end')}
      </div>
      <div className="flex flex-col gap-1.5">
        <div
          className="flex h-2 rounded overflow-hidden bg-muted"
          role="img"
          aria-label={`${mine}% win probability`}
        >
          <div className="bg-primary" style={{ width: `${mine}%` }} />
          <div className="bg-orange-500" style={{ width: `${100 - mine}%` }} />
        </div>
        <div className="flex justify-between text-[12px] tabular-nums">
          <span className="font-semibold">{mine}% win probability</span>
          <span className="text-muted-foreground">{100 - mine}%</span>
        </div>
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-[12px] text-muted-foreground border-t border-border/50 pt-3">
        <span>
          All-time H2H{' '}
          <strong className="text-foreground font-semibold">{h2hText}</strong>{' '}
          {lead}
        </span>
        {lastMeeting && (
          <span>
            Last meeting{' '}
            <strong className="text-foreground font-semibold">
              {lastMeeting.result} {fmtPts(lastMeeting.points)}–
              {fmtPts(lastMeeting.oppPoints)}
            </strong>{' '}
            · {lastMeeting.season} Wk {lastMeeting.week}
          </span>
        )}
        {matchup.opponentLast3.length > 0 && (
          <span>
            Their last {matchup.opponentLast3.length}{' '}
            <strong className="font-semibold">
              {matchup.opponentLast3.map((r, i) => (
                <span key={i}>
                  {i > 0 && ' '}
                  <ResultLetter r={r} />
                </span>
              ))}
            </strong>
          </span>
        )}
      </div>
    </div>
  );
}

function InSeasonCard({
  view,
  colors,
  onChangeTeam,
}: {
  view: InSeasonView;
  colors: Map<string, string>;
  onChangeTeam: () => void;
}) {
  const { team, lastWeekGame: g, playoffOddsChange: delta } = view;
  const deltaPts = delta != null ? Math.round(delta * 100) : null;
  return (
    <>
      <CardHeader
        team={team}
        heading={`Your week · Week ${view.currentWeek}`}
        colors={colors}
        onChangeTeam={onChangeTeam}
      />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <Tile
          label="Last week"
          value={
            g ? (
              <>
                <ResultLetter r={g.result} /> {fmtPts(g.points)}
              </>
            ) : (
              '—'
            )
          }
          sub={
            g
              ? `vs ${fmtPts(g.oppPoints)} · ${
                  g.result === 'W' ? 'won' : g.result === 'L' ? 'lost' : 'tied'
                }${g.result === 'T' ? '' : ` by ${fmtPts(Math.abs(g.margin))}`}`
              : view.lastWeek == null
                ? 'No games played yet'
                : 'Bye'
          }
          to="/matchups"
        />
        <Tile
          label="Record"
          value={record(team)}
          sub={`${ordinal(team.rank)} · ${fmtPf(team.pf)} PF`}
          to="/standings"
        />
        <Tile
          label="Playoff odds"
          value={fmtPct(view.playoffOdds)}
          sub={
            deltaPts == null
              ? 'Change not available yet'
              : deltaPts > 0
                ? `▲ ${deltaPts} pts since last week`
                : deltaPts < 0
                  ? `▼ ${-deltaPts} pts since last week`
                  : 'No change since last week'
          }
          subTone={
            deltaPts == null || deltaPts === 0
              ? 'muted'
              : deltaPts > 0
                ? 'up'
                : 'down'
          }
          to="/playoff_bracket"
        />
        {efficiencyTile(view)}
      </div>
      <MatchupPanel team={team} matchup={view.matchup} colors={colors} />
    </>
  );
}

function OffseasonCard({
  view,
  colors,
  onChangeTeam,
}: {
  view: OffseasonView;
  colors: Map<string, string>;
  onChangeTeam: () => void;
}) {
  const { team } = view;
  return (
    <>
      <CardHeader
        team={team}
        heading={`Final result · ${view.season} season`}
        colors={colors}
        onChangeTeam={onChangeTeam}
      />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <Tile
          label="Final record"
          value={record(team)}
          sub={`${fmtPf(team.pf)} PF | ${fmtPf(team.pa)} PA`}
          to="/standings"
        />
        <Tile
          label="Final standing"
          value={view.finalRank != null ? ordinal(view.finalRank) : '—'}
          sub={view.champion ? 'League champion' : undefined}
          subTone={view.champion ? 'up' : 'muted'}
          to="/manager_history"
        />
        {efficiencyTile(view)}
        <Tile
          label="Longest win streak"
          value={view.longestWinStreak}
          to="/matchups"
        />
      </div>
    </>
  );
}

function YourWeekCard({
  view,
  colors,
  onChangeTeam,
}: {
  view: MyTeamView;
  colors: Map<string, string>;
  onChangeTeam: () => void;
}) {
  return (
    <section
      aria-label="Your week"
      className="bg-card border border-border/50 rounded-xl p-4 sm:p-5 flex flex-col gap-4"
    >
      {view.kind === 'in-season' ? (
        <InSeasonCard view={view} colors={colors} onChangeTeam={onChangeTeam} />
      ) : (
        <OffseasonCard
          view={view}
          colors={colors}
          onChangeTeam={onChangeTeam}
        />
      )}
      <TopDraftPicks picks={view.topDraftPicks} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <AwardsRow view={view} />
        <EmailPlaceholderRow />
      </div>
    </section>
  );
}
