# How Claude and the user work together

These are the user's rules for how Claude talks to them and works with them on llamatron, kept
apart from the rules for the code (`.claude/STYLE.md`) so that they can be reviewed on their own.
`CLAUDE.md` imports this file, so it's in force in every session.

## Every Reply That Asks Something

The user's rules for a reply that puts anything to them, gathered here so that each reply can be checked against one list.

- **The line of equal signs.** A reply that needs the user's answer or action starts with a line of equal signs, before any
  other word, so that the user, scrolling back through a long reply, sees where to stop. A reply that only reports has none.
- **The time it was asked.** Straight under the line of equal signs comes one line with the date and time the reply was
  written, local time, like `Asked 2026-11-13 14:05`, read from the computer's clock with `date` just before writing, so
  that the user, coming back after a long while, sees when Claude paused (the user's ask). Only once, at the top.
- **Progress first.** What was built since the last answers comes first, then the questions.
- **One subject at a time.** When a reply covers separate pieces of work, like a demo and the pattern editor, it asks about
  one and waits until that subject's questions are settled before the next, since batches that mixed subjects were too long
  to answer. When the user asks for the open questions, every one is listed in full in that reply, whatever its subject.
- **Numbers.** Questions, proposals, concerns, findings and decisions put to the user share one running list of numbers,
  continued across replies, so that the user can answer "on 11, yes". A number is never reused while anything numbered is
  open, and one reply never holds two lists that both start at 1. A question keeps its number until it's answered; once
  every number is resolved, the next may start again from 1.
- **In order.** Whatever is numbered is presented in ascending order of its numbers, never one out of place.
- **Separated.** Two numbered questions in one reply are separated by a line of dashes,
  `-----------------------------------------------------`, so that each stands apart.
- **The kind of answer.** A question says at its start what is wanted: `[Confirm?]` for a yes or no, `[Need To Choose An
  Option]` for a choice of lettered options, and the like; with several kinds in one reply, sections may group them.
- **The opening.** A question opens with a complete sentence saying what has to be decided and about what, like "I need to
  decide how a cursor key behaves on the clip page", before any example or choice, never with a heading alone.
- **Standing alone, and asked again in full.** Each question carries enough context to be understood on its own, the thing
  it's about introduced before it's asked, even when that repeats an earlier message, since the user doesn't scroll up. A
  question asked again, referred to by number or clarified is posted again under its number in full, with what has been
  learnt since worked in and nothing of the old context dropped, never a number with a few words after it. A confirmation
  holds the whole of what's confirmed: the values, the rule and a short example, never "as above" or "the table above".
- **Choices, always with a recommendation.** Wherever a question can offer options, it does: each a capital letter, A, B,
  C, starting again at A under each number, each named in full. After the options, a sentence of its own says which Claude
  recommends and why. The user values the recommendation, so a question offers options and a recommendation whenever it can,
  and even a yes or no question says what Claude recommends (the user's rule).
- **Decisions to confirm.** A decision Claude made and lists for the user to confirm is written as a full question: what was
  decided and about what, on which page, the rule chosen, the alternative and a short example, never a one-line note.
- **Restating.** When the user asks for something to be restated, the whole gist of the subject is restated, everything
  decided and proposed about it, in a short summary, and then the open questions.
- **The list of what's open.** A reply that leaves questions open ends with them, each number on a line of its own with the
  kind of answer it takes: "77, yes or no." then "78, choose A or B."

## Building and committing

- Commit directly to main when asked, as you go, with the full suite passing when the commit changes
  code (`internal_tools/check_before_commit.sh`, run by Claude, since there is no git hook, the user's
  rule in `.claude/TESTING.md`), and never push unless asked in that conversation.
- Every Markdown file outside `.claude/` (`GUIDE.md`, `README.md`, `INSTALL.md`, `docs/ARCHITECTURE.md`,
  `docs/WHY_LLAMATRON.md`, `docs/MIDI_SETUP.md`, `docs/RECORDING.md`, `docs/DEMOS.md` and the rest) is the
  user's own writing, whose phrasing the user very likely cares about, since the user edits them to
  say what they want (the user's rule). Claude makes only minimal corrections there, only to remove
  an inaccuracy, keeping the user's words, and never rewrites, rewords, moves or tidies the prose on
  its own. Each such change is proposed first, exactly, as a before and an after, and made only once
  the user confirms it. A feature that needs new text in those files comes with that text proposed
  the same way. The one exception is a path, a file name or a command a change made wrong, like a
  renamed script, which Claude always fixes without asking (the user's rule). Every reply that follows
  a change to them brings a synopsis of exactly what changed, grouped by document. The generated parts,
  the diagrams and the demo table, are rewritten by their tools as ever. `CLAUDE.md`, `dev_notes/IDEAS.md` and `dev_notes/DOCS_IDEAS.md`
  are Claude's, like the files in `.claude/`: `CLAUDE.md` holds the rules for Claude, whose style
  doesn't matter, and the ideas file's language is for Claude, which may reword it (the user's rule),
  so Claude keeps all of them consistent and correct as needed. For now, until the work reaches the video tutorial, the
  user has given Claude leave to edit the documents as it judges best and report what changed, rather than proposing each
  change first.
- The documentation website is published whenever its sources change, without asking (the user's standing
  permission): when a commit changes `GUIDE.md`, a page in `docs/`, a new page among them, or what builds the site
  (`internal_tools/stage_docs_site.py`, `internal_tools/build_docs.sh`, the VitePress configuration), or retakes screenshots in
  `docs/screenshots/` (which `README.md`, GitHub's front page, shows too), Claude runs
  `internal_tools/build_docs.sh`, commits `web_docs/` and runs `internal_tools/publish_docs.sh`, which pushes the
  `gh-pages` branch alone. That is the one push Claude makes unasked; `main` is still pushed only when asked.
- Claude commits only the files it changed, naming them, never `git add -A`, and checks
  `git status` first: a change it didn't make, like a hand edit of the user's in progress, stays
  out of its commit and is mentioned, so that the user's work is never swept into Claude's.
- Agreed work is built before the next questions are asked, so that a reply carries progress as well as questions, and
  the user's answers are acted on without asking them to be confirmed. A message that asks a question ends the turn: what
  depends on the answer waits for it.
- The agreed work not yet built is kept in order in `dev_notes/QUEUE.md`, Claude's file: an item leaves it once built, and a
  request that comes in while Claude works goes where the user says, the bottom unless told otherwise, and Claude says where
  it went (the user's rule).
- When the user says they'll test something, Claude stops there and never reminds them to test (the user's rule).
- When working through an agreed list of steps, Claude goes on from one step to the next without
  stopping to report, committing each as it lands, and stops only for a question the designs
  don't settle (the user's rule). The recap comes when the list is done or a
  question arises.
- A clean layout and code quality matter more than a file's history in git: moving, splitting and
  renaming files is always fine. Ideas for a better architecture or layout are brought to the
  user whenever there are any, as proposals to approve.
- A change made for speed is reported with its timings before and after (`internal_tools/time.sh`), and the
  user is asked whether to commit.
- Flag names and layouts that don't fit, and suggest better ones. Point out where a feature that
  already exists does what's being asked, or where a new thing should look like an existing one,
  because consistency and usability matter more to the user than novelty.
- The user edits the wording of messages themselves, so a change doesn't need to name the `MSG_`,
  `ERR_` or `HELP_` constants it touched.
- An idea in `dev_notes/IDEAS.md` starts its heading with its priority, like `(High priority)`, where the
  user has given one, so that the file can be sorted by priority when asked, with no separate
  list of what comes first, and it describes keys by what they do rather than by their letters,
  since the letters change (the user's rules).
- An idea in `dev_notes/IDEAS.md` is removed as soon as it's built, without being asked, and ideas are added
  to it only when the user asks. Nothing in it is started or proposed unprompted: the user picks
  what to do from it, one item at a time.
- The rules carry no dates: a choice is marked as the user's design or rule, never dated (the user's
  rule). `.claude/DECISIONS.md`, the history of the choices, is where dates belong.
- Questions about undo, redo and what they should do to a page come to the user before anything is
  built, since the behaviour was agreed in detail (`.claude/TRACKER.md`, "Undo and redo").
- Claude records what it understands of what the user said, never the user's literal words: a rule, a decision or a note
  is written in Claude's own plain statement of what is wanted, which Claude may edit as its understanding improves, and no
  file quotes a reply of the user's (the user's rule).
- When the user asks for a rule, or gives an instruction meant to last, it's discussed first, and
  then written into the repository's rules rather than into Claude's memory, which a reset can
  lose: into the `.claude/` file whose topic it belongs to (this file for how Claude and the user
  work together, `STYLE.md` for the code, `TESTING.md` for the tests, `UX.md` for how the text UI
  behaves, `FORMAT.md` for the model, `TRACKER.md` for how each page is built), and into
  `CLAUDE.md` only when it's about the project as a whole.
  `CLAUDE.md` stays short and orderly, and each other file stays on its topic.

## Discussing a feature

- A proposal about the screen comes with a drawing of it, a page or a dialog as the console would show it, since the user
  judges a layout by seeing it (the user's rule).
- A behaviour the design doesn't settle is asked about before it's built, not assumed, unless
  the user has said to keep going without questions. When Claude has been told to keep going
  and has to decide something itself, each such decision is listed in the recap as a numbered
  item of the running sequence, with the rule it chose and the alternative, so that the user
  can answer "1 is wrong". The user dislikes assumptions being made at all, so fewer, asked
  earlier, is the rule.
- A recommendation weighs the least surprising musical result heavily, which usually wins over
  what is simplest to build (`.claude/FORMAT.md`, "Musical answers first").
- Rewriting an example set, moving a feature's demonstration into it or changing what it plays, is always confirmed by
  the user, and asked about upfront, before it's done, when Claude thinks it a good idea (the user's rule).
- For every new feature, Claude asks whether a demo for it is appropriate, a set of its own or a
  place in an existing one, and the user confirms; no demo is made or skipped without asking
  (the user's rule).
- When the user describes how someone could use a feature, that is a scenario to check the
  design against, not a request for new behaviour: a story about one instrument playing every
  track once became a proposed shortcut that was not wanted. When it is unclear whether the
  user is describing a use or asking for something to be built, Claude asks before proposing
  or building anything.
- When the user says they will look at something later, Claude drops it: it isn't listed among
  the things waiting, asked about again or treated as blocking anything, and the user comes back
  to it when they decide to. The same goes for anything the user has set aside: Claude goes on
  with the rest until the user says to stop.
- A proposed change of wording comes as a general proposal with concrete before and after
  examples, so that the user can judge it on real messages.
- Proposed text, a before and an after or a new passage for a document, is laid out on its own: a
  blank line above and below each block, each block a quotation starting at the left margin rather
  than indented under a numbered question, and a short line naming it, "Before:" or "After:", above
  it, so that the user reads it as the document will show it (the user's rule).
- Recaps say what was built, what was left out and why, and what's next, so that a reader who only
  sees the last message has the whole picture.

## Reading the user's answers

- The user's reply is the answer. An explanation or a description given in reply to open
  questions settles every question it speaks to, and a general approval, like "ok", "looks good"
  or "otherwise sounds good", accepts Claude's recommended option on every open question it
  covers. Claude acts on that reading and states it in one line, like "took 'looks good' as A on
  10, 11 and 12", and the user corrects it if it's wrong. Claude never asks the user to confirm
  what they said. When an answer does raise something new, Claude may ask about that as a new
  question.
- When the user's numbers don't match Claude's, as when the user answers "35" about Claude's
  34, Claude matches the answers by what they say, notes the match in one line, and goes on.

## How explanations and examples are written

- **In the tracker's words.** Usability and interface points are explained by what the user
  would see and press, in the words the tracker shows on screen, naming the existing feature they
  build on. Code names come after, if at all, and software components go by their formal names:
  `__init__` and the like are special methods, never dunders.
- **The page first.** Anything said about the text UI, a question, an example or an explanation,
  opens by naming the page, "When you are on the clip page, ..." or "In an example scenario, on
  the Arrange page, ...", before any key or cell, and names the page again whenever the page
  changes, since the same key means different things on different pages.
- **Keys.** A letter key is never named alone: what the key does follows in parentheses, every
  time, like `C` (Copy), `S` (Sort) or `R` (Reconfigure). The same goes for a mark that is a key,
  like `[` and `]` (Length) on the piano roll.
- **No pronouns.** Explanations and examples write the name of the thing, like "the Velocity cell
  on step 3" or "pressing Space on the Grab row", never "it", "this", "its cells" or "there",
  because the user can't tell which of several things a pronoun means. This rule is the one most
  often broken, and the user wants it stressed.
- **Gauges and the cursor.** A gauge is named by its direction and what it measures, never as
  "the gauge" or "the bar": the vertical Degree gauge in the pattern editor's rows, where the bar
  on each step rises to the step's degree; the vertical offsets gauge in the offsets editor,
  where the bar on each step rises or falls from the zero line; the horizontal length bars on
  Arrange, as long as a scene or a clip plays. The cursor is named by the row, step or cell that
  holds it. Where a word could still mean more than one thing, write "for example" and give one.
- **Settings and values.** A setting is named by the object it is on and the field, then the
  value, like "the clip's Advance field set to "Off"", never by the value alone, like "a clip set
  to Off". A value a field can take is written in double quotes, like "With Scene", every time.
- **Conditions.** A condition and what follows from it are written as a sentence, "when the
  pattern is used by one track, `L` plays at once", never as a label and a colon. In a list of
  cases, each item starts with "when" or "if" and says "then" where the sentence needs it.
- **Examples.** An example starts with "In an example scenario," so that it reads as one case and
  not as what is always true. It is complete: what the pattern or page holds before, which key is
  pressed where, and what is seen after. Its objects are few and plain, two tracks and two scenes
  rather than a song's worth, and a name made up for it is introduced as made up the first time,
  like "an instrument called, say, `organ`".
- **The clip grid as a table.** An example that involves Arrange's scenes and tracks, including
  one about a single clip or the clip page that ends in playback, is drawn as a table: one column
  per track and one row per scene, named, each cell naming the clip's pattern and, in parentheses,
  the setting the example is about, like `fill` ("Off"). The table marks the cursor and the key
  pressed, with `▶ Space here` or `◀ cursor`, and the sentence after it says the same in words,
  naming the page, the field or cell and the key.
- **Spelling and words.** Spelling is American, as the program's messages are: "forever", not "for
  ever". When the user says accumulators, read it as registers, the program's word, which is the
  one written everywhere. The glossary below has the rest of the user's words.

## The user's words

What the user says, what the tracker shows for it, and what the code calls it. Explanations to
the user use the middle column, the words on screen. Where one word could mean two things, the
row says which, and a reply says which too.

| The user says | The tracker shows | The code calls it |
| --- | --- | --- |
| accumulators, registers | Registers, `AX` to `DX`, and the rows `+Note`, `+Vel` and `+=` | `RegisterName`, `registers`, `RegisterRow` |
| the set, the file, the setlist | the set, named by its file in the crumbs | `Setlist`, held by `Document` in the tracker |
| song | a song of the set, one of which is current | `Song`, `document.song()` |
| scene, track | a row and a column of Arrange | `Scene`, `Track`. Rendered, a `ClipRow` and a `ClipColumn` |
| clip | a clip on Arrange | `ClipSlot` is what a track plays in a scene, as the file stores it. `Clip` is the finished notes in the grid. Messages always say clip |
| pattern | a pattern, shared by every song | `Pattern` |
| the main screen, the main menu | the grid of cells the tracker opens on | `MainPage` |
| the pattern editor | the page that edits one pattern, in either view | `PatternEditor` |
| the roll, the piano roll | the pattern editor's piano roll view | `PianoRoll`, `RollDrawing`, `editor.roll` |
| the rows, the editor, the grid | the pattern editor's rows view, which Tab's legend calls `to editor` | `PatternRows`, `PatternDrawing`, `editor.rows_view` |
| sections, the accordion | the headings `+ Basics` to `+ Reg. Mod` in the rows view | `SectionRow`, `SECTIONS`, `RowSection` |
| the pinned rows | Degree and Octave, which stay at the top of the rows view | `PINNED_ROWS` |
| the Degree gauge | the vertical Degree gauge in the rows view, a bar on each step rising to the step's degree | `DegreeRow` |
| the offsets gauge | the vertical offsets gauge in the offsets editor, a bar on each step rising or falling from the zero line | `SignedGauge`, `OffsetsEditor` |
| the length bars | the horizontal length bars on Arrange, as long as a scene or a clip plays | `LengthBar`, `SCENE_BAR`, `CLIP_BAR` |
| the box, the frame | the double-lined box around what Arrange's cursor is on | `Frame` |
| the triangle, the mark | `▶` at the left of the selected row | `SELECTED_MARK`, `cursor_mark` |
| the slash, a blocked cell | a dim `/` in a cell that can't take a value | `MSG_BLOCKED_CELL`, `PatternRow.blocked` |
| a toggle, the dot | `●` in a cell that's on | `ToggleRow`, `MSG_TOGGLE_ON` |
| the pencil, the knife, the eraser | Space, `K` and `Bksp` on the piano roll | `PLACE`, `KNIFE` and `ERASE` of `keybindings.PianoRoll` |
| ghosts | the thin dim lines of a chord's other notes on the piano roll | `ghost_cell`, `ghosts_of` |
| entry size | Entry size, how long a note drawn on the piano roll lasts | `entry_size` |
| grab | the Grab row of a pattern and the Grab track of a clip | `grab`, `grab_track`, `GrabRow` |
| munge | Munge, under `R` in the pattern editor | `Munge`, and `Pattern`'s reverse, pivot and shuffle methods |
| reconfigure | the dialog `R` opens in the pattern editor | `Reconfigure` |
| generators, arps, AutoRatchets | Generators, with Arpeggiators and AutoRatchets under it | `Arp`, `AutoRatchet`, `ArpSettings`, `AutoRatchetSettings` |
| chain | a chain of generators a clip runs | `Chain` |
| groove, swing | Grooves, with the factory grooves first | `Groove`, `FactoryGroove` |
| kind, of a scale | Kind on the Scale page, and scale type in a message | `ScaleType` |
| export, render | export, always. Render is the code's word for playing a song into clips | `SongRenderer` renders, and each `Exporter` in `exporters/` writes with `export()` |
| Live, Ableton | Ableton Live set, in the export dialog | `AbletonProject` |
| the legend, the footer | the keys listed at the bottom of a page | `keys()`, `shown_keys()`, each class's `IN_LEGEND` in `tui/keybindings.py` |
| a key binding, a hotkey | a key with its name in the legend and what the key does | a tuple in the page's class of `tui/keybindings.py`, bound with `self.bind` |
| the everywhere keys | Ctrl+S, Ctrl+O, Ctrl+X, Ctrl+T, Ctrl+Z, Ctrl+Y, F1 and F2 | `everywhere_keys`, `keybindings.Page.EVERYWHERE` |
| the status line | the dim line above the legend | `StatusLine`, `Page.say` |
| the crumbs | the path at the left of every header | `Crumb`, `crumbs` |
| a picker | a dialog with a list of choices | `ChoiceDialog`, `GridChoiceDialog` |
| a settings page, a list page | a page of fields, and a page of rows with a `+` row at the bottom | `FieldPage` with `Field` and `Button`, and `ListPage` |
| protected | the Protected toggle on the Set File page | `protected`, `file_is_protected` |
| the demos, the examples | the sets in `examples/` | every set there but the pieces, and the pieces, `PIECES` in `test/rendering.py` |
| the ideas file | `dev_notes/IDEAS.md`, and `dev_notes/DOCS_IDEAS.md` for the documentation's ideas | |
| the support folder | nothing on screen: `internal_tools/`, the folder of development tools and scripts (the user's word, since there is no other support folder at the top) | `internal_tools/` |
| follow action, advance | Follow action on the clip page, "With Scene" or "Off", and Default follow action on the Set File page | `FollowAction`, `ClipSlotSetting.FOLLOW_ACTION`, `follow_action_of` |
| launch together, advance together | Launch together on the Scene page, and `┆` after a scene's name on Arrange when off | `SceneSetting.LAUNCH_TOGETHER`, `Scene.launches_together` |
| an instrument, a device | an instrument on the Instruments page, with its Device and Channel; the Real Time switch on the main screen | `Instrument`, `Section.INSTRUMENTS`, `TrackSetting.INSTRUMENT`, `Setlist.is_real_time` |
| the Realtime Sender Process | nothing on screen: the separate process that plays MIDI in real time, fed each clip's events by the player | `RealtimeMIDISenderProcess` |
| the player | nothing on screen: what launches scenes and clips and follows the follow actions | `Player`, on a `Score` |
| the transport | nothing on screen: the tracker's side of real-time playback, which every page asks what plays | `Transport`, `app.transport` |
| play, stop, the corner | Space on Arrange, the `▶ song` and `■ song` cell over the scene names, the `▶` and `■` beside each clip | `ArrangePage.play_song`, `play_scene`, `play_clip`, `stop_playing_all`, `stop_clip`, `on_corner` |
| listen, preview | `L` (Listen) on the clip page and in the pattern editor, and the clip page's Play and Stop buttons | `listen`, `listen_to_pattern` in `tui/screens/listening.py` |
| the lights | the red `■`, the green `●` after a track's name, the scene bar and each playing clip's bar filling as read heads, the clock `▶ 0:22 / 3:00` | `Style.PLAYING`, `Style.SOUNDING`, `LengthBar.draw(played=)`, `MSG_PLAYING_CLOCK` |
| silence, the emergency stop, Ctrl+T | Ctrl+T on every page, `SILENCE` in the F1 dialog | `Page.SILENCE`, `Transport.silence_everything`, `PlaybackEngine.silence` |
