import { zodResolver } from '@hookform/resolvers/zod';
import { Check, Copy, HelpCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import {
  type FieldErrors,
  Controller,
  useForm,
  useWatch,
} from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { getLeague } from '@/components/api/leagues';
import {
  type OnboardRequest,
  getRefreshStatus,
  onboardLeague,
} from '@/features/connect_league/api-calls';
import {
  type EspnFormValues,
  type LeagueConnectFormValues,
  leagueConnectSchema,
} from '@/features/connect_league/league-connect-schema';
import { clearEspnCookies, setLeagueCookies } from '@/lib/cookie-handler';
import {
  EspnExtensionError,
  isEspnExtensionAvailable,
  onEspnExtensionReady,
  requestEspnCookies,
} from '@/lib/espn-extension';
import { ApiError, clearApiError } from '@/lib/api-client';

const API_PLATFORM = { espn: 'ESPN', sleeper: 'SLEEPER' } as const;

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

const MAX_ONBOARD_ATTEMPTS = 3;
const MAX_CONSECUTIVE_ERRORS = 3;
const ONBOARD_RETRY_DELAY_MS = 2000;
const POLL_INITIAL_DELAY_MS = 5000;
const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 45000;

export async function pollForCompletion(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  requestType: 'ONBOARD' | 'REFRESH',
): Promise<'success' | 'failed'> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let consecutiveErrors = 0;
  let pollCount = 0;

  while (Date.now() < deadline) {
    pollCount += 1;
    await sleep(POLL_INTERVAL_MS);
    try {
      const statusData = await getRefreshStatus(
        leagueId,
        platform,
        requestType,
      );
      const { refresh_status } = statusData.data;
      consecutiveErrors = 0;
      if (refresh_status === 'COMPLETED') {
        return 'success';
      }
      if (refresh_status === 'FAILED') {
        return 'failed';
      }
    } catch (err) {
      consecutiveErrors += 1;
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        return 'failed';
      }
    }
  }
  return 'failed';
}

function CopyOperationId({ operationId }: { operationId: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard.writeText(operationId).then(() => {
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    });
  };

  return (
    <span className="mt-1 flex items-center gap-1.5">
      <span className="font-mono text-xs">{operationId}</span>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-5 w-5 shrink-0"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="h-3 w-3" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {copied ? 'Copied!' : 'Copy operation ID'}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </span>
  );
}

