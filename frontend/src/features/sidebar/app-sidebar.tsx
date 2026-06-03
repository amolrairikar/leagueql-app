import { UserButton } from '@clerk/react';
import {
  ArrowLeftRight,
  CreditCard,
  GraduationCap,
  History,
  Home,
  LogIn,
  LogOut,
  RefreshCw,
  Scroll,
  Search,
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
import { deleteLeague } from '@/features/sidebar/api-calls';
import { ManageSubscriptionDialog } from '@/features/subscription/manage-subscription-dialog';
import { useSubscription } from '@/features/subscription/use-subscription';
import { clearApiCache } from '@/lib/api-client';
import {
  clearAllLeagueCookies,
  clearLeagueCookies,
  getLeagueCookies,
  isDemoMode,
} from '@/lib/cookie-handler';

const navItems = [
  { title: 'Home', url: '/home', icon: Home },
  { title: 'Standings', url: '/standings', icon: TableProperties },
  { title: 'Matchups', url: '/matchups', icon: Swords },
  { title: 'Playoff Bracket', url: '/playoff_bracket', icon: Trophy },
  { title: 'Manager Comparison', url: '/manager_comparison', icon: Users },
  { title: 'Manager History', url: '/manager_history', icon: History },
  { title: 'Draft Recap', url: '/draft_recap', icon: Scroll },
  { title: 'Draft Grades', url: '/draft_grades', icon: GraduationCap },
  { title: 'Player Records', url: '/player_records', icon: Star },
  { title: 'Matchup Records', url: '/matchup_records', icon: Zap },
];

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { state, isMobile, setOpenMobile } = useSidebar();

  function closeMobileSidebar() {
    if (isMobile) setOpenMobile(false);
  }
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [subscriptionDialogOpen, setSubscriptionDialogOpen] = useState(false);

  const { expiringSoon } = useSubscription();

  const demoMode = isDemoMode();

  // Pre-fill (and lock) the platform/league ID on the refresh form with the
  // league the user is currently viewing.
  const { leagueId: currentLeagueId, platform: currentPlatform } =
    getLeagueCookies();
  const refreshLeagueUrl = currentLeagueId
    ? `/connect_league?leagueId=${encodeURIComponent(currentLeagueId)}&platform=${currentPlatform.toLowerCase()}`
    : '/connect_league';

  function handleExitDemo() {
    clearAllLeagueCookies();
    void navigate('/');
  }

  function handleConnectFromDemo() {
    clearAllLeagueCookies();
    void navigate('/?connect=true');
  }

  async function handleDeleteLeague() {
    const { leagueId, platform } = getLeagueCookies();

    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteLeague(leagueId, platform);
      clearApiCache();
      clearLeagueCookies();
      setDialogOpen(false);
      void navigate('/');
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
                    <Link to={item.url} onClick={closeMobileSidebar}>
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
                    onClick={() => {
                      closeMobileSidebar();
                      handleConnectFromDemo();
                    }}
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
                      <Link to={refreshLeagueUrl} onClick={closeMobileSidebar}>
                        <RefreshCw />
                        <span>Refresh League</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      asChild
                      tooltip="Migrate League"
                      className="cursor-pointer"
                    >
                      <Link to="/migrate_league" onClick={closeMobileSidebar}>
                        <ArrowLeftRight />
                        <span>Migrate League</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      asChild
                      tooltip="View Another League"
                      className="cursor-pointer"
                    >
                      <Link to="/?connect=true" onClick={closeMobileSidebar}>
                        <Search />
                        <span>View Another League</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      tooltip={
                        expiringSoon
                          ? 'Manage Subscription — expiring soon'
                          : 'Manage Subscription'
                      }
                      className="cursor-pointer"
                      onClick={() => {
                        closeMobileSidebar();
                        setSubscriptionDialogOpen(true);
                      }}
                    >
                      <span className="relative flex shrink-0 items-center justify-center">
                        <CreditCard />
                        {expiringSoon && (
                          <span
                            aria-hidden="true"
                            className="absolute -top-1 -right-1 size-2 rounded-full bg-destructive ring-2 ring-sidebar"
                          />
                        )}
                      </span>
                      <span>
                        Manage Subscription
                        {expiringSoon && (
                          <span className="sr-only"> (expiring soon)</span>
                        )}
                      </span>
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
                            This will permanently delete all data for this
                            league. This action cannot be undone.
                          </DialogDescription>
                        </DialogHeader>
                        {deleteError && (
                          <p className="text-sm text-destructive">
                            {deleteError}
                          </p>
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
        <ManageSubscriptionDialog
          open={subscriptionDialogOpen}
          onOpenChange={setSubscriptionDialogOpen}
        />
      </SidebarContent>
      <SidebarFooter className="p-3">
        {demoMode ? (
          <SidebarMenuButton
            tooltip="Exit Demo"
            className="cursor-pointer text-muted-foreground hover:text-foreground"
            onClick={() => {
              closeMobileSidebar();
              handleExitDemo();
            }}
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
