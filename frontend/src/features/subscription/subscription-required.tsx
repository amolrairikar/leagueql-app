import { Lock } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { ManageSubscriptionDialog } from '@/features/subscription/manage-subscription-dialog';

/**
 * Inline paywall shown in place of an analytics page when the current league's
 * subscription is expired or absent. Rendered inside the app layout so the
 * sidebar and header stay visible.
 */
export function SubscriptionRequired() {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="bg-muted flex size-12 items-center justify-center rounded-full">
        <Lock className="size-6 text-muted-foreground" />
      </div>
      <h1 className="text-2xl font-bold">Subscription required</h1>
      <p className="text-muted-foreground max-w-md">
        This league&apos;s subscription has expired. Manage your subscription to
        regain access to your league&apos;s analytics.
      </p>
      <Button className="cursor-pointer" onClick={() => setDialogOpen(true)}>
        Manage Subscription
      </Button>
      <ManageSubscriptionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}
