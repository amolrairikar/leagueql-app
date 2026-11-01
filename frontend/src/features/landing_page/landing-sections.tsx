import { ArrowRight, ChevronRight, HelpCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  FEATURES,
  HOW_STEPS,
  PLATFORMS,
  SUPPORT_EMAIL,
  YAHOO_BETA_SUPPORT_NOTE,
} from '@/features/landing_page/constants';
import { Faq } from '@/features/landing_page/faq';
import { ProductShowcase } from '@/features/landing_page/product-showcase';
import type { Feature, HowStep } from '@/features/landing_page/types';

/** Eyebrow + heading (+ optional blurb) shared by the marketing sections. */
function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="mx-auto mb-11 flex max-w-160 flex-col items-center gap-3 text-center">
      <span className="text-xs font-medium uppercase tracking-[0.16em] text-primary">
        {eyebrow}
      </span>
      <h2 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
        {title}
      </h2>
      {description && (
        <p className="max-w-lg text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

function FeatureCard({ icon: Icon, title, desc }: Feature) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-xs transition-all duration-200 hover:-translate-y-1 hover:border-primary/35 hover:shadow-lg">
      <div className="mb-4 grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">
        <Icon className="size-5.5" />
      </div>
      <h3 className="font-heading text-foreground mb-2 text-base font-semibold">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

function Step({ step, isLast }: { step: HowStep; isLast: boolean }) {
  const { icon: Icon } = step;
  return (
    <div className="relative z-10 rounded-2xl border border-border bg-card p-7">
      <div className="mb-4.5 flex items-center gap-3">
        <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-5.5" />
        </div>
        <span className="font-mono text-xs font-semibold tracking-wider text-primary">
          {step.step}
        </span>
      </div>
      <h3 className="font-heading mb-2 text-base font-semibold text-foreground">
        {step.title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">
        {step.desc}
      </p>
      {!isLast && (
        <div
          aria-hidden
          className="absolute top-1/2 -right-[41px] z-20 hidden size-[30px] -translate-y-1/2 place-items-center rounded-full border border-border bg-card text-primary shadow-sm md:grid"
        >
          <ChevronRight className="size-4" />
        </div>
      )}
    </div>
  );
}

export function ShowcaseSection() {
  return (
    <section className="relative z-10 px-6 pt-4 pb-8">
      <SectionHeader
        eyebrow="See it in action"
        title="Every angle of your league, one click away"
        description="Explore your league's complete history through rich, interactive views."
      />
      <ProductShowcase />
    </section>
  );
}

export function WorksWithSection() {
  return (
    <section className="relative z-10 px-6 py-8">
      <div className="mx-auto flex max-w-160 flex-wrap items-center justify-center gap-x-7 gap-y-4 border-y border-border py-5">
        <span className="w-full text-center text-xs uppercase tracking-[0.14em] text-muted-foreground sm:w-auto">
          Works with
        </span>
        {PLATFORMS.map((p) => (
          <span
            key={p.name}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm font-semibold"
          >
            <img src={p.logo} alt="" className="h-5 w-auto" />
            {p.name}
            {p.beta && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      className="inline-flex cursor-help items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wide text-primary"
                    >
                      Beta
                      <HelpCircle className="size-3" aria-hidden="true" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-72">
                    {YAHOO_BETA_SUPPORT_NOTE.before}
                    {SUPPORT_EMAIL}
                    {YAHOO_BETA_SUPPORT_NOTE.after}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </span>
        ))}
        <p className="w-full text-center text-sm text-muted-foreground">
          Don&apos;t see your league&apos;s fantasy platform here? Submit a
          feature{' '}
          <a
            href="https://leagueql.supahub.com/en"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            request
          </a>{' '}
          to get it added!
        </p>
      </div>
    </section>
  );
}

export function FeaturesSection() {
  return (
    <section className="relative z-10 px-6 pt-20 pb-8">
      <SectionHeader
        eyebrow="Everything, tracked"
        title="A record book that writes itself"
        description="Connect once and every stat, streak, and rivalry stays up to date, season after season."
      />
      <div className="mx-auto grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f) => (
          <FeatureCard key={f.title} {...f} />
        ))}
      </div>
    </section>
  );
}

export function HowItWorksSection() {
  return (
    <section className="relative z-10 px-6 pt-20 pb-8">
      <SectionHeader
        eyebrow="How it works"
        title="From league ID to full history in under a minute"
      />
      <div className="relative mx-auto grid max-w-5xl grid-cols-1 gap-[52px] md:grid-cols-3">
        <div
          aria-hidden
          className="absolute left-[10%] right-[10%] top-1/2 hidden h-0.5 -translate-y-px bg-gradient-to-r from-transparent via-border to-transparent md:block"
        />
        {HOW_STEPS.map((step, i) => (
          <Step
            key={step.step}
            step={step}
            isLast={i === HOW_STEPS.length - 1}
          />
        ))}
      </div>
    </section>
  );
}

export function FaqSection() {
  return (
    <section className="relative z-10 px-6 pt-20 pb-8">
      <SectionHeader
        eyebrow="FAQ"
        title="Before you connect"
        description="Everything you need to know about connecting and managing your league."
      />
      <Faq />
    </section>
  );
}

export function FinalCtaSection({
  onConnect,
  onViewDemo,
}: {
  onConnect: () => void;
  onViewDemo: () => void;
}) {
  return (
    <section className="relative z-10 px-6 pt-20 pb-16">
      <div className="relative mx-auto max-w-4xl overflow-hidden rounded-3xl border border-primary/30 bg-primary/[0.08] px-8 py-14 text-center">
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-[-60%] h-[500px] w-[600px] -translate-x-1/2"
          style={{
            background:
              'radial-gradient(50% 50% at 50% 50%, color-mix(in oklab, var(--chart-3) 24%, transparent), transparent 70%)',
          }}
        />
        <h2 className="font-heading relative text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Your league history should be preserved
        </h2>
        <p className="relative mx-auto mt-4 mb-7 max-w-md text-muted-foreground">
          Connect in seconds and see your entire history come to life.
        </p>
        <div className="relative flex flex-wrap justify-center gap-3">
          <Button
            size="lg"
            className="text-[0.82rem] px-6 cursor-pointer"
            onClick={onConnect}
          >
            Connect Your League <ArrowRight />
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="text-[0.82rem] px-6 cursor-pointer"
            onClick={onViewDemo}
          >
            View Demo
          </Button>
        </div>
      </div>
    </section>
  );
}
