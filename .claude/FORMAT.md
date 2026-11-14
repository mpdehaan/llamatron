# The model, the file format, playback and export

Reference notes for Claude on what a set file holds, how it's played into clips and how those are
written out, one short section per topic. `.claude/STYLE.md` holds the rules; this is the detail.
`GUIDE.md` says the same things for people using the tracker, and `docs/ARCHITECTURE.md` for people
reading the code. What a choice here replaced is in `.claude/DECISIONS.md`. When a module moves
or is renamed, the paths in this file move with it: `test/test_doc_paths.py` checks that every
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
- `importers/`: the MIDI import, a MIDI file made into a song of the set ("The MIDI import" below).
- `generators/`: the clip generators.
- `realtime/`: real-time playback below the tracker ("Real-time playback" below).
- `tui/`: the tracker (`.claude/TRACKER.md`).
- `visualizers/`: the visualizer's modes, which Arrange's clip area shows while a song plays in real time (`.claude/TRACKER.md`, "The visualizer").
- `tutorial/`: the video tutorial, which drives the tracker from outside its pages (`.claude/TRACKER.md`, "The video tutorial").
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
  sound, the tuple a render makes ("Sounds and lengths in a render" below), worked out from the
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
  ("Sounds and lengths in a render" below), which is what playback, the generators and the
  exporters' timing work on. `get_sounds()`, `resolved_sounds()` and `played_sounds()` give
  either clip as sounds, and `get_notes()`, `resolved_notes()` and `played_notes()` as objects.
  A clip of sounds asked for `get_notes()` makes the objects once and keeps the objects from
  then on, so that the list is the clip's own and can be appended to. `total_length()`,
  `section(start=, end=)` and `repeated(times)` take and give `Rational`s either way.
  `test/test_clip_sounds.py` runs every method both ways, on clips written by hand and on every
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
  needing two repeats, stays written out in the class. `test/test_setting.py` tests the kinds
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
  `test/test_revisions.py` checks the rule.
