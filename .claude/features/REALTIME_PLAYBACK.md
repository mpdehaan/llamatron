# Real-Time Playback


The package is three parts (step 6 of the subsystem moves): `realtime/render_process/`, the score, its building ahead and
changing, and the player; `realtime/sender_process/`, the engines, the outputs and CoreMIDI, with the process in `process.py`;
and `realtime/devices/`, the ports found and watched (`ports.py`) and FluidSynth.
Reference notes for Claude, one of `.claude/features/`: the engine and the Realtime Sender Process that play a set as MIDI in real time, and how the tracker's pages drive them. `CLAUDE.md` says which file to read for which work.

## Real-time playback

- `py_legacy/src/llamatron/realtime/` plays a rendered song out of the computer's MIDI ports, the user's
  design. What is left of it is in the ideas files of `.claude/features/` under "Real-time
  MIDI, what's left". How the tracker drives it is under "Real-time playback on the pages" below.
- Render first, then only schedule: `song_timeline(grid=, routes=)` in `realtime/render_process/timeline.py`
  turns a `ClipGrid` into one time-ordered list of `Playing` events across every track, the
  scenes laid end to end as the MIDI export lays them, read from the same note timing
  (`engine/timing/timing.py`), so everything that makes the music has already happened. Each event
  carries its whole-note time, its seconds, the port and channel of its track's `Route`, its
  kind and bytes, and a `Tag` of scene place and track name, so that one clip's events can be
  dropped or stopped. A track with no route, which is a track with no instrument, and a muted
  track are left out. Note offs sort before note ons at one instant.
  `tests/realtime/test_realtime.py` holds every example's timeline to its MIDI export, tick for tick.
- `PlaybackEngine` (`realtime/sender_process/engine.py`) holds the events still to send in a heap, sends each
  when its time comes (`send_due`), remembers which notes are sounding, and silences on
  `stop_tag` (that tag's sounding notes) and `stop_all` (every sounding note, then CC 123 and
  CC 120 on every channel used). `forget(tag=, after=)` forgets a clip's events from a time on,
  which is how an edit while playing replaces the passes not yet started. It reads a `Clock`
  and writes to `MidiOutput`s and nothing else: a `SteppedClock` and `RecordingOutput`s drive
  it in tests with no time passing, and `MonotonicClock` and `RtMidiOutput` in the process.
- `RealtimeMIDISenderProcess` (`realtime/sender_process/process.py`), the Realtime Sender Process, runs
  the engine in a spawned process, since a thread drifts by the interpreter's switch interval
  while the screen draws and a process measured within 0.11 ms. The tracker's side sends
  `start`, `add`, `forget`, `stop_tag`, `stop_all` and `close` over a pipe. The process sleeps in
  half-millisecond slices until 1.5 ms before the next event and spins to the moment, since
  sleep is loose on macOS. With `recording=True` it opens `RecordingOutput`s and `close`
  returns when the timeline started and every message sent, which the suite's short lag test
  and `py_legacy/internal_tools/realtime_report.py` (`py_legacy/internal_tools/realtime_report.sh`) read.
- Two drivers, chosen once as the sender starts (`driver=`, `sender_process.default_driver()`): `TIMESTAMPED` where CoreMIDI is
  (`coremidi.is_available()`, macOS, asked once a run) and `IMMEDIATE` elsewhere, the sending above through python-rtmidi, kept
  whole as the driver for Linux and every other system. `engine_for` makes each driver's engine and outputs; both are tested on
  the Mac. The user's direction: the best fast path on macOS, nothing of it given up, and the generic way kept working.
- The timestamped driver: `ScheduledPlaybackEngine` (`realtime/sender_process/scheduled_engine.py`), a `PlaybackEngine` that hands each event
  `HORIZON_SECONDS` (0.1 s) ahead of its moment to a `ScheduledOutput`'s `send_at(data=, at=)`, at a reading of
  `time.perf_counter`, so that the system delivers it on time however late the process wakes; the loop asks the engine
  `next_action()` and `spins()` and, for this engine, sleeps until the next event enters the horizon, the pipe's poll waking it
  for a message, rather than spinning. `CoreMidiOutput` (`realtime/sender_process/coremidi.py`) reaches CoreMIDI by ctypes: one client a process
  (`core_midi()`), a destination found by its own name or the name shown, the one python-rtmidi lists, as `RtMidiOutput` finds a
  port (equal, or starting with the name), and stamps on the mach clock tied to `perf_counter` as the port opens. Measured with
  `py_legacy/internal_tools/coremidi_timing.sh` under twenty busy processes: ten minutes, worst 0.27 ms with no note over 1 ms late,
  against 10.35 ms and 412 of 5,200 late sending as each comes; on the IAC bus, 0.071 ms against 6.0 ms; and about a fifth of the
  processor time, 0.10 s against 0.55 s over a 22 s run, start included.
