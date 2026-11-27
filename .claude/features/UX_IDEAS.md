# UX Ideas

Wanted changes to how the tracker looks and is used: what each is, never its status or order (those are in
`.claude/planning/QUEUE.md`). An idea leaves this file once built, and a rule it makes goes into `.claude/rules/UX.md`.

- **The open circle**: Everywhere a toggle is shown, an unset one shows `○` where today it is blank, a set one `●`, on every
  page, the pattern editor's toggle rows and the tabs' marks included; built with the tab box.
- **A line at the foot of every major editor** saying what the tab or section under the cursor does.
- **Holding `[` or `]`** on a stepped field, such as the synths' gauges, speeds up as it is held.
- **Muted scenes** change colour on Arrange (which colour and where, asked first: a new allowance of colour).
- **The wording of everything shown**: A discussion first, then an audit of every string. No "you" or "your"; "allow", never
  "let"; formal throughout; Claude answering as a professor of English who designs applications for business professionals,
  with its own rules to recommend; the tests' labels of choices in scope.
- **"F5 Wizard"** on the main screen's legend, and on no other page's.
- **A dialog of buttons only** shows no legend of keys.
- **A blank line under every dialog's title**, before its text and buttons.
- **The keys audit**: Letter clashes, `Bksp`'s words echoing the value it brings back, "move" for every cursor motion.
- **"Notes & Octaves" to "Octaves & Steps"**, and the track's Notes column to "Pitch".
- **The keyswitch map** on the Instruments page: Note and Octave as ordinary rows, no keyboard drawing, no second dialog.
- **The on-screen keyboard**: `K` on every page opens a keyboard drawn on screen and played from the computer's keys,
  sounding the instrument of the page, or of the track or pattern under the cursor. `K` (Keyswitch map) on the Instrument
  page and `K` (keyswitch) in the pattern editor move to `W`, one letter for keyswitches on both pages.
- **Listening to a drum-track pattern**: a pattern whose clips are all on drum tracks listens through the drum track's own
  instrument where it has one, and otherwise through FluidSynth's drum kit, as a drum pattern does, rather than the
  song's Preview instrument or the piano.
- **Space on an empty drum Note step**: in a drum pattern's rows, Space on a Note cell with no note writes C there.
- **Solo a track, and mute from Arrange**: on Arrange, with the cursor anywhere in a track's column, a key mutes or
  unmutes the track (the same Mute as its track editor's) and a key solos it; a solo is one track at a time, every other
  track silent while it lasts, soloing another moving the solo there; live and in Listen. A muted track's column shows in
  its own colour and its heading an `M`, a soloed track's heading an `S`. The keys and the colour are still to settle.
- **Drawing only what changed**: the screen kept as a grid of cells, each its character and style, and each frame compared
  with the last so that only the cells that changed are sent to the terminal, the cursor moved only where the next changed
  cell does not follow the last and a style sent only where it changes, after the open-source Ratatui's buffer (MIT,
  credited where its approach is followed); the pages unchanged, every screen identical, the time and output measured
  before and after.
- **Smoother gauges**: every horizontal gauge filled in eighths of a cell, whole cells then one of `▏▎▍▌▋▊▉`, so that a gauge
  shows eight times the steps at the same width, its value and width unchanged.
- **Cheaper visualizers**: drawn through the grid of cells so that only what changed is sent, at a steady frame rate set by
  the clock that drops a frame rather than queue it, with fewer distinct colours where that leaves more cells unchanged, the
  anti-strobe limit kept; timed before and after.
- **Batch pattern editing** on a group: a discussion, then building.
- **Transpose** by scale degrees, semitones or octaves, with a mockup; Grab track removed, each Grab step choosing the track
  it grabs from; drop chords and smarter voice leading on the object tabs.
- **The sender falling behind**: When the Realtime Sender Process is starved, it does not choke, and the status line says so in
  the warning colour; what counts as behind, how often it says so, and the words, designed first.
- **The pattern documents' Munge table** checked against the dialog's choices, heading by heading.

## More UX Ideas

In the order of their priority, the highest first.

- **A picker field's mark that is not taken for the other arrows**: A settings field that opens a list of choices shows a
  dim down-pointing triangle after its value (`MSG_PICKER_MARK`). At a small text size, and from a distance, that mark reads
  like the tracker's other triangles and diamonds: the selected row's mark, the play mark, the flyout's mark and the
  keyswitch light. The user asks how a list field could be marked differently, so that the kind of field is still seen at a
  glance and is not confused with those. To discuss with pictures of the candidates at the size they are drawn, before
  anything changes; whatever is chosen changes every settings page, the mockup rules of `.claude/rules/UX.md` and the
  screenshots.
