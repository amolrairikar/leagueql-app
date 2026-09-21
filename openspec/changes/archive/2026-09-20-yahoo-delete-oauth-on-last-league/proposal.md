# Proposal

## Why

A user's Yahoo OAuth credentials are stored in a single per-user item
(`PK=USER#{clerk_user_id}, SK=YAHOO_OAUTH`), separate from any league's items
(`PK=LEAGUE#{canonical_league_id}`). `DELETE /leagues/{leagueId}` removes only
the league's items and S3 payloads, so deleting a Yahoo league leaves the
owner's encrypted OAuth token item orphaned in DynamoDB indefinitely — even
after the user has deleted every Yahoo league they own. This contradicts the
privacy commitment that stored Yahoo tokens are removed when the user requests
deletion of their league data.

We cannot simply delete the token item on every Yahoo league delete: one linked
Yahoo account backs *all* of that user's Yahoo leagues, so removing the token
while other Yahoo leagues remain would break their refreshes and force a
needless re-link.

## What Changes

- When `DELETE /leagues/{leagueId}` deletes a league whose effective platform is
  Yahoo, after the league's items and S3 payloads are removed the API SHALL
  check whether the owner still owns any *other* Yahoo league. If none remain,
  it deletes the owner's `YAHOO_OAUTH` token item so no orphaned credentials are
  left behind.
- If the owner still has at least one other Yahoo league, the token item is
  left in place (the link is still in use).
- Deleting an ESPN or Sleeper league never touches any `YAHOO_OAUTH` item.
- The OAuth-item cleanup is best-effort and fully self-contained: because the
  league data is already gone before it runs, any failure within it — the
  ownership-check GSI3 query included — is logged and alerted but never fails the
  league deletion, consistent with the existing S3 best-effort behavior.
- The API Lambda's IAM role is granted `dynamodb:Query` on the GSI3 index (it
  previously had Query only on the base table and GSI1), so the ownership-check
  query succeeds rather than failing with `AccessDeniedException`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `backend/delete-league`: deleting the owner's last Yahoo league now also
  removes their encrypted `YAHOO_OAUTH` token item.
- `backend/yahoo-oauth`: the token lifecycle gains a deletion path — a user's
  stored Yahoo tokens are removed once they no longer own any Yahoo league.

## Impact

- Backend only:
  - `src/common/yahoo_tokens.py` — `YahooTokenClient.delete_tokens`.
  - `src/api/yahoo_oauth.py` — `delete_tokens` module wrapper.
  - `src/api/helpers.py` — `owner_has_other_yahoo_leagues` (GSI3 query).
  - `src/api/routes.py` — `delete_league` invokes the cleanup for Yahoo leagues.
  - Backend unit + component tests.
- Infrastructure: `infrastructure/global/{prod,dev}/main.tf` — add
  `/index/GSI3` (primary + replica) to the API role's `CRUDDynamoDB` DynamoDB
  `Query` resources.
- No frontend or API-contract changes. No new DynamoDB items or indexes (reuses
  GSI3, the sparse all-METADATA index).
