# Playback

Reference notes for Claude, one part of `.claude/format/`: playing a song into clips, the command line, performance, sounds and lengths in a render, and real-time playback. `CLAUDE.md` says which part to read for which work.

## Playback and the command line

- `SongRenderer(song).render()` (`src/llamatron/playback/`) plays a song into a `ClipGrid`, with
  a `ClipSlotPlayer` for each clip slot and a `PatternPlayer` for each pass through a pattern. Tests use
  the helpers in `tests/support/rendering.py`.
- `src/llamatron/cli.py` is the command line, installed as `llamatron`. There's deliberately no
  separate command for the tracker, and `python -m llamatron` is the same as the command.
- Without `--to` it opens the tracker, on a set if one is named. `--autoplay`,
  `--autoplay-quit-when-finished`, `--launch-for-recording` and `--max-seconds` make the tracker
  play the set on its own (`.claude/tracker/RECORDING.md`, "Launching to play on its own"); they need a
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

## Performance

- The tracker re-renders or re-estimates the song as people edit it, loading and saving should be
  quick, and real-time MIDI playback may come later, so the time to render a song and the work
  done after each edit are both watched.
- Lengths and times are exact `Rational`s (`src/llamatron/support/rational.py`), never floats.
  `Rational` does only what the program needs and is about twice as fast per operation as the
  standard library's `Fraction`. `tests/music/test_rational.py` checks it against `Fraction` for every
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
  `tests/music/test_note.py` holds each copy to the constructor's note and the constructor's refusals.
- What a pattern holds is gathered once for each clip that plays it (`PlayedPattern`, kept by
  the `PatternPlayer`): every step's values (`Pattern.get_every_step_values`, which fills only
  the rows that hold anything, where asking all thirty rows about every step was an eighth of a
  render), and whether any step sends a CC value (`Pattern.sends_controls`), adds to a register
  (`adds_to_registers`) or uses one (`uses_registers`). A pattern with none of those skips that
  work on every step, and `tests/playback/test_registers.py`, `tests/composition/test_tracks_and_controls.py` and
  `tests/composition/test_composition.py` test both sides of each. A pass takes all its steps from the
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
  speedup changed nothing. `tests/grid/test_clip_lengths.py` checks the arithmetic lengths against a
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
- `tests/music/test_length.py` holds every `Length` method to `Fraction`. `tests/music/test_sound.py` holds
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
  design. What is left of it is in `dev_notes/IDEAS.yml` under "Real-time
  MIDI, what's left". How the tracker drives it is in `.claude/tracker/ARRANGE.md`, "Real-time
  playback".
- Render first, then only schedule: `song_timeline(grid=, routes=)` in `realtime/timeline.py`
  turns a `ClipGrid` into one time-ordered list of `Playing` events across every track, the
  scenes laid end to end as the MIDI export lays them, read from the same note timing
  (`exporters/timing.py`), so everything that makes the music has already happened. Each event
  carries its whole-note time, its seconds, the port and channel of its track's `Route`, its
  kind and bytes, and a `Tag` of scene place and track name, so that one clip's events can be
  dropped or stopped. A track with no route, which is a track with no instrument, and a muted
  track are left out. Note offs sort before note ons at one instant.
  `tests/realtime/test_realtime.py` holds every example's timeline to its MIDI export, tick for tick.
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
  `tests/support/sender_under_capture.py`, run by `tests/realtime/test_realtime.py` in an interpreter of its own
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
- `tests/data/sample_sets/heavy_chain.yml`, a chain of twenty generators with grabs and chords, is
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
  docstring states and `tests/realtime/test_realtime.py` holds it to, with every example played from the
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
  (`PROGRAM_CHANGE`, sorted before the note ons at its instant). `tests/realtime/test_fluidsynth.py` and
  `tests/tui/test_tui_playback.py`'s `TestFluidSynthPlayback` test it.
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

