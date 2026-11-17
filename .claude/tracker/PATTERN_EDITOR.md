# The Pattern Editor

Reference notes for Claude, one part of `.claude/tracker/`: the Patterns page, the pattern editor's rows, the piano roll, keyswitches and the one-row editors. `CLAUDE.md` says which part to read for which work.

## Patterns

- The Patterns page's `A` offers `pattern-2`, `pattern-3` and so on (`new_name`), the way
  new tracks and scenes are numbered.

## The pattern editor

`PatternEditor` (`tui/screens/pattern/pattern_editor.py`) shows one of two views of a pattern, the piano
roll or the rows.

- Each view is a component with its own cursor, its own keys and its drawing: `PianoRoll`
  (`tui/components/piano_roll.py`, drawn by `RollDrawing`) and `PatternRows`
  (`tui/components/pattern_rows.py`, drawn by `PatternDrawing`), kept as `editor.roll` and
  `editor.rows_view`.
- `editor.view()` returns the one showing, and `keys()` and `body()` ask it, so nothing else
  asks which is showing. Both views answer `move_keys()`, `keys()`, `other_view_binding()` (the
  editor's binding for Tab from here, whose words `other_view_what()` gives),
  `step_keys(can_remove=)` (the view's `I` and `D`), `lists_step_keys()` (whether the legend shows
  them) and
  `takes_note_letters()` (true on a drum pattern's Note row, where `D` is a note), and each has a
  `drawing`.
- Tab (`PatternEditor.TO_ROLL` and `TO_EDITOR` in `tui/keybindings.py`, `toggle_roll`) switches, legend `to piano roll` or `to editor`. The
  choice is kept for the session on the app as `on_roll`, the roll to start with. A drum pattern
  has no roll (`has_roll`) and no Tab, and opens on the rows.
- The editor keeps what the views share: the cursor's step (`step`, `first_step`,
  `jump_end`), the value under the cursor (`value`, `set_value`, `is_note`), the digits typed so
  far (`typed`, `typed_number`), and the edits to the whole pattern. The step, the window of
  steps and the typed digits are `StepEditor`'s ("The one-row editors" below), which the
  pattern editor inherits. `editor.row_for(name)` and
  `editor.row_name()` forward to the rows view, for the row components.
- The editor's crumbs say where ESC goes back to. Opened from the Patterns page they are
  `PATTERNS › tune`, the mixin's own. Opened from a clip with `P`, `PatternEditor(holder=,
  name=, opened_from=)` keeps the page that opened it and `crumb_trail` puts that page's crumbs
  first and `MSG_PATTERN_CRUMB` last: `ARRANGE › pattern: tune`, or `ARRANGE › clip: (scene 1,
  lead) › pattern: tune` (the user's choice). The opener's crumbs are asked each
  time, so a scene renamed under the clip page renames the editor's crumbs too.
- `S` sizes the pattern (`keybindings.PatternEditor.RESIZE`). On the rows, `I` and `D` insert and remove a step.
- `R` (`keybindings.PatternEditor.RECONFIGURE`) opens the Reconfigure `ChoiceDialog` (`MSG_RECONFIGURE_TITLE`,
  `reconfigure_choices`, indexed by the `Reconfigure` class): munge, load over, step size, time
  signature, drum on or off, direction, rename.
- Munge opens a `ChoiceDialog` (`MSG_MUNGE_CHOICES`, indexed by the `Munge` class): reverse after
  the cursor, reverse before it, reverse all, pivot around it, or randomize, which shuffles the
  steps unseeded as an ordinary edit. Each is a `Pattern` method. The cursor stays on its step, so
  that choosing a reverse or the pivot again undoes it.
- Load over loads a copy of another pattern over this one. Drum on or off always asks first
  (`MSG_CHANGE_TYPE_EMPTY_QUESTION` when there are no notes to lose).
- Typing never moves the cursor or grows the grid. Digits build up a number in a cell until the
  cursor moves or a number would be out of range.

### What both views draw

- `GridDrawing` (`screens/pattern/grid_drawing.py`) is shared by `PatternDrawing`
  (`screens/pattern/pattern_drawing.py`) and `RollDrawing` (`screens/pattern/roll_drawing.py`): the header, the
  window of steps that scrolls sideways, the rules, the Step row and the description of the step
  under the cursor. Each drawing is built once by the editor and asked for its body.
- Both views share one label column, `PatternEditor.label_width`, the wider of the two drawings'
  `widest_label` (the rows', sized for every row there could be, and the roll's, worked out from
  the label's parts at their widest by `PianoRoll.widest_row_label`, since a row's label needs a
  note that exists), so that the step columns stay put when Tab switches views (the user's
  choice).
- The header's two lines are cells in aligned columns (`header_cells` in
  `screens/pattern/grid_drawing.py`): Steps, Step size, Drum and Direction on the first, and on the
  second Time and then what the view adds (`header_extra`, a list of cells: the scale and the
  entry size on the roll, the section's hint or the scale on the rows). Each column is as wide
  as its wider cell, and a line's last cell runs on, so the long hint widens nothing. The
  user's layout, where the lines were two strings with four spaces between the
  parts. `(song's)` marks a value the pattern takes from the song.
- A pattern wider than the screen scrolls sideways rather than wrapping. The editor's
  `first_step` is the window's first step, `scroll_to_cursor` moves it so the cursor's step is
  shown (`StepEditor.window_of_steps`), and the header's second line says `steps 1-11 ›`
  (`StepEditor.steps_shown_text`, `MSG_STEPS_SHOWN`). Home and End go to
  the ends (`jump_end`).
- The step numbers that start a beat are bold, and each such step's left edge is a bold double
  line (`Box.DOUBLE_BAR` and its tees, through single rules). The joints where the edge crosses a
  rule are plain, between the rule's dim and the edge's bold.
- The header's second line shows the time signature, which is set through `R`.
- Every cell keeps `CELL_WIDTH` whatever its value, so the grid never shifts.

### The rows view

- `PatternRows` holds the cursor's row (`row`, a place among `reachable()`), `first_row`,
  `gauge_rows` and the row objects, built once per name by `row_for(name)` from `ROW_CLASSES`.
- `PINNED_ROWS` (Degree, Octave, with a rule under Octave) come first and stay on screen while
  the rows beneath scroll (`pinned_rows()`, `scrolled_rows()`, `scrolled_row()`).
- The rows under the pinned ones come in sections (`SECTIONS`, keyed by `RowSection` in
  `tui/keys.py`): Basics (#/b, Chord, Inversion, Velocity), Timing (Tie, Gate, Dot, Glide), Advanced
  (Probability, Ratchet, Ratchet Offset, Grab), CCs (the CC rows and Slide), Reg. Mod (the `=` rows, `SetRow`,
  then `+=`, `AddRow`), Reg. Apply (`+Note` and `+Vel`) and Reg. Cond (`ConditionRow`), in the order a step
  works them out (the user's choice). `SetRow`'s number line starts at blank just below the current
  song's register Minimum; `AddRow` stops at `Document.allowed_inc_max` and says so; a condition is blocked on an empty step. A drum pattern leaves out the rows whose description says it has none (`is_in_drum_patterns()`).
- Each section is headed by a `SectionRow` (`tui/components/section_row.py`), labelled
  `+ Advanced` closed or `- Advanced` open (`MSG_SECTION_LABEL`, `MSG_SECTION_CLOSED_MARK`,
  `MSG_SECTION_OPEN_MARK`). The row has no cells, so the label is drawn in reverse video under
  the cursor (`marks_label`).
- Space or ENTER opens or closes a section (`toggle_section`), and PgUp and PgDn move between the
  headings (`jump_section`). The open sections are kept on the app as `open_sections`,
  `OPEN_AT_START` (Basics and Timing) to begin with.
- The label column is sized for every row, open or closed (`all_row_names`), so nothing moves
  when a section opens. The header's second line shows the cursor's section's hint
  (`MSG_SECTION_HINTS`) where one has something to say.
- A heading has a rule over and under it (`rule_before`, `rule_after`, two neighbouring rules
  drawn as one by `PatternDrawing.row_blocks`) and no dividers across it. The rule over it ends
  the dividers above in bottom tees, the rule under it starts the ones below in top tees, two
  headings share an unbroken rule, and a closed last heading sits on a plain bottom rule
  (`PatternDrawing.rule_between`, `GridDrawing.closing_rule`, `opening_rule`, `plain_rule`).
- `PatternDrawing.fit_gauge` sizes the Degree gauge against the whole screen
  (`Page.screen_height`, less `Page.header_lines()`, `LINES_UNDER_BODY`, `LEGEND_LINES` and the fixed lines), so that
  the gauge keeps one height as the cursor moves between rows whose legends differ, leaving room
  for the tallest scrolled row.
- `scrolled_rows_shown` moves `first_row` so that the cursor's row is shown, counting the
  window's rows with `window_height`, which leaves out the rule a heading would draw against the
  pinned rows' rule or the bottom rule. On a tall terminal nothing scrolls.

### The row components

- `PatternRow` (`pattern_row.py`) is the base. `described()` is the row's one description in the
  model (`ROW_DESCRIPTIONS` in `composition/row_descriptions.py`, `.claude/format/FILE_RULES.md`,
  "Patterns"), which gives `NumberRow` its limits, what a blank step plays as and whether a
  blank shows a dot, `OctaveRow` its limits, `CycleRow` its choices and `GateRow` its longest
  gate, so no row component holds a range or a list of values of its own. Each row says what
  its cells show (`cell_text`), which keys work on it (`keys`, listed only when the row is
  `editable()` on the cursor's step) and whether a rest can hold a value on it (`on_rests`).
- The rows: `DegreeRow`, `GateRow`, `DotRow` and `AccidentalRow` (both `CycleRow`s),
  `OctaveRow`, `ChordRow` (which holds `CHORD_GROUPS`), `NumberRow`, `ControlRow` (a number a
  rest can hold), `CcRow`, `ToggleRow`, `GrabRow`, `GlideRow`, `SlideRow`, `TieRow` and
  `RegisterRow`.
- `[` and `]` are two legend entries on every row, `[` dec and `]` inc (`PatternRow.LESS` and
  `MORE`, `PatternRow.adjust_keys`, each calling the row's `nudge` with its direction), with
  `-`, `+` and `=` still working, the user's choice over one entry `[/]` adjust,
  which read as a slash key. On a `CycleRow` (Dot, #/b and the register rows) `nudge` goes
  round the cycle, and Space or ENTER (`CycleRow.NEXT`, `TOGGLE_KEYS`) goes to the next
  choice. `ChordRow` is the one row where ENTER can't cycle, since ENTER opens the picker, so
  Space alone is its `NEXT`.
- `RegisterRow`, the `+Note` and `+Vel` rows, is a `CycleRow` of three: add (`+`), subtract
  (`-`) and off (blank), on any step. A cycle starts from the row's blank, which
  `CycleRow.choices` takes from the description, since these rows' blank is 0 where Dot's is
  None.
- Space and ENTER are one legend entry on every toggle (`TOGGLE_KEYS`,
  `KeyName.SPACE_ENTER`): `ToggleRow`, a `FieldPage`'s `Toggle` fields and the offsets
  editor's silent step.
- A row can be more than one line tall: `labels()` gives a label per line, `cell_lines(step=)` a
  step's text per line, `cursor_line()` the line the cursor's reverse video sits on (the last),
  `rule_after()` whether a rule follows the row, and `edge_text(step=)` what replaces the divider
  at a step's left edge, so that a bar can run through it.
- A toggle that's on shows `MSG_TOGGLE_ON` (`●`), never a letter or `*`.
- A cell that can't take a value, which the render would ignore, shows `MSG_BLOCKED_CELL` (`/`)
  dim (`PatternRow.blocked`, which `editable` and `cell_lines` read): an empty step on a row a
  rest can't hold, or Tie on a note's step. Chord is open on a grab step, since the chord is
  built on the grabbed note. The cursor can sit there, with
  the row's keys off the legend.
- CC rows, Slide and every register row (`RegisterRow` for the uses, `ControlRow` for the
  changes) can be set on a rest. No register setting is ever locked out for want of a note.
- `TieRow` marks a tied step with `MSG_TOGGLE_ON` and shows nothing on a note's own step, which
  is blocked. `Pattern.clear_sound` clears the ties that followed the note too.
- `GlideRow` is a plain toggle, drawn with the dot like Tie. `AccidentalRow` shows `#`, `b`
  or nothing.
- `CcRow` is one line of numbers whose label says the lane's CC number on the tracks playing the
  pattern (`Document.cc_numbers_for_pattern`, `MSG_CC_ROW_LABEL`, `MSG_CC_LANE_OFF`,
  `MSG_CC_LANE_VARIES`).
- `GrabRow` works on every step, giving an empty step the root as its own note.
- Velocity and Probability stay numbers.
- `]` on the Chord row follows `CHORD_SYMBOLS`. `pick_chord` in `components/chord_row.py` opens the Chord dialog
  (`tui/dialogs/chord_dialog.py`, `ChordDialog`, the user's design), shared with the roll and with a progression's chord
  editor: four lists in the user's order, quality, inversion (None for root position, then the inversions the page stores), tensions and the borrowed scale type, Tab or Left and Right from
  list to list, Space toggling a tension, the scale list holding the categories of `tui/scale_categories.py` (Common first,
  then every scale type once), each opening a flyout, a box of the dialog's size stacked over it, with Space or ENTER, where ENTER picks and
  goes on to the qualities and ESC or Left closes (a flyout is drawn by the dialog, never a second dialog, the user's rule), and under them what `ChordInWords` (`tui/chord_text.py`) says of the choice, its name in its scale, its
  name in the clip's own scale when it borrows, and its notes. It answers a `ChordChoice`, stored on the step's Chord, Inversion, Tension
  and Scale rows together, one undo step. `TensionRow` and `ChordScaleRow` are `ChordRow`s with their own choices, in the
  Chord section (`RowSection.CHORD`, the user's design and order: Chord, Tension, Scale and Inversion together, closed at the start
  so that every heading still fits an 80 by 24 console, and left out of a drum pattern, which has none of its rows); the
  Scale row steps through `SCALE_TYPES_IN_ORDER`, every scale type in the categories' order. While the dialog is open the
  pattern editor shows the chord as the choice moves (the dialog's `moved`): the step is written without an undo step and
  written back on ESC, so the whole is one step or none. The pencil on the step where a chord starts, at another pitch, moves the chord's root and keeps the rest of the step
  (`Pattern.starts_chord`, `move_root`, the user's rule); erasing the note is what removes its chord. A note whose chord has an inversion is drawn hollow (`MSG_NOTE_HOLLOW`, `PianoRoll.root_is_lifted`, the user's design), since the
  root sounds an octave up and nothing sounds where the note is written. The roll's thin lines are green (`Style.CHORD_NOTE`) and include
  tensions and a borrowed scale's notes (`_tones_leaving_the_scale` in `composition/pattern_notes.py`); a Tension cell is blocked on a step with no chord. `Page.resting_status()` is what the status line says
  while nothing else is said: the pattern editor and the chord editor name the cursor's chord there, in the scale known
  (`PatternEditor.known_scale`, the first of the pattern's uses' scales).
- The chord editor (`ChordsEditor`) has six rows, in the user's order: Chord with its root's `#/b`, then Quality, Tens., Scale
  and Inv. Its Degree gauge is drawn two degrees a line with a half block, so that the page still fits 24 lines.
- Drum patterns keep note letters and no gauge. Both `D` and `F` are note letters on a drum
  pattern's Note row.

### The Degree gauge

- The Degree row (`DegreeRow`) is a vertical gauge: one `MSG_GAUGE_BAR` (`███`) per row from the
  bottom up to the step's degree.
- When the pattern's uses agree on one scale (`Document.scales_of_pattern`, `pattern_scale`,
  through `Setlist.scales_for_pattern`; a pattern used nowhere takes the current song's), the
  gauge has one row per note of the scale, labelled with the scale's notes from the root
  (`NamedScale.get_note_names`, `note_names` in `composition/named_scale.py`).
- Otherwise it has `GAUGE_ROWS_WITHOUT_SCALE` (7) numbered rows.
- The header's second line says the scale, or `MSG_SEVERAL_SCALES`, or `MSG_NO_SCALE_NEEDED` for
  drums (`PatternDrawing.scale_header`).
- The number sits under the bars, where the cursor is, since reverse video on a solid block is
  blank, and a rule follows it.
- When the scale is known, a degree past its size is shown as the degree within the scale with
  Octave one higher (`shown_degree`, `octave_shift`, which `OctaveRow` reads). `]` at the top and
  `[` at the bottom stop there and say `ERR_TOP_OF_SCALE` or `ERR_BOTTOM_OF_SCALE` on the status
  line (`nudge`). Nudging writes a file's degree back within the scale with Octave moved up to
  match.
- When the scale isn't known, any degree up to `Document.degree_limit` can be typed, and one
  above the rows fills the gauge and marks its number with `MSG_OVER_THE_TOP_MARK` (`▲`).

## The piano roll

`PianoRoll` holds the cursor's pitch and the roll's keys and knows nothing of Textual, and
`RollDrawing` draws it. `tests/tui/test_tui_piano_roll.py` tests it.

### Pitches and rows

- A pitch is counted from the bottom in half steps when the pattern's uses agree on one scale
  (`Document.pattern_scale`, `per_octave`, `scale_steps` from `NamedScale.get_half_steps`), so
  that a sharp or flat has a pitch between two degrees (`pitch_of`, `note_at`, `is_degree`).
- Otherwise a pitch is one per row, with room for the largest scale the pattern can play in
  (`Document.degree_limit`, at least `GAUGE_ROWS_WITHOUT_SCALE`), and the rows are labelled by
  octave and degree alone (`MSG_ROLL_OCTAVE_ONLY`).
- The rows drawn (`PianoRoll.rows`) are every degree of every octave and, between two degrees, a
  row for each pitch that a note or a chord's note of the pattern falls on. Such a row exists
  only while something is on it, so a pattern that stays in its scale looks like a scale.
- The cursor moves by rows (`move`, `snapped`) and follows a note that `.` moves
  (`cycle_accidental`), so it can only reach a pitch outside the scale that a note already has.
- A row between two degrees is labelled with the note alone, dim, spelled with sharps unless the
  scale's root has a flat (`Document.scale_note_at`, `scale_spells_flats`). `Space` on it writes
  the degree below with a sharp or the degree above with a flat (`Document.place_note` with
  `accidental`).
- Rows run from the highest pitch down, labelled `MSG_ROLL_ROW_LABEL` with the note, its octave
  in the set's octave labels (`NamedScale.octave_of_degree`, since a scale's upper degrees cross
  into the next octave) and the degree. `inner_rule` is drawn where each octave starts, and a
  double rule under the step numbers (`heading_rule`).
- The cursor opens on the first note, or the root in the song's default octave (`place_cursor`).
  The window of rows (`top_pitch`, `pitches_shown`) centres on it the first time and then keeps
  it on screen.
- Rows outside the octaves of the one track that plays the pattern
  (`Document.pattern_octave_range`) are dim with `MSG_OUT_OF_RANGE_CELL`.
- The header's second line names the scale and the entry size (`MSG_ENTRY_SIZE_SHOWN`,
  `Document.entry_size`), as cells under Step size and Drum.

### How notes and the cursor are drawn

- A note is drawn over the steps it covers (`Document.covering_notes`, from `Pattern.covering_notes`
  and `note_span`: its
  ties, or its gate rounded up to whole steps, and any ties right after that, cut where a later
  note starts) as `MSG_NOTE_CELL` bars, with `MSG_NOTE_EDGE` in place of the dividers it crosses.
- A gate that ends inside a step fills only part of the note's last cell
  (`Pattern.partial_cell`, `filled_columns`, never none or all of `CELL_WIDTH`, built from
  `MSG_NOTE_EDGE` or `MSG_CURSOR_BLOCK`), so the bar ends where the sound does.
- The cursor's cell stands between two bold double bars (`RollDrawing.cursor_edges`, drawn by
  `pitch_line` in place of the step's edges unless a note's bar runs through). The cell is
  `MSG_NOTE_UNDER_CURSOR` on a note and a reversed blank on an empty cell.
- Where the cursor's row lies against a rule (the heading rule, an octave divider or the bottom
  rule), the piece of the rule under or over the cell is a bold double rule with double-armed
  joints (`╬═════╬`, or `╩═════╩` on the bottom rule and `╣` at the right border), so that the
  cell is boxed on that side too (`GridDrawing.rule`'s `boxed`, `boxed_tee` and `boxed_right`,
  through `RollDrawing.boxed_beside`).
- A note's mark is drawn in reverse video at `MARK_COLUMN` of its first cell, or the bar's last
  column when the bar is shorter (`RollDrawing.note_cell`): `G` for a grab
  (`MSG_GRAB_NOTE_MARK`), or its sharp or flat, only on the numbered rows of a pattern with no
  one scale.
- A chord's other notes are ghosts, thin dim lines `─────` on their rows as long as the note
  (`MSG_GHOST_LINE`, `RollDrawing.ghost_cell`, `ghosts_of`), which can't be edited on their own.
  A note that grabs has no ghosts (`PianoRoll.ghost_pitches`): the chord is built on whatever
  note the grab takes, which the roll can't know, so the `G` is all the roll shows, and the
  description of the step under the cursor (`GridDrawing.describe`) calls the sound `the
  grabbed note` (`MSG_GRABBED_SOUND`) and names no note, on the roll and the rows alike. The
  user chose that, since a pattern is played in many places and generators and registers move
  what is grabbed.
  `Pattern.chord_tones` gives a scale chord's tones as degrees above the step's, and a named
  chord's through `NamedScale.degree_above`, which places half steps in the pattern's one scale as
  a degree with a sharp or a flat, or none when the pattern plays under several scales.
  `PianoRoll.ghost_pitches` turns them into rows.

### The roll's keys

The roll is one pencil: every key does one thing, and nothing has a mode. Space is the one key
that does what is meant by where the cursor is: draw on an empty cell, erase on a note. The keys are the
bindings of `keybindings.PianoRoll`. Each key that needs a note under the cursor is written under `@on_a_note`
(`components/piano_roll.py`), which finds the note (`note_here`), hands the key the step the note
starts on, and says so on the status line when there's none. The knife has its own sentence for
an empty cell and isn't marked.

- The arrows move by step and pitch, stopping at every edge (`cursor_moved`), and Home and End go
  to the ends. There is no octave jump and no bar jump.
- `Space` or `ENTER` (`keybindings.PianoRoll.PLACE`, `TOGGLE_KEYS`) draws a note of the entry
  size (`Document.place_note`, through `Pattern.draw_note`,
  which `Pattern.place_note` writes as a degree, an octave and ties, or a gate for an entry size
  shorter than a step, clearing each step it covers). On a note already at the cursor's pitch, from any of the note's cells, it erases the
  note as `Bksp` does (`PianoRoll.place_or_erase`), so Space turns a note on and off; a note drawn
  again is a new one of the entry size. It cuts a note at another pitch where the new one starts and leaves
  the rest as a note of its own (`Pattern.place_note` splits the tie after the new note first,
  `Pattern.split_note`), and cuts a gate that reached over the step to end there
  (`Pattern.cut_gate_before`).
- `[` and `]` (`keybindings.PianoRoll.SHORTER` and `LONGER`, the legend's `[` shrink and `]`
  stretch, the user's words for a note) drag the note's end a step earlier or
  later (`drag`,
  called with the direction, `Pattern.lengthen_note`, which makes a note shorter than
  a step a whole one first, and `shorten_note`, which stops at one step, `ERR_NOTE_IS_ONE_STEP`,
  and at the next note, `ERR_NO_ROOM_AFTER`). A key that could do nothing changes nothing, so it
  is no undo step and leaves the unsaved mark alone.
- `K` (Keyswitch) opens the keyswitch dialog for the note on the cursor's step, whatever the cursor's row, and refuses a
  step no note covers with `ERR_NO_NOTE_ON_STEP`, drawing nothing ("Keyswitches" below).
- `X` (Split) is the knife, the user's choice of the letter people know for cutting (`Pattern.split_note`, giving the step the note's pitch, chord and velocity,
  `SPLIT_ROWS`, and clearing its tie).
- `.` cycles the accidental (`ACCIDENTAL_CYCLE`), and the cursor follows the note to its new row.
- `Bksp` erases the note with its ties (`clear_sound`), and leaves what a rest can hold on the
  step: CC values, Slide and every register row, `+Note` and `+Vel` among them, which the
  rows' descriptions say (`is_kept_by_a_rest`).
- `G` marks the note to grab or unmarks it (`toggle_grab`).
- The Chord dialog's keyboard: `pick_chord` gives the dialog `keyboard=`, `step_keyboard(editor=, step=, choice=)` in
  `components/chord_row.py`, which answers None unless `document.scales_of_pattern` has exactly one scale and the step has a degree,
  and otherwise the lines of a `Keyboard` (`components/keyboard.py`) given `chord=chord_keys(note_names=, inversion=)`, the chord's
  keys from its root up, an inversion's lowest notes an octave higher; `Keyboard.rows()` gives each line as pieces with a `KeyKind`,
  drawn in `KEY_STYLES`. `ChordDialog.sentences_and_keyboard` draws it one blank line under the last sentence when
  `has_room_for_keyboard`, the dialog keeping its height. The progression editor's Chord dialog has none yet.
- `H` (`keybindings.PianoRoll.CHORD`, `pick_chord`) opens the Chord dialog, with `(single note)`
  at the top, on the note under the cursor from any of its cells. ENTER drew nothing and picked
  the chord until the user made ENTER do what Space does, as everywhere else,
  and the picker took the free letter. It refuses an empty cell
  (`ERR_NO_NOTE_HERE`), and takes a note that grabs like any other.
- `E` (`keybindings.PianoRoll.ENTRY_SIZE`, `pick_entry_size`) opens a `ChoiceDialog` of the pattern's entry
  size: the song's first (`MSG_SONG_ENTRY_SIZE_CHOICE`) and then `STEP_SIZE_CHOICES`, opening on
  what the pattern has now (`Document.written_entry_size`).
- The whole-pattern keys `S` and `R` stay. The roll neither inserts nor removes a step, the user's rule, as Live's
  piano roll never did; the rows view does both. `X` and `G` are listed by F1 alone, so that the roll's legend keeps to drawing.

## Keyswitches

The user's design, mockup by mockup; `.claude/format/FILE_RULES.md`, "Instruments", says what is stored and how keyswitches play.

- **The Keyswitch Map** (`tui/dialogs/keyswitch_map_dialog.py`, `KeyswitchMapDialog`), opened from the Instrument Editor by the
  Keyswitch Map button or `K` (Keyswitch Map) from any field: ten rows, a slot's number, name and note, the note in the set's
  octave labels with its MIDI number, `C0 (24)` (`tui/keyswitch_text.py`). `N` or F2 (Rename) prompts for the name, an empty one
  leaving none; the cursor is on a slot's name, where it starts and ENTER renames (`RENAME_HERE`), or with Right on
  its note, the triangle before the one it is on in a place each keeps so that nothing shifts, Up and Down keeping the cell
  (`NAME_CELL`, `NOTE_CELL`, the user's design; the slot's number is only text at the left); on the note ENTER (Note) opens the note picker; `Bksp` (Clear) empties the slot. The dialog edits a copy: `O` (OK), or the
  OK button reached with Down from the last slot, stores the ten slots as one undo step (`Document.set_instrument_keyswitches`),
  and ESC or the CANCEL button changes nothing (Claude's choices, since ENTER was given to the note picker).
- **The note picker** is a flyout over the map: one octave of keys (`one_octave_rows` in `tui/components/keyboard.py`), Left and
  Right along the octave's keys, Up and Down an octave, every edge stopping, ENTER taking the note and ESC closing. It opens on
  the slot's note, else a half step above the map's highest note, else the lowest C, MIDI 0 (`first_note_offered`).
- **Keyswitch lead** is a number field of the Instrument Editor, in milliseconds.
- **The Keyswitch row** (`tui/components/keyswitch_row.py`, `KeyswitchRow`) is in Basics under Velocity: a blank cell for none,
  else how many slots are on, and the blocked slash on a step with no note. ENTER opens `KeyswitchDialog`
  (`tui/dialogs/keyswitch_dialog.py`, a `PickManyDialog`): Up and Down, Space toggling the cursor's slot, a digit toggling its
  slot and moving the cursor to it, one legend entry `0-9`, ENTER OK and ESC CANCEL as drawn buttons, one undo step. `Bksp`
  on the row clears the step's.
- **Names or numbers.** The dialog names the slots from one instrument when the editor was opened from a clip (Arrange and the
  clip page pass `track=`, `PatternEditor.opened_track`) or when every track playing the pattern in any song has the one
  instrument (`Document.instruments_of_pattern`, `PatternEditor.keyswitch_instrument`); otherwise the slots go by number with a
  line saying why. A slot with no note can be switched on.
- **The description line** under the grid ends with the cursor step's keyswitches, by name where known (`keyswitches_described`).
- **The roll's light**: `with_keyswitch_lights` in `tui/screens/pattern/roll_drawing.py` writes `◆` over the top pitch line
  (`TOP_PITCH_LINE`) in each such step's column, keeping the line's width.
- `tests/tui/test_tui_keyswitches.py` tests all of these.

## The one-row editors

- `StepEditor` (`screens/shared/step_editor.py`) is what every editor of steps shares, the pattern
  editor among them: the cursor's `step`, the window's `first_step`, the digits `typed` into
  the cursor's cell with `typed_number(digit=, low=, high=)`, which continues the edit so that
  two digits are one undo step, `keep_step()`, `window_of_steps(shown)`, which scrolls the
  window to the cursor, and `steps_shown_text(first=, last=)`. A page says how many steps
  there are with `steps()`.
- `OneRowEditor` (`screens/shared/one_row_editor.py`), a `StepEditor`, is the offsets editor and the
  groove editor: one row of numbers either side of zero. `OneRowEditor` holds `keys()`, `move`,
  `type_digit`, which keeps the sign, `nudge`, `insert`, `remove_step`, and the drawing both
  share (`steps_shown`, `scroll_to_cursor`, `grid_rule`, `grid_line`, `with_steps_shown`). A
  page names `CELL_WIDTH`, `MOST` (the largest number either side of zero), `MOST_STEPS`,
  `FEWEST_STEPS`, and `INSERT` and `REMOVE`, the page's own bindings for `I` and `D`, and says
  what the row is with `values()`, `set_value(value)`, `add_step()` and `drop_step()`, with
  `can_edit()` for a row that is only shown and `more_keys()` for keys beyond the row's own.
  `keybindings.OneRowEditor` holds Left and Right, Up and Down and the digits. A new one-row
  editor is those few answers and a `body`.
- `tests/tui/test_tui_step_editors.py` runs one set of checks on both one-row editors.

## The offsets editor

- An arp's offsets have their own editor (`screens/generators/offsets_editor.py`): a vertical offsets gauge
  of bars either side of a zero line, drawn from `SignedGauge` in
  `tui/components/signed_gauge.py`.
- `gauge_levels` gives as many levels as the screen has room for, up to `MAX_GAUGE_LEVELS` (7),
  and five on an 80 by 24 console, where the legend takes two lines.
- A value past the edge fills its column, and the Offset row marks it with
  `MSG_OVER_THE_TOP_MARK` or `MSG_UNDER_THE_BOTTOM_MARK` (`+7▲`, `-9▼`).
- The cursor's column is marked at both ends in reverse video (`MSG_CURSOR_STEP_MARKS`,
  `MSG_CURSOR_VALUE_MARKS`: `<<4>>` and `<+7▲>`).
- The row scrolls sideways (`first_step`, `scroll_to_cursor`), with the steps shown at the right
  of the note above the grid (`with_steps_shown`).
- Opening the editor gives a new arp its row of offsets, which is why an undo of that takes the
  page away.
- Tab (`OffsetsEditor.NEXT_ROW`) moves the cursor from the Offset row through a row per register,
  what each step adds (`set_arp_step_add`), and back; `OneRowEditor.most()` gives the edited row's
  limit, the register's Allowed Inc Max on an add row. Only the add rows in use, and the cursor's,
  are drawn (`shown_add_rows`), so the gauge keeps five levels on an 80 by 24 console when an arp
  adds nothing. The arp editor has AX+= per note to DX+= per note (`note_add_field`), and its
  Step starts at `(pattern)` (`STEP_CHOICES`).

- **Scale length** (the user's design). A pattern's `scale_length` (`PatternSetting.SCALE_LENGTH`, `Pattern.get_scale_length`,
  `set_scale_length`, `suits_scale_of`) says how many notes the scale has that it was written for, `MIN_SCALE_LENGTH` (5) to
  `MAX_SCALE_LENGTH` (12), or nothing, shown as "(any)", which an older file's pattern and every drum pattern have. It changes
  no note and nothing a render plays. `[ New Pattern ]` and `A` on the Patterns page open the `NewPatternDialog`
  (`tui/dialogs/new_pattern_dialog.py`): Scale length, stepped, starting at `NEW_PATTERN_SCALE_LENGTH` (7), where ENTER is OK,
  the Drum pattern toggle, which blocks the Scale length, and boxed OK and CANCEL; then the name's prompt. A blank pattern
  made on Arrange asks nothing: it takes its clip's scale's size (`Document.scale_length_for_pattern`) and is a drum pattern on
  a drum track. The Reconfigure dialog's `scale length` choice, its last and left out for a drum pattern until the pattern is made
  no drum pattern, opens a picker, "(any)" first and then 5 to 12. Where a scale the pattern plays under has another number of notes (`Document.scales_unsuited_to_pattern`), the
  header says so after the scale, `Scale A Minor Pentatonic, written for 7`. `tests/composition/test_scale_length.py` and
  `tests/tui/test_tui_new_pattern_dialog.py` test it.
