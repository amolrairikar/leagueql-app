# ownership-transfer Specification

## Purpose
Surface league ownership in the UI: gate owner-only sidebar actions to the owner, give non-owners an ESPN membership-verification path, and provide the ownership transfer/claim flow. Owner state comes from the current league's `is_owner`, and mutating call sites surface a `403` as an owner-only/membership message inline.

## Requirements

### Requirement: Gate owner-only actions
The sidebar SHALL show Refresh / Migrate / Transfer Ownership / Delete only when the caller is the owner; non-owners SHALL see View Another League and Claim Ownership, with owner actions hidden until `getLeague` resolves.

#### Scenario: Owner vs non-owner
- **WHEN** the sidebar renders for a league
- **THEN** Refresh, Migrate, Transfer Ownership, and Delete appear only when `is_owner`, while non-owners see View Another League and Claim Ownership

#### Scenario: Owner state loading and failure
- **WHEN** `getLeague` has not resolved, or fails, or the app is in demo/no-league
- **THEN** owner-only actions stay hidden until it resolves (no flash), a failed request resolves to non-owner, and demo/no-league bypasses gating

### Requirement: Verify ESPN membership for non-members
An ESPN league returning `403` SHALL show a "Verify your ESPN league membership" prompt and open the shared Join League dialog, revealing the dashboard on a successful verify and an inline error on rejection.

#### Scenario: Membership verification
- **WHEN** `getLeague` returns `403` for an ESPN league
- **THEN** the `MembershipGuard` shows the verification backdrop and opens the Join League dialog; the caller supplies cookies (extension autofill or manual), and on `verify-membership` success the guard clears the API cache and re-renders the page in place

#### Scenario: Verify rejected
- **WHEN** ESPN rejects the submitted cookies
- **THEN** the dialog shows "We couldn't confirm you're in this ESPN league."

#### Scenario: Fail-open guard
- **WHEN** `getLeague` fails for a non-`403` reason
- **THEN** the guard renders the page (backend remains source of truth); only a `403` shows the verification backdrop

### Requirement: Transfer and claim ownership
An owner SHALL be able to mint a one-time transfer token, and a recipient SHALL be able to redeem it, reloading league state on success.

#### Scenario: Mint token
- **WHEN** the owner opens the Transfer Ownership dialog
- **THEN** a one-time token is minted and copyable, and closing the dialog clears it

#### Scenario: Claim ownership
- **WHEN** a recipient redeems a valid token via the Claim Ownership dialog
- **THEN** the API cache is cleared and league state reloads so the new owner immediately sees owner actions

### Requirement: Inline 403 messaging
A `403` on a mutating endpoint SHALL render a clear owner-only message inline (via `toResult` + `<ErrorAlert>`), with no global error banner.

#### Scenario: Owner-only 403
- **WHEN** a mutating call returns `403`
- **THEN** an inline owner-only/membership message is shown rather than a generic error
