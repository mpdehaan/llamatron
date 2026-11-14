# How the tracker behaves

The user's rules for what every page, dialog and message of the text UI does, kept apart from the
rules for the code (`.claude/STYLE.md`) and the notes on how each page is built
(`.claude/TRACKER.md`) so that they can be reviewed on their own. `CLAUDE.md` imports this file,
so it's in force in every session. What each rule replaced, and when, is in `.claude/DECISIONS.md`. `docs/GETTING_STARTED.md` tells people the same rules in its own words, under
"Keyboard Control", and a change here changes it too. Consistency and usability matter
more to the user than novelty: a new thing looks like the existing thing it's most like, and where
a feature that already exists does what's being asked, that's pointed out first
(`.claude/COMMUNICATION.md`).

## Keys and legends

- Anything that works on every page is a Ctrl+ key or a function key, never a plain letter, so
  that a page's letters stay its own: Ctrl+S save, Ctrl+O open, Ctrl+X export, Ctrl+T silence
  (the emergency stop for real-time playback), Ctrl+Z undo, Ctrl+Y redo, F1 help, F3 about and Ctrl+C,
  which quits at once from any page or dialog, even while typing, with no question about unsaved changes, closing
  FluidSynth and the Realtime Sender Process as quitting does (the user's ask; `quits_at_once` in `tui/key_table.py`). Quit is the plain `Q`, on the main screen alone, because
  Ctrl+Q was awkward to type and nobody needs to quit from inside a page; Textual's own Ctrl+Q is
  switched off. A page's footer shows only its own keys, so
  that it stays short and leaves the page its room: the main screen has a cell for Save, Open,
  Export and Import, in the row under the pages, where Open, Export and Import show the plain
  letters `O`, `X` and `M`, which work on that screen alone to save a keystroke (Save stays
  Ctrl+S, since `S` is Songs), and F1 and F3 in its footer, and the F1 dialog, which
  every page opens, lists them all. Undo and Redo have no cell, since they're Ctrl+Z and Ctrl+Y
  everywhere, and F1 is where they're listed. Nothing reminds you of F1 and F3 on the other
  pages, by the user's choice, since two keys are easy to remember. In the F1 dialog they're
  written in capitals (SAVE, OPEN, HELP), the one exception to lower-case legends (`render MIDI`
  keeps its proper noun).
- F1 opens a dialog of every key that works on the page: the everywhere keys at the top, a blank
  line, then the page's own keys, each group in two columns like the main menu's rows. Tab, Left
  and Right turn to a second panel saying what the page is about, and back; Enter, Esc or F1
  again closes it, and the dialog doesn't list F1 among the keys, so that Undo and Redo sit in
  one column, Ctrl+T taking the last place of the first. F3 opens About (F2 renames, as on Windows, the user's choice, beside `N`, since a stock Mac needs fn for F2): the cow, the version and build date, the links, a quote and the license.
  Neither works inside a dialog, which has its own keys.
- The same action takes the same letter on every page that has it: `N` rename, `C` copy, `M`
  move, `S` sort, `Bksp` delete, `A` add, `I` insert, `Enter` open or choose.
  Every page that lists named things has all of them. A name is renamed and anything more
  complex is edited: Enter on a Name field reads `rename` on every page, and `edit` is for
  what opens an editor.
- No key needs Shift, since `+` and `*` need Shift on a US keyboard,
  not every terminal sends Shift with an arrow, and macOS keeps Ctrl with an arrow for itself. `[`
  means dec and `]` means inc wherever a value steps, the user's one adjust system and the
  user's two words: on every row of the pattern editor the legend lists `[` dec
  and `]` inc as two entries, a number down and up, a gate shorter and longer, and on the
  Chord, #/b, Dot and register rows a cycle of choices back and forward, where Space or Enter
  also goes to the next choice (Space alone on Chord, whose Enter opens the picker). On the
  settings pages and in the offsets and groove editors they step the value under the cursor,
  with the same two legend entries, `[` dec and `]` inc, the user's choice over
  the legends `←` dec and `→` inc and `↑↓` adjust. On the piano roll `[` and `]` drag a note's
  end a step earlier and later, as `[` shrink and `]` stretch, the user's words for a note,
  which is not a number, where the legend read `[/]` length. `-`, `+` and `=` still step a value, off the legend. No page binds Shift or Ctrl
  with an arrow, and a new key is a plain letter or an unshifted mark. Shift+Tab, which goes back
  through a grid picker's pages, is the one exception, since Tab alone reaches every page.
- Tab means the next part of a page (the user's rule): it completes a search, switches the pattern editor's views and turns
  a grid picker's pages, and nothing else takes it; Scene View jumps a bar with PgUp and PgDn instead. A settings page's
  buttons are reached with Down from its last field, never with Tab (the user's design).
- Nobody has to know a key to get around: every page with rows has a cursor that Up and Down move
  and Enter follows, and the selected row carries the triangle `▶` at its left, on the list
  pages, the settings pages and the pickers alike, so that the arrows show themselves. The main
  screen is a grid of cells, the pages four to a row and then Save, Open, Export, Import and Quit, which
  all four arrows move over and Enter opens, with the selected cell alone drawn in a box, its
  name bold, the one sentence shown being the selected cell's, and a count on each cell
  whose page is a list. The letters are for people who know them, and the grids are the
  exception, with keys of their own: the pattern and groove editors mark the cursor's cell in
  reverse video, the offsets editor's gauge marks the cursor's column at both ends, `<<4>>`
  around the step number and `<+7▲>` around the offset, in reverse video too, the piano roll stands the cursor's cell between two bold double bars, shading the note under
  it (`▓▓▓▓▓`) or reversing the blank of an empty cell, since reverse video on a solid bar is
  blank and the shading alone was hard to find, with the rule beside the cursor's row meeting the bars in double-armed
  joints, a note that an inversion plays an octave up drawn hollow (`░░░░░`, and `▒▒▒▒▒` under the cursor), and Arrange draws a
  double-lined box around the clip, scene, track or `+` under the cursor, because its cells hold
  bars that reverse video would hide. Every dialog's answers are boxed buttons, as a real window's (`tui/components/button_row.py`, the user's design): each
  key reversed and then its name, the selected button double-lined, Left and Right moving between them and Enter pressing,
  each button's key answering at once; a message has one OK, a Yes or No question Yes and No, and quitting with unsaved changes
  "Quit without saving", "Save, then Quit" and "Cancel" (`QuitDialog`), the user's words.
- A cursor stops at every edge and never goes round: Left on the first step, Right on the last,
  Up on the top row and Down on the bottom row stay where they are, on every page, dialog and
  picker alike (`cursor_moved` in `tui/key_table.py` is the one place that moves one), because an arrow held down should fly to the end and stay there, the way a
  pointer flies to the edge of a screen, and going round breaks that. Nothing may wrap a cursor
  from one edge to the opposite one without asking the user first. Stepping a value through a
  fixed cycle of a few choices, like the #/b row's `]` or a field's Left and Right, is not a cursor
  and may go round, but a chord's quality, tensions and scale stop at the first and the last choice on every page that steps
  them (the user's rule, who dislikes going round in such widgets, so a new long list of choices stops too). Tab through the F1 dialog's panels, the Chord dialog's lists and a grid picker's pages may go round.
- Reverse video is for things that act: the key labels in menus and legends, the Save, Open and
  Export buttons, which are also reversed when selected, and the Yes and No buttons. A value or a
  row that's only being edited or chosen is never reversed, only marked with the triangle. The
  one exception is the video tutorial's caption strip, bold black on white at the foot of the
  screen, the page moved up to make room, which only the tutorial shows, so that a video's captions
  stand out (the user's choice); the other is a visualizer mode's name, shown in reverse
  video near the bottom of the clip area for eight seconds when the mode changes.
- Each screen lists its keys once in `keys()`, which both handles and draws them, so no key can
  work without being shown in the legend or, for a key left off the legend to keep it short, in
  the F1 dialog, which lists every key: Home and End, and on the
  piano roll `K` and `G` are the ones left off
  (their class's `IN_LEGEND` in `tui/keybindings.py` leaves them out), so that the roll's legend keeps to drawing. A key that acts on a step is named in full, `insert step` and
  `remove step`, and on a groove's cells `insert cell` and `remove cell`. Every page's legend and
  help fit an 80 by 24 console.
- A legend reads in one order on every page: Esc first, then the arrows, then the keys the page
  has in all of its modes, then the rest, so that the same key is found in the same place.
- Space on Arrange plays and stops, read from where the cursor is, while the set's Real Time
  switch is on, and Enter stays edit: on the corner over the scene names Space plays the song
  from the top or stops everything, on a scene's name it plays from that scene or stops
  everything, and on a clip it plays that clip alone or stops its track. The mark under the
  cursor, `▶` or `■`, says which Space will do, and the legend names it. A song played from
  Arrange plays on through every page, Esc to the main screen included, so that it can be edited
  as it plays, and every edit is heard on what plays at the moment the song's Live response says;
  only a listening page's preview stops when its page is left, and Space on the corner or Ctrl+T
  stops the song. While it plays, a track or scene with clips can't be deleted, and anything can
  be inserted. A start by hand while anything plays is always at the next bar, and a
  looping clip never holds its scene: the scene is done when its clips that don't loop have
  finished, and the loop stops where the scene below starts on its track, so Space on the
  corner plays every demo to its end, and only a scene whose every clip loops waits for the
  human. The user's design and rules.
- Anything that's true or false answers to Space and Enter alike, as one legend entry, `Space/Enter`
  (`TOGGLE_KEYS`): the pattern editor's toggle rows, a settings page's toggles, which are the
  fields of the kind `Toggle`, and a silent step in the offsets editor, so that either
  habit works and no page has to be learnt on its own. The piano roll's pencil and the
  register rows' three-way cycle answer to both the same way, so a picker on the roll takes a
  letter, `H` for the chord.
- Move mode, the user's design: `M` picks up what the cursor is on, a row of a list page, or a scene, a track or a clip
  on Arrange; the arrows carry it, a clip only into an empty cell (the user's rule), passing over cells that hold clips;
  and Enter, Esc or `M` again drops it where it is, every carry of one move making one undo step. A carried row's name is
  drawn between `<` and `>`, which take the places of the spaces beside it so that nothing shifts, and on Arrange the box
  around what is carried is green. While it is carried, only those keys work.
- Upper and lower case are the same key, and `Bksp` and `Delete` are the same key.
- Esc closes the topmost thing, one layer at a time, and never quits, so that Esc gets you out of anything: a dialog
  it cancels, an Inset Window or a locked cell it closes, and a page it goes back from (the user's rule); the legends say so. Tab never goes back: it switches the pattern editor
  between the piano roll and the rows, it cycles a grid picker's pages, with Shift+Tab going the
  other way, it completes typed text in a picker or a list search, and it moves between the
  Notes page's text and its Save and Cancel buttons. Anything with more than one mode or
  page switches with Tab. PgUp and PgDn jump between the pattern editor's section headings.
- Every list a page can add to has a `+` row at the bottom, where Enter does the same as `A`.
- A settings page leaves a blank line above its first setting, another after a Name that starts it, and another above its first section, and its labels take
  the width of the longest of every field, shown or not, so that opening a section never moves the values (the user's rules).
- A choice field whose value comes from above shows the value it takes and where from, in plain text, like `A Minor (from
  scene)`, `forward (from pattern)`, `down (from track)`, `With Scene (from set)`, and its picker's first entry takes it from
  above again (the user's design).
- A settings field whose Enter opens a list of choices, its `enter_what` being `What.CHOOSE`, shows a dim `▾` after its
  value (`MSG_PICKER_MARK`), the user's choice, so that it isn't taken for a field that's typed.
- On a settings page, Up and Down pick a field, `[` and `]` make a value less and more, as the
  legend names them, `[` dec and `]` inc, with Left and Right doing the same off the legend,
  Enter types or chooses, and `Bksp` clears. In a one-row editor, the offsets and groove
  editors, `[` and `]` make the cell's value less and more with the same two legend entries,
  and Up and Down do the same off the legend, since no row lies below the cursor. A value with a list of choices of its own, like the piano roll's entry size, opens a
  picker with a letter rather than stepping. A gate is stepped with `[` and `]` or typed with
  Enter, with no keys to double or halve it. A settings page with many settings groups some into sections, as the rows view's accordion:
  `+ Name` closed and `- Name` open, `Space` or `Enter` on the heading toggling it, `PgUp` and
  `PgDn` jumping between headings, closed until opened and remembered by name for the session,
  a closed heading saying `(set)` when anything inside holds a value (the user's design). Action rows are `Button`s, drawn below the settings after
  one blank line, the key's name in reverse video and then the button's name, so that what edits
  the set and what acts on it never run together.

## Pickers and lists

- A picker, any dialog that offers a list of things to choose from, shows them sorted by name,
  ignoring case, and arrows that step through the same choices on a field step through them in the
  same order. Entries that aren't names, like `(none)`, `use the song's` or `off`, come first, in
  their fixed order. A fixed set with an order of its own, like step sizes, directions, export
  kinds, munges or the pattern editor's Reconfigure choices, keeps that order.
- A list's first column heading says what choosing a row picks, the user's design, never `NAME`: `SELECT PATTERN`,
  `SELECT CHAIN`, `SELECT ARPEGGIATOR` (the kind's name on a generator page), `SELECT GENERATOR TYPE`, `SELECT CHAIN LINKS
  (generators)` in the chain editor and `SELECT FILE` on the Open page (`Column.SELECT_...` in `strings/labels.py`).
- A list page shows the set's items in the file's order, which is the order they play or are
  written in, and `S` sorts them for good. A picker never changes the file's order.
- A flyout, the user's design and name, is a box a dialog draws over itself for a row drawn as a button, `[ Common ]`, since the row opens something, listing that row's
  choices (the row whose choice was made shows it after a `▸`, `[ Common ▸ Major ]`, and no other row carries the mark), as large as the dialog and two cells down and to the right of it, covering what lies under it, so that the two read
  as a stack to attend to (`Dialog.flyout_lines`, `FLYOUT_SHIFT`): Space or Enter on the row opens it, Up and Down move, Enter picks and closes it, and Esc or Left closes it with
  nothing changed. It is how a dialog offers a second level without opening a dialog over a dialog, which is avoided (the
  user's rule). The Chord dialog's categories of scale types are the first.
- A picker opens on the current choice, and the thing being edited is left out where choosing it
  would mean nothing, like the pattern itself in Load over.
- A picker searches as you type: the list shrinks to the names that contain the typed text,
  ignoring case, shown as `search: ba` above the list, Bksp erases, Tab completes as far as every
  remaining name agrees from its start, Enter picks, and Esc cancels.
- A list page searches with `/`, since its letters are keys: the rows shrink to the ones
  containing the typed text, the status line shows `/ba`, Bksp erases, Tab completes, Enter keeps
  the cursor where the search put it and shows the whole list again, and Esc puts the cursor back
  where it was. Every page's help mentions it.

## Dialogs and the status line

- A dialog asks one thing. Enter answers, Esc cancels, and nothing changes until it's answered.
- Deleting anything still used is refused with up to five uses listed, and otherwise confirms.
  Deleting a scene, a track or a clip always confirms, and the last scene and the last track of a
  song are refused in a dialog.
  Saving and quitting with unsaved changes ask first; nothing is saved or exported unless asked.
- A set file is never changed by opening it. A file that holds values out of range opens only
  after a dialog lists what each becomes, a few at a time and each cut to fit, and Yes opens the
  set unsaved. The command line refuses to export such a file without `--force`.
- The status line draws a refusal or problem in amber (`Page.refuse`, `Style.REFUSAL`) and every other note dim, and a
  question about deleting has its title in red (`Style.DELETE_TITLE`), the user's design and the sixth allowance of colour.
- The status line, one dim line above the legend on every page, says what the last key did when
  that isn't obvious, where a save or export went, what an undo undid or why a key did nothing,
  and the next key press clears it. A message that's a note goes there; a message that needs an
  answer, or that the user must not miss, is a dialog.
- A message on the status line is a lower-case fragment with no full stop, like `saved to
  first.yml` or `undone: pattern (bass)`, keeping only the capitals of names the user typed and of
  key names like Tab. A message in a dialog is a sentence with a capital and a full stop. A raised
  error is a lower-case fragment with no full stop, because the place it happened is put in front
  of it, like `scene entry 2, track (bass): repeat must be an integer from 1 to 9999, got 0`.

## Wording

- A bad value reads `x must be ..., got value`, never `invalid x: value (must be ...)`, and a
  wrong type reads `expected a Note, got value`. Only the value after `got` keeps its Python repr,
  since there it shows the type.
- A name is written in parentheses, like `no pattern called (tune)`, never in quotes, which read
  like air quotes.
- Lists are joined with commas by `listed()` in `composition/checks.py` and never shown as Python
  lists, and a list of choices is given only for a fixed set, like registers or settings
  (`expected one of: AX, BX, CX, DX`), never for things people name.
- Say `integer` rather than `whole number`, `true or false` in lower case, `directory` rather than
  `folder`, `scale type` rather than `kind`, `clip` rather than `cell`, `export` rather than
  `render`, and `cannot` rather than `can't`. Don't write `like` in a message; where an example
  really helps, as for fractions, write `such as 1/8`. A field with no value shows `(none)` while a
  sentence says `no scale`.
- Documents for people use the names the tracker shows, never code names that differ.
- These rules come from reading the modules of `src/llamatron/strings/` together, and a new message
  is checked against them before it's added.

## Drawing

- The tracker draws with bold, dim, reverse video, box characters and the one triangle `▶` that
  marks the selected row, because terminal backgrounds differ, and everything fits an 80 by 24
  console. The one exception is colour for the lights of real-time playback, allowed by the
  user for these alone: the red `■` on a playing clip and a green `●` after a
  track's name while a note sounds on it (`Style.PLAYING`, `Style.SOUNDING`). The shapes change
  too, `▶` to `■` and the dot appearing, so that the state shows without the colour. The title
  on black that the start screen, the recordings' splash and the batch videos show
  (`tui/components/title_card.py`) is all in blue, block letters, scanner, address and prompt, the
  user's design after a classic video game's start page; the user wants the questions of a colour
  mode for the rest explored as the demos are built (`dev_notes/IDEAS.md`). The
  visualizer (`visualizers/`), shown over Arrange's clip area while a song plays in real time, is
  the other place colour is allowed, the user's design, and it never strobes and
  never flashes brightly, since some people are sensitive to that: brightness rises and falls
  gently, a limiter holds the whole picture down as more plays, and nothing jumps to white.
  The piano roll's read head, a thin line on the step that sounds while the pattern plays, is light yellow (`Style.READ_HEAD`), the user's
  design, and is never drawn over a note's bar.
  The piano roll's thin lines of a chord's other notes are green (`Style.CHORD_NOTE`), the user's design, so that they stand
  apart from the notes written.
  Arrange's details view (`D`) is the third, the user's design, and only for what it lists:
  its dividers in blue (`Style.DETAILS_DIVIDER`), so that the view shows itself, each chain
  and generator in green (`Style.DETAILS_GENERATOR`), the box around a cell Tab has locked into in
  green (`Style.DETAILS_LOCKED`), and `stock`, a cell with no details of its own, in red
  (`Style.DETAILS_STOCK`). Scene View is the fourth: each track's notes in a colour of its own, tracks at
  once two colours in one cell, its legend in the tracks' colours, and its Inset Window's border purple while
  it shows the patterns as written and the splash's blue while it shows them as played.
- An Inset Window, the user's design and name, is a read-only window over a page, `INSET` (4) cells in from
  every edge: a solid band of a colour the view chooses, drawn as spaces on that background so that it joins from
  line to line, outlined in white one cell further out, its closing key's name in reverse video in the band's bottom
  corner, and inside the band, one cell in on every side, the title in reverse video and then the view
  (`tui/components/inset_window.py`).
  The key that opened it closes it, and so does Esc, which closes the topmost thing on every page, so that a second Esc goes
  back from the page as ever; the page's legend lists the window's keys. Scene View is the first; the list
  previews are to come with `P`, the one key for looking inside things across the tracker (the user's rule). Where two lines cross or meet, the joint is the box character that joins them, a tee
  or a cross with the right single or double arms, in a style that breaks neither line: a bold
  beat edge crossing a dim rule meets it in a plain joint, since a bold joint broke the rule and
  a dim one broke the edge. A change to anything drawn with lines is checked at every crossing,
  rule and edge, by rendering it and reading it, before it's shown to the user. Bars are drawn with block characters, as Arrange's lengths and the pattern editor's
  Degree gauge are, a toggle that's on is `●`, a tie and a glide included, never a letter or
  `*`, and a cell that can't take a value, which the render would ignore, is a light `/`; the
  register rows are never such a cell, since no register setting is locked out for want of a note.
- Every page but Arrange has a theme colour by its kind, the main screen's white, the user's design, a solid stripe in place of the
  header's rule (`.claude/TRACKER.md`, "The header and the crumbs"); the stripes are the fifth allowance of colour.
- The header is two lines over the rule or the theme's stripe, the user's design of keeping what matters in the corners: the
  first line has the crumbs, the page's own path, which change with every page, in its left corner, llamatron centred, and the
  open set and the save mark at the right; the second has the current song and the length at the right. The set and the song
  are one block, left-justified and as wide as it needs, just left of the save mark and the length, so that llamatron stays
  exactly centred, giving way when the crumbs or the block need its room. The save mark is `● unsaved` for a set that has no
  file yet, `● unsaved changes` for a set changed since its file was written or read, and `○ saved` otherwise. The theme's stripe
  carries the page's caption, black on a light theme and white on a dark one: a list's name, like `PATTERNS`, or what an editor
  edits, like `EDITING PATTERN: tune`. The version is shown by F3 alone.
- The crumbs say where Esc goes back to: every crumb but the last is a page on the way back, so
  a page reached two ways shows two trails. The pattern editor reads `PATTERNS › tune` from the
  Patterns page, `ARRANGE › pattern: tune` from a clip on Arrange and `ARRANGE › clip: (scene 1,
  lead) › pattern: tune` from the clip page, never `PATTERNS` where the Patterns page is not on
  the way back (the user's rule). A page that jumps somewhere else gives the page
  it opens its own crumbs to put first.
- There are no tooltips and no mouse.
