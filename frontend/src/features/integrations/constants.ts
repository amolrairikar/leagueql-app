import type { ExportView, IntegrationCategory } from './types';

/** Category order for the filter chips and submit form. */
export const CATEGORIES: IntegrationCategory[] = [
  'ai_prompt',
  'dashboard',
  'spreadsheet',
  'bot',
  'notebook',
];

/** Singular label shown on a card's category badge. */
export const CATEGORY_LABELS: Record<IntegrationCategory, string> = {
  ai_prompt: 'AI prompt',
  dashboard: 'Dashboard',
  spreadsheet: 'Spreadsheet',
  bot: 'Bot',
  notebook: 'Notebook',
};

/** Plural label shown on the filter chips. */
export const CATEGORY_CHIP_LABELS: Record<IntegrationCategory, string> = {
  ai_prompt: 'AI prompts',
  dashboard: 'Dashboards',
  spreadsheet: 'Spreadsheets',
  bot: 'Bots',
  notebook: 'Notebooks',
};

/** The export's view names, in the order the submit form lists them. */
export const EXPORT_VIEWS: ExportView[] = [
  'standings',
  'weekly_standings',
  'matchups',
  'draft',
  'transactions',
  'playoff_bracket',
  'league_settings',
  'teams',
];

export interface HowItWorksStep {
  title: string;
  body: string;
}

export const HOW_IT_WORKS: HowItWorksStep[] = [
  {
    title: 'Export your league',
    body: 'Download a ZIP of <season>_<view>.json files, plus README.md and manifest.json.',
  },
  {
    title: 'Plug it into something',
    body: 'Upload it to an AI assistant, import it into a sheet, or point a script at it.',
  },
  {
    title: 'Share what you built',
    body: 'Submit it here so other leagues can reuse it. Every submission is reviewed before it goes live.',
  },
];

/** Field limits, kept in sync with the backend's submission model. */
export const LIMITS = {
  name: 60,
  authorHandle: 30,
  link: 300,
  description: 500,
  setupSteps: 6,
  setupStep: 200,
  prompt: 2000,
} as const;
