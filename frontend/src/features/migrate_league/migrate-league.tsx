import { AlertTriangle, HelpCircle } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { getLeague } from '@/components/api/leagues';
import { getRefreshStatus } from '@/features/connect_league/api-calls';
import {
  getEspnMembers,
  getSleeperUsers,
  getTeams,
  migrateLeague,
  type EspnMemberEntry,
  type ManagerMappingEntry,
  type SleeperUserEntry,
  type TeamEntry,
} from '@/features/migrate_league/api-calls';
import { setLeagueCookies, getLeagueCookies } from '@/lib/cookie-handler';
import type { Platform } from '@/components/api/types';

// ── Constants ─────────────────────────────────────────────────────────────────

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

const POLL_INITIAL_DELAY_MS = 5000;
const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 60000;
const MAX_CONSECUTIVE_ERRORS = 3;

// ── Types ─────────────────────────────────────────────────────────────────────

type WizardStep = 1 | 2 | 3 | 4 | 5;

interface NewPlatformInfo {
  newPlatform: 'ESPN' | 'SLEEPER';
  newPlatformLeagueId: string;
  season?: string;
  s2?: string;
  swid?: string;
}

type NewPlatformUser = EspnMemberEntry | SleeperUserEntry;

function getUserId(user: NewPlatformUser): string {
  return 'user_id' in user ? user.user_id : user.owner_id;
}

function getUserDisplayName(user: NewPlatformUser): string {
  return user.display_name || ('username' in user ? user.username : user.owner_id);
}

// ── Polling ───────────────────────────────────────────────────────────────────

async function pollForCompletion(
  leagueId: string,
  platform: Platform,
): Promise<'success' | 'failed'> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let consecutiveErrors = 0;

  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS);
    try {
      const statusData = await getRefreshStatus(leagueId, platform, 'MIGRATE');
      const { refresh_status } = statusData.data;
      consecutiveErrors = 0;
      if (refresh_status === 'COMPLETED') return 'success';
      if (refresh_status === 'FAILED') return 'failed';
    } catch {
      consecutiveErrors += 1;
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) return 'failed';
    }
  }
  return 'failed';
}

// ── Step 1: Confirm current league ───────────────────────────────────────────

function Step1({
  leagueId,
  platform,
  seasons,
  leagueName,
  onNext,
}: {
  leagueId: string;
  platform: Platform;
  seasons: string[];
  leagueName: string;
  onNext: () => void;
}) {
  const seasonRange =
    seasons.length > 0
      ? seasons.length === 1
        ? seasons[0]
        : `${seasons[0]}–${seasons[seasons.length - 1]}`
      : '—';

  return (
    <div className="flex flex-col gap-5">
      <Alert className="border-amber-500/50 bg-amber-500/10">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        <AlertTitle className="text-amber-600 dark:text-amber-400">
          Experimental Feature
        </AlertTitle>
        <AlertDescription className="text-amber-700 dark:text-amber-300">
          League migration is an experimental feature. Please review each step
          carefully before confirming. This action cannot be undone — all-time
          metrics will be recalculated to reflect the merged history.
        </AlertDescription>
      </Alert>

      <div className="flex flex-col gap-3">
        <p className="text-[13px] text-muted-foreground">
          You are migrating the following league to a new platform:
        </p>
        <div className="bg-muted/50 rounded-lg p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              League
            </span>
            <span className="text-[13px] font-medium">{leagueName}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              Current platform
            </span>
            <span className="text-[13px] font-medium">{platform}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              League ID
            </span>
            <span className="text-[13px] font-mono">{leagueId}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              Seasons
            </span>
            <span className="text-[13px] font-medium">{seasonRange}</span>
          </div>
        </div>
        <p className="text-[12px] text-muted-foreground">
          Your {platform} league data (seasons {seasonRange}) will be preserved
          after migration.
        </p>
      </div>

      <Button className="w-full cursor-pointer" onClick={onNext}>
        Continue
      </Button>
    </div>
  );
}

// ── Step 2: New platform setup ────────────────────────────────────────────────

