# Generators

Reference notes for Claude, one part of `.claude/format/`: every generator and what each does to a clip. `CLAUDE.md` says which part to read for which work.

## Generators

- Each generator is a plugin, a folder of `py_legacy/src/llamatron/engine/generators/` (217 A, 224 A, 233 A): `declaration.py` holds its
  `PLUGIN`, a `GeneratorPlugin` of `model/schema/generator_plugins.py` (its name, the section of a set that holds its generators, its
  settings' class and its strings module), `__init__.py` its `NAME` and `SECTION`, read as `arp_plugin.NAME` through
  `from llamatron.engine.generators import arp as arp_plugin` (234 A), `strings.py` every word only it shows (`MSG_LABEL`,
  `MSG_KIND_WORD`, `MSG_CAPTION_WORD`, `MSG_CHANGED_WORD`, a step-row plugin's `MSG_STEP_ROW_NAME` and `MSG_STEP_ROW_NOTE`),
  `model.py` its settings (244), `controller.py` its logic, the controller's methods it fills in (`engine/generators/controller.py`,
  asked through `engine/generators/registry.py`), and `generator.py` the code a chain's step runs, where it has one. Wherever the plugins are
  listed or written by kind, they come in the order of their names (240 A); the Model asks the contract's questions
  (`sections_by_name`, `names_by_section`, `names_naming`, `is_generator_entry`) and never names a plugin, and a class whose
  settings list chains says so in `CHAINS_NAMED_BY`, read through `references_of`, so that every plugin's section is covered. The
  Model finds the plugins through `generator_plugins.plugins()`, which imports every folder's declaration once, the first time
  any is asked for, and names no plugin itself. What several share is beside the folders: `base.py` (`ClipGenerator`),
  `parts.py`, `settings_base.py` (`GeneratorSettings`, which every settings class extends); each plugin keeps its own defaults and
  `blend.py`, which morphing uses. Pieces that the plugins and the clips' and tracks' own settings share are in `engine/parts/`:
  `scale_moves.py` (`along_scale`). The tests are in `tests/engine/generators/`.
- Each subclasses `ClipGenerator` (`base.py`) and implements `_generate(clip)`, which reads
  `clip.resolved_sounds()` and returns new sounds and a length. A generator works on sounds
  and never on `Note`s ("Sounds and lengths in a render"). `generate(clip)` then returns a new `Clip` with the same name and scale,
  leaving the original unchanged, so generators can be chained.
- A generator's list of values must only step through notes and chords, so rests never use up a
  value (`tests/engine/generators/test_generator_list_steps.py` checks this, so add new list generators there).
- Chain generators work on finished clips rather than patterns, so a chain follows scale changes.
  Pattern generators that write steps are a separate idea in the ideas files of `.claude/features/`.

### Generators as paint

- The user's way of seeing generators and chains: a generator is paint. A chain
  applies it to exactly the clips that should have it, and editing the generator afterwards
  changes everything painted with it at once. So where a setting also exists on a scene, a
  clip or a track, the generator is still worth having, for the clips across a song that should
  share one shape, and a demo can show both: the quick field on one clip, and one generator
  painted on many and edited in one place.

### Enabled and the built-in generators

- Every generator's settings hold `enabled` first (`GENERATOR_ENABLED`, given by `GeneratorSettings.__init_subclass__`): a
  generator of the set's list is on unless written false, and `Setlist.chain_run` leaves one switched off out of what a chain or
  a list runs. Its page shows Enabled first after Name.
- A clip slot and a track each hold a built-in generator of every kind whose declaration gives a `built_in_place` (Chords 10,
  Arpeggiator 20, Guitarify 30, Timing 60, Phrasing 70), written by kind under `built_in` (`HoldsBuiltIns` in
  `model/objects/built_ins.py`), each read as its plugin's settings with `built_in=True`, so switched off until `enabled: true`.
  A built-in has no name; it is changed only through its holder's `set_built_in_setting`, so the holder's revision moves, and a
  rename reaches into it (`names_item`, `named_items`, `rename_references`).
- `SongRealizer.chains_of` gives a clip's `ChainRun`s (`engine/realizer/chain_runs.py`), worked out once a render: the built-ins
  placed below `generator_plugins.LIST_PLACE`, the chains of the clip's, the scene's and the track's lists, then the built-ins
  placed above it; a clip's built-in switched on stands in for its track's of the same kind. A built-in runs as a chain of one
  `BuiltInStep`, which holds its settings (`settings_in`, as a `ChainStep` asks the set), under the name `(built-in)`, which keeps
  its state from clip to clip on the track as Restart says. A scene has no built-in.
- `tests/engine/realizer/test_built_ins.py` tests them.

### Timing: Rush, Drag, Shorten and Glide

- The generator section `timings` (`TimingSettings` in `engine/generators/timing/`), the user's design, which combined four
  generators of their own: four parts (`parts.py`: `PARTS`, Rush, Drag, Shorten, Glide), each `{part}_steps`, a list of 1 to 16,
  each true or false, drawn as every toggle is; `{part}_step`, a time, the pattern's step size unless set; and `{part}_amount`:
  a Glide's 1/256 to 1/16, 1/128 by default, a Shorten's 10 to 95, 70, a Rush's and a Drag's 0 to 50% of a step, 15 and 20
  (`DEFAULT_AMOUNTS`). A part's row (`step_row.py`, `StepRow`) reads four unlit steps until written; a part is in force only while
  a step is lit (`is_lit`), so a new Timing generator changes nothing.
- `TimingController.make_generator` gives a `TimingGenerator` (`generator.py`) running the lit Glide and then the lit Shorten, each
  a `StepRowGenerator` changing the single notes starting on a lit step: a Glide holds one past its place into a next note of
  another pitch, a Shorten plays its share with a rest after; chords, rests and held sounds are left alone, so a note the Glide
  held is not shortened.
- The Rush and the Drag run on no clip itself: `moving_rows` gives a `MovingRow` for each lit one, `SongRealizer.nudge_plan`
  gathers every one a clip's chains name into a `NudgePlan` (`engine/timing/nudge_plan.py`) on the finished clip, and
  `timed_events` adds their moves together to each slot's grooved start, never before the clip's start, so a step on in both moves
  by the difference. A grab reads notes without them. All four follow the one Restart by their offset.
- Its page is drawn from its view (`SectionView` for each part, holding a `TimeView`, the amount and a `StepsView`), `ENTER` on a
  Steps field opening the shared `StepRowEditor` (`screens/shared/step_row_editor.py`). The song wizard writes a track's rush and
  drag as one Timing generator of the track's name (`timing_generators` in `wizards/create_song/arranger.py`).
- `tests/engine/realizer/test_step_rows.py` tests them; `12_acid_glide.yml` is the demo, its drop loosening the drums with a Rush
  and Drags.

### Musician

- The generator section `musicians` (`MusicianSettings`, kind `musician`, `MusicianSetting`), under the documents' heading
  "Band Generators": one kind of generator for every player of a band, whose Instrument
  setting chooses among the fifteen classes of `generators/musician.py` (`MUSICIANS`), each a subclass of `Musician` that
  says the instrument's lowest and highest note and what its player does unasked (`USUAL_GIVES_WAY`, `USUAL_NOTES`). One
  kind with an Instrument setting was chosen over fifteen kinds, so that a new instrument is a small class and no new page.
- Settings: `instrument`, `chords_from` and `tune_from` (tracks, which a rename follows, `REFERENCES`), `activity`,
  `loudness` (-3 to 3), `looseness` (0 to 3), `gives_way`, `accents`, `notes`, `range`, and `by_section`, a dictionary by
  kind of section (`SECTION_KINDS`) of `plays` (true or false) and `played` (a form), checked by
  `check_musician_by_section`. A value that is what the musician does unasked is left out of the file; for `gives_way` and
  `notes` that is the instrument's.
- What it does, in order (`Musician._generate`): rests where the section's `plays` is off; follows the chords of the track
  named (through `FollowChords`, pitched instruments only); the section's form; activity; gives way to the tune; holds or
  shortens notes; accents; range; loudness and looseness. Every note heard is one the clip wrote. Chance is used only for a
  loose player's loudness, drawn from the render's seed.
- `SongRealizer.make_generator` builds it with `Surroundings` (`section` from the written scene's scene, `chords` a
  `ChordSource` as Follow Chords gets, `tune` a `TuneSource` of the named track's finished clip, `engine/realizer/tune_source.py`,
  found by `SongRealizer.tune_heard`, which refuses a circle of tracks as `chords_followed` does).
- `generators/parts.py` holds `Part` and `parts_of`, the sounds of a clip with their starts, which Phrasing shares.
- Stage 1 shapes the clip's own notes. Riffs by section, a musician choosing among patterns, are not built.
- `tests/engine/generators/test_musician.py` and `tests/interface/tracker/test_tui_musician.py` test it; `24_musician.yml` is its demo.

### Phrasing

- The generator section `phrasings` (`PhrasingSettings`, kind `phrasing`, `PhrasingSetting`), the user's design, under
  Articulation: four lists of plain words and nothing else, the user's choice of a simple page over more power. `line_bars`
  (1, 2 or 4, shown "1 bar", "2 bars", "4 bars", default 2), `breath` ("none", "quick", "deep", default "quick"), `rise_and_fall`
  ("none", "a little", "a lot", default "a little") and `notes` ("choppy", "as written", "flowing", default "as written"). No
  number is shown, no row of the pattern marks anything for it, and nothing is by section: a section that wants another delivery
  names another Phrasing in its clip's chain.
- What the program decides (`generators/phrasing.py`): a breath shortens a line's last note, an eighth for "quick" and a quarter
  for "deep", by half the note at most, by nothing where the tune already rests or the note sounds on into the next line, and
  never drops a note; a line's main note is its longest note starting on a bar's start or middle in the line's second half, the
  higher and then the later of two as long; the main note stays as loud as written and the others are softer, the last softest,
  a note that starts a bar a little louder (`RISE_DEPTHS`); "choppy" halves a note up to a quarter and takes an eighth off a
  longer one; "flowing" holds each note of a line but the last until the next, stopping short of a note of its own pitch.
  The breath is a note length, not milliseconds, so far. Nothing is random.
- `SongRealizer.make_generator` builds it with the bar's length (`PhrasingSettings.generator_for(where=, bar=)`).
- `tests/engine/generators/test_phrasing.py` and `tests/interface/tracker/test_tui_phrasing.py` test it; `23_phrasing.yml` is its demo.

### Hocket

- The generator section `hockets` (`HocketSettings`, kind `hocket`, `HocketSetting`), the user's
  design: `source`, the name of a track of the song it plays in, and `restart`. A new
  one has no source and hands out nothing.
- It runs on no clip itself (`GENERATOR` is `None`). For each written scene,
  `SongRealizer.hocket_turns` works out once the source track's notes as turns, the notes that
  start together being one turn (`source_turns`, through `timed_events` with `grooved=False`, from
  the source's finished clip, its own pattern and chain, never notes handed to it), and deals them
  round the pool (`hocket_pool`: every track but the source whose clip names the Hocket, in the
  song's track order), starting from the turns the run's earlier scenes used, as Restart says. A
  rest passes no turn and a chord passes whole. A track's share (`handed_notes`, `HandedNote` in
  `engine/timing/handed_note.py`) is set on its finished clip (`Clip.set_handed`), and `timed_events` adds
  the handed notes to the clip's own, moved by its groove and its Rush and Drag, cut at its end, never by the hocketing track's transpose or the generators after the Hocket in its chain, the user's answer.
  A Hocket a clip of its own source names is skipped there.
- The source track plays its own pattern as ever; the demo mutes it with the track's Mute. A
  muted source still hands out notes, and a source the song lacks hands out nothing.
- Renaming a track renames a Hocket's source (`Song.rename_item` passes a track's rename to the
  set's hockets, whose `REFERENCES` name `Section.TRACKS`), the user's rule.
- `tests/engine/generators/test_hocket.py` tests it; `17_hocket_shanty.yml`, which replaced `grab.yml`, is its demo.

### Guitarify

- The generator section `guitarifies` (`GuitarifySettings`, kind `guitarify`, `GuitarifySetting` in `model/schema/file_format.py`),
  the user's design: one generator of two halves, each with a switch (`shape`, `strokes`, both on unless written false), every
  setting left out for its default, so a new one writes `{}`. `generators/guitarify.py` is the generator, a `ClipGenerator` in
  the chains like any other.
- Shape (`tuning` of `TUNINGS`, `position` 0 to 12 with 0 the open position, `capo`, `user_strings` 3 to 6 counted from the highest,
  `single_notes` of `SINGLE_NOTES`): a chord is voiced again as its pitch classes on the strings (`OPEN_STRINGS`), at most one
  note a string, within `REACH` frets, the best of every way by `_cost`: a note left out costs most (the root most of all, the
  fifth least), then the bass not being the chord's lowest written note, a silent string between sounding ones, each silent
  string, and frets from the position. Each chord's voicing is worked out once a generator. A single note is left, made a
  power chord (root, fifth, octave from the lowest string that reaches the root) or the triad its place in the clip's scale
  builds, then voiced; a note outside the scale builds none. Degrees are settled into notes by the clip's scale first.
- Strokes (`bar`, a list of `STROKES`, at most 32; `accents` beside it; `cell`, a time setting; `let_ring`; `spread` in
  milliseconds, `fade` and `loose_timing` in percent, `upstroke`, how many top strings, 0 for all): the bar goes round under
  the clip, following the song's bars from the generator's Restart (`continuation.offset`), and each cell's stroke strikes
  whatever note or chord sounds there. A `stab` (every string) and a `muted_bass` (the lowest string) stop at `SHORT_LENGTH` of
  their cell whatever Let ring says, and a muted bass without an accent plays at `MUTED_BASS_VELOCITY`, never softened twice. A `squeal` is one note `SQUEAL_ABOVE` the lowest, short, never softened. `single_notes` also offers
  `octave`, `third_above` (the scale's) and `double_stop`, none voiced; `color` (`CHORD_COLORS`) adds a ninth or moves or drops the third before a chord
  is voiced; `approach` (`APPROACHES`) plays a chord that differs from the one before a fret away for `APPROACH_LENGTH` first, never the clip's first. Struck strings are held sounds (`HELD`) staggered by the spread, which is turned into
  time by the scene's tempo, the one generator handed it (`GeneratorSettings._with_tempo`, `SongRealizer.make_generator`);
  a strum takes at most half the time to the next stroke, and every delay is put on a grid of `STRUM_TICKS` to a whole note so
  that lengths stay exact fractions under `FINEST_LENGTH`. A string stops at the next stroke, or with Let ring when the same
  pitch is struck again or the chord ends, never past the chord. Mute is a quarter of a cell at half velocity; where a bar has
  an accent, the other strokes play at four fifths. Loose timing draws from the render's seed.
- The ready-made bars are `READY_BARS` in `engine/generators/guitarify/schema.py`, named by `ReadyBar`; a bar that matches one exactly is
  shown by its name (`ready_bar_matching`), and nothing in a file says which was picked. Strum mode, below, strums chords as
  written instead.
- `tests/engine/generators/test_guitarify.py` tests it; `21_guitarify.yml` is its demo, a Strum-mode scene and twenty scenes by genre, guitars only.

### Restart

- Every generator's `restart` (`GENERATOR_RESTART`, `Restart`: every_clip, on_new_scene,
  whole_song, every_clip by default, `GeneratorSettings.get_restart`), the user's design, Drift alike, whose documents suggest "whole song" (`mainstreet_hoedown.yml`'s drift
  says it, so it plays as before).
- A run starts at the clip's written scene, at the first play of its scene, or at the song's first
  (`SongRealizer.run_start`); `run_offset` is how far into the run the clip starts and `run_span`
  how long the run lasts. Generators that follow time take the offset: `Progression`,
  the shape generators in `ClipSlotPlayer._shaped` (whose ramp spans the run), and a
  Guitarify's strum by the beat (`StrumPlan.offset`).
- Generators that keep state are handed a `Continuation` (`generators/base.py`: offset, span and
  the state the same track's latest clip before in the run left), made by
  `SongRealizer.continuation`, which works out the clips before first, with no grabs waiting; each
  clip starts from the state it was handed and `end_state()` is kept by `keep_end_state`, by pass,
  written scene, track and the generator's place (its kind, name and how often it came up in the
  chains). Voice leading's chord before, an arpeggiator's
  random state, and a Guitarify's strum down up (`StrumPlan.chords_before`, from the chords the
  render loop counted) carry on. Each track keeps its own copy (the user's answer).
- A drift's clock starts at its run's start (`SongRealizer.drift_origin`, `DriftPlay.effects`
  and `trigger_times` taking origins).
- `tests/engine/realizer/test_restart.py` tests it.

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
- It takes a groovebox's settings: `octave_range` (1 to 4) plays the chord again in higher
  octaves, `octave_jump` is `after_chord` or `after_each_note` (descriptive names rather than
  numbers), and `offsets` is a step track of 1 to 16 values, each moving its note along the
  clip's scale (or by half steps with no scale).
- A `None` step is silent and doesn't use up a chord note, and the offsets restart with each
  chord. With offsets or a range, a single note is arpeggiated as a chord of one note.

### An arp's step

- An arp's `step` may be left out, which means the step size of the pattern its clip plays
  (`make_generator`'s `default_step`), the user's rule; a new arp leaves it out.

### Drift

- `drifts` is a generator section (`DriftSettings`, kind `drift`), the user's design, but no generator runs on a clip: a chain step naming a drift is skipped by
  `ClipSlotPlayer._through_chain`, and the render reads the drift as one process for the song
  (`engine/generators/drift/play.py`, `DriftPlay`, made by its controller's `modulation` and held for each render by `engine/realizer/modulations.py`'s `Modulations`).
- Its own settings: `every` (whole notes, blank for a bar of the song's time signature),
  `steps_to_b` (default 16) and `direction` (`DriftDirection`: forward, loop, pendulum, brownian).
  A drift has no seed of its own, nor has an arpeggiator: each draws from the render's seed, so every play is a new take (the user's
  rule); a file's old `seed` on either is passed over. Each version's values are named with its letter, `a_` or `b_` (`versioned`,
  `DriftValue`): `velocity`, `probability`, `degree`, `degree_random`,
  `scale`, `scale_probability`, `root` and `root_probability`.
- Its clock runs from the song's top, the written-out scenes laid end to end
  (`SongRealizer.scene_start`). Each trigger's picks (`DriftPlay.picked`) are worked out once and
  kept, so every clip and both plays hear the same drift: numbers blended by the position,
  rounded; the random degree from the drift's chooser; a scale or root B's with a chance of the
  position, then kept with its probability.
- The `PatternPlayer` reads a drift at each step's song time (`DriftEffects`): velocity added after the draws' `Vel+=`,
  probability added and held from 0 to 100, the degree added to the note's move along the scale
  (not on drums), and a scale or root override building the scale the degrees play in
  (`_scene_scale_at`).

### Chords: Progression, Follow Progression, AutoChord and Voicing

- The generator section `chords` (`ChordsSettings` in `engine/generators/chords/`, kind `chords`), the user's design, which
  combined a Progression, a Follow Chords and a Voice leading: `mode` (`MODES`: `voicing`, the default, `progression`,
  `follow_progression` or `auto_chord`, the user's design, the modes exclusive of one another); AutoChord's `chord` (`CHORDS` in
  `auto_chord.py`, `from_scale` by default) and `note_on_top` (default false); the progression's `chords`, 1 to 32 degrees from 1 to 7, a new one `[1]`, with `accidentals`,
  `inversions`, `scales`, `qualities` and `tensions` beside them (`ProgressionSetting`, read as long as the chords,
  `_lined_up`), and `every`, a time setting, a bar when left out; `chords_from`, a track of the song, which a rename of the track
  follows (`REFERENCES`); and the voicing's `voice_leading` (on when left out in Voicing mode alone, `voices()`),
  `lowest_octave` and `highest_octave` (defaults 4 and 6, never crossing, `limits_of`) and `root_in_bass` (default false).
- `ChordsController.make_generator` gives a `ChordsGenerator` (`generator.py`) running the mode's generator, a `Progression`
  (`progression.py`), a `FollowChords` (`following.py`) or an `AutoChord` (`auto_chord.py`: each single note, a one-note chord
  too, made its chord by `chord_on`, From scale's triad by `triad_above`, both in `engine/parts/chords_on_notes.py`, which
  Guitarify shares; a note outside the scale, or with no scale, left alone; held sounds and each part of a phrase too), then
  the `VoiceLeading` (`voicing.py`) where it voices; its end state
  is the voicing's, which a Restart carries on. `MOVES_PITCHES`, so a drum pattern is skipped; `FOLLOWS_TRACKS`, the track it
  names rendered first. The Musician reuses `FollowChords`.
- A `Progression` moves each sound to the chord current at its start (`chord_at`, counted from the
  clip's start in lengths of `every`, looping): a plain degree along the clip's scale by
  `along_scale` (`engine/parts/scale_moves.py`), a note outside the scale keeping its distance from the
  scale note below; a degree with a sharp or flat by the exact half steps to that degree, one
  more or less; a chord whole, its inversion moving its lowest one or two notes up an octave; a
  note that would leave the MIDI range staying as it was. `ClipSlotPlayer._through_chain` skips
  it on a drum pattern, still counting it for the seeds.
- `model/values/progressions.py` says what the chords are in a `NamedScale`, needing no tracker:
  `quality_of` and `roman_numeral`, and the
  named progressions (`NAMED_PROGRESSIONS`, keyed by `NamedProgression`, written in numerals
  against a major key), matched to a scale by `matched_to`: a chord on a scale note is that plain
  degree, any other the degree above with a flat, or the one below with a sharp.
- `tests/engine/generators/test_progression.py` tests it; `06_chord_progression_generator.yml` and `07_blues_chords.yml`
  are its demos.

- `SongRealizer.chords_followed` hands `FollowChords` a `ChordSource`
  (`engine/realizer/chord_source.py`) of the followed track's finished clip in the same written scene, after its chains, the counting
  pass's clip in the counting pass, each worked out once; None for no track, a track the song lacks, one with no clip there or
  the clip's own track. Tracks following each other in a circle raise `ERR_CIRCULAR_FOLLOW`.
- A note moves up the clip's scale by the place of the chord's root in the scale, and the half steps left over for a root
  between two scale notes; a note a third, fifth or seventh above the figure's root then takes the chord's own note where the
  scale's is a half step off, so a chord from outside the scale is followed. A chord goes on through rests; nothing moves
  before the first. A drum pattern is skipped (`KINDS_MOVING_PITCHES` in `engine/realizer/clip_slot_player.py`).
- Voicing: The first chord of a clip plays as written; each chord after
  tries every inversion of its notes at every octave within `OCTAVES_TRIED` of where it was
  written, keeps those whose notes all lie in the range and in MIDI's, and takes the one whose
  sorted notes move least from the chord before (note by note when both have as many notes,
  otherwise each to the nearest), the smaller octave move on a tie. With `root_in_bass`, the
  lowest written note stays and only the notes above it are voiced, above it, against the notes
  above the bass before. A chord no voicing fits stays as written, and single notes are left
  alone. 
- `tests/engine/generators/test_progression.py`, `test_follow_chords.py` and `test_voice_leading.py` test each part; the page's
  `06_chord_progression_generator.yml`, `07_blues_chords.yml`, `22_follow_chords.yml`
  and `05_voice_leading.yml` are its demos.

### Strum: a Guitarify in Strum mode

- A Guitarify's `mode` (`MODES` in `engine/generators/guitarify/model.py`: `guitar`, the default, or `strum`), the user's design,
  which replaced the Strum generator and the clips' and tracks' own strum settings, with no backward compatibility. In Strum mode
  its `make_generator` gives an `UnchangedClip` (`generators/base.py`), so the chain changes no notes, and its `strum` gives
  `strum_values()`, a `StrumValues` (`model/objects/strum.py`): its `direction` (`DIRECTIONS`: by_the_beat, the default, down, up,
  down_up) and the four settings Guitar mode shares, Spread in milliseconds, Fade, Loose timing and Upstroke strings (0 for every
  string), with Guitarify's defaults.
- `SongRealizer.strum_plan` takes the strum of the last generator a clip's chains name whose controller gives one, and sets a
  `StrumPlan` (`engine/timing/strum_plan.py`) on the finished clip beside its groove: the gap in whole notes at the scene's tempo,
  the beat, and a seed fixed for the render. `timed_events` in `engine/timing/timing.py` plays it (`_strummed`): the
  notes that start together sound low to high or high to low, each a gap after the last, varied by
  the loose timing, the last faded by the fade, an upstroke keeping only its top strings, each note
  ending as written. Grabs read the notes unstrummed. `tests/engine/generators/test_guitarify_strum.py` tests it; the first scene
  of `21_guitarify.yml` is its demo.

### Time settings

- Every time setting chooses from one list, `TIME_CHOICES` in `model/schema/file_format.py`, the
  user's rule: an arp's `step`, a drift's `every` and a shape's `over` (and,
  when built, the harmonizer's delay). The list runs 1/64, 1/32, 1/16, then each triplet after
  its straight value and the dotted one after that up to 1/2, then `1 bar`, `2 bars`, `4 bars`,
  `8 bars` and `16 bars` (`ONE_BAR_WRITTEN`, `BARS_WRITTEN`).
- A file holds a length in whole notes or a count of bars as that text. `time_length` in
  `model/file/checks.py` reads either, a count of bars as `Bars`, and `in_whole_notes(time=,
  bar=)` turns it into a length with the song's bar, which the render passes on (an arp through
  `make_generator(bar=)`, a drift through `DriftPlay.every`, a shape through
  `ClipSlotPlayer._shaped`). Any positive length is still read, so an older file's `every: 2`
  plays as before. `tests/model/test_time_settings.py` tests it.

### Density, Swell and Articulate: the Shapes generator

- The shapes (`Shape`, `SHAPES` in `model/schema/file_format.py`), the user's design: how many of a clip's notes play, how loud and how long, each a percentage ramping
  from a start to an end. A scene and a clip slot each hold `density_start`, `density_end`,
  `density_over`, `density_then` and the same for `articulate_` (`PLACED_SHAPES`; how loud a scene or a clip plays is its
  velocity and velocity ramps, `.claude/format/FILE_RULES.md`, which a Shapes generator's Swell scales again) (`shape_setting`,
  described by `shape_settings()` in `model/objects/shapes.py`), and a Shapes generator
  (section `shapes`, `ShapesSettings` in `engine/generators/shapes/`) holds all three under the same names, `density_start` to
  `articulate_then`, with `swell_accent` and its Restart. Its controller names `SHAPES`, which the Realizer asks of each chain's
  step (`registry.shapes_of`, `ClipSlotPlayer._name_shapes`); a shape the generator leaves with start and end blank
  (`get_shape` returning None) is not named, so the clip's or the scene's own stays in force. Its page is drawn from its view
  (`ShapeView`, `NumberView`, `RestartView`) by `PluginEditor`.
- The limits: Density 0 to 100, Swell 0 to 200, Articulate 10 to 200, Accent 0 to 50
  (`model/schema/limits.py`). A part left blank plays as 100 (`UNCHANGED`), so a song that sets
  none plays as it always has; a shape is in force where its start or end is set
  (`shape_values`). `over` is a length in whole notes, blank for the whole span; `then`
  (`ShapeThen`: hold, repeat, bounce, hold by default) says what follows a ramp.
- Like a drift, a shape generator runs on no clip itself (`GENERATOR` is `None`):
  `ClipSlotPlayer._shaped` reshapes the finished clip after its chains, outside the counting
  play, taking the last generator of each kind the clip's chains name, else the clip's own,
  else its scene's. A scene's ramp spans the scene's length, a clip's or a generator's the
  clip's.
- `engine/realizer/shapes.py` does it on sounds (`reshaped`): each position keeps its place, a dropped
  note becoming a rest of its length. Density keeps a note when the density passes the
  threshold of its place's strength (`strength`, `PLAYS_ABOVE`: the bar's start always, its
  middle above 6.25, a beat above 12.5, an eighth above 25, a sixteenth above 50, anything finer
  only at 100), in the song's time signature, chords whole, drums too. Swell scales each note's
  velocity (a blank velocity counting as 127), held from 1 to 127, the accent adding its share
  on a beat and stronger. Articulate scales the written length, a longer note held over the
  rests after it but never past the track's next note or the clip's end.
- `tests/engine/realizer/test_shapes.py` tests them; `edm_density.yml`, `14_bolero_swell.yml` and
  `13_acid_articulate.yml` are their demos.

### Blend

- `Blend(target, amount, mode)` moves a clip towards an equally long target, with
  `BlendMode.LEFT`, `RIGHT` and `MIDDLE` sweeping the target in from one side or the center.

