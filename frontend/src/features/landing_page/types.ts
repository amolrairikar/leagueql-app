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
  icon: React.FC<LucideProps>;
  title: string;
  desc: string;
}

export interface HowStep {
  step: string;
  icon: React.FC<LucideProps>;
  title: string;
  desc: string;
}

export interface Platform {
  name: string;
  logo: string;
}
