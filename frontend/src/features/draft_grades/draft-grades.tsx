import { Suspense, use, useCallback, useMemo, useState } from 'react';

import { type DraftPickItem } from './api-calls';
import { type DraftResult, useDraftData } from './use-draft-data';

import { TooltipProvider } from '@/components/ui/tooltip';
import { getAlts } from '@/features/draft_grades/alts';
import { BustAlternatives } from '@/features/draft_grades/bust-alternatives';
import {
  AUCTION_BUST_MIN_BID,
  BUST_DELTA_MAX,
  BUST_ROUND_BUFFER,
  BUST_ROUND_MAX,
  STEAL_DELTA_MIN,
} from '@/features/draft_grades/constants';
import { DraftFilterBar } from '@/features/draft_grades/draft-filter-bar';
import { DraftPicksTable } from '@/features/draft_grades/draft-picks-table';
import { DraftStatStrip } from '@/features/draft_grades/draft-stat-strip';
import { DraftGradesSkeleton } from '@/features/draft_grades/skeleton';

interface DraftGradesContentProps {
  promise: Promise<DraftResult>;
  seasons: string[];
  selectedSeason: string;
  onSeasonChange: (season: string) => void;
  isDemo: boolean;
  demoAuction: boolean;
  onDemoAuctionChange: (auction: boolean) => void;
}

function DraftGradesContent({
  promise,
  seasons,
  selectedSeason,
  onSeasonChange,
  isDemo,
  demoAuction,
  onDemoAuctionChange,
}: DraftGradesContentProps) {
  const result = use(promise);

  const allPicks = useMemo(() => (result.ok ? result.data : []), [result]);

  // Auction vs. snake is driven entirely by the loaded dataset's flag. In demo
  // mode a Switch (below) chooses which dataset the parent fetches.
  const isAuction = allPicks[0]?.is_auction ?? false;
  const fmtBid = (n: number) => `$${n}`;
  const pickLabel = (pick: DraftPickItem) =>
    isAuction
      ? fmtBid(pick.bid_amount)
      : `Rd ${pick.round} · Pick ${pick.overall_pick_number}`;

  const managers = useMemo(() => {
    const seen = new Map<string, { id: string; username: string }>();
    for (const p of allPicks) {
      if (!seen.has(p.team_id)) {
        seen.set(p.team_id, { id: p.team_id, username: p.owner_username });
      }
    }
    return [...seen.values()].sort((a, b) =>
      a.username.localeCompare(b.username),
    );
  }, [allPicks]);

  const [rawSelectedManager, setSelectedManager] = useState(
    managers[0]?.id ?? '',
  );
  const [openBusts, setOpenBusts] = useState<Record<string, boolean>>({});

  // Derive the effective selection during render so a stale id (after the
  // manager list changes) falls back to the first manager without an effect.
  const selectedManager = managers.some((m) => m.id === rawSelectedManager)
    ? rawSelectedManager
    : (managers[0]?.id ?? '');

  const picks = useMemo(
    () => allPicks.filter((p) => p.team_id === selectedManager),
    [allPicks, selectedManager],
  );

  // Best/worst grading needs a draft_rank_delta; picks with null analytics
  // (e.g. D/ST, kickers, unscored players) are excluded per frontend/draft-grades.
  const scorablePicks = picks.filter(
    (p) =>
      p.position !== 'K' && p.position !== 'D/ST' && p.draft_rank_delta != null,
  );

  const bestPick = scorablePicks.length
    ? scorablePicks.reduce((best, p) =>
        (p.draft_rank_delta ?? 0) > (best.draft_rank_delta ?? 0) ? p : best,
      )
    : null;

  const worstPick = scorablePicks.length
    ? scorablePicks.reduce((worst, p) =>
        (p.draft_rank_delta ?? 0) < (worst.draft_rank_delta ?? 0) ? p : worst,
      )
    : null;

  const maxRound = allPicks.length
    ? Math.max(...allPicks.map((p) => p.round))
    : 0;
  const isBustPick = useCallback(
    (p: DraftPickItem) =>
      p.draft_rank_delta != null &&
      p.draft_rank_delta <= BUST_DELTA_MAX &&
      (isAuction
        ? p.bid_amount > AUCTION_BUST_MIN_BID
        : p.round <= maxRound - BUST_ROUND_BUFFER && p.round <= BUST_ROUND_MAX),
    [isAuction, maxRound],
  );
  const busts = picks.filter(isBustPick).length;
  const steals = picks.filter(
    (p) => p.draft_rank_delta != null && p.draft_rank_delta >= STEAL_DELTA_MIN,
  ).length;

  const toggleBust = (key: string) => {
    setOpenBusts((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const bustsWithAlts = useMemo(
    () =>
      picks.flatMap((pick, i) => {
        if (!isBustPick(pick)) return [];
        const alts = getAlts(pick, allPicks, isAuction);
        if (alts.length === 0) return [];
        return [
          { pick, alts, bustKey: `${selectedManager}-${selectedSeason}-${i}` },
        ];
      }),
    [picks, allPicks, isAuction, isBustPick, selectedManager, selectedSeason],
  );

  const bustsWithAltsMap = useMemo(
    () => new Map(bustsWithAlts.map((item) => [item.bustKey, item])),
    [bustsWithAlts],
  );

  if (!result.ok) {
    return (
      <p className="text-[13px] text-destructive text-center py-8">
        {result.error}
      </p>
    );
  }

  return (
    <TooltipProvider>
      {/* Filter Bar */}
      <DraftFilterBar
        seasons={seasons}
        selectedSeason={selectedSeason}
        onSeasonChange={onSeasonChange}
        managers={managers}
        selectedManager={selectedManager}
        onManagerChange={setSelectedManager}
        isDemo={isDemo}
        demoAuction={demoAuction}
        onDemoAuctionChange={onDemoAuctionChange}
      />

      <DraftStatStrip
        bestPick={bestPick}
        worstPick={worstPick}
        steals={steals}
        busts={busts}
        isAuction={isAuction}
        pickLabel={pickLabel}
        fmtBid={fmtBid}
      />

      <DraftPicksTable
        picks={picks}
        selectedManager={selectedManager}
        selectedSeason={selectedSeason}
        isAuction={isAuction}
        isBustPick={isBustPick}
        bustsWithAltsMap={bustsWithAltsMap}
        openBusts={openBusts}
        toggleBust={toggleBust}
        pickLabel={pickLabel}
        fmtBid={fmtBid}
      />

      {bustsWithAlts.length > 0 && (
        <BustAlternatives
          bustsWithAlts={bustsWithAlts}
          openBusts={openBusts}
          toggleBust={toggleBust}
          pickLabel={pickLabel}
          isAuction={isAuction}
          fmtBid={fmtBid}
        />
      )}
    </TooltipProvider>
  );
}

export default function DraftGrades() {
  const {
    seasons,
    isDemo,
    selectedSeason,
    setSelectedSeason,
    demoAuction,
    setDemoAuction,
    draftPromise,
  } = useDraftData();

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-250 mx-auto w-full">
        <Suspense fallback={<DraftGradesSkeleton />}>
          <DraftGradesContent
            promise={draftPromise}
            seasons={seasons}
            selectedSeason={selectedSeason}
            onSeasonChange={setSelectedSeason}
            isDemo={isDemo}
            demoAuction={demoAuction}
            onDemoAuctionChange={setDemoAuction}
          />
        </Suspense>
      </div>
    </div>
  );
}
