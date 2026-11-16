# Generators

Reference notes for Claude, one part of `.claude/format/`: every generator and what each does to a clip. `CLAUDE.md` says which part to read for which work.

## Generators

- Generators live in `src/llamatron/generators`, with the same test layout as exporters: `arp`
  and `auto_ratchet`, the two that a chain can use, `blend`, which morphing uses, and `base`.
- Each subclasses `ClipGenerator` (`base.py`) and implements `_generate(clip)`, which reads
  `clip.resolved_sounds()` and returns new sounds and a length. A generator works on sounds
  and never on `Note`s ("Sounds and lengths in a render"). `generate(clip)` then returns a new `Clip` with the same name and scale,
  leaving the original unchanged, so generators can be chained.
- A generator's list of values must only step through notes and chords, so rests never use up a
  value (`tests/generators/test_generator_list_steps.py` checks this, so add new list generators there).
- Chain generators work on finished clips rather than patterns, so a chain follows scale changes.
  Pattern generators that write steps are a separate idea in `.claude/IDEAS.yml`.

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
- `tests/playback/test_step_rows.py` tests them; `14_acid_glide.yml` is the Glide and Shorten demo and
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
- `tests/generators/test_hocket.py` tests it; `19_hocket_shanty.yml`, which replaced `grab.yml`, is its demo.

### Guitarify

- The generator section `guitarifies` (`GuitarifySettings`, kind `guitarify`, `GuitarifySetting` in `composition/file_format.py`),
  the user's design: one generator of two halves, each with a switch (`shape`, `strokes`, both on unless written false), every
  setting left out for its default, so a new one writes `{}`. `generators/guitarify.py` is the generator, a `ClipGenerator` in
  the chains like any other.
- Shape (`tuning` of `TUNINGS`, `position` 0 to 12 with 0 the open position, `capo`, `strings` 3 to 6 counted from the highest,
  `single_notes` of `SINGLE_NOTES`): a chord is voiced again as its pitch classes on the strings (`OPEN_STRINGS`), at most one
  note a string, within `REACH` frets, the best of every way by `_cost`: a note left out costs most (the root most of all, the
  fifth least), then the bass not being the chord's lowest written note, a silent string between sounding ones, each silent
  string, and frets from the position. Each chord's voicing is worked out once a generator. A single note is left, made a
  power chord (root, fifth, octave from the lowest string that reaches the root) or the triad its place in the clip's scale
  builds, then voiced; a note outside the scale builds none. Degrees are settled into notes by the clip's scale first.
- Strokes (`bar`, a list of `STROKES`, at most 32; `accents` beside it; `cell`, a time setting; `let_ring`; `spread` in
  milliseconds, `fade` and `loose_timing` in percent, `upstroke`, how many top strings, 0 for all): the bar goes round under
  the clip, following the song's bars from the generator's Restart (`continuation.offset`), and each cell's stroke strikes
  whatever note or chord sounds there. Struck strings are held sounds (`HELD`) staggered by the spread, which is turned into
  time by the scene's tempo, the one generator handed it (`GeneratorSettings._with_tempo`, `SongRenderer.make_generator`);
  a strum takes at most half the time to the next stroke, and every delay is put on a grid of `STRUM_TICKS` to a whole note so
  that lengths stay exact fractions under `FINEST_LENGTH`. A string stops at the next stroke, or with Let ring when the same
  pitch is struck again or the chord ends, never past the chord. Mute is a quarter of a cell at half velocity; where a bar has
  an accent, the other strokes play at four fifths. Loose timing draws from the render's seed.
- The ready-made bars are `READY_BARS` in `composition/guitar_bars.py`, named by `ReadyBar`; a bar that matches one exactly is
  shown by its name (`ready_bar_matching`), and nothing in a file says which was picked. The Strum generator and the strum
  settings of a track and a clip are apart and unchanged (the user's choice).
- `tests/generators/test_guitarify.py` tests it; `23_guitarify.yml` is its demo, twenty scenes by genre, guitars only.

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
- `tests/playback/test_restart.py` tests it.

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
  `quality_of` and `roman_numeral`, and the
  named progressions (`NAMED_PROGRESSIONS`, keyed by `NamedProgression`, written in numerals
  against a major key), matched to a scale by `matched_to`: a chord on a scale note is that plain
  degree, any other the degree above with a flat, or the one below with a sharp.
- `tests/generators/test_progression.py` tests it; `06_chord_progression_generator.yml` and `07_blues_chords.yml`
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
  alone. `tests/generators/test_voice_leading.py` tests it; `05_voice_leading.yml` is its demo.

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
  ending as written. Grabs read the notes unstrummed. `tests/generators/test_strum.py` tests it; `13_classic_strum.yml`
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
  shapes. Masks stack because each silences what it misses. `tests/generators/test_euclid.py` tests it;
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
  plays as before. `tests/composition/test_time_settings.py` tests it.

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
- `tests/playback/test_shapes.py` tests them; `edm_density.yml`, `16_bolero_swell.yml` and
  `15_acid_articulate.yml` are their demos.

### AutoRatchet and Blend

- `AutoRatchet(counts)` chops each note or chord into that many adjacent equal repeats, using the
  next count in a cycle, and rests don't use one up.
- `Blend(target, amount, mode)` moves a clip towards an equally long target, with
  `BlendMode.LEFT`, `RIGHT` and `MIDDLE` sweeping the target in from one side or the center.

