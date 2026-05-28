import { Link } from 'react-router-dom';

import { ModeToggle } from '@/components/mode-toggle';
import { NavLink } from '@/components/nav-link';
import { NAV_LINKS } from '@/features/landing_page/constants';
import type { NavLinkItem } from '@/features/landing_page/types';

export default function Header() {
  return (
    <nav
      className="
      fixed top-0 left-0 right-0 z-50
      flex items-center justify-between
      px-8 h-15
      bg-background/80 backdrop-blur-md
      border-b border-border
      "
    >
      <Link
        to="/"
        className="flex items-center gap-2 no-underline font-heading"
      >
        <span className="text-foreground text-xl tracking-tight">League<span className="text-primary font-bold">QL</span></span>
      </Link>

      <div className="flex items-center gap-1">
        {NAV_LINKS.map((link: NavLinkItem) => (
          <NavLink key={link.label} {...link} />
        ))}

        <div className="ml-2">
          <ModeToggle />
        </div>
      </div>
    </nav>
  );
}
