import { Navigate } from 'react-router-dom';

import YahooConnectReturn from '@/features/connect_league/yahoo-connect-return';

/**
 * The `/connect_league` route. Its only remaining job is the Yahoo OAuth return:
 * Yahoo redirects the browser back here with `platform=YAHOO` (plus a
 * `yahooLinked` flag and the league id), which renders the two-phase
 * {@link YahooConnectReturn} UI.
 *
 * The standalone ESPN/Sleeper onboard/refresh form has been retired — ESPN and
 * Sleeper onboard inline on the landing page (frontend/landing-page) and ESPN
 * refresh happens in the in-dashboard dialog (frontend/navigation-sidebar). Any
 * other hit on this route is sent to the landing connect entry.
 */
export default function LeagueConnect() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('platform')?.toUpperCase() === 'YAHOO') {
    return (
      <YahooConnectReturn
        linked={params.get('yahooLinked') === '1'}
        leagueId={params.get('leagueId') ?? ''}
      />
    );
  }
  return <Navigate to="/?connect=true" replace />;
}
