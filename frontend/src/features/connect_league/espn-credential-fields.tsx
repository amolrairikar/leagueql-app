import { HelpCircle } from 'lucide-react';
import { useState } from 'react';

import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useEspnExtensionReady } from '@/hooks/use-espn-extension-ready';
import {
  ESPN_EXTENSION_URL,
  EspnExtensionError,
  requestEspnCookies,
} from '@/lib/espn-extension';

interface EspnCredentialFieldsProps {
  swid: string;
  espnS2: string;
  onSwidChange: (value: string) => void;
  onEspnS2Change: (value: string) => void;
  swidError?: string;
  espnS2Error?: string;
  /** Called with the cookies retrieved by the extension so the parent stores them. */
  onAutofill: (swid: string, espnS2: string) => void;
  disabled?: boolean;
  /**
   * Show the visible manual cookie-retrieval instructions below the inputs.
   * Defaults to true; the landing page hides it since the per-field tooltips
   * already carry the same guidance.
   */
  showManualInstructions?: boolean;
}

/**
 * The ESPN private-league credential block, shared by the landing-page inline
 * connect bar and the `/connect_league` refresh form. Renders the SWID/espn_s2
 * inputs, the extension autofill button (or the Chrome Web Store install promo
 * when the extension is absent), and the manual cookie-retrieval instructions.
 *
 * Controlled: the parent owns the SWID/espn_s2 values and receives autofilled
 * cookies via {@link EspnCredentialFieldsProps.onAutofill}. The cookies are only
 * held here transiently; the parent transmits them once and clears them
 * (`clearEspnCookies`) on success (backend/espn-credential-storage).
 */
export function EspnCredentialFields({
  swid,
  espnS2,
  onSwidChange,
  onEspnS2Change,
  swidError,
  espnS2Error,
  onAutofill,
  disabled,
  showManualInstructions = true,
}: EspnCredentialFieldsProps) {
  const extensionReady = useEspnExtensionReady();
  const [autofilling, setAutofilling] = useState(false);
  const [autofillError, setAutofillError] = useState<string | null>(null);

  const handleAutofill = async () => {
    setAutofillError(null);
    setAutofilling(true);
    try {
      const cookies = await requestEspnCookies();
      onAutofill(cookies.swid, cookies.espnS2);
    } catch (err) {
      setAutofillError(
        err instanceof EspnExtensionError && err.reason === 'not_logged_in'
          ? 'Log into fantasy.espn.com, then try again.'
          : 'Could not reach the ESPN extension. Please try again.',
      );
    } finally {
      setAutofilling(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="swid">SWID</Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-64">
                Found in your ESPN cookies. In your browser, open DevTools →
                Application → Cookies → fantasy.espn.com, then copy the value of
                the SWID cookie (including the curly braces).
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <Input
          id="swid"
          type="text"
          placeholder="Enter your SWID"
          value={swid}
          disabled={disabled}
          onChange={(e) => onSwidChange(e.target.value)}
        />
        {swidError && <p className="text-sm text-destructive">{swidError}</p>}
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1.5">
          <Label htmlFor="espn-s2">ESPN S2</Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-64">
                Found in your ESPN cookies. In your browser, open DevTools →
                Application → Cookies → fantasy.espn.com, then copy the value of
                the espn_s2 cookie.
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <Input
          id="espn-s2"
          type="text"
          placeholder="Enter your ESPN S2 token"
          value={espnS2}
          disabled={disabled}
          onChange={(e) => onEspnS2Change(e.target.value)}
        />
        {espnS2Error && (
          <p className="text-sm text-destructive">{espnS2Error}</p>
        )}
      </div>
      {extensionReady ? (
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            variant="outline"
            className="w-full cursor-pointer"
            disabled={autofilling || disabled}
            onClick={() => void handleAutofill()}
          >
            {autofilling ? (
              <span className="flex items-center gap-2">
                <Spinner />
                Autofilling
              </span>
            ) : (
              'Autofill cookies from ESPN'
            )}
          </Button>
          {autofillError && (
            <p className="text-sm text-destructive">{autofillError}</p>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Tired of copying cookies?{' '}
          <a
            href={ESPN_EXTENSION_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-4"
          >
            Get the LeagueQL ESPN Cookie Helper extension
          </a>{' '}
          to autofill them automatically.
        </p>
      )}
      {/* Manual retrieval steps, shown below the boxes for users without the
          extension. The per-field tooltips carry the same guidance, so callers
          (the landing page) can suppress this to avoid the duplication. */}
      {showManualInstructions && (
        <p className="text-sm text-muted-foreground">
          To find these manually, open your browser DevTools → Application →
          Cookies → fantasy.espn.com, then copy the <code>SWID</code> (including
          the curly braces) and <code>espn_s2</code> cookie values.
        </p>
      )}
    </div>
  );
}
