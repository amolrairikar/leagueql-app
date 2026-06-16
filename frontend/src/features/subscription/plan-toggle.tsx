import type { SubscriptionPlan } from '@/components/api/types';
import { SUBSCRIPTION_PRICES } from '@/lib/pricing';
import { cn } from '@/lib/utils';

const OPTIONS: {
  value: SubscriptionPlan;
  label: string;
  price: string;
  hint?: string;
}[] = [
  {
    value: 'MONTHLY',
    label: 'Monthly',
    price: `${SUBSCRIPTION_PRICES.MONTHLY}/mo`,
  },
  {
    value: 'YEARLY',
    label: 'Yearly',
    price: `${SUBSCRIPTION_PRICES.YEARLY}/yr`,
    hint: 'Save ~58%',
  },
];

/**
 * Segmented monthly/yearly picker for the subscription plan (FE-022). Both plans
 * gate the same premium features; the choice only selects which Stripe price the
 * checkout session uses. Each option shows its price for full transparency before
 * checkout. Rendered above the Subscribe CTA in the locked overlay and the Manage
 * Subscription dialog.
 */
export function PlanToggle({
  value,
  onChange,
  disabled,
}: {
  value: SubscriptionPlan;
  onChange: (plan: SubscriptionPlan) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Subscription plan"
      className="bg-muted inline-flex rounded-lg p-1"
    >
      {OPTIONS.map((opt) => {
        const selected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={cn(
              'flex cursor-pointer flex-col items-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              selected
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <span>
              {opt.label}
              {opt.hint && (
                <span className="text-primary ml-1.5 text-xs">{opt.hint}</span>
              )}
            </span>
            <span className="text-muted-foreground text-xs font-normal">
              {opt.price}
            </span>
          </button>
        );
      })}
    </div>
  );
}
