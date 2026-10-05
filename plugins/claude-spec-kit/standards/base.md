# claude-spec-kit base coding standard

The default rules `standards-reviewer` applies in every repository. A repo
changes them through the frontmatter of its own standards file (`disable`,
`enforce`, `extends: none`), referring to each rule by the id in its heading.
Base rules are **fix or defer** unless the repo enforces them.

Each rule is a `### <id> — <Name>` heading followed by its description. Keep ids
stable: repos refer to them.

### mysterious-name — Mysterious Name
A name doesn't say what the thing does or means, or contradicts the domain
terms in the spec or the repo's glossary.

### duplicated-code — Duplicated Code
The same logic appears in more than one place, so a change to it must be made
twice.

### feature-envy — Feature Envy
A function works mostly with another module's data instead of its own; it
belongs next to that data.

### data-clumps — Data Clumps
The same group of values travels together through several signatures. Only
worth a type when the group already appears in at least two places.

### primitive-obsession — Primitive Obsession
A domain concept with its own rules is passed around as a bare string or
number, so its validation is repeated at each use.

### repeated-switches — Repeated Switches
The same branching on the same value appears in several places, so a new case
means editing all of them.

### shotgun-surgery — Shotgun Surgery
One change to one concept requires small edits across many files.

### divergent-change — Divergent Change
One module changes for several unrelated reasons.

### speculative-generality — Speculative Generality
Parameters, hooks, options, or abstractions that no current caller or scenario
needs. Includes any port, interface, protocol, or dependency-injection
parameter with a single implementation (production code plus a test stand-in
counts as two).

### message-chains — Message Chains
A caller walks a chain of objects (`a.b().c().d()`), so it depends on the
whole structure in between.

### middle-man — Middle Man
A module or function mostly forwards calls to another one without adding
behavior: a pass-through that fails the deletion test.

### refused-bequest — Refused Bequest
A subclass or implementation ignores or overrides most of what it inherits.
