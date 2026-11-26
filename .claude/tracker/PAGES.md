# The List and Settings Pages

Reference notes for Claude, one part of `.claude/tracker/`: File and Notes, Songs, Scales, Generators and chains, Grooves, Instruments and Draws. `CLAUDE.md` says which part to read for which work.

## File and Notes

- The File/Global page (`F`, `FilePage`) shows a tab box, in the user's order: Settings, its settings by meaning (Title, Author,
  Description, Notes, then Default follow action and Protected), then the tabs Notes & Octaves (Default drum octave, Default octave,
  Octave labels, Step size) and Visualizers (Visualizer, and Hide Visualizers, a field opening a `PickManyDialog`,
  `interface/tracker/dialogs/pick_many_dialog.py`, where Space picks modes and ENTER keeps them), then the buttons
  New and Save As (no keys), Open and Save, with the path of the set's file and where the current song exports noted below.
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
  signature, entry size, scale, groove, genre (a `text_field`, which `FieldPage` holds for
  every settings page, as the File/Global page's title uses), Live response (a `ChoiceField` of
  `LIVE_RESPONSIVENESSES`, named by `MSG_LIVE_RESPONSIVENESS_NAMES`) and an Export button.
- Draws and Arrange edit the current song.
- A brand-new song (`Song.started`, `started_song`, `Setlist.add_started_song`, which
  `new_setlist()` and the Songs page's `A` use) starts with `track-1` and `scene-1`. A file that
  leaves tracks or scenes out stays empty (`new_song`, `Song.new`, `add_new_song`).
- Only a new set gets the starter pattern and the clip that plays it (`new_setlist`,
  `.claude/format/FILE_RULES.md`), since a song added to a set already has the set's patterns.

## Patterns, in a tab for each group

The user's design. `PatternsPage` (`interface/tracker/screens/pattern/patterns_page.py`) lists the patterns in a tab for each
group and is always sorted, so `S` (Sort) and `M` (Move) are not on it; every other list page keeps both.

- **A group is only text.** Every pattern has a text setting, `group` (`PatternSetting.GROUP`), and a group exists while a
  pattern names it; nothing else stores one. A group made on the page that holds no pattern yet is the page's own
  (`new_groups`) until a pattern is made in it, and is not in the set.
- **The tabs** (`PatternTab(kind, group)`): one per group, sorted by `name_order`; `Ungrouped`, the patterns in no group, an
  older file's, shown only while any exist, last among them; then `+ New`. The row of tabs and the box are drawn by
  `tab_box.boxed_tabs`, as a settings page's tab box is. The chosen tab is kept for the session in `app.chosen_tabs`.
- **The rows** (`Listed(kind, name)`): the chosen group's patterns, sorted by `name_order`, then `+ (New)` (`NEW_PATTERN`),
  which makes a pattern in the group and opens it; Ungrouped has no `+ (New)`, since nothing can be added there; `+ New` holds
  only the button `[ New Pattern Group ]` (`NEW_GROUP`). Both buttons are in the Patterns theme colour (`row_style`).
- **The cursor** opens on the chosen tab's first pattern, so that ENTER edits at once; `on_tabs` says it is on the row of tabs.
  `current()` is the pattern's name, or nothing on a button or the row of tabs; `listed()` says what the row is. Up from the
  list's first row goes to the row of tabs, and Down from there comes back.
- **Keys.** On a pattern: ENTER edits, `G` (Group) opens a sorted picker of the groups ending with the new group entry, `A`
  adds to the pattern's group, `N`, `C`, `Bksp` and `L` as before; a copy stays in its source's group. On the row of tabs:
  Left and Right (or `[` and `]`) choose a tab and Tab goes into the list; on a group's tab `A` adds a pattern, `N` renames
  the group, `C` copies the group and `Bksp` asks and then takes every pattern out of the group, deleting none; on `+ New`,
  ENTER makes a group. In the list Tab goes to the row of tabs; PgUp and PgDn choose the tab before or after from anywhere.
- **Copying a group** opens a prompt titled "Confirm copying the entire pattern group" with the field "New Group Name:", opened
  on the group's name counted up. Each copy's name takes the new group's name at the front, in place of the old group's name
  where the name began with it and joined with an underscore otherwise (`name_in_copied_group`); a taken name counts up; a name
  over 30 characters refuses the whole copy with the reason; the copy is one undo step.
- **Search** looks at the patterns alone, in every group, and ENTER chooses the found pattern's tab. Pickers of patterns
  elsewhere stay flat.
- **A pattern made elsewhere** takes the group named after its track: the starter pattern of a new set, a blank pattern made on
  Arrange or on the clip page, the MIDI import and the song wizard (`Setlist.group_patterns_by_track`); every example's patterns
  are grouped so too. Renaming a track renames the group of its name (`rename_named`), unless a group has the new name.

## Scales and Scale

- The Scales page (`Z`) lists the set's scales. `ENTER` opens `ScalePage`
  (`interface/tracker/screens/set/scale_page.py`), and `A` adds a C major scale and opens it.
- `ScalePage` has one scale's Name, Root and Kind on one page, laid out by `SCALE_PAGES` and
  `ROOT_KEYBOARD`. The scale picker shortens long names only on screen.
- A new scale is `scale-N` (`new_name`, `MSG_NEW_SCALE_WORD`), the user's rule, and keeps its name. A scale named after its root and kind, like `C_major`, as an import or an older file names one, is renamed as they change
  (`Document.set_scale_root` and `set_scale_kind` return the name, and `is_default_scale_name` in
  `model/objects/naming.py` decides). A name of the user's own stays.
- Under the fields, `ScalePage.notes` draws a two-octave `Keyboard`
  (`interface/tracker/components/keyboard.py`): the black keys' row above the white keys', the scale's keys
  `MSG_KEY_IN_SCALE` and the rest `MSG_KEY_OUT_OF_SCALE`. The names row brackets the root
  (`MSG_ROOT_KEY_NAME`), under its black key in place of the two white names beside it when the
  root is a black key.

## Generators and chains

- A chain is one more kind on the Generators page, Chain, among the picker's kinds (`CHAIN_LISTING` and
  `LISTED_PAGES` in `interface/tracker/screens/generators/generator_pages.py`, `file_format.CHAIN_KIND` and `LISTED_GENERATORS`), opened in the
  chain editor; a chain's own steps offer only the plain kinds (`GENERATOR_PAGES`). Chains' old cell on the main screen is
  empty, a gap the arrows pass over (`EMPTY_CELL` in `interface/tracker/screens/set/main_page.py`), until a page takes it.
