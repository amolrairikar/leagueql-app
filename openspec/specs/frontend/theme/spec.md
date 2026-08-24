# theme Specification

## Purpose
Provide app-wide light/dark theme support: a theme provider persists the user's preference, a header toggle switches modes, and the active theme applies across the app including third-party UI (Clerk) and charts.

## Requirements

### Requirement: Theme toggle
The app SHALL provide a header control that switches the active theme between light and dark mode.

#### Scenario: User switches to dark mode
- **WHEN** the user activates the header theme toggle while in light mode
- **THEN** the app switches to dark mode and the new theme is reflected across the UI

#### Scenario: User switches back to light mode
- **WHEN** the user activates the header theme toggle while in dark mode
- **THEN** the app switches to light mode

### Requirement: Theme persistence
The app SHALL persist the user's selected theme so it survives reloads and new sessions.

#### Scenario: Theme survives a reload
- **WHEN** the user selects a theme and then reloads the app
- **THEN** the previously selected theme is still active after the reload

### Requirement: Default to system preference
The app SHALL follow the operating system's color-scheme preference as the initial theme when the user has not yet made an explicit selection.

#### Scenario: No stored preference
- **WHEN** the app loads and no theme has been explicitly selected
- **THEN** the initial theme matches the OS color-scheme preference

### Requirement: No flash of incorrect theme
The app SHALL apply the resolved theme before first paint so there is no visible flash of the wrong theme on initial load.

#### Scenario: Dark-theme user loads the app
- **WHEN** a user whose resolved theme is dark opens the app
- **THEN** the app renders in dark mode from the first paint with no light-mode flash

### Requirement: App-wide theme application
The app SHALL apply the active theme across all surfaces, including third-party components such as Clerk authentication UI and charts.

#### Scenario: Third-party UI respects the theme
- **WHEN** the active theme is dark
- **THEN** Clerk UI and charts render using their dark-theme styling
