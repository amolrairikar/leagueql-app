import { Switch } from '@/components/ui/switch';

export function DraftFilterBar({
  seasons,
  selectedSeason,
  onSeasonChange,
  managers,
  selectedManager,
  onManagerChange,
  isDemo,
  demoAuction,
  onDemoAuctionChange,
}: {
  seasons: string[];
  selectedSeason: string;
  onSeasonChange: (season: string) => void;
  managers: { id: string; username: string }[];
  selectedManager: string;
  onManagerChange: (managerId: string) => void;
  isDemo: boolean;
  demoAuction: boolean;
  onDemoAuctionChange: (auction: boolean) => void;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 mb-6">
      <div className="flex items-center gap-2.5">
        <span className="text-[12px] font-medium text-muted-foreground w-16 sm:w-auto">
          Season
        </span>
        <select
          className="px-3 py-1.5 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
          value={selectedSeason}
          onChange={(e) => onSeasonChange(e.target.value)}
        >
          {[...seasons]
            .sort((a, b) => Number(b) - Number(a))
            .map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
        </select>
      </div>
      <div className="flex items-center gap-2.5">
        <span className="text-[12px] font-medium text-muted-foreground w-16 sm:w-auto sm:ml-2">
          Manager
        </span>
        <select
          className="px-3 py-1.5 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
          value={selectedManager}
          onChange={(e) => onManagerChange(e.target.value)}
        >
          {managers.map((mgr) => (
            <option key={mgr.id} value={mgr.id}>
              {mgr.username}
            </option>
          ))}
        </select>
      </div>
      {isDemo && (
        <label className="flex items-center gap-2 cursor-pointer sm:ml-2">
          <span
            className={`text-[12px] font-medium ${demoAuction ? 'text-muted-foreground' : 'text-foreground'}`}
          >
            Snake
          </span>
          <Switch
            checked={demoAuction}
            onCheckedChange={onDemoAuctionChange}
            aria-label="Toggle auction draft display"
          />
          <span
            className={`text-[12px] font-medium ${demoAuction ? 'text-foreground' : 'text-muted-foreground'}`}
          >
            Auction
          </span>
        </label>
      )}
    </div>
  );
}
