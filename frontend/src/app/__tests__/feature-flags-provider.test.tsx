import { act, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FeatureFlagProvider } from '../feature-flags-provider';

import { isBillingEnabled, setFlagsForTesting } from '@/lib/feature-flags';

// A leaf that reads the synchronous flag helper, so the only way its text
// updates is if FeatureFlagProvider forces a re-render on a provider change.
function BillingProbe() {
  return <span>billing:{isBillingEnabled() ? 'on' : 'off'}</span>;
}

describe('FeatureFlagProvider', () => {
  it('re-renders flag call sites when the provider changes', async () => {
    setFlagsForTesting({ billing: true });
    render(
      <FeatureFlagProvider>
        <BillingProbe />
      </FeatureFlagProvider>,
    );
    expect(await screen.findByText('billing:on')).toBeInTheDocument();

    // A runtime toggle swaps the provider; OpenFeature emits PROVIDER_READY
    // asynchronously, which the provider listens for and bumps state so the probe
    // re-evaluates the flag. Flush the microtask inside act so React commits.
    await act(async () => {
      setFlagsForTesting({ billing: false });
      await Promise.resolve();
    });
    await waitFor(() =>
      expect(screen.getByText('billing:off')).toBeInTheDocument(),
    );
  });
});
