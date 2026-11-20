# The File Format's Rules

Reference notes for Claude, one part of `.claude/format/`: what a set file holds, setting by setting. `CLAUDE.md` says which part to read for which work.

## The format's rules

### A set

- A file is a set, held by `Setlist` (`composition/setlist.py`), like the songs played in one
  concert.
- The set owns the shared sections, `scales`, `patterns`, each generator kind, `chains` and
  `grooves` (`SETLIST_SECTIONS` in `composition/sections.py`), and `songs`.
- The file mirrors the objects, the user's design: everything a person names is an item of a list with its `name:` first, never a
  mapping keyed by name: `scales`, `patterns`, `generators`, `grooves`, `instruments` and `songs`, a song's `tracks`, and a scene's
  `clips`, each clip `{ track: x, ... }`. `generators` holds every kind, each item with `kind:`, a chain among them as
  `kind: chain` with `generators: [{ name: x }]`; a clip, a scene and a track write the generators they run as
  `generators: [{ name: x }]`. Fixed fields stay keys, and a song's `registers` keep AX to DX as keys. The objects keep their named
  things by name, each generator kind apart and the chains apart, and `composition/file_layout.py` turns one into the other
  (`as_file_layout` for the writer, `as_object_layout` for the reader). A generator's name is unique across every kind and the
  chains: adding or renaming refuses another kind's name (`Setlist._check_generator_name`), a set's data with two is refused
  (`setlist_reader._check_generator_names`), a new or copied generator's name steps past every generator's
  (`DocumentNamedEdits.names_taken`), and the MacroComposer tells its own apart (`composer.names_apart`: two kinds' generators
  take their kind's word, as kick rush, and a chain that shares a generator's name takes the word chain).
- Migrations, the user's design and rule: an older file is moved to the layout written now by `composition/migrations/`, one
  module a migration, run in the order of their versions for every migration newer than the file's `version`
  (`migrations/running.py`), a file with no version moved where its data has the old shape. Every piece of code that only runs
  on an older layout lives in that package and nowhere else, nothing outside imports more than `migrated` and `Conversion`, and
  a migration knows nothing of the objects or the reader (`tests/composition/test_migrations.py`). Only a breaking change of
  layout gets one; adding a setting needs none, and a feature taken away leaves nothing to move: a removed setting never gets a migration, since reading passes over
  every name it does not know and nothing writes one again (the user's rule; "Keys a File Holds That llamatron Does Not Know"). A migration is never changed
  once released. They are: Live's octaves before 1.0.30, one song at the top before 1.0.39 (named after the file), the
  description as notes before 1.0.155, and lists before 1.0.591 (which also turns a clip's single `chain` into a list, and settles
  a name two kinds shared by the naming rules, the later going on as `x-2`). An old file opens converted and unsaved, the status
  line saying `converted from an older format` with every rename (`DocumentFiles.conversion_note`), and the file on disk is
  untouched until saved. `tests/data/migrations/` keeps files in older layouts for the tests.
- Each song is a `Song` (`composition/song.py`) with its own `tempo`, `time_signature`, `scale`,
  `groove`, `genre`, `live_responsiveness`, `preview_instrument`, `registers`, `tracks` and `scenes`
  (`SONG_SECTIONS`), written in that order under `songs:` by `setlist_writer.py`. A song's
  `live_responsiveness` (`LiveResponsiveness`: next_bar, clip_restart or asap, next_bar by default and
  written only when set, `Song.get_live_responsiveness`), the user's design, is when an edit made while
  the song plays in real time is heard on what plays: at the next bar, at each playing clip's next
  pass, or at once. A song's `preview_instrument` (`Song.get_preview_instrument_name`, the user's design) names the instrument of the set that
  Listen plays a pattern through, None, the default, for General MIDI's piano through FluidSynth; a rename follows it and the song is a use of the instrument. A song's `genre` is text only for people, blank by
  default (`Song.get_genre`, `Setlist.get_genres`), the user's design, which the demo
  tables show; every example has the broad genre the user approved.
