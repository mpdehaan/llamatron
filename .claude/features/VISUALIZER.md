# The Visualizer

Reference notes for Claude, one of `.claude/features/`: the visualizer and its modes. `CLAUDE.md` says which part to read for which work.

## The visualizer

- On Arrange, with the set's Real Time switch on, `Z` (`ArrangePage.VISUALIZER`) shows the
  visualizer over the clip area, the user's design (the ideas files of .claude/features/, "The visualizer", holds
  the plan, built a stage at a time): `next_visualizer` steps through `MODES`
  (`interface/visualizers/modes.py`) and after the last back to the clips. While it shows, the page binds
  only `TO_CLIPS` (ESC, which brings the clips back and stays on the page) and `VISUALIZER`, and
  `show_visualizer` runs a timer that draws a frame every `FRAME_SECONDS` (0.05) until
  `hide_visualizer` stops it, so it costs nothing while the clips show. With Real Time off the key
  isn't bound.
- `ArrangeDrawing.visualized_body` draws the track names and the scene names as ever, the
  divider down every line, and lays the mode's frame (`Visualizer.frame(width=, height=, now=)`)
  over the clip area from `CLIP_AREA_LEFT` and `HEADER_LINES` to the line above the footer with
  `laid_over` (`interface/tracker/drawing.py`), with no frame for the cursor. The page passes the seconds since
  the mode began.
- A mode (`interface/visualizers/visualizer.py`) works out only what fits its area and starts again when the
  area's size changes (`resized`), returning big pixels as an array of rows by columns by red,
  green and blue, which `pixel_lines` (`interface/visualizers/pixels.py`) draws as full blocks two columns
  wide and one row tall, one piece of text per run of a colour, each colour's style made once.
  Rich draws them in full colour, or the nearest of 256 or 16 where the terminal shows fewer.
  numpy holds the arrays.
- Each frame hears the notes (`interface/visualizers/heard.py`): Arrange asks `Transport.heard(since=)` for
  the notes that started since its last frame and those still held, by their track's place, with
  the seconds a beat lasts and the beats played, from `Player.heard` and `Score.heard`, which hold
  each clip's notes with their numbers and velocities; only notes that have started are heard, so
  a mode never knows what is coming, and no MIDI is read back. Nothing playing is `SILENCE`.
