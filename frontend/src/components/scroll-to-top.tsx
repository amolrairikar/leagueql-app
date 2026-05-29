import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Resets the window scroll position to the top whenever the route changes.
 * React Router preserves scroll position across in-app navigations, which
 * otherwise leaves users partway down a new page (e.g. landing on the home
 * page after connecting a league on mobile).
 */
export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}
