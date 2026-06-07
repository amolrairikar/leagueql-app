/**
 * Feature-flag evaluation backed by OpenFeature (FE-026).
 *
 * Flag state is read at build time from `src/config/feature-flags.json`, which
 * maps a flag name to `{ "enabled": <bool> }`. The config is baked into the
 * bundle, so toggling a flag is a one-line edit to that JSON followed by a
 * frontend rebuild/redeploy. Keep it in sync with the backend's
 * `src/common/feature_flags.json`.
 *
 * A single `billing` flag currently gates all subscription UI (FE-021/022/023):
 * when it is off, `SubscriptionGuard` is a pass-through and the "Manage
 * Subscription" sidebar entry is hidden.
 *
 * Evaluation goes through OpenFeature's in-memory provider so the rest of the app
 * depends only on the vendor-neutral OpenFeature client. An unknown flag fails
 * safe to `false` (feature off).
 */
import { OpenFeature, InMemoryProvider } from '@openfeature/web-sdk';

import flagConfig from '@/config/feature-flags.json';

interface FlagSpec {
  enabled?: boolean;
}

/** Convert the `{ name: { enabled } }` config into an OpenFeature flag map. */
function toFlagConfiguration(config: Record<string, FlagSpec>) {
  return Object.fromEntries(
    Object.entries(config).map(([name, spec]) => [
      name,
      {
        variants: { on: true, off: false },
        defaultVariant: spec?.enabled ? 'on' : 'off',
        disabled: false,
      },
    ]),
  );
}

OpenFeature.setProvider(
  new InMemoryProvider(
    toFlagConfiguration(flagConfig as Record<string, FlagSpec>),
  ),
);

const client = OpenFeature.getClient();

/** Whether `flagName` is on; unknown flags default to `false`. */
export function isEnabled(flagName: string): boolean {
  return client.getBooleanValue(flagName, false);
}

/** Whether subscription/billing UI (FE-021/022/023) is enabled. */
export function isBillingEnabled(): boolean {
  return isEnabled('billing');
}

/**
 * Replace the active provider with an explicit flag map (tests only). Lets a test
 * exercise the billing-on path without editing the bundled config file.
 */
export function setFlagsForTesting(flags: Record<string, boolean>): void {
  OpenFeature.setProvider(
    new InMemoryProvider(
      toFlagConfiguration(
        Object.fromEntries(
          Object.entries(flags).map(([name, enabled]) => [name, { enabled }]),
        ),
      ),
    ),
  );
}
