import { RiErrorWarningLine } from '@remixicon/react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useApiError } from '@/lib/api-client';

// Render <ApiErrorAlert /> anywhere in the tree to surface API errors.
// It is invisible when there is no active error.
export function ApiErrorAlert() {
  const error = useApiError();
  if (!error) return null;
  return (
    <Alert variant="destructive">
      <RiErrorWarningLine />
      <AlertTitle>
        {error.status ? `Error ${error.status}` : 'Request failed'}
      </AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  );
}
