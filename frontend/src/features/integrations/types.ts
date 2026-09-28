/** Integration categories (frontend/integrations); mirror the backend enum. */
export type IntegrationCategory =
  'ai_prompt' | 'dashboard' | 'spreadsheet' | 'bot' | 'notebook';

/** Views in the league export ZIP an integration can read. */
export type ExportView =
  | 'standings'
  | 'weekly_standings'
  | 'matchups'
  | 'draft'
  | 'transactions'
  | 'playoff_bracket'
  | 'league_settings'
  | 'teams';

/** Body of `POST /integrations`. */
export interface IntegrationSubmission {
  name: string;
  author_handle: string;
  category: IntegrationCategory;
  link: string;
  views: ExportView[];
  description: string;
  setup_steps: string[];
  prompt?: string | null;
}

/** One approved integration from `GET /integrations`. */
export interface Integration extends IntegrationSubmission {
  issue_number: number;
  featured: boolean;
}

export interface ListIntegrationsResponse {
  detail: string;
  data: { items: Integration[] };
}

export interface SubmitIntegrationResponse {
  detail: string;
  data: { issue_number: number };
}
