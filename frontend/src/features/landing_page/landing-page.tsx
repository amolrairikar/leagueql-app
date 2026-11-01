import { SignIn } from '@clerk/react';

import Footer from '@/components/footer';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { LandingHero } from '@/features/landing_page/landing-hero';
import {
  FaqSection,
  FeaturesSection,
  FinalCtaSection,
  HowItWorksSection,
  ShowcaseSection,
  WorksWithSection,
} from '@/features/landing_page/landing-sections';
import { useLandingPage } from '@/features/landing_page/use-landing-page';

export default function LeagueQLLanding() {
  const state = useLandingPage();
  const { authOpen, setAuthOpen, handleConnectLeague, handleViewDemo } = state;

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans overflow-x-hidden">
      {/* Decorative fixed grid + primary glow */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(var(--border) 1px, transparent 1px),
            linear-gradient(90deg, var(--border) 1px, transparent 1px)
          `,
          backgroundSize: '52px 52px',
          maskImage:
            'radial-gradient(ellipse 90% 55% at 50% 0%, #000 30%, transparent 78%)',
          WebkitMaskImage:
            'radial-gradient(ellipse 90% 55% at 50% 0%, #000 30%, transparent 78%)',
          opacity: 0.5,
        }}
      />
      <div
        className="fixed left-1/2 top-[-14%] -z-0 h-[640px] w-[820px] -translate-x-1/2 pointer-events-none blur-2xl"
        style={{
          background:
            'radial-gradient(50% 50% at 50% 50%, color-mix(in oklab, var(--chart-3) 30%, transparent) 0%, transparent 70%)',
        }}
      />

      <LandingHero s={state} />

      <Dialog open={authOpen} onOpenChange={setAuthOpen}>
        <DialogContent
          className="p-0 overflow-hidden w-auto max-w-none bg-transparent border-none shadow-none ring-0"
          showCloseButton={false}
        >
          <DialogTitle className="sr-only">Sign in to LeagueQL</DialogTitle>
          <SignIn
            routing="hash"
            forceRedirectUrl="/?connect=true"
            signUpForceRedirectUrl="/?connect=true"
          />
        </DialogContent>
      </Dialog>

      <ShowcaseSection />

      <WorksWithSection />

      <FeaturesSection />

      <HowItWorksSection />

      <FaqSection />

      <FinalCtaSection
        onConnect={handleConnectLeague}
        onViewDemo={handleViewDemo}
      />

      <Footer className="mt-auto" />

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(18px); }
          to   { opacity: 1; transform: translateY(0);    }
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-\\[fadeUp_0\\.6s_0\\.1s_both\\],
          .animate-\\[fadeUp_0\\.6s_0\\.25s_both\\],
          .animate-\\[fadeUp_0\\.6s_0\\.4s_both\\],
          .animate-\\[fadeUp_0\\.6s_0\\.55s_both\\],
          .animate-\\[fadeUp_0\\.4s_both\\] { animation: none; }
        }
      `}</style>
    </div>
  );
}
