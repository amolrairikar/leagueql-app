# Design

## Owner-level flag on `ESPN_CREDENTIALS`

ESPN cookies belong to the owner and are shared by every ESPN league they opted into
auto-refresh, so the rejection flag lives on `USER#{id} / ESPN_CREDENTIALS` as `auth_failed_at`
(ISO 8601), not on each league's `METADATA`.

- `store_credentials` uses `put_item`, which replaces the whole item. Any re-store (a successful
  opted-in refresh, or the opted-in blocked-refresh enrollment path) clears the flag with no
  extra code.
- `mark_auth_failed(user_id, expected_updated_at)` is an `update_item` conditioned on
  `attribute_exists(PK) AND updated_at = :u`. If the owner re-stored cookies while the scheduled
  refresh was in flight, the condition fails and the new cookies stay unflagged.
- The onboarder reads the item once with `get_stored_credentials`, which returns the decrypted
  cookies plus `updated_at`, so it knows which version it used.

## Classifying async auth failures

`fetch_one` records the HTTP status of a failed request as `error_status`. When
`validate_api_results` finds every season failed and every failure carries a `401`/`403`, it
raises `UpstreamAuthError` (a `RuntimeError` subclass). The handler maps it to `ESPN_AUTH` for ESPN
and to `UPSTREAM` for other platforms. It is caught before the generic `RuntimeError` branch.
Partial failures still drop the failed seasons (unchanged).

## Marking only stored-cookie runs

Only a run that used stored cookies marks the item. A user-initiated refresh supplies cookies in
the request and already shows the failure in the dialog. Marking is best-effort: an error is
logged and never changes the recorded failure.

## Skipping flagged owners

The scheduled refresh reads `auth_failed_at` (projection only, no KMS) for each selected ESPN
league's owner and skips the league when it is set. This stops repeated calls to ESPN with dead
cookies, and it cannot strand a league because re-storing cookies clears the flag.

## Surfacing to the owner

`GET /leagues/{leagueId}` computes `espn_reauth_required` only for the owner of an ESPN league with
`auto_refresh_enabled`: true when the credential item is missing or carries `auth_failed_at`.
Non-owners always get `false`. The frontend reads it through `useIsOwner`, shows a banner, and
exposes "Update ESPN Cookies", which opens the existing refresh dialog with auto-refresh
pre-checked. Both success paths in that dialog re-store the cookies.
