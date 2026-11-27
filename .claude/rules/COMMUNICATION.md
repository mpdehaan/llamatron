# How Claude and the user work together

## Every reply that asks something

- **Top.** A reply that needs the user's answer or action MUST start with a line of equal signs, then one line `Asked YYYY-MM-DD
  HH:MM`, local time read with `date` just before writing. A reply that only reports has neither.
- **Progress first**, then questions. A step of a long process names its count: "step 3 (of 7)".
- **One subject a reply.** Questions about separate pieces of work, or separate ideas in one message ("another idea is",
  "idea 2"), wait until the current subject's are settled, open questions first; a waiting subject is named in one line, without
  questions. When the user says "questions", every open question of the current subject is
  asked again in full and each waiting subject is named in a line. A new topic leaves the open questions alone: they are named in
  one line as waiting.
- **Numbers.** Questions, proposals, concerns, findings and decisions share one running
  list, continued across replies; a number is never reused while anything numbered is open, and once all are resolved the list
  MAY restart at 1. One decision per number. A proposal gets a number and needs an answer. Items appear in ascending order, separated by a line of dashes
  (`-----------------------------------------------------`).
- **Each question**: starts with its kind (`[Confirm?]`, `[Need To Choose An Option]`, ...); opens with a full sentence saying
  what has to be decided about what; stands alone with its context, even if repeated; when asked again, is posted in full under
  its number with what has been learnt. A confirmation holds the whole of what is confirmed: values, rule, a short example.
- **Options and a recommendation.** Wherever possible, options lettered A, B, C (restarting under each number), the recommended
  one first as A, then a sentence saying Claude recommends A and why. Even a yes or no says what Claude recommends.
- **A decision Claude made** and lists for confirmation is a full question: what, where, the rule chosen, the alternative, an
  example.
- **A conversation asked for comes first.** When the user asks to talk something over, Claude finishes the step in hand and
  then has that conversation, pausing for it, rather than going on along the chain of work.
  When the user answers questions and asks in the same message for a discussion, the discussion comes now, before any of the
  work the answers agree: the answers are recorded, and the work waits until the discussion is done.
- **An explanation asked for is a separate discussion.** When the user asks for an explanation of something ("I need an
  explanation", "explain", "I don't understand"), the reply about it is a separate discussion: a long explanation for a
  reader new to it, in the tracker's words, with examples and pictures, asking no question about it, and the reply stops
  after it for the user to discuss.
- **A question from the user stops the work.** When the user asks a question, Claude answers it and stops, so that the user can weigh in on the answer and say whether to go on; Claude MUST NOT act on its own on what the question raises, without exception.
- **Asking is pausing.** A reply that asks is the last thing of its turn: no commands run after it. When only unresolved questions
  remain, reply once with them and wait.
- **The list of what's open** ends the reply, one line a number with its kind of answer: "77, yes or no." "78, choose A or B."
- **Restating**: the whole gist of the subject in a short summary, then the open questions.

## Macros

"macros" or "show macros" lists these, each with what it does; a new shorthand is added here.

- **push**: retake screenshots if needed, then `internal_tools/push_all.sh`.
- **questions**: ask every open question again in full, rephrased.
- **ask again**: work what the user just said into the open questions and ask them again in full.
- **discuss and wait**: discuss what the user said, with every related question, concern and idea, as one batch; build nothing
  until answered.
- **mockup**: draw the screen from the user's suggestion and Claude's ideas, with its questions; one mockup a reply. A mockup
  shows each field's kind (typed, stepped, chosen), an example value, its range, and the list of choices as the picker shows it.
- **continue**: go on to the next idea's questions.
- **features days=2**, "features since last night": the features that matter from git history over that span, one line each,
  leaving out fixes, refactoring and notes.
- **understand?**, **ok?**, "let me know you understand": reply with what Claude understands and stop; nothing is built,
  changed or recorded until the user answers.
- **update**: work what the user said into the whole reply being answered and redo its questions, mockups and tables.
- **separate discussion**, **sep**: each thing named before it is a topic with its own reply, explained at length for a confused
  reader, with pictures and examples, asking no numbered question; the others wait, named in one line, in the user's order.

## Building and committing

- Commit directly to main as work lands, after `internal_tools/check_before_commit.sh` passes for code. Claude MUST NOT push
  unless asked in that conversation, and then only with `internal_tools/push_all.sh` (`.claude/rules/DOCS.md`). A reply that leaves
  commits waiting says how many.
- Commit only the files Claude changed, by name, never `git add -A`; check `git status` first and mention changes Claude did not
  make.
- Agreed work is built before the next questions, and answers are acted on without asking for confirmation.
- Through an agreed list of steps, go on without stopping, committing each as it lands (a feature in three to five commits: model
  with tests, page, documents; a small refactoring step its own commit), and stop only for a question the designs don't settle.
  The recap comes at the end or at a question.
- Agreed but unbuilt designs go in `.claude/planning/DESIGNS.md` (or `.claude/planning/WIZARD_DESIGNS.md`). A design leaves
  once built. A request arriving mid-work goes into its ideas file and its place in the queue where the user says, the bottom
  by default, and the reply says where.

## The ideas files and the queue

- Every idea the user wants built is written into one of the ideas files in `.claude/features/`, by topic: `SYNTH_IDEAS.md`
  (the built-in synths, drum engines and effects), `GENERATOR_IDEAS.md` (the generators and chains), `WIZARD_IDEAS.md` (the song wizard, its players and templates),
  `DEMO_IDEAS.md` (demos and examples), `UX_IDEAS.md` (how the tracker looks and is used) and `OTHER_IDEAS.md` (the rest). A
  new topic that outgrows these gets a file of its own, proposed first.
- The ideas files are tracked in git, since several computers work on the project. Each idea is a bold name and what is
  wanted: never its status, its order, a date or a record of the conversation. Ideas describe keys by what they do. Ideas
  are added only when the user asks, and nothing in them is started unprompted. Claude keeps them organized, merges
  duplicates, moves an idea that suits another file, and deletes an idea, or trims its finished part, as soon as it is built.
- `.claude/planning/QUEUE.md` is only the order of work, tracked in git, very short, naming each idea by its file and bold
  name and saying nothing of what it is, nor any status. It is not a master file for anyone working on the project: the ideas
  files decide what is wanted, and a computer without a queue makes one from them. Instructions about order stay in the
  queue.
- Before working on a feature, Claude checks that its idea is still in its ideas file. One that is gone was likely built on
  another computer: Claude checks `git log`, drops it from the queue, and does not build it again.
- A song-wizard feature goes on its page in the same change, and the reply names the panel and field. A report on agreed work
  says of each thing: on the page, built underneath only (and why), or not started.
- A set for the user to open is given as its whole command: `sh llamatron.sh output/previews/some_folder/song.yml`.
- When the user says they'll test something, stop there without reminders.
- Claude MUST NOT file or draft bug reports or feedback on the user's behalf, to Anthropic or anyone else; it learns from
  what the user says by writing it into the rules.
- Moving, splitting and renaming files is always fine. Ideas for a better layout are brought as proposals.
- In a refactoring, the shape of the code's own names and calls is Claude's to decide, unless it has a major effect on behaviour
  or speed, or on what a person sees.
- A speed change MAY be committed without asking, provided every export is byte for byte the same and nothing is slower; a
  slower change MUST wait for the user's yes. At the end of each batch, a report MUST give the timings and call counts before and
  after (the timing tools come back with the next talk about performance).
- Flag names and layouts that don't fit. Point out where an existing feature already does what's asked, or where a new thing
  should look like an existing one.
- The user edits message wording; a change need not name the constants it touched.
- Rules carry no dates, and no file quotes the user: Claude records its own plain statement of what is wanted.
- A lasting instruction is discussed, then written into the `.claude/` file of its topic (`CLAUDE.md` only for the project as a
  whole), never only into memory. `CLAUDE.md` stays short; each file stays on its topic.
- Questions about undo and redo come to the user before anything is built (`.claude/tracker/SHARED.md`).

## Discussing a feature

- A proposal about the screen comes with a drawing of it.
- A behaviour the design doesn't settle is asked about before building. When told to keep going, each decision Claude makes is
  listed in the recap as a numbered item with the rule chosen and the alternative.
- Before designing anything musical, read the subject's file in `.claude/notes/music_theory/` and raise musicality. Once the
  `music_theory` package holds a subject, read its chapter too and answer from it, saying where Claude's own knowledge goes
  beyond the code; what Claude knows that the code lacks becomes a proposal to add it.
- The professor of music, the code maintainability expert and the Rust performance expert are agents consulted only
  when the user asks; read `.claude/features/EXPERTS.md` first.
- A recommendation weighs the least surprising musical result heavily (`.claude/format/GENERATORS.md`, "Musical answers first").
- Rewriting an example set MUST be confirmed by the user first. For every new feature, ask whether a demo fits.
- A described use of a feature is a scenario to check the design against, not a request; ask when unclear.
- When the user says they will look at something later, or sets it aside, drop it: not listed, asked about or blocking.
- A proposed wording change comes with concrete before and after examples. Proposed text is laid out as quotations at the left
  margin, a blank line around each, labelled "Before:" and "After:".
- Recaps say what was built, what was left out and why, and what's next.

## Reading the user's answers

- A suggestion of the user's is followed; where Claude thinks another choice better, it asks first, saying why.
- The user's reply is the answer. An explanation settles every question it speaks to; a general approval ("ok", "looks good")
  accepts the recommended option on every question it covers. State the reading in one line ("took 'looks good' as A on 10 and
  11") and never ask the user to confirm what they said.
- When the user's numbers don't match Claude's, match by content and note it in one line.

## How explanations are written

- In the tracker's words: what the user sees and presses, naming the existing feature. Code names after, if at all; special
  methods, never "dunders".
- No made-up words: name things as the screen or the user does, in full; ask the user for a group name if one would help.
- Only the program acts: the Realizer draws, tests and decides; a table or field never does.
- The page first: open by naming the page ("On the clip page, ..."), and name it again when it changes.
- A letter key is always followed by what it does: `C` (Copy).
- Pronouns: name a thing in full first ("the Velocity cell on step 3"); a pronoun MAY follow only where it can mean nothing else.
- Gauges by direction and measure ("the vertical Degree gauge"); the cursor by the row, step or cell that holds it.
- A setting by object, field and value: "the clip's Advance field set to "Off"". Values in double quotes.
- Conditions as sentences: "when the pattern is used by one track, `L` plays at once"; list items start with "when" or "if".
- Examples start "In an example scenario,", are complete (before, key, after), use few plain objects, and introduce made-up names
  as made up.
- Anything about tracks, scenes and clips draws the Arrange grid first as a table (a column per track, a row per scene, each cell
  the clip's pattern and the setting in question, the cursor and key marked), then the words. Every pattern named is shown, as a
  piano roll or its rows. A chain is shown as a table of its generators, in order, with each setting's value.
- The program is "llamatron". American spelling. "Accumulators" means draws.

## The user's words

What the user says, what the tracker shows for it, and what the code calls it. Explanations to
the user use the middle column, the words on screen. Where one word could mean two things, the
row says which, and a reply says which too.

| The user says | The tracker shows | The code calls it |
| --- | --- | --- |
| accumulators, draws | Draws, `AD` to `HD`, and the rows `Note+=`, `Vel+=` and `Reset` | `DrawName`, `draws`, `RegisterRow` |
| the set, the file, the setlist | the set, named by its file in the crumbs | `Setlist`, held by `Document` in the tracker |
| song | a song of the set, one of which is current | `Song`, `document.song()` |
| scene, track | a row and a column of Arrange | `Scene`, `Track`. Rendered, a `ClipRow` and a `ClipColumn` |
| clip | a clip on Arrange | `ClipSlot` is what a track plays in a scene, as the file stores it. `Clip` is the finished notes in the grid. Messages always say clip |
| pattern | a pattern, shared by every song | `Pattern` |
| a wizard panel | one part of the song wizard's tree, such as Genre, Band, a player, Composition, Chords, a section or Apply, with the fields shown at its right. Always "wizard panel" when speaking to the user, never "branch", which reads as a git branch | `Branch` and its subclasses in `interface/tracker/screens/wizard/` |
| the main screen, the main menu | the grid of cells the tracker opens on | `MainPage` |
| the pattern editor | the page that edits one pattern, in either view | `PatternEditor` |
| the roll, the piano roll | the pattern editor's piano roll view | `PianoRoll`, `RollDrawing`, `editor.roll` |
| the rows, the editor, the grid | the pattern editor's rows view, which Tab's legend calls `to editor` | `PatternRows`, `PatternDrawing`, `editor.rows_view` |
| sections, the accordion | the headings `+ Basics` to `+ Mute When` in the rows view | `SectionRow`, `SECTIONS`, `RowSection` |
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
| munge | Munge, `M` in the pattern editor | `Munge`, `munges_in_order`, and `Pattern`'s methods that rearrange, copy, clear and smooth its steps |
| reconfigure | the dialog `R` opens in the pattern editor | `Reconfigure` |
| generators, arps, AutoRatchets | Generators, with Arpeggiators and AutoRatchets under it | `Arp`, `AutoRatchet`, `ArpSettings`, `AutoRatchetSettings` |
| chain | a chain of generators a clip runs | `Chain` |
| groove, swing | Grooves, with the factory grooves first | `Groove`, `FactoryGroove` |
| kind, of a scale | Kind on the Scale page, and scale type in a message | `ScaleType` |
| export, render | export, always. Render is the code's word for playing a song into clips | `SongRealizer` renders, and each `Exporter` in `exporters/` writes with `export()` |
| Live, Ableton | Ableton Live set, in the export dialog | `AbletonProject` |
| the legend, the footer | the keys listed at the bottom of a page | the keys a page offers, each class's `IN_LEGEND` in `src/tracker/src/generated/keybindings.rs` |
| a key binding, a hotkey | a key with its name in the legend and what the key does | a `Binding` in the page's class of `src/tracker/src/generated/keybindings.rs` |
| the everywhere keys | Ctrl+S, Ctrl+O, Ctrl+X, Ctrl+T, Ctrl+Z, Ctrl+Y, F1 and F2 | `everywhere_keys`, `keybindings.Page.EVERYWHERE` |
| the status line | the dim line above the legend | `StatusLine`, `Page.say` |
| the crumbs | the path at the left of every header | `Crumb`, `crumbs` |
| a picker | a dialog with a list of choices | `ChoiceDialog`, `GridChoiceDialog` |
| a settings page, a list page | a page of fields, and a page of rows with a `+` row at the bottom | `FieldPage` with `Field` and `Button`, and `ListPage` |
| protected | the Protected toggle on the File/Global page | `protected`, `file_is_protected` |
| the demos, the examples | the sets in `examples/` | every set in `examples/` |
| the ideas files | the `*_IDEAS.md` files of `.claude/features/`, one a topic | |
| the support folder | nothing on screen: `internal_tools/`, the folder of development tools and scripts | `internal_tools/` |
| follow action, advance | Follow action on the clip page, "With Scene" or "Off", and Default follow action on the File/Global page | `FollowAction`, `ClipSlotSetting.FOLLOW_ACTION`, `follow_action_of` |
| launch together, advance together | Launch together on the Scene page, and `┆` after a scene's name on Arrange when off | `SceneSetting.LAUNCH_TOGETHER`, `Scene.launches_together` |
| an instrument, a device | an instrument on the Instruments page, with its Device and Channel; a song plays in real time once a track's instrument can sound | `Instrument`, `Section.INSTRUMENTS`, `TrackSetting.INSTRUMENT`, `Song::plays_in_real_time` |
| the Realtime Sender Process | nothing on screen: the separate process that plays MIDI in real time, fed each clip's events by the player | `RealtimeMIDISenderProcess` |
| the player | nothing on screen: what launches scenes and clips and follows the follow actions | `Player`, on a `Score` |
| the Realizer | nothing on screen: the part of llamatron that plays a song into clips, draws the draws and tests the statements as it evaluates the patterns and the other objects | `SongRealizer`, with a `ClipSlotPlayer` and a `PatternPlayer` for each clip |
| the transport | nothing on screen: the tracker's side of real-time playback, which every page asks what plays | `Transport`, `app.transport` |
| play, stop, the corner | Space on Arrange, the `▶ song` and `■ song` cell over the scene names, the `▶` and `■` beside each clip | `ArrangePage.play_song`, `play_scene`, `play_clip`, `stop_playing_all`, `stop_clip`, `on_corner` |
| listen, preview | `L` (Listen) on the clip page and in the pattern editor, and the clip page's Play and Stop buttons | `listen`, `listen_to_pattern` in `src/tracker/src/screens/listening.rs` |
| the lights | the red `■`, the green `●` after a track's name, the scene bar and each playing clip's bar filling as read heads, the clock `▶ 0:22 / 3:00` | `Style.PLAYING`, `Style.SOUNDING`, `LengthBar.draw(played=)`, `MSG_PLAYING_CLOCK` |
| silence, the emergency stop, Ctrl+T | Ctrl+T on every page, `SILENCE` in the F1 dialog | `Page.SILENCE`, `Transport.silence_everything`, `PlaybackEngine.silence` |
