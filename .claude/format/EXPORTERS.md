# Exporters and the MIDI Import

Reference notes for Claude, one part of `.claude/format/`: each exporter and the MIDI import. `CLAUDE.md` says which part to read for which work.

## Exporters

- Exporters live in `py_legacy/src/llamatron/exporters`, with their tests in `tests/exporters/`.
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
  say, is one class and its place in those two lists, and `tests/exporters/test_exporter.py` fails if an
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
- Note timing for every writer comes from `py_legacy/src/llamatron/engine/timing/timing.py`.
- `tests/app/test_matrix.py` is an end-to-end example of the classes underneath the tracker.

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
  track is a drum track (`SongRealizer.gm_sound_of`). A track whose instrument has no sound sends
  none. `midi_track(channel=, program=)` writes either. `py_legacy/internal_tools/preview_midi.py` writes it, and
  `tests/exporters/test_general_midi.py` tests it.
- `WaveFluidSynth` (`exporters/wave_fluidsynth.py`, `--to wav`, `<name>.wav`), the user's design, is the
  WAV export for anyone with no DAW: the General MIDI file of only the unmuted tracks whose instrument
  plays through FluidSynth (`ClipColumn.plays_through_fluidsynth`, set by
  `SongRealizer.plays_through_fluidsynth`), written into a temporary folder that is always removed, played
  by FluidSynth faster than real time with the SoundFont, then normalized to a peak 1 dB below full scale
  (`exporters/wave_level.py`, which `py_legacy/internal_tools/normalize_wave.py` shares). It refuses with
  `ERR_WAV_NEEDS_FLUIDSYNTH` or `ERR_NO_FLUIDSYNTH_TRACKS` before writing anything. The tests that export
  every kind leave it out, and `tests/exporters/test_wave_fluidsynth.py` tests it with a stand-in for FluidSynth.
- Everything the MIDI writers share, the tick rate, `MidiEvent`, message building and
  `midi_track`, is in `exporters/midi_messages.py`.
- `ClipTree` (`py_legacy/src/llamatron/exporters/clip_tree.py`) takes a directory, a `ClipGrid` and a name,
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
  (`py_legacy/src/llamatron/exporters/ableton_project.py`) writes a Live 12 set to
  `<directory>/<name>.als`, with clips in Session View and the scenes laid end to end in
  Arrangement View.
- A `.als` file is gzipped XML with no public documentation, so it edits a template Live saved,
  `py_legacy/src/llamatron/templates/live12.als`, installed with the package, whose first MIDI track must
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

- `py_legacy/src/llamatron/importers/` makes a MIDI file a song of the open set, the user's design. `MidiImport` (`midi_import.py`) reads the file once (`midi_reading.py`: a part for
  each channel of each track, times as exact whole notes, tempos, time signatures and key
  signatures) and `imported(setlist=, choices=)` makes the song as data without changing the set,
  as often as `ImportChoices` change; `add_imported` (`writing.py`) adds the scales, the
  patterns and the song through the set's own reading.
