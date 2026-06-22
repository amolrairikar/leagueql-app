"""Phrase bank for the deterministic weekly recap composer (BE-022).

Data only — no logic. ``generate.py`` selects one fragment from the relevant list
with a per-matchup seeded RNG and fills its ``str.format`` placeholders from the
deterministic highlights (``highlights.py``). Each group documents the exact
placeholder names it uses so the composer can supply them and a unit test can
guard against typos / unfillable templates.

Voice: a lively "commissioner's column" with light, good-natured trash talk.
Keep every fragment a complete, standalone sentence ending in punctuation so the
composer can join them with a single space regardless of which variants it draws.
"""

# Headlines — placeholder-free, punchy. The composer picks the set by week shape
# (championship > playoff > blowout > general).
HEADLINES = {
    "general": [
        "Around the League: Winners, Losers, and Everyone In Between",
        "The Weekly Reckoning",
        "Box Scores Don't Lie",
        "Another Week, Another Set of Receipts",
        "Wins, Wails, and Wasted Benches",
        "The Commissioner's Column",
        "Touchdowns and Turmoil",
        "This Week in Fantasy Justice",
    ],
    "blowout": [
        "Blowout City",
        "Mercy Rules and Margin Calls",
        "It Got Ugly Out There",
        "Beatdowns, Bloodbaths, and a Few Close Calls",
    ],
    "playoff": [
        "Playoff Football Is Here",
        "Win or Go Home",
        "The Bracket Tightens",
        "Postseason Pressure Cooker",
    ],
    "championship": [
        "We Have a Champion",
        "Crowning Glory",
        "The Title Is Settled",
        "For All the Marbles",
    ],
}

# Regular-season result sentence, keyed by margin bucket.
# Placeholders: {winner} {loser} {winner_score} {loser_score} {margin}
RESULT = {
    # Placeholders: {team_a} {team_b} {score}
    "tie": [
        "{team_a} and {team_b} slugged it out to a {score}-{score} draw that "
        "satisfied absolutely no one.",
        "Deadlock: {team_a} and {team_b} both finished on {score} and split the "
        "difference.",
        "{team_a} and {team_b} played to a {score}-{score} tie, kissing your "
        "sister, fantasy edition.",
        "Nobody blinked as {team_a} and {team_b} knotted it up at {score}.",
        "A rare stalemate, as {team_a} and {team_b} matched each other point for "
        "point at {score}.",
        "{team_a} and {team_b} couldn't be separated, settling for a {score}-"
        "{score} tie.",
    ],
    "nailbiter": [
        "{winner} survived a heart-stopper over {loser}, {winner_score}-"
        "{loser_score}, by a razor-thin {margin} points.",
        "{winner} edged {loser} {winner_score}-{loser_score} in a game that came "
        "down to the final whistle.",
        "By the slimmest of margins, just {margin} points, {winner} squeaked past "
        "{loser} {winner_score}-{loser_score}.",
        "{winner} clipped {loser} {winner_score}-{loser_score}, holding on by all "
        "of {margin} points.",
        "It doesn't get tighter than this: {winner} nipped {loser} {winner_score}-"
        "{loser_score}.",
        "{winner} won the coin-flip of a matchup, slipping by {loser} "
        "{winner_score}-{loser_score}.",
        "A {margin}-point thriller went {winner}'s way over {loser}, "
        "{winner_score}-{loser_score}.",
    ],
    "close": [
        "{winner} held off {loser} {winner_score}-{loser_score}, never quite "
        "letting the lead slip.",
        "{winner} took care of business against {loser}, {winner_score}-{loser_score}.",
        "{winner} had just enough to beat {loser} {winner_score}-{loser_score}, a "
        "{margin}-point cushion.",
        "{winner} kept {loser} at arm's length all week, winning {winner_score}-"
        "{loser_score}.",
        "{winner} grinded out a {margin}-point win over {loser}, {winner_score}-"
        "{loser_score}.",
        "{winner} answered every push from {loser} and won {winner_score}-"
        "{loser_score}.",
    ],
    "solid": [
        "{winner} handled {loser} with room to spare, {winner_score}-{loser_score}.",
        "{winner} put {loser} away {winner_score}-{loser_score} in a {margin}-"
        "point statement.",
        "{winner} controlled this one from the jump, downing {loser} "
        "{winner_score}-{loser_score}.",
        "No drama here, as {winner} beat {loser} {winner_score}-{loser_score}.",
        "{winner} built a lead and cruised past {loser}, {winner_score}-{loser_score}.",
        "{winner} had the better roster and it showed, topping {loser} "
        "{winner_score}-{loser_score}.",
    ],
    "comfortable": [
        "{winner} rolled {loser} {winner_score}-{loser_score}, a {margin}-point "
        "thumping.",
        "{winner} never broke a sweat, dispatching {loser} {winner_score}-"
        "{loser_score}.",
        "{winner} flexed on {loser}, {winner_score}-{loser_score}.",
        "{winner} ran away from {loser} for a tidy {margin}-point win, "
        "{winner_score}-{loser_score}.",
        "{winner} made {loser} look overmatched, winning {winner_score}-{loser_score}.",
        "{winner} cruised to a {winner_score}-{loser_score} win over {loser} and "
        "barely looked back.",
    ],
    "blowout": [
        "{winner} absolutely demolished {loser} {winner_score}-{loser_score} in a "
        "{margin}-point bloodbath.",
        "Call the cops, because {winner} mugged {loser} {winner_score}-{loser_score}.",
        "{winner} buried {loser} {winner_score}-{loser_score}, a {margin}-point "
        "massacre.",
        "{loser} never stood a chance as {winner} cruised {winner_score}-"
        "{loser_score}.",
        "{winner} turned this into a laugher, throttling {loser} {winner_score}-"
        "{loser_score}.",
        "Somebody check on {loser} after {winner} dropped {winner_score}-"
        "{loser_score} on them, a {margin}-point beatdown.",
        "{winner} left no doubt, steamrolling {loser} {winner_score}-{loser_score}.",
    ],
}

