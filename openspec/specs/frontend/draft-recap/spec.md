# draft-recap Specification

## Purpose
The `/draft_recap` page renders a draft board for a selected season. Snake drafts show the classic round-by-round grid with the overall pick number per cell; auction drafts show a spend board with the winning bid per pick. Each pick cell is colored by position and shows the player's season points.

## Requirements

### Requirement: Render snake and auction boards
`/draft_recap` SHALL render a snake grid with overall pick numbers for snake leagues and a spend board with winning bids for auction leagues, detecting the draft type from pick data.

#### Scenario: Snake grid
- **WHEN** a snake-draft season is selected
- **THEN** the round-by-round grid renders with overall pick numbers per cell

#### Scenario: Auction spend board
- **WHEN** an auction-draft season is selected
- **THEN** a spend board renders showing the winning `bid_amount` per pick

### Requirement: Place traded picks in the draft-slot column
A pick traded to another manager SHALL render in its draft slot's column (never dropped) and be marked with a "traded to <manager>" badge.

#### Scenario: Traded pick
- **WHEN** a pick was traded so a manager makes more/fewer picks in a round
- **THEN** the pick is placed in its draft slot's column (derived from `overall_pick_number`, team count, and snake/linear direction — not `round_pick_number`) and marked "traded to <manager>"

### Requirement: Style and annotate cells
Each cell SHALL be colored by position and show the player's season points when available, with keeper picks visually indicated.

#### Scenario: Cell styling
- **WHEN** the board renders
- **THEN** each cell is colored by position, shows the player's season points when available, and keeper picks are visually indicated

### Requirement: Adapt to league shape and null data
The board SHALL adapt to the league's team and round counts and tolerate null player data.

#### Scenario: Varying shape and nulls
- **WHEN** the league has a varying number of teams/rounds or missing `player_name`/`total_points`
- **THEN** the grid adapts and renders null player data gracefully (not relying on Sleeper's null `pick_id`)
