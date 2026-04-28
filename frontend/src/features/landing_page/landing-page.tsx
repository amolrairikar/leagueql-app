import { SignIn, useUser } from '@clerk/react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { AboutDialog } from '@/features/about/about-dialog';
import { PrivacyDialog } from '@/features/privacy/privacy-dialog';
import {
  SLIDES,
  FEATURES,
  FOOTER_LINKS,
} from '@/features/landing_page/constants';
import type { Slide, Feature } from '@/features/landing_page/types';

interface ScreenshotPlaceholderProps {
  title: string;
  badge: string;
}

function ScreenshotPlaceholder({ title, badge }: ScreenshotPlaceholderProps) {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-4 bg-card">
      <div className="flex flex-col items-center gap-2 opacity-40">
        <svg
          width="48"
          height="48"
          viewBox="0 0 48 48"
          fill="none"
          className="text-primary"
        >
          <rect
            x="4"
            y="4"
            width="18"
            height="18"
            rx="3"
            fill="currentColor"
            fillOpacity="0.3"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <rect
            x="26"
            y="4"
            width="18"
            height="18"
            rx="3"
            fill="currentColor"
            fillOpacity="0.15"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <rect
            x="4"
            y="26"
            width="18"
            height="18"
            rx="3"
            fill="currentColor"
            fillOpacity="0.15"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <rect
            x="26"
            y="26"
            width="18"
            height="18"
            rx="3"
            fill="currentColor"
            fillOpacity="0.3"
            stroke="currentColor"
            strokeWidth="1.5"
          />
        </svg>
        <p className="font-mono text-xs text-muted-foreground tracking-widest uppercase">
          Screenshot placeholder
        </p>
        <p className="font-mono text-[0.65rem] text-muted-foreground/60">
          {title} · {badge}
        </p>
      </div>
    </div>
  );
}

interface BrowserChromeProps {
  url: string;
}

function BrowserChrome({ url }: BrowserChromeProps) {
  return (
    <div className="bg-secondary/50 border-b border-border px-3.5 py-2.5 flex items-center gap-3">
      <div className="flex gap-1.25">
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: '#FF5F57' }}
        />
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: '#FFBD2E' }}
        />
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: '#28C840' }}
        />
      </div>
      <div className="flex-1 bg-background/50 rounded h-5.5 flex items-center px-2.5">
        <span className="font-mono text-[0.68rem] text-muted-foreground">
          {url}
        </span>
      </div>
    </div>
  );
}

function Slideshow() {
  const [current, setCurrent] = useState<number>(0);

  const goTo = useCallback((n: number): void => {
    setCurrent(((n % SLIDES.length) + SLIDES.length) % SLIDES.length);
  }, []);

  const next = useCallback((): void => goTo(current + 1), [current, goTo]);
  const prev = useCallback((): void => goTo(current - 1), [current, goTo]);

  useEffect(() => {
    const t = setInterval(next, 4000);
    return () => clearInterval(t);
  }, [next]);

  const slide: Slide = SLIDES[current];

  return (
    <section className="relative z-10 px-6 pb-24">
      <div className="max-w-215 mx-auto">
        <div className="rounded-xl overflow-hidden border border-border bg-card shadow-2xl">
          <BrowserChrome url={slide.url} />

          <div className="relative h-120 overflow-hidden">
            {SLIDES.map((s: Slide, i: number) => (
              <div
                key={i}
                className={`
                  absolute inset-0 transition-opacity duration-500
                  ${i === current ? 'opacity-100' : 'opacity-0 pointer-events-none'}
                `}
              >
                {s.image ? (
                  <img
                    src={s.image}
                    alt={s.title}
                    className="w-full h-full object-contain bg-card"
                  />
                ) : (
                  <ScreenshotPlaceholder title={s.title} badge={s.badge} />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-center gap-6 mt-5">
          <button
            onClick={prev}
            aria-label="Previous slide"
            className="
              w-9 h-9 rounded-full flex items-center justify-center
              bg-card border border-border text-muted-foreground
              hover:bg-accent hover:text-foreground
              transition-colors duration-200
            "
          >
            <ChevronLeft size={16} />
          </button>

          <div className="flex gap-1.5">
            {SLIDES.map((_: Slide, i: number) => (
              <button
                key={i}
                onClick={() => goTo(i)}
                aria-label={`Go to slide ${i + 1}`}
                className={`
                  h-1.5 rounded-full transition-all duration-300
                  ${
                    i === current
                      ? 'w-4.5 bg-primary'
                      : 'w-1.5 bg-border hover:bg-muted-foreground/30'
                  }
                `}
              />
            ))}
          </div>

          <button
            onClick={next}
            aria-label="Next slide"
            className="
              w-9 h-9 rounded-full flex items-center justify-center
              bg-card border border-border text-muted-foreground
              hover:bg-accent hover:text-foreground
              transition-colors duration-200
            "
          >
            <ChevronRight size={16} />
          </button>
        </div>

        <p className="text-center font-mono text-[0.7rem] text-muted-foreground tracking-wide mt-3">
          {slide.caption}
        </p>
      </div>
    </section>
  );
}

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
  const [privacyOpen, setPrivacyOpen] = useState(false);

  function handleConnectLeague() {
    if (isSignedIn) {
      void navigate('/league');
    } else {
      setAuthOpen(true);
    }
  }

  function handleViewDemo() {
    const seasons = encodeURIComponent(JSON.stringify(['2022', '2023', '2024']));
    document.cookie = 'leagueId=999999999; path=/; max-age=86400';
    document.cookie = 'leaguePlatform=ESPN; path=/; max-age=86400';
    document.cookie = `leagueSeasons=${seasons}; path=/; max-age=86400`;
    document.cookie = 'demo_mode=true; path=/; max-age=86400';
    void navigate('/standings');
  }

  function handleFooterLinkClick(link: string) {
    if (link === 'About') {
      setAboutOpen(true);
    } else if (link === 'Privacy') {
      setPrivacyOpen(true);
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
      <PrivacyDialog open={privacyOpen} onOpenChange={setPrivacyOpen} />

      <Slideshow />

      <section className="relative z-10 px-6 pb-24">
        <h2 className="text-center text-[2rem] font-heading tracking-tight text-foreground mb-2">
          Your league&apos;s full story, in one place
        </h2>
        <p className="text-center text-muted-foreground text-sm mb-12">
          Every matchup, milestone, and memory — going back to season one
        </p>

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
