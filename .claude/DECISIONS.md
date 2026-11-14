# Decisions, and what was tried first

The history behind the tracker and the format: what the user chose, what it replaced or was
chosen over, and why, with the date. `CLAUDE.md` doesn't import this file, so it isn't in a
session unless it's read. Read the section for a thing before proposing to change it, so that an
idea the user already tried and dropped isn't proposed again. The rules themselves are in
`.claude/UX.md`, and how each page is built is in `.claude/TRACKER.md`. Those two say what is
true now, and this file says how it came to be.

A new decision is added here when the user makes one, under the topic it belongs to: what was
chosen, over what, why, and the date.

## Keys

- **No key needs Shift** (2026-11-09). `+` and `*` need Shift on a US keyboard, not every
  terminal sends Shift with an arrow, and macOS keeps Ctrl with an arrow for itself: Mission
  Control's hotkeys were found enabled on the user's Mac, so Ctrl with an arrow never reached the
  terminal. `[` and `]` took over from `+` and `-` as the legend's keys for less and more, and
  `-`, `+` and `=` still work, off the legend. Shift+Tab in a grid picker is the one exception,
  since Tab alone reaches every page.
- **What went with Shift** (2026-11-09). The gate's `*` and `/` to double and halve it, the
  roll's octave jump on Shift+Up and Shift+Down, and the bar jump on Shift+Left and Shift+Right in
  both views of the pattern editor were all taken out rather than moved to other keys. A gate is
  stepped with `[` and `]` or typed with Enter.
- **`A` adds on every list and on Arrange** (2026-11-09), where `+` added before. On Arrange `U`
  and `D` move a scene up and down, as they move a row on a list page, and `[` and `]` move a
  track left and right.
- **The entry size is picked from a list with `E`** (2026-11-09), over stepping through the sizes
  with a key each way.
- **A cursor stops at every edge and never goes round** (2026-11-09), because an arrow held down
  should fly to the end and stay there, the way a pointer flies to the edge of a screen. The main
  screen's cursor had already been chosen to stop at its edges on 2026-11-08, over going round.
- **Space and Enter both toggle** anything that's true or false (2026-11-08), as one legend
  entry, so that either habit works.
- **`U/D` is one legend entry** on the list pages (2026-11-08), to shorten the legends.
- **Reconfigure gathers the whole-pattern actions under `R`** (2026-11-08): munge, load over,
  step size, time signature, drum on or off, direction and rename each had a letter of their own
  before, and the user asked for a shorter legend.
- **The roll's legend keeps to drawing** (2026-11-09): `I`, `D`, `K` and `G` work on the roll but
  are listed by F1 alone.
- **PgUp and PgDn jump between section headings** (2026-11-08), so that Tab could switch between
  the roll and the rows.
- **Quit is the plain `Q`, on the main screen alone.** Ctrl+Q was awkward to type and nobody
  needs to quit from inside a page. Quitting with unsaved changes offers quit without saving first
  and as the default, because Quit is never an accident.
- **Nothing reminds anyone of F1 and F2** on pages other than the main screen, by the user's
  choice, since two keys are easy to remember.
- **Keys that step one way or the other are bound with their direction** (2026-11-09, `Steps`).
  Before, each handler asked which key had been pressed, so changing a key meant finding every
  handler that named it.
- **Every key binding lives in one module** (2026-11-09, `tui/keybindings.py`), one class for
  each page, dialog and component, named after it, each binding a tuple of the key or keys, the
  name shown and what the key does. Before, `tui/keys.py` had a class of key names for each page
  and each page gave a key its label and its words where it bound it, so a key's whole meaning was
  in three places. The tuple of three parts is the user's design, accepted for now. The legends
  and the F1 dialog were compared before and after at every cursor place and didn't change.

## The main screen and the dialogs

- **The pattern editor's two views share one label column, and its header is aligned cells**
  (2026-11-09). The roll's labels like `G3   5` had a column of their own, eight wide against
  the rows' sixteen, so Tab moved every step column; now the roll takes the wider width. The
  header's lines were two strings with four spaces between the parts, so Time sat under the
  middle of Steps; now each column is as wide as its wider cell, Time under Steps, Scale under
  Step size, Entry under Drum. `(the song's)` became `(song's)` and the varying scale's note
  lost its second half so that both lines fit an 80-column console.


