# espn-cookie-autofill Specification

## Purpose
Provide a Chrome extension that reads the user's ESPN `espn_s2` and `SWID` cookies and makes them available to the LeagueQL connect/migrate forms, so users with private ESPN leagues do not have to copy cookie values by hand. The extension only reads ESPN cookies and hands them to the LeagueQL app for onboarding; it never stores or transmits them elsewhere.

## Requirements

### Requirement: Read ESPN cookies for onboarding
The extension SHALL read the user's `espn_s2` and `SWID` ESPN cookies and provide them to the LeagueQL connect/migrate form.

#### Scenario: Logged-in ESPN user with the extension installed
- **WHEN** a user logged into ESPN with the extension installed opens the LeagueQL connect or migrate form
- **THEN** the form receives the `espn_s2` and `SWID` values from the extension without manual entry

### Requirement: Manual-entry fallback
The connect/migrate forms SHALL support manual cookie entry when the extension is not installed.

#### Scenario: Extension absent
- **WHEN** the user opens the connect or migrate form without the extension installed
- **THEN** the form still allows the user to enter `espn_s2` and `SWID` manually

### Requirement: Guidance when not logged into ESPN
The extension SHALL communicate that the user must log into ESPN first when the ESPN cookies are absent.

#### Scenario: User not logged into ESPN
- **WHEN** the user requests cookie auto-fill but is not logged into ESPN (cookies absent)
- **THEN** the UI explains that the user must log into ESPN before the cookies can be read

### Requirement: ESPN-scoped permissions
The extension SHALL request cookie/host permissions scoped to ESPN domains only.

#### Scenario: Extension permission scope
- **WHEN** the extension declares its permissions
- **THEN** the requested cookie and host access is limited to ESPN domains

### Requirement: Cookies are never persisted
The extension and app SHALL NOT store or log ESPN cookie values, and SHALL clear them after onboarding.

#### Scenario: Cookies cleared after use
- **WHEN** cookie values have been passed to LeagueQL and onboarding completes
- **THEN** the values are cleared and appear in no persisted store or log

### Requirement: Validated page–extension messaging
The page↔extension message channel SHALL validate the origin and shape of messages it accepts.

#### Scenario: Message from an untrusted origin
- **WHEN** a message arrives on the page↔extension channel from an origin or shape the extension does not trust
- **THEN** the message is rejected and no cookie data is exchanged

### Requirement: Behavior matches published privacy disclosure
The extension's behavior SHALL match the published `/extension-privacy` disclosure and Chrome Web Store policy (public privacy page, minimal permissions).

#### Scenario: Disclosure consistency
- **WHEN** the extension reads and forwards ESPN cookies
- **THEN** that behavior is consistent with what the `/extension-privacy` page discloses
