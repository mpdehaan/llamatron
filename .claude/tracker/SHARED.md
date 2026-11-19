# The Tracker's Shared Parts

Reference notes for Claude, one part of `.claude/tracker/`: where things are, how keys are bound, help, the main screen, dialogs, settings pages, files, the document, undo and redo, the status line and the header. `CLAUDE.md` says which part to read for which work.

Reference notes for Claude on the text UI in `src/llamatron/tui`, which is meant to become the only
way people use the program. One short section per page or topic, so that the part about one thing
can be found and read on its own. `.claude/UX.md` holds the rules for how the tracker behaves,
`.claude/STYLE.md` the rules for the code, `GUIDE.md` is the user's guide to the same pages, and
`.claude/format/` covers what the pages edit.
`tests/rules/test_doc_paths.py` checks that every source path named here exists, so paths move with the
code.

A page asks for one of some values with `Page.pick(title=, values=, then=, current=, shown=)`, which opens a picker on the current value and hands `then` the value chosen, never its place in the list. A yes-or-no question is `Page.confirm(title=, lines=, then=)`, and a question about deleting `Page.confirm_delete(lines=, then=)`; each runs `then` on yes alone. A line of text is asked for with `Page.ask_text(title=, then=, value=, is_name=)`, where `is_name` holds the text to a name's length. A new item's name comes from `Document.new_name(section=, word=)`, or `new_name(word)` on a page that lists a section. A page opens the editor of a named thing with `Page.open_editor(section=, name=, word=)`, which asks the program for the editor's class (`tui/screens/editors.py`), so that no page imports another's editor; `internal_tools/make_diagrams.py` reads those calls for the map of the screens.

## Where things are

`llamatron [set]` or `./llamatron.sh [set]` opens the tracker. It uses Textual with
`ansi_color=True`. One class per file in `screens/` and `dialogs/`.

- `tui/app.py`: `LlamatronApp`, which holds the document, the status line and what is kept for
  the session (`on_roll`, `open_sections`, `has_confirmed_overwrite`).
- `tui/document.py` and `tui/document_parts/`: the set being edited ("The document" below).
- `tui/history.py`: the undo history. `tui/lengths.py`: how long things last. `tui/uses.py`: what
  uses what, in the words a page shows. `tui/text.py`: text helpers pages share (`clock`, `sorted_names`),
  and `composition/naming.py` how a new thing is named (`words`, `new_name`, `unique_name`, `copy_name`, the one rule of `.claude/UX.md`, "Names the tracker makes",
  `is_default_scale_name`), which the MIDI import shares.
- `tui/keys.py`: every physical key's name. `tui/keybindings.py`: every key binding, one class
  for each page, dialog and component. `tui/key_table.py`: `KeyBinding`, `BindsKeys`, `bound()`,
  `cursor_moved()` and `pressed_key()`.
- `strings/help.py`: every page's help text, one `HELP_` constant each.
- `tui/drawing.py`: the styles, the box characters, the selected row's mark (`SELECTED_MARK`,
  `cursor_mark(selected)`), `Canvas` and the text-fitting helpers.
- `tui/status_line.py`: `StatusLine`.
- `tui/screens/`: every page, each a `Page` (`screens/shared/page.py`), a `ListPage`
  (`screens/shared/list_page.py`) or a `FieldPage` (`screens/shared/field_page.py`), with the helpers only one
  page uses beside it, what several share in `screens/shared/shared.py`, and the keys every page has in
  `screens/shared/everywhere.py`. `screens/pattern/grid_drawing.py`, `screens/pattern/pattern_drawing.py` and
  `screens/pattern/roll_drawing.py` draw the pattern editor, and `screens/arrange/arrange_drawing.py` draws
  Arrange.
- `tui/components/`: what pages are drawn from. One class per row of the pattern editor, the
  editor's two views (`PatternRows`, `PianoRoll`), `Frame`, `LengthBar`, `Keyboard` and
  `SignedGauge`. They draw with Rich text, know nothing of Textual and hold no data.
- `tui/dialogs/`: every dialog, each a `Dialog`.

## How keys are bound

- `tui/keys.py` names every physical key once, in `Key` (`Key.N` is the letter n and nothing
  else), with `Steps(back=, forward=)` for keys that step something one way or the other and the
  groups of keys bound together (`ARROWS`, `TOGGLE_KEYS`, `MORE_KEYS`, `LESS_KEYS`,
  `NUDGE_MORE_KEYS`, `NEXT_KEYS`, `SEARCH_CHARACTERS`, `CANCEL_KEYS`).
- `tui/keybindings.py` holds every binding and nothing else does: one class for each page, dialog
  and component that binds keys, with the same name and the same inheritance, so that
  `keybindings.PatternsPage` builds on `keybindings.ListPage`. A binding is a tuple of three
  things: the key or keys (a `Steps` for stepping keys), the name the legend shows (a `KeyName`
  from `strings/legends.py`) and what the keys do (a `What` or a `MSG_..._WHAT`). To change a key,
  change it there.
- Each class has two lists. `IN_HELP` is every binding of the class, in the order of the F1
  dialog, which is the order of the legend too. `IN_LEGEND` is the bindings the legend shows: one
  left out still works and is listed by F1 alone (Home and End, a list's `/`, and on the roll
  `X` and `G`). `Page.EVERYWHERE` is the keys every page has.
