# Spec Delta

## ADDED Requirements

### Requirement: Equal-width comparison columns with horizontal scroll

The comparison grid SHALL give both managers' stat columns (header name, values, and bars) equal
width regardless of username length, and SHALL scroll horizontally within its own container
rather than compressing either manager's column when the equal-width columns do not fit the
viewport.

#### Scenario: Long username on a narrow viewport

- **WHEN** one selected manager's username is much longer than the other's and the viewport is
  too narrow to fit both columns at that width
- **THEN** both manager columns render at the same width, and the comparison grid scrolls
  horizontally within its container without widening the rest of the page

#### Scenario: Columns fit the viewport

- **WHEN** both manager columns fit within the available width
- **THEN** the columns split the available width equally and no horizontal scroll appears
