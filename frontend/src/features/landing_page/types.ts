import type { LucideProps } from 'lucide-react';

export interface NavLinkItem {
  label: string;
  href: string;
  icon: React.FC<LucideProps>;
  external?: boolean;
}

export interface Slide {
  title: string;
  url: string;
  caption: string;
  image?: string;
}

export interface Feature {
  icon: string;
  title: string;
  desc: string;
}

export interface PricingPlan {
  name: string;
  price: string;
  period: string;
  billedAs: string;
  /** Visually emphasize this plan as the recommended / best-value option. */
  highlight?: boolean;
  /** Optional badge text (e.g. "Best value"). */
  badge?: string;
}

export interface PremiumFeature {
  title: string;
  desc: string;
}
