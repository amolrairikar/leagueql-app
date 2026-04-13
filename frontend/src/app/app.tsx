import { useUser } from '@clerk/react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Header from '@/components/header';
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';
import LeagueConnect from '@/features/connect_league/league-connect';
import Home from '@/features/home/home';
import LeagueQLLanding from '@/features/landing_page/landing-page';
import LeagueSelection from '@/features/league_selection/league-selection';
import { AppSidebar } from '@/features/sidebar/app-sidebar';
import Test from '@/features/test/test';

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-12 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
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
          path="/home"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Home />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/test"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Test />
              </AppLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
