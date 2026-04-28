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
import PlayerRecords from '@/features/player_records/player-records';
import SeasonStandings from '@/features/season_standings/season-standings';
import DraftRecap from '@/features/draft_recap/draft-recap';
import PrivacyPage from '@/features/privacy/privacy-page';
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
      target="_blank"
      rel="noopener noreferrer"
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
          {isDemoMode() && (
            <div className="flex h-8 shrink-0 items-center justify-center bg-primary/20 border-b border-primary/20 px-4">
              <span className="font-mono text-[0.72rem] text-primary tracking-wide">
                Demo Mode — connect your own league to see your data
              </span>
            </div>
          )}
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

function isDemoMode(): boolean {
  return document.cookie.split('; ').some((row) => row === 'demo_mode=true');
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (isDemoMode()) return <>{children}</>;
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
          path="/player_records"
          element={
            <ProtectedRoute>
              <AppLayout>
                <PlayerRecords />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/draft_recap"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DraftRecap />
              </AppLayout>
            </ProtectedRoute>
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
      </Routes>
    </BrowserRouter>
  );
}

export default App;