- A song keeps a back-reference to its set and forwards lookups of shared things to it, so
  playback asks the song for a pattern or scale and doesn't know about the set.
- Songs are a `NamedItems` section like any other (`Section.SONGS`).
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
  file saved before 1.0.155 held the long text under `description`, which its migration moves to `notes`.

### Protected sets

- `protected` (`SetlistSetting.PROTECTED`, default false, `DEFAULT_PROTECTED`, written last among
  the settings) marks a set whose own file the tracker never writes over.
- `Document.save` raises `SongFileError` (`ERR_FILE_PROTECTED`) when `file_is_protected()`, which
  is true only for the set's own existing file, so a protected set that has no file yet still
  saves the first time.
- `Document.save_as`, which the tracker's Save as uses, turns a copy's protection off, because a
  copy the user makes is theirs. Plain `save(path=)` keeps it, so tests can re-save the examples.
- Every set in `examples/` is protected, and `tests/data/demo_sources/make_demos.py` writes them that
  way. A new set isn't.

### Defaults for everything

- Every setting in the file has a default when it's missing, including `tempo` (120), `tracks`
  and `scenes`, so an empty file is an empty song and a file from an older version still loads.
- This is a lasting rule: new fields get a reasonable default rather than migration code, unless
  the format changes structurally.

### Everything inline

- Every object is stored with its settings inline, never in a separate section, a permanent rule
  for every object type.
- So `tracks` is a list of tracks with their settings, like `- { name: bass, transpose: 2, cc: [74, ~, ~, 1] }` or
  `- { name: kick, drum: true }`, in order, and a track with none is `- { name: lead }`.
- Every generator setting is named, an item of a list is written on one line in braces, and clip slots are items of a scene's
  `clips`, each `{ track: x, ... }`.

### Patterns

- A pattern may say its `group`, text, the heading the Patterns page lists the pattern under; a pattern that says none is in no
  group, as every pattern of an older file is. The set's `closed_pattern_groups`, a list of group names, says which groups that
  page shows closed; a name no pattern is in, or anything that is not a list of text, is ignored and never refuses a file.
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
  still reads the plain lists. `tests/composition/test_row_descriptions.py` tests it.
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
  for the next bar of the song's time signature (`.claude/features/REALTIME_PLAYBACK.md`).
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
- `tests/composition/test_pattern_notes.py` tests it on `Pattern` alone, at several step sizes.

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
  spelled on the letters a chord stacks. `tests/composition/test_chords.py` and `tests/generators/test_progression.py` (`TestLeavingTheScale`) test
  these, `tests/tui/test_tui_chords.py` the pattern editor's rows and the dialog.

### Probability and seeds

- Probability is rolled at render once per repeat and ratchet slice. A song holds no seed: every play and export draws its
  random parts afresh, from Python's own random stream, seeded by the system, so each is a new take (the user's rule, since a
  kept seed could not promise the same take once Python's random numbers change). No generator keeps a seed of its own either, the arpeggiator's and the drift's gone the same way;
  a file's old `seed`, on a song or a generator, is passed over as an unknown name.
- `random_source(seed)` (`src/llamatron/support/random_source.py`) is the one place that decides
  between a seeded generator and the shared random stream.
- `SongRenderer(song, seed=n)` renders from a seed, the internal way that tests and tools repeat a take, which no person and no
  command-line option reaches: `internal_tools/compare_exports.py` uses it (`COMPARISON_SEED`, 1), and a test's song data may give
  `render_data` a seed under `TEST_SEED` (`tests/support/rendering.py`). Real-time playback draws one seed when a play starts and
  keeps it while the song plays, so an edit doesn't redraw what plays. The command line's `--seed` is the song wizard's alone, with `--wizard`.
- A note that probability drops is silence in its place, however long its gate: a gate that
  reached over the next note holds nothing, the steps up to the next note are rests, and the
  next note plays as normal. Until 1.0.136 such a take stopped the export, since a rest can't
  be held. `tests/composition/test_song_patterns.py` tests the take that keeps the note and the take that
  drops it.
- It deliberately doesn't use Live's per-note probability.

