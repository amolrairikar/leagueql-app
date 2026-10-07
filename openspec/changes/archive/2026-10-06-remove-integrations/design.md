# Design

## Context

The feature was self-contained: one backend module (`src/api/integrations.py`), two routes, a submission-limit
helper pair, one frontend feature folder, and one sidebar group. Nothing else imports from it.

## Decisions

- **Delete outright, no redirect.** `/integrations` falls through to the existing not-found handling rather than
  redirecting; the page was young and low-traffic, so a redirect isn't worth keeping.
- **Drop the whole "Community" sidebar group.** Integrations was its only item; an empty group is noise.
- **Leave external state for manual cleanup.** The SSM PAT parameter, the GitHub issues and the labels were created
  by hand, so they are removed by hand. Leftover `INTEGRATION_SUBMISSIONS` items expire via TTL.

## Risks

- Removing the IAM statement before the env var is harmless: the code that reads the token is gone in the same
  deploy.