# Playoff result overrides. Placeholders: {winner} {loser} {winner_score}
# {loser_score} {round} (except *_generic, which omits {round}).
PLAYOFF_RESULT = {
    "championship": [
        "{winner} are your league champions, knocking off {loser} {winner_score}-"
        "{loser_score} in the {round} to hoist the trophy.",
        "It's over, and {winner} are kings of the league, a {winner_score}-"
        "{loser_score} win over {loser} in the {round} sealing it.",
        "{winner} climbed the mountain, beating {loser} {winner_score}-"
        "{loser_score} in the {round} to claim the title.",
        "Champagne for {winner}, who took the {round} {winner_score}-{loser_score} "
        "over {loser} and the crown that comes with it.",
        "{winner} finished the job in the {round}, toppling {loser} {winner_score}-"
        "{loser_score} to become champions.",
    ],
    "advance": [
        "{winner} punched their ticket out of the {round}, sending {loser} home "
        "{winner_score}-{loser_score}.",
        "{winner} won when it mattered, taking the {round} over {loser} "
        "{winner_score}-{loser_score} to advance.",
        "Survive and advance: {winner} handled {loser} {winner_score}-"
        "{loser_score} in the {round}.",
        "{winner} booked their spot in the next round, beating {loser} "
        "{winner_score}-{loser_score} in the {round}.",
        "{winner} kept their title hopes alive, dispatching {loser} {winner_score}-"
        "{loser_score} in the {round}.",
    ],
    "advance_generic": [
        "{winner} won their playoff matchup over {loser} {winner_score}-"
        "{loser_score} and live to play another week.",
        "{winner} advanced past {loser} {winner_score}-{loser_score} in the "
        "postseason.",
        "{winner} took care of {loser} {winner_score}-{loser_score} with the "
        "season on the line.",
        "{winner} kept dancing in the playoffs, beating {loser} {winner_score}-"
        "{loser_score}.",
    ],
}

