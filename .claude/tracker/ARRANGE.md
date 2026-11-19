# Arrange

Reference notes for Claude, one part of `.claude/tracker/`: Arrange, its details view, Scene View, and the track editor and clip page; playing from the pages is in `.claude/features/REALTIME_PLAYBACK.md`. `CLAUDE.md` says which part to read for which work.

## Arrange

- There's no Tracks page. The Arrange page's row of track names is reachable by the cursor
  (`HEADER_ROW`), with a `+` after the last name.
- On a track's name: `ENTER` opens the track editor, `C` copies the track with its clips to its
  right, `I` inserts a blank track before it, `M` picks it up for Move mode
  (`ArrangePage.MOVE_TRACK`, `start_moving`), Left and Right carrying it (`CARRY_TRACK`, `shift_track`), and `Bksp`
  deletes it after asking.
- On a scene's row: `C` copies the scene below, `I` inserts a blank scene above, `M` on its name
  picks it up for Move mode (`ArrangePage.MOVE_SCENE`), Up and Down carrying it (`CARRY_SCENE`, `shift_scene`), and `Bksp`
  on its name deletes it.
- Move mode, the user's design (`ArrangePage.moving`, `MOVING_SCENE`, `MOVING_TRACK`, `MOVING_CLIP`, `moving_keys`): `M` on
  a clip picks the clip up (`MOVE_CLIP`), and each arrow carries it to the nearest empty cell that way, passing over cells
  that hold clips (`carry_clip`, `CLIP_STEPS`, `Document.move_clip_slot`, which drops a grab as a paste does), the user's
  rule that a clip moves only onto an empty cell; ENTER, ESC or `M` drops what is carried (`DROP`); every carry after the
  first continues the edit, so one move is one undo step; the frame is green (`Style.DETAILS_LOCKED`) while it lasts.
  On a list page the same (`ListPage.MOVE`, `CARRY`, `DROP`, `start_moving`, `carry`), the carried row's name drawn
  between `MSG_MOVING_OPEN` and `MSG_MOVING_CLOSE` in place of the spaces beside it. The undo history and the unsaved
  mark compare data with the order of each section's items counted (`same_in_order`, `support/ordered_data.py`), since
  `==` on dictionaries ignores the order a move changes.
- On an empty cell: `ENTER` chooses an existing pattern and adds a clip, staying on Arrange, and `B`
  (`ArrangePage.BLANK_PATTERN`, `blank_pattern`) makes a blank pattern named after the track (`lead-1`, a drum pattern on a
  drum track), puts a clip of it there and opens it in the pattern editor, the user's design after Live's empty slot.
- On a clip: `C` copies it for `V` to paste, `ENTER` opens the clip page, and `P`
  (`ArrangePage.OPEN_PATTERN`, `open_pattern`) opens the pattern editor on the clip's pattern,
  the user's choice over Shift+ENTER, which a stock terminal sends as ENTER. `P`
  is bound on a clip alone, so elsewhere it does nothing. `C` means copy everywhere.
- New tracks and scenes are numbered, `track-2` and `scene-2` (`new_name` with `MSG_NEW_TRACK_WORD` and
  `MSG_NEW_SCENE_WORD` of `strings/names.py`), one more than the highest number in use, and renamed on their own pages.
- Deleting a scene, track or clip confirms in a dialog, and the last scene or track is refused in
  a message dialog (`ERR_LAST_SCENE_SHOWN`, `ERR_LAST_TRACK_SHOWN`).
- The page has no details line under the grid.
- While the set's Real Time switch is on, the corner over the scene names is a place of its own
  (`on_corner`, the header row at `SCENE_COLUMN`, which `clamp` lets the cursor reach then and
  not otherwise), and Space plays and stops (`.claude/features/REALTIME_PLAYBACK.md`).

### How Arrange is drawn

- `ArrangeDrawing` (`screens/arrange/arrange_drawing.py`) draws the grid, as the pattern editor's
  drawings draw the editor: `ArrangePage` keeps the cursor (`row`, `column`), how far the grid
  has scrolled (`top`, `left`), the keys and what each key does to the song, builds the drawing
  once as `page.drawing`, and `ArrangePage.body` asks the drawing for the lines. `clip_text(clip_slot)`
  there is what a clip says in its cell, the name and a mark for each setting beyond the
  pattern. `tests/tui/test_tui_arrange_drawing.py` tests the drawing on its own.
- The grid is laid out on `Canvas` lines (`tui/drawing.py`, a line written in overlapping pieces
  with styles) and drawn by `draw_header`, `draw_scene`, `draw_footer` and then the frame.
- Three header lines (`HEADER_LINES`): room for a frame's top, the bold track names with the `+`
  after them, and the rule. The corner is blank, since the crumbs say where you are.