### Inversions

- A pattern's `inversion` row (`RowOfInversions`), the user's design, holds 1, 2 or
  3 on a step with a chord, or nothing for root position: that many of the chord's lowest notes
  move up an octave as it plays, never all of them, so a triad plays 3 as 2
  (`Sound.inverted`, which `PatternPlayer` applies to every slice, a grab's chord too, and the
  Progression generator to its chords). A drum pattern refuses one. `Pattern.chord_tones` gives
  the roll's ghosts where the inversion plays them, the root among them an octave up. The editor's
  `InversionRow` is blocked on a step with no chord. `tests/composition/test_inversions.py` and
  `tests/tui/test_tui_inversions.py` test it.

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
- A scene's and a clip's velocity (the user's design): `velocity`, a percentage of each note's written velocity from 0 to 200
  that holds, and `velocity_in_start`, `velocity_in_end`, `velocity_in_over`, `velocity_out_start`, `velocity_out_end` and
  `velocity_out_over`, a ramp in from the first bar and a ramp out back from the last, each over a count of bars
  (`VelocitySetting`, `composition/velocity_ramps.py`). A ramp plays when it has its bars and a start or an end, and an end
  left blank is the velocity, which the ramps start from and return to. A clip's settings win over its scene's field by
  field (`velocity_of`). A ramp whose bars the scene gives counts them across the scene's whole play, every repeat; a ramp
  whose bars the clip gives counts them over the clip's own play, from its start and back from its end, a looping clip's end
  being its scene's. The ramp in wins where the two overlap. The percentage is read at each note's own time
  (`velocity_percent_at` in `playback/shapes.py`), after a Swell generator's, which scales the notes besides. A scene and a
  clip hold no Swell of their own, and `swell_start` and the like are refused there.
- A scene's tempo ramps (the user's design): `tempo_in_start`, `tempo_in_end` and `tempo_in_over` ramp from the scene's first bar,
  `tempo_out_start`, `tempo_out_end` and `tempo_out_over` back from its last. A start or an end left out is the scene's own tempo
  (its `tempo`, else the song's), a ramp with no over, or with neither start nor end, does nothing (the user's design: Over is a number of bars). The
  tempo changes at every step of the set's step size (the user's rule: a slope, never a stair of bars or beats), counted across all the scene's repeats together;
  the ramp in wins where they overlap; nothing reaches past the scene. `playback/tempo_ramps.py` works the beats out, the renderer
  gives each row its changes (`ClipRow.get_tempo_changes`), and every length in seconds goes through `grid/row_clock.py`'s
  `RowClock`: the estimate, the real-time score and timeline. The MIDI exports write a tempo change a step; a Live set writes
  them as arrangement automation and launches the Session View scene at its first tempo (the user's choice, documented in
  `docs/EXPORTING.md`). Strums and keyswitch leads, set in milliseconds, are measured at the scene's own tempo, not the ramp's.
  The old `tempo_start` and `tempo_end` are gone, with no reading of older files.
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
- `registers:` holds the settings that differ from the defaults, like `AX: { maximum: 3, reset_behavior:
  overflow }`, with `default`, `minimum` and `maximum` from -127 to 127 (defaults 0, 0 and 10, in
  order minimum <= default <= maximum), `reset_behavior`, `reset_each_scene` and `allowed_inc_max` (1 to 127,
  default `DEFAULT_ALLOWED_INC_MAX`, 20, enough for every example written before it), the most
  a step may add or take away, the user's design. The pattern editor's `+=` rows
  stop there (`Setlist.allowed_inc_max_for_pattern`: the narrowest of the songs that play the
  pattern), while a file is still read from -127 to 127.
