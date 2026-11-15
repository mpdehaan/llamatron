# Launching, Recording and the Video Tutorial

Reference notes for Claude, one part of `.claude/tracker/`: the tracker launched to play on its own, for the recordings, and the video tutorial. `CLAUDE.md` says which part to read for which work.

## Launching to play on its own

- `Launch` (`tui/launch.py`), held by the app as `app.launch`, is what the command line's flags
  make the tracker do once open, for the demo recorder (`internal_tools/record_demo.py`,
  `docs/RECORDING.md`) and for anyone: `--autoplay` opens Arrange over the main screen and,
  after `LEAD_IN_SECONDS` (1), calls `ArrangePage.play_song`, as Space on the corner does;
  `--autoplay-quit-when-finished` implies it and, once play has begun, asks the transport every
  `FINISHED_CHECK_SECONDS` whether anything plays and quits `LEAD_OUT_SECONDS` (2) after it
  stops, or at once after the lead-out when nothing could play and a dialog says why;
  `--launch-for-recording` shows the splash first for `SPLASH_SECONDS` (6), and again once the song has ended and rung out
  (`LlamatronApp._finish`), then waits `Launch.hold_seconds` before quitting, the user's design, so that the
  recorder's trimmed video ends on the splash; it leaves the header's
  save mark blank (`Page.save_mark`), since the recorder's instruments make the set unsaved,
  and refuses a song with a scene whose every clip loops before the app starts
  (`recording_problem`, `Song.scenes_that_never_end` through `looping_scenes` in `tui/uses.py`,
  `ERR_RECORDING_SONG_LOOPS`), since real time waits on such a scene for the human; `--max-seconds` quits after that many seconds whatever plays. An interactive launch for
  recording (`Launch(interactive=True)`, `internal_tools/record_demo.py --interactive`, the user's design) opens Arrange after
  the splash with the cursor on the corner (`ArrangePage.go_to_corner`) and plays nothing; Space on the corner while playing
  (`stop_from_the_corner`) or ESC on Arrange (`ArrangePage.go_back`) calls `LlamatronApp.end_take`, which lets the
  lead-out ring and then `_finish`es on the splash; a looping song isn't refused, and the recorder records with the
  tutorial's `ScreenRecording`, which has no time limit and stops when the tracker quits. The three
  timings are arguments of `Launch` so that the tests needn't wait. `Launch(test_splash=True)` shows
  the start screen alone for `splash_seconds` and quits (`internal_tools/demo_splash_screen.py`,
  `internal_tools/demo_splash_screen.sh`). A launch other than that needs a set, and none works with `--to`.
- `Launch(scroll_text=)`, the user's design: after the opening title, `LlamatronApp._after_title` shows `DemoScroll`
  (`tui/screens/set/demo_scroll.py`, a `Splash` that draws `scroll_lines` of `tui/components/scroll_text.py`) for as long as the
  words take to cross (`scroll_seconds(text=, width=)`, or `Launch(scroll_seconds=)` in a test), then goes on as ever. The words
  are `scroll_text_for(path)`: `MSG_DEMO_SCROLL` with `demo_name(path)`, the file's name with no folder, ending or leading number,
  as words. `banner(text)` draws every character as its capital from `MSG_BLOCK_LETTERS`, which holds the whole alphabet, at
  twice the title's size. `internal_tools/record_demo.py` passes the words for every set (`scroll_text_of`), on a plain, an
  interactive and a batch take, `--scroll-text WORDS` giving others and `--no-scroll` none (`internal_tools/record_batch.py`
  takes `--no-scroll`), and `internal_tools/demo_splash_screen.sh --scroll-text WORDS` shows them.
- A batch video (`Launch(batch_video=True)`, `--batch-video`, which needs `--visualizer`), the user's design: the
  title for its whole length (`Launch.title_seconds`, `whole_title_seconds`), then Arrange with its cursor on the corner
  and a `BatchStage` (`tui/batch_stage.py`) on the page, which `Page.staged_screen` lets draw the whole screen
  (`tui/components/stage_drawing.py`): Arrange fading in, in grey on black (`faded`), the READY box over it (a blue double
  border, a pulse round its track, two rows and four columns of gap, red READY); after `Launch.ready_seconds` the song
  starts, and over `GROW_SECONDS` the box grows (`grown`) out to the frame (`frame_box`: the border in the outermost cells,
  unseen, the track one cell in, a black gap, the visualizer in `visualizer_area`, always drawn at that size and only
  revealed by the growing box, since a mode starts again when its size changes) while Arrange and READY fade. The pulse
  goes round a lap every `FRAME_LAP_BARS` bars by the song's beats, and at each change of scene turns round and eases to
  the next of `FRAME_COLOURS`. Inside the frame the clips and the visualizer take turns, the user's design and the default (`Launch(alternate=)`, `--no-alternate` to
  show the visualizer alone): the clips first, each view `ALTERNATE_SECONDS` (10), each change a fade through black over
  `ALTERNATE_FADE_SECONDS` (`BatchStage.visualizer_share`, `clips_laid_in`), the visualizer worked out only while it can be seen
  (`shows_visualizer`). When the song ends everything fades to black over the lead-out, and the tracker quits
  after the hold, with no splash. `opening_only` cuts to black where the song would start, for
  `internal_tools/demo_splash_screen.sh --batch`.
