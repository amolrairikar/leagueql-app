import { Switch } from '@/components/ui/switch';
import type { SeasonPhase } from '@/lib/matchups';

/**
 * "Regular season / Postseason" switch for the record boards, laid out like the
 * home page's all-time standings toggle.
 */
export function SeasonPhaseToggle({
  value,
  onChange,
}: {
  value: SeasonPhase;
  onChange: (phase: SeasonPhase) => void;
}) {
  const postseason = value === 'postseason';

  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`text-[12px] font-medium ${
          postseason ? 'text-muted-foreground' : 'text-foreground'
        }`}
      >
        Regular season
      </span>
      <Switch
        checked={postseason}
        onCheckedChange={(checked) =>
          onChange(checked ? 'postseason' : 'regular')
        }
        aria-label="Toggle between regular season and postseason records"
        className="cursor-pointer"
      />
      <span
        className={`text-[12px] font-medium ${
          postseason ? 'text-foreground' : 'text-muted-foreground'
        }`}
      >
        Postseason
      </span>
    </div>
  );
}