- Where one key means different things as the cursor moves, each meaning is a binding of its own
  and the page binds the one that applies: `ArrangePage.ADD_SCENE` and `ADD_TRACK`,
  `OffsetsEditor.SILENT` and `PLAY`, `SectionRow.OPEN` and `CLOSE`, `PatternEditor.TO_ROLL` and
  `TO_EDITOR`, and `ListPage.ADD_HERE` for ENTER on the `+` row. Two bindings of one class can
  hold the same keys and words, like `ArrangePage.MOVE` and `INSET_MOVE`, the arrows on the grid and in Scene View, so a binding is found
  in a list as the constant it is (`place_of` in `tui/key_table.py`), never by what it holds.
- A class that binds keys inherits `BindsKeys` (`tui/key_table.py`) and declares
  `KEYS = keybindings.<its own name>`. Each screen lists its keys once, in `keys()`, with
  `self.bind(self.KEYS.RENAME, action=self.rename)`, which returns a `KeyBinding` that both
  handles and draws the key. `bind` takes `wants_key=True` for a key that types its own character
  (digits, note letters, search text) or an arrow that moves a cursor, whose action is passed the
  key's name, and three overrides for what depends on the set: `keys=` and `name=` (the Degree
  row binds the digits of its scale's degrees, and the Octave row names its range) and `what=` (a
  settings page says what ENTER and Bksp do on the field under the cursor).
- An action bound to a `Steps` is called with `STEP_BACK` (-1) or `STEP_FORWARD` (1), never the
  key: the groove and offsets editors' nudge, Move mode's carries (`ListPage.carry`, calling `page.shift`, and Arrange's `carry`), `PianoRoll.drag`, `PatternEditor.jump_end`, `PatternRows.jump_section`,
  `GridChoiceDialog.turn_key` and `NotesPage.scroll`.
- `Page.key_table()` is `everywhere_keys(page)` joined to `page_key_table()`, which is
  `self.in_order(self.keys())`: the class's own bindings in the order of its `IN_HELP`. A page
  made of parts lists its parts' keys among its own, each part already in its own class's order,
  and `BindsKeys.in_order` leaves those where they are. The pattern editor lists ESC, the view's
  `move_keys()`, Tab, the view's `step_keys(can_remove=)` (`I` and `D` on the rows, none on the roll,
  which neither inserts nor removes a step, the user's rule, as Live's piano roll never did), `S`, `R` and then the view's `keys()`,
  which on the rows are the keys of the cursor's row.
- `Page.on_key` finds the binding that has the pressed key and calls `binding.press(name)`, then
  `document().record_edit()`, then draws. `Dialog.on_key` and `PromptDialog.on_key` call
  `press(name)` the same way. `Page.shown_keys()` is what the legend draws.
- `cursor_moved(place=, name=, count=)` is the one place an arrow moves a cursor: back for Up and
  Left, forward for Down and Right, stopping at both ends. `pressed_key(event)` reads a key press
  as one name: upper and lower case are the same, and so are both deletes.
- `Page.takes_text()` and `Dialog.takes_text()` say whether typed characters go into text rather
  than acting as keys: true while a `ListPage` is `searching`, while `NotesPage` edits its
  text, in a `PromptDialog` and in a `ChoiceDialog`, false in a `GridChoiceDialog`. The tests'
  `type(text)` asks first.
- Legends keep one order: ESC first, then the arrows, then the keys the page has in all of its
  modes, then the rest, which is the order of each class's `IN_HELP`.