export default function LeagueConnect() {
  const navigate = useNavigate();
  const [pollStatus, setPollStatus] = useState<'idle' | 'success' | 'failed'>(
    'idle',
  );
  const [lastRequestType, setLastRequestType] = useState<
    'ONBOARD' | 'REFRESH' | null
  >(null);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [loadingMessage, setLoadingMessage] = useState('');
  const loadingStartRef = useRef<number | null>(null);
  const loadingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );

  const urlParams = new URLSearchParams(window.location.search);
  const urlLeagueId = urlParams.get('leagueId') ?? '';
  const urlPlatform =
    urlParams.get('platform') === 'sleeper' ? 'sleeper' : 'espn';
  // When the user arrives with a pre-filled league ID, they've already entered
  // the platform and league ID upstream, so lock those fields against edits.
  const fieldsLocked = urlLeagueId !== '';

  const {
    control,
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LeagueConnectFormValues>({
    resolver: zodResolver(leagueConnectSchema),
    defaultValues: {
      platform: urlPlatform,
      leagueId: urlLeagueId,
    },
  });

  const platform = useWatch({ control, name: 'platform' });
  const espnErrors = errors as FieldErrors<EspnFormValues>;

  const [extensionReady, setExtensionReady] = useState(
    isEspnExtensionAvailable,
  );
  const [autofilling, setAutofilling] = useState(false);
  const [autofillError, setAutofillError] = useState<string | null>(null);

  useEffect(() => {
    if (extensionReady) return;
    return onEspnExtensionReady(() => {
      setExtensionReady(true);
    });
  }, [extensionReady]);

  const handleAutofill = async () => {
    setAutofillError(null);
    setAutofilling(true);
    try {
      const { swid, espnS2 } = await requestEspnCookies();
      setValue('swid', swid, { shouldValidate: true });
      setValue('espnS2', espnS2, { shouldValidate: true });
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

  useEffect(() => {
    if (isSubmitting) {
      loadingStartRef.current = Date.now();
      setLoadingMessage("Fetching your league's data");
      loadingIntervalRef.current = setInterval(() => {
        const elapsed = (Date.now() - loadingStartRef.current!) / 1000;
        if (elapsed < 10) {
          setLoadingMessage("Fetching your league's data");
        } else if (elapsed < 25) {
          setLoadingMessage('Calculating');
        } else {
          setLoadingMessage('Creating your league dashboard');
        }
      }, 500);
    } else {
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
        loadingIntervalRef.current = null;
      }
      loadingStartRef.current = null;
      setLoadingMessage('');
    }
    return () => {
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
      }
    };
  }, [isSubmitting]);

  const onSubmit = async (data: LeagueConnectFormValues) => {
    setPollStatus('idle');
    setLastRequestType(null);
    setOperationId(null);
    const apiPlatform = API_PLATFORM[data.platform];

    let requestType: 'ONBOARD' | 'REFRESH';

    try {
      await getLeague(data.leagueId, apiPlatform);
      requestType = 'REFRESH';
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        clearApiError();
        requestType = 'ONBOARD';
      } else {
        return;
      }
    }

    // ESPN S2/SWID are read from cookies, transmitted once over HTTPS, then cleared by
    // clearEspnCookies() on success. Never persist or log these credentials.
    const body: OnboardRequest = {
      leagueId: data.leagueId,
      platform: apiPlatform,
      season: data.platform === 'espn' ? data.latestSeason : undefined,
      s2: data.platform === 'espn' ? data.espnS2 : undefined,
      swid: data.platform === 'espn' ? data.swid : undefined,
    };

    let onboardSucceeded = false;
    let capturedOperationId: string | null = null;
    for (let attempt = 1; attempt <= MAX_ONBOARD_ATTEMPTS; attempt++) {
      try {
        const onboardResult = await onboardLeague(requestType, body);
        capturedOperationId = onboardResult.data.correlation_id;
        onboardSucceeded = true;
        clearEspnCookies();
        break;
      } catch (err) {
        const status = err instanceof ApiError ? err.status : 0;
        const isRetryable = status === 0 || status >= 500;
        if (!isRetryable || attempt === MAX_ONBOARD_ATTEMPTS) break;
        await sleep(ONBOARD_RETRY_DELAY_MS);
      }
    }
    if (!onboardSucceeded) {
      return;
    }

    setLastRequestType(requestType);
    await sleep(POLL_INITIAL_DELAY_MS);
    const result = await pollForCompletion(
      data.leagueId,
      apiPlatform,
      requestType,
    );
    if (result === 'failed') setOperationId(capturedOperationId);
    setPollStatus(result);
    if (result === 'success') {
      const leagueData = await getLeague(data.leagueId, apiPlatform);
      setLeagueCookies(data.leagueId, apiPlatform, leagueData.data.seasons);
      void navigate('/home');
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans overflow-x-hidden">
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `
            linear-gradient(var(--border) 1px, transparent 1px),
            linear-gradient(90deg, var(--border) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          opacity: 0.2,
        }}
      />

      <div className="relative z-10 flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl text-center font-bold">
              Onboard/Refresh League
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-4"
              onSubmit={(e) => void handleSubmit(onSubmit)(e)}
            >
              <div className="flex flex-col gap-2">
                <Label htmlFor="platform">Platform</Label>
                <Controller
                  name="platform"
                  control={control}
                  render={({ field }) => (
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                      disabled={fieldsLocked}
                    >
                      <SelectTrigger id="platform" className="w-full">
                        <SelectValue placeholder="Select a platform" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="espn">ESPN</SelectItem>
                        <SelectItem value="sleeper">Sleeper</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.platform && (
                  <p className="text-sm text-destructive">
                    {errors.platform.message}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="league-id">League ID</Label>
                <Input
                  id="league-id"
                  type="text"
                  placeholder="Enter your league ID"
                  readOnly={fieldsLocked}
                  className={
                    fieldsLocked ? 'cursor-not-allowed opacity-60' : undefined
                  }
                  {...register('leagueId')}
                />
                {errors.leagueId && (
                  <p className="text-sm text-destructive">
                    {errors.leagueId.message}
                  </p>
                )}
              </div>
              {platform === 'espn' && (
                <>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="latest-season">Latest Season</Label>
                    <Input
                      id="latest-season"
                      type="text"
                      placeholder="Enter the latest season your league was active"
                      {...register('latestSeason')}
                    />
                    {espnErrors.latestSeason && (
                      <p className="text-sm text-destructive">
                        {espnErrors.latestSeason?.message}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-1.5">
                      <Label htmlFor="swid">SWID</Label>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent side="right" className="max-w-64">
                            Found in your ESPN cookies. In your browser, open
                            DevTools → Application → Cookies → fantasy.espn.com,
                            then copy the value of the SWID cookie (including
                            the curly braces).
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                    <Input
                      id="swid"
                      type="text"
                      placeholder="Enter your SWID"
                      {...register('swid')}
                    />
                    {espnErrors.swid && (
                      <p className="text-sm text-destructive">
                        {espnErrors.swid?.message}
                      </p>
                    )}
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
                            Found in your ESPN cookies. In your browser, open
                            DevTools → Application → Cookies → fantasy.espn.com,
                            then copy the value of the espn_s2 cookie.
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                    <Input
                      id="espn-s2"
                      type="text"
                      placeholder="Enter your ESPN S2 token"
                      {...register('espnS2')}
                    />
                    {espnErrors.espnS2 && (
                      <p className="text-sm text-destructive">
                        {espnErrors.espnS2?.message}
                      </p>
                    )}
                  </div>
                  {extensionReady && (
                    <div className="flex flex-col gap-2">
                      <Button
                        type="button"
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
                        <p className="text-sm text-destructive">
                          {autofillError}
                        </p>
                      )}
                    </div>
                  )}
                </>
              )}
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1 cursor-pointer"
                  disabled={isSubmitting}
                  onClick={() => void navigate('/')}
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? (
                    <span className="flex items-center gap-2">
                      <Spinner className="text-primary-foreground" />
                      {loadingMessage}
                    </span>
                  ) : (
                    'Connect'
                  )}
                </Button>
              </div>
            </form>
            {pollStatus === 'success' && (
              <Alert className="mt-4 border-primary bg-primary/10 text-primary">
                <AlertTitle>Success</AlertTitle>
                <AlertDescription>
                  League onboarding completed successfully.
                </AlertDescription>
              </Alert>
            )}
            {pollStatus === 'failed' && (
              <Alert variant="destructive" className="mt-4">
                <AlertTitle>
                  {lastRequestType === 'REFRESH'
                    ? 'Refresh Failed'
                    : 'Onboarding Failed'}
                </AlertTitle>
                <AlertDescription>
                  {lastRequestType === 'REFRESH'
                    ? 'League refresh failed. Please try again or contact support if the error persists.'
                    : 'League onboarding failed. Please try again or contact support if the error persists.'}
                  {operationId ? (
                    <>
                      {' '}
                      Provide the below operation ID when contacting support:{' '}
                      <CopyOperationId operationId={operationId} />
                    </>
                  ) : (
                    ''
                  )}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
