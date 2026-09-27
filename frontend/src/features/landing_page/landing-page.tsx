import { SignIn, useUser } from '@clerk/react';
import { ArrowRight, ChevronRight, HelpCircle } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { getLeague } from '@/components/api/leagues';
import Footer from '@/components/footer';
import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
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
import {
  getYahooAuthorizeUrl,
  onboardLeague,
  onboardYahooLeague,
} from '@/features/connect_league/api-calls';
import { EspnCredentialFields } from '@/features/connect_league/espn-credential-fields';
import { pollForCompletion } from '@/features/connect_league/poll';
import {
  setYahooAutoRefreshPref,
  takeYahooAutoRefreshPref,
} from '@/features/connect_league/yahoo-auto-refresh-pref';
import {
  FEATURES,
  HOW_STEPS,
  PLATFORMS,
} from '@/features/landing_page/constants';
import { Faq } from '@/features/landing_page/faq';
import { ProductShowcase } from '@/features/landing_page/product-showcase';
import type { Feature, HowStep } from '@/features/landing_page/types';
import { API_BASE_URL, ApiError, clearApiCache } from '@/lib/api-client';
import {
  clearAllLeagueCookies,
  clearEspnCookies,
  isDemoMode,
  isPlatform,
  type Platform,
  setDemoMode,
  setLeagueCookies,
} from '@/lib/cookie-handler';
import { DEMO_SEASONS } from '@/lib/demo-constants';
import { getCurrentNflSeason } from '@/lib/season';

const LOADING_PHASES = [
  { upToSeconds: 10, toProgress: 33, message: "Fetching your league's data" },
  { upToSeconds: 25, toProgress: 66, message: 'Calculating' },
  {
    upToSeconds: 45,
    toProgress: 90,
    message: 'Creating your league dashboard',
  },
];

function computeLoadingState(elapsedSeconds: number): {
  message: string;
  progress: number;
} {
  let from = 0;
  let fromSeconds = 0;
  for (const phase of LOADING_PHASES) {
    if (elapsedSeconds < phase.upToSeconds) {
      const phaseDuration = phase.upToSeconds - fromSeconds;
      const phaseElapsed = elapsedSeconds - fromSeconds;
      const progress =
        from + (phaseElapsed / phaseDuration) * (phase.toProgress - from);
      return { message: phase.message, progress };
    }
    from = phase.toProgress;
    fromSeconds = phase.upToSeconds;
  }
  return {
    message: LOADING_PHASES[LOADING_PHASES.length - 1].message,
    progress: 90,
  };
}

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

function FeatureCard({ icon: Icon, title, desc }: Feature) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-xs transition-all duration-200 hover:-translate-y-1 hover:border-primary/35 hover:shadow-lg">
      <div className="mb-4 grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">
        <Icon className="size-5.5" />
      </div>
      <h3 className="font-heading text-foreground mb-2 text-base font-semibold">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