- **`[` dec and `]` inc are the legend's words everywhere a value steps** (2026-11-09): the
  settings pages read `←` dec and `→` inc, the offsets and groove editors `↑↓` adjust and the
  piano roll `[/]` length, and the user asked for one adjust system named one way. The arrows
  still work on those pages, off the legend, and the help texts still say so. On the piano
  roll the user then chose `[` shrink and `]` stretch, since a note is not a number.


- **`P` jumps from a clip to its pattern's editor** (2026-11-09), on Arrange from the clip under
  the cursor and on the clip page from any field, since the page has one pattern. Shift+Enter
  was asked about first and rejected: a stock macOS terminal sends it as a plain Enter, and no
  key needs Shift. The editor's crumbs then start with the opener's, `ARRANGE › pattern: tune`,
  because the crumbs say where Esc goes back to, and the Patterns page is not on that way.


- **The main screen has nothing between the rule and the cells** (2026-11-09). Two lines sat
  there, `set: first | song: verse` with the web address at the right, and `120 BPM   C Major
  2 tracks   2 scenes`. The first repeated the crumb, and the cells count the set's things, so
  the user dropped both; the tempo is to be shown on Arrange some day.
- **The crumb names the set**, `set: first.yml, song: verse` and `set: (unsaved), song: verse`
  (2026-11-09), where it read `first.yml, song: verse` and `(unsaved), song: verse`, because
  the set is what is saved, not the song.
- **The header is two lines** (2026-11-09): the program's name with the set and the song, and
  the save mark, on the first, and the crumbs with the time on the second, with `MAIN SCREEN` on
  the main screen rather than a blank. One line held the title, the set crumb and the trail,
  and once the set crumb named the set, the arpeggiator editor's name fell off an 80-column
  console. The user chose the second line over shortening the generator crumbs or cutting the
  trail from the left. The save mark is always there: `● unsaved` for a set that has no file
  yet, `● unsaved changes` for a saved set changed since, and `○ saved` otherwise. With that
  mark the first line was too tight for `minimal_techno.yml` at 80 columns, so the version
  left the header for the About dialog and the time moved beside the crumbs, the user's
  choice over an ellipsis on long names.



- **`O` opens and `X` exports on the main screen** (2026-11-09), without Ctrl, to save a
  keystroke, since that screen's letters are its own. Ctrl+O and Ctrl+X still work everywhere,
  and Save stays Ctrl+S because `S` is Songs.


- **F1 closes the F1 dialog and isn't listed in it** (2026-11-09). The dialog listed F1 among
  the everywhere keys, which the user found pointless on the dialog F1 opens, and the seven keys
  put Undo at the bottom of one column and Redo at the top of the other. With F1 left out, the
  six fill two columns of three, Undo above Redo.


- **The main screen is a grid of cells** (2026-11-08), in place of a list with a sentence beside
  every row. Only the selected cell is boxed, single-lined with its name bold, chosen over a box
  on every cell with a double-lined frame on the selection.
- **The About dialog's quote has a blank line above and below** (2026-11-09).
- **The Description page has Save and Cancel buttons** under its text (2026-11-08): typing goes
  into a draft, Save stores it as one edit, and Cancel or Esc throws it away.
- **A protected set's description is read-only**, even though the set's other settings can be
  changed and saved as a copy.
- **Where an export went is said on the status line**, which replaced a dialog.
- **The Scale page's keyboard** was approved on 2026-11-08.

## The pattern editor's rows

- **The +Note and +Vel rows are three-way** (2026-11-09): `+` adds the register, `-` subtracts
  it and blank does neither, cycled by Space or Enter, where the rows were toggles that could
  only add. The file holds 1, -1 and 0, chosen over the marks `+` and `-`, which YAML would
  need quoted, and `true` from older files reads as 1.
- **`[` and `]` are two legend entries, `[` dec and `]` inc, on every row** (2026-11-09),
  where one entry read `[/]` adjust and the user took the slash for a key, and where the
  cycling rows read `Space/]` next and `[` back. The user's words are dec and inc, and the
  same words name Left and Right on the settings pages. Space or Enter goes to the next choice
  on a cycling row, except Chord, whose Enter opens the picker.