- `reset_behavior` (`ResetBehavior`, default `clip`; the user's design, which replaced `at_limit` and `wrap` with no
  compatibility code) is what an add or a subtraction past an end does (`Register.added`): `clip` holds; `reset_clip`
  (shown `reset/clip`) goes to the minimum past the maximum and holds below the minimum; `clip_reset` the mirror;
  `reset_to_default`; `overflow` rolls round keeping what is left over; `reverse` bounces off the end, what is left over
  carrying on back, and counts the other way until the other end (`Register.reversed`, the direction kept beside the values
  by `Turned` in `playback/registers.py`, carried from scene to scene by `RegisterTimeline.end_turned`, and put forward
  again by any set or reset); or `pick_random` from minimum to maximum, drawn
  from a generator of the render's own (`REGISTER_SEED_OFFSET` in `playback/song_renderer.py`),
  unseeded with the song. `reset_each_scene` (default false) sets the register back to its
  default as each scene first starts (`SongRenderer._resets_of`, `WrittenScene.is_first_play`).
- A step's `ax_set` sets AX to a value before anything adds to it, blank leaving it as it is
  and 0 setting it to 0, held between the register's minimum and maximum and never wrapped
  (`Register.held`). A step's `ax_add` adds to AX as it plays. Both happen even with no note,
  when probability drops it or when a Mute When statement silences it, and once for a ratchet.
- `ax_note` moves the note along the scale by AX's value, up for `1` and down for `-1`, which
  drum patterns can't use, and `ax_velocity` adds AX's value to the velocity for `1` or takes
  it off for `-1`, keeping the velocity from 1 to 127 (`_used_values` in
  `playback/pattern_player.py` sums each register's value times its row's sign).
- Within a step: sets, then adds, then uses (`+Note`, `+Vel` and the bound velocity), then
  probability decides whether the note sounds. Going past an end does what
  `reset_behavior` says.
- A step's statements (the user's design; `STATEMENT_ROWS`, `StepStatement`): the rows `stop_c1` to `stop_c5`, `restart_c1` to
  `restart_c5` and `mute_c1` to `mute_c5` hold, step by step, the five parts of one Conditional Execution statement of each kind
  (register, operator, value, comparison, against), which `Pattern.get_statement` puts together (`conditions.statement_of`) and
  `Pattern.set_statement` writes whole; parts that make no whole statement are no statement. A rest keeps them. Each is read as
  the step is reached, before the step's own sets and adds (`before_step`, `BEFORE_OWN_CHANGE`), in the order stop, restart,
  mute. Stop: the clip is done as if every repeat were played (`Pass.done`). Restart: the pass ends there and counts as a
  repeat, never on the first step played. Mute: the step is silent and still changes the registers. A step that stops or
  restarts makes none of its own changes. A looping clip whose pattern holds a stop is a clip that ends
  (`SongRenderer.fills_its_scene`, `Song.scene_never_ends`), giving up at `MAX_CLIP_REPEAT` passes. A scene with a clip whose
  pattern can cut a pass short is played until its registers settle (`SongRenderer._decide`: `RegisterSolo`, then
  `RegisterTrial` rounds until the changes and lengths repeat); every other scene keeps the two plays, and what is asked of a
  pattern or a scene to choose between them is asked once a render (`_cutting_of`, `_is_settled_by_playing`). The old condition
  rows `ax_bx`, `ax_cx` and `ax_dx` are gone, with no conversion.
