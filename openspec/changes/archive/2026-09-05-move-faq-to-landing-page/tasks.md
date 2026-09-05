## 1. Reusable Accordion component

- [x] 1.1 Create `frontend/src/components/ui/accordion.tsx` wrapping the `radix-ui` accordion primitive (mirroring `components/ui/tooltip.tsx`), exporting `Accordion`, `AccordionItem`, `AccordionTrigger`, `AccordionContent`; trigger shows a lucide `Plus` with `data-[state=open]:rotate-45` (+ → ×) and a visible focus state. Verify it type-checks (`npm run build:ci`) and renders both themes.

## 2. FAQ content + component

- [x] 2.1 Create `frontend/src/features/landing_page/faq.tsx` holding the FAQ items (moved verbatim from the docs page, including the `<Kbd>` chips, `mailto:` support link, and the ordered `steps` + italic `note`) and a `<Faq />` that renders them via `Accordion` (`type="single" collapsible`, all collapsed). Rewrite Q6's in-docs ownership `SectionLink` as a react-router `Link` to `/docs`, keeping the "League Ownership" wording.

## 3. Landing page wiring

- [x] 3.1 In `frontend/src/features/landing_page/landing-page.tsx`, add an FAQ `<section>` between "How it works" and "Final CTA" using the existing section-header pattern (eyebrow "FAQ", title "Before you connect", muted subhead) and render `<Faq />`. Verify by loading `/` that the section appears collapsed and each question expands on click.

## 4. Remove FAQ from docs

- [x] 4.1 In `frontend/src/features/instructions/instructions-page.tsx`, remove the `FaqItem` interface, `FAQ_ITEMS`, the `faqItems` const, the FAQ `<section>`, and the `faq-and-troubleshooting` TOC entry; keep `SectionLink` and `Kbd`. Verify by loading `/docs` that the FAQ section and its TOC entry are gone and the rest of the guide renders.

## 5. Tests

- [x] 5.1 Add/extend jest-cucumber coverage under `frontend/src/features/landing_page/__tests__/` (MSW + `renderRoute` pattern) for: FAQ collapsed by default (a question visible, its answer not), and clicking a question reveals its answer. Verify with `npx vitest run src/features/landing_page/__tests__`.
- [x] 5.2 Confirm the existing "The docs page renders" scenario still passes (asserted text remains outside the FAQ); optionally add a scenario asserting a FAQ question is no longer present on `/docs`.

## 6. Quality gates

- [x] 6.1 From `frontend/`, run `npm run format:fix` then `npm run lint` and verify both are clean.
- [x] 6.2 Run `openspec validate --all` and verify it passes.
