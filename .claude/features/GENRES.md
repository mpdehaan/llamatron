# The Genre Library: the Generator and What It Learns From

The standing rules for the genre library (`src/llamatron/genres/`), each stated once, in Claude's words. Not imported: read it
before working on the library, a demo or a generator. What is wanted, what exists, what was measured and the steps in order are
in `dev_notes/GENRE_PLAN.md`. Neither file names a band, an artist or a composer, and neither quotes the user.

## What It Is

- Python that a person can read, and not an AI model. Its words live in `src/llamatron/strings/genres.py`.
- What ships is something a person can read, diff and search: Python, with data as modules of named constants. Numbers may be
  generated from the corpus by the development tools, each recording the sources it stands on. No binary or trained model
  ships, since nobody can tell what one knows inside. Learning libraries are instruments for development only, never in
  `requirements.txt`, and a new one is named to the user first.
- The code decides. While the generator runs, nothing outside llamatron's code makes a choice about the song, and the plan the
  generator prints shows every choice.
- Every value says where it came from: measured from how many pieces of which source, or a recipe Claude wrote. What the code
  learnt from data and what Claude put there are never mixed without saying so.
- Generic is better. A style, an example or a remark the user gives is a case to check the design against, never something to
  lean the library toward.
- Capabilities are never overstated, least of all when the user asks what Claude thinks.

## What May Be Read

- The corpus lives in `.corpus/`, ignored by git, and nothing of it is ever committed or shipped: no MIDI, no chart, no list
  of pieces. Sources must be legal to use in the United States and Europe, and each records its terms.
- A download is proposed to the user first, with the site, the size and the terms. Downloads are sparing, archives over
  crawling. No MIDI of a copyrighted work is fetched anew.
- Copyrighted works already in the corpus may be read for general statistics pooled across many works, at low trust. Their
  melodies are not read: no pitch of a lead, a hook or a sung line. Notes that are plainly chords may be read and the
  progression inferred; a lead's rhythm, density and place in the song may be read. Chords, drums, bass, tempo, meter, form
  and texture are free to measure.
- Melodic figures come only from sources clearly in the public domain.
- No example set is a source for anything in the library but the one public-domain ragtime piece, and none of the user's own
  MIDI files is, not even for a spot check. A file the user offers for discussion informs a decision and nothing about it is
  recorded.
- From any source, its metadata is read as well as its notes: form labels, key annotations, style labels.
- Tests and scripts the suite runs fetch nothing.

## Learning From Imperfect Data

Every dataset has errors. A source is measured on its own before it is pooled, only its sound fields are used, and each finding
records the sources it stands on. A source with a known fault in one field is left out for that field alone and never thrown
away whole. Scholarly sources count fully, recorded performances nearly so, crowd-made sources below half; where crowd-made
files are all a kind of music has, they are what it is learnt from, at their low weight and said to be so, and one kind's norms
never stand in for another's. The same creator spelled differently across sources is resolved to one identity before anything
is merged or counted (`corpus/identities.py`).

## Licenses Travel With Knowledge

Any tool that makes music from this knowledge can tell the person what the result owes: whether it may be used commercially and
what attribution it needs. So every source records its terms, and every value generated from sources records which.

## Ideas Kept for the Generator

- **Balancing with sliders.** A style is a network of traits that pull on one another, and making or adjusting a song balances
  them; the person sets how much each matters, with no AI model inside (`dev_notes/SLIDERS.md`, a design not built).
- **Players that listen.** Simulated players, each producing a part while reacting to the others: trading, answering, comping
  under a soloist, vamping until a cue, laying out, building together.

## Process

- Nothing of the genre library goes on the website until the user says so.
- No demo changes without the user's say-so.
- A string stays in the library only when code acts on what it says.
