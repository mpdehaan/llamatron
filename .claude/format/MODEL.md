# The Model

Reference notes for Claude, one part of `.claude/format/`: the packages, the music values, the grid of finished clips, the composition objects, reading and writing a set, corrections, renames and the tests of the model. `CLAUDE.md` says which part to read for which work.

Reference notes for Claude on what a set file holds, how it's played into clips and how those are
written out, one short section per topic. `.claude/STYLE.md` holds the rules; this is the detail.
`GUIDE.md` says the same things for people using the tracker, and `docs/ARCHITECTURE.md` for people
reading the code. What a choice here replaced is in `.claude/DECISIONS.md`. When a module moves
or is renamed, the paths in this file move with it: `tests/rules/test_doc_paths.py` checks that every
source path named in the documents exists.

## Packages

The package is `llamatron`, in `src/llamatron`, split by what each part is for.

- `music/`: the values everything works with (`Note`, `Chord`, `Scale`, `Held`, `TimeSignature`
  and the MIDI ranges), and `Sound`, the same notes as the tuples a render makes.
- `support/`: the plumbing (`Rational`, `Length` for lengths as pairs inside a render, file names, safe YAML loading, `random_source`, the
  version, and `Revised` and `Memory`, which keep work done from an object until the object
  changes).
- `composition/`: the objects a set file stores.
- `playback/`: what plays them into a grid.
- `grid/`: that grid of finished clips.
- `exporters/`: the exporters of Live sets and MIDI files, each an `Exporter`.
- `importers/`: the MIDI import, a MIDI file made into a song of the set (`.claude/format/EXPORTERS.md`, "The MIDI import").
- `generators/`: the clip generators.
- `realtime/`: real-time playback below the tracker (`.claude/features/REALTIME_PLAYBACK.md`).
- `tui/`: the tracker (`.claude/tracker/`).
- `visualizers/`: the visualizer's modes, which Arrange's clip area shows while a song plays in real time (`.claude/features/VISUALIZER.md`, "The visualizer").
- `tutorial/`: the video tutorial, which drives the tracker from outside its pages (`.claude/features/RECORDING.md`, "The video tutorial").
- `strings/`: every piece of text the program shows or raises, one module for each way the text
  is used (`.claude/STYLE.md`).
- The top level keeps only the entry points (`cli.py`, `__main__.py`).
- New modules go in the package that says what they're for, and a new group of them gets a
  package of its own.

## Notes and rests

- `Note` (`src/llamatron/music/note.py`) is immutable and built from a name, an octave and a
  required length. `Rest(length)` is the same but silent.
- Lengths are fractions of a whole note, so `0.25` is a quarter note and `0.5` a half note.
- Notes compare and hash by MIDI number and length rather than spelling, so
  `Note('C#', 4, 0.25) == Note('Db', 4, 0.25)` and `Note('B#', 3, 0.25) == Note('C', 4, 0.25)`,
  while `name` keeps the spelling it was given.
- Notes outside the MIDI range can't be constructed, and that includes `Cb0` and `G#10` and
  above. Double sharps and double flats aren't supported.
- The octave is read with `get_octave_number()`, the pitch with `get_midi_number()` and the
  spelling with `get_name()`. `Note`, `Rest`, `Degree`, `Chord`, `Scale` and `Held` keep their
  fields private behind getters and stay immutable by having no setters.
- `half_step(n)` returns a new note of the same length, spelled with flats if the note's name has
  a flat and with sharps otherwise.

## Octave numbers

- llamatron's own octave numbers start at `C0`, MIDI note 0, so the highest note is `G10` (127).
- Every DAW labels octaves differently. Live, the only DAW implemented so far, labels MIDI note 0
  as `C-2` (`LIVE_OCTAVE_OFFSET`).
- The song file stores llamatron's own numbering, from `MIN_OCTAVE` (0) to `MAX_OCTAVE` (10).
- The tracker shows octaves through the set's `octave_labels` setting (`OctaveLabels`, `live` by
  default or `llamatron`), which `Song.shown_octave` and `Song.stored_octave` convert with, so
  Live's labels run from -2 to 8 on screen.
- A file whose `version` is older than `LLAMATRON_OCTAVES_SINCE` (1.0.30) stored Live's
  numbering, and `Song.from_data` moves its octaves up by `LIVE_OCTAVE_OFFSET` before checking it.
  A file with no version is read as it is.

