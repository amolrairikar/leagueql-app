# FE-020: Theme (Light/Dark Mode)

## Description
App-wide light/dark theme support. A theme provider persists the user's preference and a
toggle in the header switches modes. The theme is applied across the app, including
third-party UI (Clerk).

## Scope
- Provider: `src/components/theme-provider.tsx`; hook `src/hooks/use-theme.ts`.
- Toggle: `src/components/mode-toggle.tsx` (in the header).
- Consumed by Clerk theming ([FE-019](FE-019-authentication.md)).

## Edge Cases
- **Persistence:** the selected theme persists across reloads/sessions.
- **System preference:** initial theme may follow the OS preference when unset.
- **Flash of incorrect theme:** avoid a visible flash on initial load.
- **Third-party components:** Clerk and charts respect the active theme.

## Acceptance Criteria
- [ ] The header toggle switches between light and dark mode.
- [ ] The selected theme persists across reloads.
- [ ] The theme applies app-wide, including Clerk UI.
- [ ] No jarring flash of the wrong theme on load.

## Sources
`src/components/theme-provider.tsx`, `src/components/mode-toggle.tsx`, `src/hooks/use-theme.ts`.
