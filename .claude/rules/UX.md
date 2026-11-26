# How the tracker behaves

The rules for every page, dialog and message of the text UI. Exact layouts and colours are in `.claude/tracker/SHARED.md`,
"Drawing details moved from UX.md". `docs/GETTING_STARTED.md` ("Keyboard Control") tells people the same rules; a change here
changes it too. A new thing looks like the existing thing it is most like.

## Keys and legends

- **Everywhere keys** are Ctrl+ or function keys, never letters: Ctrl+S save, Ctrl+O open, Ctrl+X export, Ctrl+T silence, Ctrl+Z
  undo, Ctrl+Y redo, F1 help, F2 rename (beside `N`), F3 about, Ctrl+C quit at once from
  anywhere with no question, closing FluidSynth and the sender (`quits_at_once` in `interface/tracker/key_table.py`). Quit is
  plain `Q` on the main screen alone; Textual's Ctrl+Q is off. A page's footer shows only its own keys; the F1 dialog lists all,
  the everywhere ones in capitals (SAVE, OPEN, HELP).
- **F1** lists the everywhere keys, a blank line, then the page's keys, in two columns; Tab, Left and Right turn to a panel about
  the page; ENTER, ESC or F1 closes it. F1 and F3 do nothing inside a dialog.
- **One letter, one action**: `N` rename, `C` copy, `M` move, `S` sort, `Bksp` delete, `A` add, ENTER open or choose. Every
  page listing named things has all of them, except the Patterns and Generators pages (grouped and always sorted: no move, no
  sort); a new item is added with `A` and placed with `M`, so list pages have no `I`, which inserts on Arrange and in the step
  editors. Accepted exceptions, each on a kind of page where only one meaning is ever on screen: the main screen's letters,
  which open pages; `M` munge, `S` size and `R` reconfigure in the pattern editor; `S` cell length in the groove and guitar
  bar editors and `R` ready-made in the guitar bar editor; `D` remove step or cell in the step editors and details on Arrange;
  `G` grab, `E` entry size and `H` chord on the piano roll; `V` played in Scene View; `W` when in the chain editor. ENTER
  on a Name field reads `rename`; `edit` is for what opens an editor.
- **No Shift, and no Ctrl or Shift with an arrow**; new keys are plain letters or unshifted marks. Shift+Tab in a grid picker is
  the one exception.
- **`[` dec and `]` inc** wherever a value steps, as two legend entries: on every pattern-editor row, settings pages, the offsets
  and groove editors. On the Chord, #/b, Dot and Use Draws rows they cycle choices, Space or ENTER also stepping forward (Space
  alone on Chord, whose ENTER opens the picker). On the piano roll they are `[` shrink and `]` stretch. `-`, `+` and `=` still
  step, off the legend.
- **Tab moves between the parts of a page, and from the last part back to the first**: completes a search, switches the pattern
  editor's views, turns a grid picker's pages, moves between the Notes page's text and buttons, into and out of Arrange's
  locked cell, and between a settings page's or the song wizard's row of tabs and the box under it. Nothing
  else takes it. A settings page's buttons are reached with Down. Scene View jumps a bar with PgUp and PgDn; inside a tab box
  PgUp and PgDn choose the previous and next tab, keeping the cursor's column where they can; elsewhere they jump between
  section headings.
- **Nobody needs to know a key**: every page with rows has a cursor moved by Up and Down, followed by ENTER, with `▶` on the
  selected row; every key is shown in the legend or, if left off it (`IN_LEGEND`), in F1. Each screen lists its keys once in
  `keys()`. Home and End, and the piano roll's `X` (Split) and `G`, are off the legend.
- **Cursors stop at every edge** and MUST NOT wrap without asking the user (`moves.moved` in `interface/forms/moves.py`).
  Stepping a short fixed cycle MAY wrap, but a chord's quality, tensions and scale, and any new long list, stop at both ends.
  Tab through F1's panels, the Chord dialog's lists and a grid picker's pages MAY wrap.