- Draws (the user's design; `composition/draw.py`, `playback/draws.py`): a song's `draws: {AD: {direction, slots, value_min,
  value_max, conditions_redraw}}`, four fixed names like the registers, the file naming only those changed. `slots` is a list of
  whole numbers from -99 to 99 or blanks (`~`), 1 to 64 of them, each within the draw's `value_min` and `value_max`; moving an end
  of the range moves every slot past it, and a value typed past an end is held at it. `direction` is any pattern direction or
  `serial` (every filled slot once a round, in a random order) or `any` (a filled slot at random every time). A blank slot is
  passed over without using up a draw, and a draw with no value adds nothing. A pattern's Use Draws rows, `ad_note` to `dd_note`
  and `ad_velocity` to `dd_velocity`, hold 1 (add), -1 (subtract) or 0 as the register rows do, and `ad_reset` to `dd_reset` are
  toggles; a step uses a draw once however many of its rows use it, whatever its note, its probability or its conditions decide,
  and resets come before it draws. A scene's `reset_draws: [AD]` resets those draws as it first starts. The uses are counted with
  the registers' changes (`RegisterChange.draws` and `draw_resets`), drawn in the scene's timeline in time order and then track
  order, and a draw stands where the last scene left it (`RegisterTimeline.get_end_draws`); a step sees a draw's value beside the
  registers' values, as having drawn nothing (0) before its first use.
- A statement of Conditional Execution reads a draw as it reads a register (`file_format.VALUE_NAMES`): in its first part, its
  value or what it is compared with, in a step's Stop, Restart and Mute When and in every table. It looks at the value the draw
  last gave, unless the draw's `conditions_redraw` is on: then a step whose statements read it draws from it just before they are
  read (`RegisterRecorder.before_statements`, `CONDITION_DRAWS`), the step's one draw from it, and the step's Use Draws rows hear
  that value. A table only looks, as a pass starts; drawing for a table that reads a draw that redraws is not built yet.
- Registers are shared by every track. `SongRenderer` plays each clip once with a
  `RegisterRecorder` to collect changes (the same play that finds lengths, since registers only
  change pitches, velocities and whether a note sounds), a `RegisterTimeline` applies them in
  time order and then track order, and the finished clips read it with a `RegisterReader`
  (`src/llamatron/playback/registers.py`). The counting play runs only when some pattern sets or
  adds (`Setlist.changes_registers`).
- Values carry from scene to scene. A scene's `reset: [AX, DX]` sets those back to their defaults
  as it first starts, not on its repeats.
- A scene's and a clip's `set_registers: {AX: 0}` and `add_registers: {AX: 1}` (the user's design, shown as Set Registers and
  Increment Registers): a scene's sets act as it first starts and its adds on every play; a clip's sets act on its first pass in
  each written-out play of its scene and its adds as every pass starts (`registers.at_pass`). They are register changes like a
  step's, recorded at places before any step's (`SCENE_PLACE`, `CLIPS_BEFORE_STEPS`), so the order at one moment is resets, the
  scene's sets, the scene's adds, each clip's sets, each clip's adds, the steps. The user declined changing that order.
- Conditional Execution (the user's name and design; `composition/conditions.py`): a table of at most `MAX_STATEMENTS` statements,
  each a dictionary `{register, operator, value, comparison, against}` holding only the parts its operator takes
  (`parts_of`): a comparison and a value, `odd` or `even` alone, or a sum, its number, a comparison of the result and what it is
  compared with. A value is a whole number or a register's name. Whole-number math; a typed 0 after `/` or `%` is refused and a
  register that divides holding 0 makes the statement true. Any true statement trips the table. The tables: `bypass_when` on a
  generator (every kind, `BYPASS_SETTING`), a chain (written `{steps: [...], bypass_when: [...]}`, the plain list otherwise), a
  scene, a clip and a track, and `skip_when` on a clip and a track, never a scene. The registers are read once as each pass of a
  clip's pattern starts, after that moment's sets and adds (`ClipSlotPlayer._play_passes`).
- How a table acts (`playback/clip_slot_player.py`): a sit-out pass is played and dropped for a rest of its length, so it counts
  toward Repeat and makes every register change, since a register change may never depend on a register's value (the counting play
  must find them all). A bypass runs the generator on the whole clip and splices the tripped passes' untouched notes back
  (`_kept_where`), so a generator's own state never depends on the registers; a generator that changes the clip's length is taken
  whole unless every pass tripped; a Density, Swell or Articulate named in a chain is judged at the clip's first pass; a Drift's
  table is never read, and the Drift page shows none. A table stops only what it is on: a clip's, scene's and track's bypass leave out the chains of that clip.
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
  what uses one (`.claude/format/MODEL.md`, "Renames"). A song that sets no groove names the default one, `none`,
  which `Song.names_item` says, so the factory groove `none` counts that song as a use.
- `tests/playback/test_grooves.py` and `tests/tui/test_tui_grooves.py` test it.

### Follow action and Launch together

- A clip's `follow_action` (`ClipSlotSetting.FOLLOW_ACTION`, one of `FOLLOW_ACTION_CHOICES`:
  `with_scene`, `next` or `off`, `FollowAction`, Live's word, shown as Advance on the clip page,
  the user's name for it) is what the clip sends down in real-time playback when it finishes,
  the user's design. No export reads it. Blank means the set's
  `default_follow_action` (`SetlistSetting.DEFAULT_FOLLOW_ACTION`, same choices, default
  `with_scene`, `DEFAULT_FOLLOW_ACTION`), written only when set, so the demos stay as they
  are; `Setlist.follow_action_of(clip_slot)` resolves it. The clip page's Advance field shows
  the resolved value as the clip's own, with no "(default)" choice, and the File/Global page's
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
  plays through FluidSynth, which the tracker starts (`.claude/features/REALTIME_PLAYBACK.md`): its `channel`
  is ignored and its `gm_sound` is sent as a program change, which no MIDI port's instrument is
  sent. Every example plays this way as it comes: its `real_time` is on, every unmuted track has
  an instrument on `*FluidSynth`, the melodic ones with a sound and the drum tracks sharing one
  called `drum kit`, and every track that plays only drum patterns is a drum track, which
  `tests/app/test_examples.py` holds them to. A new set has no instruments.
- Accents and default velocities, the user's design: a pattern's `accent` row (`Row.ACCENT`, a `RowOfToggles`, `AccentRow` in
  the Basics section under Velocity); a track's and an instrument's `default_velocity` (1 to 127) and `accent` (`MIN_STEP_ACCENT` 0
  to `MAX_STEP_ACCENT` 127; a track's `DEFAULT_TRACK_ACCENT` 15, an instrument's `DEFAULT_INSTRUMENT_ACCENT` 0). A step with no
  velocity plays at `Song.default_velocity_of(track)`: the track's, else its instrument's, else `DEFAULT_VELOCITY`; an accented
  step adds `Song.accent_of(track)`, the track's accent plus its instrument's, before the registers' additions, held to MIDI's
  range. `PatternPlayer` reads both once a clip. Tests: `tests/playback/test_accents.py`.
- Keyswitches, the user's design: an instrument's `keyswitches` (`InstrumentSetting.KEYSWITCHES`) is its Keyswitch Map, a list
  of `KEYSWITCH_SLOT_COUNT` (10) slots numbered 0 to 9, each nothing or a `name` and a `note` (`KeyswitchSetting`, a MIDI
  number, either alone allowed; `Keyswitch`, `NO_KEYSWITCH`, `KEYSWITCH_SETTINGS`), written only when a slot holds something,
  and its `keyswitch_lead` (`InstrumentSetting.KEYSWITCH_LEAD`, milliseconds from `MIN_KEYSWITCH_LEAD` 0 to
  `MAX_KEYSWITCH_LEAD` 500, 0 unless written) is how long before its note a keyswitch is sent. A pattern's `keyswitch` row
  (`Row.KEYSWITCH`, `RowOfKeyswitches`) holds for each step the slots that are on, a list of slot numbers lowest first or
  nothing; a pattern stores slot numbers, never notes, so the pattern works with any instrument's map, and a rest doesn't
  keep the row. The render gathers a step's slots whenever the step holds a note, whatever its probability or conditions
  decide (Claude's choice, since a switch that is missed leaves the plugin in the wrong articulation), a tie lengthening
  them with the note (`playback/pattern_player.py`, `SwitchedSlots` in `grid/keyswitch.py`), and the clip slot's player turns
  slots into the notes of the track's instrument (`_switch_notes` in `playback/clip_slot_player.py`, `SwitchNote`): none for
  a track with no instrument, an instrument on `*FluidSynth` or a slot with no note. They are kept on the clip apart from
  its sounds (`Clip.get_keyswitches`, `get_keyswitch_lead`), so no generator, transpose, scale, strum, Grab, Hocket,
  visualizer or Scene View sees them; only what moves the step's note in time moves them, a groove, a Rush and a Drag. Their
  velocity is `KEYSWITCH_VELOCITY` (100). `exporters/timing.py`'s `keyswitch_events` gives their times, the lead taken off
  (worked out from the tempo by `SongRenderer.keyswitch_lead`) and one cut where the same note starts again; at one moment a
  keyswitch is sent before a note (`KEYSWITCH_ON` before `NOTE_ON` in `exporters/midi_messages.py`, and first in
  `realtime/timeline.py`, whose `Playing.switch` marks them so that `realtime/score.py` counts none as a heard note). The
  MIDI file, the stems, the MIDI clips and the Live set carry them (`_Arrangement.KEYSWITCHES`); the General MIDI file, the
  WAV and every FluidSynth route leave them out (`MidiGeneralMidi.KEYSWITCHES`, `Route.keyswitches`). An import reads them
  as ordinary notes. `tests/playback/test_keyswitches.py` holds all of this.
- A track's `instrument` (`TrackSetting.INSTRUMENT`, in `Track.REFERENCES`) names one, or is
  blank for none, which leaves the track out of real-time playback. Renaming an instrument
  updates the tracks, and `tracks_naming` lists the uses.
- The visualizer settings, the user's design: the set's `visualizer` and a song's `visualizer` (`SetlistSetting.VISUALIZER`,
  `SongSetting.VISUALIZER`, a mode's name or left out) name the mode Arrange's visualizer key shows first, the song's over
  the set's (`Setlist.visualizer_for`); the set's `hidden_visualizers` (`SetlistSetting.HIDDEN_VISUALIZERS`, a list of modes'
  names, written only when it holds one) are the modes the key, `[` and `]` and Cycle leave out. The names are
  `VISUALIZER_NAMES` in `composition/file_format.py`, held to the modes by `tests/visualizers/test_visualizer_choices.py`, so that a set is
  read without the visualizers. A visualizer setting is never refused, the user's rule, since modes come and go: anything
  that isn't a mode's name is made sensible as it's read and set (`sensible_visualizer`, `sensible_hidden_visualizers`), an
  unknown default becoming none and an unknown hidden mode dropped, with no correction asked about. A new visualizer setting
  follows the same rule.
- The set's `generator_order` (`SetlistSetting.GENERATOR_ORDER`, the user's design) is the order the Generators page lists
  every generator in, each entry `{kind: name}`, written only when set; it's never refused (`sensible_generator_order`, an
  entry that isn't a generator's kind and a name is dropped), `Setlist.ordered_generators` leaves out entries for generators
  gone and adds any it doesn't name after the rest, kind by kind, a rename keeps a generator's place and a copy comes straight
  after its original (`copy_item`). Nothing in the render reads it, and since the Generators page lists by type, sorted, no page shows or changes it. `tests/generators/test_generator_order.py` tests it.