- The title (`tui/components/title_card.py`, `title_lines`), the user's design after a classic video game's start
  page: on black, all in blue, `LLAMATRON` in block letters (`MSG_BLOCK_LETTERS`, five by five, twice as wide where the
  screen has room, `scale_for`) coming in by `ENTRANCE` (`Entrance.SINE_WAVES`, each letter riding a wave `WAVE_ROWS`
  high and settling, or `FADE`; a constant so that other entrances can be tried), then the scanner, a glow
  `SCANNER_SHARE` of the title wide each side shaded through tones of the blue, sweeping right and back left on the
  second line under the word and gone (`scanner_level`), then the address two lines under it. A title shown for a set
  time fades to black over its last `FADE_OUT_SECONDS` (`fade_level`); `whole_title_seconds` is the whole of it.
- The splash (`Splash`, `tui/screens/set/splash.py`), a Textual `Screen` binding no keys, draws the title for its
  seconds when the tracker is launched for recording; it replaced the word that waved letter by letter, after the end
  credits of Monty Python and the Holy Grail, keeping the waves as the entrance. It draws every `FRAME_SECONDS` on its
  own timer, and takes a clock for the tests.
- The start screen (`StartScreen`, `tui/screens/set/start_screen.py`, `keybindings.StartScreen`) is the splash with
  `MSG_START_PROMPT` six lines under the address, pulsing between dim and bright (`prompt_level`), until ENTER takes
  it away. Only the command line asks for it (`LlamatronApp(start_screen=)`, `start_screen_wanted` in
  `tui/launch.py`), unless `LLAMATRON_NO_SPLASH=1`, and only on a plain launch; it goes over the main screen and any
  dialog the opening raised, so the tests and the tools that make the app never see it.
- `tests/tui/test_tui_playback.py` tests the launches on the playback test's stepped clock, with
  short timings, and the splash's picture at moments of a clock of its own.

## The video tutorial

- `internal_tools/make_video_tutorial.py` (`internal_tools/tutorial.sh SET`) launches the tracker on a new set
  with `Launch(driven_by=tutorial(target=, port=, pace=))`, and `LlamatronApp._begin_driving`
  calls that function with the app, which makes a `TutorialRunner` (`tutorial/runner.py`) on a
  `TutorialPlan` (`tutorial/plan.py`), and starts it. The tracker never imports `tutorial/`, which
  imports the tracker as the tests do, so the two don't import each other. It is the user's
  design: nothing is scripted by hand, the plan reads the target set and yields
  the steps that build it, each a `Press` of one key or a `Say` of one sentence
  (`tutorial/steps.py`, the sentences in `strings/narration.py`).