- **Glide is drawn with the dot** (2026-11-09), like Tie, in place of a bar from the step into
  the next, which the user found didn't look good.
- **A blank CC value starts at 0** (2026-11-09), when `]` steps it or Enter asks for it, in
  place of 64, the middle of the range, because the CC used most is the mod wheel, which starts
  from nothing.


- **Sections that open and close** (2026-11-08), the user's accordion design, in place of five
  sets of rows that Tab cycled through. All the rows can't fit an 80 by 24 console.
- **A section's label is `+` closed and `-` open**, chosen over triangles.
- **No divider crosses a section heading** (2026-11-09), since dividers cutting through a heading
  looked wrong.
- **The Degree row is a gauge** (2026-11-08). Seven rows were chosen over a four-row half-block
  gauge, whose labels would have been pairs of notes.
- **`]` at the top of the scale and `[` at the bottom stop there** (2026-11-08), over carrying
  into the next octave.
- **A tie is a mark, `●`, like any toggle** (2026-11-08), over a bar through the dividers, which
  broke the beat lines.
- **A cell that can't take a value shows a light `/`** (2026-11-08), over the `(X)` tried first.
- **No register setting is ever locked out for want of a note** (2026-11-08), so the register
  rows can be set on a rest.
- **The Grab row works on empty steps** (2026-11-08): the editor gives such a step the root in
  the default octave as a note of its own.
- **A grab step holds a chord, built on the grabbed note** (2026-11-09). Until then the Chord
  row showed `/` on a grab step and the render ignored a chord there, because a grabbed note is
  one note. The user wanted to grab a root from a bass and play a chord on the root, so a
  blank Chord cell keeps the one note and a symbol builds the chord. The piano roll draws no
  thin lines for such a chord and the description line names no note, only `the grabbed note`,
  by the user's choice: what is grabbed can't be known where a pattern is drawn.
- **The CC rows are one line of numbers**: the bars above the numbers were dropped on 2026-11-08.
- **Velocity and Probability stay numbers**, since one-line bars and quarter circles were drawn
  and found hard to read.
- **A beat's edge meets a rule in a plain joint** (2026-11-08). A bold joint broke the rule and a
  dim joint broke the edge, and the user saw each in turn.
- **A pattern wider than the screen scrolls sideways** rather than wrapping onto more blocks, so
  that a bar is always one row of columns.
- **Drum on or off always asks first**, since the rows change and any notes go.
- **Digits typed into one cell are one undo step**, as the user asked.
- **Erasing a note keeps every register row.** A rest could always be given `+Note` and `+Vel`,
  but erasing a note cleared them with the note, while `+=`, the CC values and Slide stayed.
  The user chose that erasing takes the note and the ties that drew it, and nothing a rest
  can hold.

## The piano roll

- **The roll itself** is the user's design of 2026-11-08: the interface music people expect, with
  everything it does mapped onto the pattern's rows.
- **One pencil, no modes** (2026-11-08), decided after a join method was tried.
- **Enter draws as Space does, and `H` picks the chord** (2026-11-09). Enter had opened the
  chord picker on a note and done nothing on an empty cell. The user wanted Space and Enter to
  do the same, as they do everywhere else, and a free letter for the picker: `C` is Copy on
  every page that copies, so the picker took `H`.
- **Space on a note erases the note** (2026-11-09), from any cell the note covers, exactly as
  `Bksp` does, where Space on a note did nothing before and the status line said `a note is
  already here`. The user's idea is do what I mean: only the result matters, which is that the
  note and the ties that made its bar go. Enter keeps the Chord picker. A note drawn again is a
  new note of the entry size, and Ctrl+Z brings the erased one back.
- **A row between two degrees exists only while a note is on it** (2026-11-08), so a pattern that
  stays in its scale looks like a scale.
- **A gate that ends inside a step fills part of its cell** (2026-11-08), so the bar ends where
  the sound does.
- **The cursor's cell stands between two bold double bars** (2026-11-08), over a box drawn over
  the rows beside it. Reverse video on a solid bar is blank, and the shading alone was hard to
  find. The rule beside the cursor's row boxes the cell on that side too (2026-11-09).
