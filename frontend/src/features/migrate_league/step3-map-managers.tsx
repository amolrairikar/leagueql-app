import { useState } from 'react';

import type { Platform } from '@/components/api/types';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  type ManagerMappingEntry,
  type TeamEntry,
} from '@/features/migrate_league/api-calls';
import { PLATFORM_LABELS } from '@/features/migrate_league/constants';
import { type NewPlatformUser } from '@/features/migrate_league/types';
import {
  getUserId,
  getUserDisplayName,
} from '@/features/migrate_league/user-helpers';

export const NOT_RETURNING = '__not_returning__';

export function Step3({
  currentManagers,
  newPlatformUsers,
  newPlatform,
  onNext,
  onBack,
}: {
  currentManagers: TeamEntry[];
  newPlatformUsers: NewPlatformUser[];
  newPlatform: Platform;
  onNext: (mapping: ManagerMappingEntry[]) => void;
  onBack: () => void;
}) {
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);

  const selectedValues = Object.values(selections).filter(
    (v) => v && v !== NOT_RETURNING,
  );
  const hasDuplicates = new Set(selectedValues).size !== selectedValues.length;

  function handleChange(ownerId: string, newUserId: string) {
    setSelections((prev) => ({ ...prev, [ownerId]: newUserId }));
    setValidationError(null);
  }

  function handleNext() {
    const mapped = Object.entries(selections).filter(
      ([, v]) => v && v !== NOT_RETURNING,
    );
    if (mapped.length === 0) {
      setValidationError('At least one manager must be mapped.');
      return;
    }
    if (hasDuplicates) {
      setValidationError('Each new platform user can only be mapped once.');
      return;
    }

    const mapping: ManagerMappingEntry[] = mapped.map(
      ([currentOwnerId, newOwnerId]) => {
        const user = newPlatformUsers.find((u) => getUserId(u) === newOwnerId);
        const mgr = currentManagers.find(
          (m) => m.primary_owner_id === currentOwnerId,
        );
        return {
          currentPlatformOwnerId: currentOwnerId,
          newPlatformOwnerId: newOwnerId,
          displayName: user
            ? getUserDisplayName(user)
            : (mgr?.display_name ?? currentOwnerId),
        };
      },
    );
    onNext(mapping);
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-[13px] font-medium mb-1">Map managers</p>
        <p className="text-[12px] text-muted-foreground">
          Match each current manager to their {PLATFORM_LABELS[newPlatform]}{' '}
          account. Leave managers who left the league as &quot;Not
          returning&quot;.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 text-[11px] font-medium uppercase tracking-wide text-muted-foreground px-1">
        <span>Current manager</span>
        <span>{PLATFORM_LABELS[newPlatform]} account</span>
      </div>

      <div className="flex flex-col gap-2 overflow-y-auto max-h-64 pr-1">
        {currentManagers.map((mgr) => {
          const selected = selections[mgr.primary_owner_id] ?? '';
          const isDuplicate =
            selected &&
            selected !== NOT_RETURNING &&
            selectedValues.filter((v) => v === selected).length > 1;

          return (
            <div
              key={mgr.primary_owner_id}
              className="grid grid-cols-2 gap-3 items-center"
            >
              <div className="flex flex-col">
                <span className="text-[13px] font-medium">
                  {mgr.display_name}
                </span>
              </div>
              <Select
                value={selected}
                onValueChange={(v) => handleChange(mgr.primary_owner_id, v)}
              >
                <SelectTrigger
                  className={`text-[13px] ${isDuplicate ? 'border-destructive' : ''}`}
                >
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NOT_RETURNING}>Not returning</SelectItem>
                  {newPlatformUsers.map((user) => (
                    <SelectItem key={getUserId(user)} value={getUserId(user)}>
                      {getUserDisplayName(user)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        })}
      </div>

      {(validationError ??
        (hasDuplicates &&
          'Each new platform user can only be mapped once.')) && (
        <p className="text-sm text-destructive">
          {validationError ?? 'Each new platform user can only be mapped once.'}
        </p>
      )}

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1 cursor-pointer"
          onClick={onBack}
        >
          Back
        </Button>
        <Button
          className="flex-1 cursor-pointer"
          onClick={handleNext}
          disabled={hasDuplicates}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