## Chords, scales and time signatures

- `Chord` (`src/llamatron/music/chord.py`) is an immutable group of notes, and chords compare by
  their sorted MIDI numbers and lengths. A chord's `length` is its longest note's, and that's how
  long it occupies in a clip. Chords hold only `Note`s so far.
- `ChordType` values are half steps above the root. `Note.to_chord(typ)` builds a chord upward
  from the note using `half_step`, so every note gets the root's length and chord tones follow
  its sharp or flat rule rather than proper chord spelling: C minor contains `D#`, not `Eb`.
- `chord.py` imports `Note`, so `to_chord` imports from `llamatron.music.chord` inside the method
  to avoid a circular import.
- `Scale` (`src/llamatron/music/scale.py`) is an immutable root note and `ScaleType`, and
  `Scale.note_at(degree=, scale_notes=, half_steps=, length=, velocity=, glide=)` is the note a
  degree plays, which `Degree.to_note` asks for and which playing a pattern asks for directly, so
  that the note is made once. `Scale.sound_at`, with the same settings, is the same note as a
  sound, the tuple a render makes (`.claude/format/PLAYBACK.md`, "Sounds and lengths in a render"), worked out from the
  root's MIDI number without making a note. `ScaleType` values are one octave of half steps
  including the root (`0`).
- Scale types with identical values are Python enum aliases, so `ScaleType.AEOLIAN is
  ScaleType.MINOR` and `list(ScaleType)` includes only the first name.
- `TimeSignature` (`src/llamatron/music/time_signature.py`) is immutable, with `beat_length()`
  the bottom number's note, or three of them in a compound meter (a top number of six or more
  divisible by three, like 6/8), and `starts_a_beat(time)`.

## The grid of finished clips

- `ClipGrid` (`src/llamatron/grid/clip_grid.py`) stores the finished clips a song renders into:
  one `Clip` per `(ClipRow, ClipColumn)`, in a dict nested as `{row id: {column id: clip}}`.
- The `grid` package holds one class per file, with `Clip`, `ClipRow`, `ClipColumn` and `Control`
  beside `ClipGrid`, and the arithmetic on a clip's positions in `positions.py`. Its setters
  check their values with the `check_` functions of `composition/checks.py`, the one checks
  module.
- A `ClipRow` is one scene's clips and a `ClipColumn` is one track's, named so that they can't be
  confused with the composition model's `Scene` and `Track`, which are what the file stores. The
  exporters hold the grid as `grid`, never `song`.
- The ids exist because names don't have to be unique. Rows and columns get theirs from `add_row`
  and `add_column`: each grid counts rows and columns separately from 0 in the order they're
  added, and the id is `None` before that, so a row or column can only join one grid. Clips get a
  unique id when created.
- `ClipRow`, `ClipColumn` and `Clip` compare by identity, and grid methods reject rows and
  columns that aren't in the grid.
- `tempo_at(row)` resolves as row, then grid. `scale_at(row, column)` resolves as clip, then row,
  then grid. Both read the current values each time.
- Clips deliberately have no tempo, because Live has no per-clip tempo for MIDI clips. Only
  `ClipGrid` has a default tempo (120, minimum 10), and a row tempo of `None` means it uses the
  grid's. Tempo is in quarter notes per minute.
- A song's `scale` can be `None`, so `scale_at` can return `None`.

## A finished clip

- `Clip.notes` is a list where each position is a `Note`, `Chord`, `Rest` or `Degree`, played in
  order. The setter also accepts shorthand and converts it to objects: `'E4'` is a `Note`, `3` is
  a `Degree`, and each dash is a quarter note of rest, whatever the `note_length`.
- A clip holds its positions one of two ways. `Clip(notes=...)` keeps the objects it was given,
  which is how a test or a tool builds one. `Clip(sounds=...)` keeps the tuples a render makes
  (`.claude/format/PLAYBACK.md`, "Sounds and lengths in a render"), which is what playback, the generators and the
  exporters' timing work on. `get_sounds()`, `resolved_sounds()` and `played_sounds()` give
  either clip as sounds, and `get_notes()`, `resolved_notes()` and `played_notes()` as objects.
  A clip of sounds asked for `get_notes()` makes the objects once and keeps the objects from
  then on, so that the list is the clip's own and can be appended to. `total_length()`,
  `section(start=, end=)` and `repeated(times)` take and give `Rational`s either way.
  `tests/grid/test_clip_sounds.py` runs every method both ways, on clips written by hand and on every
  clip of every example.
