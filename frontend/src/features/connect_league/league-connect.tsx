import { Navigate } from 'react-router-dom';

/**
 * The `/connect_league` route is retired. Yahoo now finishes its OAuth round-trip
 * inline on the landing page (frontend/landing-page), which reads the
 * `platform=YAHOO`, `yahooLinked`, and `leagueId` return params on load.
 *
 * This route is kept only as a redirect shim so in-flight OAuth callbacks and stale
 * bookmarks still resolve: a Yahoo return is forwarded to `/` with its params
 * preserved (so the inline resume runs), and anything else goes to the landing
 * connect entry. The standalone ESPN/Sleeper onboard/refresh form was already
 * retired — those onboard inline on the landing page and ESPN refresh happens in the
 * in-dashboard dialog (frontend/navigation-sidebar).
 */
export default function LeagueConnect() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('platform')?.toUpperCase() === 'YAHOO') {
    return <Navigate to={`/?${params.toString()}`} replace />;
  }
  return <Navigate to="/?connect=true" replace />;
}
