import type { LucideProps } from 'lucide-react';

export interface NavLinkItem {
  label: string;
  href: string;
  icon: React.FC<LucideProps>;
}

export interface Slide {
  title: string;
  badge: string;
  url: string;
  caption: string;
  image?: string;
}

export interface Feature {
  icon: string;
  title: string;
  desc: string;
}
