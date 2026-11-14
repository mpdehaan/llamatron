# The tracker

Reference notes for Claude on the text UI in `src/llamatron/tui`, which is meant to become the only
way people use the program. One short section per page or topic, so that the part about one thing
can be found and read on its own. `.claude/UX.md` holds the rules for how the tracker behaves,
`.claude/STYLE.md` the rules for the code, `GUIDE.md` is the user's guide to the same pages, and
`.claude/FORMAT.md` covers what the pages edit. Why each thing is the way it is, with the choices
that were tried and dropped and their dates, is in `.claude/DECISIONS.md`, which isn't loaded into
a session: read it before proposing to change something a section here says the user chose.
`test/test_doc_paths.py` checks that every source path named here exists, so paths move with the
code.

## Where things are

`llamatron [set]` or `./llamatron.sh [set]` opens the tracker. It uses Textual with
`ansi_color=True`. One class per file in `screens/` and `dialogs/`.

- `tui/app.py`: `LlamatronApp`, which holds the document, the status line and what is kept for
  the session (`on_roll`, `open_sections`, `has_confirmed_overwrite`).
- `tui/document.py` and `tui/document_parts/`: the set being edited ("The document" below).
- `tui/history.py`: the undo history. `tui/lengths.py`: how long things last. `tui/uses.py`: what
  uses what, in the words a page shows. `tui/text.py`: text helpers pages share (`clock`, `sorted_names`),
  and `composition/naming.py` how a new thing is named (`words`, `unique_name`, `copy_name`,
  `is_default_scale_name`), which the MIDI import shares.
- `tui/keys.py`: every physical key's name. `tui/keybindings.py`: every key binding, one class
  for each page, dialog and component. `tui/key_table.py`: `KeyBinding`, `BindsKeys`, `bound()`,
  `cursor_moved()` and `pressed_key()`.
- `strings/help.py`: every page's help text, one `HELP_` constant each.
- `tui/drawing.py`: the styles, the box characters, the selected row's mark (`SELECTED_MARK`,
  `cursor_mark(selected)`), `Canvas` and the text-fitting helpers.
- `tui/status_line.py`: `StatusLine`.
- `tui/screens/`: every page, each a `Page` (`screens/page.py`), a `ListPage`
  (`screens/list_page.py`) or a `FieldPage` (`screens/field_page.py`), with the helpers only one
  page uses beside it, what several share in `screens/shared.py`, and the keys every page has in
  `screens/everywhere.py`. `screens/grid_drawing.py`, `screens/pattern_drawing.py` and
  `screens/roll_drawing.py` draw the pattern editor, and `screens/arrange_drawing.py` draws
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
  `K` and `G`). `Page.EVERYWHERE` is the keys every page has.
- Where one key means different things as the cursor moves, each meaning is a binding of its own
  and the page binds the one that applies: `ArrangePage.ADD_SCENE` and `ADD_TRACK`,
  `OffsetsEditor.SILENT` and `PLAY`, `SectionRow.OPEN` and `CLOSE`, `PatternEditor.TO_ROLL` and
  `TO_EDITOR`, and `ListPage.ADD_HERE` for Enter on the `+` row. Two bindings of one class can
  hold the same keys and words, like `ArrangePage.MOVE` and `INSET_MOVE`, the arrows on the grid and in Scene View, so a binding is found
  in a list as the constant it is (`place_of` in `tui/key_table.py`), never by what it holds.
- A class that binds keys inherits `BindsKeys` (`tui/key_table.py`) and declares
  `KEYS = keybindings.<its own name>`. Each screen lists its keys once, in `keys()`, with
  `self.bind(self.KEYS.RENAME, action=self.rename)`, which returns a `KeyBinding` that both
  handles and draws the key. `bind` takes `wants_key=True` for a key that types its own character
  (digits, note letters, search text) or an arrow that moves a cursor, whose action is passed the
  key's name, and three overrides for what depends on the set: `keys=` and `name=` (the Degree
  row binds the digits of its scale's degrees, and the Octave row names its range) and `what=` (a
  settings page says what Enter and Bksp do on the field under the cursor).