- Deleting a generator, a chain among them, asks first and lists up to five uses under `It is taken out of:`
  (`ListPage.delete_taking_out`); YES deletes it and takes it out of every chain's steps and every clip's, scene's and track's list
  in one edit (`Setlist.delete_generator`, `Song.forget_generator`), the user's design.

- The Generators page (`G`, `screens/generators/generators_page.py`, the user's design) lists every generator of the set under a
  heading for its type, `- Density (2)` (`MSG_GROUP_HEADING`), the types sorted by what the tracker calls each and the generators
  sorted by name under each, always, as the Patterns page lists patterns by group, so the page has no move and no sort. Only a
  type the set has a generator of gets a heading. Every type is closed until opened (the user's rule): Space or ENTER on a heading opens and closes
  its type, which the set keeps and its file holds as `open_generator_types` (`Setlist.show_generator_type`, looking and not
  editing, as the closed pattern groups are), so the page comes back as it was left; PgUp and PgDn jump between headings, and a search looks inside closed
  types. ENTER opens the editor (`GENERATOR_PAGES` in `screens/generators/generator_pages.py`, a `GeneratorListing` of kind,
  section, label and `EDITOR` for each kind); `A`, or ENTER on the `+` row the page lists last, asks for a type, names one after
  it and opens it; `N`/F2, `C`, `Bksp` (refused while a chain uses it) and `/` as on every list, the cursor following the
  generator. The set's `generator_order` is still read and written but no page shows or changes it. Each editor's crumbs read
  `GENERATORS › name`.
- A Drift's page is drawn from its view by `PluginEditor`: Every, Steps to B, Direction and Restart, then a `DriftValuesView`,
  a row of each value's two versions side by side (`drift_values.py`, each a `SteppedCells` of `field.py`): Left and Right move
  between A and B, `[` and `]` (`keybindings.PluginEditor.SLOT_LESS` and `SLOT_MORE`) change the one under the cursor, ENTER types
  a number or picks a scale or root, and Bksp clears it. A draw's `Strip` is a `SteppedCells` too.
- A Musician's page is drawn from its view by `PluginEditor`: the Player and Touch columns, with `WhenView` hiding Chords from
  and Range for an unpitched instrument and Gives way until Tune from names a track (`MusicianSettings.holds`), and
  `InheritedChoiceView` for Gives way and Notes, "(instrument)" first and "(from instrument)" shown. Loudness and Looseness are
  `GaugeView`s. A `SectionsView` draws `section_table.py`: a `CaptionedTableRow` then `TableRow`s, one per kind of section the
  song's scenes have or the Musician holds a setting for, Plays and Played as columns of fixed width; the song wizard's Edit
  Player opens the same page in its draft.
- A Shapes generator opens `PluginEditor`, drawn from its view: Name, then a section for each of Density, Swell and Articulate
  (`shape_section` from `interface/pages/shape_fields.py`: Start, End, Over, Then, each with the shape's name in front), Swell
  accent after the Swell, and Restart. The Scene
  page and the clip page have a Velocity field and the two velocity ramp sections (`interface/pages/velocity_fields.py`,
  through `set_scene_velocity_setting` and `set_clip_velocity_setting`; a blank value shows what plays and where from)
  and a section for Density and for Articulate (`shape_section`, the same fields
  with the shape's name in front of each label), through `set_scene_shape_setting` and
  `set_clip_shape_setting` (`SongEdits`). `tests/interface/tracker/test_tui_shapes.py` tests them.
- A Chords generator's page is drawn from its view by `PluginEditor`: Name, then its Mode first (`GeneratorView.mode`), then the
  columns its mode shows (`ColumnView.modes`): Progression mode's Every and Chords (`ProgressionView`, `progression_field` in
  `interface/pages/progression_field.py`, its numerals in the song's scale), Follow Progression mode's Chords from (`TrackView`,
  `(none)` first), and in every mode Voice leading (`ToggleView`, its default by mode, written only when it differs), Lowest and
  Highest octave (`OctaveView`, `octave_field`, kept from crossing by the settings' `limits_of`), Keep the root in the bass, and
  Restart. ENTER on Chords opens the `ChordsEditor` (`screens/shared/chords_editor.py`, given the generator's section as it
  opens), a `StepEditor` with the `StepGrid`
  drawing of the one-row editors (`screens/shared/step_grid.py`) but rows of its own: a column a chord,
  a gauge of `MSG_GAUGE_BAR` up to the degree, the numeral and the name, then `#/b` and `Inv.`.
  The arrows move along the chords and between the three rows (`edited_row`); `[` and `]` step,
  digits type a degree or an inversion, Space or ENTER cycles the `#/b` and `Inv.` rows, `I` and
  `D` insert and remove, and `H` (`PICK`) opens a `GridChoiceDialog` of the named progressions,
  filling the chords through `named_progression_in` (`Document.set_progression`, handed `ProgressionRows`).
  `tests/interface/tracker/test_tui_chords_generator.py` tests the page and `test_tui_progressions.py` the chord editor.
- A plugin that describes its view (`view.py` in its folder, a `GeneratorView` of `model/schema/generator_views.py`: columns of
  settings, each a `ChoiceView`, `NumberView` (blank until given, or with a default left out of the file), `TimeView`, `StepsView`,
  `ShapeView`, `RestartView`, or a `SectionView` holding more under a heading) has no page of its own: `PluginEditor`
  (`screens/shared/plugin_editor.py`, keys `keybindings.PluginEditor`) draws its Name and then the view's settings, is given the
  plugin's section as it opens, and shows the help the view holds; `generator_pages` opens it for every such plugin. A section's
  heading says `(set)` while any setting inside is written. A `StepsView` shows `[configure]` (`MSG_CONFIGURE_STEPS`), since a long row would not fit, and ENTER opens the shared
  `StepRowEditor` (`screens/shared/step_row_editor.py`, a `StepEditor` with the `StepGrid` drawing, given the section and the
  `StepsView` as it opens): Left and Right move, Space or ENTER turns a step on or off, `I` and `D` insert and remove, the line
  above the grid the view's note. An `OffsetsView` shows an arpeggiator's offsets, ENTER opening the `OffsetsEditor` (`screens/shared/offsets_editor.py`).
  Phrasing, Shapes, Timing, Chords, Guitarify and the Arpeggiator use it; `test_tui_phrasing.py`, `test_tui_shapes.py` and
  `test_tui_step_rows.py` test it.
- A Hocket's page is drawn from its view by `PluginEditor`: Name, Source track (a `TrackView`, `(none)` first and the current
  song's tracks, sorted, the Hocket's own source kept among them even where the song lacks it) and Restart. `test_tui_hocket.py`
  tests it.
- A Guitarify's page is drawn from its view by `PluginEditor`: Name, Mode, then in Strum mode Direction, Spread in ms, Fade, Loose
  timing and Upstroke strings (`all` for every string); in Guitar mode the Left Hand (Shape chords, Tuning, Position shown as `open`
  or `fret 5` through `NumberView`'s `shown` and `zero_shown`, Capo, Strings, Single notes, Color) and the Right Hand (Play strokes,
  Bar, Let ring, the four shared settings, Approach); then Restart. Each setting is left out of the file at its default. Bar
  (`GuitarBarView`, `guitar_bar_field`) shows the ready-made bar's name or `custom`, the cells and the cell length, and ENTER opens the
  `GuitarBarEditor` (`screens/shared/guitar_bar_editor.py`), a `StepGrid` of a Stroke row over an Accent row: Left and
  Right move, `[` and `]` (Up and Down too) step the stroke through `STROKES`, stopping at both ends, Space or ENTER accents,
  `I` and `D` insert and remove a cell (1 to 32), `S` steps the cell length round `CELL_LENGTHS`, and `R` picks a ready-made
  bar from a list, which replaces strokes, accents and cell length as one undo step. The line above the grid says the
  cursor's stroke in words. `tests/interface/tracker/test_tui_guitarify.py` tests both.
- Every generator's editor ends its own settings with `restart_field(page)`
  (`interface/pages/restart_field.py`), a `ChoiceField` of `RESTARTS` named by `MSG_RESTART_NAMES`, found by
  the page's `SECTION` and `item`.
- Every time setting's field is `time_field(page=, label=, written=, first=, store=)`
  (`interface/pages/time_field.py`): its first choice, standing for blank, then `TIME_CHOICES`, named by
  `MSG_TIME_NAMES` where a dotted or triplet fraction says nothing, and a value the list lacks
  offered last so nothing is lost. The arp editor's Step, the drift editor's Every and the
  shapes' Over use it.
- The shared page of a plugin's view has a Name field, and the chain editor's `N` renames.
- The chain editor shows each step as the generator's name and then its kind, `sparse (Density)` (`steps_shown`), the user's choice over
  `density: sparse`, which read as a chain's name; a generator listed again is numbered on screen only, `sparse 2 (Density)`.
- The chain editor's picker of generators (`ChainEditor.pick_generator`, for `A` and ENTER) offers `(new generator)`
  first, the user's ask, which asks for a kind (`new_generator`, in `GENERATOR_PAGES` order), makes one named after
  the kind (`arpeggiator 1`, numbered after the first), puts it in the chain where the step was being added or
  changed, and opens its editor with the chain's crumbs first (`ShowsNamedItem.opened_from`).
- An arp's offsets have their own editor (`.claude/tracker/PATTERN_EDITOR.md`, "The offsets editor").

## Grooves

- The Grooves page (`V`, `GroovesPage`) lists the factory grooves first, marked `factory`, with
  only `ENTER` (view) and `C` (copy) on them, and the set's own with the usual list keys.
- `A` adds `groove-1` and so on (`new_name` in `model/objects/naming.py`) and opens the `GrooveEditor`.
- The `GrooveEditor` is a one-row editor like the offsets editor (`.claude/tracker/PATTERN_EDITOR.md`, "The one-row editors"),
  with `I`, `D`, `S` for the cell length (`GROOVE_CELL_LENGTH_CHOICES`) and `N` to rename, and
  the name shown above the cells. A groove wider than the screen scrolls sideways, with
  `cells 1-11 ›` (`MSG_CELLS_SHOWN`) at the right of the name, where the cells used to wrap onto
  more blocks.
- In both one-row editors `[` and `]` nudge the cell and are what the legend names
  (`OneRowEditor.LESS` and `MORE`, `[` dec and `]` inc), with Up and Down doing the same off
  the legend (`NUDGE_LESS_KEYS`, `NUDGE_MORE_KEYS`), since no row lies below the cursor.
- The Song, Scene and Track pages have a Groove field. The last two are built by
  `interface/pages/groove_choice.py`, stepping through take-from-above, `off` and the names.

## Instruments and the Real Time switch

- The Instruments page (`I`, `InstrumentsPage`, a `NamedListPage`) lists the set's instruments
  with each one's device, channel and uses. `A` adds `instrument-1` and so on
  (`new_name`) with no device, and opens the `InstrumentEditor`, a `FieldPage`
  with Name, Device and Channel. Device opens a `ChoiceDialog` of `(none)` and the computer's
  ports (`output_port_names()` in `realtime/sender_process/outputs.py`, sorted), the instrument's own device
  among them even when it has gone, so that a set opens without it and keeps it. Channel is a
  `NumberField` from 1 to 16, or a plain `Field` showing `MSG_AUTO_CHANNEL_SHOWN` (`(auto)`) while
  the Device is `*FluidSynth` (`channel_field`), which the device picker offers after `(none)`,
  leaving out any tracker's own FluidSynth port (`FLUIDSYNTH_PORT_PREFIX`). GM sound opens a `SoundDialog` (`interface/tracker/dialogs/sound_dialog.py`, the user's design) of `(none)` above General MIDI's
  families (`MSG_GM_FAMILIES`, `MSG_GM_SOUNDS`, `sound_families`), each a row that opens a flyout of its eight sounds; `/` searches every
  sound and ENTER there opens the flyout of the sound found, since letters are keys in this dialog; `L` tries the sound under the cursor
  through a `SoundTrial` (`interface/tracker/screens/shared/sound_trial.py`), which has the pattern preview play a run once through General MIDI in
  FluidSynth (`PatternPreview.play_sound`), or, where FluidSynth is not installed, on the song's Preview instrument, which is sent the
  notes and no sound of its own (the user's design); where neither can sound, the dialog says what to do in amber under its rows until
  the next key (`sound_refusal`, `ERR_NOTHING_TO_TRY_A_SOUND_WITH`); stopped by `L` again, a move of the cursor
  or closing
  , and `[` and `]` step it by number (`step_gm_sound`). An asker whose sound plays on one note passes `note=`, and the dialog keeps a Note row in view under its list: `[` and `]` step the note, a name such as C3 or f#2 typed and ENTER sets it (`interface/forms/note_names.py`), ENTER with nothing typed takes the sound the dialog opened on, and the answer is the sound and the note.
- The track editor's last field, Instrument, picks one of the set's instruments or `(none)`.
- The main screen's Real Time cell (`T`, `MainPage.toggle_real_time`) sits among the pages,
  with `MSG_REAL_TIME_ON_MARK` (`●`) or `MSG_REAL_TIME_OFF_MARK` (`○`) where a page's cell has
  its count. With no instruments it tells `ERR_ADD_INSTRUMENT_FIRST` in a dialog; otherwise it
  flips the set's `real_time` and says so on the status line. Turning it off while something plays stops it
  (`MSG_REAL_TIME_OFF_STOPPED`), and `Transport.tick` stops whatever plays once the switch is off by any path, deleting the
  last instrument included, since Arrange shows no stop with Real Time off (a bug the user found). A cell's count sits against the
  box's edge when a name as long as Instruments leaves no room for the space before it.
- The Scene page's last field is the Launch together toggle, and the clip page's last field is
  Advance, the clip's follow action (`.claude/format/FILE_RULES.md`, "Follow action and Launch together").

## Draws

- The Draws page (`D`, in the main screen's middle cell where Modulators were; `interface/tracker/screens/set/draws_page.py`, the user's design):
  a section for each draw, AD to HD, closed at first, each with Direction (a `ChoiceField` of `DRAW_DIRECTIONS`), Slots (1 to 64),
  Value Min and Value Max (-99 to 99, a new end moving every slot past it), Conditions redraw (a `Toggle`, off for a new draw), then
  after one blank line its strip, a `Strip` (`interface/forms/nodes.py`, drawn by `interface/tracker/renderers/fields.py`): a grid boxed in dim lines, a `slot` row numbering the
  slots over a `value` row, every cell one width with a space either side of -99 and its value right-justified, the cursor's slot
  in reverse video (`FieldPage.strip_lines`); Left and Right move between slots (`ALONG_CELLS`), `[` and `]` step one
  (`SLOT_LESS`, `SLOT_MORE`), ENTER types one and Bksp makes it blank; it scrolls with the cursor past the page's width. While a
  song plays, each draw's last slot is drawn in the draws' bright violet (`Style.DRAW_LIGHT`, from `Transport.draw_places`, which
  asks the score, `Score.draw_places_at`, where every draw stood that many seconds into the playing scene, from each timeline's
  `get_draw_moments`), and a draw's heading says the slot, `▸ 3` (`MSG_DRAW_HEADING_LIT`). The Scene page has a Reset toggle for
  each draw, which resets it as the scene first starts.
- A statement's pickers, on the settings pages' tables and the pattern editor's statement rows, offer the draws under
  `--Draws--`, and a value's picker a number to type first under `--Constant--`
  (`interface/forms/grouped_choices.py`, `GroupedChoices`): a `ChoiceDialog` may hold headings and blank lines between groups, drawn
  dim, which the cursor passes over and a search leaves out. `[` and `]` step a statement's first cell through the same order.
- A `FieldPage` taller than the screen scrolls to keep the cursor's field in view (`window_of_lines`).
- The scene page has a Reset field for each.

## The song wizard

The user's design, agreed in detail in `.claude/planning/WIZARD_DESIGNS.md` (S16 to S39), of which this is the part built.

- `W` on the main screen (`MainPage.WIZARD`, the Wizard cell beside Songs) opens `WizardPage`
  (`interface/tracker/screens/wizard/wizard_page.py`); no other page opens it, since many keyboards have no F keys to spare.
  The page is a `FieldPage`: a row of tabs, one per top branch (`WizardTree.roots`: Genre, with the subgenre's fields, Band,
  Composition, Form, Apply), over a box (`renderers/tab_box.boxed_tabs`), and `< Back` and `Next >` buttons at the box's foot, inside it, showing their keys PgUp and PgDn, which work
  from anywhere in the wizard, the fields included, where they choose a tab and not a section (Back alone on
  the last tab, `WizardPage.buttons`; the Apply tab's own Apply button follows its summary). A tab with branches under it lists them at the box's left, 24 cells
  wide, every branch shown (no folding), each a space in from the one holding it, its own row first, named for what its fields
  hold (`MSG_WIZARD_TAB_OWN_ROWS`: Members on Band, Summary on Composition, Shape on Form), and at the right the fields of the branch under the cursor, drawn by
  `FieldPage.body`, the cursor's mark on a field only while the cursor is in the fields; a tab of one branch shows its fields alone. A
  tab whose branch refuses (`Tab.not_ready`) is dim and says why in its box. Its stripe is bright cyan.
- The cursor is on the row of tabs (`on_tab_row`), in the list, in the fields (`in_fields`) or on the buttons
  (`on_buttons`), as a settings page's tab box has it: Tab between the row and the box; on the row Left and Right choose a
  tab and Tab, ENTER or Down go in; in the list Up and Down move, Up from its head to the row and Down from its foot to the
  buttons, ENTER or Right into the fields, onto the first field that does something (the buttons where none does), and PgUp
  and PgDn choose a tab; in the fields the keys are a settings page's, and ESC or Left (where no field takes Left) move back.
  Outside a list, a tab of one branch keeps the cursor on the row (`settle_cursor`). ESC outside the fields closes the
  wizard, asking first once anything was chosen (`choosing` wraps every setter and notes it).
- The page knows nothing of any one branch, the user's ask, who expects to revise the organization: a `Branch`
  (`branch.py`) says its `name`, `note`, `children`, `fields`, `notes` and `refusal`, and `WizardPage.roots()` lists the
  top branches (the Chords branch's Progression, under Composition, starts on "any", each run then drawing one of the subgenre's; rock's singer has no Plays field, the Sound field alone choosing what stands in for the voice; the drums' branch has Fills come, a gauge of four positions, "never", "each section", "every 4 bars" and
  "every 2 bars", drawn empty at "never", the user's design, and a Quiet notes toggle where the snare of the groove chosen has
  soft strokes; the drums' branch has a toggle for each piece of the kit the song plays, `kit: kick`, the user's design, the
  last piece staying on; the Band's Guitarists field, "2" or "1", the user's choice, shows where the genre's template says who its
  one guitarist would be: with "1" the player of the solo is not shown, `roles_shown`, and the player of the chords is called
  "guitar"; a player is shown by `role_title`, the clearer name the genre's template gives the player, which may follow
  how the player plays; the Band's Sounds field, "usual", "acoustic", "electric" or "synth", is the band's, and a player's
  Sound field shows the band's sound as `(from band)` or the player's own, an override, the user's design, picked from the
  band's again, the genre's sounds for the player, or "More sounds", every General MIDI sound by family in the same `SoundDialog`, tried as a run of the song's scale from its root in the player's octave), in the order Genre, Band, Themes, Form, Playing, Apply. `ThemesBranch` and `PlayingBranch` are built in a
  first working form, the user's ask that every page work before any is deepened (`SongWaysBranch`, a field for each way
  the whole song goes, shown only where the subgenre has more than one way, the branch saying so where none is): Composition
  (`CompositionBranch`) holds no fields of its own: its branches are Chords (`ChordsBranch`, Progression, each progression shown with its numerals, `three chord (I IV I V)`, in the field and its list, and under the field the chords each kind of section plays, spelled in the song's key, or a line saying they are drawn when the song is made while the field reads "any"), Melody (`MelodyBranch`: Melody played by, then Busy, Range and Repeats, each list marking the genre's own value, `WizardChoices.melody_ways_offered`, then Character, "from genre" until chosen, then the Phrasing switch and Edit Phrasing; the writing methods and their gauges are underneath, chosen by Character, `CHARACTER_ENGINES` and `CHARACTER_GAUGES`), Melodies (`MelodiesBranch`, a group with no fields, open from the start, which Left and Right close and open; the tree's rows are walked to any depth, `WizardPage.rows`), holding Hook (`HooksBranch`: two headings that start open, `starts_open`; under Main Hook, Sung in, read only, Intro hook, Behavior, a list of `hook_writing.BEHAVIORS` with the genre's marked, and the behavior's gauges, `hook_gauges`, each a `writing_gauge_field` of `Branch`, 0 to 9, said to be the genre's until moved, Bksp giving it back, with a Main hook switch only where the genre's songs have no hook unless asked or the song was kept without one; under Second Hook, the Second hook switch and Tag sung in, `second_hook_kinds`; the buttons Listen, which plays the hook under the cursor's heading, Regenerate, which asks and then draws another take, and New Second Hook; and under the fields the main hook's picture, `picture_of` in `hook_picture.py`) and then a panel for each kind of section with a melody (`SectionMelodyBranch`; the kind that carries the hook, `is_body_of_hook`, shows Placement, `hook_placements_offered`, each value a whole plan of the chorus's lines, `plan_with_hook_placed`, and the body's gauges, `body_gauges`, in place of Height and Busy, named for the kind and remembered by `MELODY_KEY`: Height and Busy, each one list of every value in its own order, the genre's or the song's own value said to be so and giving the field back when picked, a value that makes the same song as that one left out; Notes, which ENTER opens in the pattern editor and Bksp gives back to the wizard; and the buttons Listen, Listen With Band and Regenerate, none with a key of its own but `L`, Regenerate asking first and starting on NO), Riffs (`RiffsBranch`: a heading for each player a riff can be written for, closed at first and saying how many it holds, `(2)`, the columns BARS and USED IN while open, a row a riff and a `+` row; on a heading `A` opens `NewRiffDialog`, on a riff ENTER opens its notes through `RiffChoices.riff_heard`, a song where the riff's own player plays it, `N` renames, `C` copies for a player picked from a list, `R` regenerates after asking, `L` listens and Bksp deletes after a question titled in red that says where the riff is used), Riff Assign (`RiffAssignBranch`: the riffs each player knows, with who each was written for and where the player plays it; `A` gives the player another of the song's riffs, Bksp takes one away, asking only where the player plays it) and Section Players (`SectionPlayersBranch`: a heading for each kind of section and under it a field for each player with more than one choice there: "accompaniment", or "rests" for the genre's melody player, "melody", and each riff the player knows). A panel's own keys in its fields come from `Branch.field_keys()`. A player's panel has, while the song's melodies are written in rows (the Character "atonal") and the player plays lines, the fields Lengths, Loudness and Articulation (`PlayerBranch.row_field`), each showing the row and `(from genre)` until changed, ENTER opening the Row dialog (`interface/tracker/dialogs/row_dialog.py`): a bar over each number, Left and Right moving, `[` and `]` stepping between the row's lowest and highest, I and D inserting and removing a cell, Bksp putting the genre's row back, ENTER OK and ESC CANCEL. Under the switch while the song has a hook is the button New hook (`WizardChoices.new_hook`): the song keeps which take of the hook it has, `hook_take`, and a take after the first is rolled with dice of its own (`HOOK_TAKE_SEED` in `wizards/create_song/melody.py`), so that only the hook's lines change. A run draws its seed when it starts (`WizardPage.start_with`), so that the hook shown is the hook Apply makes, each a `SongWaysBranch`, and Composition lists what each is set to, leaving out one with nothing to choose; Playing has Fills, a fill chosen there being played whatever the drummer's Busy level would play (Feel is gone until a feel changes what is played: a style's feels were written into its drums and the field chose nothing; a melody style that sketches as "usual" does is not offered). Built so far: `GenreBranch` (Genre and Subgenre, each starting on `(choose)`, then Key, Scale and Tempo once
  a subgenre is chosen, with Meter, the subgenre's and only shown, and Length, the song's length with the form's name,
  whose `[` and `]` choose the next shorter and longer form, since the length follows the sections, and the song's Name), `BandBranch` and `FormBranch` both start open in the tree, the user's ask, since a closed branch hid its pages twice. `FormBranch` (which starts open in the tree, the user's ask, so that the sections and their keys show themselves; the
  form's name, only shown, reading "your own" once a section was changed; the "Use a suggested form" button, the user's
  design, which opens a dialog of the subgenre's forms, each with its sections and length, and asks first where it would
  replace sections a person changed, since no stepped field may replace a person's work with one stray key; the sections
  listed under the button with a line saying they are in the tree, and a `SectionBranch` for each section by its place: Kind, Bars, offered
  only at the lengths the subgenre's parts fill, and a toggle for each player of the band, a section keeping one. A section is
  one of a list and takes a list's keys in the tree, the user's ask for an editable form: In the tree and the list, a kind the form has several of is numbered, `verse-1`, `verse-2`, the user's design (`section_labels`). `I` (insert) asks the kind in a picker
  and puts the new section before the cursor's, as on Arrange, and `A` (add) puts one at the form's end, the user's wording; `C` (copy), `Bksp` (delete), with no
  question since nothing is in the set yet, the last section staying; and `M` (move), the tracker's move mode, the carried
  section's name between `<` and `>`. A `Branch` says `adds()`, `is_listed()`, `kinds_to_add()`, `add`, `copy`, `remove` and
  `move`, so another list in the tree gets the same keys. Once the form is the song's own, the Genre branch's Length is only
  shown) and `CreateBranch` (a summary and the Create button, refused with `(genre?)`
  until a genre and a subgenre are chosen), and `BandBranch`, a toggle for each player the genre's band may have, with a
  `PlayerBranch` under it for each player who is in: Plays, the way the player plays, or a field for each part of the
  drums, and Busy, 1 to 4, drawn as a horizontal Busy gauge. The last player cannot be left out. A player's Sound, the
  Sounds field, the kit's pieces and the Interplay section are to come. The Playing branch is gone: its one field is the drums' Fill pattern (`PlayerBranch.fill_pattern_fields`), beside Fills come and Fill size, and a branch for the whole song's playing returns with Intensity, Contrast and Humanize. A player's own gauges (`PlayerBranch.player_gauge_field`, `MSG_WIZARD_PLAYER_GAUGE_LABELS`) are fields under the player's Busy field, each 0 to 20 drawn as a horizontal gauge; Busy is the preset that fills them in and reads `(custom)` once one is moved, until a Busy level is chosen again.
- When the current song was made by the wizard, `W` first asks how to start in a picker titled Song Wizard, the user's
  design after a Start branch in the tree proved poor (`LlamatronApp.show_wizard`, the ways in `starts.py`): a new song or
  the current song replaced, each from the settings the current song kept or from scratch. ESC opens no wizard. Replacing
  keeps the song's name, which the Genre branch then only shows, and its place (`Document.replace_with_made_song`,
  `Setlist.replace_song`), as one undo step. The picker's last row is CANCEL, the user's ask. Every run of the wizard
  draws a new seed at Create, the user's rule: a run from the last settings keeps the settings and never the seed, and
  there is no Take field. The four names are Claude's shortening of the user's, which the user accepted. A current song nothing was
  done to, as a new set's (`Setlist.song_is_untouched`), is filled in place under the wizard's name, where otherwise a song
  is added. Create turns the set's Real Time switch on, in the same undo step, the user's ask, so that the song can be
  played at once.
- Nothing in the set changes until Create, so undo and redo do nothing in the wizard and say why (`Page.steps_history`,
  `why_no_history`). Create is `Document.add_made_song`: `Setlist.take_in` of the set `WizardChoices.made_setlist` made
  (`.claude/features/SONG_WIZARD.md`, "The Wizard's Choices"), one change and so one undo step, after which
  `LlamatronApp.show_arrange_on_new_song` closes down to the main screen and opens Arrange on the song.
- `tests/interface/tracker/test_tui_wizard.py` tests the page and undo, and the key tour and the fields tour both visit it.

- **The picker of a new generator's type** (the user's design). `generator_type_dialog` in `interface/tracker/screens/generators/generator_pages.py`
  makes a `ChoiceDialog` of every type sorted by name, capitals ignored, with no headings, searched by typing. The Generators page's `A` and the chain editor's new generator both open it.
  Every type's name starts with a capital, Arpeggiator included (the user's rule).
  `tests/interface/tracker/test_tui_generator_type_picker.py` tests it.

Every page of one generator is a `GeneratorEditor` (`interface/tracker/screens/shared/generator_editor.py`): `settings()` is the generator's settings and `store(setting=, value=)` keeps one, and a page overrides `store` only where a value at its default is left out of the file. `ShowsNamedItem` holds the constructor of every page of one named thing, `(holder=, name=)`; a page that takes more calls it with both.
