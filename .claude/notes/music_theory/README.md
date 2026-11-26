# Music Theory Notes

What Claude knows about how songs are put together, kept by Claude and for
Claude, so that the song wizard and the style templates are built on stated
principles and not on what is remembered that day. The user may ask for a
summary of any of it written for people.

## The Rules of These Notes (the user's)

- The notes run ahead of the code: a note need not match what is built, and a
  build is checked against the notes.
- No band, artist, composer, song or other work is named, only genres and
  subgenres, with one exception: a note Claude wrote in another conversation,
  which the user hands over as Claude's own, keeps the names it has, in these
  notes only. A name the user mentions in conversation is never written down
  anywhere. No melody, riff, bass line or lyric is written down.
- Principles are stated and summarized, high level, in Claude's own words. No
  source is listed; a reader can search for alternatives.
- What may go in: what public searching finds, general theory, and the theory
  books the user lent, paraphrased as principles with no passage, example or
  exercise taken. Nothing learned from the homage work goes in.
- Each statement says how sure it is where that matters: **measured** (a study
  counted it), **practice** (what arrangers and players commonly say and do),
  **judgment** (Claude's own, to be tested by listening).
- Claude adds to a file whenever the work teaches something, and reads the
  subject's file before building in its area.
- Prose and list items wrap at 78 characters, so that a note reads easily in a
  terminal; tables, headings and code blocks keep their own lines.
- A note Claude wrote in another conversation, which the user hands over as
  Claude's own, is folded in nearly whole, in a section that says so, and may
  keep the names it has.
- The `music_theory` package (the user's plan, `.claude/planning/IDEAS.yml`) is to
  become the program's own musicianship, read before answering a theory
  question or building anything musical. As a principle is built there, its
  note shrinks to a line pointing at its module; the notes keep what is not
  built yet, and the reasons, certainty and examples, which stay out of the
  code.
- A note Claude never reads while working in its subject is kept in mind for
  removal and proposed to the user when noticed.
- Claude may add notes and files freely. What the notes say about where
  llamatron's code holds something is a convenience, never a limit: the
  architecture changes, and a note is updated rather than followed.

## How the Research Is Done (the user's)

- Search one narrow thing at a time, a few words, such as one beat's name or
  one machine's one feature: a search of many terms at once returns thin
  summaries of everything. Run many small searches side by side.
- Read into the best pages a search finds rather than stopping at the search's
  summary, and go back with narrower searches for whatever a first pass left
  out.

## The Files

- `SONG_STRUCTURE.md`: sections, forms, lengths, how songs start and end; at
  length: how intros begin and exit, typical lengths, bridges, and the
  transition at every join.
- `HOOKS.md`: what a hook is, where hooks go, repetition and variation.
- `MELODY.md`: the ways a melody is made and made interesting.
- `PHRASING.md`: how a melody divides into lines, how each section lays its lines out (line and tag, parallel lines,
  hook and run, cells), density and contrast between sections, stress without words, and checks a program can run.
- `HARMONY.md`: progressions, borrowed chords, chords across sections.
- `RHYTHM_AND_GROOVE.md`: drumming above all: the groove, fills, ghost notes,
  feel, the kit by section; fills and form at length.
- `ARPEGGIOS.md`: arpeggiators and sequenced lines, the arpeggio as a theme,
  the ostinato score.
- `KEYBOARDS.md`: the organs of rock, what an organist plays, keyboard bass,
  organ with guitar; keyboards in a band at length: voicings, accompaniment by
  genre, the organ, soloing.
- `LEADS.md`: how a lead line is composed: the three ways, target notes,
  developing an idea, the arc, technique, leads by genre.
- `BASS_LINES.md`: the ways a bass part is written, by family, each named for
  its sound; keyboard and organ bass.
- `DRUM_MACHINES.md`: the machines, what each gave its genres, electronic
  percussion by style. Machines are named, as products.
- `BAND_INTERPLAY.md`: who answers whom, layering, making room, intensity
  through a song; trading parts: fixed chunks, swapping roles, signaling the
  handoff.
- `ARRANGING_ADVICE.md`: advice question by question on energy, joins and
  their harmony, bridges, solos, hooks, players, sharing space, lengths and
  each genre's tell; read before designing any of those in the wizard.
- `PLAYER_STYLE.md`: what separates skilled players (time feel, tone, density,
  melody or pattern, vocabulary), and when a rule is rightly broken.
- `TECHNIQUES.md`: things read about and not yet used.
- `MUSICIANSHIP_MAP.md`: the bodies of musical knowledge and how they depend
  on each other, what reading a song recovers and in what order, what
  accompanying and fixing need, the warnings against theory that fits only
  common practice, and where the code holds musical knowledge today.
- `genres/`: a file for each genre, with what each subgenre usually does, and
  for kinds of music not yet a genre of the wizard (`SOUNDTRACK.md`, `JAM.md`,
  `JAZZ.md`, `COUNTRY.md`, `POP.md`, `METAL.md`, `TV_THEMES.md`,
  `MUSIC_BOX.md`).

## Measuring, and Weighting

- A statement marked (measured) comes from counting chords and sections in the
  transcriptions of `output/library/` (chart songs by decade, chords by genre tag,
  drummers by style), never from melodies, and names no song. Measures correct
  a template's settings: lengths, shares, what a decade or a style really
  does.
- Averaging many styles together makes mud. A style is a range of habits with
  shares, and where two habits fight, the style is split rather than blended.
- The user weights habits up and down. Weighted up so far: craft in the tune
  (melody first, a bright tune over a sad story, a hook every few bars), and a
  lead instrument that sings like a voice over a funk groove. Recorded as
  habits, never as names.