- **Reverse video is for things that act**: key labels, buttons. An edited or chosen value is marked only with `▶`. Exception:
  a visualizer mode's name, shown for eight seconds near the bottom.
- **Every cursor motion is `move`** in the legend, whichever arrows do it; where Up and Down and Left and Right all move, the
  footer shows one `←↑↓→ move`. Move mode's arrows `carry`, since they move a thing, not the cursor.
- **Legend order**: ESC, the arrows, the keys the page has in all modes, then the rest. A key acting on a step says so in full:
  `insert step`, `remove step`, `insert cell`, `remove cell`. Every legend and help fits 80x24.
- **Space on Arrange** plays and stops while the Real Time switch is on; ENTER stays edit. On the corner over the scene names:
  the song from the top, or stop all; on a scene's name: from that scene, or stop all; on a clip: that clip, or stop its track.
  The mark under the cursor, `▶` or `■`, and the legend say which. A song played from Arrange plays on through every page; edits
  are heard at the song's Live response; only a listening page's preview stops when its page is left; the corner or Ctrl+T stops
  the song. While playing, a track or scene with clips cannot be deleted; anything can be inserted. A start by hand while
  anything plays is at the next bar. A looping clip never holds its scene: the scene ends when its non-looping clips end, and the
  loop stops where the next scene starts on its track; only a scene whose every clip loops waits.
- **True or false** answers to Space and ENTER alike, one legend entry `Space/ENTER` (`TOGGLE_KEYS`): toggle rows, `Toggle`
  fields, a silent step in the offsets editor, the piano roll's pencil, the Use Draws rows' cycle. A picker on the roll takes a
  letter: `H` for the chord, drawing a note at the cursor first on an empty step.
- **Move mode**: `M` picks up a list row, or a scene, track or clip on Arrange; arrows carry it (a clip only into empty cells,
  passing over full ones); ENTER, ESC or `M` drops it; one move is one undo step. A carried name is drawn between `<` and `>` in
  place of its spaces; on Arrange its box is green. Only those keys work meanwhile.
- OK, YES, NO, CANCEL, ENTER and ESC are written in capitals everywhere: buttons, legends, help, messages, documents.
- **ESC closes the topmost thing**, one layer at a time, and never quits: a dialog, an Inset Window, a locked cell, then the page.
  In the song wizard, outside a part's settings, ESC always asks before closing, starting on NO (`ConfirmDialog(starts_on_no=True)`).
- Every list a page adds to has a `+ (New)` row at the bottom, where ENTER does what `A` does.
- **Dialog answers** are boxed buttons (`interface/tracker/components/button_row.py`), the selected one double-lined: Left and
  Right move, ENTER presses the selected one, and ESC is NO or CANCEL. A dialog of OK, or of YES and NO or OK and CANCEL, with
  nothing else to do, has no letter keys, and its buttons show their names alone; a dialog of fields reaches its buttons with
  Down. Only a choice of three, quitting with unsaved changes ("Quit without saving", "Save, then Quit", "CANCEL",
  `QuitDialog`), keeps a letter on each button. The key line under the buttons lists only keys no button shows.
- **A dialog's title is its question**, such as "Delete pattern (tune)?"; the text under it says only what the title does not,
  and a question that says all in its title has nothing under it. A dialog that asks for a name is titled "New" and the kind,
  or "Rename" or "Copy", the kind and the name in parentheses: "Rename pattern (tune)".

## Settings pages

