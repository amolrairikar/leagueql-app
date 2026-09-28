import type {
  Integration,
  IntegrationSubmission,
  ListIntegrationsResponse,
  SubmitIntegrationResponse,
} from './types';

import { apiClient } from '@/lib/api-client';

/** Approved community integrations, newest first (frontend/integrations). */
export async function listIntegrations(): Promise<Integration[]> {
  const response =
    await apiClient.get<ListIntegrationsResponse>('/integrations');
  return response.data.items;
}

/** Submit an integration for maintainer review; resolves to the issue number. */
export async function submitIntegration(
  submission: IntegrationSubmission,
): Promise<number> {
  const response = await apiClient.post<SubmitIntegrationResponse>(
    '/integrations',
    submission,
  );
  return response.data.issue_number;
}
