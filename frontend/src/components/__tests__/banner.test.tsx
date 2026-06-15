import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Banner } from '../banner';

import { setFlagsForTesting } from '@/lib/feature-flags';

// FE-030: the banner is gated behind the `banner` flag and remembers a dismissal
// in localStorage. The global setup defaults flags to billing-only, so each test
// opts the flag in explicitly. jsdom's localStorage is not wired in this test env
// (the render helper never exercises it), so back the component with a fresh
// in-memory Storage per test — dismissals never leak between tests.
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => void store.set(key, String(value)),
    removeItem: (key) => void store.delete(key),
    clear: () => store.clear(),
    key: (index) => [...store.keys()][index] ?? null,
    get length() {
      return store.size;
    },
  } as Storage;
}

describe('Banner', () => {
  beforeEach(() => vi.stubGlobal('localStorage', createMemoryStorage()));
  afterEach(() => vi.unstubAllGlobals());

  it('renders nothing when the banner flag is off', () => {
    setFlagsForTesting({ banner: false });
    const { container } = render(<Banner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the banner message and link when the flag is on', () => {
    setFlagsForTesting({ banner: true });
    render(<Banner />);

    expect(screen.getByText(/Join the LeagueQL Discord/i)).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /community/i });
    expect(link).toHaveAttribute('href', expect.stringContaining('discord'));
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('hides the banner and remembers the dismissal when dismissed', async () => {
    setFlagsForTesting({ banner: true });
    const { unmount } = render(<Banner />);

    await userEvent.click(
      screen.getByRole('button', { name: /dismiss banner/i }),
    );
    expect(
      screen.queryByText(/Join the LeagueQL Discord/i),
    ).not.toBeInTheDocument();

    // Remounting (e.g. a fresh page load) keeps it hidden via localStorage.
    unmount();
    render(<Banner />);
    expect(
      screen.queryByText(/Join the LeagueQL Discord/i),
    ).not.toBeInTheDocument();
  });
});
