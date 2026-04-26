import { useUser } from '@clerk/react';
import { type LucideProps } from 'lucide-react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Header from '@/components/header';
import { ModeToggle } from '@/components/mode-toggle';
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';
import LeagueConnect from '@/features/connect_league/league-connect';
import { NAV_LINKS } from '@/features/landing_page/constants';
import LeagueQLLanding from '@/features/landing_page/landing-page';
import type { NavLinkItem } from '@/features/landing_page/types';
import LeagueSelection from '@/features/league_selection/league-selection';
import ManagerComparison from '@/features/manager_comparison/manager-comparison';
import ManagerHistory from '@/features/manager_history/manager-history';
import Matchups from '@/features/matchups/matchups';
import PlayoffBracket from '@/features/playoff_bracket/playoff-bracket';
import ScoringRecords from '@/features/scoring_records/scoring-records';
import SeasonStandings from '@/features/season_standings/season-standings';
import { AppSidebar } from '@/features/sidebar/app-sidebar';

function NavLink({
  href,
  icon: Icon,
  label,
}: {
  href: string;
  icon: React.FC<LucideProps>;
  label: string;
}) {
  return (
    <a
      href={href}
      className="
        flex items-center gap-1.5 px-3 py-1.5 rounded-md
        text-muted-foreground hover:text-foreground hover:bg-accent
        font-mono text-xs tracking-wide
        transition-colors duration-200
      "
    >
      <Icon size={13} className="opacity-70" />
      <span className="hidden sm:inline">{label}</span>
    </a>
  );
}

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-12 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="cursor-pointer" />
            <div className="ml-auto flex items-center gap-1">
              {NAV_LINKS.map((link: NavLinkItem) => (
                <NavLink key={link.label} {...link} />
              ))}
              <div className="ml-2">
                <ModeToggle />
              </div>
            </div>
          </header>
          {children}
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isSignedIn, isLoaded } = useUser();
  if (!isLoaded) return null;
  if (!isSignedIn) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
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
          path="/league"
          element={
            <ProtectedRoute>
              <Header />
              <div className="pt-1">
                <LeagueSelection />
              </div>
            </ProtectedRoute>
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
          path="/standings"
          element={
            <ProtectedRoute>
              <AppLayout>
                <SeasonStandings />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/matchups"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Matchups />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/manager_comparison"
          element={
            <ProtectedRoute>
              <AppLayout>
                <ManagerComparison />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/playoff_bracket"
          element={
            <ProtectedRoute>
              <AppLayout>
                <PlayoffBracket />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/manager_history"
          element={
            <ProtectedRoute>
              <AppLayout>
                <ManagerHistory />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/scoring_records"
          element={
            <ProtectedRoute>
              <AppLayout>
                <ScoringRecords />
              </AppLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
