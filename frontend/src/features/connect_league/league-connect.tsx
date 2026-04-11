import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import {
  type FieldErrors,
  Controller,
  useForm,
  useWatch,
} from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import {
  type OnboardRequest,
  getLeague,
  getRefreshStatus,
  onboardLeague,
} from '@/features/connect_league/api-calls';
import {
  type EspnFormValues,
  type LeagueConnectFormValues,
  leagueConnectSchema,
} from '@/features/connect_league/league-connect-schema';
import { ApiError, clearApiError } from '@/lib/api-client';

function getCookieValue(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
}

export default function LeagueConnect() {
  const navigate = useNavigate();
  const [pollStatus, setPollStatus] = useState<'idle' | 'success' | 'failed'>(
    'idle',
  );

  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LeagueConnectFormValues>({
    resolver: zodResolver(leagueConnectSchema),
    defaultValues: {
      platform: 'espn',
      swid: getCookieValue('SWID'),
      espnS2: getCookieValue('espn_s2'),
    },
  });

  const platform = useWatch({ control, name: 'platform' });

  const onSubmit = async (data: LeagueConnectFormValues) => {
    setPollStatus('idle');
    const apiPlatform = data.platform.toUpperCase() as 'ESPN' | 'SLEEPER';

    let requestType: 'ONBOARD' | 'REFRESH';
    let existingSeasons: string[] = [];

    try {
      const leagueData = await getLeague(data.leagueId, apiPlatform);
      requestType = 'REFRESH';
      existingSeasons = leagueData.data.seasons;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        clearApiError();
        requestType = 'ONBOARD';
      } else {
        return;
      }
    }

    const mostRecentSeason = [...existingSeasons].sort().at(-1);
    const body: OnboardRequest = {
      leagueId: data.leagueId,
      platform: apiPlatform,
      season:
        requestType === 'REFRESH'
          ? mostRecentSeason
          : data.platform === 'espn'
            ? data.latestSeason
            : undefined,
      s2:
        data.platform === 'espn' && requestType === 'ONBOARD'
          ? data.espnS2
          : undefined,
      swid:
        data.platform === 'espn' && requestType === 'ONBOARD'
          ? data.swid
          : undefined,
    };

    await onboardLeague(requestType, body);

    await new Promise<void>((r) => setTimeout(r, 5000));

    await new Promise<void>((resolve) => {
      let done = false;

      const cleanup = (status: 'success' | 'failed') => {
        if (done) return;
        done = true;
        clearInterval(intervalId);
        clearTimeout(timeoutId);
        setPollStatus(status);
        if (status === 'success') {
          void navigate('/home');
        } else {
          setTimeout(() => setPollStatus('idle'), 10000);
        }
        resolve();
      };

      const intervalId = setInterval(() => {
        void (async () => {
          try {
            const statusData = await getRefreshStatus(
              data.leagueId,
              apiPlatform,
              requestType,
            );
            const { refresh_status } = statusData.data;
            if (refresh_status === 'COMPLETED') {
              cleanup('success');
            } else if (refresh_status === 'FAILED') {
              cleanup('failed');
            }
          } catch {
            cleanup('failed');
          }
        })();
      }, 1000);

      const timeoutId = setTimeout(() => cleanup('failed'), 20000);
    });
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
              Connect League
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
                    <Select onValueChange={field.onChange} value={field.value}>
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
                      placeholder="Enter the latest season"
                      {...register('latestSeason')}
                    />
                    {(errors as FieldErrors<EspnFormValues>).latestSeason && (
                      <p className="text-sm text-destructive">
                        {
                          (errors as FieldErrors<EspnFormValues>).latestSeason
                            ?.message
                        }
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="swid">SWID</Label>
                    <Input
                      id="swid"
                      type="text"
                      placeholder="Enter your SWID"
                      {...register('swid')}
                    />
                    {(errors as FieldErrors<EspnFormValues>).swid && (
                      <p className="text-sm text-destructive">
                        {(errors as FieldErrors<EspnFormValues>).swid?.message}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="espn-s2">ESPN S2</Label>
                    <Input
                      id="espn-s2"
                      type="text"
                      placeholder="Enter your ESPN S2 token"
                      {...register('espnS2')}
                    />
                    {(errors as FieldErrors<EspnFormValues>).espnS2 && (
                      <p className="text-sm text-destructive">
                        {
                          (errors as FieldErrors<EspnFormValues>).espnS2
                            ?.message
                        }
                      </p>
                    )}
                  </div>
                </>
              )}
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? (
                  <Spinner className="text-primary-foreground" />
                ) : (
                  'Connect'
                )}
              </Button>
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
                <AlertTitle>Failed</AlertTitle>
                <AlertDescription>
                  League onboarding failed or timed out. Please try again.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