- Up and Down pick a field; `[` and `]` step; ENTER types or chooses; `Bksp` clears. `Bksp`'s legend says what it brings back,
  as the field then shows it: `from song` (or scene, pattern, instrument) for a value from above, `(none)`, or the default value
  itself, such as `127`; `clear` only where the field then shows nothing. Left and Right never step a value on a
  settings page: they only move, along a row of cells, the buttons or the row of tabs, and inside a tab box to the field beside
  in the next column, the nearest by line (a shorter column's last), stopping at the sides. Inside a tab box Up and Down keep to
  a column: at its head Up goes to the column above or the row of tabs, at its foot Down goes to the column below or out of the
  box to what is under it, and Up from under the box comes in at the foot of its first column. In a one-row editor Up and Down
  also step. A value with its own list of choices opens a picker with a letter. A gate is stepped or typed,
  never doubled or halved.
- A blank line above the first setting, after a starting Name, and above the first section. Labels take the width of the longest
  field, shown or not, so opening a section never moves values.
- Settings pages group their fields in tabs and columns; accordion sections stay only on long scrolling pages of rows, such as
  the pattern editor's rows view and the Draws page. A legend lists only the keys that do something where the cursor is.
- Sections like the rows view's accordion: `+ Name` closed, `- Name` open, Space or ENTER toggles, PgUp and PgDn jump, closed
  until opened and remembered by name for the session, `(set)` on a closed heading holding a value.
- Action rows are `Button`s after one blank line below the settings, key reversed then name. Buttons stand in one row where it
  fits, otherwise one per line in brackets, reached with Up and Down. A button deep in a page needs no key; only what is pressed
  often keeps a letter.
- A value from above shows what it takes and where from: `A Minor (from scene)`, `With Scene (from set)`; its picker's first entry
  takes it from above again.
- A field whose ENTER opens a picker (`enter_what` is `What.CHOOSE`) shows a dim `▾` after its value (`MSG_PICKER_MARK`).
- A table-like layout gives each column the room of its heading or widest possible value, every choice included, so columns
  never move.
- A list of a field's values is one list in the values' order, the value from above marked in it (`middle (from genre)`); picking
  it gives the field back; a value identical in effect to the marked one is left out.

## Pickers and lists

- Pickers are sorted by name ignoring case, and stepping a field goes in the same order. Non-name entries (`(none)`, `off`) come
  first in fixed order. A fixed set with its own order (step sizes, directions, export kinds, munges, Reconfigure) keeps it.
- A list's first heading says what choosing picks, never `NAME`: `SELECT PATTERN`, `SELECT CHAIN`, `SELECT FILE`
  (`Column.SELECT_...` in `user_strings/labels.py`).
- A name is at most 30 characters (`MAX_NAME_LENGTH`); lists keep 30 cells for names and the next column starts there. Longer names
  from older files stay, shown cut with an ellipsis. A clip's name may hold up to 60 (`MAX_CLIP_NAME_LENGTH`), such as the
  import's `S01:a1,a2,a3`, and is shown cut at 30 with an ellipsis.
- A list page shows items in the file's order; `S` sorts for good; a picker never changes the order.
- A flyout, a box a dialog draws over itself for a row drawn as a button (`[ Common ]`), offers a second level without a dialog
  over a dialog, which is avoided. Windows stacked several deep cascade down and to the right. A window leaves a blank line above
  its bottom edge.
- A picker opens on the current choice and leaves out what would mean nothing, like the pattern itself in Load over.
- A picker searches as you type: `search: ba`, Bksp erases, Tab completes as far as all agree, ENTER picks, ESC cancels.
- A list page searches with `/`: status shows `/ba`, Bksp, Tab completes, ENTER keeps the cursor and shows all again, ESC puts it
  back. Every page's help mentions it.

## Names the tracker makes

All made by `model/objects/naming.py` (`tests/model/test_naming.py`):

- Lowercase, underscores for spaces (`c_major`), except a note's name in a scale's name (`C_major`, `F#_harmonic_minor`).
- A new thing is its kind's word, a dash and one more than the highest number in use: `pattern-1`, `scene-1`, `scale-1` (a scale is
  never named after its notes, except by an import). A blank pattern made on Arrange takes its track's name: `lead-1`.
