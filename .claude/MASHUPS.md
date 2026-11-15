# How a Mashup Is Made

Claude's notes on making a mashup the user is happy with, and on bringing a classical work's notes in for one, written down at the
user's ask once the method worked. A mashup sets one public-domain work's notes on a band of another genre; it lives in
`examples/mashups/`, in the folder of the band's genre. The rule that a mashup never puts the borrowed tune on the lead alone over a
beat is in `.claude/FORMAT.md`, "Examples and demos"; this file says how that rule is met. It isn't imported: read it before making or
changing a mashup.

## What the User Judges a Mashup By

- **The genre is half the piece, in bars.** The failure to avoid is the medley record: a classical tune with drums under. The borrowed
  tune plays in about half of the bars, never three quarters, and the band has stretches with no borrowed note at all.
- **Every mashup has a form of its own**, the form its genre's records have, never one form shared by all. Jungle is intro, the break
  alone, drop, breakdown, snare roll, second drop. Bebop is head, solos, the bass walking alone, fours with the drums, a drum solo, head
  out. A brass band's funeral is a dirge out and a dance home. House opens on a kick and closes on bass and drums for the mix. A funk
  record gives the drummer some. Write the form down before any note.
- **What a form is built from**, each a section with a name: the drums alone (to open, as a break, to close); the bass alone or bass
  and drums; a riff of the genre with no tune (a flat second for surf, a flat fifth for psychedelic rock, a tritone for doom, palm-muted
  chugging for metal, piano stabs for hardcore and house); a breakdown with no drums and a build back; a solo or two over one or two
  chords; a twelve-bar chorus where the genre has one; parts entering one at a time; stop-time hits.
- **The drums change inside a section.** One bar of drums repeated sounds like a machine where the genre has a player: alternate two
  to four bars, a turn in the fourth, a re-cut for a break, and a different kit for the half-time, the quiet and the build.
- **The borrowed tune is treated as the genre treats a tune**: looped as a two-bar sample before it plays whole, tremolo-picked,
  traded between two voices every two or four bars with the other answering, put in the bass over half time, played by a
  synthesizer's arpeggiator when it is an arpeggio, slowed to a dirge. A tune in another meter is spread over the genre's bar by the
  genre's own rhythm (six notes over four beats as three, three and two) rather than forcing the band into the tune's meter, unless
  the meter is the point.
- **The borrowed notes are kept**: their pitches and their order, moved by octaves and keys as needed. Where a rhythm is changed, or
  a major version of a minor tune is made, the demo's notes say that it is this demo's doing.
- **Not one tune many times.** One mashup may use a famous tune; a second mashup takes another work. Pair a tune with the genre it
  already resembles (a gallop with thrash, a funeral march with a brass band's funeral, arpeggios with a synthesizer).
- **Nothing of the reference band's own songs is quoted.** The band, where one is named, gives the manner only: its drums, its sounds,
  its devices. Every riff, lick, fill and solo is new.
- **Sounds and range.** Each mashup has its genre's instruments, never the same five. Every pitch stays between 21 and 108, a lead in
  the range the real instrument has. It lasts about three minutes.
- **The notes of the demo** say, in this order: what is borrowed, from whom and when, and that it is public domain; how it was read
  (from a score of the corpus, or from Claude's knowledge of the score); what is new; then the Subgenre paragraph (drums first, the
  kick first, tempo, bass, sounds, and the form), the band's manner, and the checklist with the hook, the lift and the contrast.

## Bringing a Classical Work's Notes In

- **The right first.** The work must be public domain in the United States and in Europe: the composer dead more than seventy years
  and the work published before the American cutoff. A work still protected in Europe waits, however old it sounds.
- **A score, never a performance.** The notes are read from an engraved score's file, which sits on the grid: the corpus's scores in
  kern and MusicXML, and the Mutopia Project's MIDI files, which are typeset from scores. A MIDI file of someone playing, with rubato,
  cannot be read cleanly and is not used; a count of notes off the sixteenth grid shows which kind a file is.
- **The corpus before a download.** Look in `.corpus/` first. A download is one small file of the one work, from a site of
  public-domain scores, named to the user in the reply, kept in `.corpus/` and never checked in. No site whose terms forbid automated
  fetching is fetched.
- **Reading it.** Dump the file to notes on a grid of sixteenths with each note's part, look at it bar by bar before using it, and take
  the theme as the top voice of the part that carries it, bar numbers counted from the file and not from memory. Take the chords from
  the lowest note of each span when the score has a bass, and write them by hand when it is a single line.
- **When no clean score is at hand**, a short, famous theme may be written from Claude's knowledge of the score, a few bars checked
  for sense by ear of the numbers (the bar adds up, the cadence lands), and the demo's notes say so. A long or intricate passage is
  never written from memory.
- **A check that the borrowed notes survived**: when a mashup places a whole passage, the placed notes are listed and compared with the
  source after every change, so that an inserted section moves them without altering one.

## Where the Work Is Done

The builders are scripts kept untracked beside the trial sets, in the previews folder's homage trials: one engine that holds a band
as data (its kits by name, its bass and chord figures by name, its two lead voices, their licks and solo bars) and a form as a list of
sections, each naming its theme, who carries it, the kit or kits, the figures, the answers, a solo or a riff. A trial is built,
measured for length and range, rendered and landed one commit a mashup, with its section on its genre's mashup page.
