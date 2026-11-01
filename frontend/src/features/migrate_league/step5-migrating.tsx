import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export function Step5({
  pollOutcome,
  operationId,
  failureReason,
}: {
  pollOutcome: 'polling' | 'success' | 'failed';
  operationId: string | null;
  failureReason: string | null;
}) {
  if (pollOutcome === 'polling') {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        <Spinner className="size-8 text-primary" />
        <p className="text-[13px] text-muted-foreground text-center">
          Migration in progress. This may take up to a minute…
        </p>
      </div>
    );
  }

  if (pollOutcome === 'success') {
    return (
      <Alert className="border-primary bg-primary/10">
        <AlertTitle className="text-primary">Migration complete</AlertTitle>
        <AlertDescription>
          Your league has been successfully migrated. Redirecting to your
          dashboard…
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert variant="destructive">
      <AlertTitle>Migration failed</AlertTitle>
      <AlertDescription>
        {failureReason
          ? `${failureReason} `
          : 'The migration did not complete successfully. Please try again. '}
        If the error persists, contact{' '}
        <a
          href="mailto:support@leagueql.com"
          className="font-medium underline underline-offset-4"
        >
          support
        </a>
        {operationId ? ` and provide this ID: ${operationId}` : ''}.
      </AlertDescription>
    </Alert>
  );
}