- A copy or clash counts: `foo` gives `foo-2` (never `foo-1`); a name ending in a number counts up, keeping its joiner (`bass-2` to
  `bass-3`, `name1` to `name2`, `bass 2` to `bass 3`); never a number after a number.
- Names compare without regard to case and are kept as typed; a file holding both still opens. Taken means anything it could be
  confused with. Existing names in a file stay as written.

## Dialogs and the status line

- A dialog asks one thing; ENTER answers, ESC cancels, nothing changes until answered.
- Deleting anything in use is refused with up to five uses listed; otherwise it confirms. Deleting a scene, track or clip always
  confirms; the last scene and track of a song are refused in a dialog. Saving and quitting with unsaved changes ask first;
  nothing is saved or exported unasked.
- Opening a file never changes it. A file with values out of range opens only after a dialog lists what each becomes, and YES
  opens it unsaved. The command line refuses to export such a file without `--force`.
- The status line, one dim line above the legend: what the last key did when not obvious, where a save or export went, what an
  undo undid, why a key did nothing; the next key clears it. A refusal is amber. A message needing an answer, or that must not be
  missed, is a dialog.
- A status message is a lower-case fragment with no full stop (`saved to first.yml`), keeping only typed names' and key names'
  capitals. A dialog message is a sentence. A raised error is a lower-case fragment, with its place put in front of it.

## Wording

- A bad value: `x must be ..., got value`; a wrong type: `expected a Note, got value`; only the value after `got` keeps its repr.
- Names in parentheses, `no pattern called (tune)`, never quotes.
- Lists joined with commas by `listed()` in `model/file/checks.py`; choices are listed only for fixed sets (`expected one of: AX,
  BX, CX, DX`).
- Say `integer`, `true or false`, `directory`, `scale type`, `clip`, `export`, `cannot`; never `like` (use `such as 1/8`). An empty
  field shows `(none)`; a sentence says `no scale`. Counts are numbers.
- Text is formal, exact and as short as it can be while obvious: no chatty phrasing, no caption repeating a title, no word leaning
  on assumed knowledge ("usual", "go back to"). Choices read the plainest way a person says them: "only this section", "going
  forward". Mockups and proposed wording follow the same rules and the tracker's existing style.

## Drawing

- Bold, dim, reverse video, box characters and `▶`, because terminal backgrounds differ; everything fits 80x24. Colour only where
  `.claude/tracker/SHARED.md` lists it; the visualizer never strobes or flashes.
- Where lines cross or meet, the joint is the box character joining them with the right arms, breaking neither line (a plain beat
  edge crossing a dim rule meets it in a plain joint). Check every crossing by rendering before showing the user.
- A double-lined box is never bold, since many fonts draw bold double-line characters short of the corners; what it holds MAY be
  bold (`Style.SELECTED_EDGE`).
- Bars are block characters; an on toggle is `●` (ties and glides too); a cell that cannot take a value is a light `/` (never on
  the Use Draws rows).
- Every page but Arrange has a theme stripe by its kind in place of the header's rule.
- The crumbs say where ESC goes back to; a page reached two ways shows two trails: `PATTERNS › tune`, `ARRANGE › pattern: tune`,
  `ARRANGE › clip: (scene 1, lead) › pattern: tune`. A page that jumps elsewhere gives the opened page its crumbs.
- An Inset Window is a read-only window over a page, closed by its key or ESC. `P` is the one key for looking inside things.
- The song wizard is a row of tabs, Genre, Band, Composition, Form and Apply, over a box: a tab with parts lists them at the
  left of the box, each shown, its own fields first, and the settings of the part under the cursor at the right; `< Back` and
  `Next >` at the foot of the box, showing their keys PgUp and PgDn, open the tab before and after, the last tab having Back alone; Apply is a button after the Apply tab's summary. A tab not ready yet is dim and says
  why in its box.