- The plan never counts keys ahead: between two steps it reads the page open and where its
  cursor is, presses an arrow, looks again, and gives up with `TutorialStuck` after
  `MOST_MOVES`. It goes by the bindings of `tui/keybindings.py` and by fields' labels, as the
  tests do, so a key that moves can't break it. On the main screen it opens every page by moving the
  cursor's box onto the page's cell with the arrows (`select_cell`, `cell_place`), saying
  "Opening Patterns" after a blank line (`Gap`, `MSG_NARRATE_OPENING`, or "Turning on Real
  Time" for the switch), and
  pressing ENTER, never with the page's letter, so that a viewer sees where it is going
  (`open_page`, the user's wish, which reversed the letters of earlier that day),
  which `tests/tui/test_tutorial.py` holds it to. A page that is open already, under what is on top,
  is gone back to with ESC instead and nothing is said (`CELL_PAGES`, `go_back_to`), so that no
  page is opened twice in a row.
- The build goes the song's settings, the scales, then one track at a time, each track's clips
  scene by scene from the top, each pattern drawn on the piano roll when a track first needs it
  and its other rows set in the rows view, then the clip put on Arrange. Each thing made is
  announced, "And now we are making a pattern called (riff).", and each thing the new set
  already has, its song, `track-1`, `scene-1` and the starter pattern, "There is already a track,
  so we are going to rename it." (`MSG_NARRATE_MAKING`, `MSG_NARRATE_RENAMING`), said once the
  list of that kind of thing shows: the Songs page, Arrange or the Patterns page. Then it shows
  the finished song on Arrange, "Now the song is complete, we can export it now."
  (`show_the_finished_song`), and goes back to the main screen. With a driver it says it will
  play live into a DAW, that Ctrl+X would export, and that it sets up real-time MIDI, adds an
  instrument per track on that port, one channel each in track order (adding the first turns
  Real Time on, and `T` is pressed only if it is still off), says "And now it's time to play the
  song.", goes into Arrange and plays from the corner, waits for the song to end
  (`Wait`, `song_has_ended`) and `AFTER_THE_SONG_SECONDS` (2) more. Without one it says "To
  export it now we would press Ctrl+X." and "The tutorial is now complete." Either way it then
  goes back to the main screen, says "In exiting the app, we will be asked if we want to save any
  changes.", moves the box onto Quit and chooses "Quit without saving" (`quit`). The user's
  design. What the plan can't set yet is listed as
  left out in the report the tool prints after the tracker quits.
- The runner presses each key straight into the screen with `key_event` (`tui/key_table.py`,
  which the tests' `press` uses too) and gives the event loop its turn, one key every `pace`
  seconds (`HUMAN_PACE`, nothing in the tests), half that for a letter typed into a dialog
  (`Press.in_dialog`, `DIALOG_TYPING_SHARE`, the user's choice), and `SAY_PAUSES`
  of them for a sentence at least. Every caption, a sentence or a key's call-out, shows as long as it takes to read
  (`READING_CHARACTERS_PER_SECOND`, 15) and `LINE_SECONDS` (1) more (`caption_seconds`, the user's choice), and
  nothing at no pace, where the runner only lets the tracker handle each key (`pilot.pause(0)`),
  with no wait for the computer to go idle, the user's idea. There is no voice, which the user tried and took out.
- What a key says as it is pressed (`TutorialPlan.pressing`, the user's design):
  a letter is called the first time on each kind of page, "Press R for reconfigure", with its
  legend's words (`letter_call`, `MSG_CALL_LETTER`, `WORDS`), and the pattern editor's two views
  are two kinds (`page_kind`). Some keys are explained once, as a `Say` before the press
  (`explaining`): the arrows the first time anywhere, "Arrow keys navigate around the app.", and
  again on the piano roll and in the rows view (`ARROWS_EXPLAINED`); ENTER and ESC the first time
  anywhere; and Space once on each kind of page, in that
  page's words on the piano roll and Arrange (`SPACE_EXPLAINED`) and "Pressing space toggles
  many types of cells" on every other. Nothing else is called, and typing, into a prompt or into
  a pattern's cells, never is (`typed`).
- The caption strip (`tui/caption_strip.py`, `CaptionStrip`, the user's design, which replaced the narrator box) shows
  what is said at the foot of the screen while the tutorial runs, as a film's captions. `tutorial()` gives the app one
  (`LlamatronApp.show_caption_strip`), and the runner's `CaptionNarrator` shows each sentence and each key's call-out,
  a part at a time when it's too long for one line (`parts`, broken between words), then draws every open page again
  (`redraw_pages`). `Page.draw` draws the page `CAPTION_LINES` (2) lines shorter, so that nothing is covered, and adds the
  strip's lines (`CaptionStrip.lines`): the caption bold black on white and centred, then a white line, which keeps the
  words clear of a video player's controls. Without a tutorial the app has no strip and draws as ever. The recorder writes
  the captions as a SubRip file beside the video (`tutorial/subtitles.py`, `recordings/<set>_tutorial.srt`), for YouTube,
  which can't turn captions on for every viewer. `tests/tui/test_tui_caption_strip.py` tests it.
- Nothing is saved, unless `--save-set-yaml` names a file. `tests/tui/test_tutorial.py` tests it.
- The tool records the tutorial as a video, `recordings/<set>_tutorial.mov`, unless `--no-video`:
  the terminal window through `screencapture`, as `internal_tools/record_demo.py` records, with the
  loopback audio device's sound when it plays and none under `--no-play`, the tracker launched
  for recording so that it opens on the splash. `ScreenRecording` starts `screencapture` under a
  pseudo-terminal of its own and types a character there when the tracker has quit, which stops
  the recording and writes the file, where a signal would leave no file, so
  the video ends with the tracker. `screencapture` gets no `-V`, since with a time limit it
  neither prompts nor stops for a character, which hung the first real take; `--max-seconds` (an
  hour) quits the tracker instead (`Launch(max_seconds=)`), and a `screencapture` that still
  doesn't stop is ended after `STOP_TIMEOUT_SECONDS` and reported, leaving no file.
  `tests/tools/test_make_video_tutorial.py` tests the recording with a stand-in for `screencapture`.

