import { act, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FeatureFlagProvider } from '../feature-flags-provider';

import { isBannerEnabled, setFlagsForTesting } from '@/lib/feature-flags';

// A leaf that reads the synchronous flag helper, so the only way its text
// updates is if FeatureFlagProvider forces a re-render on a provider change.
function BannerProbe() {
  return <span>banner:{isBannerEnabled() ? 'on' : 'off'}</span>;
}

describe('FeatureFlagProvider', () => {
  it('re-renders flag call sites when the provider changes', async () => {
    setFlagsForTesting({ banner: true });
    render(
      <FeatureFlagProvider>
        <BannerProbe />
      </FeatureFlagProvider>,
    );
    expect(await screen.findByText('banner:on')).toBeInTheDocument();

    // A runtime toggle swaps the provider; OpenFeature emits PROVIDER_READY
    // asynchronously, which the provider listens for and bumps state so the probe
    // re-evaluates the flag. Flush the microtask inside act so React commits.
    await act(async () => {
      setFlagsForTesting({ banner: false });
      await Promise.resolve();
    });
    await waitFor(() =>
      expect(screen.getByText('banner:off')).toBeInTheDocument(),
    );
  });
});
