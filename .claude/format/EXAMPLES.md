# Examples and Demos

Reference notes for Claude, one part of `.claude/format/`: the rules for the sets in `examples/`. `CLAUDE.md` says which part to read for which work.

## Examples and demos

- `examples/` is for people interested in music, who may not be technical and may never develop
  the program: every set there is musically interesting to them. A set that exists only to test
  the program, such as one with wrong values, never lives there; test data lives under `tests/`.
- A song made from now on, by Claude or by the MacroComposer, orders its tracks with the chord tracks first, then the lead and
  the backing tracks, then the bass, and the drums last (the user's rule; the bass's place is Claude's choice). Existing examples
  keep the order they have.
- `examples/` is in folders by purpose, the user's layout, which `support/example_sets.py` names and lists
  (`example_sets()`, which every test and tool asks):
  `examples/learning/` the demos in the order a newcomer learns, each file numbered in that order, zero-padded so that the files sort, like `01_hello_world.yml` (the user's rule: a demo moved into or out of `examples/learning/`, or put in another place in the order, means renumbering the learning demos after it, with every reference to their files; a demo's song and its sections and anchors in the documents go by the name after the number; the Entertainer, with too many patterns to teach, is in `examples/by_genre/ragtime/`), `examples/other/` the demos that fit no other folder (the Euclidean mask so far), `examples/by_genre/` every other song, the pieces and the songs in the manner of others alike, each in a folder of its genre, the genre in lower case with spaces and hyphens made underscores, like `examples/by_genre/tv_theme/` (`genre_folder`, the user's layout, since one folder held too many to explore; a homage whose genre changes moves with it, which `tests/app/test_examples.py` holds), and
  `examples/mashups/` the mashups, each one work's notes set in another's style, in a folder for each subgenre, the genre of the band that plays, like `examples/mashups/metal/`, each song's genre that subgenre and the word Mashup, like Metal Mashup, which names its page, `docs/demos/METAL_MASHUP.md`; the pages are listed under the guide's Mashups heading, a group of the website's sidebar beside Demo Songs (the user's design), and
  `examples/midi/` the MIDI files to import. `tests/data/demo_sources/make_demos.py` writes each demo into its folder.
- A mashup never gives the borrowed work's main tune to the lead alone over a beat, which sounds like a medley record (the
  user's rule): the band plays in its genre throughout, with the genre's own licks, fills and answers between and around the
  borrowed phrases, parts trading the tune and replying to each other, and the borrowed notes shared among the instruments as
  that genre's players would share them. The licks are new, never the reference work's own.
- `examples/` holds two kinds of set. The pieces, `minimal_techno.yml` and `mainstreet_hoedown.yml`, are meant to sound good and last about three minutes (`PIECES` in `tests/support/rendering.py` lists them). Every other set
  there is a demo, which teaches one feature a scene at a time, described for people in
  `docs/DEMOS.md`, whose index is generated, and on a page for each genre in `docs/demos/`, where each demo has a section of its own, a heading and a description written by hand and a summary generated between markers (`internal_tools/demo_table.sh`), which a new demo needs before the tests pass, and in each set's `description`, whose "When changing this demo" part says
  what to keep true when editing one.
- A demo with a video on YouTube shows it at the end of its section on its genre's page, under the generated summary, as a linked thumbnail like the guide's (`[![The Density demo, edm_density.yml, on YouTube](https://img.youtube.com/vi/ID/hqdefault.jpg)](https://www.youtube.com/watch?v=ID)`), the same way for every demo, the user's rule; a demo without one shows none, and the user adds them now and then. A video isn't redone when its demo changes: the disclaimer on Listening to the Demos says a video may be out of date. The Density demo's is also on the guide's front page and in `README.md`, under the visualizers' video.
- A demo's title, description, heading and notes never call it a homage, the user's rule, except in a sentence that says "This is a homage to" a work: a heading names the style, like "Synth-Pop", and a description says "in the manner of" the work.
- A homage keeps its inspiration written in its description and notes, the work and who made it, when it is rewritten too (the
  user's rule): a demo's own file and its section on its genre's page are where an artist and a work may be named, so that a later
  improvement knows what to study. What may be taken from the work, the user's rules: its chord progression and the order of its
  sections, since a progression is nobody's property, looked up from chord charts and never from memory alone; never its melody,
  riff or bass line, which Claude neither reads nor reproduces, even where it knows them. A homage's own melody moves the way
  melodies of the genre usually move and has the same kind of feel, written new. The rhythms of its parts are written new as well
  (Claude's reading, to keep each demo an original piece).
- A homage's melody is written from measured traits of the work's melody, never from its notes (the user's rule): a separate
  lookup reports only traits, section by section, such as the range and where it sits above the tonic, how simple or busy the
  line is, how many beats a note lasts, the share of steps, leaps and repeated notes, the share of chord tones, and how
  syncopated it is; no note, rhythm or tab in order reaches Claude, and nothing of them is stored. Claude writes the tune new
  from those traits and the chords. The traits come from what Claude knows of the work or from the user; Claude fetches no
  page of a site whose terms forbid copying or automated reading, the chord-analysis site first used among them.
- What Claude knows of a work is used freely in a homage (the user's rule): its chords and how long each lasts, its form, its
  arrangement and instruments, its groove and tempo, its devices such as a key change or a stop, and the general traits of its
  melody. No run of notes of its melody, riff or bass line is written from memory, and every tune is new.
- A tune is composed, never random (the user's rule): phrases rise and fall with a shape, a motif comes back varied, a leap is
  answered by steps the other way, note lengths make a rhythm that repeats, a phrase ends on a longer note of the chord, and the
  manner is the genre's own. An effect is used only where the style has it: a piece in an old style stays old, so no modern
  club build, Density or Swell, goes on a baroque or novelty synthesizer tune.
- Before a note of a homage is written, three blocks are written into its notes, from what Claude knows, and every part is then
  checked against them (the user's rules). **Subgenre:** its name, and its drums, tempo and feel, bass, builds, sounds, melody
  manner and form; the subgenre is named exactly, since two styles filed under one genre share little. **Band and song:** what
  the band is known for and what the song is known for. **The checklist:** first, why the work is good and why it is remembered, in a sentence, which every later choice serves
  (the user's rule, for every song); then the hook and the instrument that carries it; the
  emotion; the lift, where the biggest moment is and what changes there in register, loudness, voices and drums; the contrast
  between quiet and loud sections; the sounds of the lead, the chords and the bass, each a General MIDI sound with the right
  attack, a sung lead never on a soft sound alone; and each section's tune, its register, note lengths and shape, the chorus
  above the verse where the song lifts. The drums come first: a homage with the wrong drum style has failed whatever else is
  right, the kick drum's rhythm and weight above all, and the bass's rhythm is next.
- A homage's notes carry a line saying which rebuild the file is, like "Rebuild version 2.", counted from 1 for the first
  version checked in, so that a later rebuild knows which one it follows (the user's ask).
- A homage that is written or rewritten uses the generators that fit (the user's rules): the Progression generator heavily, so
  that a part is one written bar a Progression moves through the song's chords, section by section; Guitarify on guitar parts;
  Voice leading on keyboard and pad chords; Strum on plucked parts that aren't guitars; a Hocket where two instruments trade a
  line; Density, Swell and Articulate for builds. Keyswitches stay out while the demos play through FluidSynth.
- Whether a new feature gets a demo is asked of the user every time (`.claude/COMMUNICATION.md`,
  "Discussing a feature").
- A new example runs about three minutes, give or take ten seconds, unless the user asks for
  another length, as for `weather.yml`'s ten minutes (the user's rule). The demos
  written before the rule keep their lengths. `tests/app/test_examples.py` holds every example to it
  but those listed in `WRITTEN_BEFORE_THE_LENGTH_RULE` and, with their own lengths, `OTHER_LENGTHS`.
- `tests/app/test_demos.py` loads, renders and saves every demo without checking what it plays, so
  they can be edited freely.
- `tests/data/demo_sources/make_demos.py` wrote the first versions of all but the hand-written ones
  (`HAND_WRITTEN` in `tests/app/test_demos.py`), from tune data written into it, plus the Mutopia
  Project's public domain `examples/midi/entertainer.mid`, kept with its LilyPond source among
  the MIDI files people can import.
- Run directly, it overwrites the demos, hand edits included, so it's only for starting over. The
  tests also run it into a temporary folder and check its output against those sources.
- Song data a test or script needs is kept in the repository as data files, separate from the
  test code.
- Muted tracks in the demos have SILENT in their names, which a test checks.

**A sung lead is phrased as its lyric is sung** (the user's rule). Before a homage of a sung work is written or reworked, Claude sets
out how the work's lines are sung: how many lines a stanza has, how long each is, which start with a pickup before the bar, where
the singer breathes, and what answers in the gaps. No lyric is written into any file. The lead then follows that plan with pitches
of its own. These are what a lead generally does, and a song may have a reason to do otherwise:

- The lead generally sounds for no more than about three quarters of a verse or chorus, and a phrase generally runs no longer than
  four bars without a rest of at least half a beat.
- A line generally starts with a pickup wherever the work's line does, and lands on the downbeat.
- A stanza generally mixes its line lengths as the work does: short clauses, then a longer last line.
- An instrument or a second voice generally answers in the rests wherever the work has an answer.
- A learning example and a homage of an instrumental are exempt.

**Velocity is a full default with accents** (the user's rule). A lead keeps one default velocity, about 104, and moves from it by
accents only: generally up to 14 above and no more than 12 below, never under 90. The accents come from the phrase and the rhythm:
a pickup is softer, the stressed note a line lands on is accented, a line's highest note takes the strongest accent, a note sung
ahead of the beat is accented, and a line's last note eases a little. A section is never made quieter by lowering all of its
notes; a quieter section has fewer instruments. No section's loudest note falls under 100. Velocity is used sparingly: a song
that is too quiet is worse than one that is plain.

