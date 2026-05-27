import { memo } from 'react';
import { Link } from 'react-router-dom';

import type { NavLinkItem } from '@/features/landing_page/types';

const linkClass = `
  flex items-center gap-1.5 px-3 py-1.5 rounded-md
  text-muted-foreground hover:text-foreground hover:bg-accent
  text-xs tracking-wide
  transition-colors duration-200
`;

export const NavLink = memo(function NavLink({ href, icon: Icon, label, external = true }: NavLinkItem) {
  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={linkClass}
      >
        <Icon size={13} className="opacity-70" />
        <span className="hidden sm:inline">{label}</span>
      </a>
    );
  }
  return (
    <Link to={href} className={linkClass}>
      <Icon size={13} className="opacity-70" />
      <span className="hidden sm:inline">{label}</span>
    </Link>
  );
});
