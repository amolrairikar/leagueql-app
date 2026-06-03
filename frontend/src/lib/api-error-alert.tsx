import { RiErrorWarningLine } from '@remixicon/react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useApiError } from '@/lib/api-client';

// Render <ApiErrorAlert /> anywhere in the tree to surface API errors.
// It is invisible when there is no active error.
export function ApiErrorAlert() {
  const error = useApiError();
  if (!error) return null;
  // 4xx client errors are expected, actionable states (e.g. a 409 "checkout
  // already in progress"), so show them in the neutral variant; reserve the
  // destructive (red) variant for 5xx / unknown failures.
  const isClientError = error.status >= 400 && error.status < 500;
  return (
    <Alert
      variant={isClientError ? 'default' : 'destructive'}
      className="m-4 w-auto"
    >
      <RiErrorWarningLine />
      <AlertTitle>
        {error.status ? `Error ${error.status}` : 'Request failed'}
      </AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  );
}