- `kept_data()` is what `to_data()` returns, built once and kept until the object changes, for
  whoever only reads it: the undo history, and the comparisons behind the unsaved mark. It is
  shared and never changed. An object that holds others (a `Scene`, a `Song`, the `Setlist`, a
  `NamedItems`) puts its kept data together from its parts' each time, since a clip or a track
  changes without its scene or song changing (`data_built_anew` and `data_as_kept` in
  `composition/llama_data.py` are the two ways a holder takes a part's data). `own_copy` copies
  the lists a setting holds, so that data and objects share nothing.
- `Setlist.restore(data)` makes the set what data it kept earlier says, through the same reading
  as `from_data`, keeping every item whose kept data equals the data. `test/test_kept_data.py`
  tests it, with every example restored to another example's data.
- `test/test_composition.py` tests each class, and `test/test_llama_data.py` checks every
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

## Reading and writing a set

- `Setlist.read_file(path)` reads a set file with `safe_yaml.load_safely`, and
  `Setlist.write_file(path)` writes the same format, recording the version, with the YAML layout
  in `composition/setlist_writer.py` (`dump_setlist`).
- The format is mainly for machines, but it stays readable for version control diffs where it
  can.
- Reading is strict: `read_file` and `from_data` stop at the first wrong value with a
  `SongFileError`, and `Setlist.restore`, which undo uses, reads the same way.
- `Setlist.new()` is a new set with one song called `untitled` (`MSG_DEFAULT_SONG_NAME`) and a
  starter pattern, `pattern 1` (`MSG_NEW_PATTERN_NAME`, `starter_pattern()`: `STARTER_PATTERN_STEPS`
  sixteenths with `STARTER_DEGREE` every `STARTER_STEPS_PER_BEAT` steps and a blank gate), which
  the song's `track 1` plays in `scene 1`, so that a new set plays at once and shows what a
  pattern is. Both can be deleted, like the `C Major` scale.
- `new_setlist()` and `new_song()` are their data. `Setlist.fill_in_defaults()` gives a loaded
  set every setting a new one has so that saving writes them all, which `Document` calls on every
  set it holds. `Document(setlist=..., path=...)` takes a `Setlist`, never data.
- YAML is only ever read through `safe_yaml.load_safely`, which uses PyYAML's `CSafeLoader` when
  PyYAML was built with libyaml and `SafeLoader` otherwise. Both only make plain data, so loading
  a file can never run code.
- `yaml.load` with any other loader, `full_load`, `unsafe_load` and custom loaders are never
  used, and `safe_yaml.py` is the only module allowed to name a loader, which
  `test/test_yaml_safety.py` checks.
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
- `test/test_corrections.py` tests every setting and row that has a correction, what is still
  refused, and the two sets in `test/sample_sets/`.

## The format's rules

### A set

- A file is a set, held by `Setlist` (`composition/setlist.py`), like the songs played in one
  concert.
- The set owns the shared sections, `scales`, `patterns`, each generator kind, `chains` and
  `grooves` (`SETLIST_SECTIONS` in `composition/sections.py`), and `songs`.
- Each song is a `Song` (`composition/song.py`) with its own `tempo`, `time_signature`, `scale`,
  `seed`, `groove`, `genre`, `live_responsiveness`, `registers`, `tracks` and `scenes`
  (`SONG_SECTIONS`), written in that order under `songs:` by `setlist_writer.py`. A song's
  `live_responsiveness` (`LiveResponsiveness`: next_bar, clip_restart or asap, next_bar by default and
  written only when set, `Song.get_live_responsiveness`), the user's design, is when an edit made while
  the song plays in real time is heard on what plays: at the next bar, at each playing clip's next
  pass, or at once. A song's `genre` is text only for people, blank by
  default (`Song.get_genre`, `Setlist.get_genres`), the user's design, which the demo
  tables show; every example has the broad genre the user approved.
- A song keeps a back-reference to its set and forwards lookups of shared things to it, so
  playback asks the song for a pattern or scale and doesn't know about the set.
- Songs are a `NamedItems` section like any other (`Section.SONGS`).
- A file whose `version` is older than `SETLISTS_SINCE` (1.0.39) held one song.
  `holds_one_song(data)` and `as_setlist_data(data=, song_name=)` turn it into a set of one song
  named after the file's stem, and `test/demo_sources/make_demos.py` writes sets the same way.
- Error places name the song first, like `song (verse), scene entry 2, track (bass): ...`, and a
  song setting reads `song (verse): scale: ...`.
- Each demo is its own file with one song, a new set has one song called `untitled`, and the
  set's name (its file stem) and a song's name are independent.

### Title, author, description and notes

- `title` and `author` are optional text at the top of a file, only for attribution when sets
  are shared, and blank by default.
- `description` is one optional line saying what the set is, like the tune it plays (`The
  Wellerman`, `a C major scale`), which `internal_tools/demo_summary.py` shows for each example, the
  user's design.
- `notes` is optional text of any length, written as a YAML `|` block straight after the three
  so that it reads as plain text, and kept when the tracker saves, which comments aren't. A
  file saved before `NOTES_SINCE` (1.0.155) held the long text under `description`, and
  `_as_a_set_is_written` reads such a file's `description` as its `notes`; a file with no
  version is read as it is.

### Protected sets

- `protected` (`SetlistSetting.PROTECTED`, default false, `DEFAULT_PROTECTED`, written last among
  the settings) marks a set whose own file the tracker never writes over.
- `Document.save` raises `SongFileError` (`ERR_FILE_PROTECTED`) when `file_is_protected()`, which
  is true only for the set's own existing file, so a protected set that has no file yet still
  saves the first time.
- `Document.save_as`, which the tracker's Save as uses, turns a copy's protection off, because a
  copy the user makes is theirs. Plain `save(path=)` keeps it, so tests can re-save the examples.
- Every set in `examples/` is protected, and `test/demo_sources/make_demos.py` writes them that
  way. A new set isn't.

### Defaults for everything

- Every setting in the file has a default when it's missing, including `tempo` (120), `tracks`
  and `scenes`, so an empty file is an empty song and a file from an older version still loads.
- This is a lasting rule: new fields get a reasonable default rather than migration code, unless
  the format changes structurally.

### Everything inline

- Every object is stored with its settings inline, never in a separate section, a permanent rule
  for every object type.
- So `tracks` is named tracks with their settings, like `bass: { transpose: 2, cc: [74, ~, ~, 1]
  }` or `kick: { drum: true }`, in order, and a track with none is `lead: {}`.
- Every generator setting is named, YAML stays flat with `{}` only one level deep, and clip slots
  always use the hash form inside a scene's `tracks`.

### Patterns

- A pattern holds `steps` and one list per row, mirroring the pattern editor: `degree`, `gate`,
  `dot`, `accidental`, `octave`, `chord`, `inversion`, `velocity`, `probability`, `glide`, `ratchet`,
  `ratchet_offset`, `grab`, `cc1` to `cc4`, `slide`, and for the registers `ax_note` to
  `dx_note`, `ax_velocity` to `dx_velocity` and `ax_add` to `dx_add`.
- Each row is described once, in `ROW_DESCRIPTIONS` (`composition/row_descriptions.py`), in the
  order a file writes the rows: a `RowOfNumbers` with its lowest and highest, what a blank step
  plays as and whether a blank changes nothing, a `RowOfToggles`, a `RowOfChoices`, the Gate's
  `RowOfLengths`, and `RowOfDegrees`, `RowOfOctaves`, `RowOfChords` and `RowOfNoteMoves` for the
  rows with rules of their own. A description says what a step may hold (`check`,
  `problem_with`, `nearest`), what a blank step holds, how a file writes the row, whether a
  rest keeps the value when a note is cleared (the CC rows, Slide and every register row), and
  what the row does in a drum pattern.
  Reading a file, `Pattern.set_value` and the pattern editor's rows all ask it, and playback
  still reads the plain lists. `test/test_row_descriptions.py` tests it.
- The on or off rows, `glide`, `tie`, `grab` and `slide` (`is_on_or_off()`), always hold `true`
  or `false` and never null, and the text UI shows them as a mark or a blank.
- The registers' note and velocity rows (`RowOfRegisterUses`, `RowOfNoteMoves`) hold `1` to add
  the register's value, `-1` to subtract it or `0` for neither (`RegisterUse`), the user's
  design, where they were on or off rows. A file from before holds `true` and
  `false`, which read as `1` and `0`, and a null reads as `0`, so the pattern always holds one
  of the three numbers (`read`, the description's one way in) and writes a row only when a
  step differs from the row's blank.
- Rows of all blanks are left out.
- Nothing is packed into one value, so there's nothing to parse apart, except that lengths stay
  as whole numbers or fractions like `5/16`, because decimals can't hold 1/3. Decimals are
  refused for step sizes and gates.
- `drum: true` puts note letters in `degree`, and has no chords.
- A pattern needs at least one step. A new pattern is one bar long, `Song.steps_in_a_bar()` at
  the set's step size, or `NEW_PATTERN_STEPS` (16) when a bar isn't whole steps.

### Time signatures

- A song has a `time_signature`, written like `6/8` (default `4/4`, `DEFAULT_TIME_SIGNATURE`).
- A pattern can set its own, blank by default meaning the song's, exactly like its step size,
  because patterns are shared by every song of the set and late binding is the rule.
- A time signature is graphical in llamatron: nothing in the render reads it, no note moves
  and no length changes. Its one use in playback is real time, where a launch by hand waits
  for the next bar of the song's time signature ("Real-time playback" below).
- The pattern editor marks the steps that start a beat and shows the signature on the header's
  second line.
- The exporters write it as metadata: one meta event at the start of the MIDI file, each stem and
  each clip tree file (a clip's own if its pattern has one), the Live set's main track control and
  its automation as Live's one-number code (`_live_time_signature`, 201 for 4/4), and each Live
  clip's own signature.
- Scenes don't carry one. An optional scene setting could be added later with no migration.

### Entry size

- `entry_size` on a song (`SongSetting.ENTRY_SIZE`, blank by default, written after the time
  signature) and on a pattern (`PatternSetting.ENTRY_SIZE`, blank meaning the song's, whose blank
  means one step) is how long a note placed on the piano roll lasts.
- It is a whole number or fraction of whole notes up to `MAX_GATE`, like a gate, and
  `Song.entry_size_for(pattern)` resolves it. Nothing in the render reads it.
- The Song page sets the song's, and the piano roll's `E` picks the pattern's from
  `STEP_SIZE_CHOICES`, or the song's.
- A placed note of whole steps is written as a degree and ties (`Pattern.place_note`), and only
  an entry size shorter than a step writes a gate.

### Notes as bars

- `PatternNotes` (`composition/pattern_notes.py`), which `Pattern` inherits, is what a pattern
  knows about its notes as the bars a piano roll draws, each a note with its gate and the ties
  after it: `note_span`, `covering_notes`, `partial_cell` and `chord_tones` read them, and
  `draw_note`, `place_note`, `cut_gate_before`, `split_note`, `lengthen_note`, `shorten_note` and
  `cycle_accidental` change them, through `set_value` and `clear_sound`.
- How many steps a gate reaches depends on the step size, which is bound late, so each method
  that reads a gate as steps takes `step_size` from its caller, and `chord_tones` takes the
  `NamedScale`. Nothing there needs the tracker, so a wizard or a pattern generator can use it.
- `fraction_text` in `composition/checks.py` writes an exact length the way a file holds it,
  which `written_length` reads back.
- `test/test_pattern_notes.py` tests it on `Pattern` alone, at several step sizes.

### Steps and gates

- Every step of a pattern lasts its `step_size`, which the pattern can set and otherwise comes
  from the set's `step_size` (default 1/16), so a pass lasts steps times step size.
- A step with a note sounds for its `gate`, a whole number or fraction of whole notes up to
  `MAX_GATE` (4), or one step if blank, made dotted (`d`, half as long again) or a triplet (`t`,
  two thirds) by its `dot` row.
- A gate can run past later steps but is cut at the end of the pattern, though glide still runs
  slightly into the next pass.
- A blank degree is an empty step, which is a rest.

### Ties

- A `tie` on an empty step keeps the note that played just before it, in play order, sounding to
  the end of the tied step. A step with a note can't have a tie, which the file refuses.
- The ties win over the gate, so a note and three ties of 1/16 is a quarter note whatever its
  gate says, and the bar the editor draws is what plays. The editor's description line says when
  a gate is overridden.
- `_tied_to` in `playback/pattern_player.py` does it: the last piece is lengthened, so a tie
  holds the last slice of a ratchet, and where the gate reached past the ties the pieces share
  the tied span equally, so a ratchet keeps its count.
- A tie after an empty step or a dropped note is silence.
- Ties at the start of a pass are the one thing gates can't do. `PatternPlayer.play_pass` returns
  a `Pass` with `tied_from_before`, and `ClipSlotPlayer` lengthens the note the passes so far ended
  with (`_tied_on`, making it a `Held`).
- So a tie carries across repeats and loops of a clip but not into a new scene's clip, where it's
  silence, because clips are separate in Live.
- A morph's target's ties work inside the target, and ties at the start of a pass follow the
  clip slot's own pattern.

### Octaves

- Absolute, with no track offset, numbered from C0 as MIDI note 0, so `5` with degree 1 of C
  major is MIDI 60, and the defaults are 5 for notes and 3 for drums.
- The tracker shows them in the set's `octave_labels`, Live's by default, where that same octave
  is 3.
- A degree past the top of the scale wraps up an octave, for a scene with a smaller scale.

### Chords

- Chord symbols come in two kinds, listed in `FIXED_CHORDS` and `SCALE_CHORDS` in
  `composition/file_format.py`, in the order the editor offers them.
- Named symbols like `M`, `dom7`, `m7b5` and `M13` are exact half steps from the note, so they
  can leave the scale.
- Plain numbers `5`, `3`, `7`, `9`, `11` and `13` stack every other scale note, so they follow
  scale changes. A bare number always means a scale chord, which is why dominants are `dom7` and
  so on.
- Every symbol fits the editor's 5-character cell.
- A chord's parts are worked out in one order, the same on a pattern's step and a progression's chord (the user's design,
  `composition/chords.py`): the scale type it borrows (a step's `chord_scale` row, a progression's `scales`), on the clip's
  root, in place of the clip's scale; the degree and the sharp or flat, which give the root in that scale; the symbol (a
  step's `chord`, a progression's `qualities`, named symbols only there); and the tensions on top (`tension`, `tensions`):
  `b9`, `9`, `#9`, `11`, `#11`, `b13`, `13` (`TENSIONS`, half steps above the root). A step holds its tensions as a tuple,
  lowest first, written as a list; a single note takes none, and a drum pattern has neither row. Only a scale type is
  borrowed, never a named scale, so that a change of root carries every chord with it (the user's choice for now).
- On a step, tensions are added above the chord's root (`_with_tensions` in `playback/pattern_player.py`), and the step's
  scale type replaces the clip's for its degree, its scale chord and its register moves (`_scene_scale_at(kind=)`).
- In a `Progression`, a note of the figure is carried to the same place in the borrowed scale; then, where it is a scale
  note at a place the chord names (`replaced_places`: the third, fifth and seventh by the quality, the notes between by the
  tensions), it becomes the chord's moved root plus those half steps; a chord of the figure has its tensions added on top.
  A progression none of whose chords sets any of the three moves its notes the short way, as before (`_plain`).
- `spelled_chord` says what a chord comes to in a `NamedScale`: its short name, like `A7(b9)`, its long name and its notes,
  spelled on the letters a chord stacks. `test/test_chords.py` and `test/test_progression.py` (`TestLeavingTheScale`) test
  these, `test/test_tui_chords.py` the pattern editor's rows and the dialog.

### Probability and seeds

- Probability is rolled at render once per repeat and ratchet slice, from the song's `seed` when
  it has one, so that a seeded render plays the same every time.
- The default is no seed (`DEFAULT_SEED` is `None`): an unseeded song draws from Python's own
  random stream, seeded by the system once when the program starts, so every export is a new
  take, and the Song page shows `(none)`.
- `random_source(seed)` (`src/llamatron/support/random_source.py`) is the one place that decides
  this, for probability, directions and arps.
- `SongRenderer(song, seed=n)` renders with a seed in place of the song's, which is what the
  CLI's `--seed` passes and what `internal_tools/compare_exports.py` uses (`COMPARISON_SEED`, 1). Tests
  that check a specific random outcome set a seed.
- A note that probability drops is silence in its place, however long its gate: a gate that
  reached over the next note holds nothing, the steps up to the next note are rests, and the
  next note plays as normal. Until 1.0.136 such a take stopped the export, since a rest can't
  be held. `test/test_song_patterns.py` tests the take that keeps the note and the take that
  drops it.
- It deliberately doesn't use Live's per-note probability.

### Inversions

- A pattern's `inversion` row (`RowOfInversions`), the user's design, holds 1, 2 or
  3 on a step with a chord, or nothing for root position: that many of the chord's lowest notes
  move up an octave as it plays, never all of them, so a triad plays 3 as 2
  (`Sound.inverted`, which `PatternPlayer` applies to every slice, a grab's chord too, and the
  Progression generator to its chords). A drum pattern refuses one. `Pattern.chord_tones` gives
  the roll's ghosts where the inversion plays them, the root among them an octave up. The editor's
  `InversionRow` is blocked on a step with no chord. `test/test_inversions.py` and
  `test/test_tui_inversions.py` test it.

### Ratchet and glide

- `ratchet` splits a step into equal notes in the same time, from `MIN_RATCHET` (1) to
  `MAX_RATCHET` (16).
- `glide` runs a note slightly into the next one, which a synth with glide turned on slides
  across, and it does nothing before a rest or the same pitch.
- `ratchet_offset` moves each ratchet slice further along the scale, or by half steps in a drum
  pattern, by up to `MAX_RATCHET_OFFSET` (24) either way. Both limits were the pattern editor's
  alone until each row got one description, and a file is now held to them, with a correction
  on opening for a value outside.

### Scenes

- A scene launches clips and has no length of its own: it lasts as long as its longest clip that
  doesn't loop.
- A clip plays its pattern `repeat` times and stops. `loop: true` repeats it until that longest
  clip ends, and every clip in a scene looping is an error at build.
- A scene's `tempo_start` and `tempo_end` ramp the tempo across its `repeat`.
- A scene's `repeat` runs from `MIN_REPEAT` to `MAX_SCENE_REPEAT` (999) and a clip's to
  `MAX_CLIP_REPEAT` (9999), in a file and on the Scene and Clip pages alike, with a correction
  on opening for a value outside.

### Morphs

- A clip with a repeat above 1 can `morph_to` a second pattern in a `morph_style` (`left`,
  `right` or `middle`) across its repeats, and the second pattern is looped or cut to match the
  first. There's no way to morph across a scene's repeats.
- A morph's target follows the clip's `direction` when the clip has one, like the clip's own
  pattern, and otherwise its own pattern's, keeping its place across the repeats in a `StepOrder`
  of its own with its own seed (`MORPH_DIRECTION_SEED`), so that a random direction can't change
  what the clip's own pattern draws.
- The target never grabs, and uses registers without adding.
- A pattern with no notes still morphs, since its steps are rests that carry CC values and
  register changes.

### Registers

- The song has four registers, `AX`, `BX`, `CX` and `DX` (`RegisterName`). Their names are fixed.
- `registers:` holds the settings that differ from the defaults, like `AX: { maximum: 3, wrap:
  true }`, with `default`, `minimum` and `maximum` from -127 to 127 (defaults 0, 0 and 10, in
  order minimum <= default <= maximum), `at_limit`, `reset_each_scene` and `allowed_inc_max` (1 to 127,
  default `DEFAULT_ALLOWED_INC_MAX`, 20, enough for every example written before it), the most
  a step may add or take away, the user's design. The pattern editor's `+=` rows
  stop there (`Setlist.allowed_inc_max_for_pattern`: the narrowest of the songs that play the
  pattern), while a file is still read from -127 to 127.
- `at_limit` (`AtLimit`, default `stop`) is what an add past an end does (`Register.added`):
  `stop`, `reset` to the default, `overflow` to the other end (what `wrap: true` did, and how a
  file saved before reads it, `_read_wrap`), `overflow_right` (only past the maximum, stopping at
  the minimum), `overflow_left` (the reverse), or `pick_random` from minimum to maximum, drawn
  from a generator of the render's own (`REGISTER_SEED_OFFSET` in `playback/song_renderer.py`),
  unseeded with the song. `reset_each_scene` (default false) sets the register back to its
  default as each scene first starts (`SongRenderer._resets_of`, `WrittenScene.is_first_play`).
- A step's `ax_set` sets AX to a value before anything adds to it, blank leaving it as it is
  and 0 setting it to 0, held between the register's minimum and maximum and never wrapped
  (`Register.held`). A step's `ax_add` adds to AX as it plays. Both happen even with no note,
  when probability drops it or when a condition silences it, and once for a ratchet.
- `ax_note` moves the note along the scale by AX's value, up for `1` and down for `-1`, which
  drum patterns can't use, and `ax_velocity` adds AX's value to the velocity for `1` or takes
  it off for `-1`, keeping the velocity from 1 to 127 (`_used_values` in
  `playback/pattern_player.py` sums each register's value times its row's sign).
- Within a step: sets, then adds, then uses (`+Note`, `+Vel` and the bound velocity), then the
  conditions and probability decide whether the note sounds. Going past an end does what
  `at_limit` says, dropping what is left over.
- The condition rows `ax_bx`, `ax_cx` and `ax_dx` (`CONDITION_ROWS`, `Comparison`) each hold
  `<`, `>`, `=` or nothing: AX compared with that register, as the step sees them, after its own
  changes. A note sounds only when every condition on its step holds (`_conditions_hold`), and
  a step that fails sounds nothing, all its ratchet slices together, a chord whole. Only a note
  can hold one, so clearing a note clears its conditions. A condition never stops a register
  change, so the counting play still finds every change, the user's rule.
- Registers are shared by every track. `SongRenderer` plays each clip once with a
  `RegisterRecorder` to collect changes (the same play that finds lengths, since registers only
  change pitches, velocities and whether a note sounds), a `RegisterTimeline` applies them in
  time order and then track order, and the finished clips read it with a `RegisterReader`
  (`src/llamatron/playback/registers.py`). The counting play runs only when some pattern sets or
  adds (`Setlist.changes_registers`).
- Values carry from scene to scene. A scene's `reset: [AX, DX]` sets those back to their defaults
  as it first starts, not on its repeats.
- A note pushed outside the MIDI range goes to the nearest octave that fits.

### Directions

- `direction` on a pattern sets the order its steps play in: `forward`, `reverse_a`,
  `reverse_b`, `alternate`, `pendulum`, `random`, `brownian` or `eitherway`, as the Cirklon names
  them.
- `direction` on a clip overrides its pattern's, and a morph's target's.
- Whichever order the steps play in, a pass lasts as long as the pattern does, with the last
  step cut to fit, so a direction can't change how long a clip or scene is.
- Positions carry on across repeats, and chosen directions use the song's seed with a separate
  generator, so they can't change what probability rolls.

### Grooves

- A groove (`composition/groove.py`, `Groove`) is a row of `cells`, each a signed percentage of a
  `cell_length` (default 1/16, `DEFAULT_GROOVE_CELL_LENGTH`) that moves a note late or early,
  from `MIN_GROOVE_AMOUNT` (-50) to `MAX_GROOVE_AMOUNT` (50) so that notes can't change order,
  with 1 to `MAX_GROOVE_CELLS` (32) cells.
- The row repeats its own length from the start of the scene and a note takes the cell its time
  falls in (`Groove.offset_at`, `moved`), whatever its pattern's step size or direction. It
  doesn't read the time signature.
- The factory grooves (`FACTORY_GROOVES`, named in `FactoryGroove`: `none`, `swing 54` to `swing
  66`, `8th swing 58` and `8th swing 66`, `push`) are defined in code and never written.
  `Setlist.get_groove` returns a copy of one, so nothing can change them, and
  `check_groove_name` keeps their names from the set's own `grooves` section (`Section.GROOVES`,
  written after the chains).
- The song's `groove` (default `none`, `SongSetting.GROOVE`, written only when set) and a
  scene's or track's `groove` (a name, or `false`, checked by `check_groove_choice`) choose one.
- `Song.groove_at(scene=, track=)` uses `groove_for`: a `false` anywhere means no groove, and
  otherwise the track's name wins, then the scene's, then the song's. A straight groove like
  `none` gives `None`.
- `SongRenderer.render` sets the groove on each finished grid `Clip` last (`Clip.set_groove`), so
  generators, grabs and lengths never see it.
- `exporters/timing.py` applies it: `timed_events` moves each note's start and keeps its gate
  (the clip's end still cuts), `control_points` moves each CC value with its step, and
  `grab_source.py` reads with `grooved=False`.
- Renaming a groove updates the song, scenes and tracks, and `uses_of` in `tui/uses.py` lists
  what uses one ("Renames" below). A song that sets no groove names the default one, `none`,
  which `Song.names_item` says, so the factory groove `none` counts that song as a use.
- `test/test_grooves.py` and `test/test_tui_grooves.py` test it.

### Follow action and Launch together

- A clip's `follow_action` (`ClipSlotSetting.FOLLOW_ACTION`, one of `FOLLOW_ACTION_CHOICES`:
  `with_scene`, `next` or `off`, `FollowAction`, Live's word, shown as Advance on the clip page,
  the user's name for it) is what the clip sends down in real-time playback when it finishes,
  the user's design. No export reads it. Blank means the set's
  `default_follow_action` (`SetlistSetting.DEFAULT_FOLLOW_ACTION`, same choices, default
  `with_scene`, `DEFAULT_FOLLOW_ACTION`), written only when set, so the demos stay as they
  are; `Setlist.follow_action_of(clip_slot)` resolves it. The clip page's Advance field shows
  the resolved value as the clip's own, with no "(default)" choice, and the Set File page's
  Default follow action field sets the set's.
- "With Scene" sends a start to the clip directly below when the whole scene is done; "Next"
  sends it the moment the clip's own repeats end, whatever the rest of the scene is doing;
  "Off" sends nothing, so the track falls silent until something launches it. A scene is done
  when every clip launched in it that doesn't loop has finished its repeats, which is the
  export's length for the scene: an empty slot is done from the start and counts as "With
  Scene", and a looping clip never finishes on its own, so it doesn't hold its scene, and
  loops on until the scene below starts on its track. A scene whose every clip loops is never
  done and waits for the human, while the export goes on refusing it. Once, one
  looping clip held its scene, and the registers demo, whose kick and hat loop in every scene,
  never left its first scene in real time; the user changed the rule so that Space on the
  corner plays every demo to its end.
- A scene's `launch_together` (`SceneSetting.LAUNCH_TOGETHER`, `Scene.launches_together`,
  default true, `DEFAULT_LAUNCH_TOGETHER`, written only when false) says what a start reaching
  one of its clips does: true launches every clip of the scene together, false starts that
  clip alone, each clip waiting for the clip directly above it. The Scene page's Launch
  together toggle sets it, and Arrange draws `MSG_LAUNCH_APART_MARK` (`┆`) after the name of a
  scene with it off. Space on a scene's name launches every clip whatever anything says. With
  the defaults every demo plays start to finish as Live's Arrangement View plays the export,
  which is the test to hold the player to. The playing itself comes with the tracker's
  real-time pages.

### Instruments

- `instruments` is a named section of the set (`Section.INSTRUMENTS`, written after the grooves,
  `composition/instrument.py`, `Instrument`), each a `device`, the name of a MIDI output port as
  the port lists itself or blank until chosen, and a `channel` from `MIN_CHANNEL` (1) to
  `MAX_CHANNEL` (16) as people number them, default `DEFAULT_CHANNEL` (1), the byte sent being
  one less. Two instruments may share a device and a channel. An instrument's `gm_sound`
  (`InstrumentSetting.GM_SOUND`, `MIN_GM_SOUND` 1 to `MAX_GM_SOUND` 128, none by default), the
  user's design, is the sound the General MIDI export gives its tracks, and no
  other export reads an instrument. A `device` of `*FluidSynth` (`FLUIDSYNTH_DEVICE` in
  `composition/file_format.py`, `Instrument.uses_fluidsynth`), the user's design,
  plays through FluidSynth, which the tracker starts ("Real-time playback" below): its `channel`
  is ignored and its `gm_sound` is sent as a program change, which no MIDI port's instrument is
  sent. Every example plays this way as it comes: its `real_time` is on, every unmuted track has
  an instrument on `*FluidSynth`, the melodic ones with a sound and the drum tracks sharing one
  called `drum kit`, and every track that plays only drum patterns is a drum track, which
  `test/test_examples.py` holds them to. A new set has no instruments.
- A track's `instrument` (`TrackSetting.INSTRUMENT`, in `Track.REFERENCES`) names one, or is
  blank for none, which leaves the track out of real-time playback. Renaming an instrument
  updates the tracks, and `tracks_naming` lists the uses.
- The visualizer settings, the user's design: the set's `visualizer` and a song's `visualizer` (`SetlistSetting.VISUALIZER`,
  `SongSetting.VISUALIZER`, a mode's name or left out) name the mode Arrange's visualizer key shows first, the song's over
  the set's (`Setlist.visualizer_for`); the set's `hidden_visualizers` (`SetlistSetting.HIDDEN_VISUALIZERS`, a list of modes'
  names, written only when it holds one) are the modes the key, `[` and `]` and Cycle leave out. The names are
  `VISUALIZER_NAMES` in `composition/file_format.py`, held to the modes by `test/test_visualizer_choices.py`, so that a set is
  read without the visualizers. A visualizer setting is never refused, the user's rule, since modes come and go: anything
  that isn't a mode's name is made sensible as it's read and set (`sensible_visualizer`, `sensible_hidden_visualizers`), an
  unknown default becoming none and an unknown hidden mode dropped, with no correction asked about. A new visualizer setting
  follows the same rule.
- The set's `generator_order` (`SetlistSetting.GENERATOR_ORDER`, the user's design) is the order the Generators page lists
  every generator in, each entry `{kind: name}`, written only when set; it's never refused (`sensible_generator_order`, an
  entry that isn't a generator's kind and a name is dropped), `Setlist.ordered_generators` leaves out entries for generators
  gone and adds any it doesn't name after the rest, kind by kind, a rename keeps a generator's place and a copy comes straight
  after its original (`copy_item`). Nothing in the render reads it. `test/test_generator_order.py` tests it.
