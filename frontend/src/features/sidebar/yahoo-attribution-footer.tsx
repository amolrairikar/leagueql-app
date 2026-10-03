import yahooFantasyLogo from '@/assets/yahoo-fantasy-logo.svg';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

export const YAHOO_FANTASY_URL = 'https://sports.yahoo.com/fantasy/';

/**
 * Yahoo Fantasy attribution required by Yahoo's Fantasy Sports API terms
 * (frontend/yahoo-attribution). Rendered as the last child of the in-app
 * layout so it sits at the bottom of every in-app page. Shows only for Yahoo
 * leagues outside demo mode. The official logo must not be recolored, so it
 * sits on a white chip to stay legible in the dark theme.
 */
export function YahooAttributionFooter() {
  const { platform, leagueId } = getLeagueCookies();
  if (isDemoMode() || !leagueId || platform !== 'YAHOO') return null;

  return (
    <footer className="flex h-9 shrink-0 items-center justify-center border-t border-border bg-background/80 px-4 backdrop-blur-md">
      <a
        href={YAHOO_FANTASY_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 text-[0.72rem] tracking-wide text-muted-foreground no-underline transition-colors duration-200 hover:text-foreground"
      >
        <span className="flex items-center rounded bg-white px-1.5 py-1">
          <img
            src={yahooFantasyLogo}
            alt="Yahoo Fantasy"
            className="h-3 w-auto"
          />
        </span>
        Fantasy data provided by Yahoo Fantasy
      </a>
    </footer>
  );
}
