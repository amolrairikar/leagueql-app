import { type LucideProps } from 'lucide-react';
import { Link } from 'react-router-dom';

import { ModeToggle } from '@/components/mode-toggle';
import { NAV_LINKS } from '@/features/landing_page/constants';
import type { NavLinkItem } from '@/features/landing_page/types';

interface NavLinkProps {
  href: string;
  icon: React.FC<LucideProps>;
  label: string;
}

function NavLink({ href, icon: Icon, label }: NavLinkProps) {
  return (
    <a
      href={href}
      className="
        flex items-center gap-1.5 px-3 py-1.5 rounded-md
        text-muted-foreground hover:text-foreground hover:bg-accent
        font-mono text-xs tracking-wide
        transition-colors duration-200
      "
    >
      <Icon size={13} className="opacity-70" />
      <span className="hidden sm:inline">{label}</span>
    </a>
  );
}

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
      <Link to="/" className="flex items-center gap-2 no-underline font-heading">
        <span className="w-1.75 h-1.75 rounded-full bg-primary inline-block" />
        <span className="text-foreground text-xl tracking-tight">LeagueQL</span>
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
