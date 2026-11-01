import { getJobStatus } from '@/features/connect_league/api-calls';

export const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const POLL_INITIAL_DELAY_MS = 5000;
export const POLL_INTERVAL_MS = 1000;
// Migration runs the same onboarder + processor pipeline, which can take a while
// end-to-end; poll long enough to observe COMPLETED rather than time out early.
export const POLL_TIMEOUT_MS = 150000;
export const MAX_CONSECUTIVE_ERRORS = 3;

export interface PollResult {
  status: 'success' | 'failed';
  failureReason?: string;
}

export async function pollForCompletion(jobId: string): Promise<PollResult> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let consecutiveErrors = 0;

  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS);
    try {
      const statusData = await getJobStatus(jobId);
      const { status, failure_reason } = statusData.data;
      consecutiveErrors = 0;
      if (status === 'COMPLETED') return { status: 'success' };
      if (status === 'FAILED')
        return { status: 'failed', failureReason: failure_reason ?? undefined };
    } catch {
      consecutiveErrors += 1;
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS)
        return { status: 'failed' };
    }
  }
  return { status: 'failed' };
}
