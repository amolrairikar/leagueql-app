/**
 * Feature-flag evaluation backed by OpenFeature (FE-026).
 *
 * Flag state lives in **AWS SSM Parameter Store** (global, per environment) and is
 * resolved at runtime from the backend's public `GET /feature-flags` endpoint — so a
 * console toggle reaches the SPA without a rebuild. There is no bundled config:
 * until {@link initFeatureFlags} resolves (and any time the backend is
 * unreachable) every flag fails safe to `false` (feature off).
 *
 * A `billing` flag currently gates all subscription UI (FE-021/022/023): when it
 * is off, `SubscriptionGuard` is a pass-through and the "Manage Subscription"
 * sidebar entry is hidden.
 *
 * Evaluation goes through OpenFeature's in-memory provider so the rest of the app
 * depends only on the vendor-neutral OpenFeature client. An unknown flag fails
 * safe to `false`.
 */
import { OpenFeature, InMemoryProvider } from '@openfeature/web-sdk';

import { API_BASE_URL } from '@/lib/api-client';

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

/**
 * Canonical serialization of a flag map (name → enabled, key-sorted) used to
 * detect whether the resolved flags actually changed. A refresh that returns the
 * same values — e.g. the `visibilitychange` refresh on every tab focus — must NOT
 * swap the provider, because swapping emits `PROVIDER_READY` /
 * `PROVIDER_CONFIGURATION_CHANGED`, which remounts the whole app (FE-026).
 */
function serializeFlags(config: Record<string, FlagSpec>): string {
  return JSON.stringify(
    Object.entries(config)
      .map(([name, spec]) => [name, spec?.enabled ?? false] as const)
      .sort(([a], [b]) => a.localeCompare(b)),
  );
}

/** The flag map currently installed on the active provider (see `serializeFlags`). */
let lastAppliedFlags = '';

/** Build the `InMemoryProvider` for a flag config and register it globally. */
function setProviderFromConfig(config: Record<string, FlagSpec>): void {
  lastAppliedFlags = serializeFlags(config);
  OpenFeature.setProvider(new InMemoryProvider(toFlagConfiguration(config)));
}

// Until initFeatureFlags() resolves the real values from the backend, every flag
// is off — there is no bundled config to fall back on. Also the fail-safe state
// whenever the flags endpoint is unreachable.
setProviderFromConfig({});

const client = OpenFeature.getClient();

/** Whether `flagName` is on; unknown flags default to `false`. */
export function isEnabled(flagName: string): boolean {
  return client.getBooleanValue(flagName, false);
}

/** Whether subscription/billing UI (FE-021/022/023) is enabled. */
export function isBillingEnabled(): boolean {
  return isEnabled('billing');
}

/** Whether the in-app informational banner (FE-030) is enabled. */
export function isBannerEnabled(): boolean {
  return isEnabled('banner');
}

/** Vitest sets this sentinel (see vite.config.ts); flag fetching stays off in tests. */
function isTestEnv(): boolean {
  return import.meta.env.VITE_API_URL === 'http://test.local';
}

/** Shape of the public `GET /feature-flags` payload (`{ name: enabled }` under `data`). */
interface FeatureFlagsPayload {
  data?: Record<string, boolean>;
}

/**
 * Fetch the global flags and register them. Any failure (non-200, network error,
 * unreachable backend) leaves the current provider in place, so the app keeps the
 * last-known — or the fail-safe all-off — flags rather than throwing.
 *
 * Exported for tests (the mapping seam); production code calls it via
 * {@link initFeatureFlags}, which gates it behind the Vitest check.
 */
export async function refreshFlags(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE_URL}/feature-flags`);
    if (!res.ok) return;
    const body = (await res.json()) as FeatureFlagsPayload;
    const flags = body.data ?? {};
    const config = Object.fromEntries(
      Object.entries(flags).map(([name, enabled]) => [name, { enabled }]),
    );
    // Only swap the provider when the values actually changed. An unchanged
    // refresh (the common case for the visibilitychange/poll refresh) must be a
    // no-op so it does not emit a provider event and remount the app (FE-026).
    if (serializeFlags(config) === lastAppliedFlags) return;
    setProviderFromConfig(config);
  } catch {
    // Keep the fail-safe provider; a transient outage must not flip flags on.
  }
}

// How often the SPA re-polls the flags so a console toggle is picked up without a
// reload. Paired with a refresh whenever the tab regains focus.
const REFRESH_INTERVAL_MS = 60_000;

let refreshStarted = false;

/**
 * Resolve feature flags from the backend and keep them fresh. Called once at
 * bootstrap (see `app/main.tsx`) before first render. A no-op under Vitest so
 * component tests never hit the network (MSW runs `onUnhandledRequest: 'error'`);
 * those drive flags via {@link setFlagsForTesting} instead.
 */
export async function initFeatureFlags(): Promise<void> {
  if (isTestEnv()) return;
  await refreshFlags();
  if (refreshStarted) return;
  refreshStarted = true;
  setInterval(() => void refreshFlags(), REFRESH_INTERVAL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void refreshFlags();
  });
}

/**
 * Replace the active provider with an explicit flag map (tests only). Lets a test
 * exercise the billing-on path without standing up the backend flags endpoint.
 */
export function setFlagsForTesting(flags: Record<string, boolean>): void {
  setProviderFromConfig(
    Object.fromEntries(
      Object.entries(flags).map(([name, enabled]) => [name, { enabled }]),
    ),
  );
}
