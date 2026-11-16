# Real-Time Playback

Reference notes for Claude, one of `.claude/features/`: the engine and the Realtime Sender Process that play a set as MIDI in real time, and how the tracker's pages drive them. `CLAUDE.md` says which file to read for which work.

## Real-time playback

- `src/llamatron/realtime/` plays a rendered song out of the computer's MIDI ports, the user's
  design. What is left of it is in `.claude/IDEAS.yml` under "Real-time
  MIDI, what's left". How the tracker drives it is under "Real-time playback on the pages" below.
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

## Real-time playback on the pages

- `Transport` (`tui/transport.py`, `app.transport`) is the tracker's side of real-time playback,
  between the pages and the player ("Real-time playback" above). It answers
  `problem(track=)` before anything is rendered (with `ERR_FLUIDSYNTH_NOT_INSTALLED` when a track
  plays through FluidSynth and `fluidsynth_installed()` says no, the tests giving a `FakeFluidSynth`
  and their own answer): `ERR_REAL_TIME_OFF` when the set's switch is
  off, `ERR_ADD_INSTRUMENT_FIRST` when the set has no instrument, `ERR_NO_TRACK_HAS_AN_INSTRUMENT`
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
- On Arrange, with Real Time on, Space is bound by where the cursor is: `PLAY_SONG` on the
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
  `Transport.tick` calls `_follow_edits`, which waits until the document's revision has stayed the
  same for `LIVE_SETTLE_SECONDS` (0.15), so that typed digits are heard once, renders the song again
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
- The pattern preview (`tui/pattern_preview.py`, `app.pattern_preview()`), the user's design: `L` in the
  pattern editor and on the Patterns page (`pattern_listen_keys`, `listen_to_pattern`) plays the pattern
  at once with nothing asked, and `L` stops it. `PatternPreview` is a second `Transport` beside the
  song's (`Transport.shared()`), with a player and a sender of its own, so that it never stops the song
  and plays whatever the Real Time switch says (`may_play`). It plays a copy of the set (`PreviewSet`,
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
- `tests/tui/test_tui_playback.py` tests all of it, with a `Transport` on a `SteppedClock` and a
  `PlaybackEngine` of `RecordingOutput`s in place of the process, and
  `llamatron.tui.transport.output_port_names` patched to two ports of the test's own.