- Voices (`voices.py`): drums a voice per sound, named by General MIDI or `perc 1`; a part
  whose notes sound together further apart than one hand reaches split at middle C into
  `<track> treble` and `<track> bass`; notes that start and end together at one velocity in a
  fixed chord symbol's shape one chord when chords are asked for, in root position or in an
  inversion (`chord_named`), the step's degree its root and the Inversion row moving its lowest
  notes up as the file has them, read by `music_theory/harmony/chord_naming.py` in the user's order, plainest first: a
  chord or inversion; that with one change, doubled (`undoubled_pitches`, checked by `doubled_pitches`), a
  four-note chord with tones left out (Omit) or one tension; then two changes, such as D7's 3rd, 7th and 13th;
  then a slash chord, the lowest note (or two an octave apart, Bass Octave) a 5th or more under the rest and
  within the octave below them, where the Realizer plays the Bass. Where readings tie (`Hearing`), a root in
  the song's first key wins, then the step before's chord; among omissions the sevenths, the dominant first,
  and with a tension the voicings that keep the 3rd and 7th, the 13th and the 9th first. The
  Bass is written as scale steps from the root in the key (`bass_note_of` in `steps.py`). So octaves,
  3rds, 6ths, a chord with its root on top, three-finger sevenths and F/G are one step; the rest ranked into voices
  lettered `a`, `b`, each the first free at a moment, so that no voice overlaps itself and no
  note is left out. A legato line, single notes none starting together, each held into the next (`legato_line`), is one
  voice, each slurred note ending where the next starts with Glide, which runs it on by `GLIDE_OVERLAP`, and the import
  says how many (`MSG_WARN_GLIDED`): on an instrument that plays one note at a time (`MONOPHONIC_SOUNDS`: the basses,
  solo strings, voices, solo brass, reeds, pipes and synth leads, by the part's program) wherever notes overlap, so an
  oboe line plays on a monosynth with its portamento, on any other only where every overlap is under half the earlier note
  and reaches no further than the next. On every part but a line of one note at a time, a held note or chord rings with
  its gate under the voice's next notes (`lines_of`, `Played.rings`), as a pianist holds a chord under a moving line, so a
  hand is one track; it is written with a gate rather than ties, and no phrase is cut across it.
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
- The Import Wizard's cut (`phrase_cut.py`, `PhraseCutter`), used where the longest pattern is asked for in
  bars (`ImportChoices.longest_bars`, `WIZARD_LONGEST_BARS`, eight): the song is cut into phrases of
  that many bars at clean steps, after a lead of whole bars, an introduction or a pickup, chosen
  so that the most phrases repeat (`lined_up_phrases`). A phrase may end across a note held for
  whole steps (`can_cut`), the next pattern of the clip's list carrying it on with ties at its
  start (`Voice.carried_into`), as the Realizer holds a note on through patterns of ties alone
  (`_held_through_rests` in `clip_slot_player.py`); a section, a scene, still starts only where
  no note is held across, and each phrase is written in the key of the last boundary before it;
  each voice's phrase is a pattern every
  phrase alike shares, or, where the phrase is heard nowhere else, its halves or quarters that come
  back at least twice more elsewhere are patterns of their own, the stretches between them one
  piece each (`phrase_pieces`). Each phrase has a family, that of the earlier phrase at least 70%
  alike step by step, a verse sung again to other notes (`phrase_families`, `LIKE_ENOUGH`); no note
  changes for it. Phrases gather into sections, one a scene: a new one at a key or tempo change,
  where music the song plays more than once begins, first time and every time, where that music
  gives way to music heard once, and after four phrases (`sections_of`); a scene's clip plays its
  phrases' pieces as a list, or one pattern repeated where every phrase repeats it. Sections are
  lettered by their families, A, B, and A' for one beginning as an earlier one did (`lettered`).
  With `ImportChoices.numbered` (`Naming`), scenes are named `S01 A, bars 1-8`, each run of scenes in one key
  shares a scale named after the scene that begins it, `S01_C_major`, a new one at every key change, a return
  too (the user's rule), patterns go in the group of the letter of the first scene that plays them and are
  named after it, `a1`, `a2`, numbered through the group, and each clip is named after its scene's number
  and its patterns, `S01:a1,a2`, up to 60 characters. Where a file names no key, its keys are worked out phrase by phrase,
  a change taken where it holds for two phrases (`keys_by_phrase`). The import dialog's Longest
  pattern in steps keeps the older cut.
- Licks (`importers/licks.py`, the user's design), after the Import Wizard's cut, where every bar is one length: each
  track's clips are cut into bars and rewritten as the fewest licks of 1 to `MOST_BARS` (4) bars, a hard limit, each clip a
  list of them. The cost of a track's licks is the bars of music they hold, plus `LICK_PRICE` (2 bars) a lick and
  `ENTRY_PRICE` (a quarter bar) an entry of a clip's list; each run of bars heard twice or more is tried as a lick, every
  clip cut again into its cheapest list (`cheapest_list`), and kept where the cost goes down, so A A A C becomes A, A, A, C
  and a pair heard once stays inside its pattern. Exactness: a bar line a gate or a CC slide crosses is never cut
  (`rung_bar_lines`, `slides_on`), bars held together longer than four are one piece; a bar that begins by tying a note on
  matches only one with the same note held into it; each lick states its CC values at its first step (`stated_controls`);
  each lick takes the longest step size it fits (`coarsened`). On the user's files every file plays as it did without it.
- Quantizing (`step_size_for`): a file whose notes all start on a grid, as a score's do, keeps
  them; a file played by hand goes on the longest grid nearly all its notes start near (within
  an eighth of a step, 98% of them, `NEAR_A_STEP`, `MOST_NOTES`), a triplet grid tried before the
  shorter straight one; a file played too freely for any goes on the finest step allowed,
  1/64 unless asked (`ImportChoices.finest_step`, `FINEST_STEP_SIZE`). The import says how many
  notes it moved (`Imported.moved`).
- Instruments (`writing.py`): each track plays through an instrument named after the General
  MIDI sound of its channel's program (`MidiPart.program`: the first program change on the
  channel in its track, or anywhere in the file), `acoustic_grand_piano` where the file sets
  none, through FluidSynth until the user picks a device; drum tracks through `drums`. An
  instrument the set has by that name already is used as it is, keeping the user's device.
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
  (`MSG_WARN_` in `user_strings/importing.py`). `comparison.py` compares two MIDI files' notes and
  tempos to llamatron's tick, and each CC brought in as its value over time
  (`control_difference`: the largest difference and the longest time off), which the round trip in the tests and `py_legacy/internal_tools/import_check.py`
  use. The groove demo is the one example that differs, since a swing's offsets fall between
  any step.

