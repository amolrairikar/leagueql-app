import { type ManagerData } from '@/features/manager_history/types';

export function ManagerHeader({
  managers,
  idx,
  m,
  onSelect,
}: {
  managers: ManagerData[];
  idx: number;
  m: ManagerData;
  onSelect: (index: number) => void;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-6">
      <div className="flex items-center gap-4 sm:flex-1 order-2 sm:order-1">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center text-[18px] font-medium text-white shrink-0"
          style={{ background: m.color }}
        >
          {m.init}
        </div>
        <div className="flex-1">
          <div className="text-[18px] font-medium text-foreground">
            {m.owner_username}
          </div>
        </div>
      </div>
      {managers.length > 1 && (
        <select
          className="px-3 py-2 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer w-full sm:w-auto order-1 sm:order-2"
          value={idx}
          onChange={(e) => onSelect(Number(e.target.value))}
        >
          {managers.map((mgr, i) => (
            <option key={mgr.owner_id} value={i}>
              {mgr.owner_username}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
