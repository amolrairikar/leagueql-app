import { RiErrorWarningLine } from '@remixicon/react';

import { Alert, AlertDescription } from '@/components/ui/alert';

/**
 * Presentational inline error alert. Features render this wherever the error
 * belongs — below a form, next to a button — passing the message they caught
 * from a rejected API call. There is no global error store; each feature owns
 * its own error state.
 */
export function ErrorAlert({
  message,
  className,
}: {
  message: string;
  className?: string;
}) {
  return (
    <Alert variant="destructive" className={className}>
      <RiErrorWarningLine />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
