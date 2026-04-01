import type { LucideProps } from 'lucide-react';

import GitHubSvg from '@/assets/github.svg?react';

export function GitHubIcon({ size = 24, className }: LucideProps) {
  return <GitHubSvg width={size} height={size} className={className} />;
}