- The rules are kept by `tests/rules/test_keybindings.py` (every class that binds keys has the bindings
  class of its name, inheriting the same way; every binding is keys, a name and words, is listed
  and is bound somewhere; every `Key` is bound or in the test's `NEVER_BOUND`; every `KeyName`
  names a binding) and by the tour in `tests/tui/test_tui_help_keys.py` (every bound key is one of its
  own class's bindings, and no key reaches two bindings in one place). `internal_tools/show_keys.py`
  (`internal_tools/keys.sh`) prints every class's bindings, one class's, or every binding that has a key.

## The keys that work everywhere

- `everywhere_keys(page)` in `tui/screens/shared/everywhere.py` returns Ctrl+S (save), Ctrl+O (open,
  which shows `OpenPage` and comes back to the page it was pressed on), Ctrl+X (export), Ctrl+T
  (silence, `Page.SILENCE`, the emergency stop of real-time playback, `.claude/features/REALTIME_PLAYBACK.md`), F5 (the song wizard, `LlamatronApp.show_wizard`), Ctrl+Z, Ctrl+Y, F1 (help) and F3 (about), in that order (`Page.EVERYWHERE` in
  `tui/keybindings.py`).
- The footer draws only `Page.shown_keys()`, the page's own keys. The main screen has cells for
  Save, Open and Export, the last two bound to `O` and `X` there (`MainPage.OPEN_SET_HERE`,
  `EXPORT_HERE`, doing what Ctrl+O and Ctrl+X do), and F1 and F3 in its footer (`MSG_HELP_FOOTER_WHAT`,
  `MSG_ABOUT_FOOTER_WHAT`, lower case where the F1 dialog's `What.SAVE` and `What.OPEN_SET` are
  capitals). No other page reminds anyone of F1 and F3.
- Quit is `Q` on the main screen alone (`keybindings.MainPage.QUIT`, in
  `MainPage.page_key_table`). The app is
  built with `inherit_bindings=False` so that Textual's own Ctrl+Q does nothing. Quitting quits at
  once with nothing unsaved, and otherwise asks with a `ChoiceDialog` of `MSG_QUIT_CHOICES`, quit
  without saving first and as the default.
- ESC goes back on every page and cancels every dialog. Tab never goes back: it switches the
  pattern editor's view, turns a `GridChoiceDialog`'s pages, completes in the pickers and the list
  search, and reaches the Notes page's buttons.

## Help and About

- `HelpDialog` (`tui/dialogs/help_dialog.py`, `Page.show_help`) shows the everywhere keys, a blank
  line and the page's own keys in two columns (`key_columns`). Tab, Left and Right turn to the
  panel with the page's `HELP` text (`MSG_HELP_PANELS`). ENTER, ESC or F1 again closes it, and
  `Page.show_help` leaves F1 out of the everywhere keys it lists, so that the seven left fill two
  columns downwards over four lines, Silence last in the first column, with Undo still above
  Redo in the second, the user's choice.
- Each page names its `HELP_` constant from `strings/help.py` as `HELP`. `tests/tui/test_tui_help_keys.py`
  checks that every key a help text names is bound on that page, and `tests/tui/test_tui_help.py`
  that the help fits an 80 by 24 console.
- `AboutDialog` (`tui/dialogs/about_dialog.py`, `Page.show_about`) draws the cowsay cow in code
  (`cow_saying`), `VERSION`, `BUILD_DATE` and `BUILD_TIME` from `support/version.py`, the links, a
  quote and the license with `build_year()`.
- The quote is drawn by `random_quote` from `MSG_ABOUT_QUOTES`, or is the eight ball's answer a
  third of the time (`EIGHT_BALL_CHANCE`), with Python's own `random`. It has a blank line above
  and below and wraps onto up to `QUOTE_LINES` (4) lines. The blank below gives way at two lines
  and the one above at three, so that the dialog stays on an 80 by 24 console.

## The main screen

- `MainPage` is one block of buttons drawn on `Canvas` lines, the user's layout, `GRID_WIDTH` (80) wide on every console and at
  the top left, never stretched to the window: `rows()` is the geometry, six rows of three, Arrange across the first row, then
  Songs, Patterns and Scales, Generators, Chains and Grooves, Instruments, Registers and the Real Time switch, then the bar's two
  rows, Open, Import and File/Global over Save, Export and Quit. `body()` draws Arrange as a regular button as wide as the grid
  (`draw_cell`), the three rows of buttons, `LINES_ABOVE_BAR` blank lines and the bar (`draw_bar`), whose keys start under the keys
  of the buttons above, each column's names starting at one place, past its longest key. `menu_items()` is each cell once. The
  cursor is `chosen`, its cell's binding, with `position`, the row and column inside a cell that covers several.
  `moved(rows=, position=, key=)`, a function of the geometry alone, steps by `ARROW_STEPS` until the cell changes or an edge stops
  it; a cell entered across the way it stretches keeps where, so that Down from Arrange goes back to the button the cursor came up
  from. `arrows_between(rows=, position=, binding=)` finds the fewest arrows to a cell, which the video tutorial's `select_cell`
  presses through `arrows_to(binding)`. `column_widths()` shares the grid's width between the three columns. `time_text()` shows
  `Page.playing_clock()`, the play mark and the clock beside the song's length, while the song plays, as Arrange's header does;
  the app's playback timer redraws it. `caption()` is empty, so the theme's stripe says nothing, and `resting_status()` is the
  page's own nothing, so the status line shows only what is said or refused. With a set open the cursor starts on Arrange.
- A cell is named by `cell_name(item)`: the page its key opens, which is the binding's words (a
  `PageName` from `strings/labels.py`), or the action's name (`ACTION_NAMES`).
- `draw_cell` draws the key bold and reversed, the name, and the count right-aligned, and a box around
  every cell: its page's theme colour toned to one brightness (`themes.balanced`, `EDGE_LUMINANCE`, `edge_style`, the user's ask
  that no colour look stronger than another), dim for a cell with no theme, and double-lined and bold around the selected cell.
- `count(item)` is the set's songs, patterns, chains, generators (both kinds), scales or own
  grooves (`COUNTED_SECTIONS`, `Setlist.get_own_groove_names`), and `None` for File, Registers,
  Arrange and the actions.
- Nothing sits between the rule and the cells: the crumbs name the set and the song, and the
  cells count what the set holds. The user dropped the set-and-song line and the song summary
  (tempo, scale, tracks, scenes), and later the details inside Arrange's cell and the description of the selected cell.
- Started with no set named, the tracker opens with the cursor on Open (`LlamatronApp(cursor_on_open=)`, which
  `main` passes when the command line names no file, `MainPage.select_open`), the user's ask.
- The cursor (`place`, `menu_items()`, `row_and_column`, `move_cursor`, `open_selected`) moves
  with all four arrows: Left and Right along the cells from row to row, Up and Down between rows
  keeping the column where the row has one, none going past an edge. ENTER follows. The cursor
  keeps its place while a page is open over it.

## Dialogs, pickers and searching

- `ConfirmDialog` draws Yes and No as buttons (`MSG_CONFIRM_BUTTONS`, `choice`), moved by Left and
  Right and pressed by ENTER, with `Y` and `N` still answering.
- `PromptDialog` keeps a cursor that Left and Right move, so text is inserted and erased where the
  cursor is.
- `ChoiceDialog` searches as you type (`SEARCH_CHARACTERS`): `typed`, `matches()` through
  `places_matching`, `completed` for Tab. `place` is always a place in the whole list, so that the
  answer doesn't change.
