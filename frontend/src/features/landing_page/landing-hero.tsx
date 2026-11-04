import { ArrowRight, ChevronDown, HelpCircle } from 'lucide-react';

import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
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
import { EspnCredentialFields } from '@/features/connect_league/espn-credential-fields';
import { MyLeaguesPanel } from '@/features/landing_page/my-leagues';
import { type LandingState } from '@/features/landing_page/use-landing-page';
import { isPlatform } from '@/lib/cookie-handler';

export function LandingHero({ s }: { s: LandingState }) {
  const {
    isSignedIn,
    showConnectForm,
    showMyLeagues,
    myLeagues,
    myLeaguesCount,
    platform,
    setPlatform,
    espnSwid,
    setEspnSwid,
    espnS2,
    setEspnS2,
    espnAutoRefresh,
    setEspnAutoRefresh,
    needsEspnCredentials,
    setNeedsEspnCredentials,
    leagueId,
    setLeagueId,
    loading,
    loadingMessage,
    progress,
    error,
    setError,
    leagueCount,
    handleConnectLeague,
    loadMyLeagues,
    handleToggleMyLeagues,
    handleViewDemo,
    handleConnectSubmit,
  } = s;

  return (
    <section className="relative z-10 flex flex-col items-center text-center px-6 pt-24 pb-8">
      {leagueCount !== null && (
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground animate-[fadeUp_0.6s_0.1s_both]">
          <span className="flex items-center -space-x-1">
            <span className="block size-2.5 shrink-0 rounded-full bg-red-500" />
            <span className="block size-2.5 shrink-0 rounded-full bg-green-500" />
            <span className="block size-2.5 shrink-0 rounded-full bg-blue-500" />
          </span>
          Join{' '}
          <span className="font-mono font-medium text-foreground">
            {leagueCount}
          </span>{' '}
          leagues tracking their history
        </div>
      )}

      <h1
        className="
            text-[clamp(2.6rem,6vw,4.5rem)] leading-[1.05] tracking-tight
            text-foreground max-w-175 font-heading
            animate-[fadeUp_0.6s_0.25s_both]
          "
      >
        Your league&apos;s story,{' '}
        <em className="italic text-primary">beautifully told</em>
      </h1>

      <p
        className="
          mt-5 text-base text-muted-foreground max-w-120 leading-relaxed
          animate-[fadeUp_0.6s_0.4s_both]
          "
      >
        Explore every season, rivalry, and record across your league&apos;s full
        history — from the first draft pick to the last championship.
      </p>

      <div className="flex flex-wrap justify-center gap-3 mt-9 animate-[fadeUp_0.6s_0.55s_both]">
        <Button
          size="lg"
          className="text-[0.82rem] px-6 cursor-pointer"
          onClick={handleConnectLeague}
        >
          Connect Your League <ArrowRight />
        </Button>

        {isSignedIn && (
          <Button
            variant="outline"
            size="lg"
            className="text-[0.82rem] px-6 cursor-pointer aria-expanded:border-primary aria-expanded:bg-primary/10 aria-expanded:text-primary"
            aria-expanded={showMyLeagues}
            aria-controls="my-leagues-panel"
            onClick={handleToggleMyLeagues}
          >
            View My Leagues
            {myLeaguesCount !== null && (
              <span
                aria-label={`${myLeaguesCount} leagues`}
                className="rounded-full bg-muted px-1.5 font-mono text-[11px] text-muted-foreground"
              >
                {myLeaguesCount}
              </span>
            )}
            <ChevronDown
              className={`transition-transform motion-reduce:transition-none ${showMyLeagues ? 'rotate-180' : ''}`}
            />
          </Button>
        )}

        <Button
          variant="outline"
          size="lg"
          className="text-[0.82rem] px-6 cursor-pointer"
          onClick={handleViewDemo}
        >
          View Demo
        </Button>
      </div>

      {showMyLeagues && myLeagues && (
        <MyLeaguesPanel
          leagues={myLeagues}
          onRetry={loadMyLeagues}
          onConnect={handleConnectLeague}
        />
      )}

      {showConnectForm && (
        <div className="mt-8 w-full max-w-lg animate-[fadeUp_0.4s_both]">
          <form
            className="flex gap-2"
            onSubmit={(e) => void handleConnectSubmit(e)}
          >
            <Select
              value={platform}
              onValueChange={(v) => {
                if (isPlatform(v)) {
                  setPlatform(v);
                  // Switching platform re-gates the ESPN credential fields.
                  setNeedsEspnCredentials(false);
                  setError(null);
                }
              }}
            >
              <SelectTrigger className="w-36 shrink-0">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ESPN">ESPN</SelectItem>
                <SelectItem value="SLEEPER">Sleeper</SelectItem>
                <SelectItem value="YAHOO">Yahoo</SelectItem>
              </SelectContent>
            </Select>
            <Input
              className="flex-1"
              placeholder="League ID"
              name="leagueId"
              autoComplete="on"
              value={leagueId}
              onChange={(e) => {
                setLeagueId(e.target.value);
                // A new league ID must be looked up afresh before we know
                // whether to ask for ESPN credentials.
                setNeedsEspnCredentials(false);
                setError(null);
              }}
              disabled={loading}
            />
            <Button
              type="submit"
              disabled={loading || !leagueId.trim()}
              className="cursor-pointer shrink-0"
            >
              {loading ? (
                <Spinner className="text-primary-foreground" />
              ) : (
                'Connect'
              )}
            </Button>
          </form>
          {platform === 'ESPN' && needsEspnCredentials && (
            <div className="mt-3 flex flex-col gap-4 text-left">
              <p className="text-sm text-muted-foreground">
                League not added to LeagueQL yet. Enter your ESPN cookies below
                to connect.
              </p>
              <EspnCredentialFields
                swid={espnSwid}
                espnS2={espnS2}
                onSwidChange={setEspnSwid}
                onEspnS2Change={setEspnS2}
                onAutofill={(nextSwid, nextEspnS2) => {
                  setEspnSwid(nextSwid);
                  setEspnS2(nextEspnS2);
                }}
                disabled={loading}
                showManualInstructions={false}
              />
              <div className="flex items-center gap-2">
                <input
                  id="espn-auto-refresh"
                  type="checkbox"
                  className="size-4 cursor-pointer accent-primary"
                  checked={espnAutoRefresh}
                  onChange={(e) => setEspnAutoRefresh(e.target.checked)}
                  disabled={loading}
                />
                <div className="flex items-center gap-1.5">
                  <Label htmlFor="espn-auto-refresh" className="cursor-pointer">
                    Enable automatic weekly refresh
                  </Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent side="right" className="max-w-64">
                        When enabled, LeagueQL securely stores your ESPN cookies
                        (encrypted) and refreshes your league automatically each
                        week during the season. ESPN cookies expire
                        periodically, so you may occasionally need to re-enter
                        them.
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>
            </div>
          )}
          {loading && (
            <div className="mt-4 flex flex-col gap-1.5">
              <Progress value={progress} className="w-full" />
              <p className="text-xs text-muted-foreground">{loadingMessage}</p>
            </div>
          )}
          {error && (
            <Alert variant="destructive" className="mt-3 text-left">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
      )}
    </section>
  );
}