- The set's `real_time` (`SetlistSetting.REAL_TIME`, default `DEFAULT_REAL_TIME`, false) is the
  main screen's Real Time switch. `Document.add_instrument` turns it on with the first
  instrument, and `delete_named` turns it off with the last.

### Clip names

- A clip can have a `name` of its own (`ClipSlotSetting.NAME`, any text), which the Arrange grid
  shows and every export uses, as the Live clip's name and in the clip tree's file names.
- Without one it goes by its pattern's name (`ClipSlot.get_display_name`). Renaming a pattern doesn't
  touch it.

### Grabs

- A clip's `grab_track` names another track in the same scene, like the Cirklon's note grab.
  There's no `notes_from` or `source_pattern`.
- Each of the pattern's `grab` steps plays the note that track most recently started, at or
  before the step, after the other clip's chain, so a silent track gives the last note it played.
- It takes a chord's root, the note the chord was built on, which is the chord's first note
  however it's inverted or voice-led (`GrabSource`, `playback/grab_source.py`, reading the clip's
  sounds rather than its timed notes), the user's rule; it took the lowest note
  until inversions came. `test/test_grab_roots.py` tests it.
- A grab step with a symbol on its `chord` row plays that chord with the grabbed note as its
  bottom note (`PatternPlayer._chord_on`): a named symbol like `m7` adds notes exact half steps
  above the grabbed note, and a scale chord like `7` adds notes of the grabbing clip's scale
  above it, a grabbed note outside the scale keeping its distance from the scale note below.
  A blank `chord` plays the one note, which basslines need. A scale chord with no scale is
  refused as a degree is, and a note of the chord above the MIDI range is left out. A drum
  pattern has no chords.
