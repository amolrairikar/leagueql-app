## Why

The FAQ ("FAQ and Troubleshooting") is buried at the bottom of the `/docs` page, where
prospective users rarely look before deciding to connect a league. Surfacing these
questions on the public landing page — as a scannable, collapsible accordion — answers
common onboarding objections at the point of decision and gives the page a familiar,
low-friction "Before you connect" section.

## What Changes

- Add an **FAQ accordion** section to the landing page (`/`), titled "Before you connect",
  placed between the "How it works" steps and the final CTA band. Every question renders
  collapsed by default (only the question and a `+` indicator visible); clicking a question
  expands its answer, and the `+` rotates to a `×` to signal the open state.
- Move the seven FAQ items (verbatim content) out of the docs page into the landing-page
  feature. Answers that reference the docs' own ownership section link out to `/docs` instead.
- **Remove** the FAQ section and its table-of-contents entry from the `/docs` page.
- Add a reusable `Accordion` UI component wrapping the already-installed `radix-ui` accordion
  primitive, following the repo's existing `components/ui/*` wrapper convention.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `frontend/landing-page`: the "Render the marketing sections" requirement gains an FAQ
  accordion section, plus a new requirement for the collapse/expand behavior (collapsed by
  default, click to expand, indicator reflects open state).

<!-- Not modified: frontend/instructions-docs. The FAQ was never a documented requirement in
     that spec, so removing the FAQ section from the docs page introduces no spec-level
     behavior change and needs no delta. -->

## Impact

- Frontend: `frontend/src/features/landing_page/landing-page.tsx` (new section),
  `frontend/src/features/landing_page/faq.tsx` (new — FAQ content + component),
  `frontend/src/components/ui/accordion.tsx` (new — reusable component),
  `frontend/src/features/instructions/instructions-page.tsx` (FAQ + TOC entry removed).
- Tests: `frontend/src/features/landing_page/__tests__/*` (accordion render + interaction).
- Dependencies: none added — `radix-ui` (accordion primitive) is already installed.
