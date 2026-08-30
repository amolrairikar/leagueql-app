import { getJobStatus } from '@/features/connect_league/api-calls';

/** Resolve after `ms` milliseconds. */
export const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

const MAX_CONSECUTIVE_ERRORS = 3;
const POLL_INTERVAL_MS = 1000;
// The backend can take a while end-to-end (the processor alone runs up to 120s on
// large leagues), so poll long enough to actually observe COMPLETED rather than
// giving up early and showing a false failure.
const POLL_TIMEOUT_MS = 150000;

export interface PollResult {
  status: 'success' | 'failed';
  failureReason?: string;
  failureCode?: string;
}

/**
 * Poll an onboard/refresh/migrate job's status until it terminates.
 *
 * Returns `success` on COMPLETED, `failed` (with the backend `failureReason`
 * and `failureCode`) on FAILED, and `failed` after too many consecutive errors
 * or the timeout.
 */
export async function pollForCompletion(jobId: string): Promise<PollResult> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let consecutiveErrors = 0;

  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS);
    try {
      const statusData = await getJobStatus(jobId);
      const { status, failure_reason, failure_code } = statusData.data;
      consecutiveErrors = 0;
      if (status === 'COMPLETED') {
        return { status: 'success' };
      }
      if (status === 'FAILED') {
        return {
          status: 'failed',
          failureReason: failure_reason ?? undefined,
          failureCode: failure_code ?? undefined,
        };
      }
    } catch {
      consecutiveErrors += 1;
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        return { status: 'failed' };
      }
    }
  }
  return { status: 'failed' };
}