- An action bound to a `Steps` is called with `STEP_BACK` (-1) or `STEP_FORWARD` (1), never the
  key: the groove and offsets editors' nudge, Move mode's carries (`ListPage.carry`, calling `page.shift`, and Arrange's `carry`), `PianoRoll.drag`, `PatternEditor.jump_end`, `PatternRows.jump_section`,
  `GridChoiceDialog.turn_key` and `NotesPage.scroll`.
- `Page.key_table()` is `everywhere_keys(page)` joined to `page_key_table()`, which is
  `self.in_order(self.keys())`: the class's own bindings in the order of its `IN_HELP`. A page
  made of parts lists its parts' keys among its own, each part already in its own class's order,
  and `BindsKeys.in_order` leaves those where they are. The pattern editor lists Esc, the view's
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
- Legends keep one order: Esc first, then the arrows, then the keys the page has in all of its
  modes, then the rest, which is the order of each class's `IN_HELP`.
- The rules are kept by `test/test_keybindings.py` (every class that binds keys has the bindings
  class of its name, inheriting the same way; every binding is keys, a name and words, is listed
  and is bound somewhere; every `Key` is bound or in the test's `NEVER_BOUND`; every `KeyName`
  names a binding) and by the tour in `test/test_tui_help_keys.py` (every bound key is one of its
  own class's bindings, and no key reaches two bindings in one place). `internal_tools/show_keys.py`
  (`internal_tools/keys.sh`) prints every class's bindings, one class's, or every binding that has a key.

## The keys that work everywhere

- `everywhere_keys(page)` in `tui/screens/everywhere.py` returns Ctrl+S (save), Ctrl+O (open,
  which shows `OpenPage` and comes back to the page it was pressed on), Ctrl+X (export), Ctrl+T
  (silence, `Page.SILENCE`, the emergency stop of real-time playback, "Real-time playback"
  below), Ctrl+Z, Ctrl+Y, F1 (help) and F3 (about), in that order (`Page.EVERYWHERE` in
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
- Esc goes back on every page and cancels every dialog. Tab never goes back: it switches the
  pattern editor's view, turns a `GridChoiceDialog`'s pages, completes in the pickers and the list
  search, and reaches the Notes page's buttons.

## Help and About

- `HelpDialog` (`tui/dialogs/help_dialog.py`, `Page.show_help`) shows the everywhere keys, a blank
  line and the page's own keys in two columns (`key_columns`). Tab, Left and Right turn to the
  panel with the page's `HELP` text (`MSG_HELP_PANELS`). Enter, Esc or F1 again closes it, and
  `Page.show_help` leaves F1 out of the everywhere keys it lists, so that the seven left fill two
  columns downwards over four lines, Silence last in the first column, with Undo still above
  Redo in the second, the user's choice.
- Each page names its `HELP_` constant from `strings/help.py` as `HELP`. `test/test_tui_help_keys.py`
  checks that every key a help text names is bound on that page, and `test/test_tui_pages.py`
  that the help fits an 80 by 24 console.
- `AboutDialog` (`tui/dialogs/about_dialog.py`, `Page.show_about`) draws the cowsay cow in code
  (`cow_saying`), `VERSION`, `BUILD_DATE` and `BUILD_TIME` from `support/version.py`, the links, a
  quote and the license with `build_year()`.
- The quote is drawn by `random_quote` from `MSG_ABOUT_QUOTES`, or is the eight ball's answer a
  third of the time (`EIGHT_BALL_CHANCE`), with Python's own `random`. It has a blank line above
  and below and wraps onto up to `QUOTE_LINES` (4) lines. The blank below gives way at two lines
  and the one above at three, so that the dialog stays on an 80 by 24 console.

## The main screen

- `MainPage` is a grid of cells drawn on `Canvas` lines, the user's layout: `rows()` is Arrange and the Real Time switch, then
  Songs, Scales, Patterns and Grooves, then Generators, Chains, Instruments and Registers (the user's order), then the Set File page and `actions()`
  (Save, Open, Export, Import, Quit), with `LINES_ABOVE_ARRANGE`, `LINES_ABOVE_PAGES` and `LINES_ABOVE_FILE` blank lines over the
  groups. A row's cells share `GRID_WIDTH` (80), each as wide as it needs (`needed_width`), the spare columns spread evenly and
  Arrange's cell taking all its row leaves (`cell_widths`); a row too wide gives up the space before the right edge of each cell
  with no count, as the file's row does at 80 columns. With a set open the cursor starts on Arrange.
- A cell is named by `cell_name(item)`: the page its key opens, which is the binding's words (a
  `PageName` from `strings/labels.py`), or the action's name (`ACTION_NAMES`).
- `draw_cell` draws the key reversed, the name, and the count right-aligned, Arrange's key and name centred, and a box around
  every cell: its page's theme colour toned to one brightness (`themes.balanced`, `EDGE_LUMINANCE`, `edge_style`, the user's ask
  that no colour look stronger than another), dim for a cell with no theme, and double-lined and bold around the selected cell.
- `count(item)` is the set's songs, patterns, chains, generators (both kinds), scales or own
  grooves (`COUNTED_SECTIONS`, `Setlist.get_own_groove_names`), and `None` for File, Registers,
  Arrange and the actions.
- Nothing sits between the rule and the cells: the crumbs name the set and the song, and the
  cells count what the set holds. The user dropped the set-and-song line and the song summary
  (tempo, scale, tracks, scenes), and wants the tempo on Arrange some day. The
  last body line is the selected cell's `MSG_ABOUT` sentence, dim.
- Started with no set named, the tracker opens with the cursor on Open (`LlamatronApp(cursor_on_open=)`, which
  `main` passes when the command line names no file, `MainPage.select_open`), the user's ask.
- The cursor (`place`, `menu_items()`, `row_and_column`, `move_cursor`, `open_selected`) moves
  with all four arrows: Left and Right along the cells from row to row, Up and Down between rows
  keeping the column where the row has one, none going past an edge. Enter follows. The cursor
  keeps its place while a page is open over it.

## Dialogs, pickers and searching

- `ConfirmDialog` draws Yes and No as buttons (`MSG_CONFIRM_BUTTONS`, `choice`), moved by Left and
  Right and pressed by Enter, with `Y` and `N` still answering.
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
- Every list a page can add to has a `+` row at the bottom, where Enter does the same as `A`
  (`keybindings.ListPage.ADD` and `ADD_HERE`, as `ArrangePage.ADD_SCENE` and `ADD_TRACK` have
  their `_HERE` bindings on Arrange).
- On settings pages `[` and `]` change a value and are what the legend names
  (`FieldPage.LESS` and `MORE`, `KeyName.LEFT_BRACKET` and `RIGHT_BRACKET`, `[` dec and `]`
  inc as everywhere), with Left and Right and the rest of `LESS_KEYS` and
  `MORE_KEYS` doing the same off the legend.
- Deleting anything still used is refused with up to five uses listed, and otherwise confirms.
- The pages that list the named things of one section, Patterns, Scales, Chains, Grooves, Songs
  and the two generator pages, are each a `NamedListPage` (`screens/named_list_page.py`), which
  holds `rename`, `copy`, `delete`, `shift` and `sort` once, each calling the document's edit
  that takes the section (`rename_named` and the rest). A page names its `LISTED_SECTION`, its
  `RENAME_PROMPT` and its `WHAT` (the words for one thing in a question), and says what Enter
  opens with `open_item`. `S` sorts on every one of them, the Grooves page sorting the set's own
  grooves under the factory ones. `LISTED_SECTION` is not `SECTION`, which is the
  section of the one thing an editor shows. What a page alone does is an override: the Songs
  page adds Space and refuses to delete the last song, the Grooves page lists the factory
  grooves first (`own_place`) and gives a factory groove only view and copy
  (`item_keys`), and the generator pages word their prompt and question with their label.
  Adding stays with each page. `C` says `copied to` and the copy's name on the status line and
  puts the cursor on the copy, and `S` keeps the cursor on the thing it was on, on every one.
  `test/test_tui_named_lists.py` runs the same checks on each page.
- The pages that show one named thing, the pattern, chain, groove, arpeggiator, AutoRatchet and
  offsets editors, the Scale page and the track editor, each inherit the mixin `ShowsNamedItem`
  (`screens/shows_named_item.py`) beside their `Page`, `ListPage` or `FieldPage`. The mixin
  holds `show_item(name)`, `still_exists()`, `follow_renames(renames)` and `rename()` once. A
  page names its `SECTION`, its `CRUMBS_BEFORE` and `CRUMBS_AFTER` the name, its `ITEM_CRUMB`
  where the name reads another way (the track editor's `track: lead`) and its `RENAME_PROMPT`.
  The offsets editor shows an arpeggiator and renames nothing, and its thing is gone when the
  arpeggiator has no offsets. `Document.names_of(section)` and `has_named(section=, name=)`
  answer which names a section has, the factory grooves among the grooves.
  `test/test_tui_named_item_pages.py` runs the same checks on each page.

## Settings pages

- A `FieldPage`'s widgets (`screens/field.py`) are `Field`s, one setting each, and `Button`s,
  rows that act on Enter (`FieldPage.button` makes one from a main screen action).
- A `Button` is drawn as the main menu draws a row: the key's name in reverse video and then the
  button's name, with no explanation beside it.
- Buttons always come after the settings in `fields()`, and `FieldPage.body` draws them as one row of boxes
  (`tui/components/button_row.py`) below the settings after one blank line, the selected one double-lined, so no page codes
  that gap itself. Down from the last setting reaches the first button, Left and Right move along them
  (`FieldPage.ALONG_BUTTONS`, `move_along_buttons`), Up from any goes back to the last setting, and Down on them stays
  (`move_cursor`, `first_button_place`), the user's design.
- A `Field` is a label, the text of its value and what Left and Right, Enter and Bksp do, each
  a function, so any setting can be one. Most settings are one of four kinds, each a class in
  `screens/field.py` that is given what the setting is and works those functions out: `Toggle`
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
  Enter types one, so a tempo stops at `MIN_TEMPO` and `MAX_TEMPO` and a scene's or a clip's
  Repeat at `MAX_SCENE_REPEAT` or `MAX_CLIP_REPEAT`. A seed has no ends.
- A `Toggle` answers to Space and Enter alike (`TOGGLE_KEYS`, `KeyName.SPACE_ENTER`):
  `FieldPage.keys` asks the field `is_toggle()`, never what the field's words are.
- A settings page groups fields into sections with `FieldPage.heading(label=, is_set=)`, a
  `Heading` field (`screens/field.py`): the fields after it, up to the next heading, show only
  while it is open (`shown_fields`, which the cursor, the drawing and the tests' `select_field`
  go by, a page's buttons always showing). A heading is drawn as the rows view's are,
  `MSG_SECTION_LABEL` with `+` or `-`, bold, and `MSG_SECTION_SET` (`(set)`) when `is_set()`;
  `Space` or `Enter` toggles it (`is_toggle`), and `PgUp`/`PgDn` (`FieldPage.SECTION`, bound
  only on a page with headings) jump between headings (`jump_section`). The open sections are
  kept by label on the app as `open_field_sections`, closed to begin with, for the session.
- `test/test_tui_fields.py` tests each kind, and tours every settings page for the ends of its
  numbers and the keys of its toggles.

## Opening, saving and exporting

- Opening goes through `open_file(page=, path=, then=)` in `screens/everywhere.py`, which the
  Open page calls. `Document.load_or_correct(path)` returns the document and the corrections the
  file needed (`.claude/FORMAT.md`, "Corrections"): none for a file that reads strictly, and
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
  export dialog once it's saved. The Set File page's Exports note says `(save the set first)` until
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
  `revision()`, `outside_patterns()`, `memory()`, `remembered`, `uses`, `lengths()` and `_change`.
- Every `Document` method makes its change through the composition objects' own setters
  (`Pattern.set_value`, `Scene.set_cell`, `Song.rename_item` and so on), which check every value
  the way `from_data` does and raise `InvalidValue`, then calls `changed()`. `Document` never
  touches an object's data, and neither does any page.
- `Document.remembered(key=, on=, compute=)` keeps an answer in the document's `Memory`
  (`support/memory.py`) until one of the things in `on` has a new revision (`.claude/STYLE.md`,
  "Performance matters"). There are three kinds of `on`. The document itself, whose revision
  moves with every change and every change of the current song, is for anything in the set: a
  `ListPage`'s `remembered_rows`, the song's estimate, the roll's answers and every drawn line.
  `document.outside_patterns()`, a `ChangeMark` that `_change` moves unless the method called was
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
  the object changes (`LlamaData.kept_data`, `.claude/FORMAT.md`, "The composition model"), and
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
- `test/test_tui_history.py` tests the history and the document, and `test/test_tui_undo.py` has
  an undo test class for every page (`.claude/TESTING.md`, "One test class per page"). Questions
  about what undo should do come to the user before anything is built.

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
  (`stop_from_the_corner`) or Esc on Arrange (`ArrangePage.go_back`) calls `LlamatronApp.end_take`, which lets the
  lead-out ring and then `_finish`es on the splash; a looping song isn't refused, and the recorder records with the
  tutorial's `ScreenRecording`, which has no time limit and stops when the tracker quits. The three
  timings are arguments of `Launch` so that the tests needn't wait. `Launch(test_splash=True)` shows
  the start screen alone for `splash_seconds` and quits (`internal_tools/demo_splash_screen.py`,
  `internal_tools/demo_splash_screen.sh`). A launch other than that needs a set, and none works with `--to`.
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
- The splash (`Splash`, `tui/screens/splash.py`), a Textual `Screen` binding no keys, draws the title for its
  seconds when the tracker is launched for recording; it replaced the word that waved letter by letter, after the end
  credits of Monty Python and the Holy Grail, keeping the waves as the entrance. It draws every `FRAME_SECONDS` on its
  own timer, and takes a clock for the tests.
- The start screen (`StartScreen`, `tui/screens/start_screen.py`, `keybindings.StartScreen`) is the splash with
  `MSG_START_PROMPT` six lines under the address, pulsing between dim and bright (`prompt_level`), until Enter takes
  it away. Only the command line asks for it (`LlamatronApp(start_screen=)`, `start_screen_wanted` in
  `tui/launch.py`), unless `LLAMATRON_NO_SPLASH=1`, and only on a plain launch; it goes over the main screen and any
  dialog the opening raised, so the tests and the tools that make the app never see it.
- `test/test_tui_playback.py` tests the launches on the playback test's stepped clock, with
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
  pressing Enter, never with the page's letter, so that a viewer sees where it is going
  (`open_page`, the user's wish, which reversed the letters of earlier that day),
  which `test/test_tutorial.py` holds it to. A page that is open already, under what is on top,
  is gone back to with Esc instead and nothing is said (`CELL_PAGES`, `go_back_to`), so that no
  page is opened twice in a row.
- The build goes the song's settings, the scales, then one track at a time, each track's clips
  scene by scene from the top, each pattern drawn on the piano roll when a track first needs it
  and its other rows set in the rows view, then the clip put on Arrange. Each thing made is
  announced, "And now we are making a pattern called (riff).", and each thing the new set
  already has, its song, `track 1`, `scene 1` and the starter pattern, "There is already a track,
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
  again on the piano roll and in the rows view (`ARROWS_EXPLAINED`); Enter and Esc the first time
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
  which can't turn captions on for every viewer. `test/test_tui_caption_strip.py` tests it.
- Nothing is saved, unless `--save-set-yaml` names a file. `test/test_tutorial.py` tests it.
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
  `test/test_make_video_tutorial.py` tests the recording with a stand-in for `screencapture`.

## Instruments that cannot sound here

- `tui/silent_instruments.py`, the user's design: when a set opens, by the Open page
  (`open_set`), on the command line, or after the Corrections dialog's Yes (`LlamatronApp._opened`),
  a `MessageDialog` of `ERR_SILENT_INSTRUMENTS_TITLE` lists `ERR_FLUIDSYNTH_WILL_NOT_SOUND` once
  when an instrument a track plays through is on `*FluidSynth` and FluidSynth isn't installed, and
  `ERR_DEVICE_WILL_NOT_SOUND` for each such instrument whose port `output_port_names()` doesn't list
  (`silent_instrument_lines`). Nothing changes in the set. A launch that plays on its own
  (`Launch.is_plain()` false) shows nothing, since a dialog would stop it. `UITest` answers that
  FluidSynth is installed, so opening an example warns of nothing, and
  `test/test_tui_silent_instruments.py` tests the warning.

## Importing a MIDI file

- `M` on the main screen (`keybindings.MainPage.IMPORT_HERE`), the Import cell after Export,
  calls `import_midi` (`screens/importing.py`), which shows the Open page given
  `suffixes=MIDI_SUFFIXES`, `folder=home_folder()`, the crumbs `IMPORT MIDI` and `chosen`, what
  Enter on a file does in place of opening a set, until the file picker is designed for the
  whole tracker (dev_notes/IDEAS.md). `offer_import` reads the file with `MidiImport`, telling a file that
  can't be read in a `MessageDialog`, and asks with an `ImportDialog`.
- `ImportDialog` (`tui/dialogs/import_dialog.py`, `keybindings.ImportDialog`) is a dialog of
  fields, the user's design: the found line (`MidiImport.found`), Song name,
  Longest pattern, Use unique names, Chords, Import CCs and Step size, the line of what the import makes and
  its warnings, and Import and Cancel side by side, each its key reversed and its name. The keys
  bound depend on the row: Enter renames on Song name (a `PromptDialog` over the dialog), `[`
  and `]` step Longest pattern and Step size, Space or Enter flips the toggles, and on the
  buttons Left and Right choose and Enter presses; Esc and `I` work on every row. Each change
  asks `MidiImport.imported` again, remembered for each set of choices (`made`), so nothing is
  added until Import, which dismisses with what was made.
- `finish_import` calls `Document.import_song` (`SetEdits`), which adds the song with
  `add_imported` as one change and makes it current, so one Ctrl+Z takes the import away, goes
  back to the main screen, says `MSG_IMPORTED` and shows an `ImportedDialog`
  (`tui/dialogs/imported_dialog.py`), the user's design: "Song imported as
  (name).", what it holds, and every warning, or "Import complete with no warnings.", with one
  OK button that Enter or Esc presses and no key list (`Dialog.shows_legend`). `test/test_tui_import.py` tests it, with the
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
  generators magenta, scales teal, grooves orange, instruments yellow, the Registers page red, the Set File, Notes and Open pages
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
- `Page.header_lines()` counts the header's lines, which `screens/pattern_drawing.py` reads, so a third
  header line would change it.

## File and Notes

- The Set File page (`F`, `FilePage`) shows, in the user's order, the loose settings alphabetically (Author, Default follow
  action, Description, Notes, Protected, Title), then the sections Notes & Octaves (Default drum octave, Default octave,
  Octave labels, Step size) and Visualizers (Visualizer, and Hide Visualizers, a field opening a `PickManyDialog`,
  `tui/dialogs/pick_many_dialog.py`, where Space picks modes and Enter keeps them), then Save and Open
  buttons, with the path of the set's file and where the current song exports noted below. `N`
  starts a new set and `W` saves as.
- The Description field is one line of text, typed in a prompt like the title. The Notes field
  shows the notes' first line or `not set`, and Enter on it opens `NotesPage` editing
  (`editing=True`). The page was the Description page until the user made the
  description one line and the long text the notes.
- Editing types into a draft of the page's own until Tab reaches the Save and Cancel buttons
  under the text (`MSG_NOTES_BUTTONS`, `on_buttons`, `button`; Left and Right choose, Enter
  presses, Tab comes back to the text). Save stores the draft as one edit. Cancel, or Esc
  anywhere, throws the draft away.
- Reading, Esc goes back, Up and Down scroll (`scroll`), `E` edits and `Bksp` clears after
  asking.
- A protected set's notes open reading with no `E` or `Bksp`
  (`MSG_NOTES_PROTECTED`): it is read-only even though the set's other settings can be
  changed and saved as a copy.

## Songs and Song

- The Songs page (`S`, `SongsPage`) lists the songs and marks the current one with `●`. `Space`
  makes the selected song current, and `Enter` makes it current and opens `SongPage`.
- It adds, copies, renames, moves, sorts and deletes songs, refusing to delete the last one.
- `SongPage` has the song's name, which `Enter` on the Name field renames, then tempo, time
  signature, entry size, scale, seed, groove, genre (a `text_field`, which `FieldPage` holds for
  every settings page, as the Set File page's title uses), Live response (a `ChoiceField` of
  `LIVE_RESPONSIVENESSES`, named by `MSG_LIVE_RESPONSIVENESS_NAMES`) and an Export button.
- Registers and Arrange edit the current song.
- A brand-new song (`Song.started`, `started_song`, `Setlist.add_started_song`, which
  `new_setlist()` and the Songs page's `A` use) starts with `track 1` and `scene 1`. A file that
  leaves tracks or scenes out stays empty (`new_song`, `Song.new`, `add_new_song`).
- Only a new set gets the starter pattern and the clip that plays it (`new_setlist`,
  `.claude/FORMAT.md`), since a song added to a set already has the set's patterns.

## Scales and Scale

- The Scales page (`Z`) lists the set's scales. `Enter` opens `ScalePage`
  (`tui/screens/scale_page.py`), and `A` adds a C major scale and opens it.
- `ScalePage` has one scale's Name, Root and Kind on one page, laid out by `SCALE_PAGES` and
  `ROOT_KEYBOARD`. The scale picker shortens long names only on screen.
- A scale still named after its root and kind, like `C Major`, is renamed as they change
  (`Document.set_scale_root` and `set_scale_kind` return the name, and `is_default_scale_name` in
  `composition/naming.py` decides). A name of the user's own stays.
- Under the fields, `ScalePage.notes` draws a two-octave `Keyboard`
  (`tui/components/keyboard.py`): the black keys' row above the white keys', the scale's keys
  `MSG_KEY_IN_SCALE` and the rest `MSG_KEY_OUT_OF_SCALE`. The names row brackets the root
  (`MSG_ROOT_KEY_NAME`), under its black key in place of the two white names beside it when the
  root is a black key.

## Generators and chains

- The Generators page (`G`, `screens/generators_page.py`, the user's design) lists every generator of the set on one
  list, its kind in parentheses beside its name (`MSG_GENERATOR_KIND_SHOWN`), in the order `Setlist.ordered_generators`
  gives: the set's `generator_order` (`.claude/FORMAT.md`), then any it leaves out, kind by kind. Enter opens the editor
  (`GENERATOR_PAGES` in `screens/generator_pages.py`, a `GeneratorListing` of kind, section, label and `EDITOR` for each kind);
  `A` asks for a kind, names one after it and opens it; `N`/F2, `C` (the copy straight after), `Bksp` (refused while a chain
  uses it) and `/` as on every list; Move mode keeps the order in the set (`Document.move_generator`). There's no sort, and no
  page of one kind: the fifteen were taken out, and each editor's crumbs read `GENERATORS › name`.
- The drift editor (`screens/drift_editor.py`, a `FieldPage`) lists the drift's own settings, then
  one row per value with A's and B's side by side, the picked one in `MSG_DRIFT_PICKED`; on such a
  row Left and Right pick the version (`DriftEditor.VERSION`), so only `[` and `]` change a value,
  and the page scrolls as settings pages do.
- A Density, Swell or Articulate opens a `ShapeEditor` (`screens/shape_editor.py`): Name, then `shape_fields` from
  `screens/shape_fields.py` (Start, End, Over, Then), and on the swell editor Accent. The Scene
  page and the clip page end with a section for each shape (`shape_section`, the same fields
  with the shape's name in front of each label), through `set_scene_shape_setting` and
  `set_clip_shape_setting` (`SongEdits`). `test/test_tui_shapes.py` tests them.
- The `ProgressionEditor` has Name, Every and Chords, whose
  Enter opens the `ChordsEditor` (`screens/chords_editor.py`), a `StepEditor` with the `StepGrid`
  drawing of the one-row editors (`screens/step_grid.py`) but rows of its own: a column a chord,
  a gauge of `MSG_GAUGE_BAR` up to the degree, the numeral and the name, then `#/b` and `Inv.`.
  The arrows move along the chords and between the three rows (`edited_row`); `[` and `]` step,
  digits type a degree or an inversion, Space or Enter cycles the `#/b` and `Inv.` rows, `I` and
  `D` insert and remove, and `H` (`PICK`) opens a `GridChoiceDialog` of the named progressions,
  filling the chords through `named_progression_in` (`Document.set_progression`).
- The `VoiceLeadingEditor` has Name, Lowest octave and Highest octave
  (`octave_field`, `screens/octave_field.py`, which the track editor's range shares) and the toggle
  Keep the root in the bass. `test/test_tui_voice_leading.py` tests them.
- The `StrumEditor`, and the `+ Strum` sections at the end of the
  track editor and the clip page, share `strum_fields` (`screens/strum_fields.py`): Direction, with
  `(none)` first on a track and `(track)` on a clip, Spread named with its milliseconds, Fade, Loose
  timing and Upstroke strings, prefixed Strum in a section. `test/test_tui_strum.py` tests them.
- The `EuclidEditor`, and the track
  editor's `+ Euclid` section, share `euclid_fields` (`screens/euclid_fields.py`): Hits, Steps,
  Rotate and Step; on the Hits field, `H` (`PICK_RHYTHM`, bound by the page's `page_keys` only
  there) opens `pick_rhythm`, a `ChoiceDialog` of the named rhythms. `test/test_tui_euclid.py`
  tests them.
- A Glide, Shorten, Rush or Drag opens its editor (each a `StepRowGeneratorEditor`, its steps on one line by `steps_text`: Name, Step, its amount,
  Steps and Restart). Enter on Steps opens the kind's steps page (`GlideStepsEditor` and the rest),
  each a `StepRowEditor` (`screens/step_row_editor.py`, a `StepEditor` with the `StepGrid`
  drawing): Left and Right move, Space or Enter (Up and Down off the legend) turns a step on or
  off, `I` and `D` insert and remove. `test/test_tui_step_rows.py` tests them.
- The `HocketEditor` has Name,
  Source track (a `ChoiceField` of `(none)` and the current song's tracks, sorted, the Hocket's own
  source kept among them when the song lacks it) and Restart. `test/test_tui_hocket.py` tests them.
- Every generator's editor ends its own settings with `restart_field(page)`
  (`screens/restart_field.py`), a `ChoiceField` of `RESTARTS` named by `MSG_RESTART_NAMES`, found by
  the page's `SECTION` and `item`.
- Every time setting's field is `time_field(page=, label=, written=, first=, store=)`
  (`screens/time_field.py`): its first choice, standing for blank, then `TIME_CHOICES`, named by
  `MSG_TIME_NAMES` where a dotted or triplet fraction says nothing, and a value the list lacks
  offered last so nothing is lost. The arp editor's Step, the drift editor's Every and the
  shapes' Over use it.
- The arp and AutoRatchet editors have a Name field, and the chain editor's `N` renames.
- The chain editor shows each step as the generator's name and then its kind, `sparse (Density)` (`steps_shown`), the user's choice over
  `density: sparse`, which read as a chain's name; a generator listed again is numbered on screen only, `sparse 2 (Density)`.
- The chain editor's picker of generators (`ChainEditor.pick_generator`, for `A` and Enter) offers `(new generator)`
  first, the user's ask, which asks for a kind (`new_generator`, in `GENERATOR_PAGES` order), makes one named after
  the kind (`arpeggiator 1`, numbered after the first), puts it in the chain where the step was being added or
  changed, and opens its editor with the chain's crumbs first (`ShowsNamedItem.opened_from`).
- An arp's offsets have their own editor ("The offsets editor" below).

## Grooves

- The Grooves page (`V`, `GroovesPage`) lists the factory grooves first, marked `factory`, with
  only `Enter` (view) and `C` (copy) on them, and the set's own with the usual list keys.
- `A` adds `groove 1` and so on (`MSG_NEW_GROOVE_NAME`) and opens the `GrooveEditor`.
- The `GrooveEditor` is a one-row editor like the offsets editor ("The one-row editors" below),
  with `I`, `D`, `S` for the cell length (`GROOVE_CELL_LENGTH_CHOICES`) and `N` to rename, and
  the name shown above the cells. A groove wider than the screen scrolls sideways, with
  `cells 1-11 ›` (`MSG_CELLS_SHOWN`) at the right of the name, where the cells used to wrap onto
  more blocks.
- In both one-row editors `[` and `]` nudge the cell and are what the legend names
  (`OneRowEditor.LESS` and `MORE`, `[` dec and `]` inc), with Up and Down doing the same off
  the legend (`NUDGE_LESS_KEYS`, `NUDGE_MORE_KEYS`), since no row lies below the cursor.
- The Song, Scene and Track pages have a Groove field. The last two are built by
  `screens/groove_choice.py`, stepping through take-from-above, `off` and the names.

## Instruments and the Real Time switch

- The Instruments page (`I`, `InstrumentsPage`, a `NamedListPage`) lists the set's instruments
  with each one's device, channel and uses. `A` adds `instrument 1` and so on
  (`MSG_NEW_INSTRUMENT_NAME`) with no device, and opens the `InstrumentEditor`, a `FieldPage`
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
  Advance, the clip's follow action (`.claude/FORMAT.md`, "Follow action and Launch together").

## Registers

- The Registers page (`R`) edits the current song's four registers as a grid, the user's design: a row for each register and
  a column for each setting, `MSG_REGISTER_COLUMNS` (Allowed inc max, At limit, a `ChoiceField` of `AT_LIMITS` named by
  `MSG_AT_LIMIT_NAMES`, Minimum, Default, Maximum, Reset each scene), the arrows moving over it (`move_in_grid`), `[` and `]`
  adjusting, the cursor's cell in reverse video and its field's label under the grid; each field still carries the
  register's name in its label.
  Lowering Allowed inc max calls `Setlist.hold_adds_within_limits` in the same edit (`set_register_setting`).
- A `FieldPage` taller than the screen scrolls to keep the cursor's field in view (`window_of_lines`).
- The scene page has a Reset field for each.

## Arrange

- There's no Tracks page. The Arrange page's row of track names is reachable by the cursor
  (`HEADER_ROW`), with a `+` after the last name.
- On a track's name: `Enter` opens the track editor, `C` copies the track with its clips to its
  right, `I` inserts a blank track before it, `M` picks it up for Move mode
  (`ArrangePage.MOVE_TRACK`, `start_moving`), Left and Right carrying it (`CARRY_TRACK`, `shift_track`), and `Bksp`
  deletes it after asking.
- On a scene's row: `C` copies the scene below, `I` inserts a blank scene above, `M` on its name
  picks it up for Move mode (`ArrangePage.MOVE_SCENE`), Up and Down carrying it (`CARRY_SCENE`, `shift_scene`), and `Bksp`
  on its name deletes it.
- Move mode, the user's design (`ArrangePage.moving`, `MOVING_SCENE`, `MOVING_TRACK`, `MOVING_CLIP`, `moving_keys`): `M` on
  a clip picks the clip up (`MOVE_CLIP`), and each arrow carries it to the nearest empty cell that way, passing over cells
  that hold clips (`carry_clip`, `CLIP_STEPS`, `Document.move_clip_slot`, which drops a grab as a paste does), the user's
  rule that a clip moves only onto an empty cell; Enter, Esc or `M` drops what is carried (`DROP`); every carry after the
  first continues the edit, so one move is one undo step; the frame is green (`Style.DETAILS_LOCKED`) while it lasts.
  On a list page the same (`ListPage.MOVE`, `CARRY`, `DROP`, `start_moving`, `carry`), the carried row's name drawn
  between `MSG_MOVING_OPEN` and `MSG_MOVING_CLOSE` in place of the spaces beside it. The undo history and the unsaved
  mark compare data with the order of each section's items counted (`same_in_order`, `support/ordered_data.py`), since
  `==` on dictionaries ignores the order a move changes.
- On an empty cell: `Enter` chooses an existing pattern and adds a clip, staying on Arrange, and `B`
  (`ArrangePage.BLANK_PATTERN`, `blank_pattern`) makes a blank pattern named after the track (`lead 1`, a drum pattern on a
  drum track), puts a clip of it there and opens it in the pattern editor, the user's design after Live's empty slot.
- On a clip: `C` copies it for `V` to paste, `Enter` opens the clip page, and `P`
  (`ArrangePage.OPEN_PATTERN`, `open_pattern`) opens the pattern editor on the clip's pattern,
  the user's choice over Shift+Enter, which a stock terminal sends as Enter. `P`
  is bound on a clip alone, so elsewhere it does nothing. `C` means copy everywhere.
- New tracks and scenes are numbered, `track 2` and `scene 2` (`MSG_NEW_TRACK_NAME`,
  `MSG_NEW_SCENE_NAME` in `strings/names.py`), and renamed on their own pages.
- Deleting a scene, track or clip confirms in a dialog, and the last scene or track is refused in
  a message dialog (`ERR_LAST_SCENE_SHOWN`, `ERR_LAST_TRACK_SHOWN`).
- The page has no details line under the grid.
- While the set's Real Time switch is on, the corner over the scene names is a place of its own
  (`on_corner`, the header row at `SCENE_COLUMN`, which `clamp` lets the cursor reach then and
  not otherwise), and Space plays and stops ("Real-time playback" below).

### How Arrange is drawn

- `ArrangeDrawing` (`screens/arrange_drawing.py`) draws the grid, as the pattern editor's
  drawings draw the editor: `ArrangePage` keeps the cursor (`row`, `column`), how far the grid
  has scrolled (`top`, `left`), the keys and what each key does to the song, builds the drawing
  once as `page.drawing`, and `ArrangePage.body` asks the drawing for the lines. `clip_text(clip_slot)`
  there is what a clip says in its cell, the name and a mark for each setting beyond the
  pattern. `test/test_tui_arrange_drawing.py` tests the drawing on its own.
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
- `tui/screens/arrange_details.py` says what it shows, each only when it isn't the default: under a clip's bar,
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
  the same way between its dividers. `test/test_tui_arrange_details.py` tests it.
- Tab, the user's design, in the usual view and the details view alike, on a track's name, a scene's name or a clip
  (`ArrangePage.INTO_DETAILS`, `cursor_cell`, `start_picking`), opens that cell's details if they aren't showing
  (`opened_cell`, the one cell the usual view shows details for, its row and column growing to fit, with no blue
  dividers, which belong to the details view) and locks onto its first line naming something with a page of its own
  (`pickable`, each `DetailLine` carrying a `Target`): a chain, the `+`, or a line naming a scale, an instrument or
  a groove, the user's choice over chains and generators alone. On a track's or a scene's name it opens only that
  name's own details, the user's choice over the whole column or row (`dev_notes/IDEAS.md`). A cell with no details of
  its own shows `stock` in red (`or_stock`, `MSG_DETAILS_STOCK`), in the details view too, and Tab still locks into it
  with nothing picked; an empty clip slot has no Tab. While locked (`locked`, `picked`, `picking`), the cell's box is
  green (`Style.DETAILS_LOCKED`, `Frame.styled`) and the page binds only Up and Down (`PICK_DETAIL`), which pick among
  those lines and stop at either end, Enter (`OPEN_DETAIL`, `open_picked`), which opens the thing's page
  (`DETAIL_PAGES`, or a generator's `EDITOR` through `generator_page_of_kind` in `screens/generator_pages.py`), Tab again
  (`OUT_OF_DETAILS`, `stop_picking`), which leaves and in the usual view closes the cell, `D` (`CLOSE_DETAILS`,
  `close_details`), which leaves and closes every detail, the details view too, and Enter on `+` (`ADD_CHAIN`, `add_chain_to_cell`), which asks for one of the set's chains and adds it to this cell alone,
  `Bksp` on a `chain:` line (`REMOVE_CHAIN`, `remove_chain_from_cell`), which takes it out of this cell alone, the user's
  design, Esc (`ESCAPE_CELL`), which
  leaves the cell as Tab does, since Esc closes the topmost thing (the user's rule); Left and Right do nothing (the user's rules).
  The picked line is drawn in brackets (`MSG_PICKED_OPEN`, `MSG_PICKED_CLOSE`), the user's choice over the triangle,
  which marks play. A page opened so shows Arrange's crumbs first and then the thing's word and name, `ARRANGE ›
  chain: half` (`ShowsNamedItem.opened_from`, `MSG_OPENED_ITEM_CRUMB`), since Esc goes back to Arrange, where the
  cell is still locked. A pick stays within the lines an edit leaves, and leaves when none are left. A scene's details
  are cut to `SCENE_DETAIL_ROOM` so that they never cross the scene column's divider.

## Scene View

- On Arrange, `P` on a scene's name (`ArrangePage.SCENE_VIEW`, `open_scene_view`) opens Scene View, the user's design,
  an Inset Window over the page (`ArrangePage.inset`, laid over the screen by `staged_screen` through `with_inset`)
  holding a `SceneView` (`tui/components/scene_view.py`). While it shows the page binds only `P` (`CLOSE_INSET`), the
  arrows (`INSET_MOVE`), PgUp and PgDn (`INSET_BARS`, `jump_bar`), which jump the cursor to the next bar or back,
  `V` (`TO_PLAYED` or `TO_WRITTEN`), which switches the view, `-` and `=` (`INSET_ZOOM`), `[` and `]`
  (`INSET_SCROLL`) and Esc (`ESCAPE_INSET`), which closes it as `P` does, the user's keys.
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
  choice. `test/test_tui_scene_view.py` tests it.

## The visualizer

- On Arrange, with the set's Real Time switch on, `Z` (`ArrangePage.VISUALIZER`) shows the
  visualizer over the clip area, the user's design (dev_notes/IDEAS.md, "The visualizer", holds
  the plan, built a stage at a time): `next_visualizer` steps through `MODES`
  (`visualizers/modes.py`) and after the last back to the clips. While it shows, the page binds
  only `TO_CLIPS` (Esc, which brings the clips back and stays on the page) and `VISUALIZER`, and
  `show_visualizer` runs a timer that draws a frame every `FRAME_SECONDS` (0.05) until
  `hide_visualizer` stops it, so it costs nothing while the clips show. With Real Time off the key
  isn't bound.
- `ArrangeDrawing.visualized_body` draws the track names and the scene names as ever, the
  divider down every line, and lays the mode's frame (`Visualizer.frame(width=, height=, now=)`)
  over the clip area from `CLIP_AREA_LEFT` and `HEADER_LINES` to the line above the footer with
  `laid_over` (`tui/drawing.py`), with no frame for the cursor. The page passes the seconds since
  the mode began.
- A mode (`visualizers/visualizer.py`) works out only what fits its area and starts again when the
  area's size changes (`resized`), returning big pixels as an array of rows by columns by red,
  green and blue, which `PixelPainter` (`visualizers/pixels.py`) draws as full blocks two columns
  wide and one row tall, one piece of text per run of a colour, each colour's style made once.
  Rich draws them in full colour, or the nearest of 256 or 16 where the terminal shows fewer.
  numpy holds the arrays.
- Each frame hears the notes (`visualizers/heard.py`): Arrange asks `Transport.heard(since=)` for
  the notes that started since its last frame and those still held, by their track's place, with
  the seconds a beat lasts and the beats played, from `Player.heard` and `Score.heard`, which hold
  each clip's notes with their numbers and velocities; only notes that have started are heard, so
  a mode never knows what is coming, and no MIDI is read back. Nothing playing is `SILENCE`.
- The shared pieces every mode can build from: `visualizers/fields.py` (the ripple, soft discs by
  radius, a blur), `visualizers/warp.py` (the rotozoom, through a grid of places kept per size) and
  `visualizers/colour.py` (each track's colour, leaned by pitch and brightened by octave, and the
  `Limiter`, which holds the mean brightness under a level, lets it rise and fall only so fast and
  caps every channel under a ceiling, the user's rule against strobing).
- The lava lamp (`visualizers/lava_lamp.py`): a blob per track that has played, drifting on a path
  of its own, faster for a faster song; a note starting splashes into a ripple field at its blob
  and a held note keeps pushing; the blobs glow into a colour field that fades and bleeds; the
  picture is the colour seen through the water's slope with a soft highlight, turned and zoomed
  with the beat, averaged down from twice the big pixels' resolution and limited. Its amounts are
  the named constants at its top, for the user to tune.
- The spectrum (`visualizers/spectrum.py`), the second mode: a bar per band of pitches, low at the
  left, which a note lifts by its velocity as it starts, and its neighbours a little, holds up while
  held and lets fall steadily, with caps that hang and drop. It draws its own text at the
  characters' resolution rather than big pixels (it overrides `frame`): each bar's top an eighth
  block, coloured up its height from green through yellow to red.
- MilkDrop (`visualizers/milkdrop.py`), the third mode: a feedback picture, each frame the last one
  warped through a table of where each cell comes from (zoomed in, turned, the middle swirled more
  than the edges, rebuilt only when the zoom, which breathes with the beat, moves), faded, blurred,
  and each note splashed in on a slowly turning circle at its track's place and its pitch's, a dot
  while it is held.
- The llamas (`visualizers/llamas.py`), the fourth mode, at the characters' full resolution: an
  ASCII llama for each track that plays (`MSG_LLAMA_SMALL` to `MSG_LLAMA_LARGE`, mirrored to stroll
  the other way), strolling and turning at the edges, bobbing with the beat and hopping on a note,
  its colour drifting around the wheel, its energy rising gently toward what its notes ask and
  fading, which sets its brightness and, no more often than `SIZE_HOLD_SECONDS`, its size.
- The hypercube (`visualizers/hypercube.py`), the fifth mode: a tesseract's sixteen corners turned
  in three planes, faster with the tempo and the tracks' energy, seen in perspective down to two
  dimensions and pulsing with the beat; its thirty-two edges drawn as points along them in the
  colours of the tracks that share them in turn, blurred into a glow under the sharp points, over a
  wash of the playing colours, with a limiter set brighter than the others'. It glows in silence
  too (`DARK_IN_SILENCE` false), as the user wants it bright rather than dark.
- Six more modes, the user's choices, built on autopilot to a like level:
  fireworks (`visualizers/fireworks.py`, big pixels: a rocket per note bursting into sparks held in
  numpy arrays, at most `MOST_SPARKS`); WarpZone (`visualizers/warpzone.py`, half blocks: a ball
  per track at one speed, the tempo's, bouncing off walls and each other, sending rings sliced
  from one distance table); pipes (`visualizers/pipes.py`, heavy box characters, a pipe per track
  laying cells owed by its notes at a pace, fading and starting again when full); plasma
  (`visualizers/plasma.py`, big pixels: four sine waves through a palette blended from the
  playing tracks' colours); maze (`visualizers/maze.py`, light box characters: a maze carved
  depth first on the largest odd area, a walker per track); Mandelbrot (`visualizers/mandelbrot.py`,
  big pixels: the set turning about a point on its edge and breathing in and out, iterated only on
  the points still running, coloured from a vivid palette of the tracks' hues); Mystify (`visualizers/mystify.py`,
  Braille: polygons with trails over a starfield, corners following the notes held); and Laser
  Llama (`visualizers/laser_llama.py`, half blocks with the llama in characters over them: a neon
  sunset over a perspective grid with a haze, after the user's own video backgrounds, the llama
  firing beams on notes). `visualizers/cells.py` draws half blocks, Braille and coloured cells for
  them, each line made in one go from its runs and each style looked up by a packed colour, since
  appending piece by piece was most of a frame's cost. `test/test_visualizer_modes.py` tests what
  each alone promises. After the user watched them: WarpZone is slow and calm in fine Braille
  rings, at most one a track every `RING_GAP_SECONDS`; plasma's palette goes round the tracks'
  hues at full saturation, brighter at the edges; fireworks are crisp points (no blur, each spark one fine
  pixel, taken down by the brightest of each block, `brightest_of_blocks`), bursting around
  `BURST_HEIGHT` (60%) up, a little larger than at first, in `ROCKET_COLOURS` (red, gold, green,
  cyan, blue, magenta and white) by turns, spreading and falling less, with shorter trails, the user's ask; Mystify's polygons are 60% brighter; Cycle moves on every 15 seconds. The
  oscilloscope and the kaleidoscope were built and taken out at the user's ask. Life
  (`visualizers/life.py`): Conway's Game of Life, its cells two characters by one, over a drifting
  gradient of the tracks' colours; a live cell is filled with the inverse of the colour beneath
  and outlined in Braille dots that brighten gently on the beat; it steps on each beat, at most
  `MOST_STEPS_PER_SECOND`, notes seed cells by pitch, and an empty grid is seeded afresh.
- Digital rain (`visualizers/digital_rain.py`), the user's design after the film The Matrix: green ones and zeros
  (`MSG_RAIN_DIGITS`) in coloured cells, a few changing each frame; a note starting sends a stream down the column of its
  pitch, its pale green head as bright as the note is loud and its tail fading, falling `STREAM_ROWS_PER_BEAT` rows a beat;
  the green brightens as more plays, and a sparse dim rain falls in silence. Only green, the heads never white.
- `vivid` (`visualizers/colour.py`) brings a colour to its full value and mixes in just enough white to reach
  `LEAST_LUMINANCE`, its hue kept, since the user found Pipes, Maze, WarpZone and Mystify too dim to read on an iPad or
  iPhone, where a saturated blue or red at full value still looks dark; those four draw their tracks' colours through it,
  Mystify's stars are dimmer and Maze's walls darker, so that what moves stands out.
- Cycle (`visualizers/cycle.py`), last of `MODES`: each mode of `CYCLED` in turn, fresh, every
  `CYCLE_SECONDS` (15, hard-coded for now), answering `shown_name` with the one showing. The order,
  `CYCLE_ORDER`, is shuffled once as the program starts and kept for the whole run, so that each
  recording goes through the modes in an order of its own (the user's ask).
- The piano roll (`visualizers/piano_roll.py`, `piano_roll`), the user's design, second after the spectrum: every key of the
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
  the hidden modes out of its turns. The Set File page's Visualizer field and its Hide Visualizers section, a toggle per
  mode, and the Song page's Visualizer field are `screens/visualizer_fields.py`.
- When the name a mode shows changes (`Visualizer.shown_name`), by the key or by Cycle moving on,
  `ArrangePage.name_to_show` returns it for `NAME_SECONDS` (8), and `ArrangeDrawing.with_name`
  lays it in reverse video, centred over the clip area, `NAME_ROWS_UP` lines from its bottom,
  steady, never blinking, the user's design. `internal_tools/time_visualizer.sh`
  (`internal_tools/time_visualizer.py`) times a frame of each mode with 8 and 64 tracks, small and large.
- `--visualizer NAME` (`Launch(visualizer=)`) opens Arrange with that mode showing and plays, the
  one way Arrange opens on a visualizer; the demo recorder asks clips or a visualizer after its
  checks, or takes `--visualizer` or `--clips`, and `internal_tools/preview_visualizer.py` (`make
  preview-visualizer`) plays a set the same way with no video. `test/test_visualizers.py` tests
  the modes, the drawing and that the lava lamp never flashes, `test/test_tui_visualizer.py` the
  page, and `test/test_tui_playback.py`'s `TestHeard` what the transport hears.

## Track editor and clip page

- The track editor's CC1 Reg to CC4 Reg and Vel Reg fields, after the CC numbers, bind a lane or the velocity to a
  register or `(none)` (`TrackEditor.register_field`, `set_track_cc_register`, `set_track_velocity_register`).
- The track editor's Name field renames. Its Lowest octave and Highest octave fields, in the
  set's octave labels, are the range the piano roll marks (`TrackEditor.octave_field`).
- The clip page, the Scene page and the track editor each have a Chains field
  (`screens/chains_field.py`), which opens a `ChainListPage` (`screens/chain_list_page.py`) on
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
  between the pages and the player (`.claude/FORMAT.md`, "Real-time playback"). It answers
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
- `play_through(page=, play=, said=)` in `screens/shared.py` tells the transport's problem in a
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
- Listening (`screens/listening.py`): `listen(page=, index=, track=, song=, name=)` plays one
  clip on its own and again and again (`forever=True`), asking with a `ChoiceDialog` of the
  set's instruments (`MSG_LISTEN_INSTRUMENT_TITLE`) when the track's instrument has no device,
  and says `MSG_LISTENING`. The clip page's `L` and buttons call it. The pattern editor's `L`
  (`PatternEditor.LISTEN`, `listen_to_pattern`) plays the pattern through the one track that
  plays it, or any of them when they share one instrument, and otherwise asks which track
  (`MSG_LISTEN_TRACK_TITLE`); a track that plays the pattern nowhere gets a scene of its own in
  a copy of the set's song (`listen_through`), so the set is untouched. `L` again, or the Stop
  button, is `stop_listening`.
- Ctrl+T (`everywhere.silence`) says what `Transport.silence_everything()` did: note offs, CC
  123 and CC 120 on every (device, channel) the instruments use among the connected devices
  (`channels_in_use`), `MSG_SILENCED` or `MSG_NOTHING_TO_SILENCE`.
- `test/test_tui_playback.py` tests all of it, with a `Transport` on a `SteppedClock` and a
  `PlaybackEngine` of `RecordingOutput`s in place of the process, and
  `llamatron.tui.transport.output_port_names` patched to two ports of the test's own.

## Patterns

- The Patterns page's `A` offers `pattern 2`, `pattern 3` and so on (`MSG_NEW_PATTERN_NAME`), the way
  new tracks and scenes are numbered.

## The pattern editor

`PatternEditor` (`tui/screens/pattern_editor.py`) shows one of two views of a pattern, the piano
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
- The editor's crumbs say where Esc goes back to. Opened from the Patterns page they are
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

- `GridDrawing` (`screens/grid_drawing.py`) is shared by `PatternDrawing`
  (`screens/pattern_drawing.py`) and `RollDrawing` (`screens/roll_drawing.py`): the header, the
  window of steps that scrolls sideways, the rules, the Step row and the description of the step
  under the cursor. Each drawing is built once by the editor and asked for its body.
- Both views share one label column, `PatternEditor.label_width`, the wider of the two drawings'
  `widest_label` (the rows', sized for every row there could be, and the roll's, worked out from
  the label's parts at their widest by `PianoRoll.widest_row_label`, since a row's label needs a
  note that exists), so that the step columns stay put when Tab switches views (the user's
  choice).
- The header's two lines are cells in aligned columns (`header_cells` in
  `screens/grid_drawing.py`): Steps, Step size, Drum and Direction on the first, and on the
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
- Space or Enter opens or closes a section (`toggle_section`), and PgUp and PgDn move between the
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
  model (`ROW_DESCRIPTIONS` in `composition/row_descriptions.py`, `.claude/FORMAT.md`,
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
  round the cycle, and Space or Enter (`CycleRow.NEXT`, `TOGGLE_KEYS`) goes to the next
  choice. `ChordRow` is the one row where Enter can't cycle, since Enter opens the picker, so
  Space alone is its `NEXT`.
- `RegisterRow`, the `+Note` and `+Vel` rows, is a `CycleRow` of three: add (`+`), subtract
  (`-`) and off (blank), on any step. A cycle starts from the row's blank, which
  `CycleRow.choices` takes from the description, since these rows' blank is 0 where Dot's is
  None.
- Space and Enter are one legend entry on every toggle (`TOGGLE_KEYS`,
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
  editor: three lists in the user's order, the same wherever a chord is chosen, quality, tensions and the borrowed scale type, Tab or Left and Right from
  list to list, Space toggling a tension, the scale list holding the categories of `tui/scale_categories.py` (Common first,
  then every scale type once), each opening a flyout beside it, over the two lists before it, with Space or Enter, where Enter picks and
  goes on to the qualities and Esc or Left closes (a flyout is drawn by the dialog, never a second dialog, the user's rule), and under them what `ChordInWords` (`tui/chord_text.py`) says of the choice, its name in its scale, its
  name in the clip's own scale when it borrows, and its notes. It answers a `ChordChoice`, stored on the step's Chord, Tension
  and Scale rows together, one undo step. `TensionRow` and `ChordScaleRow` are `ChordRow`s with their own choices, in the
  Chord section (`RowSection.CHORD`, the user's design and order: Chord, Tension, Scale and Inversion together, closed at the start
  so that every heading still fits an 80 by 24 console, and left out of a drum pattern, which has none of its rows); the
  Scale row steps through `SCALE_TYPES_IN_ORDER`, every scale type in the categories' order. While the dialog is open the
  pattern editor shows the chord as the choice moves (the dialog's `moved`): the step is written without an undo step and
  written back on Esc, so the whole is one step or none. The roll's thin lines are green (`Style.CHORD_NOTE`) and include
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
`RollDrawing` draws it. `test/test_tui_piano_roll.py` tests it.

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
- `Space` or `Enter` (`keybindings.PianoRoll.PLACE`, `TOGGLE_KEYS`) draws a note of the entry
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
- `K` is the knife (`Pattern.split_note`, giving the step the note's pitch, chord and velocity,
  `SPLIT_ROWS`, and clearing its tie).
- `.` cycles the accidental (`ACCIDENTAL_CYCLE`), and the cursor follows the note to its new row.
- `Bksp` erases the note with its ties (`clear_sound`), and leaves what a rest can hold on the
  step: CC values, Slide and every register row, `+Note` and `+Vel` among them, which the
  rows' descriptions say (`is_kept_by_a_rest`).
- `G` marks the note to grab or unmarks it (`toggle_grab`).
- `H` (`keybindings.PianoRoll.CHORD`, `pick_chord`) opens the Chord dialog, with `(single note)`
  at the top, on the note under the cursor from any of its cells. Enter drew nothing and picked
  the chord until the user made Enter do what Space does, as everywhere else,
  and the picker took the free letter. It refuses an empty cell
  (`ERR_NO_NOTE_HERE`), and takes a note that grabs like any other.
- `E` (`keybindings.PianoRoll.ENTRY_SIZE`, `pick_entry_size`) opens a `ChoiceDialog` of the pattern's entry
  size: the song's first (`MSG_SONG_ENTRY_SIZE_CHOICE`) and then `STEP_SIZE_CHOICES`, opening on
  what the pattern has now (`Document.written_entry_size`).
- The whole-pattern keys `S` and `R` stay. The roll neither inserts nor removes a step, the user's rule, as Live's
  piano roll never did; the rows view does both. `K` and `G` are listed by F1 alone, so that the roll's legend keeps to drawing.

## The one-row editors

- `StepEditor` (`screens/step_editor.py`) is what every editor of steps shares, the pattern
  editor among them: the cursor's `step`, the window's `first_step`, the digits `typed` into
  the cursor's cell with `typed_number(digit=, low=, high=)`, which continues the edit so that
  two digits are one undo step, `keep_step()`, `window_of_steps(shown)`, which scrolls the
  window to the cursor, and `steps_shown_text(first=, last=)`. A page says how many steps
  there are with `steps()`.
- `OneRowEditor` (`screens/one_row_editor.py`), a `StepEditor`, is the offsets editor and the
  groove editor: one row of numbers either side of zero. `OneRowEditor` holds `keys()`, `move`,
  `type_digit`, which keeps the sign, `nudge`, `insert`, `remove_step`, and the drawing both
  share (`steps_shown`, `scroll_to_cursor`, `grid_rule`, `grid_line`, `with_steps_shown`). A
  page names `CELL_WIDTH`, `MOST` (the largest number either side of zero), `MOST_STEPS`,
  `FEWEST_STEPS`, and `INSERT` and `REMOVE`, the page's own bindings for `I` and `D`, and says
  what the row is with `values()`, `set_value(value)`, `add_step()` and `drop_step()`, with
  `can_edit()` for a row that is only shown and `more_keys()` for keys beyond the row's own.
  `keybindings.OneRowEditor` holds Left and Right, Up and Down and the digits. A new one-row
  editor is those few answers and a `body`.
- `test/test_tui_step_editors.py` runs one set of checks on both one-row editors.

## The offsets editor

- An arp's offsets have their own editor (`screens/offsets_editor.py`): a vertical offsets gauge
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
