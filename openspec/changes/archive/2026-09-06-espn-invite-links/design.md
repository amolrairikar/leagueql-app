## Context

See proposal.md — Why. Membership in a private ESPN league is stored as the `members` string set on the league METADATA item, and `require_league_member` gates ESPN reads to owner + members. Today the only self-service path into `members` is `POST /leagues/{id}/verify-membership`, which replays the caller's ESPN cookies against ESPN. The ownership-transfer feature already establishes the pattern this change reuses: `create_transfer_token` mints `secrets.token_urlsafe(32)` and stores only its sha256 hash; `claim_ownership` redeems it with a constant-time compare (`hmac.compare_digest`) and `add_league_member`.

## Goals / Non-Goals

**Goals:**
- An owner-minted, reusable invite link that adds any signed-in redeemer to `members` with no ESPN cookies.
- Reuse the existing token-hash pattern and the `add_league_member` helper.

**Non-Goals:**
- Per-recipient links, auto-expiry, or usage tracking (one reusable hash; regenerate to revoke).
- Changing the read gate (`require_league_member`) or Sleeper's open-read behavior.
- Changing owner-side onboarding/refresh/migrate cookie handling or the Chrome extension.

## Decisions

- **Store a single `invite_token_hash` on METADATA, no expiry.** Mirrors `transfer_token_hash` but multi-use: `accept-invite` does NOT remove the hash on redemption. Revocation = mint again (overwrite) — matches the confirmed "one reusable, revocable link" decision. Alternative considered: single-use per-recipient tokens (rejected — higher friction, defeats "share one link with the league").
- **Redemption needs no race-safe conditional write.** Unlike `claim_ownership` (which swaps a single owner and must be single-use), `accept-invite` only does an idempotent `ADD members`, so a plain `add_league_member` is sufficient and concurrent redemptions are naturally safe.
- **Remove `verify-membership` rather than keep it as a fallback.** Confirmed with the user ("replace the cookie verification process entirely"). Keeps one join path and avoids leaving a cookie flow the UI no longer surfaces. Note: `EspnMembersPayload` is still used by `get_espn_members`, so keep that model; only the `verify_membership` route and its frontend caller are removed.
- **Link shape built on the frontend:** `${origin}/join/${leagueId}?platform=ESPN&invite=${token}`. The backend returns only the plaintext token; the owner dialog composes the full URL. The `/join/:leagueId` page is a `ProtectedRoute`, so Clerk sign-in happens first and returns the user to the page to auto-redeem.
- **Non-member 403 UX becomes informational.** `MembershipGuard`, the landing page, and the connect flow stop offering cookie entry / auto-verify and instead tell the caller to get an invite link from the owner.

## Risks / Trade-offs

- **Anyone with the link who signs in gains read access, bypassing ESPN's own membership proof.** → Accepted, owner-vouches model; the dialog states this and regenerating revokes a leaked link.
- **No owner reachable ⇒ no new members.** After removing `verify-membership`, a leaguemate with valid cookies can no longer self-join. → Ownership-transfer token remains the fallback for handing off a league; acceptable per the confirmed decision.
- **A long-lived hash is a standing secret.** → Only the sha256 hash is stored (never the plaintext), constant-time compared, and the owner can rotate it at will by minting again.

## Migration Plan

Ship backend and frontend together. Removing `verify-membership` is the only breaking change; no data migration is needed (existing `members` sets and METADATA items are untouched; `invite_token_hash` is simply absent until an owner mints one). Rollback is a straight revert — no persisted state depends on the new field.
