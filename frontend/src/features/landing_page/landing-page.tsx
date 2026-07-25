import { SignIn, useUser } from '@clerk/react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { getLeague } from '@/components/api/leagues';
import Footer from '@/components/footer';
import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { onboardLeague } from '@/features/connect_league/api-calls';
import { JoinLeagueDialog } from '@/features/connect_league/join-league-dialog';
import { pollForCompletion } from '@/features/connect_league/poll';
import { FEATURES } from '@/features/landing_page/constants';
import type { Feature } from '@/features/landing_page/types';
import { ApiError } from '@/lib/api-client';
import { setDemoMode, setLeagueCookies } from '@/lib/cookie-handler';
import { DEMO_SEASONS } from '@/lib/demo-constants';

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

interface FeatureCardProps {
  icon: string;
  title: string;
  desc: string;
}

function FeatureCard({ icon, title, desc }: FeatureCardProps) {
  return (
    <div className="bg-card p-7 hover:bg-accent/50 transition-colors duration-200">
      <div className="text-xl mb-3">{icon}</div>
      <h3 className="font-heading text-foreground text-base mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

export default function LeagueQLLanding() {
  const { isSignedIn } = useUser();
  const navigate = useNavigate();
  const [authOpen, setAuthOpen] = useState(false);
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [platform, setPlatform] = useState<'ESPN' | 'SLEEPER'>('ESPN');
  const [leagueId, setLeagueId] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<ReactNode>(null);
  const [joinLeagueId, setJoinLeagueId] = useState<string | null>(null);
  const [leagueCount, setLeagueCount] = useState<number | null>(null);
  const loadingStartRef = useRef<number | null>(null);
  const loadingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('connect') === 'true' && isSignedIn) {
      setShowConnectForm(true);
    }
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

  async function handleConnectSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!leagueId.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      const leagueData = await getLeague(leagueId.trim(), platform);
      setLeagueCookies(leagueId.trim(), platform, leagueData.data.seasons);
      void navigate('/home');
    } catch (err) {
      const status = err instanceof ApiError ? err.status : null;
      if (platform === 'ESPN' && status === 404) {
        // Not onboarded yet — route to the onboard/refresh form to set it up.
        void navigate(
          `/connect_league?leagueId=${encodeURIComponent(leagueId.trim())}&platform=espn`,
        );
      } else if (platform === 'ESPN' && status === 403) {
        // Already onboarded but the caller isn't a member of this private ESPN
        // league yet — open the Join League dialog to verify membership rather
        // than the (confusing) onboard form (LQL-01 / BE-016 / FE-025).
        setJoinLeagueId(leagueId.trim());
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
                League onboarding failed. Please try again or{' '}
                <a
                  href="mailto:support@leagueql.com"
                  className="underline underline-offset-4"
                >
                  contact support
                </a>{' '}
                if the error persists.
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
        setError(
          <>
            Something went wrong connecting your league. Please try again or{' '}
            <a
              href="mailto:support@leagueql.com"
              className="underline underline-offset-4"
            >
              contact support
            </a>{' '}
            if the error persists.
          </>,
        );
      }
    } finally {
      setLoading(false);
    }
  }

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

      <section className="relative z-10 flex flex-col items-center text-center px-6 pt-24 pb-20">
        {leagueCount !== null && (
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground animate-[fadeUp_0.6s_0.1s_both]">
            <span className="flex items-center -space-x-1">
              <span className="block size-2.5 shrink-0 rounded-full bg-red-500" />
              <span className="block size-2.5 shrink-0 rounded-full bg-green-500" />
              <span className="block size-2.5 shrink-0 rounded-full bg-blue-500" />
            </span>
            Join {leagueCount} other leagues tracking their league&apos;s
            history
          </div>
        )}

        <h1
          className="
            text-[clamp(2.6rem,6vw,4.5rem)] leading-[1.1] tracking-tight
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
            Connect Your League
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
                  if (v === 'ESPN' || v === 'SLEEPER') setPlatform(v);
                }}
              >
                <SelectTrigger className="w-36 shrink-0">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ESPN">ESPN</SelectItem>
                  <SelectItem value="SLEEPER">Sleeper</SelectItem>
                </SelectContent>
              </Select>
              <Input
                className="flex-1"
                placeholder="League ID"
                name="leagueId"
                autoComplete="on"
                value={leagueId}
                onChange={(e) => setLeagueId(e.target.value)}
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

      <JoinLeagueDialog
        open={joinLeagueId !== null}
        onOpenChange={(next) => {
          if (!next) setJoinLeagueId(null);
        }}
        leagueId={joinLeagueId ?? ''}
      />

      <section className="relative z-10 px-6 pb-16">
        <div
          className="
          max-w-215 mx-auto
          grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
          border border-border rounded-xl overflow-hidden
          divide-x divide-y divide-border
          "
        >
          {FEATURES.map((f: Feature) => (
            <FeatureCard key={f.title} {...f} />
          ))}
        </div>
      </section>

      <Footer />

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(18px); }
          to   { opacity: 1; transform: translateY(0);    }
        }
      `}</style>
    </div>
  );
}