- **A note's mark is drawn in reverse video inside its bar** (2026-11-08).
- **A chord's other notes are thin dim lines** (2026-11-08), over the hollow boxes tried first.

## The offsets editor

- **A gauge of bars either side of a zero line** (2026-11-08), with the cursor's column marked at
  both ends.

## The format and playback

- **Ties win over the gate** (2026-11-08). Before, the longer of the two won. When ties became
  what the roll draws as a note's bar, the bar had to be what plays, so a note and three ties of
  1/16 is a quarter note whatever its gate says.
- **Registers replaced Cirklon-style accumulators**, with fixed names AX to DX.
- **Grabbing from a track** was chosen as simpler than a `notes_from` or `source_pattern`
  setting.
- **No seed by default**, which replaced an earlier seeded default: an unseeded song is a new
  take every export.
- **One memory, keyed by what changed, replaced four** (2026-11-09): the document's answers, the
  roll's own, the beat steps and the lengths were each dropped whole on every edit. Timed on a set
  thirty times the size of the largest example, the costs that grew with the set were the song's
  estimate, taken on every edit though the pattern editor shows only a pattern's own length, and
  Arrange asking for the longest scene once per drawn scene, each time adding up every scene's
  repeats from the start. Both went. Asking the memory for every cell cost more than the memo it
  replaced, so a line's questions are asked once and passed down.
- **Each setting is described once** (2026-11-09). The track, the scene, the clip, the song, the
  set, the pattern, the scale and the groove each checked a setting in two places, where a file
  is read and in the setter, written out twice. Each class now lists a description of each
  setting, which holds the one check, and both paths ask it. The messages are the same, and a
  file with two wrong settings names the first one the file holds, where the order was the
  code's before.
- **A generator's settings are checked when the set is opened** (2026-11-09), where they were
  kept unchecked until a chain used them, so that a wrong setting on a generator no chain uses
  is found, and the message names the generator rather than the chain. An arp or an AutoRatchet
  written with no settings at all is refused for the setting it needs.
- **What a track plays in a scene is a `ClipSlot`** (2026-11-09). The stored class was `Cell`,
  and cell also meant a groove's cell, a cell of a grid the tracker draws and a cell of the
  main screen. The user chose `ClipSlot`, Live's own word, asking that nothing made by the
  thousand in a render be slowed: a `ClipSlot` is made once for each clip in the file, never
  for a note, and the render's timings were the same before and after. Everything named after
  the class moved with it (`ClipSlotSetting`, `ClipSlotPlayer`, `Scene.get_clip_slot`,
  `Document.clip_slot`, `clip_slots_naming`). A groove's cells and the grids' cells keep the
  word, and people are still shown clip.
- **The editors of steps share a base, and the groove editor scrolls** (2026-11-09). The
  pattern, groove and offsets editors each kept a step cursor and the digits typed into a cell,
  and the two one-row editors repeated their keys, nudging, inserting, removing and grid rules.
  `StepEditor` holds what all three share and `OneRowEditor` what the two one-row editors
  share. The groove editor wrapped a long groove onto more blocks while the other two scrolled
  sideways, and the user allowed the groove editor to scroll so that the two could be one. A
  new groove's sixteen cells no longer all fit on an 80 column console, where eleven are shown.
- **Arrange's grid is drawn by a class of its own** (2026-11-09). `ArrangePage` held the cursor,
  the keys, every edit of scenes, tracks and clips and the whole drawing of the grid in one
  file of several screens. The drawing moved to `ArrangeDrawing` in
  `screens/arrange_drawing.py`, which draws from the page's cursor and scroll as `RollDrawing`
  and `PatternDrawing` draw from the pattern editor's, so each file is about one thing. Nothing
  on screen changed.
- **The kinds of settings field are classes** (2026-11-09). Every setting was a `Field` given
  four functions, so a toggle, a number and a choice were each written out wherever one was
  needed, and a toggle was told from other fields by comparing the words of its legend entry
  with the word toggle, which an edit of the wording would have broken. `Toggle`, `NameField`,
  `NumberField` and `ChoiceField` each take what the setting is. One thing changed with it:
  Left and Right stepped a song's or a scene's tempo and a scene's or a clip's Repeat past the
  most a typed value was allowed, and now stop there, as the guide's "from 10 to 999" said.
