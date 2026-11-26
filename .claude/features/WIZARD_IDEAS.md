# Song Wizard Ideas

Wanted work on the song wizard, its players and its style templates: what each idea is, never its status or order (those are
in `.claude/planning/QUEUE.md`). Agreed designs are in `.claude/planning/WIZARD_DESIGNS.md` (S-numbers); how the wizard is
built is in `SONG_WIZARD.md`. An idea leaves this file once built.

## The Port and the Page

- **The wizard in Rust** (WIZARD_DESIGNS.md, "Finishing the song wizard in Rust"): the one freezing run of the Python wizard,
  the music_theory and wizard crates held to the sweep, the page, the musical checks, then S48 to S53.
- **Speed**: Moving between panels lags; every panel and field visited, changed and timed, the cause found, timings before
  and after.
- **Listen turns to Stop** while its sound plays, at the same width.
- **The hook's own Notes row** on the Hook panel, so that the hook, verse and chorus are each editable by hand; then, while
  such notes are edited and Listen pressed, the editor shows the read head as the piano roll does.
- **Riff Assign's FOR column** as wide as its widest value.
- **Drawing changes nothing**: Showing a player's panel writes an empty song plan into the choices; find the field and fix it.
- **The Melodies group's names and layout**: Whether Hook becomes Chorus, whether Melody moves inside the group, whether
  Melodies is the right name. Mockup first.
