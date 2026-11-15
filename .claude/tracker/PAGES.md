# The List and Settings Pages

Reference notes for Claude, one part of `.claude/tracker/`: File and Notes, Songs, Scales, Generators and chains, Grooves, Instruments and Registers. `CLAUDE.md` says which part to read for which work.

## File and Notes

- The File/Global page (`F`, `FilePage`) shows, in the user's order, the loose settings alphabetically (Author, Default follow
  action, Description, Notes, Protected, Title), then the sections Notes & Octaves (Default drum octave, Default octave,
  Octave labels, Step size) and Visualizers (Visualizer, and Hide Visualizers, a field opening a `PickManyDialog`,
  `tui/dialogs/pick_many_dialog.py`, where Space picks modes and ENTER keeps them), then Save and Open
  buttons, with the path of the set's file and where the current song exports noted below. `N`
  starts a new set and `W` saves as.
- The Description field is one line of text, typed in a prompt like the title. The Notes field
  shows the notes' first line or `not set`, and ENTER on it opens `NotesPage` editing
  (`editing=True`). The page was the Description page until the user made the
  description one line and the long text the notes.
- Editing types into a draft of the page's own until Tab reaches the Save and CANCEL buttons
  under the text (`MSG_NOTES_BUTTONS`, `on_buttons`, `button`; Left and Right choose, ENTER
  presses, Tab comes back to the text). Save stores the draft as one edit. CANCEL, or ESC
  anywhere, throws the draft away.
- Reading, ESC goes back, Up and Down scroll (`scroll`), `E` edits and `Bksp` clears after
  asking.
- A protected set's notes open reading with no `E` or `Bksp`
  (`MSG_NOTES_PROTECTED`): it is read-only even though the set's other settings can be
  changed and saved as a copy.

## Songs and Song

- The Songs page (`S`, `SongsPage`) lists the songs and marks the current one with `●`. `Space`
  makes the selected song current, and `ENTER` makes it current and opens `SongPage`.
- It adds, copies, renames, moves, sorts and deletes songs, refusing to delete the last one.
- `SongPage` has the song's name, which `ENTER` on the Name field renames, then tempo, time
  signature, entry size, scale, seed, groove, genre (a `text_field`, which `FieldPage` holds for
  every settings page, as the File/Global page's title uses), Live response (a `ChoiceField` of
  `LIVE_RESPONSIVENESSES`, named by `MSG_LIVE_RESPONSIVENESS_NAMES`) and an Export button.
