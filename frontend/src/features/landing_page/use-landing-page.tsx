import { useUser } from '@clerk/react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { getLeague, getMyLeagues } from '@/components/api/leagues';
import type { MyLeague } from '@/components/api/types';
import {
  getYahooAuthorizeUrl,
  onboardLeague,
  onboardYahooLeague,
} from '@/features/connect_league/api-calls';
import { pollForCompletion } from '@/features/connect_league/poll';
import { getLeagueCount } from '@/features/landing_page/api-calls';
import { MY_LEAGUES_FALLBACK } from '@/features/landing_page/constants';
import { computeLoadingState } from '@/features/landing_page/loading-state';
import { API_BASE_URL, ApiError, clearApiCache } from '@/lib/api-client';
import {
  clearAllLeagueCookies,
  clearEspnCookies,
  isDemoMode,
  type Platform,
  setDemoMode,
  setLeagueCookies,
} from '@/lib/cookie-handler';
import { DEMO_SEASONS } from '@/lib/demo-constants';
import { toResult, type Result } from '@/lib/result';
import { getCurrentNflSeason } from '@/lib/season';

// A linked Yahoo onboard whose stored refresh token was revoked surfaces as a
// FAILED job carrying this code (backend/yahoo-oauth); the UI restarts the OAuth
// (re)link rather than showing a generic failure.
const YAHOO_AUTH_CODE = 'YAHOO_AUTH';

// The generic inline message shown when connecting a league fails for an
// infrastructure reason (network / 5xx) rather than a bad league id.
const GENERIC_CONNECT_ERROR = (
  <>
    Something went wrong connecting your league. Please try again. If the error
    persists, contact{' '}
    <a
      href="mailto:support@leagueql.com"
      className="underline underline-offset-4"
    >
      support
    </a>
    .
  </>
);

