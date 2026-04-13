import { useState } from 'react';
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
import { getLeague } from '@/features/connect_league/api-calls';
import { ApiError } from '@/lib/api-client';

type View = 'select' | 'view-league';

export default function LeagueSelection() {
  const navigate = useNavigate();
  const [view, setView] = useState<View>('select');
  const [leagueId, setLeagueId] = useState('');
  const [platform, setPlatform] = useState<'ESPN' | 'SLEEPER'>('ESPN');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleViewLeague(e: React.FormEvent) {
    e.preventDefault();
    if (!leagueId.trim()) return;

    setLoading(true);
    setError(null);

    try {
      await getLeague(leagueId.trim(), platform);
      document.cookie = `leagueId=${encodeURIComponent(leagueId.trim())}; path=/`;
      document.cookie = `leaguePlatform=${encodeURIComponent(platform)}; path=/`;
      void navigate('/home');
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'Failed to find league. Please check your league ID and platform.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

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
              {view === 'select' ? 'Your League' : 'View League'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {view === 'select' && (
              <div className="flex flex-col gap-3">
                <Button
                  className="w-full cursor-pointer"
                  onClick={() => setView('view-league')}
                >
                  View League
                </Button>
                <Button
                  variant="outline"
                  className="w-full cursor-pointer"
                  onClick={() => void navigate('/connect_league')}
                >
                  Onboard / Refresh League
                </Button>
              </div>
            )}

            {view === 'view-league' && (
              <form
                className="flex flex-col gap-4"
                onSubmit={(e) => void handleViewLeague(e)}
              >
                <div className="flex flex-col gap-2">
                  <Label htmlFor="platform">Platform</Label>
                  <Select
                    value={platform.toLowerCase()}
                    onValueChange={(v) =>
                      setPlatform(v.toUpperCase() as 'ESPN' | 'SLEEPER')
                    }
                  >
                    <SelectTrigger id="platform" className="w-full">
                      <SelectValue placeholder="Select a platform" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="espn">ESPN</SelectItem>
                      <SelectItem value="sleeper">Sleeper</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex flex-col gap-2">
                  <Label htmlFor="league-id">League ID</Label>
                  <Input
                    id="league-id"
                    type="text"
                    placeholder="Enter your league ID"
                    value={leagueId}
                    onChange={(e) => setLeagueId(e.target.value)}
                  />
                </div>

                {error && (
                  <Alert variant="destructive">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1 cursor-pointer"
                    onClick={() => {
                      setView('select');
                      setError(null);
                    }}
                  >
                    Back
                  </Button>
                  <Button
                    type="submit"
                    disabled={loading || !leagueId.trim()}
                    className="flex-1 cursor-pointer"
                  >
                    {loading ? (
                      <Spinner className="text-primary-foreground" />
                    ) : (
                      'View'
                    )}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