function Step({ step, isLast }: { step: HowStep; isLast: boolean }) {
  const { icon: Icon } = step;
  return (
    <div className="relative z-10 rounded-2xl border border-border bg-card p-7">
      <div className="mb-4.5 flex items-center gap-3">
        <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-5.5" />
        </div>
        <span className="font-mono text-xs font-semibold tracking-wider text-primary">
          {step.step}
        </span>
      </div>
      <h3 className="font-heading mb-2 text-base font-semibold text-foreground">
        {step.title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">
        {step.desc}
      </p>
      {!isLast && (
        <div
          aria-hidden
          className="absolute top-1/2 -right-[41px] z-20 hidden size-[30px] -translate-y-1/2 place-items-center rounded-full border border-border bg-card text-primary shadow-sm md:grid"
        >
          <ChevronRight className="size-4" />
        </div>
      )}
    </div>
  );
}

export default function LeagueQLLanding() {
  const { isSignedIn } = useUser();
  const navigate = useNavigate();
  const [authOpen, setAuthOpen] = useState(false);
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [platform, setPlatform] = useState<Platform>('ESPN');
  // Yahoo auto-refresh opt-in (default off). Persisted before the OAuth redirect so the
  // return leg can apply it (backend/scheduled-league-auto-refresh).
  const [yahooAutoRefresh, setYahooAutoRefresh] = useState(false);
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
        // recovery), passing the opt-in stashed before the redirect.
        await handleYahooConnect(returnedLeagueId, takeYahooAutoRefreshPref());
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
    fetch('https://api.leagueql.com/counts')
      .then((r) => r.json())
      .then((d: { leagueCount: number }) => setLeagueCount(d.leagueCount))
      .catch(() => null);
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
      setShowConnectForm(true);
    } else {
      setAuthOpen(true);
    }
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
        void handleYahooConnect(msg.leagueId, takeYahooAutoRefreshPref());
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
  async function handleYahooConnect(
    trimmedId: string,
    autoRefreshOverride?: boolean,
  ) {
    // The normal submit path uses the checkbox state; the OAuth return path passes the
    // opt-in it stashed before the redirect (takeYahooAutoRefreshPref) as an override.
    const autoRefresh = autoRefreshOverride ?? yahooAutoRefresh;
    // Persist the opt-in so it survives a possible OAuth redirect, and apply it on the
    // direct (already-linked) onboard below.
    setYahooAutoRefreshPref(autoRefresh);
    try {
      const onboardResult = await onboardYahooLeague(trimmedId, autoRefresh);
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

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans overflow-x-hidden">
      {/* Decorative fixed grid + primary glow */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(var(--border) 1px, transparent 1px),
            linear-gradient(90deg, var(--border) 1px, transparent 1px)
          `,
          backgroundSize: '52px 52px',
          maskImage:
            'radial-gradient(ellipse 90% 55% at 50% 0%, #000 30%, transparent 78%)',
          WebkitMaskImage:
            'radial-gradient(ellipse 90% 55% at 50% 0%, #000 30%, transparent 78%)',
          opacity: 0.5,
        }}
      />
      <div
        className="fixed left-1/2 top-[-14%] -z-0 h-[640px] w-[820px] -translate-x-1/2 pointer-events-none blur-2xl"
        style={{
          background:
            'radial-gradient(50% 50% at 50% 50%, color-mix(in oklab, var(--chart-3) 30%, transparent) 0%, transparent 70%)',
        }}
      />

      {/* HERO */}
      <section className="relative z-10 flex flex-col items-center text-center px-6 pt-24 pb-8">
        {leagueCount !== null && (
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground animate-[fadeUp_0.6s_0.1s_both]">
            <span className="flex items-center -space-x-1">
              <span className="block size-2.5 shrink-0 rounded-full bg-red-500" />
              <span className="block size-2.5 shrink-0 rounded-full bg-green-500" />
              <span className="block size-2.5 shrink-0 rounded-full bg-blue-500" />
            </span>
            Join{' '}
            <span className="font-mono font-medium text-foreground">
              {leagueCount}
            </span>{' '}
            leagues tracking their history
          </div>
        )}

        <h1
          className="
            text-[clamp(2.6rem,6vw,4.5rem)] leading-[1.05] tracking-tight
            text-foreground max-w-175 font-heading
            animate-[fadeUp_0.6s_0.25s_both]
          "
        >
          Your league&apos;s story,{' '}
          <em className="italic text-primary">beautifully told</em>
        </h1>

        <p
          className="
          mt-5 text-base text-muted-foreground max-w-120 leading-relaxed
          animate-[fadeUp_0.6s_0.4s_both]
          "
        >
          Explore every season, rivalry, and record across your league&apos;s
          full history — from the first draft pick to the last championship.
        </p>

        <div className="flex gap-3 mt-9 animate-[fadeUp_0.6s_0.55s_both]">
          <Button
            size="lg"
            className="text-[0.82rem] px-6 cursor-pointer"
            onClick={handleConnectLeague}
          >
            Connect Your League <ArrowRight />
          </Button>

          <Button
            variant="outline"
            size="lg"
            className="text-[0.82rem] px-6 cursor-pointer"
            onClick={handleViewDemo}
          >
            View Demo
          </Button>
        </div>

        {showConnectForm && (
          <div className="mt-8 w-full max-w-lg animate-[fadeUp_0.4s_both]">
            <form
              className="flex gap-2"
              onSubmit={(e) => void handleConnectSubmit(e)}
            >
              <Select
                value={platform}
                onValueChange={(v) => {
                  if (isPlatform(v)) {
                    setPlatform(v);
                    // Switching platform re-gates the ESPN credential fields.
                    setNeedsEspnCredentials(false);
                    setError(null);
                  }
                }}
              >
                <SelectTrigger className="w-36 shrink-0">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ESPN">ESPN</SelectItem>
                  <SelectItem value="SLEEPER">Sleeper</SelectItem>
                  <SelectItem value="YAHOO">Yahoo</SelectItem>
                </SelectContent>
              </Select>
              <Input
                className="flex-1"
                placeholder="League ID"
                name="leagueId"
                autoComplete="on"
                value={leagueId}
                onChange={(e) => {
                  setLeagueId(e.target.value);
                  // A new league ID must be looked up afresh before we know
                  // whether to ask for ESPN credentials.
                  setNeedsEspnCredentials(false);
                  setError(null);
                }}
                disabled={loading}
              />
              <Button
                type="submit"
                disabled={loading || !leagueId.trim()}
                className="cursor-pointer shrink-0"
              >
                {loading ? (
                  <Spinner className="text-primary-foreground" />
                ) : (
                  'Connect'
                )}
              </Button>
            </form>
            {platform === 'ESPN' && needsEspnCredentials && (
              <div className="mt-3 flex flex-col gap-4 text-left">
                <p className="text-sm text-muted-foreground">
                  League not added to LeagueQL yet. Enter your ESPN cookies
                  below to connect.
                </p>
                <EspnCredentialFields
                  swid={espnSwid}
                  espnS2={espnS2}
                  onSwidChange={setEspnSwid}
                  onEspnS2Change={setEspnS2}
                  onAutofill={(nextSwid, nextEspnS2) => {
                    setEspnSwid(nextSwid);
                    setEspnS2(nextEspnS2);
                  }}
                  disabled={loading}
                  showManualInstructions={false}
                />
                <div className="flex items-center gap-2">
                  <input
                    id="espn-auto-refresh"
                    type="checkbox"
                    className="size-4 cursor-pointer accent-primary"
                    checked={espnAutoRefresh}
                    onChange={(e) => setEspnAutoRefresh(e.target.checked)}
                    disabled={loading}
                  />
                  <div className="flex items-center gap-1.5">
                    <Label
                      htmlFor="espn-auto-refresh"
                      className="cursor-pointer"
                    >
                      Enable automatic weekly refresh
                    </Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="right" className="max-w-64">
                          When enabled, LeagueQL securely stores your ESPN
                          cookies (encrypted) and refreshes your league
                          automatically each week during the season. ESPN
                          cookies expire periodically, so you may occasionally
                          need to re-enter them.
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>
              </div>
            )}
            {platform === 'YAHOO' && (
              <div className="mt-3 flex items-center gap-2 text-left">
                <input
                  id="yahoo-auto-refresh"
                  type="checkbox"
                  className="size-4 cursor-pointer accent-primary"
                  checked={yahooAutoRefresh}
                  onChange={(e) => setYahooAutoRefresh(e.target.checked)}
                  disabled={loading}
                />
                <div className="flex items-center gap-1.5">
                  <Label
                    htmlFor="yahoo-auto-refresh"
                    className="cursor-pointer"
                  >
                    Enable automatic weekly refresh
                  </Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent side="right" className="max-w-64">
                        When enabled, LeagueQL refreshes your league
                        automatically each week during the season using your
                        saved Yahoo connection.
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>
            )}
            {loading && (
              <div className="mt-4 flex flex-col gap-1.5">
                <Progress value={progress} className="w-full" />
                <p className="text-xs text-muted-foreground">
                  {loadingMessage}
                </p>
              </div>
            )}
            {error && (
              <Alert variant="destructive" className="mt-3 text-left">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </section>

      <Dialog open={authOpen} onOpenChange={setAuthOpen}>
        <DialogContent
          className="p-0 overflow-hidden w-auto max-w-none bg-transparent border-none shadow-none ring-0"
          showCloseButton={false}
        >
          <DialogTitle className="sr-only">Sign in to LeagueQL</DialogTitle>
          <SignIn
            routing="hash"
            forceRedirectUrl="/?connect=true"
            signUpForceRedirectUrl="/?connect=true"
          />
        </DialogContent>
      </Dialog>

      {/* PRODUCT SHOWCASE */}
      <section className="relative z-10 px-6 pt-4 pb-8">
        <div className="mx-auto mb-11 flex max-w-160 flex-col items-center gap-3 text-center">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-primary">
            See it in action
          </span>
          <h2 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Every angle of your league, one click away
          </h2>
          <p className="max-w-lg text-muted-foreground">
            Explore your league&apos;s complete history through rich,
            interactive views.
          </p>
        </div>
        <ProductShowcase />
      </section>

      {/* WORKS WITH */}
      <section className="relative z-10 px-6 py-8">
        <div className="mx-auto flex max-w-160 flex-wrap items-center justify-center gap-x-7 gap-y-4 border-y border-border py-5">
          <span className="w-full text-center text-xs uppercase tracking-[0.14em] text-muted-foreground sm:w-auto">
            Works with
          </span>
          {PLATFORMS.map((p) => (
            <span
              key={p.name}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm font-semibold"
            >
              <img src={p.logo} alt="" className="h-5 w-auto" />
              {p.name}
              {p.beta && (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wide text-primary">
                  Beta
                </span>
              )}
            </span>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section className="relative z-10 px-6 pt-20 pb-8">
        <div className="mx-auto mb-11 flex max-w-160 flex-col items-center gap-3 text-center">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-primary">
            Everything, tracked
          </span>
          <h2 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            A record book that writes itself
          </h2>
          <p className="max-w-lg text-muted-foreground">
            Connect once and every stat, streak, and rivalry stays up to date,
            season after season.
          </p>
        </div>
        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <FeatureCard key={f.title} {...f} />
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="relative z-10 px-6 pt-20 pb-8">
        <div className="mx-auto mb-11 flex max-w-160 flex-col items-center gap-3 text-center">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-primary">
            How it works
          </span>
          <h2 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            From league ID to full history in under a minute
          </h2>
        </div>
        <div className="relative mx-auto grid max-w-5xl grid-cols-1 gap-[52px] md:grid-cols-3">
          <div
            aria-hidden
            className="absolute left-[10%] right-[10%] top-1/2 hidden h-0.5 -translate-y-px bg-gradient-to-r from-transparent via-border to-transparent md:block"
          />
          {HOW_STEPS.map((step, i) => (
            <Step
              key={step.step}
              step={step}
              isLast={i === HOW_STEPS.length - 1}
            />
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="relative z-10 px-6 pt-20 pb-8">
        <div className="mx-auto mb-11 flex max-w-160 flex-col items-center gap-3 text-center">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-primary">
            FAQ
          </span>
          <h2 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Before you connect
          </h2>
          <p className="max-w-lg text-muted-foreground">
            Everything you need to know about connecting and managing your
            league.
          </p>
        </div>
        <Faq />
      </section>

      {/* FINAL CTA */}
      <section className="relative z-10 px-6 pt-20 pb-16">
        <div className="relative mx-auto max-w-4xl overflow-hidden rounded-3xl border border-primary/30 bg-primary/[0.08] px-8 py-14 text-center">
          <div
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-[-60%] h-[500px] w-[600px] -translate-x-1/2"
            style={{
              background:
                'radial-gradient(50% 50% at 50% 50%, color-mix(in oklab, var(--chart-3) 24%, transparent), transparent 70%)',
            }}
          />
          <h2 className="font-heading relative text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Your league history should be preserved
          </h2>
          <p className="relative mx-auto mt-4 mb-7 max-w-md text-muted-foreground">
            Connect in seconds and see your entire history come to life.
          </p>
          <div className="relative flex flex-wrap justify-center gap-3">
            <Button
              size="lg"
              className="text-[0.82rem] px-6 cursor-pointer"
              onClick={handleConnectLeague}
            >
              Connect Your League <ArrowRight />
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="text-[0.82rem] px-6 cursor-pointer"
              onClick={handleViewDemo}
            >
              View Demo
            </Button>
          </div>
        </div>
      </section>

      <Footer className="mt-auto" />

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(18px); }
          to   { opacity: 1; transform: translateY(0);    }
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-\\[fadeUp_0\\.6s_0\\.1s_both\\],
          .animate-\\[fadeUp_0\\.6s_0\\.25s_both\\],
          .animate-\\[fadeUp_0\\.6s_0\\.4s_both\\],
          .animate-\\[fadeUp_0\\.6s_0\\.55s_both\\],
          .animate-\\[fadeUp_0\\.4s_both\\] { animation: none; }
        }
      `}</style>
    </div>
  );
}
