import { zodResolver } from '@hookform/resolvers/zod';
import {
  type FieldErrors,
  Controller,
  useForm,
  useWatch,
} from 'react-hook-form';

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
  type EspnFormValues,
  type LeagueConnectFormValues,
  leagueConnectSchema,
} from '@/features/connect_league/league-connect-schema';

export default function LeagueConnect() {
  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LeagueConnectFormValues>({
    resolver: zodResolver(leagueConnectSchema),
  });

  const platform = useWatch({ control, name: 'platform' });

  const onSubmit = async (data: LeagueConnectFormValues) => {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    console.log('Form submitted:', data);
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
              )}
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <Spinner className="text-primary-foreground" />
                ) : (
                  'Connect'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
