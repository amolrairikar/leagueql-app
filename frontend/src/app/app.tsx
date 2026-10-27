import { useUser } from '@clerk/react';
import { lazy, Suspense, useEffect } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Link,
  useLocation,
} from 'react-router-dom';

import { Banner } from '@/components/banner';
import { ErrorBoundary } from '@/components/error-boundary';
import Header from '@/components/header';
import { ModeToggle } from '@/components/mode-toggle';
import { NavLink } from '@/components/nav-link';
import { ScrollToTop } from '@/components/scroll-to-top';
import { Spinner } from '@/components/spinner';
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';
import { NAV_LINKS } from '@/features/landing_page/constants';
import type { NavLinkItem } from '@/features/landing_page/types';
import { LineupBackfillBell } from '@/features/lineup_backfill/lineup-backfill-bell';
import { MembershipGuard } from '@/features/ownership/membership-guard';
import { AppSidebar } from '@/features/sidebar/app-sidebar';
import { EspnReauthBanner } from '@/features/sidebar/espn-reauth-banner';
import { HeaderAccount } from '@/features/sidebar/header-account';
import { RefreshReminderBanner } from '@/features/sidebar/refresh-reminder-banner';
import { SleeperStaleSeasonBanner } from '@/features/sidebar/sleeper-stale-season-banner';
import { YahooAttributionFooter } from '@/features/sidebar/yahoo-attribution-footer';
import { isDemoMode } from '@/lib/cookie-handler';
import { recordRouteChange } from '@/lib/telemetry';

const ChangelogPage = lazy(() => import('@/features/changelog/changelog-page'));
const JoinInvitePage = lazy(
  () => import('@/features/connect_league/join-invite-page'),
);
const LeagueConnect = lazy(
  () => import('@/features/connect_league/league-connect'),
);
const DraftGrades = lazy(() => import('@/features/draft_grades/draft-grades'));
const DraftRecap = lazy(() => import('@/features/draft_recap/draft-recap'));
const HomePage = lazy(() => import('@/features/home_page/home-page'));
const InstructionsPage = lazy(
  () => import('@/features/instructions/instructions-page'),
);
const LeagueQLLanding = lazy(
  () => import('@/features/landing_page/landing-page'),
);
const ManagerComparison = lazy(
  () => import('@/features/manager_comparison/manager-comparison'),
);
const ManagerHistory = lazy(
  () => import('@/features/manager_history/manager-history'),
);
const MatchupRecords = lazy(
  () => import('@/features/matchup_records/matchup-records'),
);
const Matchups = lazy(() => import('@/features/matchups/matchups'));
const MigrateLeague = lazy(
  () => import('@/features/migrate_league/migrate-league'),
);
const PlayerRecords = lazy(
  () => import('@/features/player_records/player-records'),
);
const PlayoffBracket = lazy(
  () => import('@/features/playoff_bracket/playoff-bracket'),
);
const ExtensionPrivacyPage = lazy(
  () => import('@/features/privacy/extension-privacy-page'),
);
const PowerRankings = lazy(
  () => import('@/features/power_rankings/power-rankings'),
);
const PrivacyPage = lazy(() => import('@/features/privacy/privacy-page'));
const SeasonStandings = lazy(
  () => import('@/features/season_standings/season-standings'),
);
const Transactions = lazy(() => import('@/features/transactions/transactions'));

/** Full-area spinner shown while a route's code loads (frontend/route-code-splitting). */
function PageFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Spinner className="size-6 text-muted-foreground" />
    </div>
  );
}

