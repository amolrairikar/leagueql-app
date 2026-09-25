## ADDED Requirements

### Requirement: Export league data action
The sidebar SHALL show an "Export League Data" action to every league member (not gated on
`is_owner`) for a connected, non-demo league. Activating it SHALL open the export dialog
(frontend/export-league-data).

#### Scenario: Export action visible to members
- **WHEN** the sidebar renders for a connected league (owner or non-owner member, any platform)
- **THEN** an "Export League Data" action is shown

#### Scenario: Export action opens the dialog
- **WHEN** the "Export League Data" action is activated
- **THEN** the export dialog opens
