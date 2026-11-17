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

## Patterns, by group

The user's design. `PatternsPage` (`tui/screens/pattern/patterns_page.py`) lists the patterns by group and is always sorted, so
`S` (Sort) and `M` (Move) are not on it; every other list page keeps both.

- **A group is only text.** Every pattern has a text setting, `group` (`PatternSetting.GROUP`), and a group exists while a
  pattern names it; nothing else stores one. A group made on the page that holds no pattern yet is the page's own
  (`new_groups`) until a pattern is made in it, and is not in the set.
- **The rows.** Each row is a `Listed(kind, name)`: a group's heading, `- name (count)` open and `+ name (count)` closed, bold;
  the group's patterns, indented, sorted by `name_order`; and, ending each open group, the button `[ New Pattern ]`. The page
  ends with the button `[ New Pattern Group ]`. Both buttons are in the Patterns theme colour (`ListPage.row_style`) and carry no
  `+`. The patterns in no group, an older file's, come last under `Ungrouped`, shown only while any exist; nothing can be added
  there, and its heading only opens and closes.
- **The cursor** opens on the first pattern showing, so that ENTER edits at once. `current()` is the pattern's name, or nothing
  on a heading or a button, as a list answers on its `+` row; `listed()` says what the row is.
- **Closed groups** are saved with the set under `closed_pattern_groups` and are no part of the set's data
  (`Setlist._closed_groups`, outside `to_data`): opening or closing one is neither an unsaved change nor an undo step. A group
  no pattern is in is forgotten.
- **Keys.** On a pattern: ENTER edits, `G` (Group) opens a sorted picker of the groups ending with the new group entry, `A`
  adds to the pattern's group, `N`, `C`, `Bksp` and `L` as before; a copy stays in its source's group. On a heading: Space or
  ENTER opens and closes, `A` adds a pattern, `N` renames the group, `C` copies the group and `Bksp` asks and then takes every
  pattern out of the group, deleting none. PgUp and PgDn jump between headings.
- **Copying a group** opens a prompt titled "Confirm copying the entire pattern group" with the field "New Group Name:", opened
  on the group's name counted up. Each copy's name takes the new group's name at the front, in place of the old group's name
  where the name began with it and joined with an underscore otherwise (`name_in_copied_group`); a taken name counts up; a name
  over 30 characters refuses the whole copy with the reason; the copy is one undo step.
- **Search** looks at the patterns alone, inside closed groups too, and ENTER opens the found pattern's group. Pickers of
  patterns elsewhere stay flat.
- **A pattern made elsewhere** takes the group named after its track: the starter pattern of a new set, a blank pattern made on
  Arrange, the MIDI import and the song wizard (`Setlist.group_patterns_by_track`).
- The video tutorial builds each pattern in its target's group, or the group named after the first track that plays it, making
  the group first (`tutorial/plan.py`, `add_to_group`).

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
- An arp's offsets have their own editor (`.claude/tracker/PATTERN_EDITOR.md`, "The offsets editor").

## Grooves

- The Grooves page (`V`, `GroovesPage`) lists the factory grooves first, marked `factory`, with
  only `ENTER` (view) and `C` (copy) on them, and the set's own with the usual list keys.
- `A` adds `groove-1` and so on (`new_name` in `composition/naming.py`) and opens the `GrooveEditor`.
- The `GrooveEditor` is a one-row editor like the offsets editor (`.claude/tracker/PATTERN_EDITOR.md`, "The one-row editors"),
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
  leaving out any tracker's own FluidSynth port (`FLUIDSYNTH_PORT_PREFIX`). GM sound opens a `SoundDialog` (`tui/dialogs/sound_dialog.py`, the user's design) of `(none)` above General MIDI's
  families (`MSG_GM_FAMILIES`, `MSG_GM_SOUNDS`, `sound_families`), each a row that opens a flyout of its eight sounds; `/` searches every
  sound and ENTER there opens the flyout of the sound found, since letters are keys in this dialog; `L` tries the sound under the cursor
  through a `SoundTrial` (`tui/screens/shared/sound_trial.py`), which has the pattern preview play a run once through General MIDI in
  FluidSynth (`PatternPreview.play_sound`), or, where FluidSynth is not installed, on the song's Preview instrument, which is sent the
  notes and no sound of its own (the user's design); where neither can sound, the dialog says what to do in amber under its rows until
  the next key (`sound_refusal`, `ERR_NOTHING_TO_TRY_A_SOUND_WITH`); stopped by `L` again, a move of the cursor
  or closing
  , and `[` and `]` step it by number (`step_gm_sound`). An asker whose sound plays on one note passes `note=`, and the dialog keeps a Note row in view under its list: `[` and `]` step the note, a name such as C3 or f#2 typed and ENTER sets it (`tui/note_names.py`), ENTER with nothing typed takes the sound the dialog opened on, and the answer is the sound and the note.
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

## The song wizard

The user's design, agreed in detail in `.claude/features/WIZARD_DESIGNS.md` (S16 to S39), of which this is the part built.

- F5 opens `WizardPage` (`tui/screens/wizard/wizard_page.py`) from any page; F5 inside the wizard says the wizard is open.
  The page is a `FieldPage`: a tree of branches at the left, 24 cells wide, and at the right the fields of the branch under
  the tree's cursor, drawn by `FieldPage.body`, dim while the cursor is in the tree. Its stripe is bright cyan.
- The cursor is in the tree or in the fields (`in_fields`). In the tree Up and Down move, Left and Right close and open a
  branch that has branches under it, Left on a branch inside another going to the one that holds it, and ENTER or Tab moves
  into the fields, onto the first field that does something; a branch only to be read takes no cursor. In the fields the
  keys are a settings page's, and ESC or Tab moves back. ESC in the tree closes the wizard, asking first once anything was
  chosen (`choosing` wraps every setter and notes it).
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
  (`CompositionBranch`) holds no fields of its own: its branches are Chords (`ChordsBranch`, Progression, each progression shown with its numerals, `three chord (I IV I V)`, in the field and its list, and under the field the chords each kind of section plays, spelled in the song's key, or a line saying they are drawn when the song is made while the field reads "any"), Melody (`MelodyBranch`, "usual" or a melody style the subgenre can use, and the smart style's gauges) and Hooks (`HooksBranch`, the Hook switch where a hook changes the song), each a `SongWaysBranch`, and Composition lists what each is set to, leaving out one with nothing to choose; Playing has Fills, a fill chosen there being played whatever the drummer's Busy level would play (Feel is gone until a feel changes what is played: a style's feels were written into its drums and the field chose nothing; a melody style that sketches as "usual" does is not offered). Built so far: `GenreBranch` (Genre and Subgenre, each starting on `(choose)`, then Key, Scale and Tempo once
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
- When the current song was made by the wizard, F5 first asks how to start in a picker titled Song Wizard, the user's
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
  (`.claude/features/MACRO_COMPOSER.md`, "The Wizard's Choices"), one change and so one undo step, after which
  `LlamatronApp.show_arrange_on_new_song` closes down to the main screen and opens Arrange on the song.
- `tests/tui/test_tui_wizard.py` tests the page and undo, and the key tour and the fields tour both visit it.