- `GridChoiceDialog` (`tui/dialogs/grid_choice_dialog.py`) is for pickers with many short
  options, laid out by `CHORD_GROUPS` in `tui/components/chord_row.py` and by `SCALE_PAGES` and
  `ROOT_KEYBOARD` on the Scale page. A grid can have pages, named on its top line, which Tab and
  Shift+Tab turn. It keeps its own keys and doesn't search.
- `ListPage` searches with `/` (`keybindings.ListPage.SEARCH`): `searching`, `typed`, `place_before_search`,
  `search_keys()` in place of the page's own keys while searching, and the same two helpers from
  `choice_dialog.py`. The status line shows `/text` (`MSG_SEARCH_STATUS`).
- Every list a page can add to has a `+` row at the bottom, where ENTER does the same as `A`
  (`keybindings.ListPage.ADD` and `ADD_HERE`, as `ArrangePage.ADD_SCENE` and `ADD_TRACK` have
  their `_HERE` bindings on Arrange).
- On settings pages `[` and `]` change a value and are what the legend names
  (`FieldPage.LESS` and `MORE`, `KeyName.LEFT_BRACKET` and `RIGHT_BRACKET`, `[` dec and `]`
  inc as everywhere), with Left and Right and the rest of `LESS_KEYS` and
  `MORE_KEYS` doing the same off the legend.
- Deleting anything still used is refused with up to five uses listed, and otherwise confirms.
- The pages that list the named things of one section, Patterns, Scales, Chains, Grooves, Songs
  and the two generator pages, are each a `NamedListPage` (`screens/shared/named_list_page.py`), which
  holds `rename`, `copy`, `delete`, `shift` and `sort` once, each calling the document's edit
  that takes the section (`rename_named` and the rest). A page names its `LISTED_SECTION`, its
  `RENAME_PROMPT` and its `WHAT` (the words for one thing in a question), and says what ENTER
  opens with `open_item`. `S` sorts on every one of them, the Grooves page sorting the set's own
  grooves under the factory ones. `LISTED_SECTION` is not `SECTION`, which is the
  section of the one thing an editor shows. What a page alone does is an override: the Songs
  page adds Space and refuses to delete the last song, the Grooves page lists the factory
  grooves first (`own_place`) and gives a factory groove only view and copy
  (`item_keys`), and the generator pages word their prompt and question with their label.
  Adding stays with each page. `C` says `copied to` and the copy's name on the status line and
  puts the cursor on the copy, and `S` keeps the cursor on the thing it was on, on every one.
  `tests/tui/test_tui_named_lists.py` runs the same checks on each page.
- The pages that show one named thing, the pattern, chain, groove, arpeggiator, AutoRatchet and
  offsets editors, the Scale page and the track editor, each inherit the mixin `ShowsNamedItem`
  (`screens/shared/shows_named_item.py`) beside their `Page`, `ListPage` or `FieldPage`. The mixin
  holds `show_item(name)`, `still_exists()`, `follow_renames(renames)` and `rename()` once. A
  page names its `SECTION`, its `CRUMBS_BEFORE` and `CRUMBS_AFTER` the name, its `ITEM_CRUMB`
  where the name reads another way (the track editor's `track: lead`) and its `RENAME_PROMPT`.
  The offsets editor shows an arpeggiator and renames nothing, and its thing is gone when the
  arpeggiator has no offsets. `Document.names_of(section)` and `has_named(section=, name=)`
  answer which names a section has, the factory grooves among the grooves.
  `tests/tui/test_tui_named_item_pages.py` runs the same checks on each page.

## Settings pages

- A `FieldPage`'s widgets (`screens/shared/field.py`) are `Field`s, one setting each, and `Button`s,
  rows that act on ENTER (`FieldPage.button` makes one from a main screen action).
- `Cells` is a row of settings side by side under one label, as a kit piece's on or off and its sound in the wizard (the user's
  design): Left and Right move between the cells (`FieldPage.cell`, `cell_field`, `ALONG_CELLS`) and step nothing there, each
  cell answers Space, ENTER and Bksp as the field it is, the cursor's cell is in reverse video, as a grid's, and a row is come
  to at its first cell.
- A `Button` is drawn as the main menu draws a row: the key's name in reverse video and then the
  button's name, with no explanation beside it.
- A `Button` with no `key_name` shows its name alone, and is reached with the arrows. A page's buttons whose row is wider than
  the page stand one under another, each a line in brackets, `[ Listen ]` (`MSG_STACKED_BUTTON`), the selected one marked with
  the triangle and bold; Up and Down then go through them as through the fields (`FieldPage.row_of_buttons`, `buttons_stacked`).
  A `Heading` made with `starts_open=True` is open until closed, the same toggle closing it.
- Buttons always come after the settings in `fields()`, and `FieldPage.body` draws them as one row of boxes
  (`tui/components/button_row.py`) below the settings after one blank line, the selected one double-lined, so no page codes
  that gap itself. Down from the last setting reaches the first button, Left and Right move along them
  (`FieldPage.ALONG_BUTTONS`, `move_along_buttons`), Up from any goes back to the last setting, and Down on them stays
  (`move_cursor`, `first_button_place`), the user's design.