- Nothing played yet leaves the step's own note, or silence on a step with none.
- The Grab row works on empty steps: the editor gives such a step the root in the default octave
  as a note of its own (`GrabRow`), and a file may hold a grab with no degree, which
  `Pattern.has_sound` counts as a note, the player plays as the grabbed note, and the roll
  draws on the root. A grab step can't hold a tie.
- The grabbing clip keeps its own rhythm, velocity and the rest, and its track's transpose,
  ratchet offset and note add still move the grabbed note along its scale. A morph's target
  doesn't grab.
- `SongRenderer` builds clips on demand and remembers them, so a grab just asks for the other
  clip, and a circle stops the render with a message naming the tracks.
- Lengths come from clips built without grabbing, because grabbing only changes pitches, which
  lets a clip grab from one that loops to fill its scene.
- The clip page refuses a grab that would go round in a circle, and pasting a clip drops one,
  using `Document.grab_circle`. Renaming a track updates grabs from it, and deleting one stops
  them.

### Scales

- `scales` holds named scales, like `main: { root: F, type: minor }`, and new sets have `C
  Major`. A name can be anything, so that what `main` is can be decided later.
- `scale` on the song, on scenes and on clip slots must be one of these names. Scales resolve as
  the clip slot's own (`ClipSlotSetting.SCALE`, the user's design), then the
  scene's, then the song's (`ClipSlotPlayer._scale_name`, which hands the name to the
  `PatternPlayer`), and patterns can't set one. `Setlist.scales_for_pattern` counts a clip's own.
- The song can have no scale, and degrees then raise an error at build that names the problem.

### Tracks

- A track's `transpose` moves every note on it along the scale at build, without changing
  patterns. It never applies to a drum pattern, and a track with `drum: true` never transposes at
  all.
- Its `lowest_octave` and `highest_octave` (defaults `MIN_OCTAVE` and `MAX_OCTAVE`, the lowest
  never above the highest, checked by `_check_octave_order`) are the octaves its instrument
  plays, which only the piano roll reads, to mark the rows outside them.
- A track's `mute: true` writes its clips as normal but switches the track off in the Live set,
  for tracks that other tracks only grab from, which the demos name with `SILENT`.
- A track's `cc` gives the CC number for each of a pattern's four CC rows, and `~` means that
  lane sends nothing on that track.
- Register binding, the user's design: a track's `cc1_register` to
  `cc4_register` (`CC_REGISTER_SETTINGS`) bind a CC lane to a register, and
  `velocity_register` binds the velocity, each a register's name or left out for none.
  - A bound lane that has a CC number sends the register's value held from 0 to 127, at the
    clip's start and whenever the value it would send changes while the clip plays, at the
    moment of the change, after every track's change then (`_bound_controls` in
    `playback/song_renderer.py`, `RegisterTimeline.changes_within` and `values_after`). A
    change that would send the value last sent sends nothing; a CC value of the clip's own at
    the same moment on that lane wins; a track with nothing in a scene sends nothing there, and
    its next clip catches up at its start. The values are ordinary controls of the clip, so
    every export and real-time playback carry them, and a groove moves them as it moves the
    clip's own.
  - A bound velocity is the velocity of a note whose Velocity is blank: the register's value as
    the step sees it, then `+Vel`, held from 1 to 127, so a binding never silences a note.

### CC rows

- CC rows send a value from 0 to 127 at the start of a step, and a blank sends nothing, so the
  last value holds.
- Rests can hold them too, ratchets don't repeat them and probability doesn't drop them.
- A morph uses the target's values where the target plays, and a direction moves them with their
  steps.
- A step with `slide` ramps each of its values to that lane's next value, as on the Elektron
  Monomachine. Glide is still only for notes.

### Generators and chains

- `arps` names arpeggiators and `auto_ratchets` names AutoRatchets, each with their settings.
- A clip slot, a scene and a track each hold `chains`, a list of chains by name (`check_chain_names`
  in `composition/chain.py`), the user's design. A clip runs its own, then its
  scene's, then its track's, each list in order (`SongRenderer.chains_of`), a chain listed twice
  running twice; each generator is counted along them all for its seed, so a clip with one chain
  draws as before. A clip's `chain`, one name, from a file saved before, reads as a list of one
  (`_read_chain`). `LlamaData.names_item` and `rename_references` handle a list of names.
- A chain is a list of steps like `arp: name` or `auto_ratchet: name`, with no settings of its
  own.

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
- `test/test_renames.py` checks that every kind of rename keeps the song loading and playing the
  same, that every declared reference is a real setting, and that in every example what uses an
  item is what its rename changes.
- Names are what the file uses to refer to objects, and they have to be unique within a section,
  but a name isn't an object's identity as such: a format with integer ids and names alongside
  would be allowed if a need appeared, as long as renames stay safe.
- The one known exception is that probability rolls and random directions are seeded from the
  track's name, so renaming a track changes what they roll. That's an open question in
  `dev_notes/IDEAS.md`.

## Playback and the command line

- `SongRenderer(song).render()` (`src/llamatron/playback/`) plays a song into a `ClipGrid`, with
  a `ClipSlotPlayer` for each clip slot and a `PatternPlayer` for each pass through a pattern. Tests use
  the helpers in `test/rendering.py`.
- `src/llamatron/cli.py` is the command line, installed as `llamatron`. There's deliberately no
  separate command for the tracker, and `python -m llamatron` is the same as the command.
- Without `--to` it opens the tracker, on a set if one is named. `--autoplay`,
  `--autoplay-quit-when-finished`, `--launch-for-recording` and `--max-seconds` make the tracker
  play the set on its own (`.claude/TRACKER.md`, "Launching to play on its own"); they need a
  set, and are refused with `--to`. Started plainly, it opens on the start screen, unless `LLAMATRON_NO_SPLASH=1` (`start_screen_wanted`).
- With `--to` it exports instead, as a Live set unless `--to` names another kind (`midi`, `stems`,
  `cliptree` or `gm`), so `--to` goes after the set's name. It exports every song of a set, or the one
  `--song` names, as `<set>_<song>` files beside the set's file, or in the directory `--out`
  names (`export_directory`, `export_song`).
- `--out`, `--template`, `--replace`, `--seed` and `--force` are refused without `--to`.
- A set file with values that have corrections ("Corrections") isn't exported: `read_set` prints
  each correction on stderr as `would change ...` and fails with `ERR_NEEDS_FORCE`. With
  `--force` it prints each as `changed ...` and exports the corrected set. The file is never
  changed.

## Exporters

- Exporters live in `src/llamatron/exporters`, with their tests directly in `test/`.
- Every kind of export is one class, a subclass of `Exporter` (`exporters/exporter.py`), which
  holds the directory, the grid and the name, checks for files in the way (`can_write`) and
  writes with `export()`. The class says what `--to` calls the kind (`KIND`, one of `ExportKind`)
  and what people are shown for it (`LABEL`), and takes one of two mixins for where its files
  are: `WritesOneFile` (`FILE`, `path()`) or `WritesManyFiles` (`FILES`, a glob pattern, and
  `FILES_SHOWN`). Both answer `shown_path`, `earlier_files` and `remove_earlier_files` as class
  methods, since they need no grid.
- `exporters/exports.py` lists the classes (`EXPORTERS`, by kind, in the order `--to`'s help
  lists them), with `EXPORT_KINDS` for the tracker's order, and its `make_exporter`,
  `shown_export_path`, `earlier_export` and `remove_earlier_export` ask the kind's class, so the command line
  and the tracker share them. Live is the main one and the default. A new kind, for another DAW
  say, is one class and its place in those two lists, and `test/test_exporter.py` fails if an
  exporter class is left out.
- Every exporter takes a `directory` and a `name` (the directory's own name when none is given).
  Only the Live set is built from a template, which `for_song` passes on and the other kinds
  have no use for.
- Every export, from the tracker and the command line alike, is a file beside the set's file
  named `<set>_<song>`
  (`export_name` in `exports.py`, like `foo_bar`) plus what it is, with no `output/` folder and
  no per-song folders, so the names are predictable and the exports of `examples/` are ignored by
  git (`examples/*.als`, `examples/*.mid`).
- A set has to be saved before it exports, since the name and the place come from its file.
- `earlier_export` finds a kind's files by their name or prefix (`stem_files_pattern`,
  `clip_files_pattern`), and `shown_export_path` is what people are shown: the file, or a pattern like
  `foo_bar_stem_*.mid`.
- Neither the Live writer nor the clip writer uses temporary files. Any future temporary files
  must use `tempfile`, be documented, and be removed when they're finished with.
- Note timing for every writer comes from `src/llamatron/exporters/timing.py`.
- `test/test_matrix.py` is an end-to-end example of the classes underneath the tracker.

### The MIDI kinds

- The four MIDI kinds are for other DAWs and players. `MidiSong` (`exporters/midi_arrangement.py`) writes
  one type 1 file, `<name>.mid`, with a tempo track and a track per llamatron track.
- `MidiStems` writes a file per track, `<name>_stem_<track number>-<track name>.mid`, each the
  full length of the song and each carrying the tempo changes.
- Both lay the scenes end to end using `ClipGrid.row_starts()`, the same arithmetic as Live's
  Arrangement View, so a track that plays nothing in early scenes starts with silence and every
  file lines up, and they leave out muted tracks.
- `MidiGeneralMidi` writes `<name>_gm.mid`, the single file for any General MIDI player: drum
  tracks on channel 10 (`DRUM_CHANNEL_BYTE`), every other unmuted track on the others in turn
  (`MELODIC_CHANNEL_BYTES`, round again after the fifteenth), and a program change first of each
  melodic track's instrument's `gm_sound`, which the grid's `ClipColumn` carries with whether the
  track is a drum track (`SongRenderer.gm_sound_of`). A track whose instrument has no sound sends
  none. `midi_track(channel=, program=)` writes either. `internal_tools/preview_midi.py` writes it, and
  `test/test_general_midi.py` tests it.
- `WaveFluidSynth` (`exporters/wave_fluidsynth.py`, `--to wav`, `<name>.wav`), the user's design, is the
  WAV export for anyone with no DAW: the General MIDI file of only the unmuted tracks whose instrument
  plays through FluidSynth (`ClipColumn.plays_through_fluidsynth`, set by
  `SongRenderer.plays_through_fluidsynth`), written into a temporary folder that is always removed, played
  by FluidSynth faster than real time with the SoundFont, then normalized to a peak 1 dB below full scale
  (`exporters/wave_level.py`, which `internal_tools/normalize_wave.py` shares). It refuses with
  `ERR_WAV_NEEDS_FLUIDSYNTH` or `ERR_NO_FLUIDSYNTH_TRACKS` before writing anything. The tests that export
  every kind leave it out, and `test/test_wave_fluidsynth.py` tests it with a stand-in for FluidSynth.
- Everything the MIDI writers share, the tick rate, `MidiEvent`, message building and
  `midi_track`, is in `exporters/midi_messages.py`.