- Three lines per scene (`SCENE_LINES`): a spacer, the name with its time, and its length bar,
  with the clips beside them.
- Three lines after (`FOOTER_LINES`): a spacer, the `+` row and room for a frame's bottom.
  `visible_scenes` keeps the header and the `+` row on screen while the scenes scroll.
- A `Frame` (`tui/components/frame.py`), a bold double-lined box, marks whatever the cursor is on
  in place of reverse video (`frame_place`). An empty cell shows `+` over `add` only under the
  cursor.
- The bars are `LengthBar`s (`tui/components/length_bar.py`). `SCENE_BAR`, hatched, is a scene's
  seconds against `Lengths.longest_scene_seconds()`. `CLIP_BAR` is a clip's seconds against
  `Lengths.scene_play_seconds()`, its scene's first play, full for a looping clip and blank where
  a length can't be worked out. With Real Time on a clip's bar is `CLIP_BAR_WITH_BUTTON`, two
  columns shorter, after the clip's play button (`play_button`: a dim `▶`, or `■` in
  `Style.PLAYING` while the clip plays), the corner holds `MSG_SONG_BUTTON` (`▶ song` or
  `■ song`), a track's name is followed by `MSG_SOUNDING_MARK` in `Style.SOUNDING` while a note
  sounds on it, a playing clip's repeat mark counts down (`clip_text(clip_slot,
  repeats_left=)`), and the playing scene's bar is drawn with `played=`, the seconds elapsed, as
  a read head (`LengthBar.draw(amount=, total=, played=)`, the part to come in `TO_PLAY`). Each
  playing clip's bar is a read head too (`clip_bar(played=)`, from `Transport.clip_elapsed`,
  `Player.clip_elapsed` and `Score.clip_elapsed`: the seconds into the clip's play in the
  scene's current row, all its repeats together, stopping at the clip's end), and a looping
  clip's, full when still, fills over one play of its scene and starts over, the user's idea.

## Fracture

- `F` (Fracture) on Arrange, the user's design, for a finished song whose sections are to be edited apart: a `ConfirmDialog`
  titled Fracture asks "Do you really want to give all clips unique patterns?", and yes calls `Document.fracture_song`
  (`Setlist.fracture(song)`): reading the scenes from the top and each scene's tracks from the left, the first clip to play a
  pattern keeps it, and each later clip plays a copy named by `copy_name` and kept in the pattern's group. One undo step. Only
  the pattern a clip plays is copied: a clip's Morph to pattern stays shared, and so does a pattern another song plays. The
  status line says how many were copied, or that every clip already has its own. `tests/tui/test_tui_fracture.py`.

## The details view

- On Arrange, `D` (`ArrangePage.SHOW_DETAILS`, and `HIDE_DETAILS` while it shows, `toggle_details`) shows the
  details view, the user's design, and `D` again the usual view; the choice is kept on the app for the session
  (`shows_arrange_details`), and the visualizer and a batch video's stage show the usual view whatever it is
  (`ArrangePage.shows_details`). Every key works in it as in the usual view.
- `tui/screens/arrange/arrange_details.py` says what it shows, each only when it isn't the default: under a clip's bar,
  under a scene's and under each track's name in the header, each chain the cell runs, `chain: name`
  (`MSG_DETAILS_CHAIN`), in the order they run, in the chains' theme colour, then `+` (`MSG_DETAILS_ADD_CHAIN`, a `Target` of
  `ADD_CHAIN`), the user's design, since a cell holds chains and a chain's generators show on the chain's own page; then a word
  and a colon for each setting: a scale only where it differs from the song's, a grab, an Advance other than the
  set's default, a strum and the shapes on a clip; a tempo or ramp, a groove, the registers reset and the shapes on
  a scene; an instrument, a transpose, a groove, a Euclidean mask, a strum and `muted` on a track. A clip's morph
  and direction are lines spelled out, `morph: other` and `direction: pendulum` (`MSG_DETAILS_MORPH`,
  `MSG_DETAILS_DIRECTION_NAMES`), the user's choice over marks, and its name line keeps only its loop and repeat
  marks (`detailed_clip_text`).
- A detail is cut at `DETAIL_WIDTH` (24) and so is a track's name; a clip's name never is (the user's rule). Each
  column widens to its longest line and each scene's row grows to its tallest cell (`details_layout`, a
  `DetailsLayout` remembered with `Document.remembered`), and `ArrangeDrawing` asks `track_width`, `header_lines`
  and `scene_lines`, which give the usual view's constants when the view is off, so the usual view draws as ever.
  `visible_wide_tracks` and `visible_tall_scenes` scroll by the widths and heights.
- The scene column's divider is a double bar and a bar runs between every two tracks, in blue
  (`draw_dividers`, `draw_rule`), and the first track's cell starts on the double bar, so that every column lies
  the same way between its dividers. `tests/tui/test_tui_arrange_details.py` tests it.
- Tab, the user's design, in the usual view and the details view alike, on a track's name, a scene's name or a clip
  (`ArrangePage.INTO_DETAILS`, `cursor_cell`, `start_picking`), opens that cell's details if they aren't showing
  (`opened_cell`, the one cell the usual view shows details for, its row and column growing to fit, with no blue
  dividers, which belong to the details view) and locks onto its first line naming something with a page of its own
  (`pickable`, each `DetailLine` carrying a `Target`): a chain, the `+`, or a line naming a scale, an instrument or
  a groove, the user's choice over chains and generators alone. On a track's or a scene's name it opens only that
  name's own details, the user's choice over the whole column or row (`.claude/IDEAS.yml`). A cell with no details of
  its own shows `stock` in red (`or_stock`, `MSG_DETAILS_STOCK`), in the details view too, and Tab still locks into it
  with nothing picked; an empty clip slot has no Tab. While locked (`locked`, `picked`, `picking`), the cell's box is
  green (`Style.DETAILS_LOCKED`, `Frame.styled`) and the page binds only Up and Down (`PICK_DETAIL`), which pick among
  those lines and stop at either end, ENTER (`OPEN_DETAIL`, `open_picked`), which opens the thing's page
  (`DETAIL_PAGES`, or a generator's `EDITOR` through `generator_page_of_kind` in `screens/generators/generator_pages.py`), Tab again
  (`OUT_OF_DETAILS`, `stop_picking`), which leaves and in the usual view closes the cell, `D` (`CLOSE_DETAILS`,
  `close_details`), which leaves and closes every detail, the details view too, and ENTER on `+` (`ADD_CHAIN`, `add_chain_to_cell`), which asks for one of the set's chains and adds it to this cell alone,
  `Bksp` on a `chain:` line (`REMOVE_CHAIN`, `remove_chain_from_cell`), which takes it out of this cell alone, the user's
  design, ESC (`ESCAPE_CELL`), which
  leaves the cell as Tab does, since ESC closes the topmost thing (the user's rule); Left and Right do nothing (the user's rules).
  The picked line is drawn in brackets (`MSG_PICKED_OPEN`, `MSG_PICKED_CLOSE`), the user's choice over the triangle,
  which marks play. A page opened so shows Arrange's crumbs first and then the thing's word and name, `ARRANGE ›
  chain: half` (`ShowsNamedItem.opened_from`, `MSG_OPENED_ITEM_CRUMB`), since ESC goes back to Arrange, where the
  cell is still locked. A pick stays within the lines an edit leaves, and leaves when none are left. A scene's details
  are cut to `SCENE_DETAIL_ROOM` so that they never cross the scene column's divider.

## Scene View

- On Arrange, `P` on a scene's name (`ArrangePage.SCENE_VIEW`, `open_scene_view`) opens Scene View, the user's design,
  an Inset Window over the page (`ArrangePage.inset`, laid over the screen by `staged_screen` through `with_inset`)
  holding a `SceneView` (`tui/components/scene_view.py`). While it shows the page binds only `P` (`CLOSE_INSET`), the
  arrows (`INSET_MOVE`), PgUp and PgDn (`INSET_BARS`, `jump_bar`), which jump the cursor to the next bar or back,
  `V` (`TO_PLAYED` or `TO_WRITTEN`), which switches the view, `-` and `=` (`INSET_ZOOM`), `[` and `]`
  (`INSET_SCROLL`) and ESC (`ESCAPE_INSET`), which closes it as `P` does, the user's keys.
- What it shows comes from `tui/scene_notes.py`: Played, the song's own render (`SongRenderer` with
  `looping_scenes_go_round`, the scene's rows laid end to end, each clip's notes through `timed_events`), after every
  generator, groove, strum, shape and register, one take of the random parts when the song has no seed; and Written,
  the same render of a copy of the set with every chain, shape, strum, Euclidean mask and groove, the probability rows
  and the rows that read the registers taken out (`written_song`). Written shows first. A clip whose pattern reads the
  registers (`Pattern.uses_registers`, `marked_tracks`) is drawn hatched in both, never mixed in, the user's ask.
- Its lines: a caption in reverse video saying which view shows (`MSG_SCENE_VIEW_WRITTEN`, `MSG_SCENE_VIEW_PLAYED`),
  which the border's colour says too (`border_colour`: purple written, the splash's blue played), the title
  `SCENE VIEW FOR SCENE: <name>` in reverse video on the top edge and `P close` in the bottom corner; what the scene
  plays with in the end and where each comes from (`effective_values`: tempo, time signature, scale, groove, song or
  scene); a legend of the tracks that play, in their colours (the drum tracks the warm colours, `WARM_COLOURS`, red first, oranges, yellows and white, and the others the cool ones, `COOL_COLOURS`, green first, the user's design, a group that runs out borrowing the other's that are left, `coloured`; each note in one colour, a track keeping its colour from scene to scene unless the song has more tracks than colours, when the tracks playing in the scene take them, `track_colour`), each with its
  number, `lead (1)` (`track_label`), a clip's own scale after it; the chord on each beat (`beat_chords`), from every note
  sounding in the beat across every track but the drums, each note name counted by the share of the beat it sounds
  through however many notes double it (`covered`): every note of a chord symbol (`FIXED_CHORDS`' shapes in one octave)
  must sound through more than `HELD_SHARE` (a sixteenth of a quarter), up to `MOST_OUTSIDE` (2) others may sound as
  passing notes, and the chord covering most wins, then fewest outside, then smallest, then rooted on the bass, with the
  bass after a slash when it isn't the root (`chord_of`, `C/E`), the user's choice; named as the scale spells (`spelled`,
  a seven-note scale one letter a degree, `letter_spelled`) with its Roman numeral (`chord_texts`), each written where it
  changes and room allows; the roll, a sixteenth a column drawn `START_CELLS` (3) cells wide, which `-` and `=`
  (`INSET_ZOOM`, `zoom_by`) change from 1 to 5, every key a row with a line and its octave's label along each C and the
  key's own name beside the label where a note plays it (`row_label`), a mark at each bar, a note's last cell left blank
  so that repeated notes stand apart, tracks at once the first's colour behind a bold `X` in the second's or their count in black (`overlap`, the user's choice), and the drum lanes pinned at its foot; a sidebar at
  the right of each track that plays, its name and number in its colour and then its clip's details in the scene and its
  own, as the details view shows them, `stock` for none (`sidebar_lines`), which `[` and `]` scroll (`INSET_SCROLL`);
  and the notes under the cursor, `strings (track #2): C3 for 1/4` (`under_cursor`). Velocity isn't shown, the user's
  choice. `tests/tui/test_tui_scene_view.py` tests it.

## Track editor and clip page

- The track editor's CC1 Reg to CC4 Reg and Vel Reg fields, after the CC numbers, bind a lane or the velocity to a
  register or `(none)` (`TrackEditor.register_field`, `set_track_cc_register`, `set_track_velocity_register`).
- The track editor's Name field renames. Its Lowest octave and Highest octave fields, in the
  set's octave labels, are the range the piano roll marks (`TrackEditor.octave_field`).
- The clip page, the Scene page and the track editor each have a Chains field
  (`screens/arrange/chains_field.py`), which opens a `ChainListPage` (`screens/generators/chain_list_page.py`) on
  the list the opener hands it: `A` adds a chain from a picker, `M` moves, `Bksp` takes one
  out, and the crumbs are the opener's with `CHAINS` after.
- The clip page's Scale field, under Pattern, picks a scale of the clip's own or `(scene)` (`ClipPage.pick_scale`,
  `MSG_SCENE_SCALE_SHOWN` for the scene's).
- The clip page's Name field sets a clip's own name and `Bksp` clears it. `P`
  (`ClipPage.OPEN_PATTERN`, `page_keys`) opens the pattern editor on the clip's pattern from
  any field, since the page has one pattern (the user's choice).
- The clip page refuses a grab that would go round in a circle, and pasting a clip drops one,
  using `Document.grab_circle`.
- The clip page's `L` (`ClipPage.LISTEN`, or `STOP_LISTENING` while the clip plays) and its
  Play and Stop buttons, after the Advance field, listen to the clip (`.claude/features/REALTIME_PLAYBACK.md`).


## The clip page's list of patterns

The clip page shows the clip's patterns as rows (`PatternRow` in `tui/screens/arrange/clip_page.py`), always a list, even of one,
with a `+` row under them. `A` (or ENTER on `+`) opens Add Pattern, a picker of two choices: an existing pattern, from a picker
that leaves out patterns of the other kind (drum or notes), or a new blank pattern, its name filled in with the track's name and
the next number, in the track's group. Bksp takes a row out of the list and refuses on the last. `M` picks a row up (the page's
own move mode: only CARRY and DROP work, one undo step a move). ENTER on a row, or `J`, opens that pattern. Pattern order and
Step direction (the clip's Direction, renamed on the page only) come before Repeat. `ClipSlot.get_display_name` gives Arrange
`riff-a +3` for a clip of several patterns with no name.