- **A view of a progression's chords as keyboards**: The progression editor could have a button that shows
  the progression's chords as drawings, each chord listed with the keyboard the Chord dialog draws, the chord's keys filled,
  so that the changes from chord to chord can be seen. The view scrolls down one drawing at a time and stops at the last,
  never going round. Only where it makes sense: whether it does, and when the button can be offered (a progression's chords
  are numbers in whatever scale a clip plays them under, so a scale has to be known), is to be discussed with the user
  first, on its own, with a drawing by Claude, once the other ideas of the current work are done. What it would mean for the
  code: `Keyboard` and `chord_keys` in `interface/tracker/components/keyboard.py` already draw one chord,
  `ChordsEditor.in_words` names each chord in the song's scale, and an Inset Window is the read-only window the tracker has
  for looking inside things.
- **Info about a set on the Open page, before opening it**: On the Open page, a key on a set's
  row, `I` (Info) say, opens a dialog that says what the file holds before you decide to open it: the set's title, its
  description (the one line saying what it plays), its author, and for each song its name, its tempo and its length when
  played. ENTER in the dialog opens the set and ESC cancels, back to the list, so that a look costs one key and opening
  after the look costs one more. - **What it would mean for the code.** The dialog reads the file the way the Open page
  already reads nothing: `Setlist.read_file` gives the title, description, author and each song's tempo, and the length
  comes from the same estimate Arrange uses (`interface/tracker/lengths.py`, `measured(song)`), which needs a `Document` of
  the set, so the dialog builds one in memory and throws it away unless ENTER keeps it, in which case opening is already
  done. A file that can't be read says so in the dialog instead, with the file's error, and a file that needs corrections
  says that it would open with corrections and how many. The dialog is a `MessageDialog` with two answers rather than one,
  ENTER open and ESC cancel, which is a `ConfirmDialog` whose buttons read Open and Cancel. The key goes in
  `keybindings.OpenPage` with a legend entry, and the Open page's help names it. - **Undecided.** Whether ENTER on a row
  should show the info first and ENTER again open, which would cost everyone a key on every open, or stay as it is with the
  info on its own key, which Claude would choose. Whether a set of several songs lists them all, or the first few with a
  count, since the dialog has to fit an 80 by 24 console.
- **The file picker, shared and better**: Every file picker is one: the Open page
  (`screens/set/open_page.py`, which starts in `examples/`), the MIDI import's, and any later one, the same page given what
  files it shows and where it starts. The files people want may be far outside the tracker's directory, so it needs to get
  there quickly: a full path typed in, with `~` for the home directory, and perhaps recent directories and recent files. The
  MIDI import starts in the home directory until this is designed. Undecided: which of those, and how a typed path is
  reached on a page whose `/` already searches, for which Claude offered a row at the top of the list, "type a path", that
  ENTER opens a prompt on (a directory goes there, a file opens, a path that doesn't exist says so on the status line), a
  letter key, `G` (Go to path), opening the same prompt, or both, recommending the row, since nobody has to know a key to
  get around.
- **Marking the chords that fit the scale in the chord picker**: When the pattern editor knows
  the one scale a pattern plays under (the gauge's scale, `Document.pattern_scale`, known when the pattern's uses agree on
  one or when nothing uses it and the current song has one), the chord picker on the Chord row (`ENTER`, the
  `GridChoiceDialog` laid out by `CHORD_GROUPS`) puts a check mark beside each fixed chord whose notes all lie in that scale
  from the step's note, like `✓ M` on a major chord from the root of a major scale. The scale chords (`5`, `3`, `7` and so
  on) are built from the scale, so they always fit and need no mark; the mark is for the named ones, `M`, `m`, `dom7` and
  the rest. Since a new song starts with `C Major` as its scale, the scale is known most of the time, and only a pattern
  played under several scales goes without the marks. What it would mean for the code: a `Chord` or `Scale` method that says
  whether a chord's notes are all in a scale, `GridChoiceDialog` taking a mark per option, and the Chord row working out the
  marks from the step's degree, accidental and octave. The user wants to talk this over before it's started.
