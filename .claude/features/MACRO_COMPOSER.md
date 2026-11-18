# The MacroComposer

Reference notes for Claude on the MacroComposer, the user's name for the tool that makes a set from structured data that says
what to play. It isn't imported: read it before working on `src/llamatron/macro_composer/` or `internal_tools/macro_compose.py`.
What is agreed and not yet built is in `.claude/features/WIZARD_DESIGNS.md`. `.claude/features/GENRES.md` holds the genre
library's rules and `.claude/format/EXAMPLES.md` the rules for the sets in `examples/`.

## The User's Rules

- **It fetches nothing and looks nothing up.** No code of the MacroComposer reads the internet, searches for lyrics or tablature,
  lists sites that have them, or finds a song or an artist for someone. It may read the corpus files for the mashups. No test
  holds this; it is kept by reading.
- **No melody of an existing song is recorded anywhere in the tree**, and no lyrics. Chord progressions, forms and the like may
  be given as input.
- **A style template comes from clean research alone**, Claude's own understanding of the style, never from memory of the
  homages and never from the user's books, of which nothing goes into the tree. A template names no band, artist or work.
- **The players are always imaginary**, and no real player is cited.
- **A homage's or a mashup's players are picked by how its inspiration's players play**, once the engine is good enough to make
  one: Claude uses what it knows of how skilled or showy each instrument's player was to choose each instrument's complexity,
  so a band with a plain drummer and a virtuoso bassist is made with those numbers. Only the numbers are written; no real
  player is named, as ever.
- **The existing examples and homages are not rewritten** by it, and nothing it makes is promoted to `examples/` until the user
  says. Trial songs live in `previews/macro_composer_design/`, ignored by git.
- **The MacroComposer decides nothing.** A song's picks decide every trait; the song's own material is kept apart from the
  picks, so that a song can be made again with other picks. The theme is full control, with randomness offered when a person
  is unsure, and an input Claude writes may override a great deal.