- `ClipTree` (`src/llamatron/exporters/clip_tree.py`) takes a directory, a `ClipGrid` and a name,
  and `export()` writes `<name>_clip_s_<scene>-<scene name>-t_<track>-<track name>.mid` for each
  filled slot (`clip_file_name`: numbers counted from 1 and zero-padded to three digits, the
  scene's or track's name left out when it has none, and whitespace and slashes in the names
  replaced by underscores by `safe_file_name`; the clip's own name isn't used).
- Each clip file has the file name (minus `.mid`) as the MIDI track name, a tempo, and the clip's
  notes at each note's velocity. CC values are written as control changes, with a slide sent as a
  value every `SLIDE_STEP`.
- `ClipTree` must never delete existing files in the directory, and says nothing about other
  files there, since the set's own folder always holds some. A file with a name it needs to write
  makes it print a warning and stop without writing anything (`ERR_FILES_EXIST`). It writes its
  `.mid` files straight to the output folder.

### The Live set

- `AbletonProject(directory, grid, template, name)`
  (`src/llamatron/exporters/ableton_project.py`) writes a Live 12 set to
  `<directory>/<name>.als`, with clips in Session View and the scenes laid end to end in
  Arrangement View.
- A `.als` file is gzipped XML with no public documentation, so it edits a template Live saved,
  `src/llamatron/templates/live12.als`, installed with the package, whose first MIDI track must
  keep a clip because all the clip details are copied from it.
- Ids on tags ending in `Target`, `Targets.N` or `Pointee` must be unique across the set and
  below `NextPointeeId`. Tempo must be set on both the control and its automation.
- To check the format, read Live's own sets in `Contents/App-Resources/Core Library/Templates`
  and its schema in `Contents/App-Resources/Schema`. Tests can check structure, but only opening
  a set in Live proves it loads.
- `AbletonProject` builds the whole set as XML in memory, writing notes and envelopes straight
  into the template's clips, and writes only the `.als` once it's complete.
- It writes one `ClipEnvelope` per CC number, pointing at the track's
  `MidiControllers/ControllerTargets.N`, where N is the CC number plus 2, after pitch bend and
  channel pressure, worked out from one set saved with a mod wheel (CC 1) envelope.
- Live draws a straight line between points, so a slide is just two points, and a value that
  holds gets a second point at the old value at the moment of the next one. Hold points and
  other CC numbers are unverified in Live.

## The MIDI import

- `src/llamatron/importers/` makes a MIDI file a song of the open set, the user's design. `MidiImport` (`midi_import.py`) reads the file once (`midi_reading.py`: a part for
  each channel of each track, times as exact whole notes, tempos, time signatures and key
  signatures) and `imported(setlist=, choices=)` makes the song as data without changing the set,
  as often as `ImportChoices` change; `add_imported` (`writing.py`) adds the scales, the
  patterns and the song through the set's own reading.
- Voices (`voices.py`): drums a voice per sound, named by General MIDI or `perc 1`; a part
  whose notes sound together further apart than one hand reaches split at middle C into
  `<track> treble` and `<track> bass`; notes that start and end together at one velocity in a
  fixed chord symbol's shape one chord when chords are asked for; the rest ranked into voices
  lettered `a`, `b`, each the first free at a moment, so that no voice overlaps itself and no
  note is left out.
- Keys (`keys.py`): each key signature is a major or minor scale, and a file with none is in the
  key its notes fit best (Krumhansl-Kessler). A note is a degree, an accidental and an octave of
  the key (`degree_of`), which the tests hold to play its own pitch.
- Steps (`steps.py`): every note starts on a step; one lasting whole steps is its step and ties,
  any other an exact gate. A clip is the shortest pattern it repeats, a note held from one pass
  into the next a tie at the pattern's start, silence on the first pass.
- Scenes (`cutting.py`): a scene splits only where no note is held across, never cutting one;
  key and tempo changes split first; then phrases of whole bars, the cut that keeps every
  pattern within Longest pattern first, then the fewest patterns, scenes and splits off the
  phrase lines. Each pattern takes the longest step size its own notes start on, down to 1/192,
  so a few triplets make only their clips' steps short. Scenes alike one after another are one
  scene with a Repeat.
- Names (`writing.py`): the song after the file, numbered when taken; a track after its voice;
  a pattern after the first track that plays it, numbered from the first number free; a key's
  scale reused only while named after its root and kind; a scene after its bars.
- CCs (`voices.py`, `steps.py`), with Import CCs on, the user's design: a part's
  first voice takes the CC numbers of `CC_PRIORITY` the part sends, the mod wheel (1), volume
  (7) and the sustain pedal (64) in that order, and then its other CCs, the most sent first, on
  its four lanes (the track's `cc`); CCs past the fourth and the channel mode messages from 120
  are left out, and pitch bend, a message of its own that llamatron can't send, too. A lane is read as the value in force at each step's start; each
  pass states each lane's value at its first step and then its changes, and a straight run of
  two steps or more is one value with Slide on, where every other lane with a value on that step
  holds steady or runs straight too. A voice whose lane changes in a scene where it plays nothing
  has a clip of rests there. A clip takes the longest step its notes and CCs fall on, or, for
  messages between steps (`controls_between_steps`), the longest within `CONTROL_TOLERANCE` (4)
  of the file (`control_error`); a slide that sends a value at any SLIDE_STEP the file doesn't
  hold counts as not exact (`slides_astray`), since a ramp between other ends rounds
  differently; the grid (`grid_for`) is as fine as the CCs need, and the song lasts past its
  last CC message (`bar_lines(holding=)`).
- What changes is warned of, never silent, each warning a sentence, since the dialog after an
  import lists them (`ImportedDialog`); notes moved to a step that are a tenth of the song's or
  more (`SWING_SHARE`) are said to sit off the steps as a swing, a groove or a live performance
  plays them: notes moved to a step, held for whole steps, too low
  to write, tempo changes moved, notes never ended, CC messages between steps or left out, and
  pitch bend and aftertouch left out
  (`MSG_WARN_` in `strings/importing.py`). `comparison.py` compares two MIDI files' notes and
  tempos to llamatron's tick, and each CC brought in as its value over time
  (`control_difference`: the largest difference and the longest time off), which the round trip in the tests and `internal_tools/import_check.py`
  use. The groove demo is the one example that differs, since a swing's offsets fall between
  any step.

## Generators

- Generators live in `src/llamatron/generators`, with the same test layout as exporters: `arp`
  and `auto_ratchet`, the two that a chain can use, `blend`, which morphing uses, and `base`.
- Each subclasses `ClipGenerator` (`base.py`) and implements `_generate(clip)`, which reads
  `clip.resolved_sounds()` and returns new sounds and a length. A generator works on sounds
  and never on `Note`s ("Sounds and lengths in a render"). `generate(clip)` then returns a new `Clip` with the same name and scale,
  leaving the original unchanged, so generators can be chained.
- A generator's list of values must only step through notes and chords, so rests never use up a
  value (`test/test_generator_list_steps.py` checks this, so add new list generators there).
- Chain generators work on finished clips rather than patterns, so a chain follows scale changes.
  Pattern generators that write steps are a separate idea in `dev_notes/IDEAS.md`.

### Generators as paint

- The user's way of seeing generators and chains: a generator is paint. A chain
  applies it to exactly the clips that should have it, and editing the generator afterwards
  changes everything painted with it at once. So where a setting also exists on a scene, a
  clip or a track, the generator is still worth having, for the clips across a song that should
  share one shape, and a demo can show both: the quick field on one clip, and one generator
  painted on many and edited in one place.

### Glide, Shorten, Rush and Drag

- The generator sections `glides`, `shortens`, `rushes` and `drags` (`GlideSettings`,
  `ShortenSettings`, `RushSettings` and `DragSettings`, sharing `StepRowSettings` and the names of
  `StepRowSetting`), the user's design, split from a Glide and a Nudge whose steps
  held two opposite letters: `steps`, a list of 1 to 16, each true or false, drawn as every toggle
  is; `step`, a time, the pattern's step size unless set; and an amount: a Glide's `glide_amount`
  (1/256 to 1/16, 1/128 by default), a Shorten's `shorten` (10 to 95, 70), a Rush's and a Drag's
  `amount` (0 to 50% of a step, 15 and 20).
- `Glide` and `Shorten` (`generators/glide.py`, `generators/shorten.py`, both a `StepRow`) change
  the single notes starting on a step that's on: a Glide holds one past its place into a next note
  of another pitch, a Shorten plays its share with a rest after; chords, rests and held sounds are
  left alone.
- A Rush and a Drag run on no clip itself: `SongRenderer.nudge_plan` gathers every one a clip's
  chains name into a `NudgePlan` of `MovingRow`s (`grid/nudge_plan.py`) on the finished clip, and
  `timed_events` adds their moves together to each slot's grooved start, never before the clip's
  start, so a step on in both moves by the difference. A grab reads notes without them. All four
  follow Restart by their offset.
- `test/test_step_rows.py` tests them; `14_acid_glide.yml` is the Glide and Shorten demo and
  its drop has the Rush and the Drags.

### Hocket

- The generator section `hockets` (`HocketSettings`, kind `hocket`, `HocketSetting`), the user's
  design: `source`, the name of a track of the song it plays in, and `restart`. A new
  one has no source and hands out nothing.
- It runs on no clip itself (`GENERATOR` is `None`). For each written scene,
  `SongRenderer.hocket_turns` works out once the source track's notes as turns, the notes that
  start together being one turn (`source_turns`, through `timed_events` with `grooved=False`, from
  the source's finished clip, its own pattern and chain, never notes handed to it), and deals them
  round the pool (`hocket_pool`: every track but the source whose clip names the Hocket, in the
  song's track order), starting from the turns the run's earlier scenes used, as Restart says. A
  rest passes no turn and a chord passes whole. A track's share (`handed_notes`, `HandedNote` in
  `grid/handed_note.py`) is set on its finished clip (`Clip.set_handed`), and `timed_events` adds
  the handed notes to the clip's own, moved by its groove and its Rush and Drag, cut at its end, never by the hocketing track's transpose or the generators after the Hocket in its chain, the user's answer.
  A Hocket a clip of its own source names is skipped there.
- The source track plays its own pattern as ever; the demo mutes it with the track's Mute. A
  muted source still hands out notes, and a source the song lacks hands out nothing.
- Renaming a track renames a Hocket's source (`Song.rename_item` passes a track's rename to the
  set's hockets, whose `REFERENCES` name `Section.TRACKS`), the user's rule.
- `test/test_hocket.py` tests it; `19_hocket_shanty.yml`, which replaced `grab.yml`, is its demo.

### Restart

- Every generator's `restart` (`GENERATOR_RESTART`, `Restart`: every_clip, on_new_scene,
  whole_song, every_clip by default, `GeneratorSettings.get_restart`), the user's design, Drift alike, whose documents suggest "whole song" (`mainstreet_hoedown.yml`'s drift
  says it, so it plays as before).
- A run starts at the clip's written scene, at the first play of its scene, or at the song's first
  (`SongRenderer.run_start`); `run_offset` is how far into the run the clip starts and `run_span`
  how long the run lasts. Generators that follow time take the offset: `Progression`,
  `EuclidMask`, the shape generators in `ClipSlotPlayer._shaped` (whose ramp spans the run), and a
  Strum generator's by the beat (`StrumPlan.offset`).