- **The pages that show one named thing share a mixin** (2026-11-09). Eight pages each kept a
  name and its crumbs, asked whether an undo had taken the thing away and renamed the thing, in
  their own words, and they descend from three bases, so what they share is the mixin
  `ShowsNamedItem`. The pattern editor's rename said `that name is empty or already in use` for
  both mistakes where every other rename says which, and now says which too.
- **The pages that list named things share one base** (2026-11-09). The Patterns, Scales,
  Chains, Grooves, Songs and generator pages each repeated rename, copy, delete, move and sort,
  about thirty-five lines a page. `NamedListPage` holds them once. Two things that differed
  between the pages became the same: only Patterns and Grooves said `copied to` and the copy's
  name on the status line, and now every page does, and sorting the songs left the cursor on
  its row where sorting the patterns kept the cursor on its pattern, and now both keep the
  cursor on its thing. Which pages sort was left as it was, Patterns and Songs, until the user chose that every
  one of them sorts with `S`, as the guide had said all along.
- **Edits of named things take the section** (2026-11-09). Moving and sorting took a section,
  while renaming, copying and deleting had a method for each kind on the document, about twenty
  in all, most of them one line that named the section. The five edits are now one method each.
  Adding stays a method for each kind.
- **Each row of a pattern is described once** (2026-11-09). A row such as Velocity had its check
  in an if-chain in the pattern, its range and its default in two dictionaries in the tracker,
  and its kind in lists of the format. Each row now has one description in the model, and the
  pattern, a file and the editor's rows ask it. The Ratchet and Ratchet Offset rows had limits
  in the editor alone, 1 to 16 and 24 either way, which the guide gave too, while a file could
  hold any number. A file is now held to the same limits, with a correction on opening. The same went for
  Repeat: the Scene page stopped at 999 and the Clip page at 9999 while a file could hold any
  number, and the user chose that a page and a file share one limit, so both limits moved to
  `composition/limits.py` and a larger Repeat in a file is corrected on opening.
  Playback still reads the plain lists.
- **Values out of range are corrected on opening, after asking** (2026-11-09). A file with a
  velocity of 200 was refused outright. The user chose to correct what has an allowed value near
  it, a number to the nearest end of its range and a choice to the default, and to refuse
  everything else as before. The tracker asks in a dialog that lists a few of the changes, cut to
  fit, and says the composition may sound different. The command line fails and says to pass
  `--force`, when exporting too. Reading stays strict first, so a file with nothing wrong costs
  nothing more, and undo's rebuild stays strict.
- **References by name are declared once** (2026-11-09). Each kind of rename was written by
  hand on the clip, the scene, the song and the set, and what uses a thing was asked again by a
  method for each kind and worded by a function for each kind. Each class now lists which of its
  settings name which section, and one rename and one question read the list.
- **A pattern knows its notes as bars** (2026-11-09). How a note, its gate and its ties make
  the piano roll's one bar, and how to draw, lengthen, shorten and cut the bar, was the
  document's, so nothing could reshape a note without the tracker. It moved onto `Pattern`, and
  the caller passes the step size, which the set may give the pattern.
- **Every kind of export is an `Exporter`** (2026-11-09). The four writers shared no base, and
  four functions each repeated an if-chain over the four kinds. The writers' method was `render`,
  which is the code's word for playing a song into clips, so it became `export`. The names
  around the exporters still said output and writer (`OutputKind`, `make_writer`,
  `exporters/outputs.py`), and the user chose that export and exporter are the only words for
  what writes files, with render kept for playing a song into clips, so those became
  `ExportKind`, `make_exporter`, `exporters/exports.py` and the like.
- **Snapshots share what didn't change** (2026-11-09). The history deep-copied the whole set's
  data on every edit, and an undo read the whole set again: 1.6 ms an edit and 14 ms an undo on
  the largest example. Each object now keeps its own data until it changes, the history copies
  nothing, and an undo reads only what differs: 0.04 ms and 0.3 ms. A whole song is read again
  when anything in it changed, which was fast enough not to go finer. The one test of the
  history copying its snapshots was replaced by tests that nothing changes data once kept.
