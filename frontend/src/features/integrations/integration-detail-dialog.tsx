import { Check, Copy, ExternalLink } from 'lucide-react';

import { CATEGORY_LABELS } from './constants';
import { CategoryPreview, ViewChip } from './integration-card';
import type { Integration } from './types';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useCopyToClipboard } from '@/lib/use-copy-to-clipboard';

function SectionHeading({ children }: { children: string }) {
  return (
    <h3 className="mb-1.5 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
      {children}
    </h3>
  );
}

/**
 * Setup details for one integration (frontend/integrations): numbered setup
 * steps, the export files it reads, a link out to the project, and — only for
 * integrations that ship a prompt — the prompt with a copy button.
 */
export function IntegrationDetailDialog({
  integration,
  onOpenChange,
}: {
  integration: Integration | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { copied, copy, resetCopied } = useCopyToClipboard();

  return (
    <Dialog
      open={integration !== null}
      onOpenChange={(open) => {
        if (!open) resetCopied();
        onOpenChange(open);
      }}
    >
      {integration && (
        <DialogContent className="max-h-[calc(100vh-3rem)] overflow-y-auto sm:max-w-140">
          <DialogHeader>
            <div className="flex flex-wrap gap-1.5">
              <Badge variant="secondary">
                {CATEGORY_LABELS[integration.category]}
              </Badge>
            </div>
            <DialogTitle>{integration.name}</DialogTitle>
            <DialogDescription>
              by @{integration.author_handle}
            </DialogDescription>
          </DialogHeader>

          <CategoryPreview
            category={integration.category}
            className="h-40 rounded-lg border"
          />
          <p className="text-sm">{integration.description}</p>

          <div>
            <SectionHeading>Setup</SectionHeading>
            <ol className="flex list-decimal flex-col gap-1 pl-5 text-sm">
              {integration.setup_steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </div>

          <div>
            <SectionHeading>Reads these files</SectionHeading>
            <div className="flex flex-wrap gap-1.5">
              {integration.views.map((view) => (
                <ViewChip key={view}>{`<season>_${view}.json`}</ViewChip>
              ))}
            </div>
          </div>

          {integration.prompt && (
            <div>
              <SectionHeading>Prompt</SectionHeading>
              <pre className="rounded-lg border bg-muted px-3 py-2.5 font-mono text-xs leading-relaxed whitespace-pre-wrap">
                {integration.prompt}
              </pre>
            </div>
          )}

          <DialogFooter>
            {integration.prompt && (
              <Button
                variant="outline"
                onClick={() => copy(integration.prompt ?? '')}
              >
                {copied ? <Check /> : <Copy />}
                {copied ? 'Copied' : 'Copy prompt'}
              </Button>
            )}
            <Button asChild>
              <a
                href={integration.link}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open project
                <ExternalLink />
              </a>
            </Button>
          </DialogFooter>
        </DialogContent>
      )}
    </Dialog>
  );
}
