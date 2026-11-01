import { SeasonCard } from '@/features/manager_history/season-card';
import { type ManagerData } from '@/features/manager_history/types';
import { type Platform } from '@/lib/cookie-handler';

export function SeasonBySeason({
  m,
  platform,
}: {
  m: ManagerData;
  platform: Platform;
}) {
  return (
    <>
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Season-by-season results
      </p>
      <div className="flex flex-col gap-2.5 mb-6">
        {[...m.seasons].reverse().map((s) => (
          <SeasonCard
            key={`${m.owner_id}-${s.year}`}
            season={s}
            managerColor={m.color}
            username={m.owner_username}
            platform={platform}
          />
        ))}
      </div>
    </>
  );
}