- Generators that keep state are handed a `Continuation` (`generators/base.py`: offset, span and
  the state the same track's latest clip before in the run left), made by
  `SongRenderer.continuation`, which works out the clips before first, with no grabs waiting; each
  clip starts from the state it was handed and `end_state()` is kept by `keep_end_state`, by pass,
  written scene, track and the generator's place (its kind, name and how often it came up in the
  chains). The AutoRatchet's next count, Voice leading's chord before, a seeded arpeggiator's
  random state, and a Strum generator's down up (`StrumPlan.chords_before`, from the chords the
  render loop counted) carry on. Each track keeps its own copy (the user's answer).
- A drift's clock starts at its run's start (`SongRenderer.drift_origin`, `DriftPlay.effects`
  and `trigger_times` taking origins).
- `test/test_restart.py` tests it.

### Musical answers first

- When a design question has a musical answer, the least surprising musical result usually wins,
  and it weighs heavily in what Claude recommends to the user (the user's rule).
  For instance, a generator painted on several tracks gives each track a copy of its own, with its
  own state, starting over as its Restart says, so tracks line up when their patterns do and
  patterns of different lengths are the composer's choice. That is a detail of the render's
  timing, but the render's timing bubbles up into the choices the pages offer, and so into how
  people compose and how the tracker feels.

### Arp

- `Arp(step, order, seed)` plays each chord one note at a time for the chord's full length, and
  leaves notes and rests alone. It restarts from the beginning until it fills a set `length`.
- A `ChordOrder` of `UP` or `DOWN` goes by pitch rather than the order the chord was built in.
- It takes the Monomachine's settings: `octave_range` (1 to 4) plays the chord again in higher
  octaves, `octave_jump` is `after_chord` or `after_each_note` (descriptive names rather than
  numbers), and `offsets` is a step track of 1 to 16 values, each moving its note along the
  clip's scale (or by half steps with no scale).
- A `None` step is silent and doesn't use up a chord note, and the offsets restart with each
  chord. With offsets or a range, a single note is arpeggiated as a chord of one note.

### An arp's register adds

- An arp's `step` may be left out, which means the step size of the pattern its clip plays
  (`make_generator`'s `default_step`), the user's rule; a new arp leaves it out.
- An arp's `ax_add` to `dx_add` (`ARP_NOTE_ADDS`, -127 to 127) add to a register on every note it
  plays, and `ax_step_adds` to `dx_step_adds` (`ARP_STEP_ADDS`, a list lined up with the offsets,
  each a number or blank) on each step of the offsets, a silent step too, the user's design. `ArpSettings.insert_offset` and `remove_offset` keep the rows lined up.
- The arp notes each add with its time (`Arp.register_adds`, every generator answering, most
  with nothing), and `ClipSlotPlayer._through_chain` hands them to the recorder after the
  pattern's own steps, so at one moment on one track the pattern's sets and adds come first.
- The counting play plays every note, skipping probability and the conditions
  (`RegisterRecorder.is_counting`), so an arp's adds are the same in every take and never
  depend on the registers they change. `Setlist.changes_registers` counts an arp with adds.

### Drift

- `drifts` is a generator section (`DriftSettings`, kind `drift`), the user's design, but no generator runs on a clip: a chain step naming a drift is skipped by
  `ClipSlotPlayer._through_chain`, and the render reads the drift as one process for the song
  (`playback/drift.py`, `DriftPlay`, built once per render by `SongRenderer`).
- Its own settings: `every` (whole notes, blank for a bar of the song's time signature),
  `steps_to_b` (default 16), `direction` (`DriftDirection`: forward, loop, pendulum, brownian)
  and `seed`. Each version's values are named with its letter, `a_` or `b_` (`versioned`,
  `DriftValue`): the four register adds, `velocity`, `probability`, `degree`, `degree_random`,
  `scale`, `scale_probability`, `root` and `root_probability`.
- Its clock runs from the song's top, the written-out scenes laid end to end
  (`SongRenderer.scene_start`). Each trigger's picks (`DriftPlay.picked`) are worked out once and
  kept, so every clip and both plays hear the same drift: numbers blended by the position,
  rounded; the random degree from the drift's chooser; a scale or root B's with a chance of the
  position, then kept with its probability.
- Register adds go into each scene's changes once a trigger, at `DRIFT_PLACE` before every track,
  for each drift some clip of the scene names (`_scene_changes`, `drifts_of`); a drift with adds
  counts in `Setlist.changes_registers`. Everything else is read by the `PatternPlayer` at each
  step's song time (`DriftEffects`): velocity added after the bound velocity and `+Vel`,
  probability added and held from 0 to 100, the degree added to the note's move along the scale
  (not on drums), and a scale or root override building the scale the degrees play in
  (`_scene_scale_at`).

### Progression

- `progressions` is a generator section (`ProgressionSettings`, kind `progression`,
  `generators/progression.py`), the user's design: `chords`, 1 to 16 degrees from
  1 to 7, a new one `[1]`; `accidentals` and `inversions`, lists beside the chords, each a sharp
  or flat or an inversion of 1 or 2, or nothing; and `every`, a time setting, a bar when left
  out. The rows beside the chords are read as long as the chords (`_lined_up`).
- `Progression` moves each sound to the chord current at its start (`chord_at`, counted from the
  clip's start in lengths of `every`, looping): a plain degree along the clip's scale by
  `along_scale` from `generators/arp.py`, a note outside the scale keeping its distance from the
  scale note below; a degree with a sharp or flat by the exact half steps to that degree, one
  more or less; a chord whole, its inversion moving its lowest one or two notes up an octave; a
  note that would leave the MIDI range staying as it was. `ClipSlotPlayer._through_chain` skips
  it on a drum pattern, still counting it for the seeds.
- `composition/progressions.py` says what the chords are in a `NamedScale`, needing no tracker:
  `quality_of`, `roman_numeral` and `chord_name` (a flat chord spelled with flats), and the
  named progressions (`NAMED_PROGRESSIONS`, keyed by `NamedProgression`, written in numerals
  against a major key), matched to a scale by `matched_to`: a chord on a scale note is that plain
  degree, any other the degree above with a flat, or the one below with a sharp.
- `test/test_progression.py` tests it; `06_chord_progression_generator.yml` and `07_blues_chords.yml`
  are its demos.

### Voice leading

- `voice_leadings` is a generator section (`VoiceLeadingSettings`, kind `voice_leading`,
  `generators/voice_leading.py`), the user's design: `lowest_octave` and
  `highest_octave` (llamatron's octaves, defaults 4 and 6, the lowest never above the highest)
  and `root_in_bass` (default false). The first chord of a clip plays as written; each chord after
  tries every inversion of its notes at every octave within `OCTAVES_TRIED` of where it was
  written, keeps those whose notes all lie in the range and in MIDI's, and takes the one whose
  sorted notes move least from the chord before (note by note when both have as many notes,
  otherwise each to the nearest), the smaller octave move on a tie. With `root_in_bass`, the
  lowest written note stays and only the notes above it are voiced, above it, against the notes
  above the bass before. A chord no voicing fits stays as written, and single notes are left
  alone. `test/test_voice_leading.py` tests it; `05_voice_leading.yml` is its demo.

### Strum

- A track's and a clip slot's `strum_direction`, `strum_spread`, `strum_fade`,
  `strum_loose_timing` and `strum_upstroke_strings` (`strum_setting`, described by
  `strum_settings()` in `composition/strum.py`), and the generator section `strums`
  (`StrumSettings`, the same parts without `strum_`), the user's design. Directions
  (`StrumDirection`): by_the_beat, down, up, down_up and off; spreads (`StrumSpread`) are
  milliseconds between strings (`SPREAD_MILLISECONDS`: tight 2, crisp 4, normal 8, loose 15,
  rake 30, harp 70, normal by default); fade and loose timing 0 to 50; upstroke strings
  (`UpstrokeStrings`) all, top_3 or top_4. A strum is in force where its direction is set
  (`strum_values`); a new generator strums by the beat.
- `SongRenderer.strum_plan` picks the last Strum generator a clip's chains name, else the clip's
  strum, else its track's, and none for off, and sets a `StrumPlan` (`grid/strum_plan.py`) on the
  finished clip beside its groove: the gap in whole notes at the scene's tempo, the beat, and a
  seed fixed for the render. `timed_events` in `exporters/timing.py` plays it (`_strummed`): the
  notes that start together sound low to high or high to low, each a gap after the last, varied by
  the loose timing, the last faded by the fade, an upstroke keeping only its top strings, each note
  ending as written. Grabs read the notes unstrummed. `test/test_strum.py` tests it; `13_classic_strum.yml`
  is its demo.

### The Euclidean mask

- A track's `euclid_hits`, `euclid_steps`, `euclid_rotate` and `euclid_step` (`euclid_setting`,
  described by `euclid_settings()` in `composition/euclid.py`), and the generator section
  `euclids` (`EuclidSettings`, the same parts without `euclid_`), the user's design: hits and steps 1 to 32, steps a bar of sixteenths (`DEFAULT_EUCLID_STEPS`) unless
  set, a rotation moving the rhythm later, and a step from the time list, the clip's pattern's
  step size unless set. A mask is in force where its hits are set; a generator refuses more hits
  than steps. `rhythm(hits=, steps=, rotate=)` is Bjorklund's spreading, so 3 over 8 is the
  tresillo; `NAMED_RHYTHMS` are the picker's eight.
- `EuclidMask` (`generators/euclid.py`) turns every note that doesn't start on a hit into a rest
  of its length, the rhythm counted from the clip's start. A generator runs in its chain like any
  other; the track's mask runs after the clip's chains (`ClipSlotPlayer._masked`), before the
  shapes. Masks stack because each silences what it misses. `test/test_euclid.py` tests it;
  `euclidean.yml` is its demo.

### Time settings

- Every time setting chooses from one list, `TIME_CHOICES` in `composition/file_format.py`, the
  user's rule: an arp's `step`, a drift's `every` and a shape's `over` (and,
  when built, the harmonizer's delay). The list runs 1/64, 1/32, 1/16, then each triplet after
  its straight value and the dotted one after that up to 1/2, then `1 bar`, `2 bars`, `4 bars`,
  `8 bars` and `16 bars` (`ONE_BAR_WRITTEN`, `BARS_WRITTEN`).
- A file holds a length in whole notes or a count of bars as that text. `time_length` in
  `composition/checks.py` reads either, a count of bars as `Bars`, and `in_whole_notes(time=,
  bar=)` turns it into a length with the song's bar, which the render passes on (an arp through
  `make_generator(bar=)`, a drift through `DriftPlay.every`, a shape through
  `ClipSlotPlayer._shaped`). Any positive length is still read, so an older file's `every: 2`
  plays as before. `test/test_time_settings.py` tests it.

### Density, Swell and Articulate

- The shapes (`Shape`, `SHAPES` in `composition/file_format.py`), the user's design: how many of a clip's notes play, how loud and how long, each a percentage ramping
  from a start to an end. A scene and a clip slot each hold `density_start`, `density_end`,
  `density_over`, `density_then` and the same for `swell_` and `articulate_` (`shape_setting`,
  described by `shape_settings()` in `composition/shapes.py`), and the generator sections
  `densities`, `swells` and `articulates` hold `start`, `end`, `over` and `then`, a swell an
  `accent` too (`ShapeSettings`, `DensitySettings`, `SwellSettings`, `ArticulateSettings`).
- The limits: Density 0 to 100, Swell 0 to 200, Articulate 10 to 200, Accent 0 to 50
  (`composition/limits.py`). A part left blank plays as 100 (`UNCHANGED`), so a song that sets
  none plays as it always has; a shape is in force where its start or end is set
  (`shape_values`). `over` is a length in whole notes, blank for the whole span; `then`
  (`ShapeThen`: hold, repeat, bounce, hold by default) says what follows a ramp.
- Like a drift, a shape generator runs on no clip itself (`GENERATOR` is `None`):
  `ClipSlotPlayer._shaped` reshapes the finished clip after its chains, outside the counting
  play, taking the last generator of each kind the clip's chains name, else the clip's own,
  else its scene's. A scene's ramp spans the scene's length, a clip's or a generator's the
  clip's.
- `playback/shapes.py` does it on sounds (`reshaped`): each position keeps its place, a dropped
  note becoming a rest of its length. Density keeps a note when the density passes the
  threshold of its place's strength (`strength`, `PLAYS_ABOVE`: the bar's start always, its
  middle above 6.25, a beat above 12.5, an eighth above 25, a sixteenth above 50, anything finer
  only at 100), in the song's time signature, chords whole, drums too. Swell scales each note's
  velocity (a blank velocity counting as 127), held from 1 to 127, the accent adding its share
  on a beat and stronger. Articulate scales the written length, a longer note held over the
  rests after it but never past the track's next note or the clip's end.
- `test/test_shapes.py` tests them; `edm_density.yml`, `16_bolero_swell.yml` and
  `15_acid_articulate.yml` are their demos.

### AutoRatchet and Blend

- `AutoRatchet(counts)` chops each note or chord into that many adjacent equal repeats, using the
  next count in a cycle, and rests don't use one up.
- `Blend(target, amount, mode)` moves a clip towards an equally long target, with
  `BlendMode.LEFT`, `RIGHT` and `MIDDLE` sweeping the target in from one side or the center.

## Examples and demos

- `examples/` is for people interested in music, who may not be technical and may never develop
  the program: every set there is musically interesting to them. A set that exists only to test
  the program, such as one with wrong values, never lives there; test data lives under `test/`.
- `examples/` is in folders by purpose, the user's layout, which `support/example_sets.py` names and lists
  (`example_sets()`, which every test and tool asks):
  `examples/learning/` the demos in the order a newcomer learns, each file numbered in that order, zero-padded so that the files sort, like `01_hello_world.yml` (the user's rule: a demo moved into or out of `examples/learning/`, or put in another place in the order, means renumbering the learning demos after it, with every reference to their files; a demo's song and its sections and anchors in the documents go by the name after the number; the Entertainer, with too many patterns to teach, is in `examples/by_genre/ragtime/`), `examples/other/` the demos that fit no other folder (the Euclidean mask so far), `examples/by_genre/` every other song, the pieces and the songs in the manner of others alike, each in a folder of its genre, the genre in lower case with spaces and hyphens made underscores, like `examples/by_genre/tv_theme/` (`genre_folder`, the user's layout, since one folder held too many to explore; a homage whose genre changes moves with it, which `test/test_examples.py` holds), and
  `examples/midi/` the MIDI files to import. `test/demo_sources/make_demos.py` writes each demo into its folder.
- `examples/` holds two kinds of set. The pieces, `minimal_techno.yml` and `mainstreet_hoedown.yml`, are meant to sound good and last about three minutes (`PIECES` in `test/rendering.py` lists them). Every other set
  there is a demo, which teaches one feature a scene at a time, described for people in
  `docs/DEMOS.md`, whose index is generated, and on a page for each genre in `docs/demos/`, where each demo has a section of its own, a heading and a description written by hand and a summary generated between markers (`internal_tools/demo_table.sh`), which a new demo needs before the tests pass, and in each set's `description`, whose "When changing this demo" part says
  what to keep true when editing one.
- A demo with a video on YouTube shows it at the end of its section on its genre's page, under the generated summary, as a linked thumbnail like the guide's (`[![The Density demo, edm_density.yml, on YouTube](https://img.youtube.com/vi/ID/hqdefault.jpg)](https://www.youtube.com/watch?v=ID)`), the same way for every demo, the user's rule; a demo without one shows none, and the user adds them now and then. A video isn't redone when its demo changes: the disclaimer on Listening to the Demos says a video may be out of date. The Density demo's is also on the guide's front page and in `README.md`, under the visualizers' video.
- A demo's title, description, heading and notes never call it a homage, the user's rule, except in a sentence that says "This is a homage to" a work: a heading names the style, like "Synth-Pop", and a description says "in the manner of" the work.
- Whether a new feature gets a demo is asked of the user every time (`.claude/COMMUNICATION.md`,
  "Discussing a feature").
- A new example runs about three minutes, give or take ten seconds, unless the user asks for
  another length, as for `weather.yml`'s ten minutes (the user's rule). The demos
  written before the rule keep their lengths. `test/test_examples.py` holds every example to it
  but those listed in `WRITTEN_BEFORE_THE_LENGTH_RULE` and, with their own lengths, `OTHER_LENGTHS`.
- `test/test_demos.py` loads, renders and saves every demo without checking what it plays, so
  they can be edited freely.
- `test/demo_sources/make_demos.py` wrote the first versions of all but the hand-written ones
  (`HAND_WRITTEN` in `test/test_demos.py`), from tune data written into it, plus the Mutopia
  Project's public domain `examples/midi/entertainer.mid`, kept with its LilyPond source among
  the MIDI files people can import.
- Run directly, it overwrites the demos, hand edits included, so it's only for starting over. The
  tests also run it into a temporary folder and check its output against those sources.
- Song data a test or script needs is kept in the repository as data files, separate from the
  test code.
- Muted tracks in the demos have SILENT in their names, which a test checks.

## Performance

- The tracker re-renders or re-estimates the song as people edit it, loading and saving should be
  quick, and real-time MIDI playback may come later, so the time to render a song and the work
  done after each edit are both watched.
- Lengths and times are exact `Rational`s (`src/llamatron/support/rational.py`), never floats.
  `Rational` does only what the program needs and is about twice as fast per operation as the
  standard library's `Fraction`. `test/test_rational.py` checks it against `Fraction` for every
  operation, and `Fraction` is still accepted wherever a length or amount comes from outside.
- The aim is fewer operations rather than a different number type: build each note once
  (`Note.with_length` and friends, not `dataclasses.replace`), keep pattern steps as per-row
  arrays with no Step objects, work out what can be worked out without playing (clip and scene
  lengths are arithmetic, see `SongRenderer.get_clip_length`), and skip whole passes that would
  do nothing (the register-recording pass only runs when a step adds to a register,
  `Song.adds_to_registers`). Any such shortcut needs tests of both paths.
- A value is checked once, where it is made. A step's notes are made with their final length,
  velocity and glide (in `playback/pattern_player.py`, through `Scale.sound_at`),
  never made and then copied for each thing the step sets. A copy of a `Note` (`with_length`,
  `with_velocity`, `with_glide`, `half_step`) checks only what the copy changes and takes the
  rest as it is (`Note._at_this_pitch`, through `note_of_checked_values`, the one place a note is made without its constructor, which `internal_tools/time_renders.py` counts), since the name, octave and MIDI number were checked
  when the note was made: checking them again for every copy was most of what a note cost.
  `test/test_note.py` holds each copy to the constructor's note and the constructor's refusals.
- What a pattern holds is gathered once for each clip that plays it (`PlayedPattern`, kept by
  the `PatternPlayer`): every step's values (`Pattern.get_every_step_values`, which fills only
  the rows that hold anything, where asking all thirty rows about every step was an eighth of a
  render), and whether any step sends a CC value (`Pattern.sends_controls`), adds to a register
  (`adds_to_registers`) or uses one (`uses_registers`). A pattern with none of those skips that
  work on every step, and `test/test_registers.py`, `test/test_tracks_and_controls.py` and
  `test/test_composition.py` test both sides of each. A pass takes all its steps from the
  `StepOrder` at once (`next_steps`).
- A clip's list keeps a note, chord or rest as it is and reads only shorthand, a section stops
  once it is past its end and keeps a position that lies wholly inside it, and `Rational`'s add,
  subtract and multiply reduce to lowest terms where the answer is made rather than through a
  call. Together with the two points above, rendering every example went from about 408 ms to
  about 214 ms, with every export byte for byte the same.
- NamedTuples are used for fixed-shape tuples like events, register changes, chain steps and
  estimates. Integer ticks in place of `Rational` were rejected, and are open to revisiting if
  profiling asks.
- Profiling is done with `cProfile` over the examples, and `internal_tools/compare_exports.py` proves a
  speedup changed nothing. `test/test_clip_lengths.py` checks the arithmetic lengths against a
  full play of every example.

## Sounds and lengths in a render

- A render makes no `Note`, `Rest`, `Chord`, `Degree` or `Held`. Each position it makes is a
  sound, a plain tuple, and each length inside a render is a pair of whole numbers. The classes
  and `Rational` stay at the edges: what a set file stores, a clip's own length, the times an
  exporter is given, the tracker and the tests.
- `Sound` (`src/llamatron/music/sound.py`) is a class of static methods that builds, reads and
  copies sounds. Every sound starts with its kind and its length: a rest `(REST, length)`, a
  note `(NOTE, length, MIDI number, velocity, glide, name)`, a chord `(CHORD, length, notes)`,
  a degree `(DEGREE, length, number, octave, scale notes, half steps)`, a held sound `(HELD,
  length, sound)` and a held phrase `(PHRASE, length, parts)`. A note carries its name so that
  its spelling survives. The places are named (`KIND`, `LENGTH`, `MIDI`, `NOTES` and the
  rest), and code reads a sound by those names, never by a bare number.
- `Sound.of(position)` says a `Note`, `Chord`, `Rest`, `Degree` or `Held` as a sound and
  `Sound.position(sound)` says a sound as the object, losing nothing either way. A sound that
  can't be made, like a note outside the MIDI range or a held rest, raises what the class
  raises in the same words, because `PatternPlayer` catches a note out of range to try another
  octave and a render's error shows the words.
- `Length` (`src/llamatron/support/length.py`) is a class of static methods on pairs
  `(numerator, denominator)`, always in lowest terms with the denominator above zero: `add`,
  `subtract`, `times`, `shared`, `multiplied`, `whole_times`, `less`, `at_most`, `shorter`,
  `longer`, `longest`, `total`, `is_positive`, `distance`, with `exact(number)`, `of(rational)` and
  `rational(pair)` at the edges. Two pairs are equal exactly when the lengths are, so `==` is
  safe. Which is longer is never asked with `<`, `min`, `max` or `sorted`, which compare tuples
  one number at a time and would put a half before a third: every ordering goes through
  `Length`.
- `grid/positions.py` cuts sounds and takes pieces out of them, `exporters/timing.py` reads a
  clip's sounds and still gives `NoteEvent`s and `ControlPoint`s with `Rational` times, so no
  exporter changed, and CC values, register times and a `Pass`'s length stay `Rational`s.
- `test/test_length.py` holds every `Length` method to `Fraction`. `test/test_sound.py` holds
  every way a sound is made or copied to the class that says the same, `Scale.sound_at` to
  `Scale.note_at` on both sides of the MIDI range, and the rule that no module of `playback/`
  or `generators/`, nor `grid/positions.py` or `exporters/timing.py`, imports one of the
  classes.
- Rendering every example went from about 213 ms to about 154 ms, and from 3.28 million
  function calls to 2.15 million, with every export byte for byte the same.
  `internal_tools/time_renders.py` counts objects made, and a sound is no object, so its count of notes
  fell from 8748 to 246 in `08_tie.yml`.

## Real-time playback

- `src/llamatron/realtime/` plays a rendered song out of the computer's MIDI ports, the user's
  design. What is left of it is in `dev_notes/IDEAS.md` under "Real-time
  MIDI, what's left". How the tracker drives it is in `.claude/TRACKER.md`, "Real-time
  playback".
- Render first, then only schedule: `song_timeline(grid=, routes=)` in `realtime/timeline.py`
  turns a `ClipGrid` into one time-ordered list of `Playing` events across every track, the
  scenes laid end to end as the MIDI export lays them, read from the same note timing
  (`exporters/timing.py`), so everything that makes the music has already happened. Each event
  carries its whole-note time, its seconds, the port and channel of its track's `Route`, its
  kind and bytes, and a `Tag` of scene place and track name, so that one clip's events can be
  dropped or stopped. A track with no route, which is a track with no instrument, and a muted
  track are left out. Note offs sort before note ons at one instant.
  `test/test_realtime.py` holds every example's timeline to its MIDI export, tick for tick.
- `PlaybackEngine` (`realtime/engine.py`) holds the events still to send in a heap, sends each
  when its time comes (`send_due`), remembers which notes are sounding, and silences on
  `stop_tag` (that tag's sounding notes) and `stop_all` (every sounding note, then CC 123 and
  CC 120 on every channel used). `drop(tag=, after=)` forgets a clip's events from a time on,
  which is how an edit while playing replaces the passes not yet started. It reads a `Clock`
  and writes to `MidiOutput`s and nothing else: a `SteppedClock` and `RecordingOutput`s drive
  it in tests with no time passing, and `MonotonicClock` and `RtMidiOutput` in the process.
- `RealtimeMIDISenderProcess` (`realtime/sender_process.py`), the Realtime Sender Process, runs
  the engine in a spawned process, since a thread drifts by the interpreter's switch interval
  while the screen draws and a process measured within 0.11 ms. The tracker's side sends
  `start`, `add`, `drop`, `stop_tag`, `stop_all` and `close` over a pipe. The process sleeps in
  half-millisecond slices until 1.5 ms before the next event and spins to the moment, since
  sleep is loose on macOS. With `recording=True` it opens `RecordingOutput`s and `close`
  returns when the timeline started and every message sent, which the suite's short lag test
  and `internal_tools/realtime_report.py` (`internal_tools/realtime_report.sh`) read.
- `realtime/outputs.py` is the only module that imports `rtmidi`, inside `midi_library()`,
  so the program runs without python-rtmidi until a real port is opened; `output_port_names()`
  lists the computer's ports, an empty list with none or no library.
- `RealtimeMIDISenderProcess.start` spawns with the interpreter's own `sys.stderr` put back
  (`real_standard_error`), because spawn's resource tracker passes `sys.stderr.fileno()` to its
  child and Textual's capture answers -1, which failed every spawn from inside the tracker with
  `bad value(s) in fds_to_keep` (found by the user on the IAC bus); then it waits
  for the process's `READY`, sent once the ports are open, so that a launch's first event isn't
  sent late while the process starts, and raises `SenderNotStarted`
  (`ERR_SENDER_DID_NOT_START`) when the process ends without it, which it does quietly when a
  port can't be opened. `close()` returns at once on a process that never ran.
  `test/sender_under_capture.py`, run by `test/test_realtime.py` in an interpreter of its own
  since the tracker starts once per interpreter, holds the spawn under a capture like Textual's.
- `internal_tools/iac_check.py` (`internal_tools/iac_check.sh`) is the one tool that touches real MIDI hardware, by
  the user's leave, and opens only a port with `IAC` in its name, the macOS bus
  from one program to another: it plays a C major scale up and down, a note a beat, built in
  memory on a new set's starter pattern (or the first seconds of a set named), out of the bus on
  channel 1 through the real process, printing each message as its time comes with the device,
  the channel and the note, so that what should be heard is on the screen; it reads the bus
  back as an input and reports what arrived, in order, how late against the schedule, and that
  the silencing on close arrived, with the least, mean, most and standard deviation of the
  lateness and a verdict at `AUDIBLE_MS` (10), and when something else is sending to the bus too,
  like the tracker playing, it decodes the first ten of those messages, says so and judges
  neither order nor lateness. `docs/MIDI_SETUP.md` is the document for people about it. Measured at a mean of
  0.16 ms and a worst of 0.9 ms over ten seconds of the Entertainer, receive thread included.
  The suite never runs it.
- `test/sample_sets/heavy_chain.yml`, a chain of twenty generators with grabs and chords, is
  the report's stress case for the stage before the process.
- `Score(song=, routes=, seed=)` (`realtime/score.py`) is a song rendered for launching: it
  renders with `SongRenderer`, groups the grid's rows by the scene they were written from
  (`WrittenScene.get_scene`), so that a scene that repeats is one scene of several rows, and
  keeps each clip's events counted from its scene's start (`events`, `played_events(scene=,
  track=, start=, play=)`, which moves them to a moment and tags them with the number of that
  play), each scene's seconds and its start when the song plays from the top, which clips loop,
  each clip's follow action (`Setlist.follow_action_of`, an empty slot counting as "With Scene")
  and whether each scene launches together, and for the lights when each note sounds
  (`is_sounding`, `sounding_across`, for cutting a clip ahead), each note's number and velocity
  as it is heard for the visualizer (`heard`, through `Player.heard`), the repeats left
  (`repeats_left`) and how far into its play a clip is (`clip_elapsed`, for the clip's bar). A track with no route, or a muted one, has no events but is still a track of
  the score, so that its clips run silently and the arrangement keeps its shape.
- `Player(score=, sender=, now=)` (`realtime/player.py`) launches scenes and clips into a
  sender, the engine or the Realtime Sender Process, on the sender's clock. `play_song()`,
  `play_scene(scene)`, `play_clip(scene=, track=, forever=)`, `stop_clip(track)` and
  `stop_all()` are what the pages do; `tick()` turns the moments due within
  `LOOKAHEAD_SECONDS` (2) into queued events, in time order, from a heap of `Moment`s; and
  `is_playing`, `playing_scenes`, `is_clip_playing`, `is_track_sounding`, `scene_elapsed`,
  `repeats_left` and `song_position` answer the lights. The rules, which the module's
  docstring states and `test/test_realtime.py` holds it to, with every example played from the
  top against its timeline event for event to the end: a scene launched by hand plays every clip of it; a scene is done when every clip
  launched in it has finished, every play ending at its launch plus the scene's seconds, and
  then each clip whose follow action isn't "Off" sends a start to the clip directly below,
  which launches the whole scene below when that scene launches together, stopping what the
  scene above still plays, and that clip alone otherwise; a clip whose follow action is
  "Next" sends its start when its own repeats end (`Score.clip_end`, a `CLIP_DONE` moment);
  a clip launched by hand plays on its own, whatever its scene says, cutting what its track
  played and cut in turn where a play already queued ahead on the track starts; a clip
  stopped or cut never finished, so it sends no start; a looping clip never finishes, so it
  doesn't hold its scene, and plays again at the scene's end unless the scene below starts on
  its track, or the scene is the last and the loop's start has nowhere to go, where it ends
  with the scene so that the song ends as the export does; a scene whose every clip loops is
  never done and waits for the human, the user's rule (an earlier rule let one
  looping clip hold its scene, and the registers demo never left its first scene).
  A launch by hand while anything plays is always at the next bar of the song's time
  signature, the user's rule, as Live's default quantization: `next_bar()`
  counts bars from the start of the earliest clip playing, at the tempo of its scene's row
  there (`Score.bar_seconds`), what plays goes on until then, a clip or scene shorter than a
  bar hands over at its end, and with nothing playing the launch is at once. The starts that
  follow actions send are at the scene's end, where the export has the next scene start. At
  one time the follow actions' work runs before a launch by hand, so the human's launch is
  what plays. None of this is read by `SongRenderer` or an exporter: every export is byte for
  byte what it was.
- FluidSynth (`realtime/fluidsynth.py`, `FluidSynth`), the user's design, is
  started by the transport when something first plays through an instrument on `*FluidSynth`
  (`ensure_running`, from `Transport._sender_for`), with the GeneralUser GS SoundFont, the Mac's
  audio and a CoreMIDI port of its own, `FLUIDSYNTH_PORT` (`llamatron FluidSynth <pid>`), and
  waited for until the port is listed (`START_SECONDS`), before the sender opens it, so no note
  is lost; a FluidSynth started again makes the sender open the port again. It reads commands
  from a pipe the tracker holds and quits when the pipe closes, so it ends with the tracker
  however the tracker ends (`stop`, from `Transport.close`). It plays at `GAIN` 0.55, measured so
  that the loudest example peaks about 1 dB below full scale, where FluidSynth's default of 0.2
  left it under a third. `fluidsynth_path` looks in `/opt/homebrew`, then `/usr/local`, then
  PATH, and `soundfont_path` in `~/soundfonts`, where `user_scripts/install_fluidsynth.sh` puts them;
  `is_installed` needs both. Its sound goes to the Mac's default output, or to the device
  `LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE` names, which only `internal_tools/record_demo.py --fluidsynth` sets.
  A track through FluidSynth gets the channel the General MIDI export gives it, 10 for a drum
  track and the rest in turn among the unmuted tracks through FluidSynth (`Transport.routes`),
  and its `Route` carries the program, which `clip_timeline` sends at each clip's start
  (`PROGRAM_CHANGE`, sorted before the note ons at its instant). `test/test_fluidsynth.py` and
  `test/test_tui_playback.py`'s `TestFluidSynthPlayback` test it.
- Live editing, the user's design (`Player.update_score`): a score rendered again after an edit is
  taken by each play from the moment the song's `live_responsiveness` says (`_switch_time`: at once,
  `LIVE_LATENCY_SECONDS` from now; the next bar of what plays, worked out by the old score; or the
  play's next pass, `Score.next_pass_start`), keeping its place in the music when the tempo changed
  (`Score.whole_at` and `seconds_at` move the play's start), ending the notes sounding across the
  moment and queuing the new notes from it (`Score.events_from`, which leaves out note offs whose
  note ons came before). A play that hasn't started is queued afresh; one the edit reaches only at its
  end takes whether it loops. The ends of scenes and repeats are planned again (`_plan_ends_again`).
  The player decides what comes next only `LOOKAHEAD_SECONDS` (0.5) ahead, where it was two seconds,
  so that an edit can still change a scene's end; every clip queues all its notes as it starts, so
  nothing is late. `is_playing` counts only a moment that can still act (`_can_act`). A scene whose
  every clip loops plays in real time as long as its longest clip plays once, going round
  (`SongRenderer(looping_scenes_go_round=True)`, which only `Score` asks for), while the export still
  refuses it and a launch by hand still says so; that is what makes a scene looped while it plays
  play on.
- `PlaybackEngine.silence(channels=)` sends a note off for every note, then CC 123 and CC 120,
  on each (port, channel) given, whatever it knows to be sounding, and the process relays it as
  `silence`, for Ctrl+T. `start(at=)` lets the tracker start the engine's clock at a reading of
  its own clock, so the two agree on the seconds.

## Tests of the model

The tests of the model, playback and the exporters, the helpers they share in
`test/song_testing.py` and `test/rendering.py`, and the rules every test follows are in
`.claude/TESTING.md`.
