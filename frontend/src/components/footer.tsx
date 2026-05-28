import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { AboutDialog } from '@/features/about/about-dialog';
import { FOOTER_LINKS } from '@/features/landing_page/constants';

export default function Footer() {
  const [aboutOpen, setAboutOpen] = useState(false);
  const navigate = useNavigate();

  function handleFooterLinkClick(link: string) {
    if (link === 'About') {
      setAboutOpen(true);
    } else if (link === 'Privacy') {
      void navigate('/privacy');
    } else if (link === 'GitHub') {
      window.open('https://github.com/amolrairikar/leagueql-app', '_blank');
    }
  }

  return (
    <>
      <AboutDialog open={aboutOpen} onOpenChange={setAboutOpen} />
      <footer className="relative z-10 border-t border-border px-8 py-8 flex items-center justify-center">
        <div className="flex gap-6">
          {FOOTER_LINKS.map((l: string) => (
            <button
              key={l}
              type="button"
              onClick={() => handleFooterLinkClick(l)}
              className="
                text-[0.72rem] tracking-wide text-muted-foreground
                hover:text-foreground no-underline transition-colors duration-200
                bg-transparent border-none cursor-pointer p-0
              "
            >
              {l}
            </button>
          ))}
        </div>
      </footer>
    </>
  );
}
