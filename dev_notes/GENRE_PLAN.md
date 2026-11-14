# Genre Library Plan

What Claude understands is wanted of the genre library, what exists, what was measured, and what Claude will build next, in
order. Claude's file, in Claude's words: it records Claude's understanding and never the user's replies, and it names no band,
artist or composer. The standing rules are in `.claude/GENRES.md`.

## What Is Wanted

1. **A generator.** llamatron's own Python makes a song from a description of its character, with no intelligence outside the
   code while it runs. A song is a list of steps, each a style held for a stretch, with a morph into the next, so that one song
   can travel through several styles over several minutes. Every knob can be set by hand. The generator prints the plan it
   chose, and every value in that plan says whether it was measured from data or is a recipe Claude wrote.
2. **Evolving a song**, later: a wizard asks what is wanted, changes a song toward it and saves the result beside the original.
3. **Saying what a song is like**, kept and rebuilt later on the measured tables.

## How It Is Built

- **From the datasets on disk, worked back from what they can teach.** Reading about styles on the web gave too little a
  program can act on, and drums and bass almost nothing.
- **Chord-first.** A progression is chosen for each section; the kit, the bass, the chord part and the lead are each a recipe
  written against the current chord and the beat; a style is a set of preferences over those recipes, with a tempo, a feel and
  sounds.
- **Learnt tables are readable Python**, a generated module of named constants, bars held as arrays, only bars common enough
  to be nobody's own (found in at least five songs by at least three sources). No trained or binary model ships.
- **Melodies are Claude's recipes**, written as code and marked as such, tuned by data only where a public-domain source sets
  a parameter. No lead melody of a copyrighted work is read.
- **Kinds of music are separate** where the data teaches them differently (popular, jazz, folk tune, classical keyboard), and
  share length, tempo, key, feel, melody style and morph.
- **A step may narrow from a genre to a subgenre to one artist of the data**, the artist counting only when at least ten of
  that artist's songs were read; otherwise the step falls back to the wider group and the plan says so. Artist names may ship
  in the learnt tables, as the dataset spells them, reconciled to one spelling each. They are data the tool reads, never
  preferences: no rule or note for Claude names one, and the tool leans toward none beyond the genres its tools offer.

## What Exists

- `src/llamatron/genres/hearing/`: the analyzer, which reads a MIDI file or a rendered set into parts, rhythm, harmony and lines.
- `src/llamatron/genres/measures/`: the traits the analyzer fills and their units.
- `src/llamatron/genres/reporting/style_document.py` and `user_scripts/describe_style.sh`: a song's measured style as JSON.
- `internal_tools/analysis_and_generation/`: the corpus fetcher, the readers and tables of each source, the dataset study, and
  the cell extractor and its report (`extract_cells.sh`, `cell_report.sh`).
- `.corpus/`, never committed: a large collection of whole-band MIDI files, two sets of chord annotations, a set of recorded
  drummers, a set of transcribed jazz solos, several folk-tune collections, two collections of public-domain lead sheets, and
  classical scores and performances kept for a later kind.

## What Was Measured

From 7,733 whole-band songs in common time, one version of each:

- **A few bars cover most songs, voice by voice.** The snare on beats 2 and 4 is 58% of songs, and three bars cover 80%. The
  timekeeper in eighths is 48%, and seven bars cover 80%. Five kick bars cover half. The whole kit taken as one bar does not
  pool, so a kit is built voice by voice.
- **The bass is mostly the root**: 84% on beat 1, 71% on beat 3, about 60% elsewhere, then the fifth and the third. Fourteen
  rhythms cover half the songs.
- **The chord part**: a chord held for the bar is a fifth of songs, and ten rhythms cover half.
- **Who made a song explains a little of it**: about a fifth of tempo and of triplet feel, a quarter of the share of minor
  chords, two fifths of the share of chords with no third. One song says little of its maker; twenty averaged say a good deal.
- **A melody against its chords**, in the public-domain lead sheets: about 65% chord tones on beat 1 and 60% elsewhere; from
  one note to the next, a step half the time, a repeat 17%, a third 19%, a leap 14%.
- The whole-band collection carries no genre or decade, so grouping its songs by genre needs another source.

## The Steps

1. **The jazz chord study.** A development script that fetches a public list of chord charts of jazz standards into `.corpus/`,
   and pooled statistics from it: progressions by form and style. Nothing of it is committed but the statistics. The study also
   lists every chord the charts use that the tracker's chords cannot express (quality, tensions, borrowed scale), so that the
   chord system can be completed.
2. **The learnt tables**, as a generated Python module: the kit's, the bass's and the chord part's common bars as arrays, with
   the weights of each group over them, and the chord tables.
3. **The generator, as a script.** Steps read from a small file; chords first; the bars laid over them; a lead from the melody
   recipes; a morph between steps; a set written and the plan printed. Popular music first. Done when it writes sets that load
   and play from sample step files, one of them a journey through three styles, and the user has tried it.
4. **The tracker's page** for it, discussed with the user once the script works. For jazz: the style, form and harmony from the
   chord study, the solo line's manner from the transcribed solos, the rhythm section from recipes.
5. **Tools for writing songs by hand**: ask a style's values, write a bar into a set, check a draft against a style.
6. **Saying what a song is like**, rebuilt on the measured tables; then the other kinds of music and evolving a song.

## Not in the Plan

Making a dull melody good, judging taste, a guaranteed memorable tune, convincing fiddle or guitar through General MIDI, and
any slider that claims an emotion.
