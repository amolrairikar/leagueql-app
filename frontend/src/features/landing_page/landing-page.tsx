import { SignIn, useUser } from '@clerk/react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { setDemoMode } from '@/lib/cookie-handler';
import { DEMO_SEASONS } from '@/lib/demo-constants';
import { AboutDialog } from '@/features/about/about-dialog';
import {
  FEATURES,
  FOOTER_LINKS,
} from '@/features/landing_page/constants';
import type { Feature } from '@/features/landing_page/types';


interface FeatureCardProps {
  icon: string;
  title: string;
  desc: string;
}

function FeatureCard({ icon, title, desc }: FeatureCardProps) {
  return (
    <div className="bg-card p-7 hover:bg-accent/50 transition-colors duration-200">
      <div className="text-xl mb-3">{icon}</div>
      <h3 className="font-heading text-foreground text-base mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

export default function LeagueQLLanding() {
  const { isSignedIn } = useUser();
  const navigate = useNavigate();
  const [authOpen, setAuthOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);

  function handleConnectLeague() {
    if (isSignedIn) {
      void navigate('/league');
    } else {
      setAuthOpen(true);
    }
  }

  function handleViewDemo() {
    setDemoMode(DEMO_SEASONS);
    void navigate('/home');
  }

  function handleFooterLinkClick(link: string) {
    if (link === 'About') {
      setAboutOpen(true);
    } else if (link === 'Privacy') {
      void navigate('/privacy');
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden">
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(var(--border) 1px, transparent 1px),
            linear-gradient(90deg, var(--border) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          opacity: 0.2,
        }}
      />

      <section className="relative z-10 flex flex-col items-center text-center px-6 pt-36 pb-20">
        <h1
          className="
            text-[clamp(2.6rem,6vw,4.5rem)] leading-[1.1] tracking-tight
            text-foreground max-w-175 font-heading
            animate-[fadeUp_0.6s_0.25s_both]
          "
        >
          Your league&apos;s story,{' '}
          <em className="italic text-primary">beautifully told</em>
        </h1>

        <p
          className="
          mt-5 text-base text-muted-foreground max-w-120 leading-relaxed
          animate-[fadeUp_0.6s_0.4s_both]
          "
        >
          Explore every season, rivalry, and record across your league&apos;s
          full history — from the first draft pick to the last championship.
        </p>

        <div className="flex gap-3 mt-9 animate-[fadeUp_0.6s_0.55s_both]">
          <Button
            size="lg"
            className="font-mono text-[0.82rem] px-6 cursor-pointer"
            onClick={handleConnectLeague}
          >
            Connect Your League
          </Button>

          <Button
            variant="outline"
            size="lg"
            className="font-mono text-[0.82rem] px-6 cursor-pointer"
            onClick={handleViewDemo}
          >
            View Demo
          </Button>
        </div>

      </section>

      <Dialog open={authOpen} onOpenChange={setAuthOpen}>
        <DialogContent
          className="p-0 overflow-hidden w-auto max-w-none bg-transparent border-none shadow-none ring-0"
          showCloseButton={false}
        >
          <DialogTitle className="sr-only">Sign in to LeagueQL</DialogTitle>
          <SignIn
            routing="hash"
            forceRedirectUrl="/league"
            signUpForceRedirectUrl="/league"
          />
        </DialogContent>
      </Dialog>

      <AboutDialog open={aboutOpen} onOpenChange={setAboutOpen} />

      <section className="relative z-10 px-6 pb-24">
        <div
          className="
          max-w-215 mx-auto
          grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
          border border-border rounded-xl overflow-hidden
          divide-x divide-y divide-border
          "
        >
          {FEATURES.map((f: Feature) => (
            <FeatureCard key={f.title} {...f} />
          ))}
        </div>
      </section>

      <footer
        className="
        relative z-10 border-t border-border
        px-8 py-8 flex flex-wrap items-center justify-between gap-4
        "
      >
        <a
          href="#"
          className="text-muted-foreground no-underline font-heading text-lg"
        >
          LeagueQL
        </a>

        <div className="flex gap-6">
          {FOOTER_LINKS.map((l: string) => (
            <button
              key={l}
              type="button"
              onClick={() => handleFooterLinkClick(l)}
              className="
                font-mono text-[0.72rem] tracking-wide text-muted-foreground
                hover:text-foreground no-underline transition-colors duration-200
                bg-transparent border-none cursor-pointer p-0
              "
            >
              {l}
            </button>
          ))}
        </div>

        <span className="font-mono text-[0.68rem] text-muted-foreground/50">
          © 2026 Amol Rairikar
        </span>
      </footer>

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(18px); }
          to   { opacity: 1; transform: translateY(0);    }
        }
      `}</style>
    </div>
  );
}
