import { useUser } from '@clerk/react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';

import { ErrorBoundary } from '@/components/error-boundary';
import Footer from '@/components/footer';
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
import ChangelogPage from '@/features/changelog/changelog-page';
import LeagueConnect from '@/features/connect_league/league-connect';
import DraftGrades from '@/features/draft_grades/draft-grades';
import DraftRecap from '@/features/draft_recap/draft-recap';
import HomePage from '@/features/home_page/home-page';
import InstructionsPage from '@/features/instructions/instructions-page';
import { NAV_LINKS } from '@/features/landing_page/constants';
import LeagueQLLanding from '@/features/landing_page/landing-page';
import type { NavLinkItem } from '@/features/landing_page/types';
import ManagerComparison from '@/features/manager_comparison/manager-comparison';
import ManagerHistory from '@/features/manager_history/manager-history';
import MatchupRecords from '@/features/matchup_records/matchup-records';
import Matchups from '@/features/matchups/matchups';
import MigrateLeague from '@/features/migrate_league/migrate-league';
import PlayerRecords from '@/features/player_records/player-records';
import PlayoffBracket from '@/features/playoff_bracket/playoff-bracket';
import PrivacyPage from '@/features/privacy/privacy-page';
import ExtensionPrivacyPage from '@/features/privacy/extension-privacy-page';
import SeasonStandings from '@/features/season_standings/season-standings';
import { AppSidebar } from '@/features/sidebar/app-sidebar';
import { isDemoMode } from '@/lib/cookie-handler';

function AppLayout({ children }: { children: React.ReactNode }) {
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
              className="absolute left-1/2 -translate-x-1/2 font-heading text-xl tracking-tight text-foreground no-underline"
            >
              League<span className="text-primary font-bold">QL</span>
            </Link>
            <div className="ml-auto flex items-center gap-1">
              {NAV_LINKS.map((link: NavLinkItem) => (
                <NavLink key={link.label} {...link} />
              ))}
              <div className="ml-2">
                <ModeToggle />
              </div>
            </div>
          </header>
          <ErrorBoundary>{children}</ErrorBoundary>
          <Footer className="py-3" />
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
  { path: '/matchups', element: <Matchups /> },
  { path: '/manager_comparison', element: <ManagerComparison /> },
  { path: '/playoff_bracket', element: <PlayoffBracket /> },
  { path: '/manager_history', element: <ManagerHistory /> },
  { path: '/player_records', element: <PlayerRecords /> },
  { path: '/matchup_records', element: <MatchupRecords /> },
  { path: '/draft_recap', element: <DraftRecap /> },
  { path: '/draft_grades', element: <DraftGrades /> },
];

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ScrollToTop />
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
                <Footer />
              </ProtectedRoute>
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
                <Footer />
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
            path="/privacy"
            element={
              <>
                <Header />
                <PrivacyPage />
                <Footer />
              </>
            }
          />
          <Route
            path="/extension-privacy"
            element={
              <>
                <Header />
                <ExtensionPrivacyPage />
                <Footer />
              </>
            }
          />
          <Route
            path="/changelog"
            element={
              <>
                <Header />
                <ChangelogPage />
                <Footer />
              </>
            }
          />
          <Route
            path="/docs"
            element={
              <>
                <Header />
                <InstructionsPage />
                <Footer />
              </>
            }
          />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
