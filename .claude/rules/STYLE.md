# How llamatron's code is written

The rules for the code, in any language it is written in: the Rust program in `src/`, and the small tools in
`internal_tools/` and `python/`. `.claude/rules/RUST.md` holds the Rust's own rules besides these, clippy and rustfmt among
them, and `developer_docs/ARCHITECTURE.md` explains the design they serve. The code MUST be easy for people to maintain without AI:
plain code, comments that explain why, tests that read clearly.

## Readability

- **Bounds for stepping**: moving through a list goes through the one stepping helper, which handles an empty list.
- **Readable over clever.** Explicit, simple, flat; errors never pass silently. Code a reader must stop to work out is allowed
  only for measured speed, with a comment saying why.
- **Timing comes first where it matters.** The synthesis and every timing-sensitive path (the audio callback, the sender, the
  player's tick, the render's per-note loop) MAY break any rule here where the rule would cost time (the user's standing
  allowance), with a comment saying why; their names stay plain.
- **No bare constants.** A number or a text whose purpose is not plain from where it stands is given a name first, a `let` or a
  named constant saying what it is for, such as `let shown_rows = 7;` or `const PREVIEW_CHANNEL: i64 = 15;`. Zero, one, and the
  empty text in their plain sense need no name.
- **A rule about shape is met by naming the thing a person would name**, never by cutting code into pieces or a clever line.
- **Organized at every scale.** A file holds one subject in a sensible order; a type is a nameable thing with a visible
  contract; each line says plainly what it does. Three or four near-repeats get a helper whose name says what the shape means.
  Keep making code simpler and more elegant, not only correct.
- **A function reads like a book**:
  1. One thing a line: a chain is named first, `let band = choices.band();`, then used.
  2. One level per function, top to bottom.
  3. Values travelling together are a missing type, proposed to the user.
  4. Statements over expressions where a statement reads more plainly.
  5. Names read as English, without repeating the type's name.
  6. A helper MUST mean something: its name says a thing a reader would name and its body reads plainly.
- **Short and shallow.** Functions short enough to read at a glance, nesting shallow, few parameters; a long function only where
  a hot loop is faster so, with a comment saying why. A file holds one subject and is split only into things a reader would
  name.
- **Steps that must go together are one function.** Where two or more steps always run together and leaving one out would be a
  bug, such as storing a scene's new name and following it in the crumbs, they live in one function named for the whole act,
  and every caller uses it.
- **Comments give the reason**, for a maintainer: never whose choice it was or when. Comments do not excuse unclear code.

## Objects

- **Behaviour lives with the data it is about**: everything about a pattern is on the pattern. The one exception is
  musicianship: what a musician does to a pattern, such as inverting, developing or voice leading it, lives apart from the
  pattern's storage and works through its methods.
- **A type is a thing a reader would name**: a player, a cursor, a run of passes. Before adding a function, name the thing it
  belongs to.
- **Changes go through one door.** Data is changed only through the methods that check it, with the setting's one check from
  the schema; musical values (a note, a chord, a scale, a time signature) never change once made; pages change the set only
  through the document.
- **Names say what a function does.** `get_x` and `set_x` hand back or store what is held; anything else works something out
  and is named for it. Yes or no: `is_x`, `has_x`, `can_x`, or a verb (`loops()`).
- **Type names** are as a person would name them and unique across the program.
- **One word for one thing:** `move_cursor` an arrow moves a cursor; `shift` carries what the cursor is on, `drop` puts it down;
  `advance` time moves on; `remove_step` and `insert_step`; `step_count` a count, `steps` the steps; `remarks` a settings
  page's lines under its settings (`notes` is only music, or the set's Notes); `toggle`; a refusal is text or nothing.
- **Asking a value its kind is a design smell** where the kinds could share a trait and be asked to act.

## Text and keys

- **Every shown or raised text is a template constant** in `src/strings/src/texts/`, filled by name: `ERR_` for anything saying
  what went wrong, dialog titles too, in `errors.rs`; `MSG_`
  for all else, in the module of how it is used (labels, legends, messages, marks, names, the command line). Comments and
  documentation stay where they are.
- **Every name used as a value is a named constant**: file keys, settings, kinds, modes, note names, chord symbols, key names,
  exporter tags, and numbers with a meaning (`MIN_PROBABILITY`). Unused constants are removed. A constant is defined once, in
  the model's schema or the strings crate, and imported, never redeclared as a local constant; no list of sections or
  settings is kept by hand where the schema holds it. Different meanings are different constants even where their values
  agree: a dozen minimums of 0 are a dozen constants, each named for what it bounds.
- **No YAML in a string**, anywhere in the source, tests included: data is built as data structures and serialized where
  it is written. A set a test starts from is a data file beside the tests, read by name.
- **A file is written by a serializer**: a format llamatron writes, YAML, JSON, MIDI or any other, is built as data and
  written by the library or the module that serializes it, never by formatting its text by hand.
- **Look before saying it is missing**: before writing code that reads or writes a format, or that does what a library
  might, the workspace's own modules and the crates its manifests already name are checked first, and a claim that
  nothing fits says what was checked.
- **Arrays stay arrays.** List-like data is stored as real values (sixteen booleans, never `'x...x...'`), in files and in
  memory. Display strings are made where shown.
- **Keys.** Every binding is in one table, a class for each page, dialog and component, each binding its keys, the name the
  legend shows and what it does; a page binds only its class's bindings. A key is written only as a `Key::` constant, and a
  test holds that no class binds a key twice or shadows an everywhere key. UX rules are in `.claude/rules/UX.md`.

## Performance

- **Lengths and times are exact**: rationals, never decimals, except inside the render's hot loop, where a length is a pair
  handled in one place.
- **Fewer operations**: build each note once, keep steps as per-row arrays, work out what can be without playing, skip passes
  that do nothing. Every such shortcut MUST have tests of both paths, and is proved with every export byte for byte the same.
- **Work out an answer once** and keep it until what it came from changes; a cache nothing can see going stale MUST NOT be
  added.
- **Every generator is efficient on its own**; what its settings alone decide is worked out once.
- **Binding is late**: a degree stays a degree until the clip knows its scale; a groove is chosen at render. Never work out again
  what has not changed.

## The set file

- Every setting has a default, so older files load and new settings need no migration.
- A key rename or structural change MUST come with a migration (`src/model/src/file/migrations.rs`), never changed once
  released. Every shipped file is migrated in the same change, exports unchanged.
- A removed setting gets no migration: the reader passes over unknown names, and the next save drops them.
- A rename MUST update every reference by name.

## Files, scripts, documents

- The GPLv3 header (`.claude/COMPLIANCE.md`) on every file of code and every script.
- No new folder whose name starts with a dot is committed, since one is easily missed in what a commit adds; `.claude/` is the
  one there is (the user's rule). Caches and other working files go in git-ignored dot folders, such as `.cache/`.
- Scripts are plain `sh`, `#!/bin/sh`, named with underscores. Setup instructions MUST NOT need `make`. A script that installs
  something offers to install what it needs first and installs nothing without a yes.
- Every change carries its documentation: a changed feature, setting, default or key updates its page in `docs/` in the same
  change, in the UI's names; a changed rule updates this file; a moved module moves every path naming it. How documents are
  written and generated: `.claude/rules/DOCS.md`.
