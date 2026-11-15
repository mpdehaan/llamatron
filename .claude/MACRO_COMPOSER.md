# The MacroComposer

Reference notes for Claude on the MacroComposer, the user's name for the tool that makes a set from structured data that says
what to play. It isn't imported: read it before working on `internal_tools/macro_composer/` or `internal_tools/macro_compose.py`.
What is agreed and not yet built is in `dev_notes/QUEUE.md`, under the arranger's heading. `.claude/GENRES.md` holds the genre
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

## The Parts

All in `internal_tools/macro_composer/`, run by `internal_tools/macro_compose.sh` (`internal_tools/macro_compose.py`):

- `composer.py`: an input made into a set's data. Its docstring lists an input's fields: what the song is called, its scales,
  tempo and feel, instruments, tracks, generators, chains, parts (a tune's lines, a drum's hits or a pattern as written), bands
  and the form, the scenes in order.
- `decomposer.py`: an existing set written as an input (`--decompose`), and `--same-as` compares an input with a set.
  `internal_tools/macro_composer/inputs/` holds three demos written as inputs, made again when their demos change.
- `notation.py`: how a tune's lines and a drum's hits become a pattern's rows, and the drum kit's names.
- `shaping.py`: the velocity of the parts an input lists, shaped by the song's feel.
- `arranger.py`: a song's picks and a style template made into an input (`--arrange PICKS --out SET`, `--keep-input INPUT`).
- `melody.py`: a tune sketched by rule from a style's habits, where the song gives none.
- `players.py`: the complexities and the names people see for them.
- `style_templates/`: blues, rock, sixties pop, electronic, and soul and funk.

`tests/tools/test_macro_composer.py` and `tests/tools/test_macro_arranger.py` test them.

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
- `melody`: the sketcher's habits: grid, line length, span, home, ladder and rhythms, which may be keyed by meter.

A step is a bar's length divided by the grid, so a shuffle has twelve steps to the bar.

## A Song's Picks

`name`, `title`, `description`, `style`, `template` (the kind), `picks` (traits changed from the kind's), `players` (a
complexity for each instrument), `key` (root and type), `tempo`, `seed`, `sections` (the song's own, or changes to the
style's) and `form`, the sections in order. A song's pick wins over the kind's.

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
- The other players so far change only timing, Guitarify's spread and looseness, and a lead's span and busyness.
- What a player says for people is written in the same block as what the player does, and must say only that.

## Sections

- A section's `intensity` is the most each instrument's player may open up there, 1 to 4: the song's player is held to it, so a
  busy player starts plainly and saves the most for a chorus or a solo (the user's design).
- A section may change a pick, such as the cymbal ridden, and start on a `crash`, whoever plays, so that sections differ even
  for the plainest player.
- Every section ends on its fill: a drum part is no longer than divides the section. Drum parts are made once for each
  different combination and named after the section's kind.
- A held section is one bar: a crash, a kick and each figure's held chord.
