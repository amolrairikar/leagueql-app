## Context

See proposal.md — Why. The FAQ currently lives in `instructions-page.tsx` as a `FAQ_ITEMS`
array rendered as always-expanded static text, with a matching `faq-and-troubleshooting`
entry in the docs table of contents. There is no accordion/disclosure component in the repo
today, but the `radix-ui` package (already a dependency) ships an accordion primitive, and the
repo has an established shadcn-style wrapper convention under `frontend/src/components/ui/`
(e.g. `tooltip.tsx`).

## Goals / Non-Goals

**Goals:**
- A reusable `Accordion` UI component the rest of the app can use later.
- FAQ content lives in one place, owned by the landing-page feature, rendered as an accordion.
- Docs page cleanly loses its FAQ section and TOC entry without breaking its other content.

**Non-Goals:**
- Redesigning any other landing-page section or the docs page structure.
- Multi-open behavior — one question open at a time is sufficient and matches the mockup.

## Decisions

- **Reusable `components/ui/accordion.tsx` over an inline landing-page accordion.** Mirrors the
  existing `components/ui/*` radix wrappers, keeps the landing page declarative, and is reusable.
  Alternative (inline `<details>`/hand-rolled state) rejected: loses radix's accessibility and
  the repo's consistent styling/animation conventions.
- **`type="single" collapsible` root.** All items start closed; opening one closes the others.
  Matches the approved mockup and avoids a wall of open answers.
- **`+` → `×` via `data-[state=open]:rotate-45` on a lucide `Plus`.** A single glyph rotated 45°
  reads as `×` when open, keeping the always-visible `+` affordance the user asked for with no
  icon swap.
- **FAQ content moves to `features/landing_page/faq.tsx` (a `.tsx`, not `constants.ts`).** The
  answers contain JSX (`<Kbd>`, links), which `constants.ts` (a `.ts` data file) should not hold.
- **Q6 cross-link rewrite.** Q6's answer currently uses the docs page's in-page `SectionLink` to
  scroll to the ownership section. On the landing page there is no such section, so it becomes a
  react-router `Link` to `/docs`, preserving the "League Ownership" wording.

## Risks / Trade-offs

- **[Existing docs render test asserts "Refresh League"]** → That string still appears outside the
  FAQ on the docs page (the Managing Your League section), so removing the FAQ keeps the test
  green; verified before implementation.
- **[Accordion animation vs. `prefers-reduced-motion`]** → Use the repo's existing radix
  animation classes and ensure content is reachable without motion; the component still expands
  when motion is reduced.