function Step2({
  currentPlatform,
  currentLeagueId,
  currentPlatformForApi,
  onNext,
  onBack,
}: {
  currentPlatform: Platform;
  currentLeagueId: string;
  currentPlatformForApi: Platform;
  onNext: (info: NewPlatformInfo, users: NewPlatformUser[]) => void;
  onBack: () => void;
}) {
  const availablePlatforms = (['ESPN', 'SLEEPER'] as const).filter(
    (p) => p !== currentPlatform,
  );

  const [destinationPlatform, setDestinationPlatform] = useState<'ESPN' | 'SLEEPER'>(
    availablePlatforms[0],
  );
  const [newPlatformLeagueId, setNewPlatformLeagueId] = useState('');
  const [season, setSeason] = useState('');
  const [swid, setSwid] = useState('');
  const [s2, setS2] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handlePlatformChange(value: 'ESPN' | 'SLEEPER') {
    setDestinationPlatform(value);
    setNewPlatformLeagueId('');
    setSeason('');
    setSwid('');
    setS2('');
    setError(null);
  }

  async function handleNext() {
    if (!newPlatformLeagueId.trim()) {
      setError('League ID is required');
      return;
    }
    if (destinationPlatform === 'ESPN') {
      if (!season.trim()) { setError('Season is required for ESPN'); return; }
      if (!swid.trim()) { setError('SWID is required for ESPN'); return; }
      if (!s2.trim()) { setError('ESPN S2 is required for ESPN'); return; }
    }

    setLoading(true);
    setError(null);
    try {
      let users: NewPlatformUser[];
      if (destinationPlatform === 'SLEEPER') {
        users = await getSleeperUsers(newPlatformLeagueId.trim());
      } else {
        const result = await getEspnMembers(
          currentLeagueId,
          currentPlatformForApi,
          newPlatformLeagueId.trim(),
          season.trim(),
          swid.trim(),
          s2.trim(),
        );
        users = result.data;
      }

      if (users.length === 0) {
        setError('No users found for that league. Check the league ID and try again.');
        return;
      }

      onNext(
        {
          newPlatform: destinationPlatform,
          newPlatformLeagueId: newPlatformLeagueId.trim(),
          season: destinationPlatform === 'ESPN' ? season.trim() : undefined,
          s2: destinationPlatform === 'ESPN' ? s2.trim() : undefined,
          swid: destinationPlatform === 'ESPN' ? swid.trim() : undefined,
        },
        users,
      );
    } catch {
      setError('Failed to fetch users for that league. Check the ID and credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="destination-platform">Migrating to</Label>
        <Select
          value={destinationPlatform}
          onValueChange={(v) => handlePlatformChange(v as 'ESPN' | 'SLEEPER')}
        >
          <SelectTrigger id="destination-platform" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {availablePlatforms.map((p) => (
              <SelectItem key={p} value={p}>
                {p === 'ESPN' ? 'ESPN' : 'Sleeper'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-[12px] text-muted-foreground">
          Enter your new {destinationPlatform === 'ESPN' ? 'ESPN' : 'Sleeper'} league details.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="new-league-id">
          {destinationPlatform === 'ESPN' ? 'ESPN' : 'Sleeper'} League ID
        </Label>
        <Input
          id="new-league-id"
          type="text"
          placeholder={`Enter your ${destinationPlatform === 'ESPN' ? 'ESPN' : 'Sleeper'} league ID`}
          value={newPlatformLeagueId}
          onChange={(e) => setNewPlatformLeagueId(e.target.value)}
        />
      </div>

      {destinationPlatform === 'ESPN' && (
        <>
          <div className="flex flex-col gap-2">
            <Label htmlFor="espn-season">Latest Season</Label>
            <Input
              id="espn-season"
              type="text"
              placeholder="e.g. 2025"
              value={season}
              onChange={(e) => setSeason(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="espn-swid">SWID</Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-64">
                    Found in ESPN cookies under DevTools → Application →
                    Cookies → fantasy.espn.com (include the curly braces).
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Input
              id="espn-swid"
              type="text"
              placeholder="Enter your SWID"
              value={swid}
              onChange={(e) => setSwid(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="espn-s2">ESPN S2</Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-64">
                    Found in ESPN cookies under DevTools → Application →
                    Cookies → fantasy.espn.com (espn_s2 value).
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Input
              id="espn-s2"
              type="text"
              placeholder="Enter your ESPN S2"
              value={s2}
              onChange={(e) => setS2(e.target.value)}
            />
          </div>
        </>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1 cursor-pointer"
          onClick={onBack}
          disabled={loading}
        >
          Back
        </Button>
        <Button
          className="flex-1 cursor-pointer"
          onClick={() => void handleNext()}
          disabled={loading}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Spinner className="text-primary-foreground" />
              Fetching users…
            </span>
          ) : (
            'Next'
          )}
        </Button>
      </div>
    </div>
  );
}

// ── Step 3: Map managers ──────────────────────────────────────────────────────

const NOT_RETURNING = '__not_returning__';

function Step3({
  currentManagers,
  newPlatformUsers,
  newPlatform,
  onNext,
  onBack,
}: {
  currentManagers: TeamEntry[];
  newPlatformUsers: NewPlatformUser[];
  newPlatform: 'ESPN' | 'SLEEPER';
  onNext: (mapping: ManagerMappingEntry[]) => void;
  onBack: () => void;
}) {
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);

  const selectedValues = Object.values(selections).filter(
    (v) => v && v !== NOT_RETURNING,
  );
  const hasDuplicates =
    new Set(selectedValues).size !== selectedValues.length;

  function handleChange(ownerId: string, newUserId: string) {
    setSelections((prev) => ({ ...prev, [ownerId]: newUserId }));
    setValidationError(null);
  }

  function handleNext() {
    const mapped = Object.entries(selections).filter(
      ([, v]) => v && v !== NOT_RETURNING,
    );
    if (mapped.length === 0) {
      setValidationError('At least one manager must be mapped.');
      return;
    }
    if (hasDuplicates) {
      setValidationError('Each new platform user can only be mapped once.');
      return;
    }

    const mapping: ManagerMappingEntry[] = mapped.map(
      ([currentOwnerId, newOwnerId]) => {
        const user = newPlatformUsers.find(
          (u) => getUserId(u) === newOwnerId,
        );
        const mgr = currentManagers.find(
          (m) => m.primary_owner_id === currentOwnerId,
        );
        return {
          currentPlatformOwnerId: currentOwnerId,
          newPlatformOwnerId: newOwnerId,
          displayName: user ? getUserDisplayName(user) : mgr?.display_name ?? currentOwnerId,
        };
      },
    );
    onNext(mapping);
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-[13px] font-medium mb-1">Map managers</p>
        <p className="text-[12px] text-muted-foreground">
          Match each current manager to their {newPlatform === 'ESPN' ? 'ESPN' : 'Sleeper'} account. Leave
          managers who left the league as "Not returning".
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 text-[11px] font-medium uppercase tracking-wide text-muted-foreground px-1">
        <span>Current manager</span>
        <span>{newPlatform === 'ESPN' ? 'ESPN' : 'Sleeper'} account</span>
      </div>

      <div className="flex flex-col gap-2 overflow-y-auto max-h-64 pr-1">
        {currentManagers.map((mgr) => {
          const selected = selections[mgr.primary_owner_id] ?? '';
          const isDuplicate =
            selected &&
            selected !== NOT_RETURNING &&
            selectedValues.filter((v) => v === selected).length > 1;

          return (
            <div
              key={mgr.primary_owner_id}
              className="grid grid-cols-2 gap-3 items-center"
            >
              <div className="flex flex-col">
                <span className="text-[13px] font-medium">
                  {mgr.display_name}
                </span>
              </div>
              <Select
                value={selected}
                onValueChange={(v) => handleChange(mgr.primary_owner_id, v)}
              >
                <SelectTrigger
                  className={`text-[13px] ${isDuplicate ? 'border-destructive' : ''}`}
                >
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NOT_RETURNING}>
                    Not returning
                  </SelectItem>
                  {newPlatformUsers.map((user) => (
                    <SelectItem key={getUserId(user)} value={getUserId(user)}>
                      {getUserDisplayName(user)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        })}
      </div>

      {(validationError ?? (hasDuplicates && 'Each new platform user can only be mapped once.')) && (
        <p className="text-sm text-destructive">
          {validationError ?? 'Each new platform user can only be mapped once.'}
        </p>
      )}

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1 cursor-pointer"
          onClick={onBack}
        >
          Back
        </Button>
        <Button
          className="flex-1 cursor-pointer"
          onClick={handleNext}
          disabled={hasDuplicates}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

// ── Step 4: Preview & confirm ─────────────────────────────────────────────────

function Step4({
  currentSeasons,
  newPlatform,
  newPlatformLeagueId,
  newSeason,
  totalManagers,
  mappedManagers,
  isSubmitting,
  submitError,
  onConfirm,
  onBack,
}: {
  currentSeasons: string[];
  newPlatform: 'ESPN' | 'SLEEPER';
  newPlatformLeagueId: string;
  newSeason?: string;
  totalManagers: number;
  mappedManagers: number;
  isSubmitting: boolean;
  submitError: string | null;
  onConfirm: () => void;
  onBack: () => void;
}) {
  const seasonRange =
    currentSeasons.length > 0
      ? `${currentSeasons[0]}–${currentSeasons[currentSeasons.length - 1]}`
      : '—';

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-[13px] font-medium mb-1">Review migration</p>
        <p className="text-[12px] text-muted-foreground">
          Confirm the details below before starting the migration.
        </p>
      </div>

      <div className="bg-muted/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            Current seasons
          </span>
          <span className="text-[13px] font-medium">{seasonRange}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            New platform
          </span>
          <span className="text-[13px] font-medium">{newPlatform}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            New league ID
          </span>
          <span className="text-[13px] font-mono">{newPlatformLeagueId}</span>
        </div>
        {newSeason && (
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              New season
            </span>
            <span className="text-[13px] font-medium">{newSeason}</span>
          </div>
        )}
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            Managers mapped
          </span>
          <span className="text-[13px] font-medium">
            {mappedManagers} of {totalManagers}
          </span>
        </div>
      </div>

      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="text-[12px]">
          This action cannot be undone. All-time metrics will be recalculated
          to reflect the merged history.
        </AlertDescription>
      </Alert>

      {submitError && (
        <p className="text-sm text-destructive">{submitError}</p>
      )}

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1 cursor-pointer"
          onClick={onBack}
          disabled={isSubmitting}
        >
          Back
        </Button>
        <Button
          className="flex-1 cursor-pointer"
          onClick={onConfirm}
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <Spinner className="text-primary-foreground" />
              Starting migration…
            </span>
          ) : (
            'Confirm Migration'
          )}
        </Button>
      </div>
    </div>
  );
}

// ── Step 5: Processing ────────────────────────────────────────────────────────

function Step5({
  pollOutcome,
  operationId,
}: {
  pollOutcome: 'polling' | 'success' | 'failed';
  operationId: string | null;
}) {
  if (pollOutcome === 'polling') {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        <Spinner className="size-8 text-primary" />
        <p className="text-[13px] text-muted-foreground text-center">
          Migration in progress. This may take up to a minute…
        </p>
      </div>
    );
  }

  if (pollOutcome === 'success') {
    return (
      <Alert className="border-primary bg-primary/10">
        <AlertTitle className="text-primary">Migration complete</AlertTitle>
        <AlertDescription>
          Your league has been successfully migrated. Redirecting to your
          dashboard…
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert variant="destructive">
      <AlertTitle>Migration failed</AlertTitle>
      <AlertDescription>
        The migration did not complete successfully. Please try again or contact
        support{operationId ? ` with operation ID ${operationId}` : ''}.
      </AlertDescription>
    </Alert>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function MigrateLeague() {
  const navigate = useNavigate();
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const [step, setStep] = useState<WizardStep>(1);
  const [leagueName, setLeagueName] = useState('');
  const [currentManagers, setCurrentManagers] = useState<TeamEntry[]>([]);
  const [newPlatformInfo, setNewPlatformInfo] = useState<NewPlatformInfo | null>(null);
  const [newPlatformUsers, setNewPlatformUsers] = useState<NewPlatformUser[]>([]);
  const [managerMapping, setManagerMapping] = useState<ManagerMappingEntry[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pollOutcome, setPollOutcome] = useState<'polling' | 'success' | 'failed'>('polling');
  const [operationId, setOperationId] = useState<string | null>(null);
  const initRef = useRef(false);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    async function init() {
      try {
        const [leagueResult, teamsResult] = await Promise.all([
          getLeague(leagueId, platform),
          getTeams(leagueId, platform),
        ]);
        setLeagueName(leagueResult.data.league_name ?? leagueId);

        const mostRecentSeason =
          seasons.length > 0 ? [...seasons].sort().at(-1)! : '';
        const filtered = teamsResult.data.filter(
          (t) => t.season === mostRecentSeason,
        );
        const deduped = Array.from(
          new Map(filtered.map((t) => [t.primary_owner_id, t])).values(),
        );
        setCurrentManagers(deduped);
      } catch {
        setLeagueName(leagueId);
      }
    }

    void init();
  }, [leagueId, platform, seasons]);

  async function handleConfirm() {
    if (!newPlatformInfo) return;
    setIsSubmitting(true);
    setSubmitError(null);

    let correlationId: string | null = null;
    try {
      const result = await migrateLeague(leagueId, platform, {
        newPlatformLeagueId: newPlatformInfo.newPlatformLeagueId,
        newPlatform: newPlatformInfo.newPlatform,
        season: newPlatformInfo.season,
        s2: newPlatformInfo.s2,
        swid: newPlatformInfo.swid,
        managerMapping,
      });
      correlationId = result.data.correlation_id;
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : 'Failed to start migration.',
      );
      setIsSubmitting(false);
      return;
    }

    setIsSubmitting(false);
    setStep(5);
    setOperationId(correlationId);

    await sleep(POLL_INITIAL_DELAY_MS);
    const outcome = await pollForCompletion(
      leagueId,
      platform,
    );
    setPollOutcome(outcome);

    if (outcome === 'success') {
      try {
        const newLeagueData = await getLeague(
          newPlatformInfo.newPlatformLeagueId,
          newPlatformInfo.newPlatform,
        );
        setLeagueCookies(
          newPlatformInfo.newPlatformLeagueId,
          newPlatformInfo.newPlatform,
          newLeagueData.data.seasons,
        );
      } catch {
        // cookies will be stale but we still navigate
      }
      await sleep(1500);
      void navigate('/home');
    }
  }

  const stepTitles: Record<WizardStep, string> = {
    1: 'Confirm Current League',
    2: 'New Platform Setup',
    3: 'Map Managers',
    4: 'Preview & Confirm',
    5: 'Migrating…',
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden">
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(var(--border) 1px, transparent 1px),
            linear-gradient(90deg, var(--border) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          opacity: 0.2,
        }}
      />

      <div className="relative z-10 flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <div className="flex items-center gap-2 mb-1">
              {([1, 2, 3, 4] as WizardStep[]).map((s) => (
                <div
                  key={s}
                  className={`h-1 flex-1 rounded-full transition-colors ${
                    s <= step ? 'bg-primary' : 'bg-muted'
                  }`}
                />
              ))}
            </div>
            <CardTitle className="text-xl text-center font-bold">
              {stepTitles[step]}
            </CardTitle>
            {step < 5 && (
              <p className="text-[12px] text-center text-muted-foreground">
                Step {step} of 4
              </p>
            )}
          </CardHeader>
          <CardContent>
            {step === 1 && (
              <Step1
                leagueId={leagueId}
                platform={platform}
                seasons={seasons}
                leagueName={leagueName}
                onNext={() => setStep(2)}
              />
            )}
            {step === 2 && (
              <Step2
                currentPlatform={platform}
                currentLeagueId={leagueId}
                currentPlatformForApi={platform}
                onNext={(info, users) => {
                  setNewPlatformInfo(info);
                  setNewPlatformUsers(users);
                  setStep(3);
                }}
                onBack={() => setStep(1)}
              />
            )}
            {step === 3 && newPlatformInfo && (
              <Step3
                currentManagers={currentManagers}
                newPlatformUsers={newPlatformUsers}
                newPlatform={newPlatformInfo.newPlatform}
                onNext={(mapping) => {
                  setManagerMapping(mapping);
                  setStep(4);
                }}
                onBack={() => setStep(2)}
              />
            )}
            {step === 4 && newPlatformInfo && (
              <Step4
                currentSeasons={seasons}
                newPlatform={newPlatformInfo.newPlatform}
                newPlatformLeagueId={newPlatformInfo.newPlatformLeagueId}
                newSeason={newPlatformInfo.season}
                totalManagers={currentManagers.length}
                mappedManagers={managerMapping.length}
                isSubmitting={isSubmitting}
                submitError={submitError}
                onConfirm={() => void handleConfirm()}
                onBack={() => setStep(3)}
              />
            )}
            {step === 5 && (
              <Step5
                pollOutcome={pollOutcome}
                operationId={operationId}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
