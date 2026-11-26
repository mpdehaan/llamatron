# How llamatron is tested

The rules for running and writing tests. The Rust's own leaner rule is in `.claude/rules/RUST.md`; the agreed plan for what
is still to be built is in `.claude/planning/DESIGNS.md`, "The Rust testing strategy".

## Running

```
cargo test --manifest-path src/Cargo.toml --workspace             # every crate's tests, in the quick dev build
.venv/bin/python internal_tools/compare_llamatron.py STEP          # llamatron held to the retired Python's frozen answers
internal_tools/check_before_commit.sh                              # before committing code; check its real exit code
```

- The commit check runs rustfmt, clippy with every warning an error, the tests, the release build, and the comparisons the
  changed crates can affect, side by side. Read its real exit code; never pipe it through `tail`. There is no git hook, and none
  MUST be added.
- `internal_tools/push_all.sh` runs every check and every comparison before any push, whatever changed.
- The comparisons (`internal_tools/compare_llamatron.py`) put every example and test set through each step, load, layout,
  migrate, save, edits, pattern edits, render, timeline, player, MIDI, Live and import, and the key tour's screens at 80x24 and
  160x50, and compare what llamatron makes with what the Python made of the same file before it retired
  (`py_legacy/frozen_test_data/`). A few `llamatron-compare` processes, one per core, answer set after set on their pipes; no set
  starts a program of its own. A set changed since the answers were frozen has none to be held to, and is counted apart.
- The key tour's screens are held to llamatron's own earlier screens, kept and retaken on purpose as the program changes,
  never to the retired Python's (the user's rule). The song wizard alone is held to the Python's frozen screens, until its
  port is done; no other part of the frozen screens is consulted.
- No commit of code, examples or tools goes in without the check passing. Documents and `.claude/` files are committed without
  a run, apart from code mid-change; a document naming paths runs `python/tests/test_doc_paths.py` first.
- Before and after a change that should leave the music alone, every export is compared byte for byte, the version line aside.

## What a change must come with

- Every behaviour has a test, at the layer a person meets it: model rules, what a file refuses, what each page's keys do to the
  set, what the exporters write. Complex scenarios, not one happy path.
- A condition-specific shortcut MUST have tests of both paths.
- A bug fixed comes with the test that would have caught it.
- A built-in synth's control, engine or effect is tested as a person plays it: the sound the tracker writes, through
  `sound_spec`, compiled and played by the backend, in `src/tracker/tests/synth_controls.rs`, every setting moved
  changing the sound and an effect heard at full Mix. A backend test fed a spec written by hand never stands alone,
  since it cannot see a setting the tracker fails to send.
- A test that looks wrong MUST NOT be changed just to pass: work out what it protected, and ask the user where the choice is
  theirs.
- Test data MUST NOT live in `examples/`; a set made to test the program is a data file beside the tests.

## How tests are written

- Tests follow every rule of `.claude/rules/STYLE.md`; values a test names are named (`let seed = 7;`), and limits come from the
  program's constants.
- **A UI test reaches its place by what is under the cursor**, never by a count of presses: it moves until the page says the
  cursor is on the row, field, cell or column named (the user's rule). The same holds for the screenshots and the tour.
- Keys are pressed by binding, never as letters; text the program shows is checked through its constant.
- A test asserts on a named part (the set's data, the status line, a field's shown value), never on a whole screen; whole
  screens are the screen baseline's.
- Keep the suite small: test a behaviour once, at the layer a person meets it. Nothing the compiler guarantees is tested.
- Tests use the program's contract, its public types, functions and the document's methods, never a type's private parts.
- A test starts from a named scenario, a set or a document made by a shared helper and named for what it holds, so that
  tests of the same thing start alike.
- A written file is checked by reading it back, never by matching its text. Random outcomes set a seed.
- Unit tests sit inline in the file they test; tests of a crate's behaviour as a whole sit in the crate's `tests/` folder.
