import { FileText, Info } from 'lucide-react';

import draftRecapScreenshot from '@/assets/draft-recap-screenshot.png';
import managerComparisonScreenshot from '@/assets/manager-comparison-screenshot.png';
import managerHistoryScreenshot from '@/assets/manager-history-screenshot.png';
import matchupRecordsScreenshot from '@/assets/matchup-records-screenshot.png';
import matchupsScreenshot from '@/assets/matchups-screenshot.png';
import playerRecordsScreenshot from '@/assets/player-records-screenshot.png';
import playoffBracketScreenshot from '@/assets/playoff-bracket-screenshot.png';
import standingsScreenshot from '@/assets/standings-screenshot.png';
import type {
  NavLinkItem,
  Slide,
  Feature,
  PricingPlan,
  PremiumFeature,
} from '@/features/landing_page/types';
import { SUBSCRIPTION_PRICES } from '@/lib/pricing';

export const NAV_LINKS: NavLinkItem[] = [
  { label: 'Changelog', href: '/changelog', icon: FileText, external: false },
  { label: 'Docs', href: '/docs', icon: Info, external: false },
];

export const SLIDES: Slide[] = [
  {
    title: 'Standings',
    url: 'leagueql.app/standings',
    caption: 'Current season standings',
    image: standingsScreenshot,
  },
  {
    title: 'Matchups',
    url: 'leagueql.app/matchups',
    caption: 'Weekly matchup results',
    image: matchupsScreenshot,
  },
  {
    title: 'Playoff Bracket',
    url: 'leagueql.app/playoff_bracket',
    caption: 'Visual playoff bracket',
    image: playoffBracketScreenshot,
  },
  {
    title: 'Manager Comparison',
    url: 'leagueql.app/manager_comparison',
    caption: 'Compare any two managers across all seasons',
    image: managerComparisonScreenshot,
  },
  {
    title: 'Manager History',
    url: 'leagueql.app/manager_history',
    caption: 'Individual manager performance over time',
    image: managerHistoryScreenshot,
  },
  {
    title: 'Draft Grades',
    url: 'leagueql.app/draft_grades',
    caption: 'Draft picks and their season performance',
    image: draftRecapScreenshot,
  },
  {
    title: 'Player Records',
    url: 'leagueql.app/player_records',
    caption: 'Single-game and season player records',
    image: playerRecordsScreenshot,
  },
  {
    title: 'Matchup Records',
    url: 'leagueql.app/matchup_records',
    caption: 'All-time matchup records between managers',
    image: matchupRecordsScreenshot,
  },
];

export const FEATURES: Feature[] = [
  {
    icon: '📜',
    title: 'Complete History',
    desc: 'Every season, every week, every score. Currently supported integrations include ESPN and Sleeper.',
  },
  {
    icon: '⚔️',
    title: 'Rivalry Tracker',
    desc: 'See your all-time head-to-head record against every manager, from the guaranteed win to the manager who always has your number.',
  },
  {
    icon: '🏆',
    title: 'Championship Timeline',
    desc: 'A visual hall of fame showing every champion across all seasons.',
  },
  {
    icon: '📈',
    title: 'Team Trends',
    desc: 'Chart how your team rankings have fluctuated throughout the years. Drill into your matchups for a particular season.',
  },
  {
    icon: '🔖',
    title: 'League Records',
    desc: 'Every record tracked and ranked automatically: single-week high scores, biggest blowouts, most unlucky losses.',
  },
  {
    icon: '🔀',
    title: 'Platform Migration',
    desc: 'Switched fantasy platforms? Use our league migration wizard to preserve your full all-time history across platforms.',
  },
];

// Subscription plans shown in the landing-page pricing table (FE-001). A yearly
// subscription is $14.99 vs. $35.88 for 12 monthly payments — ~58% cheaper.
export const PRICING_PLANS: PricingPlan[] = [
  {
    name: 'Monthly',
    price: SUBSCRIPTION_PRICES.MONTHLY,
    period: '/month',
    billedAs: 'Billed monthly',
  },
  {
    name: 'Yearly',
    price: SUBSCRIPTION_PRICES.YEARLY,
    period: '/year',
    billedAs: 'Billed annually — save ~58%',
    highlight: true,
    badge: 'Best value',
  },
];

// Features unlocked by a subscription (freemium model). Everything else is free.
export const PREMIUM_FEATURES: PremiumFeature[] = [
  {
    title: 'Schedule-swap simulator',
    desc: "See what every team's record would be under each other manager's schedule — find out who was schedule-lucky and who got robbed.",
  },
  {
    title: 'Weekly awards',
    desc: 'Weekly superlatives that crown the highest scorer, biggest blowout, closest call, and other standout performances for each week.',
  },
];

export const FOOTER_LINKS: string[] = ['About', 'Privacy', 'GitHub'];