# Consolation / losers-bracket result sentence — these games are NOT for the title,
# so the framing leans on pride / bragging rights and never implies a championship
# run. Placeholders: {winner} {loser} {winner_score} {loser_score} {margin}
CONSOLATION_RESULT = [
    "With nothing but pride on the line, {winner} beat {loser} {winner_score}-"
    "{loser_score} in the consolation bracket.",
    "It won't make the trophy case, but {winner} topped {loser} {winner_score}-"
    "{loser_score}.",
    "Down in the consolation games, {winner} handled {loser} {winner_score}-"
    "{loser_score}.",
    "Playing for bragging rights and little else, {winner} got past {loser} "
    "{winner_score}-{loser_score}.",
    "{winner} salvaged some dignity with a {winner_score}-{loser_score} win over "
    "{loser}.",
    "No title on the line, just pride: {winner} beat {loser} {winner_score}-"
    "{loser_score}.",
    "{winner} closed out the season with a {margin}-point consolation win over "
    "{loser}, {winner_score}-{loser_score}.",
    "Out of the title hunt, {winner} still took care of {loser} {winner_score}-"
    "{loser_score}.",
]

# Standout-performance sentence. Placeholders: {player} {points} {team}
# ({points} is a bare number; templates supply the "points" unit.)
STANDOUT = [
    "{player} carried {team}, posting a team-high {points} points.",
    "{team} rode {player}'s {points} points to the finish.",
    "{player} went off for {points} points to pace {team}.",
    "{player} was the engine for {team}, racking up {points} points.",
    "{points} points from {player} did the heavy lifting for {team}.",
    "{team} can thank {player}, whose {points} points led the way.",
]

# Standout with position. Placeholders: {player} {points} {team} {position}
STANDOUT_WITH_POS = [
    "{player} ({position}) led {team} with {points} points.",
    "{team} leaned on {player} at {position}, who delivered {points} points.",
    "{player} smashed for {points} points at {position} to lead the way for {team}.",
    "Best on {team} was {player}, dropping {points} points from the {position} slot.",
    "{player} was elite at {position} for {team}, going for {points} points.",
]

# Optional flavor (third) sentence. Each group documents its placeholders.
FLAVOR = {
    # {team} {player} {points}
    "bust": [
        "{team} won't want to rewatch {player}, who mustered a meager {points} points.",
        "Somebody bench {player}, because {points} points won't cut it for {team}.",
        "{player} was a no-show for {team}, limping to {points} points.",
        "{team}'s {player} laid an egg with just {points} points.",
        "The {player} experience cost {team} dearly: a measly {points} points.",
    ],
    # {team} {bench}
    "bench": [
        "{team} left a painful {bench} points on the bench; lineups matter, folks.",
        "Coaching cost {team} this week, with {bench} points rotting on the pine.",
        "{team} could've used the {bench} points they stapled to the bench.",
        "File {team}'s {bench} bench points under what could have been.",
        "{team} forgot to start their best guys, stranding {bench} points on the "
        "bench.",
    ],
    # {loser} {loser_mgr} {winner}
    "trash": [
        "Better luck next week, {loser_mgr}.",
        "{loser_mgr} will want to delete the box score and move on.",
        "{loser} have some explaining to do at the next league meeting.",
        "Tough scene for {loser_mgr}, who ran straight into a buzzsaw in {winner}.",
        "{loser_mgr} can take solace in moral victories, of which there were none "
        "here.",
    ],
    # {loser} {loser_mgr}
    "eliminated": [
        "{loser_mgr}'s season ends right here.",
        "Pack it up, because {loser} are eliminated.",
        "The dream is dead for {loser_mgr}; there's always next year.",
        "{loser} can clean out their lockers after this one.",
        "And just like that, {loser_mgr} is on the offseason clock.",
    ],
}

# Week-extreme tag — placeholder-free, appended to the matching matchup.
WEEK_EXTREME = {
    "biggest": [
        "It was the most lopsided result on the slate.",
        "No beating was more thorough across the league this week.",
        "Nobody got run off the field harder this week.",
    ],
    "closest": [
        "No game on the board was closer.",
        "Heart rates didn't get higher anywhere else this week.",
        "It was the photo finish of the week.",
    ],
}
