# How llamatron is tested

The user's rules for the tests: how they're run, what they must cover, how they're written and
where each kind lives. Testing is a standing priority in this project, and it's what keeps the
rate of error-free changes high, so these rules are kept apart from the rules for the code
(`.claude/STYLE.md`) so that they can be reviewed on their own. `CLAUDE.md` imports this file, so
it's in force in every session. `.claude/STYLE.md`'s table "Enforced by the test suite" lists the
code rules that a test enforces, and this file says how the tests themselves are written.

## Running the tests

Tests use the standard library's `unittest`. Run them from the repository root, after the install
in `CLAUDE.md`:

```
internal_tools/test.sh                # all tests, in parallel: about 35 seconds
internal_tools/test.sh test_name ...  # the tests whose module, class or method name contains any of the names, in parallel too
internal_tools/test.sh --serial       # all tests in one process, the plain unittest way: about two minutes
```

`internal_tools/test.sh` runs `test/parallel.py`: one process per test class, as many at once as there
are cores, reporting every failure in full and the total count. The slowest classes start first, by
the seconds each took on the last full run, which it keeps in `.test_times.json` (ignored by git), and a
class with no time yet starts before them all, so that no slow class is left to start last. A class
whose tests each take long, like the tour of every page's keys, is split into a class per test, so
that the tests run side by side. It exits with a failure if any
class fails, so check its exit code or its last line (`OK` or `FAILED: ...`). A class that runs
past `CLASS_TIMEOUT_SECONDS` (two minutes, where the slowest takes about 35 seconds) is
stopped and counted as failed, with a message saying so, because a test that presses a key in a
loop until something appears can loop for ever when it never does, which hung a run; a test that walks rows or pages with a loop should check that what it waits for
exists first.
`.venv/bin/python -m unittest discover -s test` still works and gives the same results, just
slower. To run one test class on its own, run `../.venv/bin/python -m unittest test_x.TestY` from
inside `test/`, because `python -m unittest test.test_x` from the root finds the standard
library's `test` package instead. `internal_tools/test.sh`, `internal_tools/test_ui.sh` (the tracker's tests), `make
test-files` (the examples and demos) and `internal_tools/test_one.sh NAME` wrap these.

**No commit of code goes in without the full suite passing, and no git hook enforces it** (the user's
rule): the repository installs no pre-commit hook or any other git hook, and none is ever added, so that a
person who only edits documents commits at once. Claude tests when appropriate instead: before committing
anything that changes code, tests, examples or tools, it stages the files and runs
`internal_tools/check_before_commit.sh`, which first refuses when Python under `src/` is staged without a
version bump (`internal_tools/bump_version.py --check`, `internal_tools/bump.sh` to fix) and then runs
`internal_tools/test.sh`, and commits only when both pass. A change that only touches `dev_notes/IDEAS.md`,
the `.claude/` files or other documents can't fail a test, so it is committed with no run, on its own,
apart from code that's mid-change; a document that names paths is the exception, since
`test/test_doc_paths.py` checks them, and Claude runs that test before committing it.

The suite runs pyflakes over `src/`, `test/` and `internal_tools/` (`test/test_pyflakes.py`), so an unused
import, an undefined name or a name defined twice fails the tests; `pyflakes` is in
`requirements.txt` for that. Before and after a refactoring, or any change that should leave the
music alone, use `internal_tools/compare_exports.py` (`internal_tools/capture.sh` and `internal_tools/compare.sh`), which proves
byte for byte that every example still exports the same (ignoring the version line in the re-saved
sets), or shows which songs changed.

## What a change must come with

- **Every behaviour has a test**, and a feature isn't finished until its tests are in: the model's
  rules, what a file refuses, what each page does to the set when its keys are pressed, and what
  the exporters write. The user wants complex, high-coverage scenarios, not one happy path.
- **A shortcut needs tests of both paths.** Any condition-specific optimization, like skipping a
  pass that would do nothing, is only acceptable with good tests of the case it skips and the
  case it doesn't (`.claude/STYLE.md`, "Performance matters"), and a speedup is proved with
  `internal_tools/compare_exports.py`.
- **Rules get rule tests.** A rule about the code's shape is enforced by a test where one can be
  written, listed in `.claude/STYLE.md`'s table, so that it holds as pages and modules are added
  and rearranged rather than by reading.
