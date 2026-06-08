import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from '../error-boundary';

// A child that throws on demand so we can drive the boundary into its error state.
function Bomb({ explode }: { explode: boolean }) {
  if (explode) throw new Error('boom');
  return <p>safe content</p>;
}

// Wraps the boundary in state so a test can flip the thrown error and the
// resetKeys array independently — mirroring a route change clearing the error.
function Harness() {
  const [explode, setExplode] = useState(true);
  const [routeKey, setRouteKey] = useState('/draft_recap');
  return (
    <>
      <button onClick={() => setExplode(false)}>stop throwing</button>
      <button onClick={() => setRouteKey('/home')}>navigate</button>
      <ErrorBoundary resetKeys={[routeKey]}>
        <Bomb explode={explode} />
      </ErrorBoundary>
    </>
  );
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // React logs caught render errors to console.error; silence the noise.
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the fallback when a child throws', () => {
    render(
      <ErrorBoundary>
        <Bomb explode />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('boom')).toBeInTheDocument();
  });

  it('clears a caught error when resetKeys change (e.g. on navigation)', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    // The boundary is in its error state from the initial throw.
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Stop the child throwing, then change the reset key — the boundary should
    // clear and re-render the now-safe children rather than stay stuck.
    await user.click(screen.getByText('stop throwing'));
    await user.click(screen.getByText('navigate'));

    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
    expect(screen.getByText('safe content')).toBeInTheDocument();
  });

  it('stays in the error state when resetKeys are unchanged', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Child stops throwing but the key never changes — without a reset the
    // boundary keeps showing the fallback (the bug we are guarding against
    // is the inverse: a *changed* key must clear it).
    await user.click(screen.getByText('stop throwing'));

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
