# Tasks

## 1. Footer

- [x] 1.1 Add the official Yahoo Fantasy logo as `frontend/src/assets/yahoo-fantasy-logo.svg` (viewBox trimmed to its clip rect only)
- [x] 1.2 Add `YahooAttributionFooter` in `frontend/src/features/sidebar/yahoo-attribution-footer.tsx`, gated to Yahoo leagues outside demo mode, with the logo, the exact attribution text, and a new-tab link to Yahoo Fantasy
- [x] 1.3 Render it as the last child of `SidebarInset` in `AppLayout` (`frontend/src/app/app.tsx`)

## 2. Tests and checks

- [x] 2.1 Add the jest-cucumber pair `yahoo-attribution-footer.feature` + `.steps.test.tsx` (Yahoo shows it; ESPN, Sleeper, and demo don't); verify with `npx vitest run`
- [x] 2.2 Run `npm run format:fix`, `npm run lint`, `npm run build:ci`, and `openspec validate --all`