- Taking back: a forget, `stop_tag` and `stop_all` flush the ports holding events they forget (`ScheduledOutput.flush`), hand
  back again what is kept, and undo, latest first, what handing the forgotten events did to `_sounding`, each `Handed` record
  keeping the tag sounding on its note before; the channels `stop_all` silences are those of events whose moments have come
  (`_heard_channels`), so a stop silences exactly what the immediate engine would. `silence` (Ctrl+T) forgets nothing, as the
  immediate engine forgets nothing, and counts again the notes handed to start after it. Within `GUARD_SECONDS` (1 ms) of a
  flush an event may have gone out or not: a note off, kept or forgotten, is sent, a note on forgotten is answered with a note
  off, and any other event kept is taken to have gone out. `tests/realtime/test_scheduled_engine.py` holds random plays of
  adds, forgets, stops and Ctrl+T heard alike by both engines, moment for moment.
- `CoreMidiOutput.flush` gives the output port up and opens another, which drops what the old one had scheduled, in about
  0.25 ms; CoreMIDI's `MIDIFlushOutput` is never called, since it reaches a destination another program made, FluidSynth's among
  them, as a one-byte packet 0xFF, MIDI's system reset, which FluidSynth answers by resetting its programs and controls (found
  reading raw packets at a destination of the test's own; the IAC bus receives nothing). `tests/realtime/test_coremidi.py` holds
  that no flush reaches a destination as a reset. With `recording=True` the timestamped driver opens
  `ScheduledRecordingOutput`s, which keep each message at the moment it was stamped with and forget on a flush what was still to
  come, as CoreMIDI does.
- `realtime/sender_process/outputs.py` is the only module that imports `rtmidi`, inside `midi_library()`,
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
- `py_legacy/internal_tools/iac_check.py` (`py_legacy/internal_tools/iac_check.sh`) is the one tool that touches real MIDI hardware, by
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
- `Score(song=, routes=, seed=)` (`realtime/render_process/score.py`) is a song rendered for launching: it
  renders with `SongRealizer`, groups the grid's rows by the scene they were written from
  (`WrittenScene.get_scene`), so that a scene that repeats is one scene of several rows, and
  keeps each clip's events counted from its scene's start (`events`, `played_events(scene=,
  track=, start=, play=)`, which moves them to a moment and tags them with the number of that
  play), each scene's seconds and its start when the song plays from the top, which clips loop,
  each clip's follow action (`Setlist.follow_action_of`, an empty slot counting as "With Scene")
  and whether each scene launches together, each clip's notes as they sound (`clip_notes`, a `ClipNotes` of
  `realtime/render_process/clip_notes.py`, made when first asked): for the lights (`is_sounding`), for cutting a clip ahead
  (`sounding_across`) and each note's number and velocity as the visualizer hears it (`heard`, through `Player.heard`), the repeats left
  (`repeats_left`) and how far into its play a clip is (`clip_elapsed`, for the clip's bar). A track with no route, or a muted one, has no events but is still a track of
  the score, so that its clips run silently and the arrangement keeps its shape.
- Events cross the pipe into the Realtime Sender Process as slim records (`sender_process.records_of` and `events_of`): a
  version byte, then for each event its seconds, its play's tag as a number (`RealtimeMIDISenderProcess.tag_number`) and its
  port's place, channel, kind, number and value (`RECORD`), read by the process as `Sent` events, five times faster than whole
  events, each holding a Rational and a Tag, and at a third of the size. Forgetting and stopping a tag send its number too.
- `Player(score=, sender=, now=, lead=)` (`realtime/render_process/player.py`) launches scenes and clips into a
  sender, the engine or the Realtime Sender Process, on the sender's clock; a launch from silence starts `lead` ahead of now
  (`LAUNCH_LEAD_SECONDS`, 3 ms, from the transport; none in the tests on a clock that never moves), so that its first window
  reaches the sender before it is due and every track starts at once. `play_song()`,
  `play_scene(scene)`, `play_clip(scene=, track=, forever=)`, `stop_clip(track)` and
  `stop_all()` are what the pages do; `tick()` turns the moments due within
  `LOOKAHEAD_SECONDS` (0.5) into plays, in time order, from a heap of `Moment`s, and hands the sender, in one message, every
  play's events due within `WINDOW_SECONDS` ahead (`Play.events_due`), never a whole clip as it starts; and
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
  looping clip hold its scene, and a demo whose kick and hat looped never left its first scene).
  A launch by hand while anything plays is always at the next bar of the song's time
  signature, the user's rule, as Live's default quantization: `next_bar()`
  counts bars from the start of the earliest clip playing, at the tempo of its scene's row
  there (`Score.bar_seconds`), what plays goes on until then, a clip or scene shorter than a
  bar hands over at its end, and with nothing playing the launch is at once. The starts that
  follow actions send are at the scene's end, where the export has the next scene start. At
  one time the follow actions' work runs before a launch by hand, so the human's launch is
  what plays. None of this is read by `SongRealizer` or an exporter: every export is byte for
  byte what it was.