- The shared pieces every mode can build from: `interface/visualizers/fields.py` (the ripple, soft discs by
  radius, a blur), `interface/visualizers/warp.py` (the rotozoom, through a grid of places kept per size) and
  `interface/visualizers/colour.py` (each track's colour, leaned by pitch and brightened by octave, and the
  `Limiter`, which holds the mean brightness under a level, lets it rise and fall only so fast and
  caps every channel under a ceiling, the user's rule against strobing).
- The lava lamp (`interface/visualizers/lava_lamp.py`): a blob per track that has played, drifting on a path
  of its own, faster for a faster song; a note starting splashes into a ripple field at its blob
  and a held note keeps pushing; the blobs glow into a colour field that fades and bleeds; the
  picture is the colour seen through the water's slope with a soft highlight, turned and zoomed
  with the beat, averaged down from twice the big pixels' resolution and limited. Its amounts are
  the named constants at its top, for the user to tune.
- The spectrum (`interface/visualizers/spectrum.py`), the second mode: a bar per band of pitches, low at the
  left, which a note lifts by its velocity as it starts, and its neighbours a little, holds up while
  held and lets fall steadily, with caps that hang and drop. It draws its own text at the
  characters' resolution rather than big pixels (it overrides `frame`): each bar's top an eighth
  block, coloured up its height from green through yellow to red.
- MilkDrop (`interface/visualizers/milkdrop.py`), the third mode: a feedback picture, each frame the last one
  warped through a table of where each cell comes from (zoomed in, turned, the middle swirled more
  than the edges, rebuilt only when the zoom, which breathes with the beat, moves), faded, blurred,
  and each note splashed in on a slowly turning circle at its track's place and its pitch's, a dot
  while it is held.
- The llamas (`interface/visualizers/llamas.py`), the fourth mode, at the characters' full resolution: an
  ASCII llama for each track that plays (`MSG_LLAMA_SMALL` to `MSG_LLAMA_LARGE`, mirrored to stroll
  the other way), strolling and turning at the edges, bobbing with the beat and hopping on a note,
  its colour drifting around the wheel, its energy rising gently toward what its notes ask and
  fading, which sets its brightness and, no more often than `SIZE_HOLD_SECONDS`, its size.
- The hypercube (`interface/visualizers/hypercube.py`), the fifth mode: a tesseract's sixteen corners turned
  in three planes, faster with the tempo and the tracks' energy, seen in perspective down to two
  dimensions and pulsing with the beat; its thirty-two edges drawn as points along them in the
  colours of the tracks that share them in turn, blurred into a glow under the sharp points, over a
  wash of the playing colours, with a limiter set brighter than the others'. It glows in silence
  too (`DARK_IN_SILENCE` false), as the user wants it bright rather than dark.
- Six more modes, the user's choices, built on autopilot to a like level:
  fireworks (`interface/visualizers/fireworks.py`, big pixels: a rocket per note bursting into sparks held in
  numpy arrays, at most `MOST_SPARKS`); WarpZone (`interface/visualizers/warpzone.py`, half blocks: a ball
  per track at one speed, the tempo's, bouncing off walls and each other, sending rings sliced
  from one distance table); pipes (`interface/visualizers/pipes.py`, heavy box characters, a pipe per track
  laying cells owed by its notes at a pace, fading and starting again when full); plasma
  (`interface/visualizers/plasma.py`, big pixels: four sine waves through a palette blended from the
  playing tracks' colours); maze (`interface/visualizers/maze.py`, light box characters: a maze carved
  depth first on the largest odd area, a walker per track); Mandelbrot (`interface/visualizers/mandelbrot.py`,
  big pixels: the set turning about a point on its edge and breathing in and out, iterated only on
  the points still running, coloured from a vivid palette of the tracks' hues); Mystify (`interface/visualizers/mystify.py`,
  Braille: polygons with trails over a starfield, corners following the notes held); and Laser
  Llama (`interface/visualizers/laser_llama.py`, half blocks with the llama in characters over them: a neon
  sunset over a perspective grid with a haze, after the user's own video backgrounds, the llama
  firing beams on notes). `interface/visualizers/cells.py` draws half blocks, Braille and coloured cells for
  them, each line made in one go from its runs and each style looked up by a packed colour, since
  appending piece by piece was most of a frame's cost. `tests/interface/visualizers/test_visualizer_modes.py` tests what
  each alone promises. After the user watched them: WarpZone is slow and calm in fine Braille
  rings, at most one a track every `RING_GAP_SECONDS`; plasma's palette goes round the tracks'
  hues at full saturation, brighter at the edges; fireworks are crisp points (no blur, each spark one fine
  pixel, taken down by the brightest of each block, `brightest_of_blocks`), bursting around
  `BURST_HEIGHT` (60%) up, a little larger than at first, in `ROCKET_COLOURS` (red, gold, green,
  cyan, blue, magenta and white) by turns, spreading and falling less, with shorter trails, the user's ask; Mystify's polygons are 60% brighter; Cycle moves on every 15 seconds. The
  oscilloscope and the kaleidoscope were built and taken out at the user's ask. Life
  (`interface/visualizers/life.py`): Conway's Game of Life, its cells two characters by one, over a drifting
  gradient of the tracks' colours; a live cell is filled with the inverse of the colour beneath
  and outlined in Braille dots that brighten gently on the beat; it steps on each beat, at most
  `MOST_STEPS_PER_SECOND`, notes seed cells by pitch, and an empty grid is seeded afresh.
- Digital rain (`interface/visualizers/digital_rain.py`), the user's design after the film The Matrix: green ones and zeros
  (`MSG_RAIN_DIGITS`) in coloured cells, a few changing each frame; a note starting sends a stream down the column of its
  pitch, its pale green head as bright as the note is loud and its tail fading, falling `STREAM_ROWS_PER_BEAT` rows a beat;
  the green brightens as more plays, and a sparse dim rain falls in silence. Only green, the heads never white.
- `vivid` (`interface/visualizers/colour.py`) brings a colour to its full value and mixes in just enough white to reach
  `LEAST_LUMINANCE`, its hue kept, since the user found Pipes, Maze, WarpZone and Mystify too dim to read on an iPad or
  iPhone, where a saturated blue or red at full value still looks dark; those four draw their tracks' colours through it,
  Mystify's stars are dimmer and Maze's walls darker, so that what moves stands out.
- Cycle (`interface/visualizers/cycle.py`), last of `MODES`: each mode of `CYCLED` in turn, fresh, every
  `CYCLE_SECONDS` (15, hard-coded for now), answering `shown_name` with the one showing. The order,
  `CYCLE_ORDER`, is shuffled once as the program starts and kept for the whole run, so that each
  recording goes through the modes in an order of its own (the user's ask).
- The piano roll (`interface/visualizers/piano_roll.py`, `piano_roll`), the user's design, second after the spectrum: every key of the
  piano a row, a dim line and label along each C (in Live's octave labels), the notes rolling in at the right edge as they
  start and off to the left at `COLUMNS_PER_BEAT`, a held note growing at the right, each bar's first cell brighter and a gap
  after it so that notes stay apart, each track a bold colour in the order the tracks are first heard (`TRACK_COLOURS`) and
  named in a legend across the top (from `Heard.names`, which the transport fills with the song's track names), the rows
  easing toward the mean pitch of the last `INTEREST_SECONDS`, and the drum tracks' hits in six lanes at the bottom
  (`MSG_PIANO_ROLL_DRUM_LANES`, `drum_lane`) once a drum plays, all on black.
- The modes the visualizer key goes through are `ArrangePage.shown_modes`, every mode but the set's hidden ones; the key shows
  first the song's or the set's choice (`first_mode`) and goes on through the rest to the clips, `[` and `]`
  (`ArrangePage.STEP_VISUALIZER`, `step_visualizer`) step to the mode before or after, going round, and with every mode
  hidden the key says `MSG_EVERY_VISUALIZER_HIDDEN`. A mode is made with `made_for(hidden=)`, which Cycle heeds by leaving
  the hidden modes out of its turns. The File/Global page's Visualizer field and its Hide Visualizers section, a toggle per
  mode, and the Song page's Visualizer field are `interface/pages/visualizer_fields.py`.
- When the name a mode shows changes (`Visualizer.shown_name`), by the key or by Cycle moving on,
  `ArrangePage.name_to_show` returns it for `NAME_SECONDS` (8), and `ArrangeDrawing.with_name`
  lays it in reverse video, centred over the clip area, `NAME_ROWS_UP` lines from its bottom,
  steady, never blinking, the user's design. `py_legacy/internal_tools/time_visualizer.sh`
  (`py_legacy/internal_tools/time_visualizer.py`) times a frame of each mode with 8 and 64 tracks, small and large.
- `--visualizer NAME` (`Launch(visualizer=)`) opens Arrange with that mode showing and plays, the
  one way Arrange opens on a visualizer; the demo recorder asks clips or a visualizer after its
  checks, or takes `--visualizer` or `--clips`, and `py_legacy/internal_tools/preview_visualizer.py` (`make
  preview-visualizer`) plays a set the same way with no video. `tests/interface/visualizers/test_visualizers.py` tests
  the modes, the drawing and that the lava lamp never flashes, `tests/interface/tracker/test_tui_visualizer.py` the
  page, and `tests/interface/tracker/test_tui_playback.py`'s `TestHeard` what the transport hears.

`Visualizer` gives every mode `seconds_since_last_frame(now)` and refuses an area with no room in `frame`; a mode that draws its own lines defines `frame_of`. `Energy` (`interface/visualizers/energy.py`) is a level that notes push up (`strike(loudness)`) and time settles (`settle(seconds)`), never faster than its rise, which is how a mode stays free of flashes.
