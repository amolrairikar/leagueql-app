import { SignIn, useUser } from '@clerk/react';
import { ArrowRight, ChevronRight } from 'lucide-react';
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
import {
  FEATURES,
  HOW_STEPS,
  PLATFORMS,
} from '@/features/landing_page/constants';
import { ProductShowcase } from '@/features/landing_page/product-showcase';
import type { Feature, HowStep } from '@/features/landing_page/types';
import { ApiError } from '@/lib/api-client';
import {
  clearAllLeagueCookies,
  isDemoMode,
  setDemoMode,
  setLeagueCookies,
} from '@/lib/cookie-handler';
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

  // Reaching the landing page is a demo-mode exit path. The landing page is never
  // part of the demo experience, so any of the ways a user can arrive here — the
  // "LeagueQL" header link, the browser back button, or a direct visit — should
  // clear lingering demo state. Otherwise the 24h `demo_mode` cookie survives and
  // a subsequently connected live league is served demo fixtures / bypasses auth
  // (FE-015). Only the dedicated "Exit Demo" button previously did this cleanup.
  useEffect(() => {
    if (isDemoMode()) clearAllLeagueCookies();
  }, []);

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
        setError(
          <>
            Something went wrong connecting your league. Please try again. If
            the error persists, contact{' '}
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
      <section className="relative z-10 flex flex-col items-center text-center px-6 pt-24 pb-16">
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

      {/* PRODUCT SHOWCASE */}
      <section className="relative z-10 px-6 pt-16 pb-8">
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
          <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Works with
          </span>
          {PLATFORMS.map((p) => (
            <span
              key={p.name}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm font-semibold"
            >
              <img src={p.logo} alt="" className="h-5 w-auto" />
              {p.name}
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