- `Clip.trim(n)` keeps the first `n` positions in place and returns the clip.
- `Clip.length` uses whole-note units. `None` ends the clip after its last position, and any
  other value adds silence or cuts notes off to fit.
- `Clip.section(start, end)` and `Clip.repeated(times)` cut and repeat clips by time.
- A `Clip`'s `controls` are `Control(time, number, value, slide)` CC values, which sections,
  repeats and generators carry along.
- A `Clip` has a `_groove` set last by the renderer (`get_groove`, `set_groove`, which raises
  `ValueError` `ERR_NOT_A_GROOVE` for anything but a `Groove` or `None`).
- In a finished clip, a note whose gate reaches exactly to the next note is an ordinary position,
  a shorter one is followed by one rest per step, and a longer one is a `Held`
  (`src/llamatron/music/held.py`), whose sound lasts its own length while the next position
  starts after its place.

## Late binding

- Binding is as late as possible, and new features keep it that way.
- A `Degree` (`src/llamatron/music/note.py`, numbered from 1) stays a degree until `ClipTree`
  converts it with `song.scale_at(scene, track)`, so a clip follows its scene's or song's scale.
- A `Note` or `Degree` with a length of `None` takes `Clip.note_length`, which
  `clip.resolved_notes()` and `clip.resolved_sounds()` fill in without changing the clip.
- Missing scales and lengths raise `ValueError` at render, before any file is written.
- Generators keep degrees as degrees.

## The composition model

- `src/llamatron/composition/` holds the objects a set file stores, each a `LlamaData` subclass
  with `to_data()` and `from_data(data, where, song)`, which checks the data and keeps settings
  the file leaves out as `None`, meaning their defaults.
- The classes are `Setlist`, `Song`, `Scene`, `ClipSlot` (what one track plays in one scene),
  `Track`, `Pattern`, `NamedScale`, `Chain`, `Groove`, `ArpSettings` and `AutoRatchetSettings`.
  The last two are checked when the file is read, like the rest, so an error names the
  generator, and again when a chain makes the generator, since settings can be built without a
  file.
- Each setting is described once (`composition/setting.py`): a `Flag`, a `WholeNumber` with its
  range, a `Choice` from a fixed list, `Text`, or a `Checked` with a check of its own, which
  holds the setting's one check and its error message. Each class's module lists its settings
  in the order a file writes them, as `SETTINGS = described(...)`, and both `from_data` and the
  setter ask the description (`check_settings`, `settings_held`, `SETTINGS[name].check`), so the
  two can't disagree. A `Length` is a whole number or fraction of whole notes with a longest
  allowed. A description also knows the allowed value nearest a wrong one (`nearest`): the
  nearest end of a range, the longest length, a choice's default, or `NO_NEAREST_VALUE`, and
  `check_held(data)` raises with a `Correction` of the data when there is one ("Corrections"
  below). A check
  that spans two settings, like a track's lowest octave not above its highest or a morph
  needing two repeats, stays written out in the class. `tests/composition/test_setting.py` tests the kinds
  and holds the rule that every name in a class of setting names has one description.
