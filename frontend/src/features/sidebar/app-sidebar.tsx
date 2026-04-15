import { UserButton } from '@clerk/react';
import { FlaskConical, TableProperties, Trash2 } from 'lucide-react';
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

const navItems = [
  { title: 'Standings', url: '/standings', icon: TableProperties },
  { title: 'Test', url: '/test', icon: FlaskConical },
];

function getCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
}

function clearLeagueCookies() {
  document.cookie = 'leagueId=; path=/; max-age=0';
  document.cookie = 'leaguePlatform=; path=/; max-age=0';
}

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { state } = useSidebar();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDeleteLeague() {
    const leagueId = getCookie('leagueId');
    const platform = (getCookie('leaguePlatform') || 'ESPN') as
      | 'ESPN'
      | 'SLEEPER';

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
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-3">
        <UserButton showName={state === 'expanded'} />
      </SidebarFooter>
    </Sidebar>
  );
}