- **When a constant is removed or renamed**, grep every place that uses it under `src/`, `test/`
  and `internal_tools/` first; pyflakes catches an undefined name, but not a string that changed meaning.
- **A test that looks wrong is an opportunity to ask a question.** Never change a test just so
  that it conforms to new code and passes: work out what it was protecting, make an intelligent
  choice, and where the choice is the user's, ask them.
- **Tests and scripts never fetch anything from the internet.**
- **Test data never lives in `examples/`**, which is for musicians (`.claude/FORMAT.md`, "Examples
  and demos"): a set made to test the program is a data file under `test/`.

## How tests are written

**Tests follow every rule the program does**, and the user requires it: `__slots__`, keyword-only
arguments, the GPLv3 header, named constants and the rest of `.claude/STYLE.md` apply to `test/`
and `internal_tools/` as they do to `src/`. Limits come from the program's constants
(`MAX_REGISTER_VALUE + 1`, not `128`), a number that means something gets a name, messages and
format strings are constants, and tests of the demos read what they check from the demo's YAML,
so that hand edits don't break them. When a test checks text the program shows, like a row label,
a key's name or a message, it imports the program's constant for that text (like
`MSG_ROW_LABELS[Row.DEGREE]` or `ERR_SCENE_NO_SUCH_SCALE`) rather than writing the words out again, so
that renaming something in the program doesn't break its tests. Keys are pressed by the bindings of
`tui/keybindings.py`, which say what they do (`keybindings.PatternEditor.RESIZE`,
`keybindings.PatternsPage.RENAME`, `keybindings.ConfirmDialog.YES`), never as letters and never as
a letter or mark of `Key`, which says only which key (`test/test_pressed_keys.py`): a test that
pressed the plus character to add broke when add became `A`, and said nothing about what it meant.
`press()` presses a binding's first key, the one the legend names. A binding that steps is pressed
with `back_key(binding)` or `forward_key(binding)`, and a key that isn't the first, like the older
`+` and `-`, with `key_of(binding=, key=)`, by the tests that check it still works. `first_key`,
`every_key` and `key_name(binding)` give a binding's keys and its name on screen to a test that
checks a legend. A key that types nothing, like Enter, Esc or an arrow, may still be pressed by
its name in `Key`. `select_field(label)` on `UITest` reaches a
settings field by its label rather than by counted presses. Any string the program defines, like a section (`Section.ARPS`), a root
(`NoteName.C`), a scale type (`scale_type_name(ScaleType.MINOR)`), a row or a direction, is the
program's constant in a test too, and any other literal a test needs is a named constant at the
top of the test file or a variable, never inline; test data of the test's own, like a pattern it
calls `tune`, can stay literal.

**Tests use the program's contract.** They work with the objects through their constructors,
getters and setters, and with the document through its methods, never by checking raw YAML or an
object's internal data structures directly; reading a file with `yaml.safe_load` to learn what it
holds is fine, poking at `document.data` or `pattern._rows` isn't. A written file is checked by
loading it back with the library that reads it and comparing data: YAML through `yaml.safe_load`,
a Live set through `ElementTree`, MIDI through `mido`, never by matching fragments of the file's
text. Tests that check a specific random outcome set a seed. Song data a test or script needs is
kept in the repository as data files, separate from the test code. A test of the command line
opening the tracker patches `LlamatronApp`, never the tracker's `main`, so that the real call into
it runs: mocking `main` once hid a wrong call for a whole release.

**Timing isn't pinned.** The user doesn't want exact MIDI timing tested, so there are no render
snapshots in the suite: `test/test_tracker_midi.py` checks the whole path from a song to MIDI with
Mary Had a Little Lamb and deliberately checks only that the notes and an accompaniment come out,
so that the math stays free to improve, and `internal_tools/compare_exports.py` is the safety net for a
change that shouldn't alter the music.

Many older tests predate these rules; new tests follow them, and old ones are brought over as
they're touched (`dev_notes/IDEAS.md`, "Refactoring the tests to the program's style rules").

## Where the tests live

Everything is directly in `test/`, with no `__init__.py`, because a package with that name would
clash with Python's standard library `test` package, and exporter and generator tests go directly
in `test/` too, since discovery doesn't reach subfolders without one. `test/demo_sources/` holds
the data the demos were written from, and `test/sample_sets/` the sets made to test the program,
like the two with values out of range. Tests are split by feature, each a file of its own, and the
shared helpers are modules beside them:

- **The model and playback.** `test/test_song_files.py` (what a file refuses, and its title and
  author), `test/test_song_patterns.py`, `test/test_song_scenes.py`,
  `test/test_song_generators.py`, `test/test_morphs.py`, `test/test_directions.py`,
  `test/test_grabs.py`, `test/test_grooves.py`, `test/test_composition.py` (each composition class),
  `test/test_length.py` (lengths as pairs, held to `Fraction`), `test/test_sound.py` (sounds as
  tuples, held to the classes that say the same, and the rule that the render imports none of
  the classes), `test/test_clip_sounds.py` (a clip held as objects and held as sounds answers
  the same, on every clip of every example), `test/test_pattern_notes.py` (a pattern's
  notes as the piano roll's bars, on `Pattern` alone), `test/test_examples.py` (every example loads, plays and exports to every kind),
  `test/test_demos.py`, `test/test_cli.py` and `test/test_corrections.py` (what opening corrects in
  a file's values, and what is still refused). They share the song-building helpers in
  `test/song_testing.py` (`pat`, `lead`, `with_parts`, `clip`, `pitches` and `BASIC`) and the
  rendering helpers in `test/rendering.py`: `as_setlist(data)` wraps old-style song data as a
  set, `setlist_from_data`, `song_from_data` (the one song of such data), `song_from_file`,
  `render_data`, `render_song(song, seed=)`, `render_file`, `estimate_data`, `is_demo` and
  `bare_document()`, a new `Document` with the starter pattern and its clip removed, for a test
  that builds a song from nothing. `test/ui_testing.py` and `test/rendering.py` both call
  `Memory.check_every_answer()`, so every document a test makes works each remembered answer out
  again after any change and fails the test with `StaleAnswer` if the answer kept was wrong
  (`test/test_memory.py` tests the memory itself, checking and not). The same switch makes a
  document check what it shares: the data its objects keep, the snapshots in its undo history,
  and that every undo leaves what loading the snapshot would (`.claude/TRACKER.md`, "Undo and
  redo"). `test/test_kept_data.py` tests the kept data and `Setlist.restore`, and holds the rule
  that data and objects share no list or dictionary. A test of what happens without the checks
  turns them off with `Memory.check_every_answer(checks=False)` and on again when it ends.
- **Real-time playback.** `test/test_realtime.py`: every example's timeline against its MIDI
  export tick for tick, the engine on a stepped clock with recording outputs, and the short
  lag test, a few seconds of the Entertainer through the real Realtime Sender Process, allowed
  ten milliseconds because the suite loads the machine. It also runs
  `test/sender_under_capture.py` in an interpreter of its own, which starts the process with
  a `sys.stderr` like Textual's capture in place, since that failed the spawn and
  only the first spawn of an interpreter can show it. The long report is `internal_tools/realtime_report.sh`,
  and `internal_tools/iac_check.sh` plays out of a real IAC bus, neither part of the suite.
- **Chains in three places.** `test/test_chain_places.py`: a clip's, its scene's and its track's
  chains running in that order, a chain named twice running twice, and a file's old single chain.
- **Density, Swell and Articulate.** `test/test_shapes.py`: the ramp over time, the strength of
  each place in a bar, each shape on a bar of sixteenths, which of a generator, a clip and a
  scene wins, and what a file refuses.
- **Grabbing a chord's root.** `test/test_grab_roots.py`: a grab takes the root of a chord in root
  position, inverted and voice-led.
- **Chords.** `test/test_chords.py`: a step's tensions and borrowed scale type, what a file refuses of both, and a chord
  spelled in a scale; `test/test_tui_chords.py` the pattern editor's Scale and Tension rows and the Chord dialog.
- **Inversions.** `test/test_inversions.py`: each inversion played, what a file refuses, and the
  roll's ghosts; `test/test_tui_inversions.py` the editor's row.
- **Progression.** `test/test_progression.py`: each chord moving a figure, sharps and flats,
  inversions, Every, drum patterns left alone, what a file refuses, and the chords' numerals,
  names and the named progressions matched to a scale. `test/test_tui_progressions.py` tests
  its pages.
- **Voice leading.** `test/test_voice_leading.py`: each chord voiced nearest the one before, the
  range, the root kept in the bass, a range nothing fits, and what a file refuses.
- **Strum.** `test/test_strum.py`: each direction, the spread in milliseconds at two tempos, fade,
  upstroke strings, loose timing from a seed, which of a generator, a clip and a track wins, and
  what a file refuses.
- **The Euclidean mask.** `test/test_euclid.py`: the named rhythms, rotation, a track's mask, its
  steps and step, a generator stacked on the track's, and what a file refuses.
- **Glide, Shorten, Rush and Drag.** `test/test_step_rows.py`: glides, short notes, the glide
  amount, a row's own step, rushes and drags and the two together, and what a file refuses.
- **The Hocket.** `test/test_hocket.py`: the turns going round the pool, a rest passing none, a
  chord passing whole, a track's own notes besides, the source unchanged and taking no turn, a
  muted source, Restart, and the source following a track's rename.
- **Restart.** `test/test_restart.py`: every clip, on new scene and whole song on the generators
  that follow time, the AutoRatchet's count and Voice leading's chord before carried on, and a
  generator starting every clip from what it was handed.
- **Time settings.** `test/test_time_settings.py`: the one list of times, bars read and measured
  by the song's time signature in a drift, a shape and an arp, and the field they share.
- **Drift.** `test/test_drift.py`: positions in every direction, what a drift does to velocity,
  probability, degrees, scale and root, its register adds once a trigger, and that every clip
  naming one hears the same picks.
- **Register binding.** `test/test_register_binding.py`: the `=` rows, the conditions, a bound
  velocity and bound CC lanes as a render plays them, and the track's and register's new
  settings; `test/test_registers.py` holds the registers themselves.
- **The MIDI import.** `test/test_midi_import.py`: every file in `examples/midi/` and every
  example set exported as MIDI, imported into a new set, played and exported again, plays the
  same notes at the same tempos, or the import warns of what it changed (`round_trip` in
  `importers/comparison.py`, all in memory), with smaller tests on MIDI files built in memory
  of the reading, the keys, the voices, the scenes and patterns, the CCs and the names, and
  `test/sample_sets/cc_sweeps.yml`, which sweeps every CC the import takes.
  `internal_tools/import_check.py` (`internal_tools/test_all_sample_midi_against_import.sh`) prints the same as a
  report. `test/test_tui_import.py` tests the tracker's side: the main screen's Import cell,
  the picker and the import dialog.
- **Live editing.** `test/test_tui_playback.py`'s `TestLiveEditing`: each Live response heard at
  its moment, typed digits heard once settled, a clip made to loop keeping its scene playing, a scene
  inserted above and a track renamed, an edit that can't render, another song made current, and the
  play's random parts kept; `TestArrangePlayback` holds the song playing on through pages and the
  refusal to delete, and `TestClipPagePlayback` the preview stopping with its page.
- **FluidSynth.** `test/test_fluidsynth.py`: FluidSynth found, started, waited for and ended,
  with a fake process and fake ports; `test/test_tui_playback.py`'s `TestFluidSynthPlayback` the
  transport's channels, program changes and starting; `test/test_tui_silent_instruments.py` the
  warning when a set opens with instruments that can't sound. `test/test_record_demo.py` tests
  `--fluidsynth`.
- **The WAV export.** `test/test_wave_fluidsynth.py`: only the tracks through FluidSynth, their sounds,
  the temporary MIDI file removed, the WAV normalized, the refusals, and the tracker's question.
- **The demos as audio.** `test/test_preview_midi.py` (the previews and their names),
  `test/test_normalize_wave.py` (a WAV file's peak moved to 1 dB below full scale) and
  `test/test_play_demo.py` (the numbered list, `afplay` and the progress line).
- **The title and the start screen.** `test/test_title_card.py`: the title on black at moments the test chooses (the
  letters' width and waves, the scanner's sweep and shading, the address, the prompt's pulse, the fade to black), and
  the start screen shown only when asked on a plain launch, until Enter.
- **A batch video's stage.** `test/test_batch_stage.py`: the READY box's room, the frame's cells from the edge in, the
  track's order, the pulse's tail and its turning and colour at a change of scene, the box growing, the fade to black and
  the opening cut to black; `test/test_tui_playback.py`'s `TestBatchVideoLaunch` the launch from title to quitting.
- **The batch recordings.** `test/test_window_region.py`: PNG stills read with every filter, the cells found inside a
  title bar, margins and rounded corners, and the screen's points; `test/test_record_batch.py`: the pairings, shortest
  first, the limit, a new set's mode and stopping at a failure; `test/test_record_demo.py` the batch take. Nothing is
  recorded.
- **The documentation website.** `test/test_stage_docs_site.py`: the guide staged as the front page,
  the links between the pages, and the sidebar made from the guide's tables, listing every chapter in
  `docs/` once; and `test/test_serve_docs.py`: the local server finding each page as GitHub Pages does, with or without `.html`, nothing outside the site, and a page in `web_docs/` for every chapter. VitePress itself is never run by the suite, which fetches nothing.
- **General MIDI.** `test/test_general_midi.py`: drums on channel 10, each track on a channel of
  its own going round after the fifteenth, its instrument's sound as a program change or none,
  muted tracks left out, and what a file refuses of an instrument's sound.
- **The genre library.** `test/test_genre_analysis.py` (each measure on songs written note by note, and a demo measured from its render), `test/test_genre_measures.py` (every measure registered once, with a unit and a label), `test/test_genre_comparing.py` (two drum grooves compared), `test/test_genre_cleaning.py` (a MIDI file cleaned and its doubts said), `test/test_describe_style.py` (a style as a document, nothing of the notes, and the script), `test/test_fetch_corpus.py` (the corpus fetcher's checks, with no network), `test/test_dataset_study.py` (the dataset study's readers on small examples) `test/test_corpus_layer.py` (the corpus layer's sources, terms and pieces) and `test/test_cells.py` (a band's MIDI file written note by note comes back as its kit's, bass's and chord part's bars, a lead's pitches change nothing, and the report's arithmetic).
- **The exporters and generators**, named after them, with `test/test_matrix.py` as an end-to-end
  example of the classes underneath the tracker and `test/test_generator_list_steps.py` checking
  that no list generator lets a rest use up a value. `test/test_exporter.py` tests the base class
  every exporter shares, with two small kinds of export made for the test, and holds the rule
  that every exporter class is listed in `exporters/exports.py`.
- **The tracker.** The `test_tui_*.py` modules run the real program with no terminal and press
  keys, through `UITest` in `test/ui_testing.py`: `a_song()` builds a document to work on,
  `press(*keys)` presses keys by their names, letting the tracker handle each with
  `settle()` (`pilot.pause(0)`) rather than `pilot.pause()`, whose wait for the computer to go idle
  cost a fiftieth of a second a key and far more with the suite's classes side by side; `UITest`
  refuses to start a real FluidSynth, so a test that plays through it gives its transport a stand-in,
  as `test/test_tui_playback.py` does; `type(text)` types text and fails unless a prompt,
  a picker's search, a list's search or the notes' text is open to take it (each screen
  and dialog answers `takes_text()`), so that a name typed at the wrong moment can't press a
  page's keys letter by letter, `select_field(label)`
  reaches a settings field by its label, `text()` is what the screen shows and `fixed_text` the
  part of a template that doesn't change. `press_at_once(name)` presses a key that only moves a
  cursor without waiting for the event loop, about 25 times faster, and `drawn()` is what the page
  drew straight after, which a test that walks a whole page uses; `leaf_pages()` lists every page
  class that isn't there to be subclassed, for the rules about every page. A test class that
  starts the tracker another way, like on a file that needs corrections, overrides `make_app()`.
  `test/test_tui_fields.py` tests the kinds of settings field and tours every settings page,
  `test/test_tui_arrange_drawing.py` tests what draws Arrange, apart from the page,
  `test/test_tui_arrange_details.py` Arrange's details view, `test/test_tui_scene_view.py` Scene View and the Inset Window, `test/test_visualizer_choices.py` the
  visualizer modes a set and a song choose and hide,
  `test/test_tui_step_editors.py` runs one set of checks on the offsets editor and the groove
  editor, which share `OneRowEditor`,
  `test/test_tui_document.py` tests `Document` on its own, `test/test_tui_named_edits.py` its
  renaming, copying, deleting, moving and sorting on every section,
  `test/test_tui_shapes.py` the Density, Swell and Articulate pages and the settings pages' sections,
  `test/test_tui_named_lists.py` the same five on every page that lists named things, and
  `test/test_tui_named_item_pages.py` the name, the rename and the undo questions of every page
  that shows one named thing, each with one set of checks run on every such page, `test/test_tui_history.py` the undo
  history and the document stepping through it, `test/test_tui_undo.py` undo and redo on every
  page, and `test/test_tui_corrections.py` the Corrections dialog, from the Open page and when
  the tracker starts. `test/test_tutorial.py` runs the video tutorial at no pace on the hello
  world demo and on `test/sample_sets/tutorial_target.yml`, and holds each set built to its
  target by its data and by its music, every song's timeline event for event, and what the
  tutorial calls out as it presses each key; `test/test_tui_caption_strip.py` tests the caption
  strip, on its own and at the foot of a page, and the SubRip file made from the captions.
- **The visualizer.** `test/test_visualizers.py` tests the modes on their own, the frames' sizes,
  a resize, the drawing of big pixels, and that the lava lamp stays dark in silence, glows where a
  track plays and never passes its ceiling or jumps in brightness, even with 64 tracks hitting at once, and `test/test_tui_visualizer.py` the visualizer on
  Arrange; `test/test_preview_visualizer.py` tests the preview tool's parts that need no port.
- **The rules.** `test/test_slots.py`, `test/test_keyword_only.py`, `test/test_revisions.py`
  (every method that changes a stored object is written under `@notes_change`),
  `test/test_setting.py` (every setting is described once, and reading and setting refuse a
  value in the same words), `test/test_row_descriptions.py` (every row of a pattern is described
  once, and a file, the setter and the editor's rows agree),
  `test/test_message_constants.py`, `test/test_pyflakes.py`, `test/test_yaml_safety.py`,
  `test/test_doc_paths.py`, `test/test_diagrams.py`, `test/test_renames.py`,
  `test/test_pressed_keys.py` (no key pressed as a letter, written out or named in `Key`),
  `test/test_keybindings.py` (the rules of `tui/keybindings.py`),
  `test/test_tui_help_keys.py` (every key a page's help names is bound on that page, every bound
  key is one of its own class's bindings and no key reaches two bindings in one place, found by
  touring every page and walking its cursor to every place, whose `TestKeyMapIsCurrent` holds `.claude/KEYMAP.md` to what the tour finds, rewritten by `internal_tools/key_map.sh`), `test/test_bump_version.py` and the
  rule tests in `test/test_tui_pages.py` and `test/test_tui_undo.py`. `test/test_key_table.py`
  tests how keys are bound, and `test/test_show_keys.py` the tool that prints them.

## One test class per page

Every page of the tracker (every leaf subclass of `Page` in `src/llamatron/tui/screens/`, leaving
out `Page`, `ListPage` and `FieldPage`, which exist to be subclassed) has two test classes named
after it, and `TestEveryPageHasTestClasses` in `test/test_tui_undo.py` fails when either is
missing, so that a new page can't arrive without them:

- `Test<Page>`, in some `test_tui_*.py` module, which tests what the page does: `TestSongPage`,
  `TestPatternEditor`, `TestArrangePage`. A page can have more classes beside it, like
  `TestArpEditorFields`, but it has that one.
- `Test<Page>Undo`, in `test/test_tui_undo.py`, a subclass of `UndoTest` there, which makes an
  edit on the page by pressing keys, undoes it with `Ctrl+Z` and redoes it with `Ctrl+Y`
  (`keybindings.Page.UNDO` and `REDO`), and checks the set, the cursor and the status line through
  `check_undo_and_redo(before=, after=)`. Where an undo can take away the thing the page shows,
  like the editor of a pattern whose adding was undone, the class also checks with
  `check_undo_goes_back_to(page_class)` that the tracker went back to the page underneath and
  said so, and where the page's thing can be renamed, that undoing the rename keeps the page
  showing it under its old name. Edits that merge into one step, like digits typed into one cell, a munge, or the
  notes' text until Tab, each have a test on the page that makes them.

Undo tests may use a shorter history through `History(depth=)` when filling the ring would be
slow; the tracker's own depth is `HISTORY_DEPTH` and nothing shows or sets it. Any question about
what undo or redo should do on a page comes to the user before anything is built, since the
behaviour was agreed in detail (`.claude/TRACKER.md`, "Undo and redo").