- FluidSynth (`realtime/devices/fluidsynth.py`, `FluidSynth`), the user's design, is
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
  `LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE` names, which only `py_legacy/internal_tools/record_demo.py --fluidsynth` sets.
  A track through FluidSynth gets the channel the General MIDI export gives it, 10 for a drum
  track and the rest in turn among the unmuted tracks through FluidSynth (`Transport.routes`),
  and its `Route` carries the program, which `clip_timeline` sends at each clip's start
  (`PROGRAM_CHANGE`, sorted before the note ons at its instant). `tests/realtime/test_fluidsynth.py` and
  `tests/interface/tracker/test_tui_playback.py`'s `TestFluidSynthPlayback` test it.
- Live editing, the user's design (`Player.update_score`): a score rendered again after an edit is
  taken by each play from the moment the song's `live_responsiveness` says (`_switch_time`: at once,
  `LIVE_LATENCY_SECONDS` from now; the next bar of what plays, worked out by the old score; or the
  play's next pass, `Score.next_pass_start`), keeping its place in the music when the tempo changed
  (`Score.whole_at` and `seconds_at` move the play's start), ending the notes sounding across the
  moment and queuing the new notes from it (`Score.events_from`, which leaves out note offs whose
  note ons came before). A play that hasn't started is queued afresh; one the edit reaches only at its
  end takes whether it loops. The ends of scenes and repeats are planned again (`_plan_ends_again`).
  The player decides what comes next only `LOOKAHEAD_SECONDS` (0.5) ahead, where it was two seconds,
  so that an edit can still change a scene's end; each play's events go to the sender a window at a time, as long as the
  lookahead while a live edit still renders on the tracker's thread, so that the sender's queue outlasts the render; an edit
  that switches a playing clip at a moment first sends what the old notes play before it. `is_playing` counts only a moment that can still act (`_can_act`). A scene whose
  every clip loops plays in real time as long as its longest clip plays once, going round
  (`SongRealizer(looping_scenes_go_round=True)`, which only `Score` asks for), while the export still
  refuses it and a launch by hand still says so; that is what makes a scene looped while it plays
  play on.
- `PlaybackEngine.silence(channels=)` sends a note off for every note, then CC 123 and CC 120,
  on each (port, channel) given, whatever it knows to be sounding, and the process relays it as
  `silence`, for Ctrl+T. `start(at=)` lets the tracker start the engine's clock at a reading of
  its own clock, so the two agree on the seconds.

## Real-time playback on the pages

- `Transport` (`interface/tracker/transport.py`, `app.transport`) is the tracker's side of real-time playback,
  between the pages and the player ("Real-time playback" above). It answers
  `problem(track=)` before anything is rendered (with `ERR_FLUIDSYNTH_NOT_INSTALLED` when a track
  plays through FluidSynth and `fluidsynth_installed()` says no, the tests giving a `FakeFluidSynth`
  and their own answer): `ERR_ADD_INSTRUMENT_FIRST` when the set has no instrument, or no track's instrument can sound, `ERR_NO_TRACK_HAS_AN_INSTRUMENT`
  when no track has one and `ERR_NO_TRACK_HAS_A_DEVICE` when no track's instrument has a device
  (`has_a_device`; an example's instruments carry only a General MIDI sound), unless a `track` is
  given, which a listening page picks an instrument for, `ERR_DEVICE_NOT_CONNECTED` for each instrument whose device `output_port_names()`
  doesn't list, and the loop errors. `routes(instead=)` is each track's `Route` from its
  instrument's device and channel, `instead` mapping a track to an instrument for one listening.
  `play_song`, `play_scene(index=)`, `play_clip(index=, track=, song=, instead=, forever=)`,
  `stop_clip`, `stop_all` and `silence_everything` are what the pages call, and `is_playing`,
  `playing_scenes`, `is_clip_playing`, `is_track_sounding`, `scene_elapsed`, `repeats_left`,
  `song_position` and `song_seconds` are the lights' questions. `_ready` renders a `Score` when
  something is launched after the document's revision or the routes changed, so an edit is
  heard at the next launch, and `_sender_for` starts the Realtime Sender Process on the routes'
  ports, another when new ports are needed. `app.playback_timer` ticks it every `TICK_SECONDS`
  (0.1) while anything plays and redraws the page on top, and the timer stops with the last
  clip. `LlamatronApp.exit` closes it, and `set_document` forgets the song.
- `play_through(page=, play=, said=)` in `screens/shared/shared.py` tells the transport's problem in a
  dialog, or plays and says `said` on the status line, telling a `SongFileError` from the render
  as `ERR_CANT_PLAY_TITLE`.
- On Arrange, whenever a track's instrument can sound, Space is bound by where the cursor is: `PLAY_SONG` on the
  corner, `PLAY_SCENE` on a scene's name, `PLAY_CLIP` on a clip, and `STOP_PLAYING` or
  `STOP_CLIP` in their place while that plays (`play_scene_keys`, `play_clip_keys`, the header's
  keys on the corner). The status line says `playing from scene 1`, `playing clip (tune) on
  track (lead) on its own`, or `scene 2 starts at the next bar` when something was playing
  (`MSG_STARTS_AT_NEXT_BAR`, since `Transport.play_scene` and `play_clip` return whether the
  launch waits), `stopped` or `stopped track (lead)`. `time_text` reads `MSG_PLAYING_CLOCK`
  (`▶ 0:22 / 3:00`) while the song plays.
- `Page.go_back` and `show_page` call `stop_playing()`, which stops only a listening page's
  preview (`Transport.is_previewing`, a clip played `forever`), the user's rule: a song played from
  Arrange plays on through every page. A preview started while the song plays stops the song first.
  While anything plays, Arrange refuses to delete a track or scene with clips
  (`ERR_TRACK_PLAYING_SHOWN`, `ERR_SCENE_PLAYING_SHOWN`); inserting is allowed.
- Live editing, the user's design: every edit made while something plays is heard on it.
  A key or a dialog's answer tells the transport at once (`Page._record_edit` → `app.edit_made` →
  `Transport.edit_made`), which follows the edit on a one-shot timer once it has settled: 0.05 s
  (`KEY_SETTLE_SECONDS`) after a key that edits by itself, `LIVE_SETTLE_SECONDS` (0.15) after a typed
  digit, so that typed digits are heard once, and then looks every `BUILT_LOOK_SECONDS` (0.01) until
  the score is built, so that an edit is heard about 70 ms after its key. An edit made otherwise is
  noticed at a tick: `Transport.tick` calls `_follow_edits`, which waits until the document's revision
  has stayed the same for `LIVE_SETTLE_SECONDS`. Either way it renders the song again
  with the seed this play drew (`_seed`, one for the whole play, so an edit re-rolls no random part),
  finds each scene and track again after the edit (`_places_after_the_edit`: by the objects, else by
  place or name after an undo read the song again), and calls `Player.update_score` with the song's
  Live response. Another song made current stops what plays at once. An edit that can't be rendered,
  or that needs a MIDI port the sender hasn't opened, leaves what plays as it was, and the status line
  says why (`take_live_message`, `MSG_LIVE_EDIT_NOT_HEARD`, `MSG_LIVE_EDIT_NEEDS_A_DEVICE`).
- Listening (`screens/shared/listening.py`): `listen(page=, index=, track=, song=, name=)` plays one
  clip on its own and again and again (`forever=True`), asking with a `ChoiceDialog` of the
  set's instruments (`MSG_LISTEN_INSTRUMENT_TITLE`) when the track's instrument has no device,
  and says `MSG_LISTENING`. The clip page's `L` and buttons call it; while Real Time is off
  and FluidSynth is installed, the clip plays through General MIDI in the pattern preview
  (`PatternPreview.play_clip_of_song`), the user's rule. `L` again, or the Stop button, is `stop_listening`.
- The pattern preview (`interface/tracker/pattern_preview.py`, `app.pattern_preview()`), the user's design: `L` in the
  pattern editor and on the Patterns page (`pattern_listen_keys`, `listen_to_pattern`) plays the pattern
  at once with nothing asked, and `L` stops it. `PatternPreview` is a second `Transport` beside the
  song's (`Transport.shared()`), with a player and a sender of its own, so that it never stops the song
  and plays whatever the song's instruments can sound (`may_play`). It plays a copy of the set (`PreviewSet`,
  made again when the set's revision moves, so an edit is heard at the next pass) whose current song
  holds one scene, the pattern's clip on a track of its own, in the pattern's direction for as many
  passes as the direction takes to come round (`passes_to_come_round`), one pass for a direction that chooses as it goes, in the first of
  `scales_of_pattern`. Its one route is the song's Preview instrument, or General MIDI's piano on
  `PREVIEW_CHANNEL_BYTE` of FluidSynth, and the drum channel for a drum pattern always. `L` is not bound
  when nothing could sound (`can_sound`); a Preview instrument that cannot sound is refused on the status
  line (`refusal`). Leaving the page, Ctrl+T, quitting and a rename or delete of the pattern stop it.
- The read head: `Transport.playing_step(pattern)` gives the step that sounds, from a playing clip's
  elapsed time and its direction's order (`step_sounding`), None for a direction that chooses as it goes;
  `PatternEditor.playing_step` asks the preview and then the song's transport, and
  `RollDrawing.with_read_head` draws a thin line in `Style.READ_HEAD` at the step's left edge on copies
  of the kept lines, never over a note's bar. The rows view draws the sounding step's number in the same colour (`GridDrawing.step_line(sounding=)`). A song
  with a track on the preview's FluidSynth channel is stopped before a preview plays (`shares_a_channel_with`), the user's rule.
- Ctrl+T (`everywhere.silence`) says what `Transport.silence_everything()` did: note offs, CC
  123 and CC 120 on every (device, channel) the instruments use among the connected devices
  (`channels_in_use`), `MSG_SILENCED` or `MSG_NOTHING_TO_SILENCE`.
- `tests/interface/tracker/test_tui_playback.py` tests all of it, with a `Transport` on a `SteppedClock` and a
  `PlaybackEngine` of `RecordingOutput`s in place of the process, and
  `llamatron.interface.tracker.transport.output_port_names` patched to two ports of the test's own.


## Scores built ahead, and the MIDI ports seen from one thread

- The player's side (`realtime/render_process/playback.py`, `LocalPlayback`) holds the score builder, the scores, the player and the sender;
  the transport keeps the document's side (routes, problems, seeds, waiting for edits to settle, finding scenes and tracks again
  after an edit) and asks the player's side through commands, each naming what a score is made from (`Wanted`: the set's
  revision, the song's name, the routes as sorted pairs and the seed): `take_set` (the set's data as kept), `build`, `built`,
  `launch` (a `Launch` of a scene, a clip or clips, returning whether it waits for the next bar), `apply` (an edit's score),
  `use_ports` (with `renewed`, FluidSynth's port after FluidSynth started again), `silence`, `stop_clip`, `stop_all`, `forget`,
  `close`, `tick`; and questions for the lights and the visualizer. Every score is made from a copy of the set's data in the
  builder (`score_of`), so a live edit's copy is made off the screen's thread too. The previews' transports drop their score and
  end their sender through `_drop_score` and `_end_playback`. Whether FluidSynth is installed is looked for once a run
  (`fluidsynth.installed`, remembering `is_installed`), since every launch, listening page and WAV export asks.
- The render process (`realtime/render_process/playback_process.py` on the tracker's side, `realtime/render_process/process.py` in the process,
  `realtime/render_process/set_changes.py` for the set's data): in real runs the transport's player's side is a `PlaybackProcess`, answering as
  `LocalPlayback` does through a pipe; a transport given its own sender (the tests', the previews') keeps `LocalPlayback`, and a
  test may give the transport a `PlaybackProcess(recording=True)` (`Transport(playback=)`). The process holds a `LocalPlayback`
  whose player ticks on the process's own loop every `PLAYER_TICK_SECONDS` (0.02) while anything plays, and starts the Realtime
  Sender Process itself. The set crosses with each build and launch as the parts that changed since the last sent
  (`changed_items`: dictionaries key by key, lists of one length item by item, identity first), and the process applies them
  copying what leads to each change (`with_changes`), so a score being built never sees the set change. A launch waits for its
  answer (`LAUNCHED` with whether it waits for the next bar and a status, or `REFUSED` with the song's or the sender's problem,
  raised as `SongFileError` or `SenderNotStarted`); every other command is sent and not waited for, and stops, forgets and
  silences mean nothing to a process not yet started, which they never start. The process sends a `Status` after every tick
  while anything plays and once as it stops, and a `BUILT` notice for each score built; the tracker carries a status's elapsed
  times on by the system's monotonic clock, which every process shares, and keeps about a second of statuses for the
  visualizer's notes. The process starts on first use, under the start screen in `prepare`; `keep_ready` waits while it starts
  (`is_ready`). A launch's own status is read before its lead has passed, so its scene shows from the next status on.
- Ending the processes: the render process leads a process group of its own (`os.setpgrp`), which the sender it starts joins.
  `PlaybackProcess.close` asks it to close, so every sounding note gets its note off, gives it `CLOSE_SECONDS` (1) to answer and
  as long to end, then ends the whole group with SIGKILL (`end_process_group`, the process alone where the system has no
  process groups), so a stuck or hung process never keeps the tracker from quitting; Ctrl+C quits through `app.exit()`, which
  closes it, and `close` is registered with `atexit` as it starts, ahead of Python waiting for its child processes, so any other
  way out ends them too. The render process ends when the tracker's end of the pipe goes, closing its sender, and the sender
  ends when the render process's end goes. Should the tracker be killed outright while the render process's loop is stuck, a
  watcher thread ends it at once (`render_process.watch_lifeline`): it waits on a lifeline, a pipe the tracker holds the other
  end of and never writes to, which costs nothing until the system closes the tracker's end, and then ends the render process
  alone with SIGKILL, so that the sender sees its own pipe go and closes as ever, sending its note offs (158: the user agreed
  to a failsafe, and the lifeline notices at once where a timed check would wait). The tracker closes its end of the lifeline
  only after the render process has ended (`tests/support/tracker_killed.py` stands in for a tracker killed outright). A render process that ends unasked is told in a dialog (`Transport.take_problem`,
  `ERR_PLAYBACK_ENDED_TITLE`, read by the app's timers), and the next play starts a fresh one.
- The transport builds the next play's score ahead, off the screen's thread (`realtime/render_process/score_builder.py`, `ScoreBuilder`): `keep_ready`,
  on a light timer started under the start screen (`KEEP_READY_SECONDS`), asks for the current song's score whenever the set has
  changed and nothing plays, from a copy of the set made on the screen's thread, with the seed the next play from silence will use
  (`_next_seed`); a launch from silence plays it when its key (revision, song, routes, seed) matches, about a millisecond, and
  renders as before when it does not. An edit made while playing is rendered the same way, a later tick handing the score over; a
  newer request replaces one not yet started. The tests' transports, which give their own sender, build at once.
- A score after an edit takes from the score before it every scene the edit cannot change (`engine/realizer/scene_reuse.py`,
  `SongRealizer.render(after=)`, `Score(data=, earlier=)`, `realtime/render_process/score_records.py`). The builder hands each build the last
  score it made, and the transport hands each score the set's data its copy was made from (`Setlist.kept_data`, whose unchanged
  parts are the same dictionaries from edit to edit, so comparing them is quick). `first_changed_scene` finds the first scene
  that differs or whose clips play or morph to a changed pattern, and the first scene when anything but the song's scenes and
  the set's patterns changed. A render made with data keeps, at each written scene's start, where the draws' chooser and
  every drift stood (`SceneCheckpoint`, `DriftPlay.snapshot`); the next render copies everything worked out about the written
  scenes before the first changed one (entries keyed by written scene number; `_cutting` and `_ramped`, keyed by pattern and by
  object, are worked out again), restores the random streams from that scene's checkpoint and plays on from there, and the score
  takes those scenes' events, rows, clip seconds and draw moments as they were. Nothing is taken without a seed, across seeds or
  routes, when the song's flags differ (`_song_flags`: `Setlist.takes_draws`, `Song.uses_draws`, `Song.redraws_in_conditions`), when any
  scene is played to find its length (a statement reading a draw can cut a clip short), or when any written scene's length differs, since a generator's run
  and a drift's clock reach across scenes by their lengths. After the scenes taken whole, where each track's clips play apart
  (`_clips_stand_apart`: no drift that draws in the order it is asked, `DriftPlay.draws_in_order`), every clip of a track the
  edit does not reach is kept too, with its generators' end states, its chord count and its counted clip (`changed_clips`, `_take_clips`, `_unchanged_clips`): a track is reached from its first clip that changed, or that
  plays or morphs to a changed pattern, onward, since a generator carries on down a track; a scene whose own settings changed
  reaches every track; a track that grabs from, or follows the chords or tune of, a reached track is reached (`_reach_through`),
  and a scene with a hocket reaches all its tracks once any is reached. In a song whose patterns take draws or whose draws hold a
  value, a finished clip reads its scene's timeline of draws, so the render builds each scene's timeline as the scene starts and
  holds it to the earlier render's (`RegisterTimeline.reads_as`); where it differs, the scene's kept clips, and their tracks'
  kept clips after it, are let go and played (`_hold_kept_clips_to_registers`), while the counted clips stay, since counting
  reads no draw's value. The earlier render is held only while the render plays (`_earlier`), so a run of edits keeps one render. The score takes the events of a track whose clips were
  kept in every repeat of a scene (`kept_tracks`, `get_taken_tracks`). While the tests check every remembered answer, every score that took
  scenes is compared with a whole render as it is made and raises `StaleAnswer` at the first difference
  (`tests/realtime/test_scene_reuse.py` runs edits chosen at random on demos that use what carries across scenes, and
  `tests/data/sample_sets/scene_reuse_drift.yml` holds a random drift to it). On `incoming_message.yml` an edit to a pattern
  only the last scene plays renders in 16 ms where a whole render takes 243 ms, and an edit to its kick, which plays from the first
  scene, in 39 ms, keeping 156 of 185 clips. `tests/data/sample_sets/scene_reuse_carry.yml` holds a generator's carried state to it.
- Every listing of the MIDI ports goes through one thread that lives as long as the process (`outputs.PortWatcher`), the first to
  make a MIDI client: CoreMIDI tells only the thread that made a process's first client of ports other programs make later, such
  as FluidSynth's, so a client of any other thread, the main one included, never saw FluidSynth's port, which made the start
  screen wait out FluidSynth's start and a launch start FluidSynth and the sender again. The ports are listed once, as llamatron starts, and again only
  while FluidSynth's port is awaited (`output_port_names_now`); a device connected later is used after a restart (the user's
  rule), and a FluidSynth that runs is not asked about again on each launch. On macOS the listing goes through CoreMIDI
  (`coremidi.destination_names`), which runs the thread's run loop once before each listing, as RtMidi does, since that is how
  CoreMIDI's notice of a destination another program made later arrives, and which answers a refused client with an error:
  python-rtmidi ended the whole process when CoreMIDI refused its client under the suite's load (status -304), a crash the user
  saw as a dialog. python-rtmidi still lists elsewhere.

## Takes

A clip launched by hand while a play goes on, and each lap of a looping clip, plays another take: new random choices of its own
(the user's choice, 193 B). `SongRealizer(takes=)`, by (the scene's place in the song, the track), folds the take into every seed
made from the clip's place: the four stream labels of `clip_slot_player` (`TAKE_SEED`), the generators' seed and the strum's
(`taken_seed`, `SEED_TAKE_FACTOR`); take 0 draws as before, so every export is the same. A render after an earlier one counts a
retaken clip as changed (`_first_retaken`, `_with_retaken`) and keeps the rest. `LocalPlayback` keeps the play's takes, reset by a
play from silence: a launch by hand while playing gives what it launches the next take and renders that score at once, keeping the
rest, before the launch's bar; the player records each looping play's lap as it starts (`Player.take_laps`), and the side asks for
the next take built off the thread, as the newest score asked for so that an edit waiting is built with it, and hands the score
over once built, which the next lap plays, or the take there is if not yet. Every score is built and found by (what is wanted,
the takes). The song's draws and drifts are the song's and take no part. Tested by `tests/engine/realizer/test_takes.py` and
`tests/realtime/test_takes_playing.py`.

## The Synthesis Process (built-in synths, the MVP in progress)

- **The native daemon** (261 A, 269 A, 270 B): `llamatron-backend`, in `src/backend/` (`docs/BACKEND.md`), plays the
  built-in synths when it is built; `realtime/synth_process/daemon.py`'s `SynthDaemon` starts and watches it behind the Python
  Synthesis Process's calls, which the sender (`sender_process/process.py`, `started_synthesis`) makes; `LLAMATRON_PYTHON_SYNTH=1`
  keeps the Python engine while it is kept (266 A). The Rust engine is held to behaviour and to the hardware each part stands
  for, not to the Python engine's samples (the user's direction): its filters are zero-delay-feedback models solved a sample
  at a time, its coefficients worked out every 4 samples. Its load reaches the screen through `synth_process/load.py`'s
  `SharedLoad`, a block of shared memory the tracker's `PlaybackProcess` makes and hands down through the render process to
  the sender, whose reader of the daemon writes each report there; `Page.playing_clock()` shows it after the clock. The WAV
  export renders the built-in tracks offline through the same daemon (`exporters/built_in_wave.py`, `llamatron-backend render`),
  handed `render_offline` through `ExportResources.built_in`, since exporters sit below `realtime`.

- **Every engine and drum its own settings** (the user's rule): every built-in engine and drum has its own settings, those
  the players of the instruments it follows reach for, named mostly as they name them, learned as exactly as can be done
  legally from the real instruments and chips; no engine shares another's settings or hides a different sound behind
  generic knobs; a flavor that is a variant of another engine's sound is a preset of that engine. A chip engine offers only
  what its chip can do, where that makes sense. An engine's settings are discussed with the user before they are built,
  each with a mockup of its Synth tab.
- **Few controls a module** (the user's rule): limits are good; a module shows the few controls that make its sound, never
  forty sliders, so that a player finds what each can do. An "all sweet spot" instrument is welcome, and one piece of code MAY
  be offered as several oscillator types, each a different face of it with its own small set of controls.
- **Presets** (the user's rule): every block type, effect and engine has at most 8 factory presets, each different from the
  others and representative of the instrument, the most useful first, few exotic ones. An engine preset loads the topology
  alone, the type of each block, and each block then takes its type's first preset. Every list of presets is brought to the
  user for a discussion once every synth is built, where the user may rename or delete them; until then they are drafts.
- **Emulations keep their sound** (the user's rule): every emulated engine keeps its own sound in the modular voice; where a
  chip or a machine has an envelope or filter of its own, it is a type of its own (the SID chip's ADSR, the handheld chip's
  steps, the acid gate), never forced into a generic one.
- **Protections whatever the patch** (the user's rule): the built-in synths protect ears and speakers whatever a patch
  does, with no setting that turns the protections off: an instrument whose chunk holds a number that is not finite, or is far
  louder than any patch makes, is silenced and its filters start again from rest, so that nothing can hang screaming; the
  output takes out DC and subsonic movement and ultrasonic hash, and a limiter holds its peaks under a ceiling, the soft knee
  after it the last guard (`realtime/synth_process/safety.py`). Every oscillator, and every modulator running at audio
  rate, is held between about 8 Hz and 20 kHz (pitch 0 to 135) and under half the sample rate, whatever the pitch
  envelope, the Mod Matrix, an audio-rate LFO, a Key ratio or a glide asks (`frequency_of` in
  `src/backend/src/voice/oscillators.rs`), so that no modulation drives a sound to a subsonic thump or past hearing; the
  output's guards then apply to whatever any modulation makes. A new engine or modulator MUST keep both.
- `realtime/synth_process/` plays built-in instruments as audio in a process of its own, beside the Realtime Sender Process
  (the ideas files of `.claude/features/`, "Built-in synths"; the professor's notes in `.claude/notes/synthesis/`). `process.py`'s
  `SynthesisProcess` (the parent's handle) spawns it, waits for READY with the sample rate and the delay, or raises
  `SynthesisNotStarted` with the reason (no sound card, PortAudio missing, the child dying while starting, with its exit
  code); `close()` asks it to close, collects its timing statistics, joins it and kills it if it hangs. The child exits
  when the pipe to its parent closes, so it is never orphaned. sounddevice is imported only inside the child. Built-in sound
  is tried only on macOS, elsewhere only with `ATTEMPT_SYNTHESIS_ANYWAY=1` (`synthesis_available`).
- `player.py`'s `SynthPlayer` opens a PortAudio stream at the device's own rate, 128 frames by default; its
  `audio_callback` maps each chunk to the clock the notes use, `time.perf_counter`, by `outputBufferDacTime`, and places
  each note at `played + round((time + delay - dac) * rate)`. `delay` is the stream's latency plus one chunk, what MIDI is to
  be held back by so that everything lands together. Notes arrive from the reader thread into a deque; drum hits are
  rendered there (`SynthEngine.prepare`), never in the callback. Garbage collection is frozen and off while it plays.
- `engine.py`'s `SynthEngine` works in samples: `schedule` pushes notes into a heap, `render` begins each due note on its exact
  sample, moves every instrument's LFOs on, has each voice's patch sound it, then runs each instrument's effects in order and
  the guards (`safety.py`). A note's patch is a voice of parts (`modular.py`'s `ModularPatch`): an oscillator module
  (`oscillators.py`: Basic's three band-limited table oscillators, the SID-style voice with its sweeping pulse, ring, sync and
  50 Hz arpeggio, the handheld chip's duty pulse, drawn wave or shift-register noise and its 128 Hz sweep, the acid saw or
  shaped square), three envelopes (`envelopes.py`: the snappy ADSR, AR, ASR, the SID chip's own ADSR from its rate table,
  the vactrol with its hyperbolic fall, age and stability, the acid gate with its accent and charging capacitor, the
  handheld chip's sixteen steps), a filter each note's own or the instrument's shared (`filters.py`'s ladder family, the
  ladder tapped for 6 to 24 dB) or the low-pass gate, which is the note's amp (`gates.py`, its ping), and the mod matrix
  (`matrix.py`), the normalled routes Env1 to the amp, Env2 to the cutoff, Env3 to pitch and the key to the cutoff kept
  outside its six slots. A voice of a mono instrument steals; a legato one slides; a drum cuts its own last hit and its
  choke group with a 3 ms fade (`DrumPatch.overlap` lets hits ring). The guards: a runaway instrument silenced and remade
  from rest; the output's band (18 Hz to 18 kHz), a limiter looking ahead within the chunk at −1 dB, a slow guard against
  sustained loudness, a backstop over 0.9, and a latch silencing repeated faults until Ctrl+T or a stop clears it; a note
  released 30 s ago is let go.
- `drums.py` renders the first nine machines from the professor's recipes (`.claude/notes/synthesis/DRUMS.md`), knobs 0
  to 127, a note tuning a drum from middle C, seeded noise so a hit renders alike each time.
- `py_legacy/internal_tools/builtin_timing.sh` plays a few seconds through it and reports start time, MIDI's delay, chunks,
  underflows, late notes and callback times, exiting 1 on any dropout or late note.
- In the set: an instrument's Kind (Off, MIDI, the default for a file that leaves it out, or Built-in; one off has no
  device in effect), a MIDI instrument's Latency in milliseconds, its Role (normal or percussion, chosen when made, a drum
  machine's sound percussion where none is written), and a built-in sound under it as parts (`model/objects/built_in_sound.py`:
  the engine it was made from, the voice layer of volume to 150%, voices, legato, glide and the filter per note or shared, the
  oscillators, three envelopes and the filter, each a type and that type's settings described once in `sound_parts.py`, four
  LFOs, two effects and the matrix's six slots); a part's setting left out is its engine preset's (`engine_presets.py`) where
  the part is still the preset's type, else its type's default, so a sound stores only what differs; `Instrument.set_engine`
  fills every part from a preset, `set_part_type` swaps one; `Instrument.synth_spec()` gives the sound to the Synthesis
  Process. The waveform and drum machine names are the set's (`file_format.Waveform`, `DrumMachine`), which the synthesis
  package uses. The Instrument page builds each part's fields from a table of each setting's kind (`interface/pages/part_fields.py`).
- A new built-in engine always brings a discussion with the user of its six Synth Control rows, ordered Pitch first, then
  the envelope's settings, then the rest (the ideas files of `.claude/features/`, "Built-in synths").
- Routing: the transport gives each track of a built-in instrument a `Route` to a built-in port (`built_in_routes`), each
  built-in instrument a channel, sixteen a port (`realtime_names.BUILT_IN_PORT`), the route naming the instrument (`sound`).
  The render side works out each route's sound as it makes a score (`playback.built_in_sounds`, `Score.set_sounds`) and
  hands the sender the sounds at each launch and edit; the sender sends only the ones that changed (`SOUNDS`). A sender
  with built-in ports starts the Synthesis Process itself, as a child, before it answers READY, or answers `NOT_STARTED`
  with the reason, which the page shows as it shows any sender that did not start. Its built-in ports are `SynthOutput`s
  (`sender_process/synth_output.py`), scheduled outputs: a note goes to the Synthesis Process stamped its delay earlier,
  all notes off and all sound off end every note of the instrument (`ALL_OFF`), and a flush takes back the port's
  instruments' unheard notes (`FORGET`), so that the scheduled engine's stops and edits work as on CoreMIDI. With a
  Synthesis Process the sender starts its timeline that delay later for every port, so that MIDI waits for built-in
  sound. On the immediate driver (no CoreMIDI) built-in notes land up to a chunk late. Only late note starts are counted.
- Not built yet: the Instrument page, a MIDI instrument's Latency, WAV export, LFOs, Synth Control rows, the Basic voice's
  three oscillators on the page.
