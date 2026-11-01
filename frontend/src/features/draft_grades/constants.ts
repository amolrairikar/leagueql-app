export const GREEN = '#16a34a';

export const RED = '#dc2626';

export const GREEN_BG = '#dcfce7';

export const RED_BG = '#fee2e2';

// ── Constants ─────────────────────────────────────────────────────────────────

// ── Types ─────────────────────────────────────────────────────────────────────

// ── Constants ─────────────────────────────────────────────────────────────────

export const STEAL_DELTA_MIN = 5; // draft_rank_delta >= this → steal

export const BUST_DELTA_MAX = -5; // draft_rank_delta <= this → potential bust

export const BUST_ROUND_BUFFER = 4; // bust only when picked more than this many rounds before the last

export const BUST_ROUND_MAX = 10; // only flag busts / show alternatives for rounds 1–10

export const ALT_PICK_ROUND_WINDOW = 2; // suggest alternatives within this many rounds of the pick

export const AUCTION_BUST_MIN_BID = 5; // auction: only flag busts on players that cost more than this

export const DELTA_PILL_POS = 3;

export const DELTA_PILL_NEG = -3;

// ── Helpers ───────────────────────────────────────────────────────────────────
