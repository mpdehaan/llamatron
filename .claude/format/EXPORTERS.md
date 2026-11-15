# Exporters and the MIDI Import

Reference notes for Claude, one part of `.claude/format/`: each exporter and the MIDI import. `CLAUDE.md` says which part to read for which work.

## Exporters

- Exporters live in `src/llamatron/exporters`, with their tests in `tests/exporters/`.
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
- Note timing for every writer comes from `src/llamatron/exporters/timing.py`.
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
  track is a drum track (`SongRenderer.gm_sound_of`). A track whose instrument has no sound sends
  none. `midi_track(channel=, program=)` writes either. `internal_tools/preview_midi.py` writes it, and
  `tests/exporters/test_general_midi.py` tests it.
- `WaveFluidSynth` (`exporters/wave_fluidsynth.py`, `--to wav`, `<name>.wav`), the user's design, is the
  WAV export for anyone with no DAW: the General MIDI file of only the unmuted tracks whose instrument
  plays through FluidSynth (`ClipColumn.plays_through_fluidsynth`, set by
  `SongRenderer.plays_through_fluidsynth`), written into a temporary folder that is always removed, played
  by FluidSynth faster than real time with the SoundFont, then normalized to a peak 1 dB below full scale
  (`exporters/wave_level.py`, which `internal_tools/normalize_wave.py` shares). It refuses with
  `ERR_WAV_NEEDS_FLUIDSYNTH` or `ERR_NO_FLUIDSYNTH_TRACKS` before writing anything. The tests that export
  every kind leave it out, and `tests/exporters/test_wave_fluidsynth.py` tests it with a stand-in for FluidSynth.
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