- Objects refer to each other by name, and the song looks names up.
- Every check raises `InvalidValue` (`composition/invalid_value.py`), a subclass of
  `ValueError`, whose message says only what's wrong with the value, like `repeat must be an
  integer from 1 to 999, got 1.5`, so the tracker can show it beside a field.
- `from_data` wraps its checks in `with reading(where):` (`composition/checks.py`), which turns
  an `InvalidValue` into a `SongFileError` that starts with where in the file it was, like
  `song (verse), scene 2, track (bass): ...`. So `SongFileError` means only that a file can't be
  loaded, and one raised by a part read inside another passes through with its own place.
- `GENERATOR_SETTINGS` in `composition/generator_settings.py` lists each generator's settings
  class, so new generators need adding there and using in an `examples/` song, which a test
  enforces.
- Every `LlamaData` and every `NamedItems` is a `Revised` (`support/revised.py`): the object
  carries a revision from one clock, which no other object has, and which moves with every
  change, because the constructor calls `note_change()` and every method that changes the object
  is written under `@notes_change`. A copy is a new object with a revision of its own.
  `tests/rules/test_revisions.py` checks the rule.
- `kept_data()` is what `to_data()` returns, built once and kept until the object changes, for
  whoever only reads it: the undo history, and the comparisons behind the unsaved mark. It is
  shared and never changed. An object that holds others (a `Scene`, a `Song`, the `Setlist`, a
  `NamedItems`) puts its kept data together from its parts' each time, since a clip or a track
  changes without its scene or song changing (`data_built_anew` and `data_as_kept` in
  `composition/llama_data.py` are the two ways a holder takes a part's data). `own_copy` copies
  the lists a setting holds, so that data and objects share nothing.
- `Setlist.restore(data)` makes the set what data it kept earlier says, through the same reading
  as `from_data`, keeping every item whose kept data equals the data. `tests/composition/test_kept_data.py`
  tests it, with every example restored to another example's data.
- `tests/composition/test_composition.py` tests each class, and `tests/support_code/test_llama_data.py` checks every
  subclass defines both methods.

## Named sections

- Each named section (scales, patterns, each generator kind (arps, AutoRatchets, drifts, progressions, voice leadings, strums, euclids, densities, swells, articulates), chains, grooves, tracks and songs)
  is a `NamedItems` (`composition/named_items.py`): items by name in the file's order, with
  `has`, `get`, `find`, `names`, `add`, `replace`, `remove`, `rename`, `move` and `sort`, which
  check names and raise `InvalidValue`, and which know whether the file wrote the section
  (`is_written`, `fill_in`).
- `Song`'s and `Setlist`'s section methods (`add_item`, `rename_item` and so on) delegate to it
  and add only what crosses sections, like updating references on a rename and removing a track's
  clip slots.
- The per-kind getters (`get_pattern`, `get_track_names`) are one-line forwarders kept because
  they read well.

- **A set takes another set's songs in** with `Setlist.take_in(other)`, which the song wizard does with the set it made
  (`.claude/features/MACRO_COMPOSER.md`, "The Wizard's Choices"): a thing of the other set whose name this set uses for
  something different is renamed there as a duplicate is (`naming.copy_name`), everything that names it following; a thing
  that is the same in both is shared; the rest is added through `restore`, so nothing of this set is rebuilt; and each song
  taken in is filled in like a loaded one, so that an undo and a redo leave the same data. A song keeps what the wizard was
  told in its `wizard` setting (`Song.get_wizard_choices`, `set_wizard_choices`), a mapping kept as data of the song's own.
  `Setlist.replace_song(name=, other=)` replaces a song entirely in its place: the old song goes with whatever only it used
  (what nothing used before stays), and the other set's song is taken in under the old name. `remove_unused()` takes out
  everything nothing names, which a set made for one song does before it is taken in.

## Reading and writing a set

- `Setlist.read_file(path)` reads a set file with `safe_yaml.load_safely`, and
  `Setlist.write_file(path)` writes the same format, recording the version, with the YAML layout
  in `composition/setlist_writer.py` (`dump_setlist`).
- The format is mainly for machines, but it stays readable for version control diffs where it
  can.
- Reading is strict: `read_file` and `from_data` stop at the first wrong value with a
  `SongFileError`, and `Setlist.restore`, which undo uses, reads the same way.
- `Setlist.new()` is a new set with one song called `untitled` (`MSG_DEFAULT_SONG_NAME`) and a
  starter pattern, `pattern-1` (`MSG_NEW_PATTERN_NAME`, `starter_pattern()`: `STARTER_PATTERN_STEPS`
  sixteenths with `STARTER_DEGREE` every `STARTER_STEPS_PER_BEAT` steps and a blank gate), which
  the song's `track-1` plays in `scene-1`, so that a new set plays at once and shows what a
  pattern is. Both can be deleted, like the scale, `scale-1` (`DEFAULT_SCALE`), C major.
- `new_setlist()` and `new_song()` are their data. `Setlist.fill_in_defaults()` gives a loaded
  set every setting a new one has so that saving writes them all, which `Document` calls on every
  set it holds. `Document(setlist=..., path=...)` takes a `Setlist`, never data.
- YAML is only ever read through `safe_yaml.load_safely`, which uses PyYAML's `CSafeLoader` when
  PyYAML was built with libyaml and `SafeLoader` otherwise. Both only make plain data, so loading
  a file can never run code.
- `yaml.load` with any other loader, `full_load`, `unsafe_load` and custom loaders are never
  used, and `safe_yaml.py` is the only module allowed to name a loader, which
  `tests/rules/test_yaml_safety.py` checks.
- PyYAML reads about ten times faster with libyaml (`yaml.__with_libyaml__`). INSTALL.md says
  how to get it, and everything works without it.

## Corrections

- A value a file holds that can't be used, and that has an allowed value near it, comes with a
  `Correction` (`composition/corrections.py`): the dictionary that holds the value, the key, the
  setting's name, the value found and the value used, with `apply()`, `described()` and the
  place in the file, which `reading(where)` sets as the error passes through.
  `InvalidValue.get_correction()` and `SongFileError.get_correction()` return the correction, or
  `None`.
- What is corrected: a whole number outside its range takes the nearest end, a length longer
  than its longest takes the longest, and a choice outside its fixed list is left out so that the
  default applies (`LEFT_OUT`), except a clip's morph style, which has no default and takes the
  first. A pattern's row is one correction however many steps need one (the row's description,
  through `nearest_step_value` and `_row_correction` in `composition/pattern.py`), and so are a groove's
  cells and an arp's offsets.
- A pattern's `+=` row adding more than the narrowest `allowed_inc_max` of the songs that play it is
  corrected to that limit, the row being one correction (`Setlist._check_adds_within_limits`,
  `held_add`), since the limit is a song's and the row a set's, so the check comes after the songs.
- What is still refused: a name that doesn't exist, an unknown setting, the wrong type or
  structure, a track's CC numbers, an AutoRatchet's counts, a scale's root or type, and two
  settings that don't fit each other.
- `Setlist.read_file_corrected(path)` and `from_data_corrected(data=)` return the set and the
  corrections made: a copy of the data is read strictly, and each failure that has a correction
  is applied before reading again, up to `MOST_CORRECTIONS`. A problem with no correction raises
  `SongFileError` as ever. Only a file that a strict read refused is read this way, and neither
  the data given nor the file is changed.
- `tests/composition/test_corrections.py` tests every setting and row that has a correction, what is still
  refused, and the two sets in `tests/data/sample_sets/`.

## Renames

- Renaming anything never breaks anything: every object that refers to another by name (clip slots
  name patterns, chains and tracks; chains name generators; the song and scenes name scales; the
  song, scenes and tracks name grooves) is updated by the rename, which `Song.rename_item` and
  `Setlist.rename_item` do with `rename_references(section=, old=, new=)`.
- Each class says once which of its settings hold the name of an item of which section, as
  `REFERENCES`, like `ClipSlot`'s `{Section.PATTERNS: (pattern, morph_to), Section.CHAINS: (chain,),
  Section.TRACKS: (grab_track,)}`, with `Scene`, `Song` and `Track` the same way. `LlamaData`
  reads it for both questions: `names_item(section=, name=)` is whether the object's own
  settings name the item, and `rename_references` rewrites the settings that did and passes the
  rename on to `referring_parts()` (a scene's clips, a song's scenes and tracks, the set's chains
  and songs). Only what named the item takes a new revision. A `Chain` names generators by its
  steps, so it answers both itself, and a `Scene` moves a renamed track's clip to the new name.
- What uses an item is asked the same way at every level: `clip_slots_naming`, `scenes_naming`,
  `tracks_naming`, `songs_naming` and `chains_naming` on the `Setlist`, the first three on a
  `Song`, and `clip_slots_naming` on a `Scene`, each taking `section=` and `name=`. A new setting that
  names something is one entry in its class's `REFERENCES`, and the rename and the uses follow.
- `tests/composition/test_renames.py` checks that every kind of rename keeps the song loading and playing the
  same, that every declared reference is a real setting, and that in every example what uses an
  item is what its rename changes.
- Names are what the file uses to refer to objects, and they have to be unique within a section,
  but a name isn't an object's identity as such: a format with integer ids and names alongside
  would be allowed if a need appeared, as long as renames stay safe.
- The one known exception is that probability rolls and random directions are seeded from the
  track's name, so renaming a track changes what they roll. That's an open question in
  `dev_notes/IDEAS.yml`.

## Tests of the model

The tests of the model, playback and the exporters, the helpers they share in
`tests/support/song_testing.py` and `tests/support/rendering.py`, and the rules every test follows are in
`.claude/TESTING.md`.
