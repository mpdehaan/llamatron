# Launching and Recording

Reference notes for Claude, one of `.claude/features/`: the tracker launched to play on its own, and the recordings. `CLAUDE.md` says which part to read for which work.

## Launching to play on its own

- `Launch` (`interface/tracker/launch.py`), held by the app as `app.launch`, is what the command line's flags
  make the tracker do once open, for the demo recorder (`py_legacy/internal_tools/record_demo.py`,
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
  (`recording_problem`, `Song.scenes_that_never_end` through `looping_scenes` in `interface/pages/uses.py`,
  `ERR_RECORDING_SONG_LOOPS`), since real time waits on such a scene for the human; `--max-seconds` quits after that many seconds whatever plays. An interactive launch for
  recording (`Launch(interactive=True)`, `py_legacy/internal_tools/record_demo.py --interactive`, the user's design) opens Arrange after
  the splash with the cursor on the corner (`ArrangePage.go_to_corner`) and plays nothing; Space on the corner while playing
  (`stop_from_the_corner`) or ESC on Arrange (`ArrangePage.go_back`) calls `LlamatronApp.end_take`, which lets the
  lead-out ring and then `_finish`es on the splash; a looping song isn't refused, and the recorder records with
  `ScreenRecording` (`py_legacy/internal_tools/record_demo.py`), which has no time limit and stops when the tracker quits. The three
  timings are arguments of `Launch` so that the tests needn't wait. `Launch(test_splash=True)` shows
  the start screen alone for `splash_seconds` and quits (`py_legacy/internal_tools/demo_splash_screen.py`,
  `py_legacy/internal_tools/demo_splash_screen.sh`). A launch other than that needs a set, and none works with `--to`.
- `Launch(scroll_text=)`, the user's design: after the opening title, `LlamatronApp._after_title` shows `DemoScroll`
  (`interface/tracker/screens/set/demo_scroll.py`, a `Splash` that draws `scroll_lines` of `interface/tracker/components/scroll_text.py`) for as long as the
  words take to cross (`scroll_seconds(text=, width=)`, or `Launch(scroll_seconds=)` in a test), then goes on as ever. The words
  are `scroll_text_for(path)`: `MSG_DEMO_SCROLL` with `demo_name(path)`, the file's name with no folder, ending or leading number,
  as words. `banner(text)` draws every character as its capital from `MSG_BLOCK_LETTERS`, which holds the whole alphabet, at
  twice the title's size. `py_legacy/internal_tools/record_demo.py` passes the words for every set (`scroll_text_of`), on a plain, an
  interactive and a batch take, `--scroll-text WORDS` giving others and `--no-scroll` none (`py_legacy/internal_tools/record_batch.py`
  takes `--no-scroll`), and `py_legacy/internal_tools/demo_splash_screen.sh --scroll-text WORDS` shows them.
- A batch video (`Launch(batch_video=True)`, `--batch-video`, which needs `--visualizer`), the user's design: the
  title for its whole length (`Launch.title_seconds`, `whole_title_seconds`), then Arrange with its cursor on the corner
  and a `BatchStage` (`interface/tracker/batch_stage.py`) on the page, which `Page.staged_screen` lets draw the whole screen
  (`interface/tracker/components/stage_drawing.py`): Arrange fading in, in grey on black (`faded`), the READY box over it (a blue double
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
  `py_legacy/internal_tools/demo_splash_screen.sh --batch`.
- The title (`interface/tracker/components/title_card.py`, `title_lines`), the user's design after a classic video game's start
  page: on black, all in blue, `LLAMATRON` in block letters (`MSG_BLOCK_LETTERS`, five by five, twice as wide where the
  screen has room, `scale_for`) coming in by `ENTRANCE` (`Entrance.SINE_WAVES`, each letter riding a wave `WAVE_ROWS`
  high and settling, or `FADE`; a constant so that other entrances can be tried), then the scanner, a glow
  `SCANNER_SHARE` of the title wide each side shaded through tones of the blue, sweeping right and back left on the
  second line under the word and gone (`scanner_level`), then the address two lines under it. A title shown for a set
  time fades to black over its last `FADE_OUT_SECONDS` (`fade_level`); `whole_title_seconds` is the whole of it.
- The splash (`Splash`, `interface/tracker/screens/set/splash.py`), a Textual `Screen` binding no keys, draws the title for its
  seconds when the tracker is launched for recording; it replaced the word that waved letter by letter, after the end
  credits of Monty Python and the Holy Grail, keeping the waves as the entrance. It draws every `FRAME_SECONDS` on its
  own timer, and takes a clock for the tests.
- The start screen (`StartScreen`, `interface/tracker/screens/set/start_screen.py`, `keybindings.StartScreen`) is the splash with
  `MSG_START_PROMPT` six lines under the address, pulsing between dim and bright (`prompt_level`), until ENTER takes
  it away. Only the command line asks for it (`LlamatronApp(start_screen=)`), always on a plain launch; it goes over the
  main screen and any dialog the opening raised, so the tests and the tools that make the app never see it. While it shows,
  real time is got ready underneath (`Transport.prepare`: FluidSynth where installed, the Realtime Sender Process on every
  port): the scanner sweeps at least once and on while anything loads (`scan_end(loaded_at=)`), and the prompt comes, and
  ENTER works, only once all is ready.
- `tests/interface/tracker/test_tui_playback.py` tests the launches on the playback test's stepped clock, with
  short timings, and the splash's picture at moments of a clock of its own.

