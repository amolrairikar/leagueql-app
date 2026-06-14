import { OpenFeature, ProviderEvents } from '@openfeature/web-sdk';
import { Fragment, useEffect, useState, type ReactNode } from 'react';

/**
 * Re-render the synchronous `isEnabled()` call sites when the flag provider
 * changes at runtime (FE-026).
 *
 * The flag helpers (`@/lib/feature-flags`) are synchronous reads of the
 * OpenFeature client, and the call sites (sidebar, subscription guard, docs,
 * landing) take no flag props — so bumping state on a wrapper would not re-render
 * them (their element identity is unchanged, React bails out). Instead, when a
 * runtime toggle swaps the provider (`initFeatureFlags`' poll → new provider →
 * `PROVIDER_READY` / `PROVIDER_CONFIGURATION_CHANGED`), remount the subtree via a
 * changing `key` so every call site re-evaluates its flags.
 *
 * The initial flags are resolved before first paint (see `app/main.tsx`), so the
 * synchronous handler fire for the already-applied provider is skipped — the app
 * remounts only on a genuine later change, which is a rare operator action.
 */
export function FeatureFlagProvider({ children }: { children: ReactNode }) {
  const [version, setVersion] = useState(0);

  useEffect(() => {
    // OpenFeature invokes a READY handler immediately when the provider is
    // already ready; that first fire is the initial flags (already rendered), so
    // ignore it and only remount on subsequent changes.
    let seenInitial = false;
    const onChange = () => {
      if (!seenInitial) {
        seenInitial = true;
        return;
      }
      setVersion((v) => v + 1);
    };
    OpenFeature.addHandler(ProviderEvents.Ready, onChange);
    OpenFeature.addHandler(ProviderEvents.ConfigurationChanged, onChange);
    return () => {
      OpenFeature.removeHandler(ProviderEvents.Ready, onChange);
      OpenFeature.removeHandler(ProviderEvents.ConfigurationChanged, onChange);
    };
  }, []);

  return <Fragment key={version}>{children}</Fragment>;
}
