import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useCopyToClipboard } from '../use-copy-to-clipboard';

/** Flush pending microtasks (e.g. the resolved clipboard.writeText promise). */
async function flushMicrotasks() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe('useCopyToClipboard', () => {
  let writeText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('writes the value and flips copied true then clears after the delay', async () => {
    const { result } = renderHook(() => useCopyToClipboard(2000));
    expect(result.current.copied).toBe(false);

    act(() => {
      result.current.copy('hello');
    });
    expect(writeText).toHaveBeenCalledWith('hello');

    await flushMicrotasks();
    expect(result.current.copied).toBe(true);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });
    expect(result.current.copied).toBe(false);
  });

  it('resetCopied clears the flag immediately', async () => {
    const { result } = renderHook(() => useCopyToClipboard());
    act(() => {
      result.current.copy('x');
    });
    await flushMicrotasks();
    expect(result.current.copied).toBe(true);

    act(() => {
      result.current.resetCopied();
    });
    expect(result.current.copied).toBe(false);
  });
});
