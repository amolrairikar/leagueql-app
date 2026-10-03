import { ArrowRight } from 'lucide-react';
import { Suspense, use, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import espnLogo from '@/assets/espn-logo.svg';
import sleeperLogo from '@/assets/sleeper-logo.svg';
import yahooLogo from '@/assets/yahoo-logo.svg';
import { getLeague } from '@/components/api/leagues';
import type { MyLeague, Platform } from '@/components/api/types';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api-client';
import { setLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';
import type { Result } from '@/lib/result';

const OPEN_FALLBACK = "Couldn't open that league. Please try again.";

const PLATFORM_LOGO: Record<Platform, string> = {
  ESPN: espnLogo,
  SLEEPER: sleeperLogo,
  YAHOO: yahooLogo,
};

const PLATFORM_NAME: Record<Platform, string> = {
  ESPN: 'ESPN',
  SLEEPER: 'Sleeper',
  YAHOO: 'Yahoo',
};

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 365 * 24 * 60 * 60],
  ['month', 30 * 24 * 60 * 60],
  ['week', 7 * 24 * 60 * 60],
  ['day', 24 * 60 * 60],
  ['hour', 60 * 60],
  ['minute', 60],
];

const relativeTime = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

/** "3 days ago", "yesterday", "just now" — or null for a missing/unparseable timestamp. */
function formatUpdatedAgo(iso: string | null, now = Date.now()) {
  if (!iso) return null;
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return null;
  const seconds = Math.max(0, Math.round((now - then) / 1000));
  for (const [unit, size] of RELATIVE_UNITS) {
    if (seconds >= size) {
      return relativeTime.format(-Math.floor(seconds / size), unit);
    }
  }
  return 'just now';
}

function seasonSpan(seasons: string[]) {
  if (seasons.length === 0) return null;
  const first = seasons[0];
  const last = seasons[seasons.length - 1];
  const count = `${seasons.length} season${seasons.length === 1 ? '' : 's'}`;
  return first === last ? `${first} · ${count}` : `${first}–${last} · ${count}`;
}

function LeagueRow({
  league,
  opening,
  disabled,
  onOpen,
}: {
  league: MyLeague;
  opening: boolean;
  disabled: boolean;
  onOpen: () => void;
}) {
  const updated = formatUpdatedAgo(league.updated_at);
  const details = [
    PLATFORM_NAME[league.platform],
    seasonSpan(league.seasons),
    updated && `Updated ${updated}`,
    league.migrated_from && `Moved from ${PLATFORM_NAME[league.migrated_from]}`,
  ].filter(Boolean);
  const name = league.league_name ?? `League ${league.league_id}`;

  return (
    <li className="border-t border-border first:border-t-0">
      <button
        type="button"
        onClick={onOpen}
        disabled={disabled}
        className="group grid w-full cursor-pointer grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3.5 px-4 py-3.5 text-left transition-colors hover:bg-muted focus-visible:bg-muted focus-visible:outline-none disabled:cursor-default disabled:opacity-60 disabled:hover:bg-transparent"
      >
        <span className="grid size-9 shrink-0 place-items-center rounded-[10px] border border-border bg-white p-1.5">
          <img
            src={PLATFORM_LOGO[league.platform]}
            alt={PLATFORM_NAME[league.platform]}
            className="size-full object-contain"
          />
        </span>
        <span className="min-w-0">
          <span className="flex min-w-0 flex-wrap items-center gap-2 text-sm font-semibold text-foreground">
            <span className="truncate">{name}</span>
            {league.espn_reauth_required && (
              <span className="rounded-md bg-amber-500/15 px-1.5 py-0.5 text-[11px] font-medium text-amber-700 dark:text-amber-300">
                Reconnect ESPN
              </span>
            )}
          </span>
          <span className="mt-0.5 block text-[12.5px] text-muted-foreground tabular-nums">
            {details.join(' • ')}
          </span>
        </span>
        <span className="inline-flex items-center gap-1 text-sm whitespace-nowrap text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary">
          {opening ? (
            <Spinner />
          ) : (
            <>
              <span className="max-sm:hidden">Open</span>
              <ArrowRight className="size-4" />
            </>
          )}
        </span>
      </button>
    </li>
  );
}