- A `Field` is a label, the text of its value and what Left and Right, ENTER and Bksp do, each
  a function, so any setting can be one. Most settings are one of four kinds, each a class in
  `screens/shared/field.py` that is given what the setting is and works those functions out: `Toggle`
  (`on=`, `set=`, `●` on and `○` off (`MSG_FIELD_TOGGLE_OFF`, the user's design) unless given words of its own), `NameField` (`value=`,
  `rename=`), `NumberField` (`number=`, `set=`, `lowest=` and `highest=`, with `start=` for a
  setting that has no number yet, `shown=` and `typed=` for text that isn't the number, and
  `title=` for the prompt) and `ChoiceField` (`choices=`, `current=`, `set=`, with `names=` for
  what the picker calls the choices). A page makes its fields afresh for every key, so a kind is
  given the value as it is now. A setting with rules of its own stays a plain `Field`: one end
  of a track's octave range, typed in the set's octave labels, the set's default octaves, a
  song's time signature, entry size, scale and groove, a scale's root and kind and a clip's
  pattern, chain, direction and grab track.
- A `NumberField` keeps the number between its ends whether Left and Right step the number or
  ENTER types one, so a tempo stops at `MIN_TEMPO` and `MAX_TEMPO` and a scene's or a clip's
  Repeat at `MAX_SCENE_REPEAT` or `MAX_CLIP_REPEAT`. A seed has no ends.
- A `Toggle` answers to Space and ENTER alike (`TOGGLE_KEYS`, `KeyName.SPACE_ENTER`):
  `FieldPage.keys` asks the field `is_toggle()`, never what the field's words are.
- A settings page groups fields into sections with `FieldPage.heading(label=, is_set=)`, a
  `Heading` field (`screens/shared/field.py`): the fields after it, up to the next heading, show only
  while it is open (`shown_fields`, which the cursor, the drawing and the tests' `select_field`
  go by, a page's buttons always showing). A heading is drawn as the rows view's are,
  `MSG_SECTION_LABEL` with `+` or `-`, bold, and `MSG_SECTION_SET` (`(set)`) when `is_set()`;
  `Space` or `ENTER` toggles it (`is_toggle`), and `PgUp`/`PgDn` (`FieldPage.SECTION`, bound
  only on a page with headings) jump between headings (`jump_section`). The open sections are
  kept by label on the app as `open_field_sections`, closed to begin with, for the session.
- `tests/tui/test_tui_fields.py` tests each kind, and tours every settings page for the ends of its
  numbers and the keys of its toggles.

- Conditional Execution on a page (`tui/screens/shared/statements.py`, the user's design): `statement_section(page=, label=, table=,
  statements=, store=)` gives a heading that never says `(set)` and a `Cells` line for each of the `MAX_STATEMENTS` statements, each
  cell at a fixed width so nothing moves: the register (`ignored` first), the operator, and the parts the operator takes. A value's
  ENTER offers `number` and each register. Bksp, or choosing `ignored`, removes the statement, and a line past the last statement
  writes the next one, since a table keeps no gaps. A line's label is blank and as long as its place on the page (`table` tells a
  page's two tables apart), which is how `restore_place` and the tests find a line. `register_fields` gives the Set Registers and
  Increment Registers sections, a number for each register, `(none)` until typed. The Scene page, the clip page and the track
  editor list their sections; every generator's page gets its table from `ShowsNamedItem.shared_sections`, which
  `FieldPage.every_field` puts before the page's buttons; and the chain editor, a list page, opens `ChainStatementsPage` with `W`
  (When). `tests/tui/test_tui_statements.py` tests them.

## Opening, saving and exporting

- A file picker comes back to the directory it last showed, for the session and never saved, the user's ask: `OpenPage` keeps the
  directory in `app.last_folders` by the endings of the files it lists, so the Open page and the import's picker each have their own,
  whenever it goes into a directory or a file is picked, and forgets one that is gone.
- `--detail` on the recorder (`Launch.details`, the user's ask) starts Arrange with its details view showing, for a recording of the
  clips; it is one of the recorder's views, so it can't be asked for with `--visualizer`.
- Opening goes through `open_file(page=, path=, then=)` in `screens/shared/everywhere.py`, which the
  Open page calls. `Document.load_or_correct(path)` returns the document and the corrections the
  file needed (`.claude/format/MODEL.md`, "Corrections"): none for a file that reads strictly, and
  otherwise a document that is unsaved and has no saved state for an undo to go back to
  (`_differs_from_its_file`). A problem with no correction is told in a `MessageDialog`.
- With corrections, `offer_corrected` asks with a `CorrectionsDialog`
  (`tui/dialogs/corrections_dialog.py`), a `ConfirmDialog` whose `message_lines` are the file's
  name, the first `MOST_SHOWN` (5) corrections, each cut to the dialog's width with `fit`, a
  count of the rest (`MSG_CORRECTIONS_MORE`), and the warning that the composition may sound
  different and the file stays as it is until the set is saved. Yes opens the set. No opens
  nothing and stays on the Open page.
- `llamatron set.yml` on such a file makes the app with `corrections=`, and `on_mount` asks the
  same question over the main screen, with a new set behind the dialog until the answer is Yes.
- Saving compares the set's data, not its text, with what the file holds
  (`Document.file_holds_this_set`), and writes nothing and says so when they match.
- When the set's own file is protected (`Document.file_is_protected`, checked first), a
  `ConfirmDialog` of `MSG_PROTECTED_TITLE` offers to save a copy, leading to Save as, which
  refuses the protected file's own name in a `MessageDialog`.
- Saving asks before writing over a file that something else has changed since it was opened or
  saved (`Document.file_changed_elsewhere`).
- Ctrl+X opens a `ChoiceDialog` of `MSG_EXPORT_CHOICES` (`EXPORT_KINDS` in
  `exporters/exports.py`: Ableton Live set, MIDI (Stems), MIDI (Single File), MIDI (Clips), MIDI
  (General MIDI), WAV (FluidSynth), in that order, and documents for people call each kind what the
  dialog does). Choosing WAV (FluidSynth) (`export_chosen`) first asks with `MSG_WAV_EXPORT_NOTE`
  that only the tracks through FluidSynth are in it, or tells `ERR_WAV_NEEDS_FLUIDSYNTH` when it isn't
  installed.
- Export refuses first with the loop errors dialog if a scene can never end. It writes the current
  song beside the set's file as `<set>_<song>` files (`Document.export_directory()`,
  `export_name()`, and `export_path(to)`, the file for a Live set or the single MIDI file and a
  pattern like `foo_bar_stem_*.mid` otherwise), then says where it went (`MSG_EXPORTED`).
- A set with no file yet can't export (`Document.can_export`, `ERR_SAVE_BEFORE_EXPORT`), so
  Ctrl+X asks to save it first (`MSG_SAVE_BEFORE_EXPORT_TITLE`), runs Save as and goes on to the
  export dialog once it's saved. The File/Global page's Exports note says `(save the set first)` until
  then.
- Only a Live set asks before it's written over, and only the first time in a session for that
  path (`LlamatronApp.has_confirmed_overwrite`). The MIDI kinds just overwrite.

## The document

- `Document` (`tui/document.py`) holds a `Setlist` (`document.setlist()`), the name of the current
  song and that song (`document.song()`), the file the set came from, whether there are unsaved
  changes, and one `Memory` of what was worked out from the set (`document.memory()`). It draws
  nothing.
- `document.lengths()` is a `Lengths` (`tui/lengths.py`), a view of the current song. The
  lengths of scenes and clips come from one estimate of the song, `measured(song)`, a `Measured`
  of plain data with every scene's plays, seconds and the longest scene worked out in one pass,
  remembered until the set changes. A pattern's own length and step size take no estimate, so the
  pattern editor, where every edit changes the song, never measures the song.
- Pages that edit a song's tracks, scenes or registers use `document.song()`, and pages of shared
  sections use the set.
- `Document` is made of six classes in `tui/document_parts/`, one subject each, with no data of
  their own: `DocumentFiles` (`files.py`: load, save, save as, protection, export),
  `DocumentUndo` (`undo.py`), `NamedEdits` (`named_edits.py`: `rename_named`, `copy_named`,
  `delete_named`, `move_named` and `sort_named`, which take the section, so a pattern, a scale,
  a generator, a chain, a groove, a song and a track are renamed, copied, deleted, moved and
  sorted by the same five methods, with what differs for the current song, a factory groove's
  copy and a track's copy written there once; adding stays a method for each kind, since each
  new thing starts with something else), `SetEdits` (`set_edits.py`: the set's settings, songs, scales,
  generators, chains, grooves), `SongEdits` (`song_edits.py`: the current song's settings,
  tracks, scenes, registers, clips and groove choices) and `PatternEdits` (`pattern_edits.py`:
  steps, notes as the roll sees them, and what the editor asks about a pattern; how a note, its
  gate and its ties make the roll's one bar is `Pattern`'s to know, in
  `composition/pattern_notes.py`, and `PatternEdits` adds the step size and entry size the set
  may give the pattern, and remembers `covering_notes`). `document.py`
  keeps what they share: the constructor, `setlist()`, `song()`, `select_song`, `changed()`,
  `revision()`, `outside_patterns()`, `memory()`, `remembered`, `uses`, `lengths()`, `change(method, ...)`, which makes one change through an object's own method and notes it, and `set_setting(holder=, name=, value=)`. A page changes the set by `document.change(...)` on a method of the object the document hands it; the document keeps a method of its own only where it does more than pass the call on.
- Every `Document` method makes its change through the composition objects' own setters
  (`Pattern.set_value`, `Scene.set_cell`, `Song.rename_item` and so on), which check every value
  the way `from_data` does and raise `InvalidValue`, then calls `changed()`. `Document` never
  touches an object's data, and neither does any page.
- `Document.remembered(key=, on=, compute=)` keeps an answer in the document's `Memory`
  (`support/memory.py`) until one of the things in `on` has a new revision (`.claude/STYLE.md`,
  "Performance matters"). There are three kinds of `on`. The document itself, whose revision
  moves with every change and every change of the current song, is for anything in the set: a
  `ListPage`'s `remembered_rows`, the song's estimate, the roll's answers and every drawn line.
  `document.outside_patterns()`, a `ChangeMark` that `change` moves unless the method called was
  a `Pattern`'s own, is for what no pattern's contents can change: `uses(section=, name=)`,
  `scales_of_pattern`, `degree_limit`, `pattern_octave_range` and `cc_numbers_for_pattern`. And
  the objects themselves: `covering_notes` is kept on the pattern and the set, and
  `GridDrawing.beat_steps` on the pattern, the song and the set.
- An undo puts the set back in place and reads again only the items whose data differs, so the
  set and every unchanged item are the objects they were. The set's revision and the document's
  both move, so nothing remembered from the set as a whole is returned again.
- `PianoRoll.remembered` keeps the roll's own answers in the same memory, under the pattern's
  name (its scale, rows, steps, and each step's pitch, span and partial cell).
- Each drawn row is kept too: `RollDrawing.pitch_line` by its pitch and the steps shown, and
  `PatternDrawing.row_lines` by its row, the steps shown, the label column's width and the Degree
  gauge's height. The cursor's row on the roll is kept by the cursor's step as well, and the
  cursor's row and the section headings of the rows view are always drawn, so moving the cursor
  draws two rows and reuses the rest. `RollDrawing.notes()` gathers what the rows need to know
  about the notes once per change (`DrawnNotes`), and whoever draws a line asks for
  `beat_steps()` once and passes the steps to `append_edge`.
- The set and the song answer what uses what (`clip_slots_naming`, `scenes_naming`,
  `scenes_that_never_end` and so on, in `Setlist` and `Song`), and `uses_of(setlist=, section=,
  name=)` in `tui/uses.py` puts the answers into the words a page shows when it refuses to delete
  something in use: songs first, then scenes, tracks, clips and chains.
- Pages that copy a clip hold a `ClipSlot` and paste it with `paste_clip_slot`.

## Undo and redo

- Ctrl+Z undoes the last edit and Ctrl+Y redoes it on every page (`keybindings.Page.UNDO`
  and `REDO`). The Notes page's `key_table` is its own keys alone while editing, so
  Ctrl+Z waits until Save commits the text.
- The history (`History` in `tui/history.py`) is a ring of `HISTORY_DEPTH` (100) `Snapshot`s of
  the set's data and the current song's name, the oldest dropped without a word.
  `History(depth=)` is only for tests. Nothing shows or sets the depth, and nothing about the
  history is ever saved.
- A snapshot's data is `Setlist.kept_data()`: every stored object keeps its own file data until
  the object changes (`LlamaData.kept_data`, `.claude/format/MODEL.md`, "The composition model"), and
  the set's is put together from its items', so a snapshot shares every piece that no edit
  touched with the snapshot before, and recording an edit costs the size of the edit, not of the
  set. The history copies nothing, and nothing may change a snapshot's data: `Snapshot` is
  frozen, `note_song` makes a new one, and `describe_change` and `renamed_items` only read.
  `Document._own_data()`, which the unsaved mark and saving compare, is kept data too.
- A document whose memory checks, as every test's does (`Memory.check_every_answer`), proves
  the sharing as it goes and raises `StaleAnswer` otherwise: each snapshot's kept data is compared
  with a fresh `to_data()`, the history (`History(checks=True)`) keeps a copy of its own of every
  snapshot and compares when one is handed back, and every undo and redo is compared with the
  set read afresh from the whole snapshot.
- The history knows nothing about pages. `Document.record_edit()` is called by `Page.on_key`
  after every key press and by `Page.ask` after every dialog answer, and records a step only if
  the set's data changed. So a key or an answer is one step however many setters ran, and
  navigation never is.
- `Document.continue_edit()` merges the next recorded step into the previous one. The pattern,
  groove and offsets editors call it when a digit extends the number typed into the same cell, so
  digits typed into one cell are one step until the cursor moves. A munge is one step like any
  dialog answer.
- `Document.undo()` and `redo()` put the set back with `Setlist.restore(data)` and
  `fill_in_defaults`, make the snapshot's song current, and set the unsaved mark by comparing
  with the data last saved or loaded. `restore` runs the reading that `Setlist.from_data` runs,
  section by section (`_read`, `_read_items`), and reading keeps an item the set already has
  under its name whose kept data equals the data (`NamedItems.same_item`), so only what the edit
  changed is built again. A whole song is one item: a change to a song's tracks, scenes or clips
  reads that song again and keeps every pattern. They return a `Change` of words for the status
  line from `describe_change` (`pattern (bass)`, `song (verse): scene 2`, `title`) and of
  `renames`, or `None` when there's nothing to undo or redo.
- Opening or starting a set calls `forget_history()`. A song added on the Songs page is filled in
  like a loaded one (`Setlist.add_started_song`), so an undo and redo leave the same data.
- `everywhere.step_history(page, step=, done=, nothing=)` does the walk for both keys. Every open
  page (`app.pages()`) remembers what its cursor is on (`remember_place`, a row's key on a
  `ListPage` and a field's label on a `FieldPage`) and puts it back after (`restore_place`), so
  the cursor stays unless the row itself went.
- A page whose thing the step took away can't be shown (`still_exists()`: a named item on the
  editors, the scene's place and the name it opened with on `ScenePage`, the clip slot on `ClipPage`,
  and the arp's offsets on the offsets editor). `app.go_back_to()` pops to the page under it, the
  first one from the bottom that's gone decides, and the status line reads `undone: track (lead
  2), back from ARRANGE › track: lead 2` (`MSG_BACK_FROM`, from the page's `crumb_trail()`).
- A page whose thing the step renamed goes on showing it under its other name. `renamed_items`
  in `history.py` finds the names that differ at the same place with the same own data, or a
  scale still named after its root and kind, by section, and scenes by their place.
  `step_history` calls every page's `follow_renames(renames)` first. A page of one named thing
  (the editors, the Scale page and the track editor, each a `ShowsNamedItem`, below) calls its
  `show_item(name)`, the one place that sets the item and its crumbs, while `ScenePage` follows
  by place and `ClipPage` follows its track.
- The screen stack is Textual's, reached only through `app.pages()`, `go_back_to` and `is_open`,
  so that another toolkit could take its place.
- `tests/tui/test_tui_history.py` tests the history and the document, and `tests/tui/test_tui_undo.py` has
  an undo test class for every page (`.claude/TESTING.md`, "One test class per page"). Questions
  about what undo should do come to the user before anything is built.

## Instruments that cannot sound here

- `tui/silent_instruments.py`, the user's design: when a set opens, by the Open page
  (`open_set`), on the command line, or after the Corrections dialog's Yes (`LlamatronApp._opened`),
  a `MessageDialog` of `ERR_SILENT_INSTRUMENTS_TITLE` lists `ERR_FLUIDSYNTH_WILL_NOT_SOUND` once
  when an instrument a track plays through is on `*FluidSynth` and FluidSynth isn't installed, and
  `ERR_DEVICE_WILL_NOT_SOUND` for each such instrument whose port `output_port_names()` doesn't list
  (`silent_instrument_lines`). Nothing changes in the set. A launch that plays on its own
  (`Launch.is_plain()` false) shows nothing, since a dialog would stop it. `UITest` answers that
  FluidSynth is installed, so opening an example warns of nothing, and
  `tests/tui/test_tui_silent_instruments.py` tests the warning.

## Importing a MIDI file

- `M` on the main screen (`keybindings.MainPage.IMPORT_HERE`), the Import cell after Export,
  calls `import_midi` (`screens/set/importing.py`), which shows the Open page given
  `suffixes=MIDI_SUFFIXES`, `folder=home_folder()`, the crumbs `IMPORT MIDI` and `chosen`, what
  ENTER on a file does in place of opening a set, until the file picker is designed for the
  whole tracker (.claude/IDEAS.yml). `offer_import` reads the file with `MidiImport`, telling a file that
  can't be read in a `MessageDialog`, and asks with an `ImportDialog`.
- `ImportDialog` (`tui/dialogs/import_dialog.py`, `keybindings.ImportDialog`) is a dialog of
  fields, the user's design: the found line (`MidiImport.found`), Song name,
  Longest pattern, Use unique names, Chords, Import CCs and Step size, the line of what the import makes and
  its warnings, and Import and CANCEL side by side, each its key reversed and its name. The keys
  bound depend on the row: ENTER renames on Song name (a `PromptDialog` over the dialog), `[`
  and `]` step Longest pattern and Step size, Space or ENTER flips the toggles, and on the
  buttons Left and Right choose and ENTER presses; ESC and `I` work on every row. Each change
  asks `MidiImport.imported` again, remembered for each set of choices (`made`), so nothing is
  added until Import, which dismisses with what was made.
- `finish_import` calls `Document.import_song` (`SetEdits`), which adds the song with
  `add_imported` as one change and makes it current, so one Ctrl+Z takes the import away, goes
  back to the main screen, says `MSG_IMPORTED` and shows an `ImportedDialog`
  (`tui/dialogs/imported_dialog.py`), the user's design: "Song imported as
  (name).", what it holds, and every warning, or "Import complete with no warnings.", with one
  OK button that ENTER or ESC presses and no key list (`Dialog.shows_legend`). `tests/tui/test_tui_import.py` tests it, with the
  home directory pointed at a folder of the test's own.

## The status line

- `StatusLine` (`tui/status_line.py`) is one object the app holds. `Page.say(text)` sets it.
- It is drawn dim on the line above the legend of every page, and kept until the next key press
  clears it (`Page.on_key`, before the key acts), even across a change of page, so that a message
  said as a page closes is read on the page beneath.
- It carries where a save or an export went, what an undo undid (`undone: ...`) or a redo
  restored (`restored: ...`), `nothing to undo`, and why a key did nothing.
- Its messages are lower-case fragments with no full stop, keeping only the capitals of the
  user's names and of key names (`.claude/UX.md`, "Dialogs and the status line").

## The header and the crumbs

- A page's theme colour (`tui/themes.py`, `Page.THEME`, `theme()`), the user's design, is drawn as a stripe of spaces in that
  colour in place of the header's rule, with a blank line under it where the screen is `ROOM_FOR_THE_GAP` (30) lines or taller
  (`has_room_for_the_gap`, `header_lines`), so that an 80 by 24 console keeps every line. A page shares its section's colour with
  its list (`theme_of`, through `ShowsNamedItem.theme` and `NamedListPage.theme`): songs blue, patterns green, chains violet,
  generators magenta, scales teal, grooves orange, instruments yellow, the Registers page red, the File/Global, Notes and Open pages
  grey, and the pages reached from Arrange (Scene, clip, track) cyan; the main screen's is white, the user's choice, and Arrange keeps the rule.

- `Page.header` draws two lines and the rule, each line by `header_line(left=, right=)`, which
  cuts the left text to leave the right whole. The first (`MSG_TITLE_LINE`) is `PROGRAM_NAME` and
  then the open set and the current song (`MSG_FILE_CRUMB`, `Page.file_crumb`), like
  `llamatron   set: first.yml, song: verse`, the set named as such, because the
  set is what is saved, not the song. Before the set is saved the crumb reads `set: (unsaved)`
  (`MSG_NO_FILE_CRUMB`), and a song that doesn't exist reads `(none)`. The version is not in the
  header, so that the names fit: the About dialog shows it.
- The first line's right side holds the save mark (`Page.save_mark`): `● unsaved`
  (`MSG_UNSAVED_MARK`) for a set with no file yet, `● unsaved changes`
  (`MSG_UNSAVED_CHANGES_MARK`) for a set with a file that is dirty, and `○ saved`
  (`MSG_SAVED_MARK`) for one that isn't.
- The second line is the crumbs (`crumb_trail`, joined with `MSG_CRUMB_SEPARATOR`), like
  `PATTERNS › lead`, with `Crumb.MAIN_SCREEN` on the main screen, and the time (`duration`,
  `clock`) at the right: the user's choice over one line of title and crumbs,
  where the deep pages' names were cut short on an 80-column console. The F1 dialog's title
  names the same crumbs.
- `Page.header_lines()` counts the header's lines, which `screens/pattern/pattern_drawing.py` reads, so a third
  header line would change it.

