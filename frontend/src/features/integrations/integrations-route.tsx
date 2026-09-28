import { Navigate } from 'react-router-dom';

import IntegrationsPage from './integrations-page';

import { isIntegrationsEnabled } from '@/lib/feature-flags';

/**
 * `/integrations` behind the `integrations` flag (frontend/integrations): the
 * page when the flag is on, otherwise a redirect home. Evaluated at render time
 * so a flag toggle (which remounts the tree) takes effect without a reload.
 */
export default function IntegrationsRoute() {
  if (!isIntegrationsEnabled()) return <Navigate to="/home" replace />;
  return <IntegrationsPage />;
}
