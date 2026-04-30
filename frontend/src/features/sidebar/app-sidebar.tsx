import { UserButton } from '@clerk/react';
import {
  History,
  Home,
  LogIn,
  LogOut,
  RefreshCw,
  Scroll,
  Star,
  Swords,
  TableProperties,
  Trophy,
  Trash2,
  Users,
  Zap,
} from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
  useSidebar,
} from '@/components/ui/sidebar';
import {
  clearAllLeagueCookies,
  clearLeagueCookies,
  getLeagueCookies,
  isDemoMode,
} from '@/lib/cookie-handler';
import { deleteLeague } from '@/features/sidebar/api-calls';

const navItems = [
  { title: 'Home', url: '/home', icon: Home },
  { title: 'Standings', url: '/standings', icon: TableProperties },
  { title: 'Matchups', url: '/matchups', icon: Swords },
  { title: 'Playoff Bracket', url: '/playoff_bracket', icon: Trophy },
  { title: 'Manager Comparison', url: '/manager_comparison', icon: Users },
  { title: 'Manager History', url: '/manager_history', icon: History },
  { title: 'Draft Recap', url: '/draft_recap', icon: Scroll },
  { title: 'Player Records', url: '/player_records', icon: Star },
  { title: 'Matchup Records', url: '/matchup_records', icon: Zap },
];

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { state } = useSidebar();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const demoMode = isDemoMode();

  function handleExitDemo() {
    clearAllLeagueCookies();
    void navigate('/');
  }

  async function handleDeleteLeague() {
    const { leagueId, platform } = getLeagueCookies();

    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteLeague(leagueId, platform);
      clearLeagueCookies();
      setDialogOpen(false);
      void navigate('/league');
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : 'Failed to delete league.',
      );
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname === item.url}
                    tooltip={item.title}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>Settings</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {demoMode ? (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    tooltip="Connect Your League"
                    className="cursor-pointer"
                    onClick={handleExitDemo}
                  >
                    <LogIn />
                    <span>Connect Your League</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ) : (
                <>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      asChild
                      tooltip="Refresh League"
                      className="cursor-pointer"
                    >
                      <Link to="/connect_league">
                        <RefreshCw />
                        <span>Refresh League</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <Dialog
                      open={dialogOpen}
                      onOpenChange={(open) => {
                        setDialogOpen(open);
                        if (!open) setDeleteError(null);
                      }}
                    >
                      <DialogTrigger asChild>
                        <SidebarMenuButton
                          tooltip="Delete League"
                          className="text-destructive hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                        >
                          <Trash2 />
                          <span>Delete League</span>
                        </SidebarMenuButton>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Delete League</DialogTitle>
                          <DialogDescription>
                            This will permanently delete all data for this league.
                            This action cannot be undone.
                          </DialogDescription>
                        </DialogHeader>
                        {deleteError && (
                          <p className="text-sm text-destructive">{deleteError}</p>
                        )}
                        <DialogFooter>
                          <Button
                            className="cursor-pointer"
                            variant="destructive"
                            onClick={() => void handleDeleteLeague()}
                            disabled={isDeleting}
                          >
                            {isDeleting ? 'Deleting…' : 'Delete League'}
                          </Button>
                          <Button
                            className="cursor-pointer"
                            variant="outline"
                            onClick={() => setDialogOpen(false)}
                            disabled={isDeleting}
                          >
                            Cancel
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  </SidebarMenuItem>
                </>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-3">
        {demoMode ? (
          <SidebarMenuButton
            tooltip="Exit Demo"
            className="cursor-pointer text-muted-foreground hover:text-foreground"
            onClick={handleExitDemo}
          >
            <LogOut />
            {state === 'expanded' && <span>Exit Demo</span>}
          </SidebarMenuButton>
        ) : (
          <UserButton showName={state === 'expanded'} />
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