- **New patterns from the clip page**: `P` (Pattern) already opens a clip's pattern in the
  editor, from Arrange and from the clip page. The clip page could gain two `Button`s under its settings: one that adds a
  new pattern, assigns it to the clip and opens it, so a clip can be filled in without a trip to the Patterns page; and one
  that adds a new pattern as a copy of another, asking which pattern to copy in a picker and then assigning and opening it
  the same way. Because a pattern made this way is used by this clip alone, the editor knows its scale at once, from the
  clip's scene or the song. What it would mean for the code: the clip page building its buttons with `FieldPage.button`,
  `Document.add_pattern` and `copy_named` (the Patterns page's `C`) followed by `set_clip_slot_setting`, then opening the
  editor as `P` does. The user wants to talk this over before it's started.
- **The pattern editor's rows in more sections, so that a pattern's many options are easier to understand**: The user finds
  a pattern has too many options to take in, and wants more of the rows view's sections (the accordion, the headings from `+
  Basics` to `+ Set Registers`) so that each opened section holds a few related rows. To discuss before it is built: which
  rows belong together, what each new section is called, which open by default, and whether the pinned rows, Degree and
  Octave, stay as they are. A closed heading already says `(set)` when anything inside holds a value, so splitting hides
  nothing that is used. It touches `SECTIONS` and the row descriptions behind the rows view
  (`interface/tracker/screens/pattern/`), the editor's help and `.claude/reference/KEYMAP.md`, and the PgUp and PgDn jumps
  between headings.
- **Performance Dashboard**: The user's name and idea: a dialog that pops up while a song plays, with dials that nudge and
  tweak the song as it plays, held in memory and not written into the set: the tempo offset of the idea "A tempo offset for
  everything playing on Arrange, while playing live", a key change offset that transposes what plays, and on the same panel
  CC controllers for the instruments, with visual feedback whenever a dial moves. It touches the real-time redesign's agreed
  step that makes the Realtime Sender Process a program of its own, which already plans a message for a knob's value and
  last-moment changes the sender applies (velocity scale, transpose, mute, CC passed through), so a dial is heard at once
  without a render; a tempo offset needs the render process to retime what it hands over instead. To discuss: which dials,
  how they are drawn and reached with the keys (a dial in the tracker's characters, `[` and `]` to turn it), whether a tweak
  can be kept into the set afterwards, what an export hears (nothing, most likely), and how the panel would appear in a web
  interface, as part of the declarative UI discussion.
- **Everything reachable with the arrows, ENTER, Space and ESC**: A follow-on to the declarative UI discussion (the user's
  idea): list what cannot be done today with the arrow keys, ENTER, Space and ESC alone, page by page, and make as much of
  it as possible doable that way, so that the letters become shortcuts for people who know them rather than the only way in.
  `.claude/reference/KEYMAP.md`, made by the key tour, is where the list starts: every binding on a letter or a mark whose
  action has no button, field, picker entry or menu row the arrows reach. It fits PRINCIPLES.md's "Someone who never reads
  the manual still gets around", and a declarative view, whose widgets say what they do, could make every action reachable
  by the arrows on every kind of interface, a web interface's included.
- **Collapsing a track or a scene on Arrange**: On the Arrange page, one key, the same for both, collapses what the cursor
  is on: a track to a column one character wide, or a scene to a single line, and the key again opens it, so that a big song
  fits on screen and the parts not being worked on step aside. Touches ArrangeDrawing's widths and heights (track_width,
  scene_lines, the visible tracks and scenes), the cursor, which still lands on a collapsed track or scene, the frame around
  a collapsed one, and the details view. Undecided: what a collapsed track's one column and a collapsed scene's line show (a
  mark, the first letter, a light while it plays), whether collapsing is kept for the session only or saved in the set,
  whether a whole run can be collapsed at once, and which letter it takes.
- **Munge as a cornerstone: a wizard in an Inset Window that previews before committing**: Munge becomes one of llamatron's
  cornerstones. In the pattern editor, Munge opens a small wizard in an Inset Window: choose a munge and its values, see the
  result previewed against the pattern, Tab between the piano roll and the rows view of the preview, munge again (another
  munge, or the same one again, such as another random shuffle) as many times as wanted, and only then commit it as one
  edit, or leave with nothing changed. Changes are shown in a different colour: easy on the piano roll, where the new or
  moved notes can be drawn over the old in their own colour; in the rows view the changed steps' values simply replace the
  old ones, perhaps marked. Claude's UX help is wanted for the design when the work starts. Touches the Munge dialog and its
  picker, the pattern editor's two views (drawn from a copy of the pattern, not the set), the Inset Window, undo (one edit
  for the whole run of munges), Listen on the preview, and colour, a new allowance. Relates to "More ways to munge a
  pattern" and "A Munge generator", and to the audit of keys where Munge was named as a mess.
- **Listening to a scene on the Scene page, and progress bars on every listen**: The Scene page gains a way to listen to its
  scene, as the clip page and the pattern editor listen to theirs. Listening may need everything else stopped first. With
  it, a question to talk through with the user before anything is built: whether a listen shows a progress bar as it plays,
  and on which pages that makes sense (the clip page, the pattern editor, the Scene page, a picker's preview). To work out:
  what a scene's listen does while a song plays from Arrange, stop the song, refuse, or wait for the bar; whether looping
  clips are cut at the scene's length; and one drawing of the bar shared by every page that listens, the length bars' read
  heads on Arrange being the nearest thing there is. The way in would be Play and Stop buttons on the Scene page, as the
  clip page has.
- **An audit of every dialog and button row for consistency**: The user wants every dialog and every row of buttons checked
  for UX consistency against `.claude/rules/UX.md`: the boxed buttons of `interface/tracker/components/button_row.py`, OK,
  YES, NO and CANCEL in capitals, ENTER and ESC, the blank line above a window's bottom edge, Left and Right between
  buttons, a settings page's buttons in one row or one under another, cascading windows and flyouts, the wording of titles.
  The audit would list each dialog and page with buttons and what differs, as numbered findings, before anything is changed.
- **A black theme forced from the environment**: When THEMES=BLACK is set in the environment, the text UI draws on a black
  background whatever the terminal's own settings, and white is the default colour of text. Touches the app's CSS (the
  screen's background and default foreground), the styles in interface/tracker/drawing.py that assume the terminal's colours
  (dim, the theme stripes' black or white caption), the visualizer and Scene View, whose colours were chosen against an
  unknown background, and the screenshots, which could be taken in it. Undecided: whether other values of THEMES follow (a
  white theme), whether a set or a setting can choose it too, and whether dim stays dim grey on black.
- **Hiding tracks on Arrange**: A key on the Arrange page, the hide key, opens a dialog that lists the song's tracks and
  lets a person hide and show each one, so that tracks a person does not need to see, such as a muted chords track or other
  guide tracks, take no room on the Arrange page. A hidden track still plays and is still followed, as before; hiding
  changes only what Arrange draws. How many tracks are hidden has to be shown somewhere on the Arrange page, so that nobody
  forgets tracks are there. To discuss before building: where the count shows, whether the choice is kept in the set file or
  only for the session, what the cursor does at a hidden track, and whether Scene View, the details view and the exports
  show hidden tracks. For the code: a setting of the track or of the song, the Arrange page's drawing and cursor skipping
  hidden columns, a new dialog, and the key's binding in interface/tracker/keybindings.py.
- **How the Chord dialog shows borrowed chords**: The Chord dialog's BORROW FROM SCALE list, a row that borrows no scale and
  then the scale categories, each a button that opens a flyout of its scale types, may be shown another way. To decide with
  the user: what a person wants to see when borrowing a chord, such as the chord each scale would give on the step rather
  than the scale's name; whether the categories stay; and how the list fits beside the other four, which take the 72 columns
  an 80-column console leaves now that the dialog has a DOUBLE list. For the code: the scale list and its flyouts in
  interface/tracker/dialogs/chord_dialog.py, and interface/tracker/scale_categories.py.
- **Typing a chord in the Chord dialog as a chart writes it**: A chart line at the top of the Chord dialog where a player
  types a chord as a lead sheet writes it, such as 7(b9,no5)/E on a step whose note is C, and the quality list and the
  fields follow as they type, so it teaches the notation too. The step fixes the root, which the line shows. Jazz spellings
  are taken as well as pop ones: -7, Δ7, ø, °7, +, maj7, m. A slash bass that the step can't play is refused in amber. To
  decide: what the line does with a root typed that differs from the step's; how a typed chord with no symbol is shown; and
  how the line and the list share the cursor. For the code: a parser of chord text in music_theory, the Chord dialog's first
  line, and the dialog's keys, since the line takes typed letters.
- **Playing lights on the list pages**: While a song plays in real time, the Patterns page lights a playing mark beside each
  pattern that a playing clip is playing at that moment, and the Generators and Chains pages do the same for each generator
  and chain that is active in a clip that is playing. It would use the lights Arrange already has, so that the same mark
  means playing everywhere. On the Patterns page a group's heading lights too, while any pattern of the group is playing, so
  that a closed group still shows that something inside plays. To work out: the transport already knows which clips play, so
  each list asks it which patterns, chains and generators those clips use, a chain counting its generators; whether a
  pattern reached only through a generator lights; and where the mark goes in a row beside the count columns.
- **List pages that use the room the console has**: After the main screen's redesign, the user wants the pages that list
  things made more compelling and useful on a console larger than 80 by 24: the set's list of patterns among them, and
  whether some lists should be shown in several columns, a grid to pick from, so that more names are in view. To be designed
  with drawings before anything is built. What it would mean for the code: `ListPage` laying its rows out in columns for the
  size it is given, the cursor moving over them with all four arrows and stopping at every edge, the search, Move mode and
  the `+` row keeping their behaviour, 80 by 24 staying as today. For the Patterns page, the user's ask: where the console
  has the room, each row shows the tracks that play the pattern, in the space the row has left, as a column TRACKS that
  reads as the number of tracks and then their names in parentheses, like `(2 lead, pad)`, cut with an ellipsis when the
  names don't fit; the number of uses is always shown, whatever the room. Also settled: a blank line separates the caption
  from the column headings; TYPE becomes DRUM, a solid circle for a drum pattern and nothing otherwise; every column,
  heading and value, is left-justified. What it would mean for the code: `uses_of` in `interface/pages/uses.py` already
  knows every use, and the Patterns page's USED column the count; the row needs the track names of the uses, without
  repeats, fitted to the width the page is given, and the answer remembered until the set changes. A way to see every use of
  one pattern, as a list of song, scene and track, like the list shown when deleting a used pattern is refused, from the
  Patterns page or the pattern editor, belongs with this: `uses_of` already puts the uses into words, so a key that shows
  them in a `MessageDialog` is most of it.
- **Arrange scrolls with what plays, when launched for recording**: For the demo recorder
  (docs/RECORDING.md, being built). A long song has more scenes than fit on an 80 by 24 console, and a video of the Arrange
  page that stays on the first scenes shows nothing of the rest. The user suggests that Arrange scrolls down to keep the
  playing scene in view, and only when the tracker is launched with a flag, say `--launch-for-recording`, which may set
  other properties for a take too, rather than always, since in ordinary use the cursor decides what Arrange shows and the
  page shouldn't move under it. What it needs: Arrange's `top`, the first scene shown, is set by `visible_scenes` to keep
  the cursor's row on screen; launched for recording, the playback timer's redraw would move `top` so that the lowest
  playing scene (`Transport.playing_scenes`) is shown, and leave the cursor where it is. What else the flag sets is open:
  the user mentioned other properties without naming them. The recorder's own flags, `--autoplay` and
  `--autoplay-quit-when-finished`, are separate, so a take can be played without the page scrolling.
- **A scroll bar wherever a list scrolls**: The user liked the scroll bar drawn at the right of the list in the mockup of
  the "Copy Pattern to Songs" dialog, a column of the list's height whose solid part shows which part of the list is in
  view, and wants to explore where else it could be used. Places to consider: every picker and every list page whose rows
  don't all fit, the Chord dialog's lists, the Open page, the F1 dialog, the pattern editor's rows view and Arrange when the
  scenes or tracks run past the console. What it would mean for the code: one component that draws the bar from the count of
  rows, the rows shown and the first row in view, used by `ChoiceDialog`, `ListPage` and the rest, each giving up one column
  at its right.
- **Details shown on one track, scene or clip of Arrange**: Rather than the details view opening every cell at once (`R`), a
  key would open the details of what the cursor is on alone, and the same key again close them: on a track's name, the whole
  column; on a scene's name, the whole row; on a clip, that clip only, though its scene's row and its track's column grow to
  fit it, since a row is as tall and a column as wide as its largest cell. For the code: `ArrangeDrawing.track_width` and
  `scene_lines` would ask which columns, rows and cells are open, a set kept on the page or the app for the session, rather
  than the one switch `shows_arrange_details`, and `draw_details` and the Tab picking would act only on open cells;
  `details_layout` already works the widths and heights out per column and per row. Whether the blue dividers show while
  only some cells are open, and how this sits beside `R`, are to be discussed.
- **A tree sidebar, to try on a branch**: The user's idea, to be described more later: a sidebar beside the
  page, drawn as a tree whose nodes expand and collapse, so that what's under each song (its tracks, scenes and clips, and
  the set's shared patterns, scales, generators, chains and grooves above them) can be seen at a glance, along with where
  you are and what you're looking at. It may not work out, so it's something to try on a branch rather than build straight
  in. What it would touch, roughly: every page is laid out for 80 columns, and the pattern editor and the Arrange grid use
  all of them, so the sidebar would have to fold away or only show on wider terminals, or replace the crumbs on the top line
  rather than sit beside the page. Textual has a `Tree` widget, which would need checking against the rule that the tracker
  draws with bold, dim, reverse video and box characters only. If the tree can also be moved in, it becomes the first way to
  jump between pages that isn't up or down one level, which is the question under "What Tab means, once pages can jump".
- **Buttons: rows on a page that do what a key does**: The File/Global page already has Save and Open rows that do what
  Ctrl+S and Ctrl+O do, so that the page can be worked with the arrow keys alone, and the user wants that idea finished and
  named: a "button" is a row on a page, drawn like the menu rows on the main screen, that ENTER presses and that shows the
  hotkey it stands for, so nothing is reachable only by a key. The File/Global page has Save and Open buttons below its
  settings, and the clip page Play and Stop; Save as is still `W` alone. Buttons are for places where a Ctrl+ or other
  shortcut has a logical home on the page too; the rest of the UI is easy enough to move around that it doesn't need them
  yet. Where they'd go next: - **The pattern editor**: A Munge button right after the step grid, which opens the munge
  dialog and shows `M`, so that munging moves out of the footer and the footer gets shorter. - **Claude's other candidates,
  to weigh**: An Export button on the Song page already exists as a row, which is the same idea; a Rename button on the
  editors that rename with `N`; Load over on the pattern editor beside Munge; New set and Save as on the File/Global page;
  Add at the bottom of every list, which the `+` row is already; and a Help button is probably not worth a row, since F1 is
  on every legend. The footer stays the key legend for the page's own keys, as "F1 as the hotkey dialog, and a shorter
  footer" below describes, so a button's key still shows there. What it would mean for the code: `Button` in
  `screens/shared/field.py` exists, made by `FieldPage.button` and drawn below the settings after a blank line with its
  key's name in front, as the main menu draws a row, so what's left is a Save as button on the File/Global page, a cursor
  position below the grid in the pattern editor, which is new for it, and a check in
  `tests/interface/tracker/test_tui_keys_shown.py` that every button's key is still in `keys()`, so pressing the key and the
  button do the same.
- **Naming the CC numbers in the track editor's picker**: To confirm when it comes up. The
  track editor's CC 1 to CC 4 fields take a number from 0 to 127, typed or nudged, and the MIDI specification gives most of
  those numbers a standard purpose: 1 is the mod wheel, 7 volume, 10 pan, 11 expression, 64 the sustain pedal, 71 resonance,
  74 brightness, which is the filter cutoff on most synths, and so on. ENTER on one of those fields would open a picker
  listing every number with its name beside it, like `74 brightness (filter cutoff)`, searchable as every picker is by
  typing, so that typing `filt` finds the number for a filter sweep without looking it up, and the unnamed numbers would be
  listed as numbers alone. The pattern editor's CC row labels, which say the lane's number, like `CC 1 (74)`, could add the
  name where the cell width allows. What it would mean for the code: a table of the standard names in
  `model/values/midi.py`, the CC fields' ENTER opening a `ChoiceDialog` built from it in place of the number prompt
  (`MSG_CC_PROMPT`), with `+` and `-` still stepping the number, and the names as `MSG_` constants since they're shown.
- **A Settings page, from a YAML dotfile**: A Settings page in the app, reached from the main screen, whose values live in a
  dotfile in the user's home directory, `~/.llamatron`, written as YAML and read through `safe_yaml.load_safely` like
  everything else. The settings are the user's own preferences rather than anything a set stores, so they never go in a set
  file, and every one has a default so that no dotfile at all means the program as it is today. What they could hold: -
  **Streamlining the app**: Hiding features the user never uses, such as pages, pattern editor rows or whole export kinds in
  the Ctrl+X dialog (someone who never writes MIDI files sees only the Live set), so that the legends and dialogs get
  shorter. - **Defaults for new songs and sets**: Real-time MIDI on by default once it exists, default MIDI channels for
  tracks, default track names for a new song (`kick`, `bass`, `lead` instead of `track 1`), a default tempo, time signature
  or scale. - **Starter content**: A set file whose patterns (and perhaps scales, chains and grooves) are added to every new
  set automatically, so that a personal library follows the user around; this overlaps with "A library of patterns, chains
  and arps" below and could be how that starts. What it would mean for the code: a `Settings` object in `support/` or a
  package of its own, read once at start with defaults for everything, passed to the app rather than read from a global;
  `Document` and the pages ask it for defaults where they use `model/schema/defaults.py` today, so the file format's
  defaults stay what they are and the user's defaults only apply to what the tracker creates; the Ctrl+X dialog and the
  legends filter their lists through it; and the page itself is a `FieldPage` that writes the dotfile back. Tests set a
  dotfile path explicitly so that they never read the developer's own.
- **Colour: a light terminal's palette, and switching itself off**: Colour has arrived allowance by allowance
  (`.claude/rules/UX.md`, "Drawing"), the themes' stripes among them, in place of the one switch first imagined. Two things
  are left. The colours were chosen on a dark terminal, so each wants checking on a light one, with a second palette if any
  reads badly: `Style` in `interface/tracker/drawing.py` is the one place styles are named, so a palette is a mapping from
  each of its names to a Rich style, picked when the app starts. And colour should switch itself off where a terminal cannot
  show it, with no setting: what to look up is Textual's `theme`, `available_themes` and `register_theme` (the app runs with
  `ansi_color=True` today, which keeps the terminal's own sixteen colours), whether it asks the terminal for its background
  colour and exposes the answer, Rich's `Console.color_system` for the colour depth, and the `COLORTERM` and `NO_COLOR`
  environment variables, which a terminal sets and a person can set to switch colour off. Also asked for and not built: the
  piano roll's cursor box in a colour of its own.
- **Keys for the rest of what's global, to discuss**: What works on every page is a Ctrl+ key or a function key, so that the
  plain letters are always a page's own (`.claude/rules/UX.md`, "Keys and legends"). Two things are left to discuss. New and
  Save As are still plain letters on the File/Global page, and whether they count as global and should take Ctrl+ keys too.
  And whether the things that matter most, Save, Export and Open, could take function keys as well, since one key is easier
  to type than Ctrl and a letter; F1, F2, F3 and F5 are taken, macOS keeps F9 and above for its windows, and on a Mac the
  function keys need Fn unless they're set to standard keys, which weighs against it. Ctrl+C, Ctrl+Z and a few others are
  taken already.
- **A llama that runs across the bottom of the screen**: Asked for by the user: a small llama drawn in ASCII
  block characters that runs across the bottom of the screen when the program starts, and runs across again every time the
  set is saved, each run in the opposite direction to the last. An export runs a llama too, but one that's somehow different
  from the save's, perhaps two llamas running together, to be decided when the idea is picked up. The first thought was a
  llama that stood on the main screen until the first key press; the running one replaced it the same day. What the llamas
  look like is to be discussed then, with sketches to iterate on first, as with every drawing. What it would mean for the
  code: the drawing as a tuple of `MSG_` lines, like the About dialog's cow (`MSG_COW`), and a mirrored copy for the way
  back; a Textual timer on the app that moves the llama a column or two at a time along the line above the legend, or over
  the status line, which every page shares, so that it runs on whatever page is open; `Document.save` and the export telling
  the app which happened, which starts the next run with the right llama or llamas; the app remembering which way the last
  run went; and the run leaving the keys working throughout, since it's only a drawing. The tests would step the timer by
  hand rather than wait, and check that a save starts a run the other way.
- **Every object has a unique name**: All objects must have unique names. Patterns, tracks, scales, arps, AutoRatchets and
  chains already do, within each kind, because the file stores them by name. The exception is scenes: their names are
  optional and can repeat, which is why the grid's `ClipRow` and `ClipColumn` have ids today. Making this a rule means: -
  **Scenes always get a name,** and a unique one. A new scene already gets a name like `scene 3`, so mostly this means
  refusing duplicates, and naming the unnamed scenes in older files when they load, by the defaults rule. - **Unique within
  a kind, or across all kinds?** A pattern and a chain both called `bass` don't clash today, because every reference says
  what kind it names. Unique within each kind is probably enough, but this needs deciding, and sections may change the
  answer if patterns belong to sections. - **Ids may become unnecessary.** With unique scene names, the ids on `ClipRow` and
  `ClipColumn`, which exist only because names could repeat, could perhaps go, and the clip tree's file names, which use
  ids, could use names instead.
- **A gauge dialog for picking a number cell's value**: To sketch before anything is built:
  ENTER on a cell that holds a number in the pattern editor, Velocity, Prob, a CC row, Octave or a register change like `AX
  +=`, would open a dialog with a gauge, the way ENTER on the Chord row opens the chord picker, so that a value can be
  picked by sight, with the arrows moving along the gauge and digits still typing. The register note and velocity rows are
  toggles, so they'd have no such dialog. The user wants example sketches first, drawn the way the pattern editor sketches
  were, before deciding. What it would mean for the code: a dialog in `interface/tracker/dialogs/` drawn from the gauge
  pieces the Degree row and `SignedGauge` already have, and an ENTER key on `NumberRow`, `ControlRow`, `CcRow` and
  `OctaveRow`, which today only take digits and `+/-`.
- **Reviewing every hotkey in the text UI**: Review the letter keys on every page of the text UI, to see whether any could
  be more logical, and only change them if it's warranted. This needs discussing before anything changes. Making one key
  more logical can mean moving another to free its letter, so the review should look at every page together. Every key
  binding is in `py_legacy/src/llamatron/interface/tracker/keybindings.py`, one class for each page, and `py_legacy/internal_tools/keys.sh`
  prints them all, or every binding that has one key (`py_legacy/internal_tools/keys.sh --key s`), so that's the complete list to work
  from. Things already worth a look: - **The same letter meaning different things on different pages,** like the letter that
  opens a page from the main screen also sorting lists, or the one that moves a row down also removing a step in the pattern
  editor. - **Letters that are text in some places.** On a drum pattern's Note row, the note letters type notes, so any
  editor key on one of those letters isn't available there. - **Letters chosen because the obvious one was taken.** Some of
  the pattern editor's whole-pattern actions moved into the Reconfigure dialog, which freed letters, so the question is
  whether the remaining letters on each page are the obvious ones. - **Whether every page offers the same key for the same
  kind of action,** such as renaming, copying, deleting and moving up or down, wherever those apply.
- **Grouping the F1 dialog's keys**: The F1 dialog lists the keys that work everywhere, a blank
  line and then the page's own keys, in two columns in the order the page's `keys()` gives them, and on the pages with many
  keys, the pattern editor above all, that's getting messy: related keys sit apart and a reader has to scan the whole list
  to find the one for moving, or for a note, or for the whole pattern. The idea is to group them, so that related things sit
  together under a short heading, like `Moving` (the arrows and the jumps to the ends), `Notes` (drawing, cutting,
  lengthening and erasing a note), `The pattern` (sizing, inserting and removing steps, reconfiguring) and `Views`
  (switching between the roll and the rows), each group in its own two columns with a blank line between, the way the
  everywhere keys already sit apart. What it would mean for the code: a binding in `interface/tracker/keybindings.py` would
  take a group, a constant from a small class of group names in `user_strings/legends.py`, and `HelpDialog.key_columns`
  would lay out one block per group in the order the groups are declared, falling back to one block for a page that names no
  groups, so that the pages can be grouped one at a time. The legend wouldn't change. The test that every page's help fits
  an 80 by 24 console (`tests/interface/tracker/test_tui_help.py`) keeps its hold, so the dialog may need to scroll, or to
  put the headings in the columns' first rows, on the pattern editor.
- **Using the tracker with the basic keys alone: the arrows, Tab, Space, ENTER and ESC**: Audit
  every flow in the tracker to see that most of it can be used with the basic keys, the arrows, Tab, Space, ENTER and ESC,
  typing only when a text or number dialog asks for it, so that the letter keys stay as shortcuts for people who know them
  and nobody needs them. There are many letters to remember now, and the point is to make the tracker intuitive, with less
  to remember, by giving every action a way to be reached without a letter. The user knows some keys will stay; which, and
  how the pattern editor's views are reached, is for the audit to propose. What the audit would look at, page by page, with
  what's already there: - **The main screen and the list pages** are nearly there: Up and Down move, ENTER opens, and every
  list has a `+` row where ENTER adds. Rename, copy, move, sort and delete are letters only (`N`, `C`, `U/D`, `S`, `Bksp`),
  so a row would need a way to reach them: a dialog of actions on the selected row, perhaps on a second ENTER or on Tab, or
  action buttons under the list the way the settings pages have `Button`s. - **The settings pages** are there: Up and Down
  pick a field, Left and Right change it, ENTER types or chooses, Space or ENTER toggles, and the action rows are `Button`s
  reached with the cursor. - **The pattern editor** is the furthest away: the rows' values are typed or nudged with `[`/`]`
  on every row that takes a number (Degree, Octave, Gate, Velocity, Prob, Ratchet, Ratchet Offset, the CC rows and the
  register change rows like `BX+=`, all through `PatternRow.adjust_keys`), and the whole-pattern actions sit behind `R`,
  `S`, `I` and `D`, which could join the Reconfigure dialog or a sidebar of buttons. No key needs Shift
  (`.claude/rules/UX.md`), so the audit proposes no Shift or Ctrl with an arrow. - **Arrange** reaches every clip, scene and
  track with the arrows and opens them with ENTER, but copying, pasting, inserting and deleting are letters; the same dialog
  of actions would serve. - **The dialogs that search** (the pickers and the list pages' `/`) should say so: a picker's
  search starts as soon as something is typed, which nothing announces, and a list page's search is behind `/`, which the
  legend no longer shows. The user wants these to be a richer dialog, one that tells you that `/` or typing opens the
  search, shows the search field and its state, and perhaps offers the search as a row or button, so that it's found without
  being known. Each page's `keys()` is the complete list of what it can do, so the audit can walk every page from those and
  write up, per page, which actions have no letterless way to them and what that way would be, before anything changes. The
  user wants that write-up, and an opinion on how to group each page's keys in the F1 dialog, once the queued work is done.
  It belongs with the hotkey review and the grouped F1 dialog above, since all three are about there being less to remember.
- **The Registers page as a grid**: The Registers page (`R` on the main screen) lists sixteen settings in one column: AX
  default, AX minimum, AX maximum, AX wraps, then the same for BX, CX and DX. The user wants it drawn as a grid like the
  pattern editor's instead, with the registers' names, AX, BX, CX and DX, across the top and one row for each kind of
  setting down the side: default, minimum, maximum and wraps. Each value is then a cell, four columns by four rows, which
  reads at a glance and is much shorter. What it touches in the code: `RegistersPage` in
  `the retired Python's registers_page.py` is a `FieldPage`, a column of `Field`s, so it would become a
  page that draws its own grid, with a cursor that moves in both directions like the pattern editor's, and the keys
  depending on the row under the cursor: digits, `+` and `-`, `ENTER` and `Bksp` on the number rows, and `Space` or `ENTER`
  on the wraps row. The grid drawing of the pattern editor (`screens/pattern/grid_drawing.py`) could be shared, since it's
  the same box characters and reverse-video cursor. `Document.set_register_setting` and the refusal messages stay as they
  are, and `TestRegistersPage` would change with the keys. The help text would need rewriting for the new keys.
- **Stepping to the previous and next pattern of the group, in the pattern editor**: The user's idea: in the pattern editor,
  a pair of keys steps to the previous and the next pattern of the pattern group the open pattern is in, in the order the
  Patterns page lists them. The pattern shown changes in the view that is open, the piano roll or the rows, and nothing else
  of the navigation changes: the crumbs keep their trail with the new pattern's name, and ESC goes back to where the editor
  was opened from. The keys, the user's choice: the semicolon steps to the previous pattern and the apostrophe to the next,
  two unshifted keys side by side under the keys that step a value, used by no page. To settle with it: whether the step
  stops at the group's first and last pattern, as a cursor does, what happens for a pattern in no group (the ungrouped
  patterns as one list is the likely answer), whether the cursor keeps its step and row, what a preview that is playing
  does, and whether an editor opened from a clip on Arrange may step at all, since the clip would still play the pattern it
  names. What it would mean for the code: `PatternEditor` swapping the pattern it edits in place, with
  `Setlist.patterns_in_group` for the order, the undo history treating the step as navigation.
