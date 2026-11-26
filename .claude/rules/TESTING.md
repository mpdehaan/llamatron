# How llamatron is tested

The rules for running and writing tests. The native code's tests follow their own, leaner rule (`.claude/rules/RUST.md`). Which module tests what is in `.claude/reference/TEST_LAYOUT.md`.

## Running

```
py_legacy/internal_tools/test.sh                # all tests in parallel, about 65 seconds
py_legacy/internal_tools/test.sh NAME ...       # classes whose module, class or method name contains a name
py_legacy/internal_tools/test.sh --serial       # one process, about two minutes
py_legacy/internal_tools/test_one.sh NAME       # one test
```

- `unittest`, run from the top folder after the install. `py_legacy/internal_tools/test.sh` runs `tests/support/parallel.py`: one process per
  class, forked from a server that has already imported llamatron, Textual and the tests' support (a module that names
  something after its process, such as FluidSynth's port, goes in `RELOADED_IN_EACH_CLASS`), slowest first by `tests/.cache/test_times.json` (git-ignored), new classes before all. Check its exit code or last line (`OK` or
  `FAILED: ...`). A class past `CLASS_TIMEOUT_SECONDS` (two minutes) fails; a test that loops waiting for something MUST first check
  that the thing exists.
- Three tiers: while building, only the feature's own modules (`py_legacy/internal_tools/test.sh NAME`); at a commit,
  `internal_tools/check_before_commit.sh`; before a push, the whole suite (`internal_tools/push_all.sh` runs it and stops on
  failure). The full suite MUST NOT be run while an idea is still being tried.
- `internal_tools/check_before_commit.sh` runs `py_legacy/internal_tools/test_changed.sh`: the classes that cover the changed files by the
  map (`tests/.cache/test_map.json`, built with `coverage` by `py_legacy/internal_tools/test_map.sh`), the rule tests always, and the whole suite for a
  change the map cannot place (a new source file, `tests/support/`). The long sweeps (every example, the wizard sweeps, the key
  tour) run only for changes in their folders (`SWEEPS` in `py_legacy/internal_tools/test_map.py`) or their own files. Rebuild the map after
  moving code or adding many tests. Read the check's real exit code; never pipe it through `tail`.
- While the Python program is frozen for the Rust port, the commit check runs its tests only when something it reads
  changed (`src/`, `tests/`, `examples/`, the Python tools, the requirements); a commit of `src/` alone is held by cargo's
  checks and the comparisons with Python (the user's direction).
- A change to the comparison tools alone (`internal_tools/compare_llamatron.py`, `py_legacy/internal_tools/compare_screens.py`) runs no
  Python test, since the frozen Python's tests cannot change (the user's direction); the comparison keeps the Python's answers
  in `.cache/compare_llamatron/`, git-ignored, worked out from the Python only where none is kept yet.
- The screen tour tries every key of every page, not only a settings page's edits: at the first stop at each kind of place
  on a page it presses each key that edits or opens something, stops where the screen changed, and takes the change back
  with ESC, CTRL+Z or the key's own way back. While llamatron2's pages are ported, `compare_llamatron.py screens --baseline`
  keeps the stops that differ, and the commit check fails only where a stop outside that baseline differs.
- No commit of code, tests, examples or tools goes in without the check passing. There is no git hook, and none MUST be added.
  Documents and `.claude/` files are committed without a run, apart from code mid-change; a document naming paths runs
  `tests/rules/test_doc_paths.py` first.
- Before and after a change that should leave the music alone: `py_legacy/internal_tools/capture.sh` and `py_legacy/internal_tools/compare.sh`
  (`py_legacy/internal_tools/compare_exports.py`), every export byte for byte, the version line aside.
- Before and after a change that should leave the screens alone, such as moving a page to the declarative pages:
  `py_legacy/internal_tools/compare_screens.sh capture DIR`, then `py_legacy/internal_tools/compare_screens.sh compare DIR`, every stop of the key
  tour, text and styles, at 80x24 and 160x50, and every dialog the UI tests that open dialogs show (`DIALOG_MODULES`), the
  first time each test shows each kind and title, about four minutes in all; for a change to dialogs alone,
  `capture-dialogs DIR` and `compare-dialogs DIR` skip the pages, about two and a half minutes, run once a batch of dialogs.

## What a change must come with

- Every behaviour has a test: model rules, what a file refuses, what each page's keys do to the set, what exporters write.
  Complex, high-coverage scenarios, not one happy path.
- A condition-specific shortcut MUST have tests of both paths.
- A rule about the code's shape gets a rule test where one can be written, listed in `.claude/rules/STYLE.md`.
- Before removing or renaming a constant, grep `src/`, `tests/` and `internal_tools/`.
- A test that looks wrong MUST NOT be changed just to pass: work out what it protected, and ask the user where the choice is theirs.
- Test data MUST NOT live in `examples/`; a set made to test the program is a data file under `tests/`.

## How tests are written