export function useLandingPage() {
  const { isSignedIn } = useUser();
  const navigate = useNavigate();
  const [authOpen, setAuthOpen] = useState(false);
  const [showConnectForm, setShowConnectForm] = useState(false);
  // Signed-in "View My Leagues" panel (frontend/landing-page). Mutually exclusive with the
  // Connect form. The list is requested on first expand and held as a never-rejecting
  // promise the panel reads with `use()`; the count feeds the button's pill.
  const [showMyLeagues, setShowMyLeagues] = useState(false);
  const [myLeagues, setMyLeagues] = useState<Promise<
    Result<MyLeague[]>
  > | null>(null);
  const [myLeaguesCount, setMyLeaguesCount] = useState<number | null>(null);
  const [platform, setPlatform] = useState<Platform>('ESPN');
  // ESPN private-league credentials entered inline (only sent when onboarding a
  // not-yet-onboarded league). Held in React state, never browser storage;
  // cleared on success (frontend/landing-page, backend/espn-credential-storage).
  const [espnSwid, setEspnSwid] = useState('');
  const [espnS2, setEspnS2] = useState('');
  // ESPN auto-refresh opt-in (default off), parity with the /connect_league onboard.
  const [espnAutoRefresh, setEspnAutoRefresh] = useState(false);
  // Gate for the ESPN credential block: the SWID/espn_s2 inputs, cookie helper, and
  // auto-refresh checkbox stay hidden until a Connect lookup shows the league isn't
  // onboarded yet (getLeague → 404). Reset whenever the league ID or platform changes
  // so a new ID re-runs the lookup gate (frontend/landing-page).
  const [needsEspnCredentials, setNeedsEspnCredentials] = useState(false);
  const [leagueId, setLeagueId] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<ReactNode>(null);
  const [leagueCount, setLeagueCount] = useState<number | null>(null);
  const loadingStartRef = useRef<number | null>(null);
  const loadingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  // Guards the Yahoo OAuth-return resume against a StrictMode double-invoke.
  const yahooReturnRef = useRef(false);
  // Removes the consent-popup message listener + poll if the page unmounts mid-consent.
  const popupCleanupRef = useRef<(() => void) | null>(null);

  // Reaching the landing page is a demo-mode exit path. The landing page is never
  // part of the demo experience, so any of the ways a user can arrive here — the
  // "LeagueQL" header link, the browser back button, or a direct visit — should
  // clear lingering demo state. Otherwise the 24h `demo_mode` cookie survives and
  // a subsequently connected live league is served demo fixtures / bypasses auth
  // (frontend/demo-mode). Only the dedicated "Exit Demo" button previously did this cleanup.
  useEffect(() => {
    if (isDemoMode()) clearAllLeagueCookies();
  }, []);

  // If the page unmounts while a Yahoo consent popup is still open, drop its message
  // listener + poll so nothing lingers (frontend/connect-yahoo-league).
  useEffect(() => () => popupCleanupRef.current?.(), []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('connect') === 'true' && isSignedIn) {
      // Reveal the connect form on return from Clerk sign-in (?connect=true).
      // This must react to isSignedIn resolving asynchronously, so the state
      // update legitimately belongs in this effect.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setShowConnectForm(true);
    }
  }, [isSignedIn]);

  // Resume the Yahoo OAuth return inline (frontend/connect-yahoo-league,
  // frontend/landing-page). Yahoo's consent flow redirects the browser back to `/` carrying
  // a YAHOO platform marker, a linked flag, and the pending league id; pick those up here so
  // onboarding finishes with the same inline progress UI as ESPN/Sleeper instead of on a
  // separate page. Gated on isSignedIn (the caller returns still signed in) and guarded
  // against a StrictMode double-invoke.
  useEffect(() => {
    if (yahooReturnRef.current) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('platform')?.toUpperCase() !== 'YAHOO') return;
    if (!isSignedIn) return;
    yahooReturnRef.current = true;

    const linked = params.get('yahooLinked') === '1';
    const returnedLeagueId = params.get('leagueId') ?? '';
    // Consume the return params so a reload doesn't re-trigger onboarding.
    try {
      window.history.replaceState(null, '', window.location.pathname);
    } catch {
      // History unavailable — the guard ref still prevents an in-session re-run.
    }

    // All state updates happen inside the async callback (not the effect body) so this
    // resume doesn't trip react-hooks/set-state-in-effect, mirroring migrate-league.
    void (async () => {
      setPlatform('YAHOO');
      setShowConnectForm(true);
      if (linked && returnedLeagueId) {
        setLeagueId(returnedLeagueId);
        setError(null);
        setLoading(true);
        // Reuse the already-linked onboard chain (poll + progress bar + revoked-link
        // recovery).
        await handleYahooConnect(returnedLeagueId);
      } else {
        // A declined/failed link (yahooLinked=0), or a linked return with no league id
        // to resume — show the inline retry alert with Yahoo preselected.
        setError('Yahoo linking was cancelled or failed — try again.');
      }
    })();
    // handleYahooConnect is a stable-enough closure for this once-per-return resume; the
    // ref guard makes the effect run at most once, so we intentionally key only on sign-in.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSignedIn]);

  useEffect(() => {
    void getLeagueCount().then((count) => {
      if (count !== null) setLeagueCount(count);
    });
  }, []);

  useEffect(() => {
    if (loading) {
      loadingStartRef.current = Date.now();
      const initial = computeLoadingState(0);
      // Seed the progress UI the moment a load starts; the interval below drives
      // subsequent ticks. The effect synchronizes with a timer (an external
      // system), so seeding state here is intentional.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoadingMessage(initial.message);
      setProgress(initial.progress);
      loadingIntervalRef.current = setInterval(() => {
        const elapsed = (Date.now() - loadingStartRef.current!) / 1000;
        const { message, progress: p } = computeLoadingState(elapsed);
        setLoadingMessage(message);
        setProgress(p);
      }, 200);
    } else {
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
        loadingIntervalRef.current = null;
      }
      loadingStartRef.current = null;
      setLoadingMessage('');
      setProgress(0);
    }
    return () => {
      if (loadingIntervalRef.current) clearInterval(loadingIntervalRef.current);
    };
  }, [loading]);

  function handleConnectLeague() {
    if (isSignedIn) {
      setShowMyLeagues(false);
      setShowConnectForm(true);
    } else {
      setAuthOpen(true);
    }
  }

  function loadMyLeagues() {
    const request = toResult(
      getMyLeagues().then((r) => r.data),
      MY_LEAGUES_FALLBACK,
    );
    setMyLeagues(request);
    setMyLeaguesCount(null);
    void request.then((r) => setMyLeaguesCount(r.ok ? r.data.length : null));
  }

  function handleToggleMyLeagues() {
    if (showMyLeagues) {
      setShowMyLeagues(false);
      return;
    }
    setShowConnectForm(false);
    setShowMyLeagues(true);
    if (!myLeagues) loadMyLeagues();
  }

  function handleViewDemo() {
    setDemoMode(DEMO_SEASONS);
    void navigate('/home');
  }

  // Hand off to Yahoo's consent screen in a popup (backend/yahoo-oauth), carrying the league
  // id so onboarding can resume when the popup reports back. Keeping consent in a popup lets
  // this page stay mounted with its progress bar — no jarring mid-onboard reload. `loading`
  // stays set while the popup is open; the postMessage handler resumes onboarding, and only a
  // failure to start (or a dismissed/declined popup) clears it. If the browser blocks the
  // popup we fall back to a full-page redirect (the callback page self-redirects with no opener).
  async function startYahooOauth(trimmedId: string) {
    try {
      const { data } = await getYahooAuthorizeUrl(
        trimmedId,
        'ONBOARD',
        'popup',
      );
      const popup = window.open(
        data.authorize_url,
        'yahoo-oauth',
        'width=600,height=760',
      );
      if (!popup) {
        window.location.href = data.authorize_url;
        return;
      }
      listenForYahooPopup(popup);
    } catch {
      setError('Could not start Yahoo sign-in. Please try again.');
      setLoading(false);
    }
  }

  // Wait for the Yahoo consent popup to report its result (backend/yahoo-oauth) and resume
  // onboarding inline. The popup document is served by the API origin, so a message is trusted
  // only when it comes from that origin and carries our own {source:'yahoo-oauth'} shape. A
  // poll on `popup.closed` covers the user dismissing the window; a short grace period avoids
  // racing a success message that was posted just before the popup closed itself.
  function listenForYahooPopup(popup: Window) {
    const apiOrigin = new URL(API_BASE_URL).origin;
    let settled = false;

    const onMessage = (event: MessageEvent) => {
      if (event.origin !== apiOrigin) return;
      const msg = event.data as {
        source?: string;
        yahooLinked?: string;
        leagueId?: string;
      } | null;
      if (msg?.source !== 'yahoo-oauth') return;
      settled = true;
      popupCleanupRef.current?.();
      try {
        popup.close();
      } catch {
        // A cross-origin popup may already be closing — ignore.
      }
      if (msg.yahooLinked === '1' && msg.leagueId) {
        void handleYahooConnect(msg.leagueId);
      } else {
        setError('Yahoo linking was cancelled or failed — try again.');
        setLoading(false);
      }
    };

    const closedTimer = setInterval(() => {
      if (!popup.closed || settled) return;
      clearInterval(closedTimer);
      // The success message (posted just before the popup self-closed) may still be in
      // flight — wait briefly before treating a closed popup as a cancel.
      setTimeout(() => {
        if (settled) return;
        popupCleanupRef.current?.();
        setError('Yahoo linking was cancelled — try again.');
        setLoading(false);
      }, 400);
    }, 500);

    window.addEventListener('message', onMessage);
    popupCleanupRef.current = () => {
      window.removeEventListener('message', onMessage);
      clearInterval(closedTimer);
      popupCleanupRef.current = null;
    };
  }

  // Connect a Yahoo league. An already-linked caller onboards in place with the same
  // progress UI as Sleeper (no consent round-trip); only an unlinked caller is sent to
  // Yahoo's consent screen. POST /leagues 403-gates unlinked callers before any side
  // effect (backend/yahoo-oauth), so we optimistically onboard first and treat a 403 as
  // "not linked". A revoked-token link passes the gate but fails the job with YAHOO_AUTH.
  // No auto-refresh opt-in: Yahoo leagues are always auto-refreshed in season.
  async function handleYahooConnect(trimmedId: string) {
    try {
      const onboardResult = await onboardYahooLeague(trimmedId);
      // A fresh onboard returns a correlation_id to poll; an already-onboarded league
      // returns 200 with null `data`, which skips straight to routing the user in.
      if (onboardResult.data) {
        const result = await pollForCompletion(
          onboardResult.data.correlation_id,
        );
        if (result.status === 'failed') {
          if (result.failureCode === YAHOO_AUTH_CODE) {
            await startYahooOauth(trimmedId);
            return;
          }
          setError(result.failureReason ?? GENERIC_CONNECT_ERROR);
          setLoading(false);
          return;
        }
      }
      // Onboarding wrote new precomputed views; drop cached reads before re-reading.
      clearApiCache();
      const leagueData = await getLeague(trimmedId, 'YAHOO');
      setLeagueCookies(trimmedId, 'YAHOO', leagueData.data.seasons);
      void navigate('/home');
    } catch (err) {
      // 403 "Link your Yahoo account first" means the caller has no stored link — hand
      // off to the OAuth consent screen (the only path that shows it now).
      if (err instanceof ApiError && err.status === 403) {
        await startYahooOauth(trimmedId);
        return;
      }
      setError(GENERIC_CONNECT_ERROR);
      setLoading(false);
    }
  }

  async function handleConnectSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!leagueId.trim() || loading) return;

    setLoading(true);
    setError(null);

    if (platform === 'YAHOO') {
      await handleYahooConnect(leagueId.trim());
      return;
    }

    try {
      const leagueData = await getLeague(leagueId.trim(), platform);
      setLeagueCookies(leagueId.trim(), platform, leagueData.data.seasons);
      void navigate('/home');
    } catch (err) {
      const status = err instanceof ApiError ? err.status : null;
      if (platform === 'ESPN' && status === 404) {
        // Not onboarded yet — onboard in place with the inline ESPN credentials
        // (no redirect to /connect_league). The season is derived automatically
        // (Sleeper NFL state, clock fallback), never entered by the user.
        const swidTrim = espnSwid.trim();
        const s2Trim = espnS2.trim();
        if (!swidTrim || !s2Trim) {
          if (!needsEspnCredentials) {
            // First lookup for this league: reveal the credential fields so the
            // user can enter the owner's cookies, then click Connect again to
            // onboard. No POST /leagues is sent on this pass.
            setNeedsEspnCredentials(true);
          } else {
            // Fields are already shown but were left empty — SWID/espn_s2 are
            // required to onboard a private ESPN league.
            setError(
              'Enter your SWID and espn_s2 to connect a private ESPN league.',
            );
          }
          setLoading(false);
          return;
        }
        try {
          const season = await getCurrentNflSeason();
          const onboardResult = await onboardLeague('ONBOARD', {
            leagueId: leagueId.trim(),
            platform: 'ESPN',
            season,
            s2: s2Trim,
            swid: swidTrim,
            autoRefresh: espnAutoRefresh,
          });
          const result = await pollForCompletion(
            onboardResult.data.correlation_id,
          );
          if (result.status === 'success') {
            // Transmitted once over HTTPS; clear them from the browser and state.
            clearEspnCookies();
            setEspnSwid('');
            setEspnS2('');
            clearApiCache();
            const leagueData = await getLeague(leagueId.trim(), 'ESPN');
            setLeagueCookies(leagueId.trim(), 'ESPN', leagueData.data.seasons);
            void navigate('/home');
          } else if (result.failureReason) {
            setError(result.failureReason);
          } else {
            setError(
              <>
                League onboarding failed. Please try again. If the error
                persists, contact{' '}
                <a
                  href="mailto:support@leagueql.com"
                  className="underline underline-offset-4"
                >
                  support
                </a>
                .
              </>,
            );
          }
        } catch {
          setError(
            'Failed to onboard league. Please check your league ID and try again.',
          );
        }
      } else if (platform === 'ESPN' && status === 403) {
        // Already onboarded but the caller isn't a member of this private ESPN
        // league yet. Membership now comes from an owner-shared invite link, so
        // point them there rather than the (confusing) onboard form
        // (backend/league-authorization / frontend/ownership-transfer).
        setError(
          'League already onboarded. Please reach out to your leaguemate who ' +
            'onboarded the league to get your league-specific invite link.',
        );
      } else if (platform === 'SLEEPER' && status === 404) {
        try {
          const onboardResult = await onboardLeague('ONBOARD', {
            leagueId: leagueId.trim(),
            platform: 'SLEEPER',
          });
          const result = await pollForCompletion(
            onboardResult.data.correlation_id,
          );
          if (result.status === 'success') {
            const leagueData = await getLeague(leagueId.trim(), 'SLEEPER');
            setLeagueCookies(
              leagueId.trim(),
              'SLEEPER',
              leagueData.data.seasons,
            );
            void navigate('/home');
          } else if (result.failureReason) {
            setError(result.failureReason);
          } else {
            setError(
              <>
                League onboarding failed. Please try again. If the error
                persists, contact{' '}
                <a
                  href="mailto:support@leagueql.com"
                  className="underline underline-offset-4"
                >
                  support
                </a>
                .
              </>,
            );
          }
        } catch {
          setError(
            'Failed to onboard league. Please check your league ID and try again.',
          );
        }
      } else {
        // A non-404/403 lookup failure (network / 5xx) is infrastructure trouble,
        // not a bad league ID — show a generic message (matching the connect-league
        // form) rather than the rarely-actionable backend detail.
        setError(GENERIC_CONNECT_ERROR);
      }
    } finally {
      setLoading(false);
    }
  }

  return {
    isSignedIn,
    authOpen,
    setAuthOpen,
    showConnectForm,
    showMyLeagues,
    myLeagues,
    myLeaguesCount,
    platform,
    setPlatform,
    espnSwid,
    setEspnSwid,
    espnS2,
    setEspnS2,
    espnAutoRefresh,
    setEspnAutoRefresh,
    needsEspnCredentials,
    setNeedsEspnCredentials,
    leagueId,
    setLeagueId,
    loading,
    loadingMessage,
    progress,
    error,
    setError,
    leagueCount,
    handleConnectLeague,
    loadMyLeagues,
    handleToggleMyLeagues,
    handleViewDemo,
    handleConnectSubmit,
  };
}

export type LandingState = ReturnType<typeof useLandingPage>;
