import { UserButton } from '@clerk/react';

import { useSidebar } from '@/components/ui/sidebar';
import { isDemoMode } from '@/lib/cookie-handler';

/**
 * Account menu (Clerk `UserButton`) rendered in the app header on mobile.
 *
 * On mobile the sidebar is a modal sheet, which locks `pointer-events` on
 * everything outside its own content. Clerk's `UserButton` dropdown portals to
 * `document.body` (outside the sheet), so taps on its items — including "Sign
 * out" — fall through to the sidebar links beneath it and the sign-out button is
 * never actually clicked (FE-014 / FE-019). Rendering the account menu in the
 * always-present header (outside the sheet) keeps sign-out working on mobile.
 *
 * On desktop the sidebar is not a modal sheet, so the avatar stays in the
 * sidebar footer (`app-sidebar.tsx`) and this renders nothing.
 */
export function HeaderAccount() {
  const { isMobile } = useSidebar();
  if (!isMobile || isDemoMode()) return null;
  // ml-2 keeps a little breathing room between the theme toggle and the avatar
  // (shifting the nav/theme icons left, since the cluster is right-anchored).
  // Lives here so it only applies on mobile and never affects desktop.
  return (
    <div className="ml-2 flex items-center">
      <UserButton />
    </div>
  );
}