/** Emits a lightweight route-change span on navigation (frontend/observability); renders nothing. */
function RouteChangeTracker() {
  const location = useLocation();
  useEffect(() => {
    recordRouteChange(location.pathname);
  }, [location.pathname]);
  return null;
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="h-svh overflow-hidden">
          {isDemoMode() && (
            <div className="flex h-8 shrink-0 items-center justify-center bg-primary/40 border-b border-primary/50 px-4">
              <span className="text-[0.72rem] font-medium text-white tracking-wide">
                Demo Mode — connect your own league to see your data
              </span>
            </div>
          )}
          <header className="sticky top-0 z-10 flex h-12 shrink-0 items-center gap-2 border-b px-4 bg-background/80 backdrop-blur-md">
            <SidebarTrigger className="cursor-pointer" />
            <Link
              to="/"
              className="font-heading text-xl tracking-tight text-foreground no-underline sm:absolute sm:left-1/2 sm:-translate-x-1/2"
            >
              League<span className="text-primary font-bold">QL</span>
            </Link>
            <div className="ml-auto flex items-center gap-1">
              {NAV_LINKS.map((link: NavLinkItem) => (
                <NavLink key={link.label} {...link} />
              ))}
              <LineupBackfillBell />
              <div className="ml-2">
                <ModeToggle />
              </div>
              <HeaderAccount />
            </div>
          </header>
          <Banner />
          <EspnReauthBanner />
          <RefreshReminderBanner />
          <SleeperStaleSeasonBanner />
          <ErrorBoundary resetKeys={[location.pathname]}>
            <MembershipGuard>
              <Suspense fallback={<PageFallback />}>{children}</Suspense>
            </MembershipGuard>
          </ErrorBoundary>
          <YahooAttributionFooter />
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isSignedIn, isLoaded } = useUser();
  if (isDemoMode()) return <>{children}</>;
  if (!isLoaded)
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    );
  if (!isSignedIn) return <Navigate to="/" replace />;
  return <>{children}</>;
}

const APP_LAYOUT_ROUTES: { path: string; element: React.ReactNode }[] = [
  { path: '/home', element: <HomePage /> },
  { path: '/standings', element: <SeasonStandings /> },
  { path: '/power_rankings', element: <PowerRankings /> },
  { path: '/matchups', element: <Matchups /> },
  { path: '/manager_comparison', element: <ManagerComparison /> },
  { path: '/playoff_bracket', element: <PlayoffBracket /> },
  { path: '/manager_history', element: <ManagerHistory /> },
  { path: '/player_records', element: <PlayerRecords /> },
  { path: '/matchup_records', element: <MatchupRecords /> },
  { path: '/draft_recap', element: <DraftRecap /> },
  { path: '/draft_grades', element: <DraftGrades /> },
  { path: '/transactions', element: <Transactions /> },
];

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ScrollToTop />
        <RouteChangeTracker />
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route
              path="/"
              element={
                <>
                  <Header />
                  <LeagueQLLanding />
                </>
              }
            />
            <Route
              path="/connect_league"
              element={
                <ProtectedRoute>
                  <Header />
                  <div className="pt-1">
                    <LeagueConnect />
                  </div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/join/:leagueId"
              element={
                <>
                  <Header />
                  <JoinInvitePage />
                </>
              }
            />
            <Route
              path="/migrate_league"
              element={
                <ProtectedRoute>
                  <Header />
                  <div className="pt-1">
                    <MigrateLeague />
                  </div>
                </ProtectedRoute>
              }
            />
            {APP_LAYOUT_ROUTES.map(({ path, element }) => (
              <Route
                key={path}
                path={path}
                element={
                  <ProtectedRoute>
                    <AppLayout>{element}</AppLayout>
                  </ProtectedRoute>
                }
              />
            ))}
            <Route
              path="/changelog"
              element={
                <>
                  <Header />
                  <ChangelogPage />
                </>
              }
            />
            <Route
              path="/privacy"
              element={
                <>
                  <Header />
                  <PrivacyPage />
                </>
              }
            />
            <Route
              path="/extension-privacy"
              element={
                <>
                  <Header />
                  <ExtensionPrivacyPage />
                </>
              }
            />
            <Route
              path="/docs"
              element={
                <div className="flex h-svh flex-col">
                  <Header />
                  <main className="flex-1 overflow-auto">
                    <InstructionsPage />
                  </main>
                </div>
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
