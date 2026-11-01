import { HelpCircle } from 'lucide-react';
import { useState } from 'react';

import type { Platform } from '@/components/api/types';
import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { getYahooAuthorizeUrl } from '@/features/connect_league/api-calls';
import {
  getEspnMembers,
  getSleeperUsers,
  getYahooMembers,
} from '@/features/migrate_league/api-calls';
import { PLATFORM_LABELS } from '@/features/migrate_league/constants';
import {
  type NewPlatformInfo,
  type NewPlatformUser,
} from '@/features/migrate_league/types';
import { useEspnExtensionReady } from '@/hooks/use-espn-extension-ready';
import { ApiError } from '@/lib/api-client';
import {
  ESPN_EXTENSION_URL,
  EspnExtensionError,
  requestEspnCookies,
} from '@/lib/espn-extension';

export function Step2({
  currentPlatform,
  currentLeagueId,
  onNext,
  onBack,
  initialDestination,
  initialLeagueId,
  initialNotice,
}: {
  currentPlatform: Platform;
  currentLeagueId: string;
  onNext: (info: NewPlatformInfo, users: NewPlatformUser[]) => void;
  onBack: () => void;
  // Set when resuming after a Yahoo OAuth round-trip so the wizard returns prefilled.
  initialDestination?: Platform;
  initialLeagueId?: string;
  initialNotice?: string;
}) {
  const availablePlatforms = (['ESPN', 'SLEEPER', 'YAHOO'] as const).filter(
    (p) => p !== currentPlatform,
  );

  const [destinationPlatform, setDestinationPlatform] = useState<Platform>(
    initialDestination ?? availablePlatforms[0],
  );
  const [newPlatformLeagueId, setNewPlatformLeagueId] = useState(
    initialLeagueId ?? '',
  );
  const [season, setSeason] = useState('');
  const [seasonError, setSeasonError] = useState<string | null>(null);
  const [swid, setSwid] = useState('');
  const [s2, setS2] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialNotice ?? null);
  // A Yahoo destination with no linked account: swap Next for a "Connect with Yahoo" action.
  const [needsYahooLink, setNeedsYahooLink] = useState(false);
  const [connecting, setConnecting] = useState(false);

  const extensionReady = useEspnExtensionReady();
  const [autofilling, setAutofilling] = useState(false);
  const [autofillError, setAutofillError] = useState<string | null>(null);

  function handlePlatformChange(value: Platform) {
    setDestinationPlatform(value);
    setNewPlatformLeagueId('');
    setSeason('');
    setSwid('');
    setS2('');
    setError(null);
    setAutofillError(null);
    setNeedsYahooLink(false);
  }

  async function handleConnectYahoo() {
    setError(null);
    setConnecting(true);
    try {
      // Carry the MIGRATE return context so the callback returns to /migrate_league, and the
      // entered Yahoo league id so the wizard resumes on it. No Yahoo token reaches the browser.
      const { data } = await getYahooAuthorizeUrl(
        newPlatformLeagueId.trim(),
        'MIGRATE',
      );
      window.location.href = data.authorize_url;
    } catch {
      setConnecting(false);
      setError('Could not start Yahoo connection. Please try again.');
    }
  }

  async function handleAutofill() {
    setAutofillError(null);
    setAutofilling(true);
    try {
      const { swid: nextSwid, espnS2 } = await requestEspnCookies();
      setSwid(nextSwid);
      setS2(espnS2);
    } catch (err) {
      setAutofillError(
        err instanceof EspnExtensionError && err.reason === 'not_logged_in'
          ? 'Log into fantasy.espn.com, then try again.'
          : 'Could not reach the ESPN extension. Please try again.',
      );
    } finally {
      setAutofilling(false);
    }
  }

  async function handleNext() {
    if (!newPlatformLeagueId.trim()) {
      setError('League ID is required');
      return;
    }
    if (destinationPlatform === 'ESPN') {
      if (!season.trim()) {
        setError('Season is required for ESPN');
        return;
      }
      if (!/^\d{4}$/.test(season.trim())) {
        setError('Latest season must be a 4-digit number (e.g. 2026)');
        return;
      }
      if (!swid.trim()) {
        setError('SWID is required for ESPN');
        return;
      }
      if (!s2.trim()) {
        setError('ESPN S2 is required for ESPN');
        return;
      }
    }

    setLoading(true);
    setError(null);
    setNeedsYahooLink(false);
    try {
      let users: NewPlatformUser[];
      if (destinationPlatform === 'SLEEPER') {
        users = await getSleeperUsers(newPlatformLeagueId.trim());
      } else if (destinationPlatform === 'YAHOO') {
        const result = await getYahooMembers(
          currentLeagueId,
          currentPlatform,
          newPlatformLeagueId.trim(),
        );
        users = result.data;
      } else {
        const result = await getEspnMembers(
          currentLeagueId,
          currentPlatform,
          newPlatformLeagueId.trim(),
          season.trim(),
          swid.trim(),
          s2.trim(),
        );
        users = result.data;
      }

      if (users.length === 0) {
        setError(
          'No users found for that league. Check the league ID and try again.',
        );
        return;
      }

      onNext(
        {
          newPlatform: destinationPlatform,
          newPlatformLeagueId: newPlatformLeagueId.trim(),
          season: destinationPlatform === 'ESPN' ? season.trim() : undefined,
          s2: destinationPlatform === 'ESPN' ? s2.trim() : undefined,
          swid: destinationPlatform === 'ESPN' ? swid.trim() : undefined,
        },
        users,
      );
    } catch (err) {
      if (
        destinationPlatform === 'YAHOO' &&
        err instanceof ApiError &&
        err.status === 403
      ) {
        // No linked Yahoo account — prompt the OAuth link instead of a generic error.
        setNeedsYahooLink(true);
        return;
      }
      setError(
        'Failed to fetch users for that league. Check the ID and credentials.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="destination-platform">Migrating to</Label>
        <Select
          value={destinationPlatform}
          onValueChange={(v) => handlePlatformChange(v as Platform)}
        >
          <SelectTrigger id="destination-platform" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {availablePlatforms.map((p) => (
              <SelectItem key={p} value={p}>
                {PLATFORM_LABELS[p]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-[12px] text-muted-foreground">
          Enter your new {PLATFORM_LABELS[destinationPlatform]} league details.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="new-league-id">
          {PLATFORM_LABELS[destinationPlatform]} League ID
        </Label>
        <Input
          id="new-league-id"
          name="migrate-new-league-id"
          type="text"
          autoComplete="on"
          placeholder={`Enter your ${PLATFORM_LABELS[destinationPlatform]} league ID`}
          value={newPlatformLeagueId}
          onChange={(e) => setNewPlatformLeagueId(e.target.value)}
        />
      </div>

      {destinationPlatform === 'ESPN' && (
        <>
          <div className="flex flex-col gap-2">
            <Label htmlFor="espn-season">Latest Season</Label>
            <Input
              id="espn-season"
              name="migrate-espn-season"
              type="text"
              inputMode="numeric"
              autoComplete="on"
              placeholder="e.g. 2025"
              value={season}
              onChange={(e) => {
                const value = e.target.value;
                setSeason(value);
                // Validate live so typing more (or fewer) than 4 digits surfaces
                // the inline error instead of being silently blocked.
                setSeasonError(
                  value && !/^\d{4}$/.test(value)
                    ? 'Latest season must be a 4-digit number (e.g. 2026)'
                    : null,
                );
              }}
            />
            {seasonError && (
              <p className="text-sm text-destructive">{seasonError}</p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="espn-swid">SWID</Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-64">
                    Found in ESPN cookies under DevTools → Application → Cookies
                    → fantasy.espn.com (include the curly braces).
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Input
              id="espn-swid"
              name="migrate-espn-swid"
              type="text"
              autoComplete="on"
              placeholder="Enter your SWID"
              value={swid}
              onChange={(e) => setSwid(e.target.value)}
            />
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
                    Found in ESPN cookies under DevTools → Application → Cookies
                    → fantasy.espn.com (espn_s2 value).
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Input
              id="espn-s2"
              name="migrate-espn-s2"
              type="text"
              autoComplete="on"
              placeholder="Enter your ESPN S2"
              value={s2}
              onChange={(e) => setS2(e.target.value)}
            />
          </div>
          {extensionReady && (
            <div className="flex flex-col gap-2">
              <Button
                variant="outline"
                className="w-full cursor-pointer"
                disabled={autofilling}
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
          )}
          {!extensionReady && (
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
        </>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      {needsYahooLink && (
        <p className="text-[13px] text-muted-foreground">
          Connect your Yahoo account to fetch this league&apos;s managers.
        </p>
      )}

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1 cursor-pointer"
          onClick={onBack}
          disabled={loading || connecting}
        >
          Back
        </Button>
        {needsYahooLink ? (
          <Button
            className="flex-1 cursor-pointer"
            onClick={() => void handleConnectYahoo()}
            disabled={connecting}
          >
            {connecting ? (
              <span className="flex items-center gap-2">
                <Spinner className="text-primary-foreground" />
                Connecting
              </span>
            ) : (
              'Connect with Yahoo'
            )}
          </Button>
        ) : (
          <Button
            className="flex-1 cursor-pointer"
            onClick={() => void handleNext()}
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Spinner className="text-primary-foreground" />
                Fetching users…
              </span>
            ) : (
              'Next'
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
