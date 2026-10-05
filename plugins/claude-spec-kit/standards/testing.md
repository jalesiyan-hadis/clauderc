# claude-spec-kit test rules

Part of the base coding standard: `_config.py` reads these rules together with
`base.md`, so a repo `disable`s or `enforce`s them by id like any other base
rule. They apply to **test code only**; `standards-reviewer` checks them on
test hunks and never on production code.

Each rule is a `### <id> — <Name>` heading followed by its description. Ids
must stay unique across `base.md` and this file, and stable: repos refer to
them.

### assert-through-seam — Assert Through the Seam
A test asserts against internal signatures behind the seam instead of the
observable outcome at it: call counts, call order, private state, or a side
channel (e.g. querying the database) to verify what the seam itself can
return.

### no-recomputed-expected — No Recomputed Expected Value
The expected value is derived the way the code derives it instead of coming
from the spec or a worked literal, so the test repeats the implementation and
passes by construction. Exception: Refactor characterisation tests, which
intentionally lock in current output.

### mock-boundaries-only — Mock Boundaries Only
A test mocks something the repo owns (its own modules, internal collaborators,
or the thing under test) instead of only the boundaries it doesn't own:
external APIs, the clock, randomness, the network. A real stand-in (temp dir,
in-memory DB) is preferred over a mock where one exists.

### one-behaviour-per-test — One Behaviour per Test
A test checks more than one behaviour, or its name says how the code works
rather than what behaviour it checks.
