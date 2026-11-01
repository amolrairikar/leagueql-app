import { AVATAR_COLORS } from '@/lib/color-constants';

export interface Team {
  team_id: string;
  display_name: string;
  team_name: string;
  team_logo: string | null;
}

// Generate consistent color from team ID
export function getTeamColor(teamId: string): string {
  let hash = 0;
  for (let i = 0; i < teamId.length; i++) {
    hash = teamId.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}
