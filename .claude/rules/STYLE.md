# How llamatron's code is written

**While llamatron is ported to Rust, the user waives every Python style rule of this file and the others** (the user's
word): Python code is written as plainly as before where it costs nothing; the tests that hold the style rules
(`tests/rules/`: code shape, keyword-only, layers, message constants, nested comprehensions, slots, unique class names) are
skipped with `STYLE_WAIVED`, and the commit check no longer runs the style fixers (constants by module, sorted imports). The
tests of behaviour, documents and safety still run, pyflakes among them for its undefined names, and the Rust code keeps its
own rules (`.claude/rules/RUST.md`), cargo fmt and clippy included.

The rules for the code, its tests and `internal_tools/` alike. `docs/ARCHITECTURE.md` explains the design they serve. Where a test
enforces a rule, it is named; otherwise the rule is kept by reading. The code MUST be easy for people to maintain without AI:
plain code, comments that explain why, tests that read clearly, object orientation throughout.

## Enforced by the test suite

| Rule | Enforced by |
| --- | --- |
| Every class declares `__slots__`, each class in a hierarchy its own, even `()`; dataclasses are `@dataclass(slots=True, kw_only=True)`. Except constant-only classes and subclasses of outside classes. | `tests/rules/test_slots.py` |
| Keyword-only parameters (a bare `*`) wherever a call passes more than one argument or any optional one. Exceptions are listed in the test. | `tests/rules/test_keyword_only.py` |
| Every shown or raised string is a constant in `py_legacy/src/llamatron/user_strings/` (or a generator plugin's `strings.py`), prefixed `ERR_`, `HELP_`, `REPR_` or `MSG_` by module; group comments name real modules; the package imports only names; no name defined twice. | `tests/rules/test_message_constants.py` |
| No unused import, undefined name or name defined twice. | `tests/rules/test_pyflakes.py` |
| Constants of llamatron, the tests or the tools are named through their module, never imported by name. | `py_legacy/internal_tools/constants_by_module.sh --write`, run by `internal_tools/check_before_commit.sh` |
| Opening imports sorted: libraries, a blank line, the project's; by module; names in order; one line a module. | `py_legacy/internal_tools/sort_imports.sh --write`, run by the commit check |
| A package imports only packages below it, only through front doors; a page imports no page and of the model only its schema names, values and version. Existing crossings are listed and the list only shrinks. | `tests/rules/test_layers.py`, `py_legacy/internal_tools/layers.sh`, `tests/rules/layer_exceptions.py` |
| No comprehension holds another comprehension or three loops (in `src/`). | `tests/rules/test_nested_comprehensions.py` |
| Body at most 30 lines (docstring aside); nesting at most 3 (4 where listed with a reason); at most 5 parameters besides `self`/`cls`; no reaching into another object's `_name`; catch-all only where listed; at most one `isinstance` per function ("Objects"); a file or class at most 500 code lines (1000 in `engine/` and `realtime/`), except the list files (`file_format.py`, `keybindings.py`, `user_strings`). Existing breaches are listed and the list only shrinks. | `tests/rules/test_code_shape.py`, `py_legacy/internal_tools/code_shape.sh`, `tests/rules/shape_exceptions.py` |
| No two classes share a name (listed exceptions only shrink). | `tests/rules/test_unique_class_names.py` |
| Each screen lists its keys once, in `keys()`; every page's help fits 80x24. | `tests/interface/tracker/test_tui_keys_shown.py`, `tests/interface/tracker/test_tui_help.py` |
| No screen method shares a name with Textual's, such as `render` or `remove`. | `tests/interface/tracker/test_tui_look.py` |
| Every key a page's help names is bound there; a page binds only its own class's bindings; no key reaches two bindings at one place. | `tests/interface/tracker/test_tui_help_keys.py` |
| Every page, dialog and component that binds keys has a class of its name in `interface/tracker/keybindings.py`, inheriting alike; every binding is listed for F1 and bound; no `Key` or `KeyName` unused. | `tests/rules/test_keybindings.py` |
| `.claude/reference/KEYMAP.md` matches the key tour. | `TestKeyTour` in `tests/interface/tracker/test_tui_help_keys.py` |
| Every page has a `Test<Page>` class. | `tests/interface/tracker/test_tui_undo.py` |
| Diagrams, demo index and demo summaries match the code and examples. | `tests/rules/test_diagrams.py`, `tests/tools/test_demo_summary.py` |
| Every path the documents name exists; every page in `docs/` is linked from `docs/GUIDE.md`. | `tests/rules/test_doc_paths.py`, `tests/tools/test_stage_docs_site.py` |
| Every generator has a settings class and an example that uses it. | `tests/app/test_examples.py` |
| Every exporter is listed in `exporters/exports.py` with a kind and label. | `tests/exporters/test_exporter.py` |
| Renames keep every example loading and playing the same; `REFERENCES` name real settings. | `tests/model/test_renames.py` |
| In `model/`, every method that changes a revised object is under `@notes_change`, and the constructor calls `note_change()`. | `tests/rules/test_revisions.py` |
| Written data shares no list or dict with the object, nor the object with what it was read from. | `tests/model/test_kept_data.py` |
| Every setting is described once in its class's `SETTINGS`; the file and the setter refuse alike. | `tests/model/test_setting.py` |
| Every pattern row is described once in `ROW_DESCRIPTIONS`; file, setter and editor agree. | `tests/model/test_row_descriptions.py` |
| No remembered answer outlives a change to what it came from. | `Memory.check_every_answer`, `tests/caching/test_memory.py` |
| YAML only through `safe_yaml.load_safely`; only `setlist_reader.py`, `setlist_writer.py` and `safe_yaml.py` import `yaml`. | `tests/rules/test_yaml_safety.py` |
| Old-layout code lives only in `model/file/migrations/`; outside imports only `migrated` and `Conversion`; a migration imports no objects or reader. | `TestMigrationsStayApart` in `tests/model/test_migrations.py` |
| Render modules (`engine/realizer/`, `engine/generators/`, `engine/clips/positions.py`, `engine/timing/timing.py`) import no `Note`, `Rest`, `Chord`, `Degree` or `Held`. | `tests/model/test_sound.py` |
| Speedups and refactorings leave every export byte for byte the same. | `py_legacy/internal_tools/compare_exports.py` |

Kept by reading: no type hints; every class has a docstring; plain getters are `get_x`/`is_x`/`has_x`/`can_x` (listed
exceptions say why); tests press keys by binding, never as letters; every made-up name comes from `model/objects/naming.py`.

## Readability

- **Readable over clever.** Explicit, simple, flat; errors never pass silently. Code a reader must stop to work out is allowed
  only for measured speed (the render's per-note loop, the real-time player), with a comment saying why.
- **The two timing processes come first.** The Synthesis Process (`realtime/synth_process/`) and the Realtime Sender Process
  may break these rules where a rule would slow their timing (the user's yes): plain attributes, long hot functions, a
  catch-all at a process's edge, and in their hot paths whatever is fastest in place of strings and dictionaries (integer codes,
  tuples, plain attributes; the user's waiver, which asks only for good method and variable names there). Each breach the rule
  tests see is listed with its reason; everything else follows the rules.
- **A shape rule is met by naming the thing a person would name**, never by cutting code into pieces or a clever line. Where no
  such thing exists, the code stays listed with a reason.
- **Organized at every scale.** A file holds one subject in a sensible order; a class is a nameable thing with a visible
  contract; each line says plainly what it does. Three or four near-repeats get a helper whose name says what the shape means.
  Claude keeps making code simpler and more elegant, not only correct.
- **A function reads like a book** (281):
  1. One thing a line: no comprehension, conditional expression or call-holding literal inside a call's arguments; no
     conditional `**` splats. A simple comprehension, a plain copy, filter or map, is always fine. In `engine/` and `realtime/`
     a complex one MAY stay where a loop would be measurably slower, and is otherwise avoided.
  2. A chain is named first: `band = choices.get_band()`, then `band.players()`. A `.get()` lands in a variable, never chained.
  3. One level per function, top to bottom. A public method MAY be two lines that build a thing and hand it to a private helper.
  4. A dictionary of fixed keys passed around is a missing object.
  5. Statements over expressions: `if`/`elif`/`else` over conditional expressions; a loop over a comprehension that filters and
     transforms at once. A comb of `if`s often signals a design problem.
  6. Names read as English, without repeating the object's name: `melody().engine()`, not `melodies().melody_engine()`.
  7. A helper MUST mean something: its name says a thing a reader would name and its body reads plainly. `@staticmethod` is
     welcome where it reads well.
  Every rework step in `model/`, `engine/` or `realtime/` is timed before and after; pages are not, since a render never runs them.
- **Order in a file.** A class MUST list special and public methods first, `_private` methods after. A module's private helper
  functions MUST come after its classes, unless a class body uses them at definition. Reorder a file after working in it; never
  reorder a file for this alone.
- **Short and shallow.** Body at most 30 lines, nesting at most 3 (4 only where listed with the reason), at most 5 parameters;
  values travelling together past that are a missing object, proposed to the user. A file or
  class at most 500 code lines, 1000 in the render and the sender (`engine/`, `realtime/`), split only into things a reader would name; the limit is generous so that files are rarely split
  for size, while behaviour that belongs together is still gathered.
- **No new exceptions** to any rule's list (`shape_exceptions.py`, `layer_exceptions.py`, a test's own list) without the user's
  yes, given only for tight performance in a critical section. Existing entries are a backlog, fixed by better design.
- **A line whose purpose isn't obvious gets a name**: a regex, a long expression, or a comprehension beyond a plain copy or
  filter goes in a function named for its purpose.
- **Steps that must go together are one method.** Where two or more steps always run together and leaving one out would be a
  bug, such as storing a scene's new name and following it in the crumbs, they live in one method named for the whole act,
  and every caller uses it; no caller repeats the steps by hand. This is for the pages, the forms and the other code a key
  press runs; the render's and the sender's hot loops (`engine/`, `realtime/`) MAY spell such steps out where a call would
  cost measurable time.
- **Comments give the reason**, for a maintainer: never whose choice it was or when. Comments do not excuse unclear code.

## Objects

- **Behaviour lives on the object that owns the data**: everything about a pattern is on `Pattern`. Code reads at the level of
  the problem, with shared helpers for repeated shapes (`llama_data.py`'s `settings_by_name`, `written_settings`, `or_default`).
  The one exception is musicianship: a pattern's storage and editing live on `Pattern`, while what a musician does to a pattern,
  such as inverting, developing or voice leading it, lives in `music_theory` and works through `Pattern`'s methods.
- **An object is a thing a reader would name**: a player, a cursor, a run of passes. Before adding a function, name the thing it
  belongs to. Functions passing the same values along, or a dict standing in for a thing, is a missing object; propose it to the
  user before going on (`.claude/planning/REFACTORING.md`).
- **Explicit methods.** Other classes change data only through `set_x(value)`, which validates with the setting's one check
  (`model/schema/setting.py`), and read through `get_x()`: no properties or descriptors. A class has the accessors others use and
  no more. `Note`, `Chord`, `Scale`, `Rest`, `Degree`, `Held`, `TimeSignature` are immutable. `Document` and pages change the set
  only through setters; pages read it via `document.get_setlist()` and `document.song()`.
- **Names say what a method does.** `get_x`/`set_x` hand back or store what is held, in every package; anything else works
  something out. `get_written_x` is the value as written, `None` if absent. Yes/no: `is_x`, `has_x`, `can_x`, or a verb
  (`loops()`, `launches_together()`); a question others answer by computing keeps the question as its name.
- **Class names** are as a person would name them and unique across the program. A kind of a role ends with the role
  (`ArpEditorPage`, `PianoRollWidget`); a machinery base (`LlamaData`, a mixin) adds nothing to the name. Judged by intuition.
- **One word for one thing:** `move_cursor(name)` an arrow moves a cursor (`Cursor.move` its own); `shift(offset)` carries what
  the cursor is on, `drop()` puts it down; `advance(seconds)` time moves on; `remove_step`/`insert_step`, with
  `remove_step_here()`/`add_step()` at a one-row editor's cursor; `step_count()` a count, `steps()` the steps; `remarks(width)` a
  settings page's lines under its settings (`notes` is only music, or the set's Notes); `toggle()`; `refusal` text or `None` (a
  `Problem` is a title and lines); `forget(tag=, after=)` the sender drops unplayed events.
- **Objects keep their own counsel.** No reading or writing another object's `_name`. No catching `Exception` or bare `except:`
  except where `shape_exceptions.py` says why.
- **Asking an object its class is a design smell.** Things kept together share a base class and are asked to act, or read a
  class constant for their kind; at most one `isinstance` on a program class per function, and existing places are a backlog.
  Checking file or typed data against built-in types is free.
- **Callbacks.** A callback with fixed arguments MUST be `functools.partial(self.give, role)`, never `lambda role=role: ...`. A
  callback that works something out MAY be a lambda.

## Python details

- **`__slots__`** on every class (see the table); `id` is read-only where present.
- **No type hints** anywhere: code without them is easier to read. Names and docstrings say what a value is. Dataclass and named-tuple fields are
  still declared.
- **Keyword arguments** after a bare `*`. Exceptions (in the test): special methods; `Rational`, `Length`, `Sound` (render hot
  path); methods Textual or `unittest` call positionally; `*arguments, **named` forwarders; nested functions. The rule's ~7%
  render cost was accepted.
- **Every string used as a value or name is a named constant**: file keys, settings, kinds, modes, note names (`NoteName.C_SHARP`),
  chord symbols, key names, exporter tags; and numbers with a meaning (`MIN_PROBABILITY`). One file's constant sits at its top;
  shared ones in the package (`model/schema/defaults.py`, `limits.py`, `file_format.py`). One constant a line, never tuple
  assignment. Unused constants are removed. `py_legacy/internal_tools/loose_strings.py src` SHOULD report nothing.
- **Constants are named through their module**: `labels.MSG_X`, `errors.ERR_X`, `limits.MAX_NAME_LENGTH`, `midi.MAX_VELOCITY`,
  `sound.KIND`, in `src/`, `tests/` and `internal_tools/`. `help.py` imports as `help_text`, `user_strings/song_wizard.py` as
  `wizard_text`. Where a file already uses the module's name, import it under another (`labels as labels_text`); never name a new
  variable after a module. Classes, name classes (`ClipSlotSetting`, `Row`) and functions are imported by name. A constant is
  named through the module that defines it. In a per-note or per-step render loop, a constant MAY be bound to a local first.
- **Imports**: two sorted groups (see the table). An import that must stand elsewhere to avoid a cycle is the one exception.
- **Arrays stay arrays.** List-like data is stored as real values (sixteen booleans, never `'x...x...'`), in files, generated
  modules and memory; shipped data is an imported Python module of named constants, never a parsed text file. Display strings are
  made where shown. Exception: the song wizard's YAML style templates in `py_legacy/src/llamatron/wizards/create_song/style_templates/`,
  with a small subclass only where a style behaves differently.

## Packages and layers

- `math/` exact arithmetic and random sources; `music_theory/` llamatron's musicianship, its `fundamentals` (pitch and
  intervals) under the model and its chapters over it; `caching/` revisions and remembered answers; `user_strings/` text; `model/` the
  set as stored (values, objects, schema, file); `engine/` clips, timing, generator plugins; `exporters/`; `importers/`;
  `interface/tracker/`; `interface/visualizers/`; `wizards/create_song/`. New modules go where their purpose says; a
  new group gets a package.
- `interface/tracker/screens/` is in folders by what the screens edit: `pattern/`, `arrange/`, `generators/`, `set/`, `shared/`.
- Anything a llamatron user runs lives in `py_legacy/src/llamatron/`; `internal_tools/` holds only launch scripts and build and analysis
  tools. Reusable scripts live in `internal_tools/` or `user_scripts/` with a docstring, never in a temporary folder.
- Layers, bottom up: `math`, `music_theory/fundamentals`, `caching`, `user_strings`, `model`, `music_theory` (its other
  chapters, which understand patterns and songs), `engine`, `exporters`, `importers`, `realtime`, `wizards`,
  `interface/visualizers`, `interface/tracker`. Front doors:
  `engine/realizer/song_realizer.py`, `exporters` via `exports`, `importers` via `midi_import`, `wizards` via
  `create_song.wizard_choices` and `create_song.wizard_limits`, `realtime` only from `interface/tracker/transport.py`,
  `interface/tracker/pattern_preview.py` and `cli.py`. A crossing import signals a missing object below, never a new exception.

## Text and keys

- **Every shown or raised text is a template constant** filled with `.format()`, in `py_legacy/src/llamatron/user_strings/`: `ERR_` for
  anything saying what went wrong (dialog titles too) in `errors.py`; `HELP_` in `help.py`, one multi-line string per page, line
  for line as shown; `REPR_` in `reprs.py`; `MSG_` for all else in `labels.py` (page names, labels, headings, crumbs, picker
  choices, `Crumb`, `Column`), `legends.py` (keys, `What`), `messages.py` (status notes, titles, prompts), `marks.py` (cell marks,
  number formats), `about.py`, `cli.py`, `names.py` (new things' names, section words, export kinds). Constants are grouped under
  a comment naming the module that uses them. The package imports names only from `file_format.py`, `interface/tracker/keys.py`
  and itself. Non-text strings (key names, file modes, format names, tags) keep their own modules. Docstrings and comments stay
  put.
- **A generator plugin's own words** live in `engine/generators/<plugin>/strings.py` (any prefix), handed over by its declaration
  and read via `generator_plugins.plugins()`; shared words stay in `user_strings`.
- **Keys.** Every binding lives in `interface/tracker/keybindings.py`: a class per page, dialog and component, each binding a
  tuple of keys, legend name and description. Stepping keys are `Steps(back=, forward=)`, and the action receives `STEP_BACK` or
  `STEP_FORWARD`; only a key that types its character, or an arrow through `moves.moved`, gets its name (`wants_key=True`).
  `keys()` both handles and draws a screen's keys; `IN_LEGEND` leaves a binding to F1 only. A settings page's actions are
  `Button`s after its `Field`s, spaced by `FieldPage`. UX rules are in `.claude/rules/UX.md`.

## Performance

- **Lengths and times are exact**: `Rational`s, except inside a render, where a length is a pair handled by `Length` and a note a
  tuple handled by `Sound` (`.claude/format/PLAYBACK.md`). Pairs are compared only through `Length`; a sound is read by named
  places (`sound[LENGTH]`).
- **Fewer operations**: build each note once, keep steps as per-row arrays, work out what can be without playing, skip passes
  that do nothing. Every such shortcut MUST have tests of both paths, and is proved with `py_legacy/internal_tools/compare_exports.py`.
- **Work out an answer once** and remember it until its sources change. Everything a set stores carries a revision
  (`caching/revised.py`), moved by `@notes_change`. The document's `Memory` keeps answers with their sources' revisions:
  `Document.remembered(key=, on=, compute=)`, `on` being the document, `document.get_outside_patterns()`, or the objects
  themselves. A key holds whatever outside the set the answer depends on. Every memory checks itself in tests.
- **Three ways to remember**: `functools.cache` for module functions of hashable arguments only (never methods;
  `cached_property` never); `cached_while(key_of)` (`caching/cached.py`) for a method depending on its object's state, with
  `said=` to recheck under tests; `cached_for_life` for an object that never changes. No class keeps its own answer dict. Set data
  goes through `Memory`. A cache no test can see going stale MUST NOT be added; a new kind needs a new decorator with tests of
  keeping and forgetting.
- A question asked per cell is asked once per line and passed down. `model/file/checks.py` keeps parsed values by their text. A
  getter that parses or searches on every call is a hotspot: find them with `cProfile`.
- YAML is touched only in `Setlist.read_file`, `write_file` and the save checks. `Document.record_edit` returns at once unless a
  setter ran; snapshots share unchanged objects' `kept_data()`, so data once kept MUST NOT change; `to_data()` gives a fresh copy.
- **Every generator is efficient on its own**, measured per note on the songs that use it; what its settings alone decide is
  worked out once.
- **Binding is late**: a degree stays a degree until the clip knows its scale; step size and time signature stay blank until the
  set's apply; a groove is chosen at render. Never recompute what has not changed.

## The set file

- Every setting has a default, so older files load and new settings need no migration.
- A key rename or structural change MUST come with a migration in `model/file/migrations/`, built from the package's helpers and
  never changed once released. Every shipped file is migrated in the same change, exports unchanged, and
  `tests/data/migrations/` keeps an old-layout file for its tests.
- A removed setting MUST NOT get a migration or a list of removed names: the reader passes over unknown names
  (`pass_over_unknown`), and the next save drops them (`tests/model/test_song_files.py`).
- A rename MUST update every reference by name (`tests/model/test_renames.py`).

## Files, scripts, documents

- The GPLv3 header (`CLAUDE.md`, "License") on every Python file and script.
- No new folder whose name starts with a dot is committed, since one is easily missed in what a commit adds; `.claude/` is
  the one there is (the user's rule). Caches and other working files go in git-ignored dot folders, such as `.cache/`.
- Scripts are plain `sh`, `#!/bin/sh`, named with underscores. Setup instructions MUST NOT need `make`. A script that installs
  something offers to install what it needs first and installs nothing without a yes.
- Every change carries its documentation: a changed feature, setting, default or key updates its page in `docs/` in the same
  change, in the UI's names; a change to the model or tracker updates `.claude/format/` or `.claude/tracker/`; a changed rule
  updates this file; a moved module moves every path naming it. How documents are written and generated: `.claude/rules/DOCS.md`.
- Tests follow every rule here (`.claude/rules/TESTING.md`).

## PEP 8

The suite runs pyflakes, not pycodestyle. `py_legacy/internal_tools/pep8.sh` runs pycodestyle for a look, leaving out E501 (long lines),
E302, E305 and W391 (named in the script). Nothing pycodestyle reports is a rule unless it is on this page.
