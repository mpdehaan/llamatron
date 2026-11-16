# The MacroComposer

Reference notes for Claude on the MacroComposer, the user's name for the tool that makes a set from structured data that says
what to play. It isn't imported: read it before working on `src/llamatron/macro_composer/` or `internal_tools/macro_compose.py`.
What is agreed and not yet built is in `dev_notes/QUEUE.md`, under the arranger's heading. `.claude/features/GENRES.md` holds the genre
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

Agreed and to come, each optional (`dev_notes/QUEUE.md`): phase and build-up; cells in order; a cellular automaton; chance tables;
clouds; generate and test, with motif development and counterpoint last.

## Players

- A song gives each instrument's player a complexity from 1 to 4, which people see as an imaginary player's name
  (`player_name` in `players.py`). The instruments and names are the same in every style; what each player does is the style's.
- **A player only decorates the kind's own parts and never replaces them** (the user's choice). Complexity 1 goes by the book
  and adds nothing; 4 is the virtuoso. The tests hold that every hit of the kind's bar stays at every complexity.
- A drummer decorates by `adds` (hits in every bar), `varies` (a list, each naming the `bars` of a four-bar phrase that get a
  small change, and the `choices`), `fill` and `fill_every` (0 for none), `timing` (a rush or a drag for each drum, in
  hundredths of a step) and `uneven` (velocity moved by a seed). Each choice says what it `needs`, so one that does not fit
  the meter is left out. A decoration's drum says its `steps` and which are `loud` and `soft`, and is laid over the bar only
  where the bar is silent.
- A player of a figure, the bass so far, decorates by `varies` too: each names the `bars` of a four-bar phrase and the `ends`,
  notes of the player's own that take the bar's last steps, written on a `grid` of so many steps to the bar; what the bar played
  before them stays, and a variation whose grid the figure's does not divide by is left out. A section's intensity holds a
  figure's player back as it holds the drummer, with a part for each level a song uses.
- The rhythm guitar and the keys so far change only timing and Guitarify's spread and looseness, and a lead its span and busyness.
- What a player says for people is written in the same block as what the player does, and must say only that.

## Sections

- A section's `intensity` is the most each instrument's player may open up there, 1 to 4: the song's player is held to it, so a
  busy player starts plainly and saves the most for a chorus or a solo (the user's design).
- A section may change a pick, such as the cymbal ridden, and start on a `crash`, whoever plays, so that sections differ even
  for the plainest player.
- Every section ends on its fill: a drum part is no longer than divides the section. Drum parts are made once for each
  different combination and named after the section's kind.
- A held section is one bar: a crash, a kick and each figure's held chord.

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