- **Later verses**: Widgets for how a later verse varies, perhaps its own row to edit its notes by hand.
- **The Ending panel**: An ending's bars and type adjustable (reported in rock and roll, not reproduced); Starts with leaves the
  Form panel and takes Ends with; Fade over needs a swell starting its ramp late (the same controls when a tempo ramp inside a
  scene reaches the form's editor).
- **The hook window**: Sliding and resizing the lit bars, a Listen of the lit bars only, Also played by, and the intro, a
  bridge and a solo quoting the lit bars of a chorus edited by hand.
- **The Melody and Form panels in groups**, each drawn first.
- **The intro question**: What kind of intro is built, asked before the Form's sections; with the professor and a mockup.
- **A second Part** on the page (the list of Parts, the arc, transitions); the model already has the Part level. Main ideas
  beyond one in a Part, and a later Part referring to an earlier one's main idea.
- **Section kinds still to write**: A recall of an earlier melody refitted to the key and tempo; a chain of fragments.
- **The Progression** (S45): chords shown, the library, a section's own, the chords editor; then what its picker does well
  (recommended ones marked, chords shown) worked back into the Progression generator.
- **Starts with and Ends with** on the Form branch, stages as sections (S46).
- **A section's changes** on the Form branch (S24 to S26).
- **The Scale field** offering every scale; a meter changing inside a song (S23).
- **The wizard's three modes**: Song, Chord Jam and MIDI; the MIDI import wizard (Quick, Selective, Import for Mashup) becomes
  the MIDI mode, a mostly complete first draft proposed, reusing the wizard's panels and engine.
- **The documentation**, deep and complete (S29), held back until release; the wizard stays out of the documents for people
  until the user says it is ready (S40a).

## The Players

- **The players as Band Generators**, every genre but electronic and experimental: rhythm guitarist (riffs), bassist, drummer,
  keys (the keyboard player and the organ player), lead guitarist, then horns, strings and backing singers. Musician stage 2,
  riffs by section. Electronic and experimental only after proposals to the user, since the players must serve electronic music.
- **The first riff's leftovers**: The genre's first riff still on the Hooks panel; a player answering the tune answers the
  wizard's tune, not an edited one; any line choosable as the hook line.
- **Interplay** (298 B): an Instrumental switch on the Genre branch with a default by subgenre, hidden where a genre has no
  singer; an instrumental writes the tune for an instrument and drops the backup singers; "Beside the tune": lays out, fills,
  answers, doubles the hook, riff; then harmonized hooks and twin leads; then trading the tune and Interplay in the solo. Soul's
  horns answer and keep the chords. Open: 291, 295 to 297, 299. A singer told from an instrumental lead, each role named for
  what it is.
- **One guitarist's fills** between sung lines.
- **How a player ends bars**, by style: each style's own endings, a choice of flavours, a consistent manner through a song that
  never sounds mechanical; with a stronger Humanize generator used by the wizard.
- **The drummer** (S47): fills by join, surface by section, loudness rules, kick against bass, leaving out, machine drummer,
  swing percent, build-up; an IDM subgenre after.

## The Music

- **Sections that differ**: Verse from chorus, and first from second verse and chorus; a plan and a control of how far they
  differ. Solos perhaps longer, perhaps two for different players in different places, not always after the bridge.
- **Weak hooks**: Measure hooks (repeats, where the peak falls, how it differs from the verse) and bring trial songs; smart
  made no subgenre's default before then. The smart melody's seven gauges come as fields with Themes.
- **Deeper Themes** (S33, S38) and **Deeper Playing** (S28, S32): each theme's lines, Words; mood gauges, energy arc, modifiers.
- **Velocity**: An assessment per genre and track (spread, accents by place in the bar, the kit's balance, sections' loudness),
  with an opinion on how hard kicks should hit by kind of kick; **Intensity and Contrast** gauges on the Genre branch; **ghost
  notes** by genre and instrument, set by the subgenre.
- **Phrasing by section kind** (`PHRASING.md`): a verse of long lines and short tags, a pre-chorus of parallel lines rising, a
  chorus of hook, answer, running lines and a tag, a bridge of cells and calls, an ending's extra line; styles adjusting it
  through their templates. The professor fills in each subgenre's verse and chorus feel. 252 and 253 open (stages; a demo).
- **The wizard tuning itself** by simulated annealing against the checks, keeping variety, no AI model checked in; the
  professor asked whether the idea is right.
- **The bridge and the solo** of the rock preset sound like neither; the professor may judge from the notes.
- **The last chorus** ends its last line on the home note, earlier ones on any note of the home chord.
- **Syllables and stresses** per line of a melody, so that a verse sounds sung: a discussion.
- **The second hook**, a tag becoming its own thing (878): explained, then the professor asked. More than one hook in a song.
- **The hook in the intro and the ending** by genre (402 A); the hook in electronic (on or off, what a hook is there) and in
  classical, where it is a motif with another name and options of its own.
- **The professor's review of every style template**: Forms, each section's plan of lines, who plays where, nothing built
  being fixed; every melody writer's gauges and behaviours used per subgenre, the presets living in the templates; which
  settings a template should hold that it does not; findings as numbered proposals with examples.
- **Subgenre flavors**: Macro parameters choosing much about the musicians, customized later; how limited the templates are.
  Whether a song's structure should change with the subgenre.
- **Generators in what the wizard makes**: More of them, Humanize included; grooves applied wherever the music needs one;
  Phrasing and Guitarify used effectively; manual options by genre and subgenre.

## Genres

- Classical (S20), then the other styles (S4, S18).
- S48: country, then rock subgenres (pop punk, emo, ska punk, power pop, yacht rock), jazz last, template corrections from
  corpus measures first. "Ska" as a subgenre (which genre holds it, asked).
- "Soundtrack" with "adventure score" and "synth score" (S52).
- "TV sitcom" and "music box" (S53): proposals for subgenres, bands and forms, then templates. "TV epic": web research first.
- The obvious subgenres and genres missing: a discussion.
- 916: confirm the trade's numbers after hearing the sets.

## More Wizard Ideas

In the order of their priority, the highest first.

- **The wizard's three modes: Song, Chord Jam and MIDI**: The wizard opens on a choice of mode, the modes sharing as many
  panels and as much of the engine as they can. To discuss how it works before anything is built. 1. Song: the song wizard
  as it is. 2. Chord Jam: open-source chord progressions brought in, some as long as 64 bars; the person chooses the
  accompaniment, and the wizard makes a song of the progression. 3. MIDI: now the Import Wizard, agreed and planned in
  .claude/planning/DESIGNS.md ("The Import Wizard"). What stays an idea: where the corpus is installed, browsing it, not
  with a file picker but a browser built for it, pleasant to look through, so that a person reaches something like a hip-hop
  version of Drunken Sailor in a few steps; what a user may download and browse of the corpus, given each source's terms, is
  settled first. 4. iReal Pro's chord charts, like the import but different: a chart holds chords and a form rather than
  notes, so its chords are broken into scenes by the chart's sections and repeats, prompting where the chart leaves it
  unclear, and accompaniment is added as Chord Jam does. Claude may need to download a sample file to see the format.
- **The song wizard's drummers refined**: The players work and the user is happy with them from a sample of the trial songs.
  Later, the drummers may be refined: what each complexity adds in each style, how a drummer opens up from section to
  section, the fills and where they come. The decorations are in each style template's `players` block
  (`.claude/features/SONG_WIZARD.md`).
- **A Hip Hop genre for the song wizard**: The user's ask: a style template for hip hop, with its subgenres, from clean
  research, with nobody named. It would lean on drum breaks and loops (the queue's talk about breaks comes first) and on a
  voice part that is rhythm more than tune, which the melody engines do not make yet.
- **An Archaic genre for the wizard**: The user's ask: old styles as a genre of the wizard, with subgenres such as
  plainchant (one unaccompanied line in a church mode, free of a beat), harp music, renaissance songs and dances, and
  whatever else of early music fits (medieval dance tunes, lute songs, rounds, a drone under a tune). Each from clean
  research and from what the public-domain corpus can be measured for, with nobody named. It would want things the arranger
  lacks today: music with no meter, the church modes as scale choices, a band of one line or of voices alone, and no drums.
- **The song wizard's band has more than two guitarists**: The Band's Guitarists field offers 1 or 2 today. More is a common
  band and would mean something to the music, not only a number: a third guitarist can double the chords an octave apart or
  in another voicing, play an acoustic guitar under electric ones, or join the lead in a tune harmonized in thirds, two
  leads at once. Each of those is a way of playing to write for the genres that have it, and the solo could then pass
  between two lead players. Undecided: whether the count alone is chosen and the genre decides what the extra player does,
  or the person picks the extra player's job.
- **Jamming: a song interpreted and stretched out**: The user sees jam music not as a genre or a set of sounds but as a way
  of interpreting a song: stretching the song out in interesting ways. Waiting, by the user's choice, until discussed
  further. What is agreed in principle: a jam would be something a song of any rock or blues subgenre can do, a long section
  on one or two chords with rising Intensity and the lead passing between players, of two kinds, inside the song (the song's
  chords, quiet to a peak) and outside the song (a new groove in a mode, a change of key, a return); jams can be long. The
  "southern epic" ending, a jump in tempo and a long outro, goes with it. The notes are
  `.claude/notes/music_theory/genres/JAM.md`. Touches the wizard's section kinds, the Interplay plan and Intensity.
