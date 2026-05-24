import { memo } from 'react';

import type { NavLinkItem } from '@/features/landing_page/types';

export const NavLink = memo(function NavLink({ href, icon: Icon, label }: NavLinkItem) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="
        flex items-center gap-1.5 px-3 py-1.5 rounded-md
        text-muted-foreground hover:text-foreground hover:bg-accent
        text-xs tracking-wide
        transition-colors duration-200
      "
    >
      <Icon size={13} className="opacity-70" />
      <span className="hidden sm:inline">{label}</span>
    </a>
  );
});
