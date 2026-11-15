# Arrange

Reference notes for Claude, one part of `.claude/tracker/`: Arrange, its details view, Scene View, the track editor and clip page, and real-time playback on the pages. `CLAUDE.md` says which part to read for which work.

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
  not otherwise), and Space plays and stops ("Real-time playback" below).

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
  name's own details, the user's choice over the whole column or row (`dev_notes/IDEAS.yml`). A cell with no details of
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
  Play and Stop buttons, after the Advance field, listen to the clip ("Real-time
  playback" below).

## Real-time playback

- `Transport` (`tui/transport.py`, `app.transport`) is the tracker's side of real-time playback,
  between the pages and the player (`.claude/format/PLAYBACK.md`, "Real-time playback"). It answers
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