- **A changing method is marked with `@notes_change`** (2026-11-09), the user's suggestion, over a
  call at the top of every such method. The piano roll's keys that need a note under the cursor
  are marked with `@on_a_note` the same way. A decorator is used where several methods open with
  the same few lines, never to replace one explicit line.
- **`Rational` replaced `Fraction`**, being about twice as fast per operation. Integer ticks were
  considered and rejected.
- **The render was made faster by doing less, with the classes kept.** Lengths as pairs of whole
  numbers and sounds as tuples, each handled by a class of static methods, were agreed first.
  Measuring before building showed where a note's cost was: a copy checked as the constructor
  checks took 517 ns, the same copy checking only what changed 102 ns, and a tuple 30 ns, so
  four fifths of the cost was checking again what had not changed. A step also made each note
  three or four times, and built a dictionary of all thirty rows for every step. Removing that
  work took the render of every example from about 408 ms to about 214 ms with no class
  replaced. Tuples through the generators could not keep the tests untouched as promised, since
  those tests read a note's spelling and the clip's own list from what a generator returns, and
  the layout agreed holds neither. What tuples and pairs would still save was estimated from
  the timings of one operation and the counts of calls, at about a tenth of the new time, and
  put to the user.
- **Sounds are tuples and lengths are pairs inside a render**, which the user asked for after
  the faster render, knowing that the generator tests would change. The estimate of a tenth was
  low: every example renders in about 154 ms where the render took 213. A clip holds either the
  objects a test gave or the sounds a render made, so only four tests changed, the ones that
  called `cut_position`, `along_scale` and a generator's `_generate` with objects. A note's
  tuple carries its name, which the first layout left out, so that a spelling survives. The
  places of a tuple are named constants, which cost nothing measurable, where a reader method
  for each place would have cost a call.
- **A long note that probability drops is silence, and the next note plays.** A note whose
  gate reached over the next note, on a take where probability dropped the note, stopped the
  export with an error about a rest that can't be held. In the pattern editor that is a Gate
  longer than a step, a note on the next step and a Probability below 100, so about half the
  exports failed at 50. The user agreed that silence is the only sensible result.
- **Exact MIDI timing isn't tested**, by the user's wish, so that the math stays free to improve.
- **A looping clip doesn't hold its scene in real time** (2026-11-10). The first rule of that
  day was that a looping clip loops until the human starts something else on its track, so a
  scene with one is never done and the song waits there, as Live's Session View does; the user
  rejected an earlier build that cut a loop as the export does. The same day the user hooked
  the registers demo up to instruments, whose kick and hat loop in every scene beside a riff
  with a Repeat, and the song never left its first scene. The user then stated the whole rule
  afresh: a scene is done when every clip in it that doesn't loop has finished, each clip's
  Advance ("With Scene", the default, "Next" or "Off") says when the clip sends its start to
  the clip below, and a scene whose Launch together is on launches whole when a start reaches
  any of its clips, stopping the scene above, loops included. So every demo plays to its end
  from Space on the corner, as its export does, with no demo file changed, and only a scene
  whose every clip loops waits for the human. The clip page's field keeps the name Advance.

## Working practice

- **The version is bumped by `internal_tools/bump.sh`, and the hook checks it** (2026-11-09). Two commits went
  in without their bump that night, because a text replacement that matched nothing changed
  nothing and said nothing.
- **The tests' `type(text)` refuses unless something takes text** (2026-11-09). Two tests had
  passed by accident: the key that should have opened a prompt had stopped working, and the
  letters of the name pressed the page's keys, the letter a pressing the new add key.
- **Tests name keys by what they do** (2026-11-09). About 35 test lines pressed the plus
  character to mean add, and all broke when add became `A`.
- **Help is checked against the keys** (2026-11-09), after the help of several pages went on
  naming keys that had moved.
- **A test class that runs past two minutes is stopped** (2026-11-08), after a test that pressed
  a key in a loop hung a run.
- **The choices under a numbered question take letters** (2026-11-09), so that an answer reads
  "43, A", after a question listed three choices as bullets.
- **One running sequence of numbers in a discussion** (2026-11-08), after a reply numbered its
  proposals and its questions separately and the user's answers couldn't be told apart.