- Registers and Arrange edit the current song.
- A brand-new song (`Song.started`, `started_song`, `Setlist.add_started_song`, which
  `new_setlist()` and the Songs page's `A` use) starts with `track-1` and `scene-1`. A file that
  leaves tracks or scenes out stays empty (`new_song`, `Song.new`, `add_new_song`).
- Only a new set gets the starter pattern and the clip that plays it (`new_setlist`,
  `.claude/format/FILE_RULES.md`), since a song added to a set already has the set's patterns.

## Scales and Scale

- The Scales page (`Z`) lists the set's scales. `ENTER` opens `ScalePage`
  (`tui/screens/set/scale_page.py`), and `A` adds a C major scale and opens it.
- `ScalePage` has one scale's Name, Root and Kind on one page, laid out by `SCALE_PAGES` and
  `ROOT_KEYBOARD`. The scale picker shortens long names only on screen.
- A new scale is `scale-N` (`new_name`, `MSG_NEW_SCALE_WORD`), the user's rule, and keeps its name. A scale named after its root and kind, like `C_major`, as an import or an older file names one, is renamed as they change
  (`Document.set_scale_root` and `set_scale_kind` return the name, and `is_default_scale_name` in
  `composition/naming.py` decides). A name of the user's own stays.
- Under the fields, `ScalePage.notes` draws a two-octave `Keyboard`
  (`tui/components/keyboard.py`): the black keys' row above the white keys', the scale's keys
  `MSG_KEY_IN_SCALE` and the rest `MSG_KEY_OUT_OF_SCALE`. The names row brackets the root
  (`MSG_ROOT_KEY_NAME`), under its black key in place of the two white names beside it when the
  root is a black key.

## Generators and chains

- The Generators page (`G`, `screens/generators/generators_page.py`, the user's design) lists every generator of the set on one
  list, its kind in parentheses beside its name (`MSG_GENERATOR_KIND_SHOWN`), in the order `Setlist.ordered_generators`
  gives: the set's `generator_order` (`.claude/format/FILE_RULES.md`), then any it leaves out, kind by kind. ENTER opens the editor
  (`GENERATOR_PAGES` in `screens/generators/generator_pages.py`, a `GeneratorListing` of kind, section, label and `EDITOR` for each kind);
  `A` asks for a kind, names one after it and opens it; `N`/F2, `C` (the copy straight after), `Bksp` (refused while a chain
  uses it) and `/` as on every list; Move mode keeps the order in the set (`Document.move_generator`). There's no sort, and no
  page of one kind: the fifteen were taken out, and each editor's crumbs read `GENERATORS › name`.
- The drift editor (`screens/generators/drift_editor.py`, a `FieldPage`) lists the drift's own settings, then
  one row per value with A's and B's side by side, the picked one in `MSG_DRIFT_PICKED`; on such a
  row Left and Right pick the version (`DriftEditor.VERSION`), so only `[` and `]` change a value,
  and the page scrolls as settings pages do.
- A Density, Swell or Articulate opens a `ShapeEditor` (`screens/generators/shape_editor.py`): Name, then `shape_fields` from
  `screens/generators/shape_fields.py` (Start, End, Over, Then), and on the swell editor Accent. The Scene
  page and the clip page end with a section for each shape (`shape_section`, the same fields
  with the shape's name in front of each label), through `set_scene_shape_setting` and
  `set_clip_shape_setting` (`SongEdits`). `tests/tui/test_tui_shapes.py` tests them.
- The `ProgressionEditor` has Name, Every and Chords, whose
  ENTER opens the `ChordsEditor` (`screens/generators/chords_editor.py`), a `StepEditor` with the `StepGrid`
  drawing of the one-row editors (`screens/shared/step_grid.py`) but rows of its own: a column a chord,
  a gauge of `MSG_GAUGE_BAR` up to the degree, the numeral and the name, then `#/b` and `Inv.`.
  The arrows move along the chords and between the three rows (`edited_row`); `[` and `]` step,
  digits type a degree or an inversion, Space or ENTER cycles the `#/b` and `Inv.` rows, `I` and
  `D` insert and remove, and `H` (`PICK`) opens a `GridChoiceDialog` of the named progressions,
  filling the chords through `named_progression_in` (`Document.set_progression`).
- The `VoiceLeadingEditor` has Name, Lowest octave and Highest octave
  (`octave_field`, `screens/shared/octave_field.py`, which the track editor's range shares) and the toggle
  Keep the root in the bass. `tests/tui/test_tui_voice_leading.py` tests them.
- The `StrumEditor`, and the `+ Strum` sections at the end of the
  track editor and the clip page, share `strum_fields` (`screens/generators/strum_fields.py`): Direction, with
  `(none)` first on a track and `(track)` on a clip, Spread named with its milliseconds, Fade, Loose
  timing and Upstroke strings, prefixed Strum in a section. `tests/tui/test_tui_strum.py` tests them.
- The `EuclidEditor`, and the track
  editor's `+ Euclid` section, share `euclid_fields` (`screens/generators/euclid_fields.py`): Hits, Steps,
  Rotate and Step; on the Hits field, `H` (`PICK_RHYTHM`, bound by the page's `page_keys` only
  there) opens `pick_rhythm`, a `ChoiceDialog` of the named rhythms. `tests/tui/test_tui_euclid.py`
  tests them.
- A Glide, Shorten, Rush or Drag opens its editor (each a `StepRowGeneratorEditor`, its steps on one line by `steps_text`: Name, Step, its amount,
  Steps and Restart). ENTER on Steps opens the kind's steps page (`GlideStepsEditor` and the rest),
  each a `StepRowEditor` (`screens/generators/step_row_editor.py`, a `StepEditor` with the `StepGrid`
  drawing): Left and Right move, Space or ENTER (Up and Down off the legend) turns a step on or
  off, `I` and `D` insert and remove. `tests/tui/test_tui_step_rows.py` tests them.
- The `HocketEditor` has Name,
  Source track (a `ChoiceField` of `(none)` and the current song's tracks, sorted, the Hocket's own
  source kept among them when the song lacks it) and Restart. `tests/tui/test_tui_hocket.py` tests them.
- The `GuitarifyEditor` (`screens/generators/guitarify_editor.py`) has Name, a `+ Shape` section (Shape chords, Tuning,
  Position shown as `open` or `fret 5`, Capo, Strings, Single notes) and a `+ Strokes` section (Play strokes, Bar, Let ring,
  Spread in ms, Fade, Loose timing, Upstroke strings, `all` for every string), then Restart; each setting is left out of the
  file at its default. Bar shows the ready-made bar's name or `custom`, the cells and the cell length, and ENTER opens the
  `GuitarBarEditor` (`screens/generators/guitar_bar_editor.py`), a `StepGrid` of a Stroke row over an Accent row: Left and
  Right move, `[` and `]` (Up and Down too) step the stroke through `STROKES`, stopping at both ends, Space or ENTER accents,
  `I` and `D` insert and remove a cell (1 to 32), `S` steps the cell length round `CELL_LENGTHS`, and `R` picks a ready-made
  bar from a list, which replaces strokes, accents and cell length as one undo step. The line above the grid says the
  cursor's stroke in words. `tests/tui/test_tui_guitarify.py` tests both.
- Every generator's editor ends its own settings with `restart_field(page)`
  (`screens/generators/restart_field.py`), a `ChoiceField` of `RESTARTS` named by `MSG_RESTART_NAMES`, found by
  the page's `SECTION` and `item`.
- Every time setting's field is `time_field(page=, label=, written=, first=, store=)`
  (`screens/generators/time_field.py`): its first choice, standing for blank, then `TIME_CHOICES`, named by
  `MSG_TIME_NAMES` where a dotted or triplet fraction says nothing, and a value the list lacks
  offered last so nothing is lost. The arp editor's Step, the drift editor's Every and the
  shapes' Over use it.
- The arp and AutoRatchet editors have a Name field, and the chain editor's `N` renames.
- The chain editor shows each step as the generator's name and then its kind, `sparse (Density)` (`steps_shown`), the user's choice over
  `density: sparse`, which read as a chain's name; a generator listed again is numbered on screen only, `sparse 2 (Density)`.
- The chain editor's picker of generators (`ChainEditor.pick_generator`, for `A` and ENTER) offers `(new generator)`
  first, the user's ask, which asks for a kind (`new_generator`, in `GENERATOR_PAGES` order), makes one named after
  the kind (`arpeggiator 1`, numbered after the first), puts it in the chain where the step was being added or
  changed, and opens its editor with the chain's crumbs first (`ShowsNamedItem.opened_from`).
- An arp's offsets have their own editor ("The offsets editor" below).

## Grooves

- The Grooves page (`V`, `GroovesPage`) lists the factory grooves first, marked `factory`, with
  only `ENTER` (view) and `C` (copy) on them, and the set's own with the usual list keys.
- `A` adds `groove-1` and so on (`new_name` in `composition/naming.py`) and opens the `GrooveEditor`.
- The `GrooveEditor` is a one-row editor like the offsets editor ("The one-row editors" below),
  with `I`, `D`, `S` for the cell length (`GROOVE_CELL_LENGTH_CHOICES`) and `N` to rename, and
  the name shown above the cells. A groove wider than the screen scrolls sideways, with
  `cells 1-11 ›` (`MSG_CELLS_SHOWN`) at the right of the name, where the cells used to wrap onto
  more blocks.
- In both one-row editors `[` and `]` nudge the cell and are what the legend names
  (`OneRowEditor.LESS` and `MORE`, `[` dec and `]` inc), with Up and Down doing the same off
  the legend (`NUDGE_LESS_KEYS`, `NUDGE_MORE_KEYS`), since no row lies below the cursor.
- The Song, Scene and Track pages have a Groove field. The last two are built by
  `screens/arrange/groove_choice.py`, stepping through take-from-above, `off` and the names.

## Instruments and the Real Time switch

- The Instruments page (`I`, `InstrumentsPage`, a `NamedListPage`) lists the set's instruments
  with each one's device, channel and uses. `A` adds `instrument-1` and so on
  (`new_name`) with no device, and opens the `InstrumentEditor`, a `FieldPage`
  with Name, Device and Channel. Device opens a `ChoiceDialog` of `(none)` and the computer's
  ports (`output_port_names()` in `realtime/outputs.py`, sorted), the instrument's own device
  among them even when it has gone, so that a set opens without it and keeps it. Channel is a
  `NumberField` from 1 to 16, or a plain `Field` showing `MSG_AUTO_CHANNEL_SHOWN` (`(auto)`) while
  the Device is `*FluidSynth` (`channel_field`), which the device picker offers after `(none)`,
  leaving out any tracker's own FluidSynth port (`FLUIDSYNTH_PORT_PREFIX`). GM sound opens a `GridChoiceDialog` of `(none)` above General MIDI's
  families (`MSG_GM_FAMILIES`, `MSG_GM_SOUNDS`), `FAMILIES_A_PAGE` (2) to a page (`sound_pages`)
  so that the longest names fit 80 columns, and `[` and `]` step it by number (`step_gm_sound`).
- The track editor's last field, Instrument, picks one of the set's instruments or `(none)`.
- The main screen's Arrange cell reads Arrange/Play while the set's Real Time switch is on (`MainPage.shown_name`, `PageName.ARRANGE_PLAY`), the user's design; its theme, sentence and crumbs keep the name Arrange.
- The main screen's Real Time cell (`T`, `MainPage.toggle_real_time`) sits among the pages,
  with `MSG_REAL_TIME_ON_MARK` (`●`) or `MSG_REAL_TIME_OFF_MARK` (`○`) where a page's cell has
  its count. With no instruments it tells `ERR_ADD_INSTRUMENT_FIRST` in a dialog; otherwise it
  flips the set's `real_time` and says so on the status line. Turning it off while something plays stops it
  (`MSG_REAL_TIME_OFF_STOPPED`), and `Transport.tick` stops whatever plays once the switch is off by any path, deleting the
  last instrument included, since Arrange shows no stop with Real Time off (a bug the user found). A cell's count sits against the
  box's edge when a name as long as Instruments leaves no room for the space before it.
- The Scene page's last field is the Launch together toggle, and the clip page's last field is
  Advance, the clip's follow action (`.claude/format/FILE_RULES.md`, "Follow action and Launch together").

## Registers

- The Registers page (`R`) edits the current song's four registers as a grid, the user's design: a row for each register and
  a column for each setting, `MSG_REGISTER_COLUMNS` (Allowed inc max, At limit, a `ChoiceField` of `AT_LIMITS` named by
  `MSG_AT_LIMIT_NAMES`, Minimum, Default, Maximum, Reset each scene), the arrows moving over it (`move_in_grid`), `[` and `]`
  adjusting, the cursor's cell in reverse video and its field's label under the grid; each field still carries the
  register's name in its label.
  Lowering Allowed inc max calls `Setlist.hold_adds_within_limits` in the same edit (`set_register_setting`).
- A `FieldPage` taller than the screen scrolls to keep the cursor's field in view (`window_of_lines`).
- The scene page has a Reset field for each.

