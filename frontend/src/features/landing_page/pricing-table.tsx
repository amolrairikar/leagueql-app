import { Check } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  PREMIUM_FEATURES,
  PRICING_PLANS,
} from '@/features/landing_page/constants';
import type {
  PremiumFeature,
  PricingPlan,
} from '@/features/landing_page/types';
import { cn } from '@/lib/utils';

/**
 * Pricing table on the landing page (FE-001), rendered below the feature grid.
 *
 * Shows the subscription plans (`PRICING_PLANS`) and the premium features a
 * subscription unlocks (`PREMIUM_FEATURES`). Each plan's CTA runs the same
 * connect-league flow as the hero CTA via `onGetStarted`. The caller only mounts
 * this when the `billing` flag is on (premium features are free otherwise).
 */
export function PricingTable({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <section className="relative z-10 px-6 pb-24">
      <div className="max-w-215 mx-auto">
        <div className="text-center mb-10">
          <h2 className="font-heading text-foreground text-2xl mb-3">
            Pricing
          </h2>
          <p className="text-sm text-muted-foreground max-w-120 mx-auto leading-relaxed">
            LeagueQL is free to use. A subscription unlocks premium features for
            your league. All subscriptions come with a 14 day trial.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {PRICING_PLANS.map((plan: PricingPlan) => (
            <div
              key={plan.name}
              className={cn(
                'relative bg-card border rounded-xl p-7',
                plan.highlight ? 'border-primary' : 'border-border',
              )}
            >
              {plan.badge && (
                <span className="absolute top-5 right-5 rounded-full bg-primary/15 text-primary text-xs px-2.5 py-0.5">
                  {plan.badge}
                </span>
              )}
              <h3 className="font-heading text-foreground text-base mb-3">
                {plan.name}
              </h3>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold text-foreground">
                  {plan.price}
                </span>
                <span className="text-sm text-muted-foreground">
                  {plan.period}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {plan.billedAs}
              </p>
              <Button
                className="w-full mt-5 cursor-pointer"
                variant={plan.highlight ? 'default' : 'outline'}
                onClick={onGetStarted}
              >
                Get started
              </Button>
            </div>
          ))}
        </div>

        <div className="bg-card border border-border rounded-xl p-7">
          <h3 className="font-heading text-foreground text-base mb-1">
            Premium features
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            Included with any subscription:
          </p>
          <ul className="flex flex-col gap-3">
            {PREMIUM_FEATURES.map((f: PremiumFeature) => (
              <li key={f.title} className="flex items-start gap-3">
                <Check className="size-4 text-primary mt-0.5 shrink-0" />
                <div>
                  <span className="text-sm text-foreground font-medium">
                    {f.title}
                  </span>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