- The set's `open_generator_types` (`OPEN_GENERATOR_TYPES` in `composition/file_format.py`), a list of kinds of generator, says which
  types the Generators page shows open; every other type is closed. Like `closed_pattern_groups` it is no setting and no part of
  the set's data, undo or what counts as unsaved; a kind with no generator is forgotten and anything else there is ignored.
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
  until inversions came. `tests/playback/test_grab_roots.py` tests it.
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
  draws as before. `LlamaData.names_item` and `rename_references` handle a list of names.
- A chain is a list of steps like `arp: name` or `auto_ratchet: name`, with no settings of its
  own.

## Keys a File Holds That llamatron Does Not Know (the user's rule)

- Every object's reader passes over the names it does not know (`pass_over_unknown` in `composition/checks.py`), the set's
  sections and a pattern's rows included, without a word, so that a file from before a feature was removed still opens, and
  nothing unknown is kept or written again: a save writes only what llamatron understands. No code migrates a removed setting.
  A wrong value for a setting that exists is still refused or corrected as before. A musician's `by_section` is read the same way
  (`MusicianSettings.pass_over_unknown_names`): a kind of section or a setting of one that it does not know is passed over. No dialog lists what was passed over, and a chain's
  step of an unknown kind of generator is still refused (the user dropped both from the plan).
