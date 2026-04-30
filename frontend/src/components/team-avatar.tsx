import { useCallback, useState } from 'react';

import { AVATAR_COLORS } from '@/lib/color-constants';

export { AVATAR_COLORS };

export function avatarColor(index: number): string {
  return AVATAR_COLORS[index % AVATAR_COLORS.length] as string;
}

function initials(username: string): string {
  const parts = username
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length >= 2)
    return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase();
  return username.slice(0, 2).toUpperCase();
}

export function TeamAvatar({
  teamLogo,
  teamName,
  ownerUsername,
  color,
  size = 'sm',
}: {
  teamLogo: string | null | undefined;
  teamName: string;
  ownerUsername: string;
  color: string;
  size?: 'sm' | 'lg';
}) {
  const [imgError, setImgError] = useState(false);
  const handleError = useCallback(() => setImgError(true), []);

  return (
    <div
      className={`${
        size === 'lg' ? 'w-10 h-10 text-sm' : 'w-7 h-7 text-[11px]'
      } rounded-full overflow-hidden shrink-0 flex items-center justify-center font-medium text-white`}
      style={{ background: color }}
    >
      {teamLogo && !imgError ? (
        <img
          src={teamLogo}
          alt={teamName}
          className="w-full h-full object-cover"
          onError={handleError}
        />
      ) : (
        initials(ownerUsername)
      )}
    </div>
  );
}
