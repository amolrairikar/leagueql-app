import { http, HttpResponse } from 'msw';

import type { Integration } from '../types';

import { API } from '@/test/msw/server';

export const HISTORIAN: Integration = {
  issue_number: 3,
  name: 'League Historian',
  category: 'ai_prompt',
  link: 'https://github.com/example/historian',
  views: ['standings', 'matchups', 'transactions'],
  description: 'Answers questions across every season you exported.',
  setup_steps: ['Export all seasons.', 'Upload the ZIP to Claude.'],
  prompt: 'Read README.md and manifest.json before anything else.',
  featured: true,
};

export const RECAP_BOT: Integration = {
  issue_number: 2,
  name: 'Weekly Recap Bot',
  category: 'bot',
  link: 'https://github.com/example/recap-bot',
  views: ['matchups'],
  description: 'Posts a Discord recap every Tuesday.',
  setup_steps: ['Fork the repo.', 'Add your webhook secret.'],
  prompt: null,
  featured: false,
};

export const POWER_SHEET: Integration = {
  issue_number: 1,
  name: 'Power Rankings Sheet',
  category: 'spreadsheet',
  link: 'https://docs.google.com/spreadsheets/example',
  views: ['standings'],
  description: 'Turns standings into all-play power rankings.',
  setup_steps: ['Make a copy of the template.'],
  prompt: null,
  featured: false,
};

export const ALL_INTEGRATIONS = [HISTORIAN, RECAP_BOT, POWER_SHEET];

export function integrationsList(items: Integration[]) {
  return http.get(`${API}/integrations`, () =>
    HttpResponse.json({ detail: 'Integrations', data: { items } }),
  );
}

export function integrationsListError(status = 502) {
  return http.get(`${API}/integrations`, () =>
    HttpResponse.json(
      { detail: "Couldn't load integrations right now." },
      { status },
    ),
  );
}