- **Structured data, never a string to be parsed**: a bar is a list of named things (`.claude/STYLE.md`, "Data that is an array
  is held as an array").
- **Easy to change afterwards**: every chord goes through the Progression generator, a strummed guitar through Guitarify, and
  electronic styles use the arpeggiator. Every track is made with a Rush and a Drag, doing nothing until set.
- **A made song's tracks** are ordered chords first, then the lead and the backing, the bass, and the drums last, for new songs
  only (`.claude/format/EXAMPLES.md`).
- **A wizard in the tracker is to use it later.** Files hold numbers and plain names; the names people see, such as a player's,
  are made for people where they are shown.
- **The drums are always split into tracks**, in every genre: the kick, the snare or clap, the hats and each other drum a track
  of its own, so that each can enter, leave and be shaped alone (the user's rule).
- **The floor is a genre's idea, not every genre's**: the kick and bass switched on and off as one belongs to the dance genres
  that have it, and is researched genre by genre before it is given to one, drum and bass above all, where on and off may be too
  simple; a genre unlike those, such as an early synthesizer novelty piece or a baroque piece on synthesizers, may want no
  drums at all, and is never given a floor or a kick by default (the user's rule).
- **Timing can be tight**: how closely a part sits on the grid is tunable by a person and defaults by genre, exactly on the
  grid where the genre is locked in, looser where the genre has a groove. The user values tight, on-the-grid timing in the
  genres that have it, and others will want otherwise, so neither is forced (the user's rule).
- **The hook is vital** (the user's rule, about how Claude designs and never about what a person is told): a song has a hook,
  a short phrase a listener remembers, and the song keeps bringing the listener back to the hook. Every default is built around
  that: every ready-made form, melody engine, modifier and amount of variance, as it arrives, puts the hook early, returns to
  the hook often, and returns recognisably after anything that departs, a solo, a bridge, a change of key, a section of high
  variance; where a song changes partway, the defaults carry a hook into the new part, in that part's rhythm and sound; and the
  design supports hooks well, several of them where wanted. None of this is enforced on a person: the wizard never warns,
  notes or refuses when a person's choices make a hook rare or leave a song without one, since a bad choice in music is the
  person's to make. In a song with several hooks, a theme may be marked a hook, and what other parts quote is the hook theme
  most recently played, with nobody saying so; a section's changes also hold a Main hook field in a closed Advanced section,
  for a person who wants another hook quoted on purpose (the user's choice).

## The Parts

All in the package `src/llamatron/macro_composer/`, since code that would ship with the program lives in `src/llamatron/` and `internal_tools/` holds only the scripts that launch things and the tools for builds and analysis (the user's rule). `internal_tools/macro_compose.sh` (`internal_tools/macro_compose.py`) runs it; its messages are in `src/llamatron/strings/macro_composer.py` and `src/llamatron/strings/errors.py`:

- `composer.py`: an input made into a set's data. Its docstring lists an input's fields: what the song is called, its scales,
  tempo and feel, instruments, tracks, generators, chains, parts (a tune's lines, a drum's hits or a pattern as written), bands
  and the form, the scenes in order.
- `decomposer.py`: an existing set written as an input (`--decompose`), and `--same-as` compares an input with a set.
  `tests/data/macro_composer_inputs/` holds three demos written as inputs, made again when their demos change.
- `notation.py`: how a tune's lines and a drum's hits become a pattern's rows, and the drum kit's names.
- `shaping.py`: the velocity of the parts an input lists, shaped by the song's feel.
- `arranger.py`: a song's picks and a style template made into an input (`--arrange PICKS --out SET`, `--keep-input INPUT`).
- `melody.py`: the melody engines, each a class that makes a section's tune from a style's habits where the song gives none:
  `StepWalk`, the singable first one, and `Serial` and `Evolving`, its subclasses. `operations.py` holds the moves on a row that the serial
  engine makes and that turn a phrase so that repeats evolve: backwards, upside down, moved, rotated.
- `players.py`: the complexities and the names people see for them.
- `style_templates/`: blues, rock, sixties pop, electronic, and soul and funk.

`tests/macro_composer/test_composer.py` and `tests/macro_composer/test_arranger.py` test them.

## A Style Template

A YAML file whose comments at its top explain each field. In short:

- `name`, `title`, `genre`, `feel` (backbeat, four, swing or down), `phrase_bars`, `loudness` by drum and role.
- `templates`: the kinds of the style, each a set of picks.
- `traits`: each trait's values, each with its `share` (how common it is; a trait's shares sum to 100, and the wizard
  recommends the commonest) and what it `needs` of other traits. A drum value gives a `bar`, each drum's hits; a fill gives a
  `fill`; a pitched value gives a `sound` and a `figure`, bars of notes written over chord one by degree, steps, octave,
  accidental or chord, with `generators` such as Guitarify or an arp; a chord value gives a `pattern`, chords `by_section`,
  and a `scale_type`.
- `roles`: the tracks in order, each with its trait, its octave and its `player`.
- `players`: for each instrument and complexity, what the player says for people and how the player decorates.
- `sounds`: General MIDI numbers.
- `sections`: each kind of section's bars, what plays, the plan of its tune, its chords, whether it is held, and its
  `intensity`, `crash` and `picks` (below).
- `forms`: the layouts a song of each kind may take, each with a name, a share and its sections; `usual` serves a kind that
  lists none. Electronic has them so far; its kinds include house, techno, minimal techno, trance, drum and bass, dubstep,
  ambient, downtempo and big beat.
- `melody`: the sketcher's habits: grid, line length, span, home, ladder and rhythms, which may be keyed by meter.

A step is a bar's length divided by the grid, so a shuffle has twelve steps to the bar.

## A Song's Picks

`name`, `title`, `description`, `style`, `template` (the kind), `picks` (traits changed from the kind's), `players` (a
complexity for each instrument), `key` (root and type), `tempo`, `seed`, `sections` (the song's own, or changes to the
style's) and `form`. A song's pick wins over the kind's.

A song's `form` is the sections in order, or the name of one of the forms its style suggests for its kind; a song with no
`form` may give a `length` in seconds and takes the suggested form that comes nearest, or gives neither and takes the
commonest (`form_of` in `arranger.py`). The user's rule for length: a longer song is never the same form repeated, but more
themes and changes, so each kind's longer forms are written with a second theme over other chords, a strip-down or another
breakdown. Key changes for a longer song, and asking the person about them, are wanted and not built. A section in which
nothing of the song's picks plays, such as pads alone in a song with no chord part, is left out.

## Melody Engines

A song picks the engine its tunes are made by (`melody_engine`), else a role names one (`engine`), else the style's melody
habits do, else the step walk. A role may name its `voice`, so that several voices of one song differ, and give `habits` of
its own; a song's `melody` adds habits too.

- **Step walk**: a rhythm cell of the style for a line, the style's ladder walked by step, long notes landing on the chord.
- **Serial** (the user's design): the row is every note of the song's scale once, in an order the seed draws, so it works in
  whatever scale is set; with the habit `chromatic` it is all twelve notes. Every line is the row and its forms, backwards,
  upside down (mirrored by places in the scale around its first note, so it stays in the scale) and both, each form moved to
  begin beside the note the last ended on; no note returns until the others have sounded. The lengths are a row of their
  own, read forwards and then backwards. Every voice shares the row. A varied line is the line's notes backwards in its own
  rhythm. With `leaps` a note may take any octave in range. A form may begin anywhere in the row and go round (`rotations`,
  usual). A voice may have a row of `loudness`, how much louder or softer than the voice each note is, and of `articulation`,
  how many parts in four of each note's length sound, both read as the lengths are. Roles of one `voice` with `together: 3`
  and `takes: 0`, `1` and `2` play chords of three neighbouring notes of the row, a track each (a chord that reaches from
  one form into the next may hold a note twice). The rest of serialism waits in the ideas file, since the user wants melody
  across a song's structure first. The experimental style template is built on it: three voices, no
  chords, no drums.

- **Evolving** (`Evolving`, the user's choice of what came after serial): repeats that evolve, the principle of registers
  written out as plain patterns with no register set up. The first line is a step walk's, and each new line is that phrase
  with a running amount added: moved so many places up the ladder, going round at the top of the range, and begun so many
  notes later (the habit `evolve: {move, rotate}`, usually one place and none). A varied line begins one note later.

Agreed and to come, each optional (`.claude/features/WIZARD_DESIGNS.md`): phase and build-up; cells in order; a cellular automaton; chance tables;
clouds; generate and test, with motif development and counterpoint last.

## Players

- **The hook** (`Hooks` and `Hooked` in `melody.py`; the user's design: a thing of the song, apart from the melody style that
  writes the other lines). A song has a hook where its picks say `hook: true`, else where its style template does (rock, sixties
  pop, and soul and funk do), and a section of its form marks a line `hook: true`. `Hooks`, the maker, a subclass of `Smart`,
  makes such a line: a figure of one bar, 2 to 4 short notes (`short_note_figures`, the Notes gauge choosing how few) reaching a
  long note, the peak: a note of the chord at or above `hook_floor()`, half the span over home. The figure fills the line's first
  bar and each second bar after; the bars between are an answer (`answer_bar`), walked under the peak as the smart engine
  walks. A varied hook changes only its last note (`varied_hook`). `Hooked` wraps the writer, any engine of `ENGINES`: hook
  lines go to the maker, and every other line of every section is the writer's, held under `hook_floor()` unless marked
  `higher` (`held_under`), so the hook's top is the song's. The wizard's Hook switch (`WizardChoices.has_hook`, `set_hook`,
  `can_have_hook`, which is false where the form marks no hook or nobody carries a tune there) is on the Hooks branch, under Composition, for now.
  `TestHooks` holds each property on forty seeds.
- **The smart engine** (`Smart` in `melody.py`, the user's design after discussion): a tune that follows what a listener expects.
  Most moves are steps, steps mostly fall and leaps mostly rise, a step tends to carry on, a leap is followed by a move back,
  each line has a shape (an arch, a climb, a tumble or a dip), a note off the chord leans toward the chord's note beside it,
  and a note that lands, a long one or a line's last, wants the chord. Seven gauges of eight positions say how strongly, in a
  style's `melody` as `smart`, which a song's `melody` may change: `moves` (steps to leaps), `steps` (fall to rise),
  `after_leap` (return to carry on), `phrase` (flat to arched), `leaning` (resolved to left hanging), `notes` (long to short)
  and `surprise` (expected to surprising). A line marked `higher` sits higher; each line of a song is dealt a rhythm of its own
  from the style's while they last, by its place among the song's lines (`line_letters` in `arranger.py`), so a chorus's hook
  has a rhythm no line of the verse has; a varied line keeps the first half of its notes and its rhythm, so a hook is known
  when it returns. The wizard's Melody picker offers it, and no subgenre takes it unasked yet: that waits for the user's say
  once trial songs are heard. `TestSmart` in `tests/macro_composer/test_melody_engines.py` measures each tendency and each
  gauge over forty seeds. The gauges are fields of the wizard's Melody branch, under Composition, under the Melody field while it reads smart
  (`MelodyBranch.gauge_field`), kept by the song as `melody_gauges`. The other styles' own settings are fields there too while the style is in use (`WizardChoices.melody_settings`, kept as `melody_settings`, written into the song's `melody` over the genre's habits by `_song_melody`): evolving's move and rotate, serial's chromatic, leaps and rotations. A song may give a player habits of the player's own, `role_habits` by role, which come over the genre's habits for that player; the wizard uses them for the serial style's rows of lengths, loudness and articulation. A line's notes are drawn by the seed and where the gauges
  stand together, so a gauge moved one position always redraws the notes, while each line's rhythm and shape, which go by
  the seed alone, stay (Claude's choice, to hold the rule that every choice changes the song: the chances alone often
  turned no draw).
- **Drum breaks** (`breaks.py`, the user's design): six bars of drums each played as one thing, named by feel (tumbling,
  shuffling, stuttering, rolling, lazy, driving), written for the program in the manner of a kind of break, no record's
  strokes and no sample. A song's pick `break` names one, in any style, in 4/4: the arranger (`break_of`, `drum_parts`) plays
  its bar in place of every way of the drums but the percussion's, the drummer's additions and fills still laid over. The
  pick `break_cut`, 1 to 8, cuts the break up: the bar is eight slices, and in each bar of a phrase after the first, one
  slice more for each position is swapped for another slice that sounds different, every drum cut alike, never the first
  slice, seeded by the song's seed and the bar. A subgenre built on a break names it in its template (big beat and downtempo
  of the electronic style). In the wizard the drums' branch starts with a Break field, (none) first, and under a chosen
  break a Cut up gauge; a break hides the kick's, the snare's and the cymbal's own fields (`WizardChoices.breaks`,
  `get_break`, `set_break`, `get_break_cut`, `set_break_cut`, `role_traits`). `tests/macro_composer/test_breaks.py`.
- **A kit piece's own sound** (the user's design): a song's `piece_sounds` names, by piece of the kit, `{drum: name}`, another
  drum of the kit, or `{sound: General MIDI number, note: MIDI note}`, a sound on one note, so that a kit can be abstract.
  The arranger (`pieces_played`) writes the piece's hits as that drum or note; a piece in a General MIDI sound gets an
  instrument of its own, named after the piece, and is no drum track, since the drum channel plays only the kit. In the
  wizard each piece is one row of two cells (the user's design): whether the piece plays, switched with Space, and, a Right
  away, what the piece sounds as, `kick`, `cowbell (kit)` or `Flute  C3`, where ENTER opens the Sound dialog on the piece's
  own drum above the kit's drums and General MIDI's families and Bksp gives the piece its own drum back. The dialog's Note
  row, under the list, holds the note a General MIDI sound plays, C4 until changed, stepped or typed by name, and the Listen
  key plays four hits on that note (`WizardChoices.piece_sound`, `set_piece_sound`, `piece_note`, `set_piece_note`,
  `PlayerBranch.piece_row`, `WizardPage.pick_piece_sound`). `TestKitPieceSounds` in `tests/macro_composer/test_breaks.py`.
- **A player's character** (the user's design, `macro_composer/characters.py`): a song's `players` gives an instrument a level, 1
  to 4, or the places of gauges, each 0 to 20 (`notes`, `variety`, `touch`, `timing`, `fills`, `strumming`, `range`). Each field
  of a template's level belongs to one gauge (`GAUGE_OF_FIELD`), and the player is put together field by field from the level
  whose band the gauge's place is in; `uneven`, `timing` and `span` are numbers and are blended between the levels, so every
  place differs. A level is a preset, every gauge at the level's place (`PRESET_PLACE`), and gives the level exactly as written,
  so the four imaginary players stay. A section that allows an instrument only so high a level holds each higher gauge to that
  level's place. The wizard keeps each moved gauge (`WizardChoices.player_gauges`, `get_player_gauge`, `set_player_gauge`,
  `player_preset`); the gauges are not on the wizard's page yet, since outside timing and touch a gauge has only four places that
  differ until rock's levels are rewritten as gauges. `tests/macro_composer/test_characters.py`.
- A song gives each instrument's player a complexity from 1 to 4, which people see as an imaginary player's name
  (`player_name` in `players.py`). The instruments and names are the same in every style; what each player does is the style's.
- **A player only decorates the kind's own parts and never replaces them** (the user's choice). Complexity 1 goes by the book
  and adds nothing; 4 is the virtuoso. The tests hold that every hit of the kind's bar stays at every complexity.
- A drummer decorates by `adds` (hits in every bar), `varies` (a list, each naming the `bars` of a four-bar phrase that get a
  small change, and the `choices`), `fill` and `fill_every` (0 for none), `timing` (a rush or a drag for each drum, in
  hundredths of a step) and `uneven` (velocity moved by a seed). Each choice says what it `needs`, so one that does not fit
  the meter is left out. A decoration's drum says its `steps` and which are `loud` and `soft`, and is laid over the bar only
  where the bar is silent.
- A player of a figure, the bass, the keys and the rhythm guitar, decorates by `varies` too: each names the `bars` of a four-bar
  phrase and the `ends`, notes of the player's own that take the bar's last steps, written on a `grid` of so many steps to the
  bar, and may say the meter it `needs`; what the bar played before them stays. An ending fits a figure when one of the two
  grids divides the other, the figure written on the finer; any other, and one written for another meter, is left out. A
  section's intensity holds a figure's player back as it holds the drummer, with a part for each level a song uses, and no
  part of its own where the player held back plays the figure no differently.
- A keys player strikes the chord again before a turn, then ends bars with quick chords and runs along the chord's notes; a
  rhythm guitarist adds strokes into each turn, more at each level, beside Guitarify's spread and looseness; the electronic
  style's sequenced part jumps an octave instead (the user's choice of the bass's way for every player). A lead changes its
  span and busyness. `tests/macro_composer/test_wizard_effect.py` holds every position of every Busy gauge to a song of its own.
- What a player says for people is written in the same block as what the player does, and must say only that.

## Interplay

- `macro_composer/interplay.py` writes what the player beside the tune plays against the tune's lines: `UnderLead.lines(way=, tune=,
  chords=, section=)` gives lines as long as the tune's. A fill or an answer starts once the tune's last note of a line has landed, a
  fill at the end of every second line and no longer than half a bar, an answer after every line in all the room there is; playing
  the hook is the tune's own lines; a riff is one bar under every bar, moved to each chord. How busy, 0 to 20, is part of every seed,
  so that each place is heard.
- A style template's `interplay` holds `busy`, a `plan` of the way by kind of section, and `by_subgenre` plans laid over it; a kind
  left out is waited through. A song's `beside` names the player (`role`), `busy`, and `ways`, one for each section of the form in
  order, which the wizard works out from the plan, the one role chosen and each section's own. The arranger (`way_beside`) acts only
  on that player, only in a section somebody has the tune in; "waits" keeps the player silent even where the section lists the
  player, and a section whose own plan writes the answers is played as written under "answers every line".
- A song kept before answering could be chosen has no `beside` and is made as before.

## Sections

- A section's `intensity` is the most each instrument's player may open up there, 1 to 4: the song's player is held to it, so a
  busy player starts plainly and saves the most for a chorus or a solo (the user's design).
- A section may change a pick, such as the cymbal ridden, and start on a `crash`, whoever plays, so that sections differ even
  for the plainest player.
- Every section ends on its fill: a drum part is no longer than divides the section. Drum parts are made once for each
  different combination and named after the section's kind.
- A held section is one bar: a crash, a kick and each figure's held chord.

## The Song Plan

- A song whose picks hold `song_plan` (true, or a mapping of `contrast`, `growth`, `phrasing`, `hook_kinds` and `sections`, a
  list by place of the form) is planned before it is arranged (`SongPlan` in `src/llamatron/macro_composer/song_plan.py`,
  called from `arranged`): every place of the form becomes a section of its own, named `verse`, `verse 2`, so that a second
  verse can differ, and the plan writes into each what the arranger reads. A song without the key is arranged as ever, and
  nothing the wizard's page offers sets the key yet: a song file does (below).
- Energy, 1 to 10, a section: the style's for the kind (`song_plan: energy` in a template), plus `growth` each time the kind
  returns, the last run of choruses taking `last_chorus`, pulled about the middle by the song's `contrast`, and a place's own
  `energy` over all of that. Energy never changes a tune's notes.
- From Energy: `intensity`, the level each player may reach, by the player's change points (`levels` in the template, each
  point but the first moved by the song's seed, so that the band never changes all at once); `plays`, the kind's players but
  those whose `comes_in` Energy is higher; the cymbal (`cymbal`, a list of Energy and way); the scene's Swell, 80 to 100
  percent, so that ordinary playing leaves room, a `rising` kind ramping from two lower; and a crash on a section arrived at
  from below at 6 or more, or after a tail.
- Joins (`src/llamatron/macro_composer/joins.py`): a section's `leaves` holds a `fill`, by how far the Energy rises (the
  template's `fills`: small, medium, big, never the same twice running), or a `tail`: `stops` before a drum solo, `drop-out`
  once a song, into the last run of choruses, about a second long by the tempo, and `build` out of a rising kind; a
  subgenre's `tails` lists what its bands do. A section with `leaves` has its drums written out whole, the small fill inside
  only every `fill_inside_every` bars, and a figure under `stops` or `drop-out` written out whole so that its last bar
  differs. `last_chord` is the chord of the last bar: the fifth, or the seventh in minor, where the next section starts at
  home and the section rises into it or would sit on home; `setup: not at all` at a place, or the subgenre under `no_setup`,
  leaves the chords alone.
- A drum solo (`src/llamatron/macro_composer/drum_solo.py`): a section whose kind has `drum_solo: true` is the drummer alone,
  a theme on the snare, the theme round the toms, a build, a peak and a last bar that plays the band in, drawn from the seed;
  in a meter other than 4/4 the drummer plays the section's ordinary part alone.
- Phrasing (`src/llamatron/macro_composer/phrasing.py`): with the habit `breathes`, every line but a hook's ends early, three
  eighths before its bars do, or five or six for the second and fourth lines of a section, and one line in two has a note
  come an eighth early; the breath is drawn apart from the line's notes.
- Hook kinds (`src/llamatron/macro_composer/hook_kinds.py`): with the habit `hook_kinds`, a hook's bar is of a contour
  (chant, arch, falling line, leap and fill, rocking, rising sequence, or the long note, the hook made as before), a rhythm
  and one odd detail; each take is the next contour and the next rhythm in the song's own order, so another take is another
  kind. The bar is said note for note in each second bar of the line and answered lower between. The kind is said in the
  song's notes beside the first section that has the hook, as each scene's Energy and join are.
- A tune that returns note for note is one part, in a planned song, and a part beside the tune is drawn by the section's kind
  (`drawn_as`), so that a hook or a riff stays the same each time.

- On the wizard's page (`tui/screens/wizard/`): a genre whose template has `song_plan` plans every song from the start, and the Form
  panel's Song plan switch turns the plan off (`WizardChoices.has_song_plan`, kept as false in the choices). The Form panel has
  Contrast, each section's plan in a line, and the Form questions button (`form_questions`, `set_form_from_answers`: verses first,
  pre-choruses, a bridge, solos, a drum solo, last choruses). The Hooks panel has Contour, Rhythm and Detail (`set_hook_part`) and
  Intro hook (`set_intro_hook`: the answering player or the singer says the hook in the intro). The Melody panel has Phrasing,
  Breath, Line lengths and Early notes (`set_phrasing_way`; early notes are a count of lines in four, never chance). A section's
  panel has Energy, Shape (`shapes:` under a kind in the template, for a solo, a pre-chorus and a bridge), Rises, Leaves with and
  Setup under a plan, and Chords, Tempo, Tempo at end, Key and Scale in every genre with or without one (`set_section_own`,
  `OWN_WITHOUT_PLAN`; without a plan they go to the section as `chords` and the scene's settings). What a section is given is kept
  in its entry of the form and moves, copies and goes with the section; a value the song cannot be made with is refused.
- A plan keeps what the person chose for the drummer: a chosen fill is the fill of every size, how often fills come sets the fills
  inside a section, and a chosen cymbal is ridden all through in place of the cymbal by Energy.
- `L` (Listen) on the Hooks panel plays the hook over the chorus's drums, looping; on the Melody panel the first section's tune
  over its drums, looping; on a section the section once (`tui/made_preview.py`, `Branch.listens`). It plays a song made from the
  choices and thrown away, through FluidSynth, and any change of a choice stops it. The whole song is never played in the wizard
  (the user's rule: small parts have previews, the song is heard on Arrange).
- **Notes written by hand** are patterns: a tune's and a riff's notes open in the pattern editor from the wizard
  (`WizardPage.open_pattern`, `OWN_TUNES`, a riff's `own`). The Lines window and the one-line note dialog are gone. A song kept
  from before still plays its `hook_notes`, its sections' `lines` and a riff's line (`macro_composer/line_edits.py`), and the
  page shows each as the person's with Bksp to give it back: the Hooks panel's Notes row, a section's Lines row under Tune and
  the riff's Notes field.
- **A section's panel is in groups** (the user's design): Kind, Bars and Energy on top, then Tune, Harmony, Shape, Joins and Who
  plays, headings that open and close as a settings page's do; a group with nothing to offer in the section is left out. The Hooks
  panel keeps the switch and Notes on top, with Kind, Where it is said and Riff under headings. The Melody and Form panels are to
  be grouped the same way, each drawn for the user first.
- **Starts and endings in stages** (S46): the Form panel's Starts with, Ends with, First player and Setup bars (`set_start`,
  `set_end`); each stage is an ordinary section of the form, so opening or closing sections a person changed read as "your own".
  Every section has Fades (`song_plan.FADES`; a scene swell without a plan). The band genres' templates have an `outro` kind.
- **Players as people**: a player's panel has Comes in and Lays out (`set_comes_in`, `set_lays_out`), which are a reading of which
  sections the player plays and set them through `set_section_plays`, and Reacts (`set_reacts`, the plan's `reacts` by player
  name), which moves the Energy the player answers to away from or toward the middle; Reacts is offered only where making the song
  with the player even and dramatic differs, since the plan only ever holds a player back.
- **A figure for a kind of section**: a value with a `figure` may say `by_section: {kind: {figure: [...]}}`, bars as long as the
  value's own; a section of that kind plays the figure as a part of its own (`bass chorus`), which a busier or held-back player
  varies as any figure, and every other section plays the usual figure. The value's generators are the same in every section.
  Written so far for the rock, sixties pop and soul basses (a verse leaving space, a chorus moving), two of rock's guitars and
  the blues basses under a solo. Nothing on the wizard's page says a value has them.
- **Loudness levels** (`macro_composer/loudness.py`): four named levels, ghost, soft, normal and accent. A drum's come from its
  `loudness` in the template, a number (accent 12 above, soft two thirds, ghost a third) or a mapping of the four; a player of
  notes' from the role's `velocity` (accent 12 above, soft 8 below, ghost 30 below). A drum bar's marks are `accent`, `loud`,
  `soft`, `ghost` and `none`; a tune's note may say `level`, and its stresses reach for the part's own accent and soft note.
  `beat_loudness`, at the template's top or under `by_subgenre`, is a lean added to the drums' strokes on each beat of the bar
  (funk lands on the one, the ballads lean on one and three). A song keeps `dynamics: {player: 0 to 10}` (5 as written, 0 every
  note alike, 10 twice as far, which also scales the feel's shaping and the lean) and `loudness: {player: {level: number}}`; the
  drummer's numbers are the whole kit's, each piece moved in proportion, and a normal level of the song's own carries the other
  three with it. On a player's panel: the Dynamics gauge (`set_dynamics`, shown where heard) and, last, the closed Loudness
  heading with a number for each level the song plays (`set_loudness_level`, `loudness_levels_offered`, found by making the song
  with the level moved, only while the heading is open); Bksp gives a level back to the genre. Not yet: the lean on players of
  notes, the phrase offsets (a section's first beat, a climbing last bar) and the small random amount.
- **Two chords in a bar** (`arranger.shares_a_bar`, `halves_of`, `progression_of`): a list inside a progression's pattern, or
  inside a section's own chords, is two chords in one bar, each half of it; the section's Progression is then written by the
  half bar (`every` half a bar of the meter), and whatever goes bar by bar, the tune, the riff, the last bar's setup, takes
  the bar's first chord (`chord_of`). A Progression holds 32 chords, so shared bars are played only in a run of 16 bars or
  fewer (`fits_by_halves`), a longer run falling back to a chord a bar. The blues' quick change and two five twelve bars
  end on a turnaround of two bars of two chords. Wizard: a section's Chords field takes two chords joined by a dash, such as `1 4 1 1-5`, and
  refuses more than 16 bars of them. Not built: a quality for every degree, a chord over two bars, a progression's own length.
- **Percussion by Energy** (`song_plan: percussion_from:`): the kit's percussion, a tambourine, handclaps or a cowbell, plays
  only in sections of that Energy or more, so that it comes in with the chorus, in rock and in soul and funk (new orleans'
  plays all through, and funk's Energies never fall under it); percussion the song chose itself plays all through, as a
  cymbal the song chose does. Sixties pop, which leans on its percussion, has none. Nothing on the wizard's page.
- **Swing by subgenre** (a template's `groove:` under `by_subgenre`, `arranger.GROOVE`): the name of one of the grooves every
  set has, which the made song takes as its groove: rock and roll, sunshine pop and bubblegum bounce on their eighths
  (`8th swing 58`), new orleans swings its sixteenths (`swing 58`) and funk a little (`swing 54`). A style written in
  triplets, as the blues, swings as written and takes none. Wizard: the Subgenre panel's Swing field under Tempo
  (`has_swing`, `get_swing`, `set_swing`), the subgenre's own said to be the genre's; `none` plays a swung kind straight.
  The review's swing numbers lie between the factory grooves, so the nearest lighter one is used.
- **Fills by the join, and markers** (`SongPlan._joins`, `_fill_inside_every`, `_marker`): a section leaves on a fill sized by
  how far the Energy rises, the big one always into the last chorus; inside a section from Energy 5 up the small fill comes
  every 8 bars; and every phrase of 4 bars that ends inside a section with no fill there ends on the style's `marker`
  (`song_plan: marker:`, a stroke or two laid over the bar by `drum_parts`). A song that chose its fill, or how often fills
  come, has no markers. The four band genres each write a marker.
- **Staged solos** (`SongPlan.stages`, a section's `staged: true` with `shapes`): the first solo of a song plays its kind's
  plan, and each solo after takes the next of the kind's shapes in turn (theme and variations, climbs, starts from the hook,
  a repeated figure, at the peak), its lines named for the stage so that each solo has ideas of its own and no two running
  are alike; the hook's line stays the song's. A shape the song gives a place stands over the stage. Rock, sixties pop, soul
  and funk and the blues stage their solos; a blues kind the guitar leads (`lead_solo`) gives the solo to the lead, since no
  player answers there. Wizard: a solo's Shape field on its section's wizard panel says the stage's shape as the plan's.
  Not built: stages inside one long solo with the band rising a step a stage, a second player trading, a jam on a vamp, the
  drum solo's named stages, a closing solo that jumps the tempo.
- **A riff of chords on its accents** (`riffs.heavy_line`, the riff's `notes: chords on the accents`): the root's two-note chord
  on beat 1, two to four accents off the beat as two-note chords at the accent level, the low root short (`gate`) at the ghost
  level or rests between (`between`), one or two `bars` alike, two or three single notes at the end that lead back, half the
  notes or more the root, the third and seventh flattened over a scale that has them major; `under the tune: leaves a gap`
  empties the first bar's second half. The riff's first player plays the chords and any other its notes alone
  (`riffs.single`); the kick strikes the accents in the sections that play it (`drum_parts(over=)`, `riffs.accent_bars`), the
  rest of the kit as ever; `with chords: stays on the home chord` writes the section out, the riff over the home chord and
  every other chord held, where half the section or more is at home and the home chord lasts the whole riff somewhere, and
  else the riff moves with each chord. A subgenre's template may say `riff:` (hard rock's does), which a new song of the
  wizard's takes when the subgenre is chosen (`_take_riff_of_genre`); a kept song has the riff it kept or none, and the
  arranger never reads the template's. Wizard: the Hooks panel's Riff group has Played by, Heard, Made of, Bars, Between,
  Under the tune and With chords, each setting shown only where it is heard (`riff_settings_offered`), hidden but With chords
  while the notes are written by hand; the riff's picture has the kick's row over it (`riff_kick`) and comes above the hook's
  while the cursor is on a field of the riff. Not built: a tail that changes into the next chord, the riff thinned to muted
  roots under the voice, the guitar alone saying it before the band (the Form panel's "riff first" start does that by hand).
- **The riff, a song's second hook** (`macro_composer/riffs.py`, `set_riff`, `set_riff_line`, `new_riff`): two bars of single
  notes over the home chord, the second answering the first, played in place of their figures by one player of a figure or by the
  first and the lowest together, in the intro, under the verses, under the choruses or everywhere, through a chain of the
  Progression alone. Kept in the song's extras as `riff`. No more than two hooks, the tune's and the riff (agreed with the user).
- Not on the page yet: keeping hooks and choosing among them, a writer per kind of section, a plan for any genre but rock, the
  Melody and Form panels in groups, a longer and more shaped solo section.

## A Song File

- `src/llamatron/macro_composer/wizard_file.py` reads a song file: the wizard's kept choices, a `name`, a `form` that is a
  form's name or a list of sections (a kind, or a mapping with the kind, `bars`, `plays` and whatever that place of the form
  is given, which goes to the plan's `sections`), `song_plan` (true where left out) and `song`, picks laid over the song the
  choices make (`WizardChoices.set_song_extras`, kept with the song under `song`, with the plan). It is the way a homage is
  written down: the form, each section's chords and Energy, and nothing of a tune that is not the song's own.
- `llamatron --wizard SONG_FILE` makes the song and writes its set to `--out`, or beside the song file as
  `NAME_song.yml`, and opens it; `--batch` stops after writing, and `--seed` gives the seed. A file with no seed makes
  another song at each run. `tests/data/wizard_songs/rock_everything.yml` is the trial that uses everything.

## The Wizard's Choices

- `WizardChoices` (`src/llamatron/macro_composer/wizard_choices.py`) holds one run of the song wizard: the genre, a style
  template by its file's name and shown by its title; the subgenre, one of the template's kinds; the key's root and scale
  type; the tempo; the form, one of the forms the template suggests for the kind; and the seed. Each setter refuses what it
  cannot hold, and the tracker's page (`.claude/tracker/PAGES.md`, "The song wizard") changes the choices only through them.
- The form follows the suggested form chosen until a section changes; the form is then the song's own (`has_own_form`), a
  list of sections each its kind and what it changes of the kind, its bars and who plays, kept with the song under
  `own_sections` and handed to the arranger as the song's own form and sections. Sections of one name are one section
  played again, so a section that differs from its kind as the genre describes it gets a letter after the name, `verse b`.
  `section_kinds()` leaves out a kind the subgenre cannot play, and `bars_offered(place)` offers half the kind's usual
  length, the usual and twice that, each only where a section made at that length really lasts that long (`bars_work`,
  measured once and remembered): a part written over several bars keeps its own length whatever is asked. Choosing a
  suggested form, a genre or a subgenre drops the song's own sections.
- The whole song's ways are picks like a player's: `song_trait` finds the trait no player owns, the chords under either
  name a genre gives them, the feel or the fills, and `song_ways` lists its ways that fit. `set_melody` chooses the melody
  style every tune is sketched by, or None for each player's own, kept under `melody_style`; `melody_styles()` leaves out
  a style that makes no song of the subgenre (`melody_works`).
- A player's sound is its way's usual one, moved by the band's Sounds (`band_sound`: the nearest sound of the kind chosen
  for the sound's General MIDI family, `NEAREST`, a sound already of the kind staying, `KEPT_BY`), unless the player has
  a sound of its own (`set_sound`, any General MIDI sound but the percussive sounds and sound effects). The drums have no
  sound to choose, since the grooves are written for the kit. A song carries the sounds that differ as `role_sounds`,
  which the arranger's `sound_of` turns into the track's instrument. A role's `title` and `titles` in a template are what
  the wizard calls the player; tracks keep the role's name.
- One guitarist: a template's `one_guitarist` names the player of the chords, the player of the solo, the way the solo is
  then played and what the one player is called. `set_guitarists` chooses it; the solo is then a guitar's, the chords are
  left out of every section the solo plays in (`_sections_of_song`), and leaving the guitarist out leaves the solo out.
  Fills between the sung lines by the one guitarist are not written yet.
- The kit's pieces: `pieces()` are the drum tracks of the song as chosen, and `set_piece_on` switches one off, kept under
  `pieces_off` and handed to the arranger as `without_pieces`: a part for a piece that is off is not made, so its strokes
  are left out and never moved to another piece, the user's rule. Extra pieces that are off until switched on, with busy
  parts written for them, are not written yet.
- Fills and quiet notes: `set_fills` chooses how often a fill comes, a position kept under `fills` and handed to the
  arranger as `fills_come` (0, each section, or a number of bars), which then decides in place of the drummer's level;
  until one is chosen the drummer decides and `get_fills` shows the nearest position. `set_quiet_notes(False)` leaves
  the snare's soft strokes out (`quiet_notes`), and `has_quiet_notes` says whether the groove has any, found by arranging
  the song both ways. Adding quiet notes to a groove that has none is not written yet.
- A style's melody habits may hold `by_scale_type`, habits that replace the usual ones for a song in that scale type: rock
  and soul give a minor song the notes 1, 3, 4, 5 and 7 resting on 1, since the major notes read in a minor scale rest on
  its third and sound like the major key beside it, which made a hard rock tune sound happy (the user's finding).
- Stand-ins, the user's choice: a template's `stand_ins` gives a player a sound by subgenre in place of the sound of the
  player's way, since General MIDI's voice is a hum that sounded weak. Rock's singer stays the singer with one way, `voice`,
  and plays a guitar or a synth lead by subgenre; `usual_sound` returns the stand-in, the band's Sounds and the player's own
  Sound still apply over it, and the picker offers every stand-in of the style.
- The progression left to chance, the user's ask: while no progression is chosen (`has_any_progression`, the Chords branch's
  first choice, "any", which a song starts on), `progressions_by_chance` draws one by the seed from the ways that work,
  likelier the commoner, the subgenre's usual one counted twice, and only from those written for the song's scale type
  where the style has any; `made_setlist` takes the next drawn when one makes no song. With no seed the usual one plays.
  Rock gained three minor progressions so that a minor subgenre has several.
- Every choice is effective, the user's rule: `tests/macro_composer/test_wizard_effect.py` makes each choice of each subgenre
  alone and fails when the song made is the same, but for the counts in its `KNOWN_TO_CHANGE_NOTHING`, each with its reason,
  which may only shrink. A choice found dead is made to work or is no longer offered: a fill the song picks (`fills` among
  its picks) wins over the drummer's own; `melody_is_usual` leaves out a melody style that sketches as the genre does unasked.
- Nothing is chosen at first, the user's rule. Choosing a subgenre fills in its usual tempo, the scale type its chords are
  in, the root that scale type starts on (C for major, E for minor, Claude's choice) and the commonest form, so that a song
  can be made from a genre and a subgenre alone; choosing another genre leaves the subgenre to be chosen again. Any tempo
  the tracker plays is allowed, the template's usual range being advice.
- The band: `roles()` are the genre's players; `set_role_in` leaves one out (a song's `without`, which the arranger
  honors: no track, and no drum tracks without the drums) or puts one in, a player whose usual way is to sit out coming in
  on the commonest way that sounds; `ways` and `set_way` choose a trait's pick among those that fit the other picks;
  `set_busy` sets the level of the player's instrument, 1 to 4, each starting at 2 (Claude's choice, so that a song has
  turns and fills). Choices kept before the band could be chosen name no levels and still make the same song.
- `meter()` is the subgenre's; `form_seconds()` is a form's length at the tempo chosen, held by a test to the length of
  the song made for every form of every subgenre; `step_length` chooses the next longer or shorter form.
- The seed is never shown: `made_setlist` draws one when the run has none, and the song keeps it with the other choices
  (`Song.get_wizard_choices`, the song's `wizard` setting), so that the same choices make the same song. `from_data` reads
  kept choices with care, leaving out what no longer fits.
- `made_setlist(name=, version=)` arranges and composes the song into a set of its own, and `Setlist.take_in` adds that
  set's song to the open set with all the song uses: a thing whose name the open set uses for something different is
  renamed as a duplicate is, everything that names it following; a thing that is the same in both, such as an instrument,
  is shared; nothing of the open set is touched.
- Every style template suggests forms now (`forms`, under `usual` or a kind's name), which rock, blues, sixties pop and
  soul and funk lacked: the forms the trial songs used, so that a song needs no form of its own.
- `tests/macro_composer/test_wizard_choices.py` and `tests/composition/test_taking_in.py` test them, every subgenre of
  every genre among the cases.
