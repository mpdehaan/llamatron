# Where the tests live

Which test module tests what, read when adding a test or looking for one. The rules for tests are in `.claude/rules/TESTING.md`.

The tests are the package `tests/` (never `test`, which would clash with Python's standard library `test` package), in
folders that mirror `py_legacy/src/llamatron/`: `tests/model/`, `tests/engine/realizer/`, `tests/engine/`,
`tests/engine/generators/`, `tests/exporters/`, `tests/importers/`, `tests/realtime/`, `tests/model/`, `tests/interface/visualizers/`,
`tests/genres/`, `tests/music_theory/` (music_theory's chapters, such as `test_tune_fit.py`, a tune fitted to new chords, `test_analysis.py`, keys and chords found from notes, `test_chord_estimate.py`, the chords a lead sheet prints, estimated from notes, and `test_heard_chords.py`, a heard chord's name and numeral in a key), `tests/wizards/create_song/` (with `test_tune_fitting.py`, the wizard's use of it), `tests/interface/tracker/` (the tracker), `tests/math/`, `tests/caching/`, `tests/app/` (the program as a
whole: the command line, every example, the demos), `tests/rules/` (the rules about the code's shape) and `tests/tools/` (the
tools of `internal_tools/` and `user_scripts/`). Every folder has an `__init__.py`, and a new test goes in the folder of the
package it tests. `tests/support/` holds the helpers the tests share and the parallel runner, imported as
`tests.support.ui_testing` and the like. `tests/data/demo_sources/` holds
the data the demos were written from, and `tests/data/sample_sets/` the sets made to test the program,
like the two with values out of range. Tests are split by feature, each a file of its own, and the
shared helpers are modules beside them:

- **Every example alone.** `tests/app/test_every_example.py` gives each example set a class of its own, which reads and renders the
  example once (`tests/support/example_renders.py`) and runs on it every check that holds of each example: each a function in the
  module of what it checks (`check_exports` in `tests/app/test_examples.py`, `check_round_trip` in `tests/importers/test_midi_import.py`,
  `check_timeline` in `tests/realtime/test_realtime.py` and the rest), listed in `CHECKS` there. A new check of every example is such a
  function, added to that list.
- **The model and playback.** `tests/model/test_song_files.py` (what a file refuses, and its title and
  author), `tests/model/test_song_patterns.py`, `tests/model/test_song_scenes.py`,
  `tests/model/test_song_generators.py`, `tests/engine/realizer/test_morphs.py`, `tests/engine/realizer/test_directions.py`,
  `tests/engine/realizer/test_grabs.py`, `tests/engine/realizer/test_grooves.py`, `tests/model/test_composition.py` (each composition class),
  `tests/math/test_length.py` (lengths as pairs, held to `Fraction`), `tests/model/test_sound.py` (sounds as
  tuples, held to the classes that say the same, and the rule that the render imports none of
  the classes), `tests/engine/test_clip_sounds.py` (a clip held as objects and held as sounds answers
  the same, on every clip of every example), `tests/model/test_pattern_notes.py` (a pattern's
  notes as the piano roll's bars, on `Pattern` alone), `tests/app/test_examples.py` (every example loads, plays and exports to every kind),
  `tests/app/test_demos.py`, `tests/app/test_cli.py` and `tests/model/test_corrections.py` (what opening corrects in
  a file's values, and what is still refused). They share the song-building helpers in
  `tests/support/song_testing.py` (`pat`, `lead`, `with_parts`, `clip`, `pitches` and `BASIC`) and the
  rendering helpers in `tests/support/rendering.py`: `as_setlist(data)` wraps old-style song data as a
  set, `setlist_from_data`, `song_from_data` (the one song of such data), `song_from_file`,
  `render_data`, `render_song(song, seed=)`, `render_file`, `estimate_data`, `is_demo` and
  `bare_document()`, a new `Document` with the starter pattern and its clip removed, for a test
  that builds a song from nothing. `tests/support/ui_testing.py` and `tests/support/rendering.py` both call
  `Memory.check_every_answer()`, so every document a test makes works each remembered answer out
  again after any change and fails the test with `StaleAnswer` if the answer kept was wrong
  (`tests/caching/test_memory.py` tests the memory itself, checking and not). The same switch makes a
  document check what it shares: the data its objects keep, the snapshots in its undo history,
  and that every undo leaves what loading the snapshot would (`.claude/tracker/SHARED.md`, "Undo and
  redo"). `tests/model/test_kept_data.py` tests the kept data and `Setlist.restore`, and holds the rule
  that data and objects share no list or dictionary. A test of what happens without the checks
  turns them off with `Memory.check_every_answer(checks=False)` and on again when it ends.
- **Real-time playback.** `tests/realtime/test_realtime.py`: every example's timeline against its MIDI
  export tick for tick, the engine on a stepped clock with recording outputs, and the short
  lag test, a few seconds of the Entertainer through the real Realtime Sender Process, allowed
  ten milliseconds because the suite loads the machine, run on the immediate driver, and the same few seconds through the
  timestamped driver's recording outputs. `tests/realtime/test_scheduled_engine.py` tests the timestamped driver's engine on a
  stepped clock, every way of taking events back and the same random plays heard alike by both engines, and
  `tests/realtime/test_coremidi.py` the CoreMIDI port on macOS through a destination of the test's own, so nothing is heard. It also runs
  `tests/support/sender_under_capture.py` in an interpreter of its own, which starts the process with
  a `sys.stderr` like Textual's capture in place, since that failed the spawn and
  only the first spawn of an interpreter can show it. The long report is `py_legacy/internal_tools/realtime_report.sh`,
  and `py_legacy/internal_tools/iac_check.sh` plays out of a real IAC bus, neither part of the suite.
- **Chains in three places.** `tests/engine/realizer/test_chain_places.py`: a clip's, its scene's and its track's
  chains running in that order, a chain named twice running twice, and a file's old single chain.
- **Density, Swell and Articulate.** `tests/engine/realizer/test_shapes.py`: the ramp over time, the strength of
  each place in a bar, each shape on a bar of sixteenths, which of a generator, a clip and a
  scene wins, and what a file refuses.
- **Grabbing a chord's root.** `tests/engine/realizer/test_grab_roots.py`: a grab takes the root of a chord in root
  position, inverted and voice-led.
- **Chords.** `tests/model/test_chords.py`: a step's tensions and borrowed scale type, what a file refuses of both, and a chord
  spelled in a scale; `tests/interface/tracker/test_tui_chords.py` the pattern editor's Scale and Tension rows and the Chord dialog.
- **Keyswitches.** `tests/engine/realizer/test_keyswitches.py`: an instrument's map and lead and what a file refuses of both, a step's
  slots played as the instrument's notes with ties, a groove and a lead, nothing touched by transpose or a generator, and which
  exports and routes carry them; `tests/interface/tracker/test_tui_keyswitches.py` the Keyswitch Map and its note picker, the Keyswitch row
  and its dialog, named or numbered, and the piano roll's key, refusal and lights.
- **Inversions.** `tests/model/test_inversions.py`: each inversion played, what a file refuses, and the
  roll's ghosts; `tests/interface/tracker/test_tui_inversions.py` the editor's row.
- **Chords.** The Chords generator, in its three modes. Progression mode, `tests/engine/generators/test_progression.py`: each
  chord moving a figure, sharps and flats, inversions, Every, drum patterns left alone, what a file refuses, and the chords'
  numerals, names and the named progressions matched to a scale. Follow Progression mode,
  `tests/engine/generators/test_follow_chords.py`. Its Voicing, `tests/engine/generators/test_voice_leading.py`: each chord voiced
  nearest the one before, the range, the root kept in the bass, a range nothing fits, and what a file refuses.
  `tests/interface/tracker/test_tui_chords_generator.py` tests its page in each mode, and `test_tui_progressions.py` the chord
  editor.
- **Strum.** `tests/engine/generators/test_strum.py`: each direction, the spread in milliseconds at two tempos, fade,
  upstroke strings, loose timing from a seed, which of a generator, a clip and a track wins, and
  what a file refuses.
- **Guitarify.** `tests/engine/generators/test_guitarify.py`: Shape's voicings by tuning, position, capo and strings, single notes
  left, made power chords and scale chords, each stroke, accents, Let ring, spread, fade, loose timing from a seed, the bar
  following the song's bars under each Restart, the ready-made bars, and what a file refuses; `tests/interface/tracker/test_tui_guitarify.py`
  its editor and the editor of its bar of strokes.
- **Glide, Shorten, Rush and Drag.** `tests/engine/realizer/test_step_rows.py`: glides, short notes, the glide
  amount, a row's own step, rushes and drags and the two together, and what a file refuses.
- **The Hocket.** `tests/engine/generators/test_hocket.py`: the turns going round the pool, a rest passing none, a
  chord passing whole, a track's own notes besides, the source unchanged and taking no turn, a
  muted source, Restart, and the source following a track's rename.
- **Restart.** `tests/engine/realizer/test_restart.py`: every clip, on new scene and whole song on the generators
  that follow time, Voice leading's chord before carried on, and a
  generator starting every clip from what it was handed.
- **Time settings.** `tests/model/test_time_settings.py`: the one list of times, bars read and measured
  by the song's time signature in a drift, a shape and an arp, and the field they share.
- **Drift.** `tests/engine/generators/test_drift.py`: positions in every direction, what a drift does to velocity,
  probability, degrees, scale and root, and that every clip
  naming one hears the same picks.
- **Draws.** `tests/engine/realizer/test_draws.py`: each direction, blank slots, the Use Draws rows, a step's and a scene's
  resets and every track drawing from one draw in track order; `tests/engine/realizer/test_step_statements.py`: Stop When,
  Restart When and Mute When; `tests/engine/realizer/test_bypass_when.py`: the Bypass When tables; `tests/engine/realizer/test_finished_sounds.py`: a looping clip cut to its scene once.
- **The MIDI import.** `tests/importers/test_midi_import.py`: every file in `examples/midi/` and every
  example set exported as MIDI, imported into a new set, played and exported again, plays the
  same notes at the same tempos, or the import warns of what it changed (`round_trip` in
  `importers/comparison.py`, all in memory), with smaller tests on MIDI files built in memory
  of the reading, the keys, the voices, the scenes and patterns, the CCs and the names, and
  `tests/data/sample_sets/cc_sweeps.yml`, which sweeps every CC the import takes.
  `py_legacy/internal_tools/import_check.py` (`py_legacy/internal_tools/test_all_sample_midi_against_import.sh`) prints the same as a
  report. `tests/importers/test_batch_import.py` tests the batch importer. `tests/interface/tracker/test_tui_import.py` tests the tracker's side: the main screen's Import cell,
  the picker and the import dialog.
- **Live editing.** `tests/interface/tracker/test_tui_playback.py`'s `TestLiveEditing`: each Live response heard at
  its moment, typed digits heard once settled, an edit a key made heard once it settles with no tick and a
  typed digit waiting longer, a clip made to loop keeping its scene playing, a scene
  inserted above and a track renamed, an edit that can't render, another song made current, and the
  play's random parts kept; `TestArrangePlayback` holds the song playing on through pages and the
  refusal to delete, and `TestClipPagePlayback` the preview stopping with its page.
- **Drawing and the collector.** `tests/interface/tracker/test_tui_look.py`'s `TestPageViewSendsOnlyChangedLines`:
  the page's view making again only the lines that changed, a style alone included;
  `tests/interface/tracker/test_garbage.py`: what the tracker keeps frozen, and what it let go still collected.
- **The built-in synths.** `tests/realtime/test_synthesis.py`: the Synthesis Process's engine, drums and tables and when
  built-in sound may start, none of it opening the sound card; `tests/model/test_built_in_sound.py`: a built-in instrument's
  kind, latency and sound in the set; `tests/realtime/test_built_in_routing.py`: built-in routes, the built-in port, sounds
  reaching their instruments, taking back and ending notes, and a sender whose Synthesis Process cannot start.
- **FluidSynth.** `tests/realtime/test_fluidsynth.py`: FluidSynth found, started, waited for and ended,
  with a fake process and fake ports; `tests/interface/tracker/test_tui_playback.py`'s `TestFluidSynthPlayback` the
  transport's channels, program changes and starting; `tests/interface/tracker/test_tui_silent_instruments.py` the
  warning when a set opens with instruments that can't sound.
- **The PDF export.** `tests/exporters/test_song_printing.py`: a song made into what the PDFs print, the tracks merged
  and read as a lead sheet, the keys, the sections and their repeats, and the tracks taken by default, from `tests/data/pdf_export/printed.yml`.
  `tests/exporters/test_chord_chart.py`: the chord chart's cards, voicings and pages.
  `tests/exporters/test_chord_changes.py`: the Chord Changes pages' moves, voicings and words.
  `tests/exporters/test_piano_roll.py`: the roll's stretches, rows, lanes, strip and pages.
  `tests/exporters/test_pdf_export.py`: the packet file, the Chord Sequence's bars and keys, and `export_pdf.sh`'s options.
- **The WAV export.** `tests/exporters/test_wave_fluidsynth.py`: only the tracks through FluidSynth, their sounds,
  the temporary MIDI file removed, the WAV normalized, the refusals, and the tracker's question.
- **The development and research tools.** A tool of `internal_tools/` that ships nothing has one quick check of its main path,
  since a broken tool fails loudly when it is run: the files of `tests/tools/` named after a tool, and
  `tests/genres/`, which puts `py_legacy/internal_tools/analysis_and_generation/` on the path. The tools whose output ships or decides what
  is tested keep their full tests: `tests/tools/test_bump_version.py`, `tests/tools/test_demo_summary.py`,
  `tests/tools/test_stage_docs_site.py`, `tests/tools/test_wizard_songs.py`, `tests/tools/test_test_map.py` (the map decides which
  tests the commit check runs) and `tests/tools/test_constants_by_module_tool.py` (the fixer rewrites source in the commit check).
- **The title and the start screen.** `tests/interface/tracker/test_title_card.py`: the title on black at moments the test chooses (the
  letters' width and waves, the scanner's sweep and shading, the address, the prompt's pulse, the fade to black), and
  the start screen shown only when asked on a plain launch, until ENTER, and the demo's name that scrolls after the title (its words, its letters and its crossing).
- **A batch video's stage.** `tests/interface/tracker/test_batch_stage.py`: the READY box's room, the frame's cells from the edge in, the
  track's order, the pulse's tail and its turning and colour at a change of scene, the box growing, the fade to black and
  the opening cut to black; `tests/interface/tracker/test_tui_playback.py`'s `TestBatchVideoLaunch` the launch from title to quitting.
- **The documentation website.** `tests/tools/test_stage_docs_site.py`: the guide staged as the front page,
  the links between the pages, and the sidebar made from the guide's tables, listing every chapter in
  `docs/` once. VitePress itself is never run by the suite, which fetches nothing.
- **General MIDI.** `tests/exporters/test_general_midi.py`: drums on channel 10, each track on a channel of
  its own going round after the fifteenth, its instrument's sound as a program change or none,
  muted tracks left out, and what a file refuses of an instrument's sound.
- **The Sound dialog.** `tests/interface/tracker/test_tui_sound_dialog.py`: General MIDI's families and their flyouts, the search of every sound, and a sound tried once through FluidSynth's stand-in, a run in its sound or a drum on the drum channel.
- **Loudness from section to section.** `tests/wizards/create_song/test_loudness_steps.py`: a player's trade of loudness for a much denser part, who is left alone, and the wizard's song as written and as made.
- **The wizard's songs compared.** `tests/tools/test_wizard_songs.py`: each subgenre's usual songs then every choice once on each genre's first subgenre, a song's hash the same for the same choices, a line a choice, a song that cannot be made said in its line, and a genre that is not one refused. `py_legacy/internal_tools/wizard_songs.sh` itself is run by hand, before and after a change that should leave the wizard's songs alone.
- **Drum breaks.** `tests/wizards/create_song/test_breaks.py`: each break as written, a break cut up slice by slice, a song that plays one, and the wizard's choice of a break and its cut.
- **The wizard shows every choice.** `tests/rules/test_wizard_shows_choices.py`: every method of `WizardChoices` that changes a choice is called from the wizard's screens, but for the few listed there with the reason, so that a choice built underneath cannot be left off the page .
- **The song wizard's choices.** `tests/wizards/create_song/test_wizard_choices.py` (each choice kept, refused and made into a song) and
  `tests/wizards/create_song/test_wizard_effect.py`, the rule that every choice the wizard offers changes the song made (each run checks every choice on one subgenre of each genre, the day's own in turn by date, `subgenre_of_the_day`, the user's choice for speed): a new field of
  the wizard is added to `every_choice` there in the same change .
- **The exporters and generators**, named after them, with `tests/app/test_matrix.py` as an end-to-end
  example of the classes underneath the tracker and `tests/engine/generators/test_generator_list_steps.py` checking
  that no list generator lets a rest use up a value. `tests/exporters/test_exporter.py` tests the base class
  every exporter shares, with two small kinds of export made for the test, and holds the rule
  that every exporter class is listed in `exporters/exports.py`.
- **The tracker.** The `tests/interface/tracker/test_tui_*.py` modules run the real program with no terminal and press
  keys, each page and component in a module of its own (`tests/interface/tracker/test_tui_main_page.py`, `tests/interface/tracker/test_tui_file_page.py`,
  `tests/interface/tracker/test_tui_pattern_sections.py` and the like; no rule on a file's size, the aim is that a page's tests are found by its
  name), a helper or base class that several of them share in `tests/support/` (`tests/support/page_testing.py`,
  `tests/support/pattern_editor_testing.py`), through `UITest` in `tests/support/ui_testing.py`: `a_song()` builds a document to work on,
  `press(*keys)` presses keys by their names, letting the tracker handle each with
  `settle()` (`pilot.pause(0)`) rather than `pilot.pause()`, whose wait for the computer to go idle
  cost a fiftieth of a second a key and far more with the suite's classes side by side; `UITest`
  refuses to start a real FluidSynth, so a test that plays through it gives its transport a stand-in,
  as `tests/interface/tracker/test_tui_playback.py` does; `type(text)` types text and fails unless a prompt,
  a picker's search, a list's search or the notes' text is open to take it (each screen
  and dialog answers `takes_text()`), so that a name typed at the wrong moment can't press a
  page's keys letter by letter, `select_field(label)`
  reaches a settings field by its label, `text()` is what the screen shows and `fixed_text` the
  part of a template that doesn't change. `press_at_once(name)` presses a key that only moves a
  cursor without waiting for the event loop, about 25 times faster, and `drawn()` is what the page
  drew straight after, which a test that walks a whole page uses; `leaf_pages()` lists every page
  class that isn't there to be subclassed, for the rules about every page. A test class that
  starts the tracker another way, like on a file that needs corrections, overrides `make_app()`.
  `tests/interface/tracker/test_tui_fields.py` tests the kinds of settings field, on a stand-in and on two real pages,
  `tests/interface/tracker/test_tui_arrange_drawing.py` tests what draws Arrange, apart from the page,
  `tests/interface/tracker/test_tui_arrange_details.py` Arrange's details view, `tests/interface/tracker/test_tui_scene_view.py` Scene View and the Inset Window, `tests/interface/visualizers/test_visualizer_choices.py` the
  visualizer modes a set and a song choose and hide,
  `tests/interface/tracker/test_tui_step_editors.py` runs one set of checks on the offsets editor and the groove
  editor, which share `OneRowEditor`,
  `tests/interface/tracker/test_tui_document.py` tests `Document` on its own, `tests/interface/tracker/test_tui_named_edits.py` its
  renaming, copying, deleting, moving and sorting on every section,
  `tests/interface/tracker/test_tui_shapes.py` the Density, Swell and Articulate pages and the settings pages' sections,
  `tests/interface/tracker/test_tui_named_lists.py` the same five on two pages that list named things, and
  `tests/interface/tracker/test_tui_named_item_pages.py` the name, the rename and the undo questions on a few pages that show one named thing,
  each with a rule that every such page keeps no way of its own, `tests/interface/tracker/test_tui_history.py` the undo
  history and the document stepping through it, `tests/interface/tracker/test_tui_undo.py` undo where a page's undo does something of its
  own, and `tests/interface/tracker/test_tui_corrections.py` the Corrections dialog, from the Open page and when
  the tracker starts.
- **The visualizer.** `tests/interface/visualizers/test_visualizers.py` tests the modes on their own, the frames' sizes,
  a resize, the drawing of big pixels, and that the lava lamp stays dark in silence, glows where a
  track plays and never passes its ceiling or jumps in brightness, even with 64 tracks hitting at once, and `tests/interface/tracker/test_tui_visualizer.py` the visualizer on
  Arrange; `tests/tools/test_preview_visualizer.py` tests the preview tool's parts that need no port.
- **The rules.** `tests/rules/test_slots.py`, `tests/rules/test_keyword_only.py`, `tests/rules/test_revisions.py`
  (every method that changes a stored object is written under `@notes_change`),
  `tests/model/test_setting.py` (every setting is described once, reading and setting refuse a
  value in the same words, and every generator's every setting refuses what its description refuses, worked out from the
  description, so that a generator's limits have no test of their own), `tests/model/test_row_descriptions.py` (every row of a pattern is described
  once, and a file, the setter and the editor's rows agree),
  `tests/rules/test_message_constants.py`, `tests/rules/test_pyflakes.py`, `tests/rules/test_yaml_safety.py`,
  `tests/rules/test_doc_paths.py`, `tests/rules/test_diagrams.py`, `tests/model/test_renames.py`,
  `tests/rules/test_keybindings.py` (the rules of `interface/tracker/keybindings.py`),
  `tests/interface/tracker/test_tui_help_keys.py` (every key a page's help names is bound on that page, every bound
  key is one of its own class's bindings and no key reaches two bindings in one place, found by
  touring every page and walking its cursor to every place, whose `TestKeyTour` holds `.claude/reference/KEYMAP.md` to what the tour finds, rewritten by `py_legacy/internal_tools/key_map.sh`), `tests/tools/test_bump_version.py` and the
  rule tests in `tests/interface/tracker/test_tui_keys_shown.py`, `tests/interface/tracker/test_tui_help.py`, `tests/interface/tracker/test_tui_look.py` and `tests/interface/tracker/test_tui_undo.py`. `tests/interface/tracker/test_key_table.py`
  tests how keys are bound, and `tests/tools/test_show_keys.py` the tool that prints them.