- Tests follow every rule of `.claude/rules/STYLE.md`.
- Limits come from the program's constants (`MAX_DRAW_VALUE + 1`, not `100`). Text the program shows is checked through its
  constant (`MSG_ROW_LABELS[Row.DEGREE]`).
- Keys are pressed by binding (`keybindings.PatternEditor.RESIZE`), never as letters or a `Key` letter: `press()` presses the
  first key; `back_key(binding)`, `forward_key(binding)`, `key_of(binding=, key=)`; `first_key`, `every_key`, `key_name(binding)`
  for legends. Non-typing keys (ENTER, ESC, arrows) MAY be pressed by `Key` name. `select_field(label)` reaches a field by label.
- A value the program names MUST be its constant everywhere, sample data included: `ScaleSetting.ROOT`, `NoteName.A`,
  `scale_type_name(ScaleType.MINOR_PENTATONIC)`. Before committing a test or tool, run `py_legacy/internal_tools/repeated_values.py -v` on it
  and name what it lists, except the test's own names that happen to match. A touched old test file is brought over whole.
- A test's own values (a seed, a velocity, a made-up name) are local variables named at the top of the test function; values
  shared by several tests are module constants. A test's own data, such as a pattern it calls `tune`, MAY stay literal.
- Keep the suite small: test a behaviour once, at the layer a person meets it. A mechanism shared by many pages is tested on two
  or three. A new rule test needs the user's agreement, after trying a design that prevents the mistake, a fixer or a comment. A
  removed feature takes its tests along. Exact-arithmetic tests are never weakened.
- A page's tests check what the page adds: its keys, its dialogs, its cursor, what it draws and which setting each field
  changes. What the change does to the set is tested once, on the object that owns it, and the page test checks only that the
  right change ran. Generic field behaviour (stepping, stopping at the ends, typing, picking, clearing) is tested on the field
  classes and in the table of every page's fields, never again on a single page.
- A test reaches a place by naming it (`go_to`, `select_field`, `pick`), never by counting presses; a test asserts on a named
  part of the screen (the status line, the legend, a field's shown value), never on the whole screen.
- A test starts from a named scenario of `tests/support/`, and a page is driven through its driver there; a page base class
  local to one module is moved to support once a second module needs it.
- Existing page tests are brought to these three rules as their page moves to the declarative pages (`.claude/planning/IDEAS.yml`, "The
  UX audit: declarative models and pages"), never before, so that no test is rewritten twice.
- Tests use the program's contract (constructors, getters, setters, document methods), never internals such as `document.data` or
  `pattern._rows`. A written file is checked by loading it with its library (`yaml.safe_load`, `ElementTree`, `mido`), never by
  matching text. Random outcomes set a seed. Song data lives in data files.
- A command-line test opening the tracker patches `LlamatronApp`, never `main`.
- MIDI timing is not pinned and there are no render snapshots; `py_legacy/internal_tools/compare_exports.py` guards the music.
- `tests/support/ui_testing.py` and `tests/support/rendering.py` call `Memory.check_every_answer()`, so every document rechecks
  remembered answers, kept data and undo snapshots; `Memory.check_every_answer(checks=False)` turns it off for a test of that.
  A method's cached answer (`cached_while` with `said=`) is checked at its first ask in each check round, which moves when
  anything in the set changes or `UITest` presses a key (`Memory.key_pressed`), not at every ask (the user's choice, 10 B), so
  a test that changes something no revision tracks starts a round itself before asking again.
- `UITest` (`tests/support/ui_testing.py`): `a_song()`, `press(*keys)` with `settle()`, `type(text)` (fails unless something takes
  text), `select_field(label)`, `text()`, `fixed_text`, `press_at_once(name)` with `drawn()`, `leaf_pages()`, `make_app()`. It
  refuses a real FluidSynth, lists no MIDI ports, so that no UI test opens CoreMIDI, and starts no render process, except in a
  class that sets `REAL_RENDER_PROCESS`, whose sender records rather than sends.
- A test class that opens CoreMIDI subclasses `CoreMidiTestCase` (`tests/support/coremidi_turns.py`), so that one such class runs
  at a time, whatever runs beside it.

## One test class per page

- Every leaf page (subclass of `Page` in `py_legacy/src/llamatron/interface/tracker/screens/`, not `Page`, `ListPage` or `FieldPage`) has a
  `Test<Page>` class in a `tests/interface/tracker/test_tui_*.py` module; `TestEveryPageHasTestClasses` in
  `tests/interface/tracker/test_tui_undo.py` enforces it.
- Undo needs no class per page: `Page` records a step after every key and dialog answer. Only a page whose undo does something of
  its own gets an `UndoTest` subclass in `tests/interface/tracker/test_tui_undo.py`, using `check_undo_and_redo(before=, after=)`
  and `check_undo_goes_back_to(page_class)`. Tests MAY shorten the history with `History(depth=)`.
- Questions about what undo or redo should do come to the user first (`.claude/tracker/SHARED.md`, "Undo and redo").