function MyLeaguesSkeleton() {
  return (
    <ul
      aria-label="Loading your leagues"
      className="overflow-hidden rounded-2xl border border-border bg-card"
    >
      {[0, 1, 2].map((i) => (
        <li
          key={i}
          className="flex items-center gap-3.5 border-t border-border px-4 py-3.5 first:border-t-0"
        >
          <Skeleton className="size-9 rounded-[10px]" />
          <span className="grid flex-1 gap-2">
            <Skeleton className="h-3 w-2/5" />
            <Skeleton className="h-2.5 w-3/4" />
          </span>
        </li>
      ))}
    </ul>
  );
}

function MyLeaguesContent({
  leagues,
  onRetry,
  onConnect,
}: MyLeaguesPanelProps) {
  const result = use(leagues);
  const navigate = useNavigate();
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  if (!result.ok) {
    return (
      <div className="grid gap-3">
        <ErrorAlert message={result.error} />
        <div>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  if (result.data.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border px-6 py-8 text-center text-sm leading-relaxed text-muted-foreground">
        <p className="mb-1 text-base font-semibold text-foreground">
          No leagues yet
        </p>
        <p>
          Leagues you connect, join from an invite link, or open on Sleeper show
          up here.
        </p>
        <Button
          size="lg"
          className="mt-4 cursor-pointer px-6 text-[0.82rem]"
          onClick={onConnect}
        >
          Connect Your League <ArrowRight />
        </Button>
      </div>
    );
  }

  async function openLeague(league: MyLeague) {
    setOpeningId(league.league_id);
    setOpenError(null);
    try {
      const { data } = await getLeague(league.league_id, league.platform);
      setLeagueCookies(league.league_id, league.platform, data.seasons);
      void navigate('/home');
    } catch (err) {
      setOpenError(
        err instanceof ApiError && err.status >= 400 && err.status < 500
          ? err.message
          : OPEN_FALLBACK,
      );
      setOpeningId(null);
    }
  }

  return (
    <div className="grid gap-2.5">
      <div className="flex items-baseline justify-between gap-3 px-1">
        <h2 className="text-[15px] font-semibold text-foreground">
          My leagues
        </h2>
        <span className="text-xs text-muted-foreground">
          Sorted by most recently updated
        </span>
      </div>
      {openError && <ErrorAlert message={openError} />}
      <ul className="overflow-hidden rounded-2xl border border-border bg-card">
        {result.data.map((league) => (
          <LeagueRow
            key={`${league.platform}-${league.league_id}`}
            league={league}
            opening={openingId === league.league_id}
            disabled={openingId !== null}
            onOpen={() => void openLeague(league)}
          />
        ))}
      </ul>
      <p className="px-1 text-xs leading-relaxed text-muted-foreground">
        Missing a league? For ESPN or Yahoo, ask the league owner for an invite
        link. For Sleeper, open your league once using &quot;Connect Your
        League&quot; and it shows up here afterwards.
      </p>
    </div>
  );
}

interface MyLeaguesPanelProps {
  /** The `GET /me/leagues` request, wrapped by `toResult` so it never rejects. */
  leagues: Promise<Result<MyLeague[]>>;
  /** Re-request the list after a failure. */
  onRetry: () => void;
  /** Open the landing page's Connect form (the empty state's call to action). */
  onConnect: () => void;
}

/**
 * The signed-in "View My Leagues" panel on the landing page (frontend/landing-page). Lists the
 * caller's leagues from `GET /me/leagues`; activating a row opens the league the same way the
 * Connect flow opens an already-onboarded one.
 */
export function MyLeaguesPanel(props: MyLeaguesPanelProps) {
  return (
    <div
      id="my-leagues-panel"
      className="mt-8 w-full max-w-160 animate-[fadeUp_0.4s_both] text-left motion-reduce:animate-none"
    >
      <Suspense fallback={<MyLeaguesSkeleton />}>
        <MyLeaguesContent {...props} />
      </Suspense>
    </div>
  );
}
