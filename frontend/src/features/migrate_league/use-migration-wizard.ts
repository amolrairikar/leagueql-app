import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { getLeague } from '@/components/api/leagues';
import {
  getYahooMembers,
  getTeams,
  migrateLeague,
  type ManagerMappingEntry,
  type TeamEntry,
} from '@/features/migrate_league/api-calls';
import {
  POLL_INITIAL_DELAY_MS,
  pollForCompletion,
  sleep,
} from '@/features/migrate_league/polling';
import {
  type NewPlatformInfo,
  type NewPlatformUser,
  type WizardStep,
} from '@/features/migrate_league/types';
import { setLeagueCookies, getLeagueCookies } from '@/lib/cookie-handler';

/** State machine for the migration wizard: step navigation, initial league load,
 * Yahoo OAuth-return resume, and the submit-then-poll flow. */
export function useMigrationWizard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const [step, setStep] = useState<WizardStep>(1);
  const [leagueName, setLeagueName] = useState('');
  const [currentManagers, setCurrentManagers] = useState<TeamEntry[]>([]);
  const [newPlatformInfo, setNewPlatformInfo] =
    useState<NewPlatformInfo | null>(null);
  const [newPlatformUsers, setNewPlatformUsers] = useState<NewPlatformUser[]>(
    [],
  );
  const [managerMapping, setManagerMapping] = useState<ManagerMappingEntry[]>(
    [],
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pollOutcome, setPollOutcome] = useState<
    'polling' | 'success' | 'failed'
  >('polling');
  const [operationId, setOperationId] = useState<string | null>(null);
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const initRef = useRef(false);
  // Set when resuming after a Yahoo OAuth round-trip so Step 2 returns prefilled.
  const [resumeDestId, setResumeDestId] = useState('');
  const [resumeNotice, setResumeNotice] = useState<string | null>(null);
  const yahooReturnRef = useRef(false);

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

  // Resume after a Yahoo OAuth round-trip (frontend/migrate-league). The callback returns to
  // this page with a platform=YAHOO marker, a yahooLinked flag, and the destination league id.
  // The source league still comes from cookies; only the Yahoo destination is reconstructed
  // here. Guarded so StrictMode's double-invoke doesn't double-fetch.
  useEffect(() => {
    if (yahooReturnRef.current) return;
    if (searchParams.get('platform') !== 'YAHOO') return;
    yahooReturnRef.current = true;

    const linked = searchParams.get('yahooLinked');
    const destId = searchParams.get('leagueId') ?? '';

    // All state updates happen inside the async callback (not the effect body) so a single
    // OAuth-return resume doesn't trip react-hooks/set-state-in-effect, mirroring init() above.
    void (async () => {
      if (linked === '1' && destId) {
        setResumeDestId(destId);
        try {
          const result = await getYahooMembers(leagueId, platform, destId);
          setNewPlatformInfo({
            newPlatform: 'YAHOO',
            newPlatformLeagueId: destId,
          });
          setNewPlatformUsers(result.data);
          setStep(3);
        } catch {
          // Link succeeded but the members fetch failed — return to Step 2 to retry.
          setResumeNotice(
            'Could not fetch that Yahoo league. Check the ID and try again.',
          );
          setStep(2);
        }
      } else if (linked === '0') {
        setResumeDestId(destId);
        setResumeNotice('Yahoo connection cancelled — try again.');
        setStep(2);
      }
    })();
  }, [leagueId, platform, searchParams]);

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
    const result = correlationId
      ? await pollForCompletion(correlationId)
      : { status: 'failed' as const };
    if (result.status === 'failed') {
      setFailureReason(result.failureReason ?? null);
    }
    setPollOutcome(result.status);

    if (result.status === 'success') {
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

  return {
    leagueId,
    platform,
    seasons,
    step,
    setStep,
    leagueName,
    currentManagers,
    newPlatformInfo,
    setNewPlatformInfo,
    newPlatformUsers,
    setNewPlatformUsers,
    managerMapping,
    setManagerMapping,
    isSubmitting,
    submitError,
    pollOutcome,
    operationId,
    failureReason,
    resumeDestId,
    resumeNotice,
    handleConfirm,
  };
}
