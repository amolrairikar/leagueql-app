# Tasks

## 1. Privacy Policy (`/privacy`)
- [x] 1.1 Correct the Yahoo token removal statement (shared connection, removed on last Yahoo league delete or Yahoo-side revoke).
- [x] 1.2 Clarify ESPN cookie removal wording (removed once no ESPN league has auto-refresh on).
- [x] 1.3 Add account-linked data (membership/invites, transfer tokens, My Team claim) and Google sign-in.
- [x] 1.4 Add a usage & diagnostics disclosure and list Better Stack under Third-Party Services.
- [x] 1.5 Rewrite "Your Rights" to describe owner self-serve Delete League and email-based removal.
- [x] 1.6 Bump "Last updated".

## 2. Extension Privacy Policy (`/extension-privacy`)
- [x] 2.1 Use the "Autofill cookies from ESPN" label.
- [x] 2.2 Bump "Last updated".

## 3. User Guide (`/docs`)
- [x] 3.1 Rename the ESPN "Fields" heading to "Form Fields".
- [x] 3.2 Describe shared ESPN cookie removal in the connect callout and the auto-refresh section.
- [x] 3.3 Document the manual refresh limits (once per week, in season, only when newer data exists).

## 4. Landing page
- [x] 4.1 FAQ: private-league framing, cookie removal, autofill label, refresh limits.
- [x] 4.2 `index.html`: include Yahoo in the meta description and JSON-LD description.

## 5. Tests
- [x] 5.1 Update the FAQ expand scenario to the corrected answer.
- [x] 5.2 Add scenarios for the refresh limits (docs), the Better Stack disclosure and deletion rights (privacy), and the extension autofill label.

## 6. Verify
- [x] 6.1 `openspec validate --all` passes.
- [x] 6.2 Frontend format + lint pass, static-pages component tests pass.
