import { type NewPlatformUser } from '@/features/migrate_league/types';

export function getUserId(user: NewPlatformUser): string {
  return 'user_id' in user ? user.user_id : user.owner_id;
}

export function getUserDisplayName(user: NewPlatformUser): string {
  return (
    user.display_name || ('username' in user ? user.username : user.owner_id)
  );
}
